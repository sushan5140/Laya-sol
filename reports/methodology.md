# Methodology and source audit

## Evidence and reproducibility

This is Phase 1 only, prepared on 2026-10-04 (Asia/Calcutta). No GPT-6.1 Sol inference, training, fine-tuning, or official test prompt optimization occurred. Later user steering requested a development-only manual export and explicitly prohibited running the model.

| Source | Exact revision |
|---|---|
| [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya/tree/2e4d9c87e8b1621deb344eac7de5c7258f32f849) | `2e4d9c87e8b1621deb344eac7de5c7258f32f849` |
| [virajbhartiya/laya-vs-jev](https://github.com/virajbhartiya/laya-vs-jev/tree/28541781c863fcdf20348e5bb3a2073d672fffe6) | `28541781c863fcdf20348e5bb3a2073d672fffe6` |
| [Dataset](https://huggingface.co/datasets/LocalLLaMA/typed-decisions/tree/d0e2f0c42fef86cc15d1688d25a19f5ba7c85b18) | `d0e2f0c42fef86cc15d1688d25a19f5ba7c85b18` |
| [Published typed-decisions checkpoint files inspected](https://huggingface.co/convaiinnovations/laya-typed-decisions/tree/e929ae5cf69bc34259cd2f95c9e91145b818b1f0) | `e929ae5cf69bc34259cd2f95c9e91145b818b1f0` |
| Historical upstream pin attributed by MLX port | `6a5819129eb220570792e417e49723d697efd76f` (not used as the metric implementation) |

The primary graph backend was queried first and coverage checked. It excludes `research/scripts` and `docs`, so relevant source sections were read directly. Exact files and hashes are recorded in `benchmark/sources.json`. The inspected upstream files include README, docs/finetune, research/README, research/scripts/bench_local, research/scripts/build_benchmark_nb, research/results/t4_colab_benchmark, research/results/cpu_51_language_sweep, laya/common, and the fine-tuning notebook's schema/evaluation/report cells. The notebook was read, never executed for training. The comparison repository's README, benchmarks/accuracy and validation-typed-decisions archive were inspected. Upstream checkouts were not edited or pushed.

## Data and schema

The official benchmark is hosted publicly on Hugging Face, not constructed anew in this experiment. The `all/test-00000-of-00001.parquet` asset has 400 rows with five questions each: four workflows, 100 cases each, 600 choice / 600 noul / 800 score questions. The official `train` asset has 1,200 rows / 6,000 questions. The dataset card describes separate generation seeds, independently sampled latent factors rendered into text/structured states, three teacher samples at temperature 0.7, and averaged distributions. It does not publish the generation program or exact numeric generation seeds in the inspected dataset checkout; those cannot be independently regenerated from these assets.

Source columns: `id`, `workflow`, `split`, `state`, `questions`, `gold`, `factors`, `label_agreement`, `n_questions`. The last four construction/convenience fields are evaluator-only. State is decoded JSON (nested dictionaries, strings, lists and numbers). Questions are an ordered mapping of question ID to `{type,instructions,criteria}`. Choice criteria map exact labels to descriptions; noul criteria map `false`/`true` to descriptions; score criteria are an ordered list of rubric descriptions. Gold maps question IDs to original `{type,label,probabilities,...}` records; choice has confidence, noul additionally has `noul`, score additionally has `score`. Gold labels are not recomputed from averaged distributions.

Model payloads contain only state and questions. The 20-case manual export selects the first five rows from each train workflow in original order. Separate `reports/development_export.json` records IDs for later offline mapping, without placing them in the manual input artifact. No official test example appears in either prompt.

## Decision and metric semantics

Primary metric version: `laya-kaggle-cell14-v1`, pinned to notebook cells 12 and 14, because those implement the fine-tuning comparison. The scorer is independently implemented; tests execute exact attributed upstream snippets on synthetic fixtures. These snippets do not contain test cases or answer keys and are never supplied to the model.

| Metric | Exact valid-output calculation |
|---|---|
| Accuracy | Mean of hard-label agreement over all decisions. Choice uses the explicit `selected` label, matching upstream `choice`. Noul selects `true` at `p_true >= 0.5`, including exact ties. Score uses the first maximum-probability zero-based level. |
| Soft accuracy | Mean `sum(p_i * g_i)` over **choice and noul only**. Choice gold probabilities are normalized; noul uses `[1-g_noul,g_noul]`, preferring gold `noul` as the notebook does. |
| Brier | Mean **sum** of squared probability differences from soft teacher gold, over **choice and noul only**. It is not hard-label Brier and not divided by number of levels. |
| ECE | 15 equal-width bins over maximum returned probability and hard-label correctness. First bin includes zero; all bins include upper endpoint; later bins exclude lower endpoint. Sum `bin_count / n * abs(mean_confidence - mean_correct)`. Floating boundaries reproduce upstream NumPy linspace. |
| Score MAE | Mean absolute difference between predicted `sum(i*p_i)` and original gold `score`, over score questions only. |
| Within one level | Fraction of score questions with the same absolute expected-score error **<= 1.0**, inclusive. |

For a complete valid official run, denominators are: accuracy/ECE 2,000; soft accuracy/Brier 1,200; score MAE/within-one 800. All probabilities must be numeric, finite, in [0,1], with exact supplied keys and mass within absolute 1e-4; accepted mass is normalized for scoring. Choice selection must be an exact supplied label. The prompt requests maximum-probability selection, but accuracy retains the notebook's explicit-selection semantics even if a distribution disagrees. Original gold is separately schema-validated and never repaired or rewritten.

Important upstream inconsistency: `bench_local.py` and the generated Colab sweep calculate soft accuracy and soft Brier across **all three** primitives; their hard `brier` field is against one-hot gold and is a different metric. `bench_local.metrics` discards `None` rows. The Kaggle notebook excludes score questions from soft accuracy/Brier and assumes every answer exists, without a failure-denominator policy. These conventions must not be silently conflated. This evaluator publishes the notebook metrics and an explicit missing-output policy.

Failures, refusals, incomplete responses and invalid decisions count as incorrect in overall and slice accuracy. A case transport failure produces five records. Partial invalid structured output retains valid decisions and counts invalid ones as failures. No failure is replaced with invented probabilities. If any decision fails, primary probabilistic and score metrics are `null`; separately labelled valid-only diagnostics include exact denominators and coverage. Thus failed outputs cannot silently improve the main probabilistic comparison. Missing prediction records are failures too; duplicate, unknown or mis-mapped IDs are rejected.

Transport retries (up to three attempts, SDK retries disabled) are restricted to transient connection/timeout errors and listed HTTP retry statuses. They repeat identical payloads. Final malformed answers are not retried or corrected. Every completed case is checkpointed atomically in SQLite; both success and failure records are final on resume. A single writer lock prevents concurrent duplication. An interruption after API billing but before checkpoint commit can cause that in-flight case to be sent again; exactly-once billing across crashes is not guaranteed. Unknown token usage on failed attempts is reported explicitly, not guessed as zero cost.

## Published reference audit

The upstream fine-tuning notebook hard-codes Jev 1.13.0 accuracy .727, soft accuracy .580, Brier .148, ECE .144, score MAE .391, within-one .952, and teacher self-agreement .735. It computes the new Laya row from a run. `bench_local.py` explicitly says Jev was not executed there. The dataset card separately reports Jev was measured through TypeSafe on 2026-09-18, all 2,000 decisions, zero errors; this is a source claim, not a run reproduced here.

The [pinned Laya README](https://github.com/NandhaKishorM/laya/blob/2e4d9c87e8b1621deb344eac7de5c7258f32f849/README.md#typed-decisions-measured-on-all-three-checkpoints) explicitly states that .766 and its per-workflow values have **no committed result file**. Its aggregate base-checkpoint runs report .3620 / .3515 (T4) and .3615 English (CPU), but contain no per-decision predictions from which this scorer can reconstruct their metrics. MLX validation compares 63 fixture questions for numerical parity; that is not the 400-case accuracy test. Its AG News scorer is a different dataset. The published typed-decisions checkpoint's inspected file inventory has no benchmark report or raw prediction archive.

Therefore **published Laya/Jev metric reproduction has not succeeded**. Fixture metric parity succeeds; it is a separate result. The official command fails before creating the API client until an authentic complete Laya archive reproduces the frozen targets via `scripts.verify_reference`. Hashes verify archive bytes, not the truth of model provenance; archive authenticity must be reviewed. Any mismatch must be diagnosed without running or tuning GPT-6.1 Sol. The gate has no command-line bypass.

## Inference configuration and accounting

Requested model is preserved exactly as `gpt-6.1-sol`, reasoning effort `max`. [Official model documentation](https://developers.openai.com/api/docs/models/gpt-6.1-sol) confirms `max` and structured outputs. [Responses structured output documentation](https://developers.openai.com/api/docs/guides/structured-outputs) supplies the strict `text.format` JSON-schema pattern. Each primary call contains all five questions in a case, matching the dataset card's hosted-row request structure; questions are evaluated independently. An exact source-level per-question adapter schema covers all primitives.

No web/file search, MCP, interpreter, computer use, retrieval, filesystem tools, agent environment, previous response or conversation state is configured. Tools are empty and `tool_choice=none`; `store=false`; fixed endpoint is api.openai.com/v1; maximum output token budget is 32,768 including reasoning; no temperature or top-p is sent. The adapter only receives a strict ModelCase. Offline preparation/research and scoring are distinct from inference.

Store only validated final decisions/statuses, safe error type and HTTP status, response ID/model/status, token usage, timestamps, latency and aggregate metrics. SDK response objects, reasoning content, raw error text, credentials and raw malformed output are not serialized. Case timestamps are UTC; report preparation date follows the user's Asia/Calcutta timezone. Runs record input/prompt/implementation/preparation/source hashes, SDK/Python versions, explicit API parameters, attempt limits and pricing. Primary requests: 400, up to 1,200 transport attempts, still exactly 2,000 decisions.

Standard-tier documented rates verified 2026-10-04 are $2/M input, $.10/M cached input, $2.50/M cache writes and $10/M output. Known-usage estimated dollars are `(uncached_input*2 + cached_input*.1 + cache_write_input*2.5 + output*10)/1e6`. Reasoning tokens are already included in output tokens. A pessimistic token-budget ceiling for 400 successful calls is 13,107,200 output tokens ($131.072 at the listed rate), plus input; this is a ceiling, not an expected quote. Retries and unknown billing can add cost. No actual API cost or latency is measured in Phase 1. Manual chat has no verified API parameters or accounting and cannot substitute for the primary API evaluation.

## Contamination and comparison limits

The dataset, question schemas, gold labels and Laya training notebook are public. We cannot exclude their inclusion in a frontier model's training data. The benchmark card describes a roughly 4B-class teacher and warns that agreement is not necessarily correctness; teacher self-agreement .735 is not a universal mathematical ceiling. An accurate reasoner can disagree with faulty teacher labels.

Laya is fitted on the official training split. GPT-6.1 Sol would be tested with a frozen zero-shot prompt. The dataset card warns fitted and general-model tables should not be treated as interchangeable quality rankings. Record benchmark performance descriptively; do not infer generalization or that GPT-6.1 Sol beats Laya before a complete frozen evaluation. No prompt fixes or test failures may inform v1. Further prompt experiments must use development data under a new disclosed version.
