# H8 preregistered protocol — dual blinded referee consensus

Status: frozen before any TRAIN-gold access, evaluator call, scoring, or correctness inspection on the H7/H8 tranche.

## Motivation

H7R proved the strict evidence-license router was too conservative: all 137 comparisons returned null licenses, yet 19 ordinary referee choice distributions independently placed the frozen baseline runner-up at a unique maximum.

H8 tests whether independent blinded agreement can recover useful baseline ranking errors without the over-broad global rewrite failure seen in H6.

## Frozen data boundary

Reuse the same fourth fresh TRAIN tranche because its gold remains unopened.

Reuse unchanged:
- artifacts/h7_baseline_choice_predictions.json
- reports/h7r_referee_eligibility_manifest.json
- artifacts/h7r_referee_predictions.json

H7R referee predictions are referee A.

No TRAIN gold or TEST gold may be opened before H8 referee B and the routed H8 output are frozen.

## H8 hypothesis

For an eligible choice question:
- baseline supplies winner k and runner-up j;
- referee A = frozen H7R referee ordinary choice distribution;
- referee B = one new independent blinded referee execution using the exact same H7R prompt and exact same blinded pair inputs.

Switch k -> j only if BOTH referee A and referee B:
1. are structurally valid;
2. have a unique probability maximum at j;
3. have selected == j.

Otherwise retain the frozen baseline answer exactly.

The H7/H7R licensed_preference field is ignored by H8 routing and is not used as a switch requirement.

## Blinding

Referee B must receive exactly the same blinded inputs as H7R:
- complete original mixed grouped case;
- canonical top-two option pair in original option order;
- no baseline winner;
- no baseline probabilities;
- no rank identity;
- no gold;
- no correctness;
- no H7R outputs.

Use:
- GPT-6.1 Sol
- existing ChatGPT authentication
- reasoning effort low
- one fresh session per batch
- no previous output exposure
- no completed-valid-batch reruns

## Frozen router

For each eligible choice qid:
- obtain baseline winner and runner-up from the already-frozen private eligibility manifest;
- require referee A unique-max selected == runner-up;
- require referee B unique-max selected == runner-up;
- if both pass, copy referee B's ordinary choice answer object into routed output;
- otherwise retain baseline answer byte-for-byte.

No workflow rule, label rule, confidence threshold, probability margin, case exception, or post-gold tuning is allowed.

Noul and score remain byte-identical to baseline.

## Evaluation

Primary endpoint:
- choice hard accuracy H8 vs frozen baseline.

Report:
- baseline choice accuracy;
- H8 choice accuracy;
- absolute pp improvement;
- switch count;
- corrections;
- regressions;
- switch precision;
- per-workflow choice accuracy;
- agent_trace_observability choice accuracy;
- paired case bootstrap stratified by workflow, 20,000 replicates, seed 20261005.

## Promotion gate

Promote H8 only if ALL:
1. overall choice improvement >= 3.0 pp;
2. corrections > regressions;
3. switch precision >= 60%;
4. agent_trace_observability choice does not regress;
5. paired bootstrap 5th percentile > 0;
6. noul/score byte-identical to baseline;
7. all referee B and routed outputs frozen before correctness inspection.

If H8 fails, retain M3 choice specialist and do not tune H8 on this tranche.
