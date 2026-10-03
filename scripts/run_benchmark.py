"""Tool-free inference with atomic case checkpoints and frozen configuration."""

import argparse
import importlib.metadata
import json
import os
import platform
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from adapters.gpt61_sol import EFFORT, MODEL, GPT61SolAdapter, build_request
from benchmark.io import digest, dump_json, encode, file_hash, load_jsonl
from benchmark.schema import ModelCase, decision_id
from benchmark.score import METRIC_VERSION
from benchmark.validate import validate_frozen
from scripts.export_development import select_development

ROOT = Path(__file__).resolve().parents[1]


def implementation_hash() -> str:
    files = sorted(
        p
        for directory in ("adapters", "benchmark", "scripts")
        for p in (ROOT / directory).glob("*.py")
    )
    return digest(b"".join(encode([str(p.relative_to(ROOT)), file_hash(p)]) for p in files))


def configuration(cases: list[dict], prompt: str, mode: str) -> dict:
    exemplar = build_request(ModelCase.from_dict(cases[0]), prompt)
    return {
        "mode": mode,
        "model": MODEL,
        "reasoning_effort": EFFORT,
        "metric_version": METRIC_VERSION,
        "prompt_sha256": digest(prompt.encode("utf-8")),
        "inputs_sha256": digest(b"".join(encode(c) for c in cases)),
        "implementation_sha256": implementation_hash(),
        "python": platform.python_version(),
        "sdk": importlib.metadata.version("openai"),
        "api_parameters": {
            k: v for k, v in exemplar.items() if k not in {"input", "instructions", "text"}
        },
        "output_schema": "per-case strict JSON schema from supplied question IDs/options",
        "max_attempts": 3,
        "request_structure": "all five questions in one case call",
        "pricing": {
            "currency": "USD",
            "input_per_1m": 2,
            "cached_input_per_1m": 0.1,
            "cache_write_per_1m": 2.5,
            "output_per_1m": 10,
            "source": "https://developers.openai.com/api/docs/models/gpt-6.1-sol",
            "verified_date": "2026-10-04",
            "estimate_only": True,
        },
    }


def run(cases: list[dict], adapter: Any, directory: Path, config: dict) -> dict:
    if not cases:
        raise ValueError("Empty run")
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / "writer.lock"
    # A second writer is refused. A stale lock after a crash must be reviewed/removed manually.
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        meta_path = directory / "run.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta["configuration"] != config:
                raise ValueError("Resume configuration differs from frozen run")
        else:
            meta = {"created_at": datetime.now(UTC).isoformat(), "configuration": config}
            dump_json(meta_path, meta)
        conn = sqlite3.connect(directory / "checkpoint.db")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, result TEXT NOT NULL)"
            )
            allowed = {c["id"] for c in cases}
            completed = {r[0] for r in conn.execute("SELECT id FROM cases")}
            if not completed <= allowed:
                raise ValueError("Checkpoint contains unknown cases")
            for case in cases:
                if case["id"] in completed:
                    continue
                prediction = adapter.predict(ModelCase.from_dict(case))
                if set(prediction["answers"]) != set(case["questions"]):
                    raise ValueError("Adapter must return one status for every question")
                result = {
                    "case_id": case["id"],
                    "completed_at": datetime.now(UTC).isoformat(),
                    "prediction": prediction,
                }
                with conn:
                    conn.execute(
                        "INSERT INTO cases VALUES (?,?)",
                        (case["id"], encode(result).decode("utf-8")),
                    )
            results = {
                row[0]: json.loads(row[1]) for row in conn.execute("SELECT id,result FROM cases")
            }
        finally:
            conn.close()
        records, attempts = [], []
        for case in cases:
            result = results[case["id"]]
            prediction = result["prediction"]
            attempts.extend(prediction["attempts"])
            for qid in case["questions"]:
                records.append(
                    {
                        "decision_id": decision_id(case["id"], qid),
                        "case_id": case["id"],
                        "question_id": qid,
                        **prediction["answers"][qid],
                    }
                )
        (directory / "predictions.jsonl").write_bytes(b"".join(encode(r) for r in records))
        dump_json(directory / "calls.json", [results[c["id"]] for c in cases])
        summary = {
            "cases": len(cases),
            "decisions": len(records),
            "attempts": len(attempts),
            "failed_decisions": sum(r["status"] != "ok" for r in records),
            "input_tokens": sum(a["usage"].get("input_tokens", 0) for a in attempts),
            "output_tokens": sum(a["usage"].get("output_tokens", 0) for a in attempts),
            "usage_unknown_attempts": sum(not a["usage"] for a in attempts),
            "known_usage_estimated_cost_usd": sum(a["estimated_cost_usd"] or 0 for a in attempts),
            "latency_ms_total": sum(results[c["id"]]["prediction"]["latency_ms"] for c in cases),
        }
        dump_json(directory / "summary.json", summary)
        return summary
    finally:
        lock.unlink()


def official_gate(frozen: Path, prompt: str) -> None:
    manifest = validate_frozen(frozen)
    if (
        file_hash(ROOT / "prompts/v1.txt")
        != json.loads((ROOT / "benchmark/prompt_lock.json").read_text())["prompt_sha256"]
    ):
        raise ValueError("Frozen v1 prompt changed")
    proof = json.loads((ROOT / "reports/reference_validation.json").read_text(encoding="utf-8"))
    if (
        proof.get("status") != "reproduced"
        or not proof.get("archive_sha256")
        or proof.get("test_inputs_sha256") != manifest["frozen_sha256"]["test_inputs.jsonl"]
        or proof.get("test_gold_sha256") != manifest["frozen_sha256"]["test_gold.jsonl"]
        or proof.get("scorer_sha256") != file_hash(ROOT / "benchmark/score.py")
        or proof.get("metric_version") != METRIC_VERSION
    ):
        raise ValueError(
            "Official run blocked: published reference scoring has not been reproduced"
        )
    if digest(prompt.encode()) != file_hash(ROOT / "prompts/v1.txt"):
        raise ValueError("Prompt bytes differ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--development", type=int, choices=[5, 20])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.official == (args.development is not None):
        parser.error("Choose exactly one of --official or --development 5/20")
    frozen = ROOT / "benchmark/frozen"
    prompt = (ROOT / "prompts/v1.txt").read_bytes().decode("utf-8")
    manifest = validate_frozen(frozen)
    if args.official:
        official_gate(frozen, prompt)
        cases = load_jsonl(frozen / "test_inputs.jsonl")
    else:
        cases = select_development(load_jsonl(frozen / "train_inputs.jsonl"))[: args.development]
    config = configuration(cases, prompt, "official" if args.official else "development")
    config["benchmark_manifest"] = manifest
    from openai import OpenAI

    # Disable implicit SDK retries and alternate endpoints. No tool environments or agents.
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url="https://api.openai.com/v1",
        max_retries=0,
        timeout=300,
    )
    print(json.dumps(run(cases, GPT61SolAdapter(client, prompt), args.output, config), indent=2))


if __name__ == "__main__":
    main()
