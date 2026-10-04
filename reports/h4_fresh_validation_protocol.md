# Fresh validation protocol — M3 vs H4

Status: **pre-score freeze candidate**

## Baseline
M3 remains the fallback incumbent. The old 20-case development set is retired from correctness-based method selection.

## Fresh validation selection
Use only frozen TRAIN inputs. Exclude every case listed in `reports/development_export.json`.

For each workflow, rank eligible case IDs by:

```text
SHA256(
  "laya-score-validation-v1\n"
  + workflow_id
  + "\n"
  + case_id
)
```

Take the first 25 per workflow. Freeze all 100 IDs before any correctness inspection.

Run:

```bash
python -m benchmark.prepare
python scripts/select_fresh_validation.py
```

This writes:
- `artifacts/fresh_validation_100_model_inputs.json`
- `reports/fresh_validation_100_manifest.json`

No gold is exported by the selector.

## Frozen comparison arms

For each fresh case:
1. obtain/cache the boundary-fidelity choice specialist output;
2. obtain/cache the original-hybrid noul specialist output;
3. obtain/cache the exact archived M2 mixed-grouped score output.

These cached outputs form the M3 arm and are shared with H4 except where H4's score gate explicitly switches a score vector.

## H4 eligibility

For each M2 score vector:
- malformed -> preserve M2 / log invalid baseline input;
- exact maximum tie -> preserve M2;
- otherwise identify unique winner k;
- identify unique runner-up j;
- runner-up tie -> preserve M2;
- require |j-k| = 1 in canonical rubric order.

Only eligible score questions are added to `score_boundary_audit`.

Do not expose M2 probabilities or identify the incumbent winner to the referee.

## Sidecar input

```json
{
  "score_boundary_audit": {
    "version": "adjacent-evidence-v1",
    "comparisons": [
      {
        "question_id": "<original question ID>",
        "level_ids": [
          "<earlier canonical level ID>",
          "<later canonical level ID>"
        ]
      }
    ]
  }
}
```

The complete original mixed grouped input remains present.

## Referee prompt

Use the exact archived scored M2 prompt, unchanged, followed by two newlines and `prompts/h4_adjacent_evidence_delta_v1.txt`.

## Referee output audit

A valid audit record includes:
- original question ID;
- compared level IDs;
- exact target-question substring;
- preferred level or null;
- `preferred_requirements_complete`;
- nonempty necessary-condition records when preference is licensed;
- exact rubric substrings;
- statuses established / contradicted / unknown;
- exact state substrings supporting assessments.

## Deterministic H4 routing

For an eligible M2 score with winner k and runner-up j, replace M2 only if all hold:

1. exactly one valid audit matches the original question ID and compared level IDs;
2. target quotation is a nonempty exact substring of the original question;
3. licensed preference is j;
4. `preferred_requirements_complete == true`;
5. preferred-requirements list is nonempty;
6. every preferred requirement is marked necessary and established;
7. every preferred requirement has valid nonempty rubric and state quotations;
8. at least one necessary condition of k is marked contradicted, with valid nonempty rubric and state quotations;
9. referee score vector is valid and has a unique maximum at j.

If any condition fails, retain M2.

Further frozen behavior:
- original M2 maximum ties remain unchanged;
- referee ties retain M2;
- duplicate/missing/contradictory/malformed audit records retain M2;
- request failure retains M2 and is logged;
- no resampling because a valid response abstains;
- choice/noul remain the cached specialist outputs.

## Evaluation

Primary endpoint is paired fresh score-accuracy difference:

```text
(candidate correct scores - M3 correct scores) / number of fresh score decisions
```

Report:
- M3 score accuracy;
- H4 score accuracy;
- corrections;
- regressions;
- net change;
- eligible scores;
- actual switches;
- preserved M2 ties;
- invalid responses;
- abstentions;
- confirmation that choice/noul are identical between arms.

Use a stratified paired case bootstrap:
- resample whole cases within workflow;
- preserve all score decisions from each sampled case;
- 20,000 resamples;
- seed 20261004.

## Promotion rule

Promote H4 only if:
1. fresh score improvement >= 5 percentage points;
2. bootstrap 5th percentile of paired improvement > 0;
3. choice/noul are identical between arms;
4. all routing, fallback and selection rules were frozen before correctness was inspected.

If H4 fails or is inconclusive, retain M3. Do not revise H4 using this validation tranche.
