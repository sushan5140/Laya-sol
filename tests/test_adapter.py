import json
from types import SimpleNamespace

import pytest

from adapters.gpt61_sol import GPT61SolAdapter, build_request, estimated_cost


def response(text, status="completed"):
    return SimpleNamespace(
        status=status,
        output_text=text,
        id="response",
        model="gpt-6.1-sol",
        usage={"input_tokens": 100, "output_tokens": 50},
    )


class Client:
    def __init__(self, events):
        self.responses = self
        self.events = iter(events)
        self.requests = []

    def create(self, **request):
        self.requests.append(request)
        event = next(self.events)
        if isinstance(event, Exception):
            raise event
        return event


def test_strict_schema_preserves_options(sample):
    schema = build_request(sample, "prompt")["text"]["format"]["schema"]
    questions = schema["properties"]["answers"]["properties"]
    assert list(questions) == list(sample.questions)
    assert questions["route"]["properties"]["selected"]["enum"] == ["zeta", "alpha"]
    assert list(questions["level"]["properties"]["probabilities"]["properties"]) == ["0", "1", "2"]
    assert schema["additionalProperties"] is False


def test_retry_identical_request_and_usage(sample, final_answers):
    client = Client([TimeoutError("SECRET"), response(json.dumps({"answers": final_answers}))])
    sleeps = []
    out = GPT61SolAdapter(client, "prompt", sleep=sleeps.append).predict(sample)
    assert len(out["attempts"]) == 2 and sleeps == [1]
    assert client.requests[0] == client.requests[1]
    assert all(a["status"] == "ok" for a in out["answers"].values())
    assert out["latency_ms"] >= 0
    assert "SECRET" not in json.dumps(out)


def test_exhausted_failure_returns_every_question(sample):
    out = GPT61SolAdapter(Client([TimeoutError()] * 3), "prompt", sleep=lambda _: None).predict(
        sample
    )
    assert len(out["attempts"]) == 3
    assert set(out["answers"]) == set(sample.questions)
    assert all(a["status"] == "api_error" for a in out["answers"].values())


@pytest.mark.parametrize(
    "text,status",
    [("not json", "completed"), ("{}", "completed"), ('{"answers":{}}', "incomplete")],
)
def test_bad_outputs_count_all_no_retry(sample, text, status):
    client = Client([response(text, status)])
    out = GPT61SolAdapter(client, "prompt").predict(sample)
    assert len(client.requests) == 1
    assert all(a["status"] == "invalid_output" for a in out["answers"].values())
    assert out["attempts"][0]["usage"]["output_tokens"] == 50


def test_partial_invalid_keeps_valid_decisions(sample, final_answers):
    final_answers["yes"] = {"probability_true": 2}
    out = GPT61SolAdapter(Client([response(json.dumps({"answers": final_answers}))]), "p").predict(
        sample
    )
    assert out["answers"]["yes"]["status"] == "invalid_output"
    assert out["answers"]["level"]["status"] == "ok"


def test_no_hidden_reasoning_serialized(sample, final_answers):
    res = response(json.dumps({"answers": final_answers}))
    res.output = [{"type": "reasoning", "summary": "HIDDEN_REASONING_SENTINEL"}]
    out = GPT61SolAdapter(Client([res]), "prompt").predict(sample)
    assert "HIDDEN_REASONING_SENTINEL" not in json.dumps(out)


def test_cost_does_not_double_count_reasoning():
    assert estimated_cost(
        {
            "input_tokens": 100,
            "output_tokens": 50,
            "input_tokens_details": {"cached_tokens": 20},
            "output_tokens_details": {"reasoning_tokens": 40},
        }
    ) == pytest.approx(0.000662)
    assert estimated_cost({}) is None


def test_cache_write_pricing():
    assert estimated_cost(
        {
            "input_tokens": 100,
            "output_tokens": 50,
            "input_tokens_details": {"cached_tokens": 20, "cache_write_tokens": 10},
        }
    ) == pytest.approx(0.000667)
