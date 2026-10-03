"""OFFLINE MOCK validation only. Does not call a model or estimate model quality."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from adapters.gpt61_sol import GPT61SolAdapter
from benchmark.io import dump_json, load_jsonl
from benchmark.schema import labels
from benchmark.score import score
from benchmark.validate import validate_frozen
from scripts.export_development import ROOT, select_development
from scripts.run_benchmark import configuration, run


class MockClient:
    def __init__(self, transient_error: bool = True) -> None:
        self.responses = self
        self.calls = 0
        self.transient_error = transient_error

    def create(self, **request):
        self.calls += 1
        if self.transient_error and self.calls == 1:
            raise TimeoutError("offline injected transient failure")
        payload = json.loads(request["input"][0]["content"])
        answers: dict[str, dict[str, Any]] = {}
        for qid, question in payload["questions"].items():
            ls = labels(question)
            if question["type"] == "noul":
                answers[qid] = {"probability_true": 0.5}
            else:
                answers[qid] = {"probabilities": {k: 1 / len(ls) for k in ls}}
                if question["type"] == "choice":
                    answers[qid]["selected"] = ls[0]
        return SimpleNamespace(
            status="completed",
            id="mock-response",
            model="OFFLINE-MOCK",
            output_text=json.dumps({"answers": answers}),
            usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens_details": {"reasoning_tokens": 0},
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, choices=[5, 20], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validate_frozen(ROOT / "benchmark/frozen")
    cases = select_development(load_jsonl(ROOT / "benchmark/frozen/train_inputs.jsonl"))[
        : args.cases
    ]
    ids = {c["id"] for c in cases}
    gold = [g for g in load_jsonl(ROOT / "benchmark/frozen/train_gold.jsonl") if g["id"] in ids]
    prompt = (ROOT / "prompts/v1.txt").read_bytes().decode()
    client = MockClient()
    adapter = GPT61SolAdapter(client, prompt, sleep=lambda _: None)
    config = configuration(cases, prompt, "OFFLINE-MOCK")
    summary = run(cases, adapter, args.output, config)
    calls_before_resume = client.calls
    resumed = run(cases, adapter, args.output, config)
    if client.calls != calls_before_resume or resumed != summary:
        raise AssertionError("Resume issued duplicate calls or changed results")
    report = {
        "mode": "OFFLINE-MOCK",
        "model_execution": "not run",
        "summary": summary,
        "resume_new_calls": 0,
        "injected_transient_error": True,
        "metrics": score(cases, gold, load_jsonl(args.output / "predictions.jsonl")),
        "usage_and_cost": "synthetic accounting fixture, not measured API cost",
        "latency": "local mock execution only, not model/API latency",
    }
    dump_json(args.output / "dry_run_report.json", report)
    dump_json(ROOT / f"reports/offline_dry_run_{args.cases}.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
