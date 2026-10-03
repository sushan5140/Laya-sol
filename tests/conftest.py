import pytest

from benchmark.schema import ModelCase


@pytest.fixture
def sample():
    questions = {
        "route": {
            "type": "choice",
            "instructions": "Choose team",
            "criteria": {"zeta": "First team", "alpha": "Second team"},
        },
        "yes": {
            "type": "noul",
            "instructions": "The state is valid",
            "criteria": {"false": "No", "true": "Yes"},
        },
        "level": {
            "type": "score",
            "instructions": "Rate urgency",
            "criteria": ["Low", "Medium", "High"],
        },
    }
    case = {
        "id": "tr_synthetic_1",
        "workflow": "synthetic",
        "state": {"text": "Example"},
        "questions": questions,
    }
    return ModelCase.from_dict(case)


@pytest.fixture
def final_answers():
    return {
        "route": {"selected": "zeta", "probabilities": {"zeta": 0.8, "alpha": 0.2}},
        "yes": {"probability_true": 0.5},
        "level": {"probabilities": {"0": 0.1, "1": 0.3, "2": 0.6}},
    }
