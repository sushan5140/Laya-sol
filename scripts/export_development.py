"""Export exactly 20 balanced training cases with only state and questions."""

import json
from collections import Counter
from pathlib import Path

from benchmark.io import dump_json, file_hash, load_jsonl
from benchmark.schema import ModelCase

ROOT = Path(__file__).resolve().parents[1]


def select_development(cases: list[dict]) -> list[dict]:
    counts: Counter = Counter()
    selected = []
    for case in cases:
        # The upstream IDs unambiguously mark training cases.
        if not case["id"].startswith("tr_"):
            raise ValueError("Development selection must use training cases only")
        if counts[case["workflow"]] < 5:
            selected.append(case)
            counts[case["workflow"]] += 1
    if len(selected) != 20 or len(counts) != 4 or set(counts.values()) != {5}:
        raise ValueError("Expected five training cases from each of four workflows")
    return selected


def export(frozen: Path, output: Path) -> dict:
    selected = select_development(load_jsonl(frozen / "train_inputs.jsonl"))
    visible = [ModelCase.from_dict(case).payload() for case in selected]
    dump_json(output, visible)
    prompt_path = ROOT / "prompts/v1.txt"
    manual_path = ROOT / "prompts/manual_chat_v1.txt"
    manual_path.write_bytes(prompt_path.read_bytes())
    manifest = {
        "source_split": "train",
        "selection": "first five rows per workflow, source order",
        "cases": 20,
        "decisions": 100,
        "case_ids_in_output_order": [c["id"] for c in selected],
        "model_inputs_sha256": file_hash(output),
        "prompt_sha256": file_hash(prompt_path),
        "contains_gold": False,
        "model_execution": "not run",
    }
    dump_json(ROOT / "reports/development_export.json", manifest)
    return manifest


def main() -> None:
    print(
        json.dumps(
            export(ROOT / "benchmark/frozen", ROOT / "artifacts/dry_run_20_model_inputs.json"),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
