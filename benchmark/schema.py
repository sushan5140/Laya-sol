"""Strict boundary between dataset records and model-facing cases."""

import json
import math
from dataclasses import dataclass
from typing import Any


def no_gold(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {"gold", "factors", "label_agreement"} or "__" in key:
                raise ValueError("Evaluator-only field in model-facing data")
            no_gold(item)
    elif isinstance(value, list):
        for item in value:
            no_gold(item)


def labels(question: dict) -> list[str]:
    if question["type"] == "noul":
        return ["false", "true"]
    criteria = question["criteria"]
    if question["type"] == "score":
        return [str(i) for i in range(len(criteria))]
    return list(criteria)


def validate_question(question: dict) -> None:
    if set(question) - {"type", "instructions", "criteria"}:
        raise ValueError("Unexpected question fields")
    if question.get("type") not in {"choice", "noul", "score"}:
        raise ValueError("Unsupported decision type")
    if not isinstance(question.get("instructions"), str) or not question["instructions"]:
        raise ValueError("Missing question instructions")
    criteria = question.get("criteria")
    if question["type"] == "noul":
        if criteria is not None and (
            not isinstance(criteria, dict) or set(criteria) != {"false", "true"}
        ):
            raise ValueError("Invalid binary criteria")
    else:
        if not isinstance(criteria, (list, dict)) or len(criteria) < 2:
            raise ValueError("Invalid criteria")
        if question["type"] == "score" and not isinstance(criteria, list):
            raise ValueError("Score rubric must be an ordered list")
        ls = labels(question)
        if any(not isinstance(k, str) or not k for k in ls) or len(set(ls)) != len(ls):
            raise ValueError("Option labels must be unique nonempty strings")
    if isinstance(criteria, dict) and any(not isinstance(v, str) for v in criteria.values()):
        raise ValueError("Criteria descriptions must be strings")
    if isinstance(criteria, list) and any(not isinstance(v, str) for v in criteria):
        raise ValueError("Criteria must be strings")


@dataclass(frozen=True)
class ModelCase:
    id: str
    workflow: str
    state: Any
    questions: dict

    @classmethod
    def from_dict(cls, row: dict) -> "ModelCase":
        if set(row) != {"id", "workflow", "state", "questions"}:
            raise ValueError("ModelCase accepts only id/workflow/state/questions")
        if not isinstance(row["id"], str) or not row["id"]:
            raise ValueError("Invalid original case ID")
        if not isinstance(row["workflow"], str):
            raise ValueError("Invalid workflow")
        if not isinstance(row["questions"], dict) or not row["questions"]:
            raise ValueError("Missing questions")
        no_gold(row)
        for qid, question in row["questions"].items():
            if not isinstance(qid, str) or not qid:
                raise ValueError("Invalid question ID")
            validate_question(question)
        return cls(**row)

    def payload(self) -> dict:
        # Validate again to reject mutation of the nested dictionaries after construction.
        ModelCase.from_dict(self.as_dict())
        return {"state": self.state, "questions": self.questions}

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow": self.workflow,
            "state": self.state,
            "questions": self.questions,
        }


def decision_id(case_id: str, question_id: str) -> str:
    # JSON tuple encoding is collision-free even when IDs contain delimiters.
    return json.dumps([case_id, question_id], ensure_ascii=False, separators=(",", ":"))


def probability(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Probability must be numeric")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Probability outside finite [0,1]")
    return float(value)


def distribution(values: Any, ls: list[str]) -> list[float]:
    if not isinstance(values, dict) or set(values) != set(ls):
        raise ValueError("Probability keys must match supplied options exactly")
    probs = [probability(values[k]) for k in ls]
    if not math.isclose(sum(probs), 1, rel_tol=0, abs_tol=1e-4):
        raise ValueError("Probability mass must sum to one within 1e-4")
    return [p / sum(probs) for p in probs]


def validate_answer(question: dict, answer: Any) -> dict:
    if not isinstance(answer, dict):
        raise ValueError("Answer must be an object")
    qt = question["type"]
    ls = labels(question)
    if qt == "noul":
        if set(answer) != {"probability_true"}:
            raise ValueError("Invalid noul output fields")
        pt = probability(answer["probability_true"])
        return {"probability_true": pt}
    expected = {"selected", "probabilities"} if qt == "choice" else {"probabilities"}
    if set(answer) != expected:
        raise ValueError("Invalid output fields")
    probs = distribution(answer["probabilities"], ls)
    out = {"probabilities": dict(zip(ls, probs))}
    if qt == "choice":
        if answer["selected"] not in ls:
            raise ValueError("Selected label must be a supplied option")
        out["selected"] = answer["selected"]
    return out


def answer_vector(question: dict, answer: dict) -> list[float]:
    out = validate_answer(question, answer)
    if question["type"] == "noul":
        return [1 - out["probability_true"], out["probability_true"]]
    return [out["probabilities"][k] for k in labels(question)]


def prediction_index(question: dict, probs: list[float]) -> int:
    # The notebook uses >= .5 for noul (true wins ties), first argmax for score/choice.
    return int(probs[1] >= 0.5) if question["type"] == "noul" else probs.index(max(probs))


def answer_index(question: dict, answer: dict, probs: list[float]) -> int:
    # The fine-tuning notebook scores the explicit choice label, not reconstructed argmax.
    if question["type"] == "choice":
        return labels(question).index(answer["selected"])
    return prediction_index(question, probs)
