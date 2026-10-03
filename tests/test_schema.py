import copy

import pytest

from benchmark.schema import ModelCase, decision_id, labels, validate_answer


def test_order_and_all_types(sample, final_answers):
    assert labels(sample.questions["route"]) == ["zeta", "alpha"]
    assert labels(sample.questions["level"]) == ["0", "1", "2"]
    for qid, q in sample.questions.items():
        assert validate_answer(q, final_answers[qid])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -0.1, 1.1, True, "0.5"])
def test_invalid_probability(sample, bad):
    with pytest.raises(ValueError):
        validate_answer(sample.questions["yes"], {"probability_true": bad})


@pytest.mark.parametrize(
    "probs", [{"zeta": 0.8}, {"zeta": 0.8, "other": 0.2}, {"zeta": 0.8, "alpha": 0.3}]
)
def test_distribution_rejects_wrong_keys_mass(sample, probs):
    with pytest.raises(ValueError):
        validate_answer(sample.questions["route"], {"selected": "zeta", "probabilities": probs})


def test_selected_must_be_supplied_label(sample):
    with pytest.raises(ValueError):
        validate_answer(
            sample.questions["route"],
            {"selected": "invented", "probabilities": {"zeta": 0.5, "alpha": 0.5}},
        )


def test_collision_free_ids():
    assert decision_id("a:b", "c") != decision_id("a", "b:c")


def test_mutation_checked_again(sample):
    case = copy.deepcopy(sample)
    case.questions["route"]["gold"] = "secret"
    with pytest.raises(ValueError):
        case.payload()


def test_raw_dataset_row_rejected(sample):
    row = sample.as_dict()
    row["gold"] = {"route": "sentinel"}
    with pytest.raises(ValueError):
        ModelCase.from_dict(row)
