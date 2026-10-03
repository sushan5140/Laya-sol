# Phase 1 readiness — official inference blocked

Prepared 2026-10-04, Asia/Calcutta. **No model has been run. No GPT-6.1 Sol score exists.** User steering requested export only and explicitly instructed not to run the model yet. Phase 1 implementation and offline validation are complete; live dry runs and published-result reproduction remain unresolved.

## 1. Upstream commits

- Laya: `2e4d9c87e8b1621deb344eac7de5c7258f32f849`
- Laya vs Jev: `28541781c863fcdf20348e5bb3a2073d672fffe6`
- Hugging Face dataset: `d0e2f0c42fef86cc15d1688d25a19f5ba7c85b18`
- Published Laya checkpoint inventory inspected: `e929ae5cf69bc34259cd2f95c9e91145b818b1f0`

Full source file hashes and the MLX port's historical upstream pin are in `benchmark/sources.json`. Neither upstream repository was changed.

## 2. Exact dataset / test split

`LocalLLaMA/typed-decisions`, configuration `all`, entire official `test` split, source asset `all/test-00000-of-00001.parquet` at the pinned revision. Train uses `all/train-00000-of-00001.parquet`; no resplitting or test sampling. Preparation decodes original state/question JSON as the upstream notebook does and preserves original content and order. The public dataset card describes separate generation seeds but provides no generation script or exact numeric seeds in this checkout.

## 3. Counts

| Split | Cases | Decisions |
|---|---:|---:|
| Official test | 400 | 2,000 |
| Official train | 1,200 | 6,000 |
| Manual development export | 20 train cases | 100 |

Test workflows each have 100 cases: agent_trace_observability, customer_service, invoice_processing, security_incidents. Question types: choice 600, noul 600, score 800. Verified disjoint train/test IDs and state hashes. Analytic uniform-random expected hard accuracy from option counts is **0.3175**, rounding to the requested reference .318; this is not the deterministic uniform argmax baseline.

## 4. Frozen benchmark and preparation hashes

- Test Parquet SHA-256: `4f294f218ea1da27f3efef936359389c62ea4d3973a41457732990f1d31b647c`
- Train Parquet SHA-256: `46a58d63edfd86e23229c78afe8b72307bb4ca9fb0e8df180cabb3c67ec9dcd5`
- Test model-input set SHA-256: `9c2eedb26113a216a04ebe1344ec9f94eed78da5d518581bc75c319424e04cf5`
- Test evaluator gold SHA-256: `e63122899dfa5b93c4663a4cf074e387b4237ec3f71361217ec07e7cd23c0751`
- Preparation script SHA-256: `df29db17fcd2d730c1e317e859623db583d0f77dba9a769740d322a05b7b7d20`

Individual train file hashes also appear in `benchmark/lock.json`. Frozen data are local and gitignored; downloading the pinned assets reproduces them. Altered schema/counts/bytes are refused. No lock-update shortcut exists.

## 5. Frozen prompt hash

`prompts/v1.txt` SHA-256: `8c774dda575f8e555f32902a9d3d3db7480f6093f7be144de60dd4070e1333ff`.
`prompts/manual_chat_v1.txt` has identical bytes and hash. The prompt contains no test examples, gold, reference predictions or test-derived corrections. Git attributes enforce LF so hashes survive Windows checkouts.

## 6. Evaluator validation

42 tests pass; Ruff, mypy and compileall pass. Tests cover payload gold exclusion, all primitives, order/IDs, probability/schema failures, explicit choice-label and noul tie semantics, exact upstream metric parity on independent fixtures, ECE boundary parity, denominator preservation, integrity rejection, retries, partial invalid outputs, hidden-reasoning exclusion, cost/cache accounting, resume configuration locks, concurrent writers, and interrupted case checkpoints. Exact check commands and results are in `reports/validation.json`.

**Published Laya .766 / Jev .727 reproduction has NOT succeeded.** No per-decision official prediction archive was found in the inspected sources. Laya README explicitly notes the fine-tuned result has no committed result file; published checkpoint inventory has no report. Base-model aggregate results and MLX 63-question parity records cannot supply missing official predictions. Fixture parity is verified and does not imply reproduction of a published score. The official run is gated before API client creation.

## 7. Reference metrics (not our results)

| Reference | Accuracy | Soft accuracy | Brier | ECE | Score MAE |
|---|---:|---:|---:|---:|---:|
| Random expected | .318 (exact .3175) | — | — | — | — |
| Jev 1.13.0, published | .727 | .580 | .148 | .144 | .391 |
| Teacher self-agreement, published | .735 | — | — | — | — |
| Fine-tuned Laya, published | .766 | .471 | .062 | .213 | .242 |

Jev rows are copied references in Laya's scripts; dataset authors state they measured Jev directly with zero errors. Laya's published .766 is self-reported. The notebook's computed Laya row would be direct for a new training run, which was not performed. There is no measured GPT-6.1 Sol row.

## 8. GPT-6.1 Sol configuration

Requested primary configuration: model `gpt-6.1-sol`, reasoning effort `max`, Responses API at api.openai.com/v1, strict per-case JSON schema, no tools/retrieval/conversation history, `store=false`, max_output_tokens 32768, SDK retries disabled, adapter maximum three identical transport attempts. One state with all five questions per request. SDK installed: openai 3.24.0; Python 3.12.10. Environment dependencies are frozen in `requirements-lock.txt`. No API key is committed; live model access has not been tested. All configured parameters, hashes and versions are recorded again when a run starts.

## 9. Dry-run status and requested manual files

| Offline mock validation | Decisions | Attempts (one injected timeout) | Final invalid outputs | New calls on resume |
|---|---:|---:|---:|---:|
| 5 train cases | 25 | 6 | 0 | 0 |
| 20 train cases | 100 | 21 | 0 | 0 |

These validate mechanics only. Mock metrics and token accounting are synthetic diagnostics; mock latency is local execution time. **Live 5-/20-case dry runs: not performed, per user instruction. Actual API latency/cost/output validity remain unmeasured.**

Requested export: `artifacts/dry_run_20_model_inputs.json`. It contains only state and questions, five training cases from each workflow. SHA-256: `ac7d4614edd60b518e455af2e5f622a0a96a76e582edbec39e15742ef5ca628b`. No IDs, gold, reference predictions, evaluator scores, factors or label-agreement information appear in it. `prompts/manual_chat_v1.txt` contains the exact frozen instructions. `reports/development_export.json` holds separate source IDs and hash provenance for offline mapping. Manual chat is development diagnostics, not the primary Responses API evaluation.

## 10. API call structure and cost estimate

400 primary case calls / 2,000 scored decisions; up to 1,200 transport attempts. Live dev stages would add 5 and 20 primary calls. Retries repeat identical input and never consult gold. Standard rates verified in official model documentation: $2/M uncached input, $.10/M cached input, $2.50/M cache writes, $10/M output. Max output budget for 400 successful calls is 13,107,200 tokens, $131.072 output ceiling plus input; it is not an expected cost. Record actual usage before estimating typical cost; failed calls with unknown usage are explicitly unknown. No API spending has occurred.

## 11. Known methodological limitations and remaining work

- Public synthetic teacher-labelled benchmark: contamination cannot be excluded; labels measure teacher agreement, not guaranteed truth. Generalization is not established.
- Laya was fitted on train; the proposed GPT-6.1 Sol run is zero-shot. Report this distinction instead of treating fitted/general scores as interchangeable quality rankings.
- Notebook soft accuracy/Brier exclude score questions; later upstream sweeps include them and also report a distinct hard-label Brier. v1 follows the notebook and documents denominators.
- Upstream failure handling either assumes valid output or drops missing logits. Here failures remain incorrect in accuracy; primary probability/score metrics are null on failures, with explicitly conditional diagnostics.
- No authentic per-decision published Laya/Jev archive is available in the inspected sources. Obtain and verify one before opening the official gate; diagnose mismatches without inference.
- Live API validation remains pending and the user currently forbids running a model. Manual chats do not prove API configuration or accounting.
- An interruption between API response/billing and durable SQLite commit can repeat an in-flight request; completed checkpoints never duplicate decisions.

Details and exact metric formulas: `reports/methodology.md`.

## 12. Exact Phase 2 commands (currently blocked)

From the repository root, **only after reference reproduction, live development validation and new Phase 2 authorization**:

```powershell
.venv/Scripts/python.exe -m scripts.run_benchmark --official --output results/gpt61-sol-v1
.venv/Scripts/python.exe -m scripts.make_report --run results/gpt61-sol-v1
```

The first command currently refuses to run because `reports/reference_validation.json` is `not_reproduced`. To verify a future authentic archive offline:

```powershell
.venv/Scripts/python.exe -m scripts.verify_reference --archive PATH_TO_AUTHENTIC_LAYA_ARCHIVE.json
```

Do not manually relabel a proof file as reproduced. No scientific comparison has been claimed.
