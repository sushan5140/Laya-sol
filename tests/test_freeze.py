import json
import shutil

import pytest

from benchmark.io import load_jsonl
from benchmark.validate import validate_frozen
from scripts.export_development import ROOT, select_development
from scripts.run_benchmark import official_gate


def test_exact_frozen_counts():
    validate_frozen(ROOT / "benchmark/frozen")
    test = load_jsonl(ROOT / "benchmark/frozen/test_inputs.jsonl")
    train = load_jsonl(ROOT / "benchmark/frozen/train_inputs.jsonl")
    assert len(test) == 400 and sum(len(c["questions"]) for c in test) == 2000
    assert len(train) == 1200
    assert not {c["id"] for c in test} & {c["id"] for c in train}
    assert all(c["id"].startswith("tr_") for c in select_development(train))


def test_tamper_refused(tmp_path):
    shutil.copytree(ROOT / "benchmark/frozen", tmp_path / "frozen")
    path = tmp_path / "frozen/test_inputs.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="hash"):
        validate_frozen(tmp_path / "frozen")


def test_published_reproduction_gate_currently_blocks():
    status = json.loads((ROOT / "reports/reference_validation.json").read_text())
    assert status["status"] == "not_reproduced"
    with pytest.raises(ValueError, match="reference scoring"):
        official_gate(ROOT / "benchmark/frozen", (ROOT / "prompts/v1.txt").read_bytes().decode())


def test_export_matches_source_exactly():
    selected = select_development(load_jsonl(ROOT / "benchmark/frozen/train_inputs.jsonl"))
    exported = json.loads(
        (ROOT / "artifacts/dry_run_20_model_inputs.json").read_text(encoding="utf-8")
    )
    assert exported == [{"state": c["state"], "questions": c["questions"]} for c in selected]
