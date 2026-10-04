"""Select a preregistered fresh TRAIN validation tranche.

Selection protocol:
- exclude all case IDs already used in reports/development_export.json
- use only frozen TRAIN inputs
- select 25 cases per workflow
- order eligible case IDs by SHA256("laya-score-validation-v1\n" + workflow + "\n" + case_id)
- export visible model inputs only (no gold)
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from benchmark.io import digest, dump_json, encode, file_hash, load_jsonl
from benchmark.schema import ModelCase

ROOT = Path(__file__).resolve().parents[1]
SEED_PREFIX = "laya-score-validation-v1"
PER_WORKFLOW = 25

WORKFLOWS = {
    "agent_trace_observability",
    "customer_service",
    "invoice_processing",
    "security_incidents",
}


def rank_key(workflow: str, case_id: str) -> str:
    payload = f"{SEED_PREFIX}\n{workflow}\n{case_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_used_ids() -> set[str]:
    path = ROOT / "reports/development_export.json"
    if not path.exists():
        raise FileNotFoundError(
            "reports/development_export.json is required so previously used cases can be excluded"
        )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    ids = manifest.get("case_ids_in_output_order")
    if not isinstance(ids, list) or len(ids) != 20:
        raise ValueError("Expected exactly 20 previously used development case IDs")
    return set(ids)


def select_fresh(cases: list[dict], used_ids: set[str]) -> list[dict]:
    by_workflow: dict[str, list[dict]] = {w: [] for w in WORKFLOWS}

    for case in cases:
        if not case["id"].startswith("tr_"):
            raise ValueError(f"Non-TRAIN case encountered: {case['id']}")
        if case["workflow"] not in WORKFLOWS:
            raise ValueError(f"Unexpected workflow: {case['workflow']}")
        if case["id"] in used_ids:
            continue
        by_workflow[case["workflow"]].append(case)

    selected: list[dict] = []
    for workflow in sorted(WORKFLOWS):
        ranked = sorted(
            by_workflow[workflow],
            key=lambda c: (rank_key(workflow, c["id"]), c["id"]),
        )
        if len(ranked) < PER_WORKFLOW:
            raise ValueError(
                f"Not enough unused TRAIN cases for {workflow}: {len(ranked)} available"
            )
        selected.extend(ranked[:PER_WORKFLOW])

    counts = Counter(c["workflow"] for c in selected)
    expected = {w: PER_WORKFLOW for w in WORKFLOWS}
    if counts != expected:
        raise ValueError(f"Unexpected workflow balance: {counts}")

    if len({c["id"] for c in selected}) != len(selected):
        raise ValueError("Duplicate case IDs in validation tranche")

    return selected


def export() -> dict:
    frozen = ROOT / "benchmark/frozen"
    train_path = frozen / "train_inputs.jsonl"
    if not train_path.exists():
        raise FileNotFoundError(
            "benchmark/frozen/train_inputs.jsonl missing; run python -m benchmark.prepare first"
        )

    used_ids = load_used_ids()
    cases = load_jsonl(train_path)
    selected = select_fresh(cases, used_ids)

    visible = [ModelCase.from_dict(case).payload() for case in selected]
    output = ROOT / "artifacts/fresh_validation_100_model_inputs.json"
    dump_json(output, visible)

    identity_index = [
        {
            "case_index": i,
            "case_id": case["id"],
            "workflow": case["workflow"],
            "payload_sha256": digest(encode(payload)),
        }
        for i, (case, payload) in enumerate(zip(selected, visible, strict=True))
    ]
    identity_path = ROOT / "reports/fresh_validation_100_identity_index.json"
    dump_json(identity_path, identity_index)

    manifest = {
        "protocol": "laya-score-validation-v1",
        "source_split": "train",
        "selection": (
            "exclude prior dev20; within each workflow sort by "
            "SHA256('laya-score-validation-v1\\n' + workflow + '\\n' + case_id); "
            "take first 25"
        ),
        "cases": 100,
        "decisions": 500,
        "cases_per_workflow": PER_WORKFLOW,
        "excluded_prior_dev_ids": sorted(used_ids),
        "case_ids_in_output_order": [c["id"] for c in selected],
        "workflow_counts": dict(Counter(c["workflow"] for c in selected)),
        "contains_gold": False,
        "model_inputs_sha256": file_hash(output),
        "identity_index_file": "reports/fresh_validation_100_identity_index.json",
        "identity_index_sha256": file_hash(identity_path),
        "identity_index_derived_directly_from_frozen_train_inputs": True,
    }
    manifest_path = ROOT / "reports/fresh_validation_100_manifest.json"
    dump_json(manifest_path, manifest)
    return manifest


def main() -> None:
    print(json.dumps(export(), indent=2))


if __name__ == "__main__":
    main()
