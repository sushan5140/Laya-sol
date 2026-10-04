# Codex handoff — H6 choice A/B fresh validation

This stage is GOLD-BLIND until both arms are fully frozen.

## Pull + verify

Pull latest main.

Verify these files exist:

- artifacts/h6_fresh_validation_100_model_inputs.json
- reports/h6_fresh_validation_100_manifest.json
- reports/h6_fresh_validation_100_identity_index.json
- prompts/m3_choice_boundary_fidelity_v1.txt
- prompts/h6_choice_action_semantics_delta_v1.txt
- reports/post_official_m4_protocol.md
- scripts/build_h6_choice_batches.py

Do not access TRAIN gold yet.

## Build frozen A/B batches

Run:

```bash
python -m scripts.build_h6_choice_batches
```

Verify:
- baseline = 10 batches × 10 cases
- h6_candidate = 10 batches × 10 cases
- exact same 100 case identities/order in both arms
- candidate prompt is bytewise baseline prompt plus frozen H6 delta
- no gold in inputs/manifests

## Execute baseline arm

Use the already-selected GPT-6.1 Sol with the same accepted signed-in Codex configuration and reasoning effort low.

Run baseline batches 01–10 sequentially.
Use one fresh model session per batch.
Do not expose prior batch answers.
Do not rerun a completed valid batch.
A quota/transport/config failure that produced no valid answer may be resumed and must be disclosed.

Save:
- artifacts/h6_baseline_choice_predictions.json
- reports/h6_baseline_choice_execution_manifest.json

Exactly 100 outputs in case_index order.

## Execute H6 candidate arm

Then run h6_candidate batches 01–10 under the identical execution rules.

Important:
- do not expose baseline outputs to candidate sessions
- do not change any prompt/input/model setting after seeing baseline outputs

Save:
- artifacts/h6_candidate_choice_predictions.json
- reports/h6_candidate_choice_execution_manifest.json

## Structural validation only

For BOTH arms verify:
- 100 unique cases
- zero missing/duplicate outputs
- original question IDs preserved
- choice selected labels allowed
- all distributions finite, [0,1], sum within 0.0001
- noul probabilities valid
- score probability keys valid

No evaluator. No TRAIN gold. No scoring yet.

Create:
- reports/h6_choice_execution_audit.md

Audit must include hashes for:
- fresh input file
- selection manifest
- identity index
- baseline prompt
- H6 delta
- candidate prompt
- both prediction files

Also record:
- model = gpt-6.1-sol
- fresh sessions = 20
- completed valid batches rerun = 0
- baseline_outputs_exposed_to_candidate = false
- train_gold_accessed = false
- evaluator_called = false
- scoring_performed = false
- tuning_performed = false

Stop with exactly:

READY FOR H6 TRAIN GOLD SCORING
