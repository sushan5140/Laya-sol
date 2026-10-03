import copy
import json
from pathlib import Path

import numpy as np
import pytest

from benchmark.io import load_jsonl
from benchmark.score import score
from scripts.import_manual_dev20 import (
    LABEL,
    METRICS,
    PREDICTIONS,
    ROOT,
    map_outputs,
    save_once,
    unique_object,
    verify_context,
)


def manual_fixture():
    cases, _, _ = verify_context()
    raw = (ROOT / PREDICTIONS).read_bytes()
    return cases, raw, json.loads(raw, object_pairs_hook=unique_object)


def test_manual_mapping_preserves_answers_and_invalid_decisions():
    cases, _, outputs = manual_fixture()
    before = copy.deepcopy(outputs)
    records, validation = map_outputs(outputs, cases)
    assert outputs == before
    assert len(records) == 100 and validation["invalid_output_count"] == 0
    assert all(
        record["answer"] == outputs[i // 5]["answers"][record["question_id"]]
        for i, record in enumerate(records)
    )
    bad = copy.deepcopy(outputs)
    bad[0]["answers"]["needs_review"]["probability_true"] = 2.0
    bad_before = copy.deepcopy(bad)
    bad_records, invalid = map_outputs(bad, cases)
    assert bad == bad_before and len(bad_records) == 100
    assert invalid["invalid_output_count"] == 1
    assert sum(record["status"] == "invalid_output" for record in bad_records) == 1


def test_missing_cases_and_question_ids_refused():
    cases, _, outputs = manual_fixture()
    with pytest.raises(ValueError, match="20 case"):
        map_outputs(outputs[:-1], cases)
    outputs[0]["answers"].pop("needs_review")
    with pytest.raises(ValueError, match="question IDs"):
        map_outputs(outputs, cases)


def test_raw_bytes_roundtrip_and_overwrite_protection(tmp_path):
    raw = b'[{"answers":{}}]\r\n'
    path = tmp_path / "untouched.json"
    save_once(path, raw)
    save_once(path, raw)
    assert path.read_bytes() == raw
    with pytest.raises(ValueError, match="overwrite"):
        save_once(path, raw + b" ")


def test_duplicate_json_keys_refused():
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        json.loads('{"answers":{},"answers":{}}', object_pairs_hook=unique_object)


def test_actual_manual_metrics_match_original_notebook():
    cases, raw, outputs = manual_fixture()
    records, _ = map_outputs(outputs, cases)
    ids = {case["id"] for case in cases}
    gold = [
        row for row in load_jsonl(ROOT / "benchmark/frozen/train_gold.jsonl") if row["id"] in ids
    ]
    by_id = {row["id"]: row["gold"] for row in gold}
    predictions = []
    for case, output in zip(cases, outputs):
        pred = {}
        for qid, question in case["questions"].items():
            answer = output["answers"][qid]
            if question["type"] == "choice":
                pred[qid] = {"choice": answer["selected"], "probabilities": answer["probabilities"]}
            elif question["type"] == "noul":
                pred[qid] = {"noul": answer["probability_true"]}
            else:
                pred[qid] = {
                    "probabilities": answer["probabilities"],
                    "score": sum(int(k) * v for k, v in answer["probabilities"].items()),
                }
        predictions.append(
            {"pred": pred, "gold": by_id[case["id"]], "questions": case["questions"]}
        )
    namespace = {"np": np, "predictions": predictions, "latencies_ms": [0.0] * 20}
    fixtures = Path(__file__).parent / "fixtures"
    exec((fixtures / "upstream_ece.txt").read_text(encoding="utf-8"), namespace)
    exec((fixtures / "upstream_metric_cell14.txt").read_text(encoding="utf-8"), namespace)
    ours = score(cases, gold, records)
    for metric, reference in [
        ("accuracy", "laya_acc"),
        ("soft_accuracy", "laya_soft_acc"),
        ("brier_score", "laya_brier"),
        ("ece", "laya_ece"),
        ("score_mae", "laya_mae"),
        ("within_1_level", "laya_within1"),
    ]:
        assert ours[metric] == pytest.approx(namespace[reference], abs=1e-12)
    saved = json.loads((ROOT / METRICS).read_text(encoding="utf-8"))
    assert saved["metrics"] == ours
    assert saved["hard_accuracy_numerator"] == 64
    assert saved["label"] == LABEL and saved["official_benchmark"] is False
    assert (ROOT / PREDICTIONS).read_bytes() == raw
