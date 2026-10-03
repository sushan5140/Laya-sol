"""Offline scoring, separately from inference."""

import argparse
import json
from pathlib import Path

from benchmark.io import dump_json, load_jsonl
from benchmark.score import score
from benchmark.validate import validate_frozen
from scripts.export_development import select_development


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--development", type=int, choices=[5, 20])
    parser.add_argument("--frozen", type=Path, default=Path("benchmark/frozen"))
    args = parser.parse_args()
    validate_frozen(args.frozen)
    split = "train" if args.development else "test"
    cases = load_jsonl(args.frozen / f"{split}_inputs.jsonl")
    if args.development:
        cases = select_development(cases)[: args.development]
    ids = {c["id"] for c in cases}
    gold = [g for g in load_jsonl(args.frozen / f"{split}_gold.jsonl") if g["id"] in ids]
    report = score(cases, gold, load_jsonl(args.run / "predictions.jsonl"))
    dump_json(args.run / "metrics.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
