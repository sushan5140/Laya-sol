# Manual development diagnostic

**development-only manual GPT-6.1 Sol diagnostic — 20 TRAIN cases / 100 decisions — not the official benchmark**

Hard accuracy: **64 / 100 (64.00%)**. Invalid outputs: **0**.

| Metric | Value | Denominator |
|---|---:|---:|
| Hard accuracy | 0.640000000 | 100 |
| Soft accuracy | 0.620550999 | 60 choice/noul |
| Brier against soft gold | 0.148962288 | 60 choice/noul |
| ECE (15 bins) | 0.187560000 | 100 |
| Score MAE | 0.467733325 | 40 score |
| Within one level | 0.900000000 | 40 score |

| Workflow | Correct / decisions | Accuracy |
|---|---:|---:|
| agent_trace_observability | 11 / 25 | 44.00% |
| customer_service | 21 / 25 | 84.00% |
| invoice_processing | 16 / 25 | 64.00% |
| security_incidents | 16 / 25 | 64.00% |

| Decision type | Correct / decisions | Accuracy |
|---|---:|---:|
| choice | 17 / 30 | 56.67% |
| noul | 27 / 30 | 90.00% |
| score | 20 / 40 | 50.00% |

All 20 outputs have five decisions with the required question IDs. Selected choice labels, exact distribution keys, probability finiteness/range, and distribution sums were checked using the unchanged frozen schema. Maximum accepted distribution sum error: 0; tolerance: 1e-4.

The 20 outputs were mapped by array position to the original export provenance. Workflow blocks and question IDs match. The user attests exact within-workflow order; outputs have no case IDs or states, so that part cannot be independently authenticated.

Input bytes and provenance match the frozen commit. Inputs contain only state and questions, with no gold, reference predictions, evaluator scores, factors or agreement fields. The exact actual chat transcript, selected model and reasoning setting are user-reported; this import does not authenticate settings or additional chat context.

The raw response was copied byte-for-byte, including formatting, numeric spelling and line endings. No selected answer or probability was changed, reordered, repaired or optimized. The unchanged scorer performs its already-frozen within-tolerance probability normalization internally for metric calculation; it does not rewrite the saved response. Soft accuracy/Brier exclude score questions. Score expectations use zero-based rubric levels. Noul selects true at probability >= 0.5. Choice accuracy uses the explicit selected label. Failures remain in the 100-decision denominator.

Frozen source commit: `ed4f84b6ada60bd46956211ffb9863f0af435cee`.
Metric version: `laya-kaggle-cell14-v1`.
Raw response SHA-256: `ae49c8985959862751edc5823930813a8c374b72ed0210592a4e5e16ecd1d43d`.
Model input SHA-256: `ac7d4614edd60b518e455af2e5f622a0a96a76e582edbec39e15742ef5ca628b`.
Prompt SHA-256: `8c774dda575f8e555f32902a9d3d3db7480f6093f7be144de60dd4070e1333ff`.
Scorer SHA-256: `d450126c9fc858027695a98bb13e018904d21874376064ac44fbb4d7069331b0`.

All protected source files, prompt, gold and frozen benchmark hashes were verified unchanged. Only TRAIN gold for the exported IDs was used to calculate this result. The official 400-case test was not evaluated. No model or API was called by the importer. API token usage, cost and latency are unavailable for this manual response.

This small training-split diagnostic is not the official benchmark and supports no claim of superiority to Laya/Jev or unseen-data generalization. Published-reference reproduction remains unresolved. These results must not be used to alter the frozen official v1 prompt or tune against official test labels.

Reproduce offline:

```powershell
.venv/Scripts/python.exe -m scripts.import_manual_dev20 --response results/manual_dev20_gpt61sol_predictions.json
```
