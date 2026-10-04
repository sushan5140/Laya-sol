"""Apply the preregistered H5 repeated-run consensus rule.

Gold-blind. Must be frozen before any H5 correctness inspection.
"""

import argparse, copy, hashlib, json, math
from pathlib import Path

TOL=1e-4

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def fh(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def valid_unique_winner(answer):
    if not isinstance(answer,dict): return None
    probs=answer.get("probabilities")
    if not isinstance(probs,dict) or not probs: return None
    try: vals={str(k):float(v) for k,v in probs.items()}
    except Exception: return None
    if any(not math.isfinite(v) or v<0 or v>1 for v in vals.values()): return None
    if abs(sum(vals.values())-1.0)>TOL: return None
    top=max(vals.values())
    winners=[k for k,v in vals.items() if v==top]
    return winners[0] if len(winners)==1 else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--a",required=True)
    ap.add_argument("--b",required=True)
    ap.add_argument("--c",required=True)
    ap.add_argument("--output",default="artifacts/h5_fresh_consensus_predictions.json")
    ap.add_argument("--audit",default="reports/h5_fresh_consensus_routing_audit.json")
    a=ap.parse_args()

    A,B,C=load(a.a),load(a.b),load(a.c)
    if not (len(A)==len(B)==len(C)==100):
        raise ValueError("Expected 100 cases in each H5 run")

    out=copy.deepcopy(A)
    rows=[]; switches=0; baseline_ties_or_invalid=0; rerun_disagreement=0

    for i,(ra,rb,rc) in enumerate(zip(A,B,C,strict=True)):
        ids={(r.get("case_index"),r.get("case_id"),r.get("workflow")) for r in (ra,rb,rc)}
        if len(ids)!=1 or ra.get("case_index")!=i:
            raise ValueError(f"Run alignment failure at case {i}")
        qa=ra.get("answers",{}); qb=rb.get("answers",{}); qc=rc.get("answers",{})
        if set(qa)!=set(qb) or set(qa)!=set(qc):
            raise ValueError(f"Question-ID mismatch at case {i}")

        for qid,ansA in qa.items():
            # Only score answers have a probabilities mapping without selected.
            if not isinstance(ansA,dict) or "probabilities" not in ansA or "selected" in ansA:
                continue
            k=valid_unique_winner(ansA)
            if k is None:
                baseline_ties_or_invalid+=1
                rows.append({"case_index":i,"case_id":ra["case_id"],"question_id":qid,
                             "baseline_winner":None,"b_winner":None,"c_winner":None,
                             "switched":False,"reason":"baseline_tie_or_invalid"})
                continue
            wb=valid_unique_winner(qb.get(qid))
            wc=valid_unique_winner(qc.get(qid))
            if wb is not None and wc is not None and wb==wc and wb!=k:
                out[i]["answers"][qid]=copy.deepcopy(qb[qid])
                switches+=1
                rows.append({"case_index":i,"case_id":ra["case_id"],"question_id":qid,
                             "baseline_winner":k,"b_winner":wb,"c_winner":wc,
                             "switched":True,"reason":"two_rerun_consensus_alternative"})
            else:
                rerun_disagreement+=1
                rows.append({"case_index":i,"case_id":ra["case_id"],"question_id":qid,
                             "baseline_winner":k,"b_winner":wb,"c_winner":wc,
                             "switched":False,"reason":"retain_baseline"})

    dump(a.output,out)
    audit={
        "protocol":"h5-repeated-run-consensus-v1",
        "contains_gold":False,
        "cases":100,
        "switches":switches,
        "baseline_ties_or_invalid_preserved":baseline_ties_or_invalid,
        "non_switch_untied_score_questions":rerun_disagreement,
        "choice_noul_modified":False,
        "run_a_sha256":fh(a.a),
        "run_b_sha256":fh(a.b),
        "run_c_sha256":fh(a.c),
        "routed_output_sha256":fh(a.output),
        "rows":rows,
    }
    dump(a.audit,audit)
    print(json.dumps({k:audit[k] for k in ["switches","baseline_ties_or_invalid_preserved","non_switch_untied_score_questions","choice_noul_modified"]},indent=2))

if __name__=="__main__":
    main()
