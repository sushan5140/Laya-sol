import copy
import json

import pytest

from adapters.gpt61_sol import build_request
from benchmark.schema import ModelCase
from scripts.export_development import ROOT


def test_request_allowlist(sample):
    request = build_request(sample, (ROOT / "prompts/v1.txt").read_text())
    assert request["model"] == "gpt-6.1-sol"
    assert request["reasoning"] == {"effort": "max"}
    assert request["tools"] == [] and request["tool_choice"] == "none"
    assert request["store"] is False
    assert set(json.loads(request["input"][0]["content"])) == {"state", "questions"}
    assert not {"previous_response_id", "conversation", "include"} & set(request)


@pytest.mark.parametrize("where", ["top", "state", "question"])
def test_gold_sentinels_never_reach_request(sample, where):
    row = copy.deepcopy(sample.as_dict())
    target = (
        row if where == "top" else row["state"] if where == "state" else row["questions"]["route"]
    )
    target["gold"] = "GOLD_SECRET_SENTINEL"
    with pytest.raises(ValueError):
        build_request(ModelCase.from_dict(row), "frozen prompt")


def test_manual_export_only_visible_fields():
    path = ROOT / "artifacts/dry_run_20_model_inputs.json"
    exported = json.loads(path.read_text(encoding="utf-8"))
    assert len(exported) == 20
    assert all(set(row) == {"state", "questions"} for row in exported)
    assert sum(len(row["questions"]) for row in exported) == 100
    for row in exported:
        ModelCase.from_dict({"id": "development", "workflow": "development", **row})
    assert (ROOT / "prompts/manual_chat_v1.txt").read_bytes() == (
        ROOT / "prompts/v1.txt"
    ).read_bytes()
