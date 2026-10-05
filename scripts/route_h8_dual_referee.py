"""Route H8 using dual independent blinded referee consensus.

Gold-blind. Reuses frozen H7 baseline and H7R referee A, combines with fresh referee B.
Only eligible choice questions may change. Noul/score remain byte-identical.
"""

import argparse, copy, hashlib, json, math
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def fh(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def unique_selected(answer, labels):
    if not isinstance(answer,dict): return None
    if answer.get("selected") not in labels: return None
    probs=answer.get("probabilities")
    if not isinstance(probs,dict) or set(probs)!=set(labels): return None
    vals={}
    for k in labels:
        v=probs[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:
            return None
        vals[k]=float(v)
    if abs(sum(vals.values())-1)>1e-4: return None
    m=max(vals.values()); winners=[k for k,v in vals.items() if v==m]
    if len(winners)!=1 or answer["selected"]!=winners[0]: return None
    return winners[0]

def index_by_case(rows):
    out={}
    for r in rows:
        i=r.get("case_index")
        if not isinstance(i,int) or i in out: raise ValueError("bad duplicate case_index")
        out[i]=r
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--inputs",default="artifacts/h7_fresh_validation_100_model_inputs.json")
    ap.add_argument("--baseline",default="artifacts/h7_baseline_choice_predictions.json")
    ap.add_argument("--ref-a",default="artifacts/h7r_referee_predictions.json")
    ap.add_argument("--ref-b",required=True)
    ap.add_argument("--eligibility",default="reports/h7r_referee_eligibility_manifest.json")
    ap.add_argument("--output",default="artifacts/h8_routed_choice_predictions.json")
    ap.add_argument("--audit",default="reports/h8_routing_audit.json")
    a=ap.parse_args()

    inputs=load(a.inputs); base=load(a.baseline); A=index_by_case(load(a.ref_a)); B=index_by_case(load(a.ref_b)); em=load(a.eligibility)
    if len(inputs)!=100 or len(base)!=100: raise ValueError("expected 100 baseline cases")

    priv={}
    for row in em.get("routing_private_rows",[]):
        priv[row["case_index"]]={x["question_id"]:x for x in row.get("eligible",[])}

    routed=copy.deepcopy(base)
    rows=[]; switches=0; eligible=0
    for i,(case,b,out) in enumerate(zip(inputs,base,routed,strict=True)):
        if b.get("case_index")!=i: raise ValueError(f"baseline mismatch {i}")
        ra=A.get(i,{}); rb=B.get(i,{})
        for qid,q in case["questions"].items():
            if q.get("type")!="choice": continue
            meta=priv.get(i,{}).get(qid)
            if meta is None: continue
            eligible += 1
            winner=meta["baseline_winner"]; runner=meta["baseline_runner_up"]; labels=list(q["criteria"])
            aa=ra.get("answers",{}).get(qid) if isinstance(ra.get("answers"),dict) else None
            ba=rb.get("answers",{}).get(qid) if isinstance(rb.get("answers"),dict) else None
            aw=unique_selected(aa,labels)
            bw=unique_selected(ba,labels)
            both=(aw==runner and bw==runner)
            if both:
                out["answers"][qid]=copy.deepcopy(ba)
                switches+=1
                action="switch"
            else:
                action="retain"
            rows.append({
                "case_index":i,"case_id":b.get("case_id"),"workflow":b.get("workflow"),"question_id":qid,
                "baseline_winner":winner,"runner_up":runner,"referee_a_unique_selected":aw,
                "referee_b_unique_selected":bw,"action":action
            })

    for i,(b,o,case) in enumerate(zip(base,routed,inputs,strict=True)):
        for qid,q in case["questions"].items():
            if q.get("type")!="choice" and b["answers"][qid]!=o["answers"][qid]:
                raise ValueError(f"non-choice changed at {i}/{qid}")

    dump(a.output,routed)
    audit={
      "protocol":"h8-dual-blinded-referee-consensus-v1",
      "contains_gold":False,"eligible_choice_questions":eligible,"switches":switches,
      "noul_score_modified":False,
      "source_baseline_sha256":fh(a.baseline),"source_referee_a_sha256":fh(a.ref_a),
      "source_referee_b_sha256":fh(a.ref_b),"eligibility_manifest_sha256":fh(a.eligibility),
      "output_sha256":fh(a.output),"rows":rows
    }
    dump(a.audit,audit)
    print(json.dumps({k:audit[k] for k in ["eligible_choice_questions","switches","noul_score_modified","output_sha256"]},indent=2))

if __name__=="__main__": main()
