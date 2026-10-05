# Codex handoff — H8 dual blinded referee consensus

H8 reuses the still-unopened fourth fresh TRAIN tranche.

Read:
- reports/h8_preregistered_protocol.md
- reports/h7r_zero_switch_debug.md
- reports/h7r_execution_audit.md

## Reuse frozen artifacts

Do NOT rerun baseline or referee A.

Frozen baseline:
- artifacts/h7_baseline_choice_predictions.json
- expected SHA-256: e8b95caebf4d98181295715571d37c2cb62d19a8dd517bfa1ea71e8be51a0773

Frozen referee A:
- artifacts/h7r_referee_predictions.json
- expected SHA-256: f8e93639a40bc735705de0a9e84c5c782d6ad47ea41b99dca27cfe0d10a355f0

Reuse exact H7R blinded batches:
- artifacts/h7r_referee_batches/batch_01.json ... batch_10.json

## Execute referee B

Run the SAME 10 H7R blinded referee batches again, but in 10 new fresh GPT-6.1 Sol sessions.

Use:
- existing ChatGPT authentication
- reasoning effort low
- one fresh session per batch
- no previous outputs
- do not expose referee A outputs
- do not expose baseline winner/probabilities/rank
- no completed-valid-batch reruns

Save:
- artifacts/h8_referee_b_predictions.json
- reports/h8_referee_b_execution_manifest.json

Each record must preserve:
- case_index
- case_id
- workflow
- answers
- boundary_audit

Validate ordinary grouped schema only. Do not normalize or repair model answers.

If a completed valid batch is malformed, stop and preserve it.

## Frozen routing

Run:

```bash
python -m scripts.route_h8_dual_referee   --ref-b artifacts/h8_referee_b_predictions.json
```

Create:
- artifacts/h8_routed_choice_predictions.json
- reports/h8_routing_audit.json

Do not modify the router.

Verify:
- exactly 100 routed cases / 500 grouped decisions
- only eligible choice questions changed
- every switch is baseline winner -> baseline runner-up
- switch occurs only when BOTH frozen referee A and fresh referee B have selected == runner-up and unique maximum at runner-up
- noul/score unchanged
- no gold access

## Audit

Create:
- reports/h8_execution_audit.md
- reports/h8_execution_manifest.json

Record:
- source commit
- baseline hash
- referee A hash
- referee B hash
- routed hash
- routing audit hash
- model/settings
- 10 fresh referee B sessions
- switch count
- train_gold_accessed = false
- test_gold_accessed = false
- evaluator_called = false
- scoring_performed = false
- tuning_performed = false
- completed valid batch reruns = 0

Do NOT access TRAIN gold yet.

Stop with:

READY FOR H8 TRAIN GOLD SCORING
