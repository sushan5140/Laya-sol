"""Deterministically route H4 referee outputs against frozen M2 score predictions.

Gold-blind. This script MUST be frozen before H4 correctness is inspected.
Choice/noul are untouched; only eligible score answers may be replaced.
"""

import argparse, copy, hashlib, json, math
from pathlib import Path

TOL=1e-4

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def fh(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def unique_max(probs):
    try: vals={str(k):float(v) for k,v in probs.items()}
    except Exception: return None
    if not vals or any((not math.isfinite(v) or v<0 or v>1) for v in vals.values()): return None
    if abs(sum(vals.values())-1.0)>TOL: return None
    m=max(vals.values()); xs=[k for k,v in vals.items() if v==m]
    return xs[0] if len(xs)==1 else None

def exact_substring(quote, text):
    return isinstance(quote,str) and bool(quote) and quote in text

def valid_condition(c, rubric_text, state_text, required_status):
    return (
        isinstance(c,dict)
        and c.get("necessary") is True
        and c.get("status")==required_status
        and exact_substring(c.get("rubric_quote"), rubric_text)
        and exact_substring(c.get("state_quote"), state_text)
    )

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-inputs",required=True)
    ap.add_argument("--m2",required=True)
    ap.add_argument("--eligibility",required=True)
    ap.add_argument("--h4",required=True)
    ap.add_argument("--output",default="artifacts/fresh_validation_h4_routed_score_predictions.json")
    ap.add_argument("--audit",default="reports/fresh_validation_h4_routing_audit.json")
    a=ap.parse_args()

    run_inputs=load(a.run_inputs); m2=load(a.m2); elig=load(a.eligibility); h4=load(a.h4)
    if len(run_inputs)!=100 or len(m2)!=100: raise ValueError("expected 100 fresh cases")
    h4_by_idx={x["case_index"]:x for x in h4}
    if len(h4_by_idx)!=len(h4): raise ValueError("duplicate H4 case_index")

    private={row["case_index"]:row for row in elig["routing_private_rows"]}
    routed=copy.deepcopy(m2)
    rows=[]; switched=0; retained=0

    for i,(ri,base) in enumerate(zip(run_inputs,m2)):
        case=json.loads(ri["request"]["messages"][1]["content"])
        state_text=json.dumps(case["state"],ensure_ascii=False,separators=(",",":"))
        href=h4_by_idx.get(i)
        audit_comps=(href or {}).get("boundary_audit",{}).get("comparisons",[])
        for meta in private[i]["eligible"]:
            qid=meta["question_id"]; k=meta["m2_winner"]; j=meta["m2_runner_up"]; pair=meta["level_ids"]
            reasons=[]
            matches=[x for x in audit_comps if isinstance(x,dict) and x.get("question_id")==qid and x.get("level_ids")==pair]
            if len(matches)!=1:
                reasons.append("comparison_match_count_not_one")
                rows.append({"case_index":i,"case_id":ri["case_id"],"question_id":qid,"switched":False,"reasons":reasons}); retained+=1; continue
            c=matches[0]
            q=case["questions"][qid]
            if not exact_substring(c.get("target_question_quote"),q.get("instructions","")):
                reasons.append("invalid_target_question_quote")
            if c.get("licensed_preference")!=j:
                reasons.append("licensed_preference_not_runner_up")
            if c.get("preferred_requirements_complete") is not True:
                reasons.append("preferred_requirements_incomplete")
            levels=c.get("levels")
            if not isinstance(levels,dict) or set(levels.keys())!=set(pair):
                reasons.append("invalid_levels_object")
                levels={}
            criteria=q.get("criteria",[])
            try: jtxt=criteria[int(j)]; ktxt=criteria[int(k)]
            except Exception:
                reasons.append("invalid_rubric_indices"); jtxt=ktxt=""
            pref=((levels.get(j) or {}).get("necessary_conditions")) if isinstance(levels.get(j),dict) else None
            inc=((levels.get(k) or {}).get("necessary_conditions")) if isinstance(levels.get(k),dict) else None
            if not isinstance(pref,list) or not pref:
                reasons.append("preferred_requirements_empty")
            elif not all(valid_condition(x,jtxt,state_text,"established") for x in pref):
                reasons.append("preferred_requirement_validation_failed")
            if not isinstance(inc,list) or not any(valid_condition(x,ktxt,state_text,"contradicted") for x in inc):
                reasons.append("no_valid_incumbent_contradiction")
            score_ans=((href or {}).get("answers") or {}).get(qid)
            probs=(score_ans or {}).get("probabilities") if isinstance(score_ans,dict) else None
            if not isinstance(probs,dict):
                reasons.append("missing_referee_score_vector")
            else:
                expected={str(x) for x in range(len(criteria))}
                if set(map(str,probs.keys()))!=expected:
                    reasons.append("referee_score_keys_invalid")
                elif unique_max(probs)!=j:
                    reasons.append("referee_unique_max_not_runner_up")

            if reasons:
                retained+=1
            else:
                routed[i]["answers"][qid]=copy.deepcopy(score_ans)
                switched+=1
            rows.append({"case_index":i,"case_id":ri["case_id"],"question_id":qid,"m2_winner":k,"runner_up":j,"switched":not reasons,"reasons":reasons})

    dump(a.output,routed)
    audit={
        "protocol":"adjacent-evidence-v1","contains_gold":False,
        "eligible_score_questions":elig["eligible_score_questions"],
        "switches":switched,"retained":retained,
        "m2_sha256":fh(a.m2),"h4_raw_sha256":fh(a.h4),"routed_sha256":fh(a.output),
        "choice_noul_modified":False,
        "rows":rows
    }
    dump(a.audit,audit)
    print(json.dumps({k:audit[k] for k in ["eligible_score_questions","switches","retained","choice_noul_modified"]},indent=2))

if __name__=="__main__":
    main()
