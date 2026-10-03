"""Responses API adapter; receives ModelCase only, with no tools or conversation history."""

import json
import time
from typing import Any

from benchmark.schema import ModelCase, labels, validate_answer

MODEL = "gpt-6.1-sol"
EFFORT = "max"
MAX_OUTPUT_TOKENS = 32768


def obj(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def answer_schema(question: dict) -> dict:
    number = {"type": "number", "minimum": 0, "maximum": 1}
    if question["type"] == "noul":
        return obj({"probability_true": number})
    ls = labels(question)
    properties: dict[str, Any] = {"probabilities": obj({k: number for k in ls})}
    if question["type"] == "choice":
        properties = {"selected": {"type": "string", "enum": ls}, **properties}
    return obj(properties)


def build_request(case: ModelCase, prompt: str) -> dict:
    schema = obj({"answers": obj({qid: answer_schema(q) for qid, q in case.questions.items()})})
    return {
        "model": MODEL,
        "reasoning": {"effort": EFFORT},
        "instructions": prompt,
        "input": [
            {
                "role": "user",
                "content": json.dumps(
                    case.payload(), ensure_ascii=False, separators=(",", ":"), allow_nan=False
                ),
            }
        ],
        "tools": [],
        "tool_choice": "none",
        "store": False,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "typed_decisions",
                "strict": True,
                "schema": schema,
            }
        },
    }


def usage_dict(usage: Any) -> dict:
    if usage is None:
        return {}
    return usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)


def estimated_cost(usage: dict) -> float | None:
    if not {"input_tokens", "output_tokens"} <= set(usage):
        return None
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    written = (usage.get("input_tokens_details") or {}).get("cache_write_tokens", 0)
    # Official GPT-6.1 Sol standard-tier USD / 1M: input 2, cached .10, output 10.
    # Reasoning tokens are included in output_tokens; never add them a second time.
    return (
        (usage["input_tokens"] - cached - written) * 2
        + cached * 0.1
        + written * 2.5
        + usage["output_tokens"] * 10
    ) / 1_000_000


class GPT61SolAdapter:
    def __init__(
        self, client: Any, prompt: str, max_attempts: int = 3, sleep: Any = time.sleep
    ) -> None:
        self.client, self.prompt, self.sleep = client, prompt, sleep
        if not 1 <= max_attempts <= 3:
            raise ValueError("max_attempts must be 1..3")
        self.max_attempts = max_attempts

    def predict(self, case: ModelCase) -> dict:
        request = build_request(case, self.prompt)
        attempts: list[dict[str, Any]] = []
        answers: dict[str, dict[str, Any]] = {}
        started = time.perf_counter()
        for attempt in range(self.max_attempts):
            t0 = time.perf_counter()
            try:
                response = self.client.responses.create(**request)
            except Exception as exc:
                # Do not serialize exception text: SDK errors may contain request bodies/secrets.
                status = getattr(exc, "status_code", None)
                retryable = status in {408, 409, 429, 500, 502, 503, 504} or type(exc).__name__ in {
                    "APIConnectionError",
                    "APITimeoutError",
                    "TimeoutError",
                    "ConnectionError",
                }
                attempts.append(
                    {
                        "attempt": attempt + 1,
                        "status": "api_error",
                        "error_type": type(exc).__name__,
                        "http_status": status,
                        "latency_ms": (time.perf_counter() - t0) * 1000,
                        "usage": {},
                        "estimated_cost_usd": None,
                    }
                )
                if retryable and attempt + 1 < self.max_attempts:
                    self.sleep(2**attempt)
                    continue
                break
            usage = usage_dict(getattr(response, "usage", None))
            meta = {
                "attempt": attempt + 1,
                "status": "completed",
                "response_id": getattr(response, "id", None),
                "response_model": getattr(response, "model", None),
                "response_status": getattr(response, "status", None),
                "latency_ms": (time.perf_counter() - t0) * 1000,
                "usage": usage,
                "estimated_cost_usd": estimated_cost(usage),
            }
            attempts.append(meta)
            try:
                if getattr(response, "status", None) != "completed":
                    raise ValueError("Incomplete/refused response")
                output = json.loads(response.output_text)
                if not isinstance(output, dict) or set(output) != {"answers"}:
                    raise ValueError("Unexpected response fields")
                if not isinstance(output["answers"], dict):
                    raise ValueError("Missing answers object")
                if set(output["answers"]) - set(case.questions):
                    raise ValueError("Invented question ID")
                for qid, question in case.questions.items():
                    try:
                        answers[qid] = {
                            "status": "ok",
                            "answer": validate_answer(question, output["answers"].get(qid)),
                        }
                    except (ValueError, TypeError, KeyError):
                        answers[qid] = {"status": "invalid_output", "error_type": "InvalidDecision"}
            except (ValueError, TypeError, KeyError, AttributeError):
                meta["status"] = "invalid_output"
            # Never retry invalid final decisions based on content or gold.
            break
        default_status = "api_error" if attempts[-1]["status"] == "api_error" else "invalid_output"
        for qid in case.questions:
            answers.setdefault(
                qid,
                {
                    "status": default_status,
                    "error_type": attempts[-1].get("error_type", "InvalidResponse"),
                },
            )
        return {
            "answers": answers,
            "attempts": attempts,
            "latency_ms": (time.perf_counter() - started) * 1000,
        }
