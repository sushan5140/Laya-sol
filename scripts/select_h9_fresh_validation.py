"""Select the fifth fresh TRAIN tranche for H9 validation."""

import hashlib, json
from collections import Counter
from pathlib import Path
from benchmark.io import digest, dump_json, encode, file_hash, load_jsonl
from benchmark.schema import ModelCase

ROOT=Path(__file__).resolve().parents[1]
SEED="laya-choice-h9-validation-v1"
WORKFLOWS={"agent_trace_observability","customer_service","invoice_processing","security_incidents"}
PER=25

def ids(path, expected):
    obj=json.loads(Path(path).read_text(encoding="utf-8"))
    xs=obj.get("case_ids_in_output_order")
    if not isinstance(xs,list) or len(xs)!=expected:
        raise ValueError(f"bad ids in {path}")
    return xs

def rk(w,c):
    return hashlib.sha256(f"{SEED}\n{w}\n{c}".encode()).hexdigest()

def main():
    train=ROOT/"benchmark/frozen/train_inputs.jsonl"
    if not train.exists():
        raise FileNotFoundError("run python -m benchmark.prepare first")

    excluded=set()
    excluded.update(ids(ROOT/"reports/development_export.json",20))
    excluded.update(ids(ROOT/"reports/fresh_validation_100_manifest.json",100))
    excluded.update(ids(ROOT/"reports/h5_fresh_validation_100_manifest.json",100))
    excluded.update(ids(ROOT/"reports/h6_fresh_validation_100_manifest.json",100))
    excluded.update(ids(ROOT/"reports/h7_fresh_validation_100_manifest.json",100))
    if len(excluded)!=420:
        raise ValueError(f"expected 420 unique exclusions, got {len(excluded)}")

    by={w:[] for w in WORKFLOWS}
    for c in load_jsonl(train):
        if c["id"] in excluded:
            continue
        by[c["workflow"]].append(c)

    sel=[]
    for w in sorted(WORKFLOWS):
        ranked=sorted(by[w],key=lambda c:(rk(w,c["id"]),c["id"]))
        if len(ranked)<PER:
            raise ValueError(f"not enough cases for {w}")
        sel.extend(ranked[:PER])

    if len(sel)!=100 or len({c["id"] for c in sel})!=100:
        raise ValueError("bad selection")
    cnt=Counter(c["workflow"] for c in sel)
    if cnt!=Counter({w:25 for w in WORKFLOWS}):
        raise ValueError(cnt)

    visible=[ModelCase.from_dict(c).payload() for c in sel]
    out=ROOT/"artifacts/h9_fresh_validation_100_model_inputs.json"
    dump_json(out,visible)

    idx=[{"case_index":i,"case_id":c["id"],"workflow":c["workflow"],"payload_sha256":digest(encode(p))}
         for i,(c,p) in enumerate(zip(sel,visible,strict=True))]
    idxp=ROOT/"reports/h9_fresh_validation_100_identity_index.json"
    dump_json(idxp,idx)

    man={
      "protocol":SEED,
      "source_split":"train",
      "cases":100,
      "decisions":500,
      "cases_per_workflow":25,
      "excluded_previous_train_cases":420,
      "case_ids_in_output_order":[c["id"] for c in sel],
      "workflow_counts":dict(cnt),
      "contains_gold":False,
      "model_inputs_sha256":file_hash(out),
      "identity_index_file":"reports/h9_fresh_validation_100_identity_index.json",
      "identity_index_sha256":file_hash(idxp),
      "selection":"exclude dev20 + H4 fresh100 + H5 fresh100 + H6 fresh100 + H7/H8 fresh100; rank by SHA256('laya-choice-h9-validation-v1\\n'+workflow+'\\n'+case_id); take first 25/workflow"
    }
    mp=ROOT/"reports/h9_fresh_validation_100_manifest.json"
    dump_json(mp,man)
    print(json.dumps(man,indent=2))

if __name__=="__main__":
    main()
