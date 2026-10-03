"""Verify an externally supplied archived Laya run; never invoke a model."""

import argparse
import json
from pathlib import Path

from benchmark.io import dump_json, file_hash, load_jsonl
from benchmark.schema import decision_id, labels
from benchmark.score import METRIC_VERSION, score
from benchmark.validate import validate_frozen
from scripts.export_development import ROOT


def convert(question: dict, answer: dict) -> dict:
    if question["type"] == "noul":
        return {"probability_true": answer["noul"]}
    ls = labels(question)
    ps = [
        float(answer["probabilities"].get(k, 1e-6 if question["type"] == "choice" else 0.0))
        for k in ls
    ]
    if sum(ps) <= 0:
        raise ValueError("Invalid archived probability distribution")
    out = {"probabilities": {k: p / sum(ps) for k, p in zip(ls, ps)}}
    if question["type"] == "choice":
        out["selected"] = answer["choice"]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        required=True,
        help="JSON array of notebook predictions: id and pred (no rerun)",
    )
    args = parser.parse_args()
    manifest = validate_frozen(ROOT / "benchmark/frozen")
    cases = load_jsonl(ROOT / "benchmark/frozen/test_inputs.jsonl")
    gold = load_jsonl(ROOT / "benchmark/frozen/test_gold.jsonl")
    archive = json.loads(args.archive.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in archive}
    if len(by_id) != len(archive) or set(by_id) != {c["id"] for c in cases}:
        raise ValueError("Archive must contain exactly all 400 unique official case IDs")
    records = []
    for case in cases:
        item = by_id[case["id"]]
        if "questions" in item and item["questions"] != case["questions"]:
            raise ValueError("Archived question schema differs from frozen benchmark")
        if set(item["pred"]) != set(case["questions"]):
            raise ValueError("Archive must cover all 2,000 decisions")
        for qid, q in case["questions"].items():
            records.append(
                {
                    "decision_id": decision_id(case["id"], qid),
                    "case_id": case["id"],
                    "question_id": qid,
                    "status": "ok",
                    "answer": convert(q, item["pred"][qid]),
                }
            )
    metrics = score(cases, gold, records)
    # The published fine-tuning targets; never choose tolerance after observing a test run.
    targets = {
        "accuracy": 0.766,
        "soft_accuracy": 0.471,
        "brier_score": 0.062,
        "ece": 0.213,
        "score_mae": 0.242,
    }
    mismatches = {
        k: {"expected": target, "got": metrics[k]}
        for k, target in targets.items()
        if metrics[k] is None or abs(metrics[k] - target) > 0.0005
    }
    proof = {
        "status": "reproduced" if not mismatches and metrics["failures"] == 0 else "mismatch",
        "metric_version": METRIC_VERSION,
        "reference_model": "laya-typed-decisions",
        "archive_sha256": file_hash(args.archive),
        "test_inputs_sha256": manifest["frozen_sha256"]["test_inputs.jsonl"],
        "test_gold_sha256": manifest["frozen_sha256"]["test_gold.jsonl"],
        "scorer_sha256": file_hash(ROOT / "benchmark/score.py"),
        "metrics": metrics,
        "targets": targets,
        "tolerance": 0.0005,
        "mismatches": mismatches,
        "fixture_parity": "verified separately by pytest",
        "official_run_allowed": not mismatches and metrics["failures"] == 0,
    }
    dump_json(ROOT / "reports/reference_validation.json", proof)
    print(json.dumps(proof, indent=2))
    if proof["status"] != "reproduced":
        raise SystemExit("STOP: reference metric mismatch; do not run GPT-6.1 Sol")


if __name__ == "__main__":
    main()
