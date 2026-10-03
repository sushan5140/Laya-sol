# Frozen typed-decisions benchmark

Source: [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions/tree/d0e2f0c42fef86cc15d1688d25a19f5ba7c85b18), configuration `all`, official `test` split. No resampling, label replacement, or prompt tuning on test. The exact source revision and Parquet/JSONL hashes are in [lock.json](lock.json).

Test: 400 cases / 2,000 decisions. Each of four workflows has 100 cases. Decision totals: 600 choice, 600 noul, 800 score. Train: 1,200 cases / 6,000 decisions, 300 cases per workflow.

Source `state`, `questions`, and `gold` columns are JSON strings. Preparation decodes them exactly as the fine-tuning notebook does, preserving string values, arrays, mapping insertion order, criteria descriptions, original case IDs and question IDs. Original file bytes are independently pinned by Parquet hashes. `factors`, `label_agreement`, and flat answer columns are never exported as model input. There is no source reconstruction or paraphrasing.

`frozen/test_inputs.jsonl` rows contain `id`, `workflow`, `state`, `questions`. Only `state` and `questions` are sent to the API. `frozen/test_gold.jsonl` contains original `id` and `gold` without label changes. The corresponding train files are separate. All four files have individual SHA-256 locks; original IDs/states must not overlap between splits. Counts, schema, gold distributions, pin and hash changes cause refusal.

`python -m benchmark.prepare` obtains pinned assets. There is deliberately no automatic lock-update mode. A changed dataset requires an explicit new scientific protocol and review. `python -m benchmark.validate` verifies prepared files against committed locks. Re-run preparation after deliberately changing the preparation script; a recorded script hash mismatch also causes refusal.

Score levels are the supplied ordered rubric positions, encoded as string indices `"0"`, `"1"`, etc. Rubric text remains verbatim in the input. The expected score is `sum(index * probability)`, not a new numeric scale or a mapping of level descriptions onto arbitrary numbers.

See [methodology](../reports/methodology.md) for exact notebook metrics, differences from later upstream scorers, failure policy and reference-evidence limitations.
