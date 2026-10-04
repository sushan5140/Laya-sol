# Codex handoff — fresh M2 validation stage

This handoff is intentionally **gold-blind**.

## Files to provide to Codex

1. `artifacts/fresh_validation_100_model_inputs.json`
2. `reports/fresh_validation_100_manifest.json`
3. `prompts/m2_explicit_noul_shield_prompt_v1.txt`

Optional verification context:
4. `reports/fresh_validation_100_preregistered_ids.json`

Do **not** provide `benchmark/frozen/train_gold.jsonl` yet.

## Codex task

Verify the fresh validation package only. Do not score anything and do not inspect gold.

Checks:
- exactly 100 fresh TRAIN cases;
- exactly 25 cases per workflow;
- no IDs overlap the 20 IDs in `reports/development_export.json`;
- manifest case order exactly matches the model-input order;
- M2 prompt file is used byte-for-byte;
- no hidden labels / gold / correctness metadata are present in the model-input package.

Then prepare the execution package for a fresh M2 run:
- preserve each grouped case unchanged;
- preserve all question IDs and rubric order;
- produce one model invocation payload per case;
- preserve case order;
- write a run manifest with SHA-256 hashes of the prompt and input file;
- do not call the evaluator;
- do not read gold;
- do not build H4 referee inputs until the M2 outputs exist.

Expected next artifact names:
- `artifacts/fresh_validation_m2_run_inputs.json`
- `reports/fresh_validation_m2_run_manifest.json`

After those are ready, stop and report that the package is ready for the GPT-6.1 Sol M2 prediction pass.
