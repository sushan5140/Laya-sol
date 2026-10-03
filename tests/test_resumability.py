import json

import pytest

from adapters.gpt61_sol import GPT61SolAdapter
from benchmark.io import load_jsonl
from scripts.dry_run import MockClient
from scripts.run_benchmark import run


def test_resume_no_duplicate_calls_or_decisions(sample, tmp_path):
    client = MockClient(transient_error=False)
    adapter = GPT61SolAdapter(client, "prompt")
    cases = [sample.as_dict()]
    result = run(cases, adapter, tmp_path / "run", {"mode": "mock"})
    assert run(cases, adapter, tmp_path / "run", {"mode": "mock"}) == result
    assert client.calls == 1
    records = load_jsonl(tmp_path / "run/predictions.jsonl")
    assert len(records) == 3 and len({r["decision_id"] for r in records}) == 3
    with pytest.raises(ValueError, match="configuration"):
        run(cases, adapter, tmp_path / "run", {"mode": "different"})


def test_failure_checkpoints_not_retried_on_resume(sample, tmp_path):
    class Failing:
        calls = 0

        def predict(self, case):
            self.calls += 1
            return {
                "answers": {qid: {"status": "api_error"} for qid in case.questions},
                "attempts": [{"usage": {}, "estimated_cost_usd": None}],
                "latency_ms": 1,
            }

    adapter = Failing()
    path = tmp_path / "run"
    result = run([sample.as_dict()], adapter, path, {"mode": "mock"})
    run([sample.as_dict()], adapter, path, {"mode": "mock"})
    assert adapter.calls == 1 and result["failed_decisions"] == 3
    assert json.loads((path / "summary.json").read_text())["decisions"] == 3


def test_concurrent_writer_refused(sample, tmp_path):
    (tmp_path / "writer.lock").touch()
    with pytest.raises(FileExistsError):
        run([sample.as_dict()], None, tmp_path, {})


def test_interruption_resumes_only_remaining_cases(sample, tmp_path):
    class Interrupted:
        def __init__(self):
            self.calls = 0
            self.adapter = GPT61SolAdapter(MockClient(False), "p")

        def predict(self, case):
            self.calls += 1
            if self.calls == 2:
                raise KeyboardInterrupt()
            return self.adapter.predict(case)

    first = sample.as_dict()
    second = {**first, "id": "tr_synthetic_2"}
    path = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        run([first, second], Interrupted(), path, {})
    client = MockClient(False)
    run([first, second], GPT61SolAdapter(client, "p"), path, {})
    assert client.calls == 1 and len(load_jsonl(path / "predictions.jsonl")) == 6
