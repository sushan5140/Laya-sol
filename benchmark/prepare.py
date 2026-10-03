"""Obtain only pinned dataset assets; write separated frozen inputs and gold."""

import argparse
import json
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path

from benchmark.io import digest, dump_json, encode, file_hash
from benchmark.schema import ModelCase
from benchmark.validate import validate_data

ROOT = Path(__file__).resolve().parents[1]
DATASET_REVISION = "d0e2f0c42fef86cc15d1688d25a19f5ba7c85b18"
DATASET_ID = "LocalLLaMA/typed-decisions"


def read_parquet(path: Path, split: str) -> tuple[list[dict], list[dict]]:
    import pyarrow.parquet as pq

    cases, gold = [], []
    for row in pq.read_table(path).to_pylist():
        if row["split"] != split:
            raise ValueError("Source split mismatch")
        case = {
            "id": row["id"],
            "workflow": row["workflow"],
            "state": json.loads(row["state"]),
            "questions": json.loads(row["questions"]),
        }
        ModelCase.from_dict(case)
        cases.append(case)
        gold.append({"id": row["id"], "gold": json.loads(row["gold"])})
    return cases, gold


def asset(source: Path | None, split: str, cache: Path) -> Path:
    filename = f"all/{split}-00000-of-00001.parquet"
    if source is not None:
        sha = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip()
        if sha != DATASET_REVISION:
            raise ValueError("Dataset checkout is not the pinned revision")
        return source / filename
    path = cache / filename
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/{DATASET_REVISION}/{filename}"
        with urllib.request.urlopen(url, timeout=120) as response:
            path.write_bytes(response.read())
    return path


def freeze(source: Path | None, destination: Path, lock_path: Path) -> dict:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock["dataset_revision"] != DATASET_REVISION:
        raise ValueError("Pin/lock revision mismatch")
    prepared = {}
    for split in ("test", "train"):
        path = asset(source, split, ROOT / "work/source-cache")
        if file_hash(path) != lock["source_sha256"][split]:
            raise ValueError(f"Unexpected {split} parquet hash")
        cases, gold = read_parquet(path, split)
        validate_data(cases, gold, expected_cases=400 if split == "test" else 1200)
        prepared[split] = (cases, gold)
    test, train = prepared["test"][0], prepared["train"][0]
    if {c["id"] for c in test} & {c["id"] for c in train}:
        raise ValueError("Train/test ID overlap")
    if {digest(encode(c["state"])) for c in test} & {digest(encode(c["state"])) for c in train}:
        raise ValueError("Train/test state overlap")
    expected = {
        "agent_trace_observability",
        "customer_service",
        "invoice_processing",
        "security_incidents",
    }
    if Counter(c["workflow"] for c in test) != {k: 100 for k in expected}:
        raise ValueError("Unexpected test workflow counts")
    outputs = {}
    for split, (cases, gold) in prepared.items():
        for kind, rows in (("inputs", cases), ("gold", gold)):
            data = b"".join(encode(row) for row in rows)
            name = f"{split}_{kind}.jsonl"
            if digest(data) != lock["frozen_sha256"][name]:
                raise ValueError(f"Unexpected frozen hash: {name}")
            outputs[name] = data
    # Verify everything before writing, including existing outputs.
    for name, data in outputs.items():
        path = destination / name
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f"Refusing to overwrite changed frozen file: {name}")
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (destination / name).write_bytes(data)
    manifest = {
        **lock,
        "preparation_script_sha256": file_hash(Path(__file__)),
        "test_cases": 400,
        "test_decisions": 2000,
        "train_cases": 1200,
        "train_decisions": 6000,
    }
    dump_json(destination / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Pinned local dataset Git checkout")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmark/frozen")
    args = parser.parse_args()
    print(json.dumps(freeze(args.source, args.output, ROOT / "benchmark/lock.json"), indent=2))


if __name__ == "__main__":
    main()
