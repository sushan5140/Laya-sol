"""Build gold-blind H5 repeated-run execution batches.

Creates one immutable set of 10 batch payloads. The same exact batch files are used
for runs A, B and C. No gold is read.
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
    ap.add_argument("--inputs",default="artifacts/h5_fresh_validation_100_model_inputs.json")
    ap.add_argument("--manifest",default="reports/h5_fresh_validation_100_manifest.json")
    ap.add_argument("--identity",default="reports/h5_fresh_validation_100_identity_index.json")
    ap.add_argument("--prompt",default="prompts/m2_explicit_noul_shield_prompt_v1.txt")
    ap.add_argument("--out-dir",default="artifacts/h5_fresh_m2_batches")
    ap.add_argument("--run-manifest",default="reports/h5_fresh_m2_batch_manifest.json")
    ap.add_argument("--batch-size",type=int,default=10)
    a=ap.parse_args()

    inputs=load(a.inputs); m=load(a.manifest); idx=load(a.identity)
    prompt=Path(a.prompt).read_text(encoding="utf-8")
    if len(inputs)!=100 or len(idx)!=100 or m.get("cases")!=100:
        raise ValueError("Expected exactly 100 fresh H5 cases")
    if m.get("contains_gold") is not False:
        raise ValueError("H5 manifest is not gold-blind")
    if [x["case_id"] for x in idx] != m["case_ids_in_output_order"]:
        raise ValueError("Identity/manifest order mismatch")

    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    batches=[]
    for bn,start in enumerate(range(0,100,a.batch_size),1):
        chunk_inputs=inputs[start:start+a.batch_size]
        chunk_idx=idx[start:start+a.batch_size]
        cases=[]
        for off,(payload,meta) in enumerate(zip(chunk_inputs,chunk_idx,strict=True)):
            ci=start+off
            cases.append({
                "case_index":ci,
                "case_id":meta["case_id"],
                "workflow":meta["workflow"],
                "request":{
                    "messages":[
                        {"role":"system","content":prompt},
                        {"role":"user","content":json.dumps(payload,ensure_ascii=False,separators=(",",":"))},
                    ]
                }
            })
        path=out/f"batch_{bn:02d}.json"
        dump(path,cases)
        batches.append({
            "batch_number":bn,
            "file":str(path).replace("\\","/"),
            "sha256":fh(path),
            "case_index_range":[start,start+len(cases)-1],
            "case_ids":[x["case_id"] for x in cases],
            "cases":len(cases),
        })

    rm={
        "protocol":"h5-repeated-run-consensus-v1",
        "contains_gold":False,
        "runs":["A","B","C"],
        "same_exact_batch_files_for_all_three_runs":True,
        "input_file":a.inputs,
        "input_sha256":fh(a.inputs),
        "selection_manifest_sha256":fh(a.manifest),
        "identity_index_sha256":fh(a.identity),
        "prompt_file":a.prompt,
        "prompt_sha256":shab(prompt.encode("utf-8")),
        "batch_size":a.batch_size,
        "total_batches":len(batches),
        "expected_cases_per_run":100,
        "expected_total_case_outputs":300,
        "batches":batches,
    }
    dump(a.run_manifest,rm)
    print(json.dumps({k:rm[k] for k in ["total_batches","expected_cases_per_run","expected_total_case_outputs","prompt_sha256"]},indent=2))

if __name__=="__main__":
    main()
