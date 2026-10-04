# H5 preregistered repeated-run consensus protocol

Status: frozen before H5 correctness inspection.

## Fresh TRAIN tranche

Use exactly 100 TRAIN cases, 25 per workflow, selected by:

- exclude the original 20 development cases;
- exclude the first fresh 100-case H4/M2 validation tranche;
- rank remaining cases within workflow by
  `SHA256("laya-score-h5-validation-v1\n" + workflow + "\n" + case_id)`;
- take the first 25 per workflow.

No gold may be read during selection, model execution, or routing.

## Model runs

For every selected case, run the exact archived M2 prompt/config three times:

- A = baseline
- B = rerun 1
- C = rerun 2

Each run uses the same grouped case and same prompt. Preserve original case/question/rubric order.

## H5 routing rule

For each score question independently:

1. If baseline A is malformed, retain A.
2. If A has an exact maximum-probability tie, retain A.
3. Otherwise let `k` be A's unique winning level.
4. B and C must each be valid and have a unique winning level.
5. Switch only if B and C agree on the same unique alternative `j`, where `j != k`.
6. When switching, copy B's complete score vector for that question.
7. Otherwise retain A.

Choice and noul outputs are copied from the frozen baseline specialist routing and must not change.
No probability pooling, confidence threshold, ordinal-distance restriction, retry-based selection, or post-gold tuning is allowed.

## Evaluation

After A/B/C outputs and the routed H5 predictions are frozen and hashed, load TRAIN gold once.

Primary endpoint: score-only paired improvement of H5 over the frozen baseline on this fresh tranche.

Report:
- baseline score accuracy;
- H5 score accuracy;
- corrections;
- regressions;
- net improvement;
- switch count;
- exact-tie preservation;
- invalids;
- per-workflow score results;
- stratified paired case bootstrap by workflow, 20,000 replicates, seed 20261004.

Promotion requires:
- score improvement >= 5 percentage points;
- bootstrap 5th percentile > 0;
- choice/noul identical to the frozen baseline;
- predictions/routing frozen before correctness inspection.

If H5 fails or is inconclusive, retain M3.
