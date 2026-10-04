# Codex handoff — H5 repeated-run consensus

This stage is GOLD-BLIND.

## First

Pull latest `main`.

Verify these files exist:

- `artifacts/h5_fresh_validation_100_model_inputs.json`
- `reports/h5_fresh_validation_100_manifest.json`
- `reports/h5_fresh_validation_100_identity_index.json`
- `prompts/m2_explicit_noul_shield_prompt_v1.txt`
- `reports/h5_preregistered_protocol.md`
- `scripts/build_h5_fresh_m2_batches.py`
- `scripts/route_h5_repeated_consensus.py`

Do not read any gold file.

## Prepare immutable batches

Run:

```bash
python -m scripts.build_h5_fresh_m2_batches
```

Verify:
- 10 batches;
- 10 cases per batch;
- 100 cases total;
- same exact batch files will be reused for A, B, C;
- prompt hash matches the archived M2 prompt.

## Execute three independent passes

Use the already-selected GPT-6.1 Sol model.

Run all 10 batches for **Run A** using one fresh model session per batch.
Then run the exact same 10 batch files again for **Run B**, again with fresh sessions.
Then run the exact same 10 batch files again for **Run C**, again with fresh sessions.

Do not carry answers from one batch/run into another.
Do not expose previous run outputs to later runs.
Do not alter prompts, cases, ordering, model settings, or batch files.
Do not score.
Do not inspect gold.

Save:

- `artifacts/h5_run_a_predictions.json`
- `artifacts/h5_run_b_predictions.json`
- `artifacts/h5_run_c_predictions.json`

Each file must contain exactly 100 case outputs in case_index order and preserve:
- case_index
- case_id
- workflow
- original question IDs

Structurally validate each run:
- 100 unique cases;
- zero missing/duplicates;
- valid JSON;
- score probability keys match supplied rubric indices;
- all distributions finite, in [0,1], and sum to 1 within 0.0001;
- noul probability_true in [0,1];
- selected choice labels allowed.

Do not repair malformed outputs and do not rerun a completed valid batch. A quota/configuration failure that produced no valid answer may be resumed and must be disclosed.

## Freeze H5 routing

Only after A/B/C are complete, run:

```bash
python -m scripts.route_h5_repeated_consensus \
  --a artifacts/h5_run_a_predictions.json \
  --b artifacts/h5_run_b_predictions.json \
  --c artifacts/h5_run_c_predictions.json
```

This produces:

- `artifacts/h5_fresh_consensus_predictions.json`
- `reports/h5_fresh_consensus_routing_audit.json`

Do not score.

## Final audit

Create `reports/h5_fresh_execution_audit.md` reporting:
- 30/30 batch executions expected;
- 300/300 case outputs expected;
- structural validity for A/B/C;
- any no-answer quota/config failures;
- H5 switch count;
- preserved baseline ties/invalids;
- choice_noul_modified must be false;
- all relevant SHA-256 hashes;
- gold_accessed = false;
- evaluator_called = false;
- scoring_performed = false.

Stop after this exact line:

READY FOR FIRST H5 GOLD SCORING PASS
