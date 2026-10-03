"""Validate frozen files without sending anything to the model."""

import argparse
import json
import math
from pathlib import Path

from benchmark.io import file_hash, load_jsonl
from benchmark.schema import ModelCase, labels, probability


def validate_data(cases: list[dict], gold: list[dict], expected_cases: int) -> None:
    if (
        len(cases) != expected_cases
        or sum(len(c["questions"]) for c in cases) != expected_cases * 5
    ):
        raise ValueError("Unexpected case/decision counts")
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids) or ids != [g["id"] for g in gold]:
        raise ValueError("Duplicate or misaligned IDs")
    for case, record in zip(cases, gold):
        ModelCase.from_dict(case)
        if len(case["questions"]) != 5 or set(case["questions"]) != set(record["gold"]):
            raise ValueError("Question/gold keys mismatch")
        for qid, question in case["questions"].items():
            answer = record["gold"][qid]
            ls = labels(question)
            if answer["type"] != question["type"] or str(answer["label"]) not in ls:
                raise ValueError("Invalid gold type/label")
            if set(answer["probabilities"]) != set(ls):
                raise ValueError("Invalid gold probability labels")
            ps = [probability(answer["probabilities"][k]) for k in ls]
            if not math.isclose(sum(ps), 1, abs_tol=1e-4, rel_tol=0):
                raise ValueError("Invalid gold probability mass")
            if question["type"] == "score":
                if not 0 <= float(answer["score"]) <= len(ls) - 1:
                    raise ValueError("Gold score outside ordered rubric")
            if question["type"] == "noul":
                probability(answer["noul"])


def validate_frozen(directory: Path, lock_path: Path | None = None) -> dict:
    if lock_path is None:
        lock_path = Path(__file__).with_name("lock.json")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for key in ("dataset_revision", "source_sha256", "frozen_sha256"):
        if manifest[key] != lock[key]:
            raise ValueError("Manifest does not match committed lock")
    for filename, expected in lock["frozen_sha256"].items():
        if file_hash(directory / filename) != expected:
            raise ValueError(f"Frozen hash mismatch: {filename}")
    for split, count in (("test", 400), ("train", 1200)):
        validate_data(
            load_jsonl(directory / f"{split}_inputs.jsonl"),
            load_jsonl(directory / f"{split}_gold.jsonl"),
            count,
        )
    if manifest["preparation_script_sha256"] != file_hash(Path(__file__).with_name("prepare.py")):
        raise ValueError("Preparation script changed: re-prepare before evaluating")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", type=Path, default=Path("benchmark/frozen"))
    args = parser.parse_args()
    print(json.dumps(validate_frozen(args.frozen), indent=2))


if __name__ == "__main__":
    main()
