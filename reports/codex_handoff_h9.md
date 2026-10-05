# Codex handoff — H9 agent-trace-only dual-referee validation

Read first:
- reports/h9_preregistered_protocol.md

Remain GOLD-BLIND until all H9 outputs are frozen.

## 0. Prepare the fresh H9 tranche

Pull latest main.

Expected committed files:
- artifacts/h9_fresh_validation_100_model_inputs.json
- reports/h9_fresh_validation_100_manifest.json
- reports/h9_fresh_validation_100_identity_index.json

If the GitHub Action has not committed them yet, generate them locally without gold:

```bash
python -m benchmark.prepare
python -m scripts.select_h9_fresh_validation
```

Verify:
- 100 cases
- 25 per workflow
- contains_gold = false
- excluded_previous_train_cases = 420
- zero overlap with prior dev/H4/H5/H6/H7-H8 tranches

Do NOT inspect TRAIN gold.

## 1. Build and execute frozen M3 baseline

Build baseline batches using the existing frozen builder:

```bash
python -m scripts.build_h7_baseline_batches   --inputs artifacts/h9_fresh_validation_100_model_inputs.json   --manifest reports/h9_fresh_validation_100_manifest.json   --identity reports/h9_fresh_validation_100_identity_index.json   --out-dir artifacts/h9_baseline_choice_batches   --run-manifest reports/h9_baseline_choice_batch_manifest.json
```

Execute all 10 baseline batches:
- GPT-6.1 Sol
- existing ChatGPT authentication
- reasoning effort low
- one fresh session per batch
- no prior answer exposure
- no completed-valid-batch reruns

Save:
- artifacts/h9_baseline_choice_predictions.json
- reports/h9_baseline_choice_execution_manifest.json

Validate exactly 100 cases / 500 grouped decisions.

## 2. Build AGENT-TRACE-ONLY blinded referee batches

Run:

```bash
python -m scripts.build_h9_referee_batches
```

Verify:
- only agent_trace_observability cases are sent to referees
- complete original grouped cases are preserved
- canonical top-two option pairs are in original option order
- baseline winner/probabilities/rank are NOT exposed
- no gold
- prompt = prompts/h7r_top_two_choice_referee_v1_1.txt

## 3. Referee A

Execute every generated H9 referee batch using fresh GPT-6.1 Sol sessions:
- reasoning low
- existing ChatGPT authentication
- no previous outputs
- no baseline rank/winner exposure
- no completed-valid-batch reruns

Save:
- artifacts/h9_referee_a_predictions.json
- reports/h9_referee_a_execution_manifest.json

Validate ordinary grouped schema. If a completed batch is malformed, stop and preserve it.

## 4. Referee B

Run the exact SAME frozen H9 referee batches again using entirely new fresh GPT-6.1 Sol sessions.

Do NOT expose referee A outputs.

Save:
- artifacts/h9_referee_b_predictions.json
- reports/h9_referee_b_execution_manifest.json

Same validation rules.

## 5. Frozen H9 routing

Run:

```bash
python -m scripts.route_h9_agent_trace_dual_referee
```

Create:
- artifacts/h9_routed_choice_predictions.json
- reports/h9_routing_audit.json

Verify:
- exactly 100 routed cases / 500 grouped decisions
- ONLY agent_trace_observability choice answers may change
- every switch is baseline winner -> baseline runner-up
- switch only when BOTH referees select the runner-up and have unique max at it
- customer_service answers byte-identical to baseline
- invoice_processing answers byte-identical to baseline
- security_incidents answers byte-identical to baseline
- all noul/score answers byte-identical to baseline
- no gold

## 6. Execution audit

Create:
- reports/h9_execution_audit.md
- reports/h9_execution_manifest.json

Record:
- source commit
- fresh tranche hashes
- baseline prompt/batches/predictions hashes
- referee prompt/batches hashes
- referee A/B hashes
- router hash
- routed hash
- routing audit hash
- model = gpt-6.1-sol
- reasoning = low
- baseline fresh session count
- referee A fresh session count
- referee B fresh session count
- switch count
- completed valid batch reruns = 0
- train_gold_accessed = false
- test_gold_accessed = false
- evaluator_called = false
- scoring_performed = false
- tuning_performed = false

Do NOT access TRAIN gold yet.

Stop exactly with:

READY FOR H9 TRAIN GOLD SCORING
