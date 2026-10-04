"""Build label-free H4 adjacent-boundary referee inputs from frozen M2 outputs.

This script MUST be run before loading fresh gold. It reads only:
- visible fresh model inputs,
- frozen M2 predictions,
- the preregistered fresh-ID manifest.

It never reads gold.
"""

import argparse
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def exact_unique_max(probabilities: dict[str, float]) -> str | None:
    values = {str(k): float(v) for k, v in probabilities.items()}
    if not values:
        return None
    maximum = max(values.values())
    winners = [k for k, v in values.items() if v == maximum]
    return winners[0] if len(winners) == 1 else None


def exact_unique_runner_up(
    probabilities: dict[str, float], winner: str
) -> str | None:
    values = {str(k): float(v) for k, v in probabilities.items() if str(k) != winner}
    if not values:
        return None
    second = max(values.values())
    runners = [k for k, v in values.items() if v == second]
    return runners[0] if len(runners) == 1 else None


def build_case(case: dict, prediction: dict) -> tuple[dict, list[dict]]:
    out = {
        "state": case["state"],
        "questions": case["questions"],
    }
    comparisons: list[dict] = []
    answers = prediction.get("answers", {})

    for question_id, question in case["questions"].items():
        if question.get("type") != "score":
            continue
        answer = answers.get(question_id)
        if not isinstance(answer, dict):
            continue
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, dict):
            continue

        winner = exact_unique_max(probabilities)
        if winner is None:
            continue

        runner_up = exact_unique_runner_up(probabilities, winner)
        if runner_up is None:
            continue

        try:
            winner_i = int(winner)
            runner_i = int(runner_up)
        except ValueError:
            continue

        criteria = question.get("criteria")
        if not isinstance(criteria, list):
            continue
        if winner_i < 0 or runner_i < 0:
            continue
        if winner_i >= len(criteria) or runner_i >= len(criteria):
            continue
        if abs(winner_i - runner_i) != 1:
            continue

        a, b = sorted((winner_i, runner_i))
        comparisons.append(
            {
                "question_id": question_id,
                "level_ids": [str(a), str(b)],
            }
        )

    out["score_boundary_audit"] = {
        "version": "adjacent-evidence-v1",
        "comparisons": comparisons,
    }
    return out, comparisons


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--m2", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()

    inputs = load_json(args.inputs)
    predictions = load_json(args.m2)
    manifest = load_json(args.manifest)

    expected_ids = manifest.get("case_ids_in_output_order")
    if not isinstance(expected_ids, list):
        raise ValueError("Manifest lacks case_ids_in_output_order")
    if len(inputs) != len(predictions) or len(inputs) != len(expected_ids):
        raise ValueError(
            f"Length mismatch: inputs={len(inputs)}, m2={len(predictions)}, ids={len(expected_ids)}"
        )

    referee_inputs = []
    audit_rows = []
    total_eligible = 0

    for index, (case, prediction, case_id) in enumerate(
        zip(inputs, predictions, expected_ids)
    ):
        built, comparisons = build_case(case, prediction)
        referee_inputs.append(built)
        total_eligible += len(comparisons)
        audit_rows.append(
            {
                "index": index,
                "case_id": case_id,
                "eligible_score_questions": comparisons,
            }
        )

    dump_json(args.output, referee_inputs)
    dump_json(
        args.audit,
        {
            "protocol": "adjacent-evidence-v1",
            "contains_gold": False,
            "cases": len(inputs),
            "eligible_score_questions": total_eligible,
            "rows": audit_rows,
        },
    )

    print(
        json.dumps(
            {
                "cases": len(inputs),
                "eligible_score_questions": total_eligible,
                "output": str(args.output),
                "audit": str(args.audit),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
