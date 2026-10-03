"""Frozen metrics from upstream fine-tuning notebook cell 14, evaluated offline."""

from typing import Any

from benchmark.schema import answer_index, answer_vector, decision_id, labels

METRIC_VERSION = "laya-kaggle-cell14-v1"


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def ece_score(conf: list[float], correct: list[float], bins: int = 15) -> float:
    if len(conf) != len(correct) or not conf:
        raise ValueError("ECE requires matching nonempty vectors")
    result = 0.0
    for i in range(bins):
        # Match np.linspace(0, 1, bins + 1) bit-for-bit, including floating bin edges.
        step = 1.0 / bins
        lo, hi = i * step, (i + 1) * step if i < bins - 1 else 1.0
        selected = [j for j, c in enumerate(conf) if (c >= lo if i == 0 else c > lo) and c <= hi]
        if selected:
            gap = abs(
                sum(conf[j] for j in selected) / len(selected)
                - sum(correct[j] for j in selected) / len(selected)
            )
            result += len(selected) / len(conf) * gap
    return result


def gold_vector(question: dict, gold: dict) -> list[float]:
    if question["type"] == "noul":
        pt = float(gold.get("noul", gold.get("probabilities", {}).get("true", 0.5)))
        return [1 - pt, pt]
    default = 1e-6 if question["type"] == "choice" else 0.0
    ps = [float(gold["probabilities"].get(k, default)) for k in labels(question)]
    return [p / sum(ps) for p in ps]


def score(cases: list[dict], gold_rows: list[dict], records: list[dict]) -> dict[str, Any]:
    gold_by_id = {g["id"]: g["gold"] for g in gold_rows}
    if len(gold_by_id) != len(gold_rows) or set(gold_by_id) != {c["id"] for c in cases}:
        raise ValueError("Gold/case IDs do not match uniquely")
    expected = {decision_id(c["id"], qid) for c in cases for qid in c["questions"]}
    pred_by_id = {}
    for prediction in records:
        did = prediction["decision_id"]
        if did not in expected or did in pred_by_id:
            raise ValueError("Unknown or duplicate decision ID")
        if did != decision_id(prediction["case_id"], prediction["question_id"]):
            raise ValueError("Decision ID mapping mismatch")
        pred_by_id[did] = prediction
    correct, conf, soft, brier, mae, within = [], [], [], [], [], []
    failures = 0
    per_type: dict[str, list[float]] = {}
    per_workflow: dict[str, list[float]] = {}
    for case in cases:
        for qid, question in case["questions"].items():
            gold = gold_by_id[case["id"]][qid]
            qt = question["type"]
            ls = labels(question)
            gi = ls.index(str(gold["label"]).lower() if qt == "noul" else str(gold["label"]))
            record = pred_by_id.get(decision_id(case["id"], qid))
            ps = None
            if record and record.get("status") == "ok":
                try:
                    ps = answer_vector(question, record["answer"])
                except (ValueError, KeyError, TypeError):
                    pass
            hit = float(
                ps is not None
                and record is not None
                and answer_index(question, record["answer"], ps) == gi
            )
            correct.append(hit)
            per_type.setdefault(qt, []).append(hit)
            per_workflow.setdefault(case["workflow"], []).append(hit)
            if ps is None:
                failures += 1
                continue
            conf.append(max(ps))
            if qt != "score":
                gs = gold_vector(question, gold)
                soft.append(sum(p * g for p, g in zip(ps, gs)))
                brier.append(sum((p - g) ** 2 for p, g in zip(ps, gs)))
            else:
                expected_score = sum(i * p for i, p in enumerate(ps))
                err = abs(expected_score - float(gold.get("score", 0.0)))
                mae.append(err)
                within.append(float(err <= 1.0))
    valid_correct = []
    # ECE is undefined without a probability output; publish conditional metrics only
    # with explicit denominators, and suppress primary probabilistic metrics on failures.
    for case in cases:
        for qid, question in case["questions"].items():
            record = pred_by_id.get(decision_id(case["id"], qid))
            if record and record.get("status") == "ok":
                try:
                    ps = answer_vector(question, record["answer"])
                    gold = gold_by_id[case["id"]][qid]
                    label = str(gold["label"])
                    gi = labels(question).index(
                        label.lower() if question["type"] == "noul" else label
                    )
                    valid_correct.append(float(answer_index(question, record["answer"], ps) == gi))
                except (ValueError, KeyError, TypeError):
                    pass
    conditional = {
        "soft_accuracy": mean(soft),
        "brier_score": mean(brier),
        "ece": ece_score(conf, valid_correct) if conf else None,
        "score_mae": mean(mae),
        "within_1_level": mean(within),
    }
    return {
        "metric_version": METRIC_VERSION,
        "n_cases": len(cases),
        "n_decisions": len(correct),
        "failures": failures,
        "accuracy": mean(correct),
        "coverage": (len(correct) - failures) / len(correct),
        **{k: v if not failures else None for k, v in conditional.items()},
        "conditional_valid_only": conditional,
        "metric_denominators": {
            "accuracy": len(correct),
            "ece_valid": len(conf),
            "soft_brier_valid_choice_noul": len(soft),
            "score_metrics_valid": len(mae),
        },
        "by_type": {k: {"n": len(v), "accuracy": mean(v)} for k, v in per_type.items()},
        "by_workflow": {k: {"n": len(v), "accuracy": mean(v)} for k, v in per_workflow.items()},
    }
