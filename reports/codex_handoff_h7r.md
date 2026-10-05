# Codex handoff — H7R schema-only referee repair

This is a NEW gold-blind execution of the same H7 hypothesis with an output-schema-only repair.

Read first:
- reports/h7r_schema_repair_amendment.md
- reports/h7_preregistered_protocol.md

## Reuse frozen baseline

Reuse unchanged:
- artifacts/h7_baseline_choice_predictions.json

Expected SHA-256:
- e8b95caebf4d98181295715571d37c2cb62d19a8dd517bfa1ea71e8be51a0773

Do NOT rerun the baseline.

## Rebuild referee batches with repaired prompt

Run:

```bash
python -m scripts.build_h7_referee_batches   --baseline artifacts/h7_baseline_choice_predictions.json   --prompt prompts/h7r_top_two_choice_referee_v1_1.txt   --out-dir artifacts/h7r_referee_batches   --manifest reports/h7r_referee_eligibility_manifest.json
```

Verify:
- same 100 H7 cases
- same eligible comparisons as original H7
- same blinded top-two pairs
- same canonical original-option ordering
- no baseline winner/probabilities/rank exposed
- no gold
- only prompt difference is explicit ordinary-answer schema wording

## Execute H7R referee

Run ALL generated H7R referee batches from batch 01 onward.

Use:
- GPT-6.1 Sol
- existing ChatGPT authentication
- reasoning effort low
- one fresh session per batch
- no previous-output exposure
- no malformed H7 batch output reused or shown
- no completed-valid-batch reruns

Save:
- artifacts/h7r_referee_predictions.json
- reports/h7r_referee_execution_manifest.json

Each saved record must include:
- case_index
- case_id
- workflow
- answers
- boundary_audit

Validate ordinary grouped answer objects strictly.

If a completed H7R batch is malformed, STOP and preserve it. Do not repair or rerun.

## Route with the SAME frozen H7 router

Run:

```bash
python -m scripts.route_h7_top_two   --baseline artifacts/h7_baseline_choice_predictions.json   --referee artifacts/h7r_referee_predictions.json   --eligibility reports/h7r_referee_eligibility_manifest.json   --output artifacts/h7r_routed_choice_predictions.json   --audit reports/h7r_routing_audit.json
```

Do not modify the router.

Verify:
- only eligible choice questions may change
- switches are baseline winner -> baseline runner-up only
- every switch passes the frozen evidence license
- noul/score unchanged
- exactly 100 routed cases / 500 decisions

## Audit

Create:
- reports/h7r_execution_audit.md
- reports/h7r_execution_manifest.json

Record:
- H7 original referee batch 01 failed structurally and is excluded
- H7R is schema-only repair
- baseline reused unchanged and hash verified
- repaired prompt hash
- H7R eligibility manifest hash
- H7R referee prediction hash
- routed prediction hash
- routing audit hash
- model/settings
- referee session count
- completed valid batches rerun = 0
- train_gold_accessed = false
- test_gold_accessed = false
- evaluator_called = false
- scoring_performed = false
- tuning_performed = false

Do NOT access gold.

Stop with exactly:

READY FOR H7R TRAIN GOLD SCORING
