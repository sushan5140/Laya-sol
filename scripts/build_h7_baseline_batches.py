"""Build frozen H7 baseline choice batches from the fourth fresh TRAIN tranche.

Gold-blind. Uses the exact archived M3 choice-boundary prompt.
"""

import argparse, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def fh(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def shab(b): return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--inputs",default="artifacts/h7_fresh_validation_100_model_inputs.json")
    ap.add_argument("--manifest",default="reports/h7_fresh_validation_100_manifest.json")
    ap.add_argument("--identity",default="reports/h7_fresh_validation_100_identity_index.json")
    ap.add_argument("--prompt",default="prompts/m3_choice_boundary_fidelity_v1.txt")
    ap.add_argument("--out-dir",default="artifacts/h7_baseline_choice_batches")
    ap.add_argument("--run-manifest",default="reports/h7_baseline_choice_batch_manifest.json")
    ap.add_argument("--batch-size",type=int,default=10)
    a=ap.parse_args()

    inputs=load(a.inputs); m=load(a.manifest); idx=load(a.identity)
    if len(inputs)!=100 or len(idx)!=100 or m.get("cases")!=100:
        raise ValueError("expected 100 fresh H7 cases")
    if m.get("contains_gold") is not False:
        raise ValueError("H7 tranche is not gold-blind")
    if [x["case_id"] for x in idx] != m["case_ids_in_output_order"]:
        raise ValueError("identity order mismatch")

    prompt=Path(a.prompt).read_text(encoding="utf-8")
    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    batches=[]
    for bn,start in enumerate(range(0,100,a.batch_size),1):
        rows=[]
        for off,(payload,meta) in enumerate(zip(inputs[start:start+a.batch_size],idx[start:start+a.batch_size],strict=True)):
            ci=start+off
            rows.append({
                "case_index":ci,
                "case_id":meta["case_id"],
                "workflow":meta["workflow"],
                "request":{"messages":[
                    {"role":"system","content":prompt},
                    {"role":"user","content":json.dumps(payload,ensure_ascii=False,separators=(",",":"))}
                ]}
            })
        path=out/f"batch_{bn:02d}.json"; dump(path,rows)
        batches.append({
            "batch_number":bn,"file":str(path).replace("\\","/"),"sha256":fh(path),
            "case_indices":[x["case_index"] for x in rows],"case_ids":[x["case_id"] for x in rows]
        })

    rm={
      "protocol":"laya-choice-h7-validation-v1",
      "contains_gold":False,
      "input_sha256":fh(a.inputs),
      "selection_manifest_sha256":fh(a.manifest),
      "identity_index_sha256":fh(a.identity),
      "prompt_file":a.prompt,
      "prompt_sha256":shab(prompt.encode("utf-8")),
      "batch_size":a.batch_size,
      "total_batches":len(batches),
      "expected_cases":100,
      "batches":batches
    }
    dump(a.run_manifest,rm)
    print(json.dumps({"total_batches":len(batches),"prompt_sha256":rm["prompt_sha256"]},indent=2))

if __name__=="__main__": main()
