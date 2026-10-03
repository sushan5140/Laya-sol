# Laya-Sol

Goal: Independent GPT-6.1 Sol evaluation on Laya's typed-decisions benchmark.

Reference targets:
- Jev: **0.727**
- Fine-tuned Laya: **0.766**

**These are published REFERENCE TARGETS, not measured GPT-6.1 Sol results. No model has been run by this project.** Phase 1 implements and validates the evaluator. The official evaluation is blocked pending reproduction of an archived reference run; the inspected sources contain no per-decision archive for the published 0.766 result. See [readiness](reports/phase1_readiness.md) and [methodology](reports/methodology.md).

## Manual development export

The requested [20-case input file](artifacts/dry_run_20_model_inputs.json) contains only `state` and `questions`, drawn from **train**, five cases per workflow. It has no IDs, workflow metadata, factors, agreement data, gold, reference predictions, or evaluator scores. [Manual instructions](prompts/manual_chat_v1.txt) are byte-for-byte identical to the frozen [v1 prompt](prompts/v1.txt).

For a future manual dry run, paste the instructions and then the JSON into a fresh GPT-6.1 Sol chat with tools disabled. Preserve input order. This export does not run a model. Manual chat results are development diagnostics; they do not establish the primary Responses API configuration, latency, usage, or cost. The user requested that no model be run yet.

## Reproduce preparation and validation

From the repository root, Python 3.12:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe -m benchmark.prepare
.venv/Scripts/python.exe -m benchmark.validate
.venv/Scripts/python.exe -m scripts.export_development
New-Item -ItemType Directory -Path work -Force
.venv/Scripts/python.exe -m pytest -q --basetemp=work/pytest-temp
.venv/Scripts/python.exe -m ruff check benchmark adapters scripts tests
.venv/Scripts/python.exe -m mypy benchmark adapters scripts
.venv/Scripts/python.exe -m compileall -q benchmark adapters scripts tests
```

Preparation downloads two Parquet assets from the pinned dataset revision and verifies committed hashes before writing. It can instead read a pinned local dataset checkout with `--source PATH`. Linux/macOS use `.venv/bin/python` and `mkdir -p work`. Frozen gold and inputs remain separate, local, and gitignored. Training and inference are never performed by preparation.

Offline dry runs, with synthetic responses and no API calls:

```powershell
.venv/Scripts/python.exe -m scripts.dry_run --cases 5 --output results/offline-5
.venv/Scripts/python.exe -m scripts.dry_run --cases 20 --output results/offline-20
```

They validate parsing, retries, all primitives, metadata, scoring, and resumability. Their scores, tokens, costs, and latency are **mock diagnostics**, not GPT-6.1 Sol measurements.

## Future evaluation commands

An authentic archived notebook prediction array can be checked offline with:

```powershell
.venv/Scripts/python.exe -m scripts.verify_reference --archive PATH_TO_AUTHENTIC_LAYA_ARCHIVE.json
```

It must cover all 400 IDs and 2,000 questions and reproduce the published metric targets. A mismatch keeps the official gate closed. Obtain archive provenance independently; satisfying numerical targets alone does not authenticate a file.

After the user authorizes live inference, securely configure `OPENAI_API_KEY` in the process environment; do not paste credentials into chat or commit them. Future development commands:

```powershell
.venv/Scripts/python.exe -m scripts.run_benchmark --development 5 --output results/live-dev-5
.venv/Scripts/python.exe -m scripts.make_report --development 5 --run results/live-dev-5
.venv/Scripts/python.exe -m scripts.run_benchmark --development 20 --output results/live-dev-20
.venv/Scripts/python.exe -m scripts.make_report --development 20 --run results/live-dev-20
```

Only after reference reproduction, live development validation and a separate Phase 2 instruction:

```powershell
.venv/Scripts/python.exe -m scripts.run_benchmark --official --output results/gpt61-sol-v1
.venv/Scripts/python.exe -m scripts.make_report --run results/gpt61-sol-v1
```

The official command currently fails before an API client is created. The configuration is `gpt-6.1-sol`, `reasoning.effort=max`, one request per case with all five questions, strict structured output, no tools, no conversation history, and no server-side response storage. Run commands with the same output directory to resume; failed decisions remain final records. Prompts and API configuration cannot change on resume.

## Project files

- `benchmark/`: pinned source/hash locks, preparation, schema, validation and offline metrics.
- `adapters/`: Responses API request construction and output validation.
- `prompts/`: one frozen zero-shot prompt and identical manual copy.
- `scripts/`: development export, mock validation, reference verification, inference and reporting.
- `tests/`: schema, leakage, metrics, integrity, API-error and resume tests; exact attributed upstream metric snippets.
- `artifacts/`: the 20 model-visible development cases.
- `reports/`: provenance, methodology, readiness and explicitly labelled offline diagnostics.
- `results/`: ignored local predictions, SQLite checkpoints and call metadata; no hidden reasoning.

The benchmark is public, synthetic, and teacher-labelled. Performance would measure agreement with that teacher on this frozen benchmark. It would not, by itself, establish generalization or superiority to a model trained on the benchmark's training split.
