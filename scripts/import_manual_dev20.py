"""Import raw manual development responses without changing the frozen evaluator."""

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from benchmark.io import digest, encode, file_hash, load_jsonl
from benchmark.schema import ModelCase, decision_id, validate_answer
from benchmark.score import METRIC_VERSION, score
from benchmark.validate import validate_frozen
from scripts.export_development import select_development

ROOT = Path(__file__).resolve().parents[1]
FROZEN_COMMIT = "ed4f84b6ada60bd46956211ffb9863f0af435cee"
LABEL = (
    "development-only manual GPT-6.1 Sol diagnostic — "
    "20 TRAIN cases / 100 decisions — not the official benchmark"
)
PREDICTIONS = "results/manual_dev20_gpt61sol_predictions.json"
METRICS = "results/manual_dev20_gpt61sol_metrics.json"
REPORT = "reports/manual_dev20_gpt61sol.md"


def frozen_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{FROZEN_COMMIT}:{path}"], cwd=ROOT)


def verify_context() -> tuple[list[dict], dict, dict]:
    protected = [
        "benchmark/io.py",
        "benchmark/schema.py",
        "benchmark/score.py",
        "benchmark/validate.py",
        "benchmark/prepare.py",
        "benchmark/lock.json",
        "benchmark/prompt_lock.json",
        "scripts/export_development.py",
        "prompts/v1.txt",
        "prompts/manual_chat_v1.txt",
        "artifacts/dry_run_20_model_inputs.json",
        "reports/development_export.json",
    ]
    for path in protected:
        if (ROOT / path).read_bytes() != frozen_bytes(path):
            raise ValueError(f"Protected source differs from frozen commit: {path}")
    manifest = validate_frozen(ROOT / "benchmark/frozen")
    provenance = json.loads(frozen_bytes("reports/development_export.json"))
    exported_bytes = frozen_bytes("artifacts/dry_run_20_model_inputs.json")
    if digest(exported_bytes) != provenance["model_inputs_sha256"]:
        raise ValueError("Development input provenance hash mismatch")
    if file_hash(ROOT / "prompts/v1.txt") != provenance["prompt_sha256"]:
        raise ValueError("Frozen prompt provenance hash mismatch")
    cases = select_development(load_jsonl(ROOT / "benchmark/frozen/train_inputs.jsonl"))
    if [case["id"] for case in cases] != provenance["case_ids_in_output_order"]:
        raise ValueError("Development provenance order mismatch")
    visible = [ModelCase.from_dict(case).payload() for case in cases]
    if visible != json.loads(exported_bytes):
        raise ValueError("Development export differs from original train states/questions")
    if any(set(case) != {"state", "questions"} for case in visible):
        raise ValueError("Unexpected model input fields")
    return cases, provenance, manifest


def unique_object(pairs: list[tuple[str, Any]]) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"Duplicate JSON key: {key}")
        obj[key] = value
    return obj


def map_outputs(outputs: Any, cases: list[dict]) -> tuple[list[dict], dict]:
    if not isinstance(outputs, list) or len(outputs) != 20 or len(cases) != 20:
        raise ValueError("Exactly 20 case outputs are required")
    records, invalid = [], []
    types: Counter = Counter()
    max_mass_error = 0.0
    for index, (output, case) in enumerate(zip(outputs, cases), start=1):
        if not isinstance(output, dict) or set(output) != {"answers"}:
            raise ValueError(f"Case {index}: expected only an answers object")
        answers = output["answers"]
        if not isinstance(answers, dict) or set(answers) != set(case["questions"]):
            raise ValueError(f"Case {index}: question IDs do not match the positional input")
        for qid, question in case["questions"].items():
            answer = answers[qid]
            status = "ok"
            types[question["type"]] += 1
            try:
                # Validation's return is intentionally discarded. Store/use the raw answer.
                validate_answer(question, answer)
                if question["type"] != "noul":
                    max_mass_error = max(
                        max_mass_error, abs(sum(answer["probabilities"].values()) - 1)
                    )
            except (ValueError, KeyError, TypeError) as exc:
                status = "invalid_output"
                invalid.append(
                    {
                        "case_position": index,
                        "case_id": case["id"],
                        "question_id": qid,
                        "reason": str(exc),
                    }
                )
            records.append(
                {
                    "decision_id": decision_id(case["id"], qid),
                    "case_id": case["id"],
                    "question_id": qid,
                    "status": status,
                    "answer": answer,
                }
            )
    if len(records) != 100:
        raise ValueError("Exactly 100 decisions are required")
    return records, {
        "cases": 20,
        "decisions": 100,
        "decision_types": dict(types),
        "invalid_output_count": len(invalid),
        "invalid_outputs": invalid,
        "probability_sum_absolute_tolerance": 1e-4,
        "max_valid_distribution_sum_error": max_mass_error,
        "choice_labels_allowed": not invalid,
        "all_probabilities_finite_and_in_range": not invalid,
        "all_distributions_within_tolerance": not invalid,
        "question_ids_match_positional_inputs": True,
        "mapping": "output array position to frozen development provenance position",
        "within_workflow_order": (
            "User attests exact order. Outputs contain no case IDs/states, so permutations "
            "within a workflow cannot be independently detected."
        ),
    }


def save_once(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"Refusing to overwrite a different saved artifact: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)


def render_report(result: dict) -> str:
    metrics = result["metrics"]

    def number(value):
        return "undefined" if value is None else f"{value:.9f}"

    lines = [
        "# Manual development diagnostic",
        "",
        f"**{LABEL}**",
        "",
        f"Hard accuracy: **{result['hard_accuracy_numerator']} / 100 "
        f"({result['hard_accuracy_percentage']:.2f}%)**. "
        f"Invalid outputs: **{result['validation']['invalid_output_count']}**.",
        "",
        "| Metric | Value | Denominator |",
        "|---|---:|---:|",
        f"| Hard accuracy | {number(metrics['accuracy'])} | 100 |",
        f"| Soft accuracy | {number(metrics['soft_accuracy'])} | 60 choice/noul |",
        f"| Brier against soft gold | {number(metrics['brier_score'])} | 60 choice/noul |",
        f"| ECE (15 bins) | {number(metrics['ece'])} | 100 |",
        f"| Score MAE | {number(metrics['score_mae'])} | 40 score |",
        f"| Within one level | {number(metrics['within_1_level'])} | 40 score |",
        "",
        "| Workflow | Correct / decisions | Accuracy |",
        "|---|---:|---:|",
    ]
    for key, value in result["accuracy_by_workflow"].items():
        lines.append(
            f"| {key} | {value['correct']} / {value['n']} | {100 * value['accuracy']:.2f}% |"
        )
    lines += ["", "| Decision type | Correct / decisions | Accuracy |", "|---|---:|---:|"]
    for key, value in result["accuracy_by_decision_type"].items():
        lines.append(
            f"| {key} | {value['correct']} / {value['n']} | {100 * value['accuracy']:.2f}% |"
        )
    lines += [
        "",
        "All 20 outputs have five decisions with the required question IDs. "
        "Selected choice labels, exact distribution keys, probability finiteness/range, "
        "and distribution sums were checked using the unchanged frozen schema. "
        f"Maximum accepted distribution sum error: "
        f"{result['validation']['max_valid_distribution_sum_error']:.18g}; tolerance: 1e-4.",
        "",
        "The 20 outputs were mapped by array position to the original export provenance. "
        "Workflow blocks and question IDs match. The user attests exact within-workflow order; "
        "outputs have no case IDs or states, so that part cannot be independently authenticated.",
        "",
        "Input bytes and provenance match the frozen commit. Inputs contain only state and "
        "questions, with no gold, reference predictions, evaluator scores, factors or agreement "
        "fields. The exact actual chat transcript, selected model and reasoning setting are "
        "user-reported; this import does not authenticate settings or additional chat context.",
        "",
        "The raw response was copied byte-for-byte, including formatting, numeric spelling "
        "and line endings. No selected answer or probability was changed, reordered, repaired "
        "or optimized. The unchanged scorer performs its already-frozen within-tolerance "
        "probability normalization internally for metric calculation; it does not rewrite the "
        "saved response. Soft accuracy/Brier exclude score questions. Score expectations use "
        "zero-based rubric levels. Noul selects true at probability >= 0.5. Choice accuracy "
        "uses the explicit selected label. Failures remain in the 100-decision denominator.",
        "",
        f"Frozen source commit: `{FROZEN_COMMIT}`.",
        f"Metric version: `{METRIC_VERSION}`.",
        f"Raw response SHA-256: `{result['provenance']['raw_response_sha256']}`.",
        f"Model input SHA-256: `{result['provenance']['model_inputs_sha256']}`.",
        f"Prompt SHA-256: `{result['provenance']['prompt_sha256']}`.",
        f"Scorer SHA-256: `{result['provenance']['scorer_sha256']}`.",
        "",
        "All protected source files, prompt, gold and frozen benchmark hashes were verified "
        "unchanged. Only TRAIN gold for the exported IDs was used to calculate this result. "
        "The official 400-case test was not evaluated. No model or API was called by the "
        "importer. API token usage, cost and latency are unavailable for this manual response.",
        "",
        "This small training-split diagnostic is not the official benchmark and supports "
        "no claim of superiority to Laya/Jev or unseen-data generalization. Published-reference "
        "reproduction remains unresolved. These results must not be used to alter the frozen "
        "official v1 prompt or tune against official test labels.",
        "",
        "Reproduce offline:",
        "",
        "```powershell",
        ".venv/Scripts/python.exe -m scripts.import_manual_dev20 "
        "--response results/manual_dev20_gpt61sol_predictions.json",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", type=Path, required=True)
    args = parser.parse_args()
    cases, provenance, manifest = verify_context()
    raw = args.response.read_bytes()
    save_once(ROOT / PREDICTIONS, raw)
    outputs = json.loads(raw, object_pairs_hook=unique_object)
    records, validation = map_outputs(outputs, cases)
    ids = {case["id"] for case in cases}
    gold = [
        row for row in load_jsonl(ROOT / "benchmark/frozen/train_gold.jsonl") if row["id"] in ids
    ]
    metrics = score(cases, gold, records)
    if metrics["n_decisions"] != 100 or metrics["failures"] != validation["invalid_output_count"]:
        raise AssertionError("Frozen scoring/validation denominators differ")

    def counts(values):
        return {
            key: {**value, "correct": round(value["accuracy"] * value["n"])}
            for key, value in values.items()
        }

    result = {
        "label": LABEL,
        "model": "GPT-6.1 Sol (manual; user-reported)",
        "split": "TRAIN development",
        "official_benchmark": False,
        "hard_accuracy_numerator": round(metrics["accuracy"] * 100),
        "hard_accuracy_denominator": 100,
        "hard_accuracy_percentage": metrics["accuracy"] * 100,
        "accuracy_by_workflow": counts(metrics["by_workflow"]),
        "accuracy_by_decision_type": counts(metrics["by_type"]),
        "validation": {
            **validation,
            "input_gold_or_evaluator_fields": False,
            "frozen_input_bytes_verified": True,
            "protected_files_unchanged": True,
        },
        "provenance": {
            "frozen_commit": FROZEN_COMMIT,
            "raw_response_sha256": digest(raw),
            "raw_response_bytes": len(raw),
            "model_inputs_sha256": provenance["model_inputs_sha256"],
            "prompt_sha256": provenance["prompt_sha256"],
            "scorer_sha256": file_hash(ROOT / "benchmark/score.py"),
            "frozen_gold_sha256": manifest["frozen_sha256"]["train_gold.jsonl"],
            "case_ids_in_output_order": provenance["case_ids_in_output_order"],
            "model_settings_independently_verified": False,
        },
        "metrics": metrics,
    }
    save_once(ROOT / METRICS, encode(result))
    save_once(ROOT / REPORT, render_report(result).encode("utf-8"))
    if (ROOT / PREDICTIONS).read_bytes() != raw:
        raise AssertionError("Raw response was changed")
    verify_context()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
