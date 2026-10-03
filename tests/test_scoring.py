import json
from pathlib import Path

import numpy as np
import pytest

from benchmark.io import file_hash
from benchmark.schema import answer_vector, decision_id
from benchmark.score import ece_score, score


def fixture(sample, final_answers):
    gold = {
        "id": sample.id,
        "gold": {
            "route": {
                "type": "choice",
                "label": "zeta",
                "probabilities": {"zeta": 0.7, "alpha": 0.3},
            },
            "yes": {
                "type": "noul",
                "label": "true",
                "noul": 0.6,
                "probabilities": {"false": 0.4, "true": 0.6},
            },
            "level": {
                "type": "score",
                "label": "1",
                "score": 1.2,
                "probabilities": {"0": 0.1, "1": 0.6, "2": 0.3},
            },
        },
    }
    records = [
        {
            "decision_id": decision_id(sample.id, qid),
            "case_id": sample.id,
            "question_id": qid,
            "status": "ok",
            "answer": answer,
        }
        for qid, answer in final_answers.items()
    ]
    return [sample.as_dict()], [gold], records


def test_hand_calculated_metrics(sample, final_answers):
    got = score(*fixture(sample, final_answers))
    assert got["accuracy"] == pytest.approx(2 / 3)
    assert got["soft_accuracy"] == pytest.approx((0.62 + 0.5) / 2)
    assert got["brier_score"] == pytest.approx(0.02)
    assert got["score_mae"] == pytest.approx(0.3)
    assert got["within_1_level"] == 1
    assert got["metric_denominators"]["soft_brier_valid_choice_noul"] == 2


def test_actual_upstream_metric_cell(sample, final_answers):
    cases, gold, records = fixture(sample, final_answers)
    predictions = []
    pred = {}
    for qid, q in sample.questions.items():
        ps = answer_vector(q, final_answers[qid])
        if q["type"] == "choice":
            pred[qid] = {
                "choice": final_answers[qid]["selected"],
                "probabilities": final_answers[qid]["probabilities"],
            }
        elif q["type"] == "noul":
            pred[qid] = {"noul": final_answers[qid]["probability_true"]}
        else:
            pred[qid] = {
                "score": sum(i * p for i, p in enumerate(ps)),
                "probabilities": final_answers[qid]["probabilities"],
            }
    predictions.append({"pred": pred, "gold": gold[0]["gold"], "questions": sample.questions})
    root = Path(__file__).resolve().parents[1]
    hashes = json.loads((root / "benchmark/sources.json").read_text())["reference_fixture_hashes"]
    for filename, expected in hashes.items():
        assert file_hash(root / "tests/fixtures" / filename) == expected
    namespace = {"np": np, "predictions": predictions, "latencies_ms": [1.0]}
    exec((root / "tests/fixtures/upstream_ece.txt").read_text(), namespace)
    exec((root / "tests/fixtures/upstream_metric_cell14.txt").read_text(), namespace)
    ours = score(cases, gold, records)
    for metric, upstream in [
        ("accuracy", "laya_acc"),
        ("soft_accuracy", "laya_soft_acc"),
        ("brier_score", "laya_brier"),
        ("ece", "laya_ece"),
        ("score_mae", "laya_mae"),
        ("within_1_level", "laya_within1"),
    ]:
        assert ours[metric] == pytest.approx(namespace[upstream], abs=1e-12)


def test_ece_boundaries_match_actual_upstream():
    namespace = {"np": np}
    exec((Path(__file__).parent / "fixtures/upstream_ece.txt").read_text(), namespace)
    # Include every bin edge and endpoints; primary scorer must match NumPy boundaries.
    conf = np.linspace(0, 1, 16).tolist()
    correct = [float(i % 2) for i in range(16)]
    assert ece_score(conf, correct) == pytest.approx(
        namespace["ece_score"](np.array(conf), np.array(correct)), abs=1e-12
    )


def test_failed_and_missing_decisions_never_drop(sample, final_answers):
    cases, gold, records = fixture(sample, final_answers)
    records[0] = {**records[0], "status": "api_error"}
    got = score(cases, gold, records[:2])
    assert got["n_decisions"] == 3 and got["failures"] == 2
    assert got["accuracy"] == pytest.approx(1 / 3)
    assert got["soft_accuracy"] is None and got["ece"] is None
    assert got["conditional_valid_only"]["soft_accuracy"] == 0.5
    assert got["metric_denominators"]["accuracy"] == 3


def test_duplicates_unknown_and_mismapped_ids_refused(sample, final_answers):
    cases, gold, records = fixture(sample, final_answers)
    with pytest.raises(ValueError):
        score(cases, gold, records + records[:1])
    with pytest.raises(ValueError):
        score(cases, gold, [{**records[0], "decision_id": "unknown"}])
    with pytest.raises(ValueError):
        score(cases, gold, [{**records[0], "case_id": "wrong"}])
