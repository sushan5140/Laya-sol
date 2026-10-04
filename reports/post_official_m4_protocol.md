# Post-official M4 research protocol

Goal: build a new method that can plausibly exceed the official frozen M3 result on a future unseen benchmark.

Important boundary:
- The official 400-case TEST is now diagnostic-only.
- Official TEST correctness may be used to identify broad failure categories, but it must not be used for prompt selection, candidate promotion, threshold tuning, or re-benchmark claims.
- All M4 method selection occurs on fresh TRAIN-only validation tranches.

## Primary target

Choice accuracy is the first target because official M3 choice accuracy was 386/600 = 64.33%, materially below noul and score.

Secondary target: agent_trace_observability, the weakest official workflow.

## Hypothesis family

H6 — action-semantics boundary decomposition.

Hypothesis:
Most remaining choice failures arise from conflating:
1. what the state establishes about the action already taken,
2. what should happen next,
3. whether the action is reversible / in-scope / safe,
4. whether uncertainty warrants observe vs human_review,
5. whether explicit harm / policy violation warrants stop.

Candidate prompt should force a compact evidence table for these five dimensions before selecting the choice label, while preserving the original grouped mixed-case context.

No gold-dependent routing and no case-specific exceptions are allowed.

## Fresh TRAIN validation

Use only TRAIN cases not previously used by:
- old dev20,
- first fresh 100-case H4/M2 tranche,
- second fresh 100-case H5 tranche.

Select a new deterministic tranche:
- 100 cases total,
- 25 per workflow,
- rank within workflow by
  SHA256("laya-choice-h6-validation-v1\n" + workflow + "\n" + case_id)
- take first 25 per workflow.

Primary endpoint:
- choice-only hard accuracy, H6 vs frozen M3 choice specialist.

Secondary endpoints:
- agent_trace_observability choice accuracy,
- all-workflow choice accuracy,
- no change to noul/score outputs.

Promotion gate:
1. overall choice improvement >= 5 percentage points;
2. agent_trace_observability choice does not regress;
3. paired bootstrap 5th percentile > 0;
4. noul and score outputs are byte-identical to frozen baseline routing;
5. candidate frozen before correctness inspection.

Bootstrap:
- paired case bootstrap stratified by workflow,
- 20,000 replicates,
- seed 20261004.

If H6 fails, retain M3 choice specialist and stop before inventing post-hoc variants on the same tranche.
