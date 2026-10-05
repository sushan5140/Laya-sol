# Codex handoff — H7 conservative top-two choice referee

This stage remains GOLD-BLIND until baseline, referee, and routed outputs are frozen.

## Pull + verify

Pull latest main.

Verify these files exist:

- artifacts/h7_fresh_validation_100_model_inputs.json
- reports/h7_fresh_validation_100_manifest.json
- reports/h7_fresh_validation_100_identity_index.json
- prompts/m3_choice_boundary_fidelity_v1.txt
- prompts/h7_top_two_choice_referee_v1.txt
- reports/h7_preregistered_protocol.md
- scripts/build_h7_baseline_batches.py
- scripts/build_h7_referee_batches.py
- scripts/route_h7_top_two.py

Do not access TRAIN or TEST gold.

## Stage A — frozen M3 choice baseline

Run:

```bash
python -m scripts.build_h7_baseline_batches
```

Verify:
- 10 baseline batches × 10 cases
- 100 unique cases
- exact H7 fresh case order
- prompt = frozen M3 choice-boundary prompt
- no gold

Execute baseline batches 01–10 sequentially using:
- already-selected GPT-6.1 Sol
- existing ChatGPT authentication
- reasoning effort low
- one fresh model session per batch
- no previous-output exposure
- no completed-valid-batch reruns

Save:

- artifacts/h7_baseline_choice_predictions.json
- reports/h7_baseline_choice_execution_manifest.json

Exactly 100 outputs in case_index order, preserving case_index, case_id, workflow, and original question IDs.

Structurally validate all grouped answers before continuing.

## Stage B — build blinded top-two referee inputs

Only after baseline outputs are frozen, run:

```bash
python -m scripts.build_h7_referee_batches   --baseline artifacts/h7_baseline_choice_predictions.json
```

Verify the generated eligibility manifest proves:
- referee sees no baseline winner identity
- referee sees no probabilities
- referee sees no baseline rank ordering
- option pairs are canonicalized by original option order
- no gold
- complete original mixed grouped cases are preserved

Do not inspect correctness.

## Stage C — H7 referee execution

Run every generated referee batch sequentially using the same GPT-6.1 Sol / signed-in / reasoning-low configuration.

Rules:
- one fresh model session per referee batch
- no baseline outputs passed to the model beyond the blinded top-two sidecar already generated
- no earlier referee output exposure
- no completed-valid-batch reruns
- no prompt/input edits
- no scoring
- no evaluator
- no gold

Save:

- artifacts/h7_referee_predictions.json
- reports/h7_referee_execution_manifest.json

Each referee prediction object must preserve:
- case_index
- case_id
- workflow
- answers
- boundary_audit

Only cases included in referee batches should appear.

Validate schema and audit structure, but do not repair malformed model content. If a completed batch is malformed, stop and preserve it.

## Stage D — frozen strict routing

Run:

```bash
python -m scripts.route_h7_top_two   --baseline artifacts/h7_baseline_choice_predictions.json   --referee artifacts/h7_referee_predictions.json
```

This must create:

- artifacts/h7_routed_choice_predictions.json
- reports/h7_routing_audit.json

Do not alter the router.

Verify:
- only eligible choice questions can switch
- every switch is baseline winner -> baseline runner-up only
- all switch-license checks passed
- noul and score outputs are byte-identical to baseline
- routed file still contains exactly 100 cases / 500 grouped decisions

## Stage E — execution audit

Create:

- reports/h7_execution_audit.md
- reports/h7_execution_manifest.json

Record at minimum:
- source commit
- model = gpt-6.1-sol
- reasoning effort = low
- existing ChatGPT authentication
- baseline fresh sessions count
- referee fresh sessions count
- baseline valid case outputs = 100
- eligible referee cases/questions
- routed switch count
- no completed valid batch reruns
- any transport/quota/config events
- baseline outputs not exposed except through the frozen blinded pair constructor
- train_gold_accessed = false
- test_gold_accessed = false
- evaluator_called = false
- scoring_performed = false
- tuning_performed = false
- hashes of fresh inputs, manifests, prompts, scripts, baseline predictions, referee predictions, routed predictions, and routing audit

Important:
- do NOT access TRAIN gold yet
- do NOT access TEST gold
- do NOT score
- do NOT tune based on switch count
- even if switch count looks low/high, do not change anything

Stop with exactly:

READY FOR H7 TRAIN GOLD SCORING
