"""Build gold-blind H4 referee batches from verified fresh M2 predictions.

Reads no gold. The referee sees only the original grouped case plus the canonical
adjacent level pair; M2 probabilities/winner/runner-up remain outside model input.
"""

import argparse, hashlib, json
from pathlib import Path

H4_DELTA = """Evaluate the complete original grouped decision set. For each comparison listed in score_boundary_audit, assess the two listed levels using the original question, its complete rubric, and the supplied state.

Identify the exact question phrase that specifies the assessed quantity, event, or consequence. Identify every explicit necessary condition of the level you prefer. Preserve thresholds, conjunctions, scope, and exclusions literally. Descriptive examples are not necessary conditions unless the rubric makes them requirements.

Mark each condition as established, contradicted, or unknown. Quote the rubric text defining the condition and the state text supporting the assessment. Missing mention is unknown; possibility does not establish occurrence.

License a preference only if every explicit necessary condition of the preferred level is established and at least one explicit necessary condition of the other level is contradicted. If the rubric does not support this distinction, the evidence is incomplete, or either requirement cannot be assessed, return no licensed preference.

Return the ordinary grouped response and the boundary audit using the supplied output schema. The final score vector must agree with any licensed preference."""

SCHEMA = """OUTPUT SCHEMA — return only a JSON array, one object per supplied case, in exact input order:
{
  "answers": <ordinary grouped answers object using the base M2 schema>,
  "boundary_audit": {
    "comparisons": [
      {
        "question_id": "<exact original score question id>",
        "level_ids": ["<earlier canonical id>","<later canonical id>"],
        "target_question_quote": "<nonempty exact contiguous substring of that question's instructions>",
        "licensed_preference": "<one of level_ids or null>",
        "preferred_requirements_complete": true|false,
        "levels": {
          "<level id>": {
            "necessary_conditions": [
              {
                "necessary": true,
                "status": "established"|"contradicted"|"unknown",
                "rubric_quote": "<nonempty exact contiguous substring of that level's rubric text>",
                "state_quote": "<nonempty exact contiguous substring of the compact JSON-serialized supplied state>"
              }
            ]
          }
        }
      }
    ]
  }
}
For every listed comparison, include both listed level IDs under levels. Do not expose or infer any incumbent model prediction; judge only the supplied state, question, rubric, and level pair."""

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def dump(path, obj):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def file_hash(path):
    return sha256_bytes(Path(path).read_bytes())

def unique_max(probs):
    vals={str(k):float(v) for k,v in probs.items()}
    if not vals: return None
    m=max(vals.values()); xs=[k for k,v in vals.items() if v==m]
    return xs[0] if len(xs)==1 else None

def unique_runner(probs, winner):
    vals={str(k):float(v) for k,v in probs.items() if str(k)!=winner}
    if not vals: return None
    m=max(vals.values()); xs=[k for k,v in vals.items() if v==m]
    return xs[0] if len(xs)==1 else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-inputs", required=True)
    ap.add_argument("--m2", required=True)
    ap.add_argument("--out-dir", default="artifacts/fresh_h4_batches")
    ap.add_argument("--manifest", default="reports/fresh_h4_eligibility_manifest.json")
    ap.add_argument("--batch-size", type=int, default=10)
    a=ap.parse_args()

    run_inputs=load(a.run_inputs); m2=load(a.m2)
    if len(run_inputs)!=100 or len(m2)!=100:
        raise ValueError("expected exactly 100 verified fresh cases")
    for i,(r,p) in enumerate(zip(run_inputs,m2)):
        if r["case_index"]!=i or p["case_index"]!=i or r["case_id"]!=p["case_id"]:
            raise ValueError(f"alignment failure at {i}")

    base_prompts={r["request"]["messages"][0]["content"] for r in run_inputs}
    if len(base_prompts)!=1: raise ValueError("M2 system prompt is not byte-identical across run inputs")
    system_prompt=next(iter(base_prompts)).rstrip()+"\n\n"+H4_DELTA+"\n\n"+SCHEMA+"\n"

    eligible_cases=[]; rows=[]; eligible_q=0
    for r,p in zip(run_inputs,m2):
        case=json.loads(r["request"]["messages"][1]["content"])
        comps=[]; private=[]
        for qid,q in case["questions"].items():
            if q.get("type")!="score": continue
            ans=p.get("answers",{}).get(qid,{})
            probs=ans.get("probabilities")
            if not isinstance(probs,dict): continue
            k=unique_max(probs)
            if k is None: continue
            j=unique_runner(probs,k)
            if j is None: continue
            try: ki,ji=int(k),int(j)
            except ValueError: continue
            criteria=q.get("criteria")
            if not isinstance(criteria,list) or not (0<=ki<len(criteria) and 0<=ji<len(criteria)): continue
            if abs(ki-ji)!=1: continue
            lo,hi=sorted((ki,ji))
            comps.append({"question_id":qid,"level_ids":[str(lo),str(hi)]})
            private.append({"question_id":qid,"m2_winner":str(ki),"m2_runner_up":str(ji),"level_ids":[str(lo),str(hi)]})
        rows.append({"case_index":r["case_index"],"case_id":r["case_id"],"workflow":r["workflow"],"eligible":private})
        if comps:
            eligible_q += len(comps)
            eligible_cases.append({
                "case_index":r["case_index"],"case_id":r["case_id"],"workflow":r["workflow"],
                "model_case":{"state":case["state"],"questions":case["questions"],"score_boundary_audit":{"version":"adjacent-evidence-v1","comparisons":comps}}
            })

    out=Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    batches=[]
    for b,start in enumerate(range(0,len(eligible_cases),a.batch_size),1):
        chunk=eligible_cases[start:start+a.batch_size]
        payload={"system_prompt":system_prompt,"cases":[x["model_case"] for x in chunk]}
        path=out/f"batch_{b:02d}.json"; dump(path,payload)
        batches.append({
            "batch_number":b,"file":str(path).replace("\\","/"),"sha256":file_hash(path),
            "case_indices":[x["case_index"] for x in chunk],"case_ids":[x["case_id"] for x in chunk],
            "cases":len(chunk)
        })

    manifest={
        "protocol":"adjacent-evidence-v1","contains_gold":False,
        "source_run_inputs_sha256":file_hash(a.run_inputs),"source_m2_predictions_sha256":file_hash(a.m2),
        "eligible_cases":len(eligible_cases),"eligible_score_questions":eligible_q,
        "ineligible_score_questions":200-eligible_q,"batch_size":a.batch_size,"total_batches":len(batches),
        "referee_does_not_receive_m2_winner_or_probabilities":True,
        "system_prompt_sha256":sha256_bytes(system_prompt.encode()),
        "batches":batches,"routing_private_rows":rows
    }
    dump(a.manifest,manifest)
    print(json.dumps({k:manifest[k] for k in ["eligible_cases","eligible_score_questions","ineligible_score_questions","total_batches"]},indent=2))

if __name__=="__main__":
    main()
