"""Select a preregistered second fresh TRAIN tranche for H5 repeated-run validation.

Gold-blind selection:
- exclude the original development 20;
- exclude the first fresh H4/M2 tranche of 100;
- use frozen TRAIN inputs only;
- select exactly 25 cases per workflow;
- rank by SHA256("laya-score-h5-validation-v1\n" + workflow + "\n" + case_id).
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from benchmark.io import digest, dump_json, encode, file_hash, load_jsonl
from benchmark.schema import ModelCase

ROOT = Path(__file__).resolve().parents[1]
SEED_PREFIX = "laya-score-h5-validation-v1"
PER_WORKFLOW = 25
WORKFLOWS = {
    "agent_trace_observability",
    "customer_service",
    "invoice_processing",
    "security_incidents",
}


def rank_key(workflow: str, case_id: str) -> str:
    return hashlib.sha256(
        f"{SEED_PREFIX}\n{workflow}\n{case_id}".encode("utf-8")
    ).hexdigest()


def read_ids(path: Path, expected: int) -> list[str]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    ids = obj.get("case_ids_in_output_order")
    if not isinstance(ids, list) or len(ids) != expected:
        raise ValueError(f"Expected {expected} IDs in {path}")
    if len(set(ids)) != len(ids):
        raise ValueError(f"Duplicate IDs in {path}")
    return ids


def main() -> None:
    frozen = ROOT / "benchmark/frozen/train_inputs.jsonl"
    if not frozen.exists():
        raise FileNotFoundError("Run python -m benchmark.prepare first")

    dev_ids = read_ids(ROOT / "reports/development_export.json", 20)
    first_fresh_ids = read_ids(ROOT / "reports/fresh_validation_100_manifest.json", 100)
    excluded = set(dev_ids) | set(first_fresh_ids)
    if len(excluded) != 120:
        raise ValueError("Expected 120 unique excluded cases (dev20 + fresh100)")

    cases = load_jsonl(frozen)
    by_workflow = {w: [] for w in WORKFLOWS}
    for case in cases:
        cid = case["id"]
        wf = case["workflow"]
        if not cid.startswith("tr_"):
            raise ValueError(f"Non-TRAIN case encountered: {cid}")
        if wf not in WORKFLOWS:
            raise ValueError(f"Unexpected workflow: {wf}")
        if cid not in excluded:
            by_workflow[wf].append(case)

    selected = []
    for wf in sorted(WORKFLOWS):
        ranked = sorted(
            by_workflow[wf],
            key=lambda c: (rank_key(wf, c["id"]), c["id"]),
        )
        if len(ranked) < PER_WORKFLOW:
            raise ValueError(f"Insufficient unused TRAIN cases for {wf}")
        selected.extend(ranked[:PER_WORKFLOW])

    counts = Counter(x["workflow"] for x in selected)
    if counts != Counter({w: 25 for w in WORKFLOWS}):
        raise ValueError(f"Unexpected workflow counts: {counts}")
    if len(selected) != 100 or len({x["id"] for x in selected}) != 100:
        raise ValueError("H5 tranche must contain exactly 100 unique cases")
    if {x["id"] for x in selected} & excluded:
        raise ValueError("H5 tranche overlaps an excluded case")

    visible = [ModelCase.from_dict(case).payload() for case in selected]
    out = ROOT / "artifacts/h5_fresh_validation_100_model_inputs.json"
    dump_json(out, visible)

    identity = [
        {
            "case_index": i,
            "case_id": case["id"],
            "workflow": case["workflow"],
            "payload_sha256": digest(encode(payload)),
        }
        for i, (case, payload) in enumerate(zip(selected, visible, strict=True))
    ]
    identity_path = ROOT / "reports/h5_fresh_validation_100_identity_index.json"
    dump_json(identity_path, identity)

    manifest = {
        "protocol": SEED_PREFIX,
        "source_split": "train",
        "selection": (
            "exclude dev20 and first fresh100; within each workflow sort by "
            "SHA256('laya-score-h5-validation-v1\\n' + workflow + '\\n' + case_id); "
            "take first 25"
        ),
        "cases": 100,
        "decisions": 500,
        "cases_per_workflow": 25,
        "excluded_dev20_ids": sorted(dev_ids),
        "excluded_first_fresh100_ids": sorted(first_fresh_ids),
        "excluded_total_unique": 120,
        "case_ids_in_output_order": [x["id"] for x in selected],
        "workflow_counts": dict(counts),
        "contains_gold": False,
        "model_inputs_sha256": file_hash(out),
        "identity_index_file": "reports/h5_fresh_validation_100_identity_index.json",
        "identity_index_sha256": file_hash(identity_path),
        "identity_index_derived_directly_from_frozen_train_inputs": True,
    }
    manifest_path = ROOT / "reports/h5_fresh_validation_100_manifest.json"
    dump_json(manifest_path, manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
