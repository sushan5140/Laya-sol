"""Route H7 blinded top-two referee outputs through the frozen strict license.

Gold-blind. Only choice questions may change; noul/score remain byte-identical to baseline.
"""

import argparse, copy, hashlib, json, math
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def fh(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def unique_max(answer, labels):
    if not isinstance(answer,dict) or answer.get("selected") not in labels: return None
    probs=answer.get("probabilities")
    if not isinstance(probs,dict) or set(probs)!=set(labels): return None
    vals={}
    for k in labels:
        v=probs[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:
            return None
        vals[k]=float(v)
    if abs(sum(vals.values())-1)>1e-4: return None
    m=max(vals.values()); wins=[k for k,v in vals.items() if v==m]
    if len(wins)!=1 or answer["selected"]!=wins[0]: return None
    return wins[0]

def exact_nonempty_quote(quote, haystack):
    return isinstance(quote,str) and bool(quote) and quote in haystack

def find_audit(ref, qid, pair):
    ba=ref.get("boundary_audit")
    if not isinstance(ba,dict): return None
    comps=ba.get("comparisons")
    if not isinstance(comps,list): return None
    hits=[]
    for c in comps:
        if not isinstance(c,dict): continue
        labs=c.get("option_labels")
        if c.get("question_id")==qid and isinstance(labs,list) and labs==pair:
            hits.append(c)
    return hits[0] if len(hits)==1 else None

def switch_licensed(comp, runner, winner, pair, criteria, state_text):
    reasons=[]
    if comp is None:
        return False,["missing_or_nonunique_audit"]
    if comp.get("licensed_preference")!=runner:
        reasons.append("licensed_preference_not_runner_up")
    opts=comp.get("options")
    if not isinstance(opts,dict) or set(opts)!=set(pair):
        reasons.append("invalid_options_block")
        return False,reasons

    preferred=opts.get(runner,{})
    incumbent=opts.get(winner,{})
    pcs=preferred.get("distinguishing_conditions") if isinstance(preferred,dict) else None
    ics=incumbent.get("distinguishing_conditions") if isinstance(incumbent,dict) else None
    if not isinstance(pcs,list) or not pcs:
        reasons.append("preferred_conditions_empty")
        pcs=[]

    preferred_ok=True
    additional=[]
    for c in pcs:
        if not isinstance(c,dict):
            preferred_ok=False; continue
        if c.get("status")!="established":
            preferred_ok=False
        if not exact_nonempty_quote(c.get("option_quote"),criteria[runner]):
            preferred_ok=False
        if not exact_nonempty_quote(c.get("state_quote"),state_text):
            preferred_ok=False
        if c.get("additional_condition_for_specificity") is True:
            additional.append(c)
    if not preferred_ok:
        reasons.append("preferred_conditions_not_all_established_with_quotes")

    contradicted=False
    if isinstance(ics,list):
        for c in ics:
            if not isinstance(c,dict): continue
            if c.get("status")=="contradicted" and exact_nonempty_quote(c.get("option_quote"),criteria[winner]) and exact_nonempty_quote(c.get("state_quote"),state_text):
                contradicted=True
                break

    specific=comp.get("strictly_more_specific") is True
    specificity_ok=False
    if specific and additional:
        specificity_ok=all(
            isinstance(c,dict)
            and c.get("status")=="established"
            and exact_nonempty_quote(c.get("option_quote"),criteria[runner])
            and exact_nonempty_quote(c.get("state_quote"),state_text)
            for c in additional
        )
    if not (contradicted or specificity_ok):
        reasons.append("no_contradiction_or_valid_specificity")

    return len(reasons)==0,reasons

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--inputs",default="artifacts/h7_fresh_validation_100_model_inputs.json")
    ap.add_argument("--baseline",required=True)
    ap.add_argument("--referee",required=True)
    ap.add_argument("--eligibility",default="reports/h7_referee_eligibility_manifest.json")
    ap.add_argument("--output",default="artifacts/h7_routed_choice_predictions.json")
    ap.add_argument("--audit",default="reports/h7_routing_audit.json")
    a=ap.parse_args()

    inputs=load(a.inputs); base=load(a.baseline); refs=load(a.referee); em=load(a.eligibility)
    if len(inputs)!=100 or len(base)!=100: raise ValueError("expected 100 baseline cases")
    ref_by_index={}
    for r in refs:
        ci=r.get("case_index")
        if not isinstance(ci,int) or ci in ref_by_index: raise ValueError("bad/duplicate referee case_index")
        ref_by_index[ci]=r

    private={}
    for row in em.get("routing_private_rows",[]):
        ci=row["case_index"]
        private[ci]={x["question_id"]:x for x in row.get("eligible",[])}

    routed=copy.deepcopy(base)
    rows=[]; switches=0; eligible=0; retained=0
    nonchoice_modified=False

    for i,(case,b,out) in enumerate(zip(inputs,base,routed,strict=True)):
        if b.get("case_index")!=i: raise ValueError(f"baseline case_index mismatch {i}")
        ref=ref_by_index.get(i,{})
        state_text=json.dumps(case["state"],ensure_ascii=False,separators=(",",":"))
        for qid,q in case["questions"].items():
            if q.get("type")!="choice":
                if out.get("answers",{}).get(qid)!=b.get("answers",{}).get(qid):
                    nonchoice_modified=True
                continue
            meta=private.get(i,{}).get(qid)
            if meta is None: continue
            eligible += 1
            winner=meta["baseline_winner"]; runner=meta["baseline_runner_up"]; pair=meta["option_labels"]
            criteria=q["criteria"]
            comp=find_audit(ref,qid,pair)
            ok,reasons=switch_licensed(comp,runner,winner,pair,criteria,state_text)
            ref_ans=ref.get("answers",{}).get(qid) if isinstance(ref.get("answers"),dict) else None
            ref_winner=unique_max(ref_ans,list(criteria)) if ref_ans is not None else None
            if ref_winner!=runner:
                ok=False; reasons=reasons+["referee_unique_max_not_runner_up"]
            if ok:
                out["answers"][qid]=copy.deepcopy(ref_ans)
                switches += 1
                action="switch"
            else:
                retained += 1
                action="retain"
            rows.append({"case_index":i,"case_id":b.get("case_id"),"workflow":b.get("workflow"),
                         "question_id":qid,"baseline_winner":winner,"runner_up":runner,
                         "pair":pair,"action":action,"reasons":reasons})

    if nonchoice_modified: raise ValueError("noul/score modified")
    audit={
      "protocol":"top-two-evidence-v1","contains_gold":False,
      "eligible_choice_questions":eligible,"switches":switches,"retained":retained,
      "choice_noul_score_scope":"only eligible choice questions can change",
      "noul_score_modified":False,
      "source_baseline_sha256":fh(a.baseline),"source_referee_sha256":fh(a.referee),
      "eligibility_manifest_sha256":fh(a.eligibility),
      "output_sha256":None,"rows":rows
    }
    dump(a.output,routed)
    audit["output_sha256"]=fh(a.output)
    dump(a.audit,audit)
    print(json.dumps({k:audit[k] for k in ["eligible_choice_questions","switches","retained","noul_score_modified","output_sha256"]},indent=2))

if __name__=="__main__": main()
