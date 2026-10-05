# H7R schema-only repair amendment

Status: frozen before any TRAIN-gold access, evaluator call, scoring, tuning, or correctness inspection on the H7 tranche.

## Why H7 stopped

Original H7 referee batch 01 produced structurally malformed ordinary grouped answers: scalar values were returned where the benchmark requires answer objects.

The failure was caused by an underspecified output-schema sentence in the referee prompt: it referenced the "base choice schema" without spelling out the ordinary grouped answer object formats.

Per the original handoff, execution stopped immediately. The malformed batch was preserved and was not repaired or rerun.

## What H7R changes

H7R is a new, schema-repair execution of the same preregistered H7 hypothesis.

The ONLY allowed change from H7 to H7R is:
- spell out the ordinary grouped answer-object schema explicitly.

No decision logic, routing logic, evidence license, thresholds, eligibility, case selection, pair construction, model settings, or promotion gates are changed.

The H7 frozen baseline predictions remain reused unchanged because:
- they passed structural validation,
- no gold has been accessed,
- no correctness has been inspected,
- they are not affected by the referee schema failure.

The malformed H7 referee output is permanently excluded from H7R and must not be used for semantic guidance, routing, scoring, or tuning.

## H7R ordinary grouped answer schema

For each ordinary answer:
- choice:
  `{"selected":"<allowed option label>","probabilities":{"<label>":<number>,...}}`
- noul:
  `{"probability_true":<number>}`
- score:
  `{"probabilities":{"0":<number>,"1":<number>,...}}`

All distributions must be finite, in [0,1], and sum to 1 within 0.0001.

## Execution

Rebuild ALL H7 referee batches using the repaired prompt and rerun the referee from batch 01 onward in fresh sessions.

Do not reuse any malformed H7 referee output.

Then run the exact already-frozen `scripts/route_h7_top_two.py` router unchanged.

## Gold boundary

H7R remains fully GOLD-BLIND until:
- all repaired referee batches are completed,
- referee predictions are structurally valid,
- routing is complete,
- routed predictions and hashes are frozen.

Only then may TRAIN gold be accessed once for H7R scoring.

## Promotion gate

Unchanged from `reports/h7_preregistered_protocol.md`.
