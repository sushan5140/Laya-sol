# H7 protocol — conservative top-two choice referee

Status: preregistered before H7 model execution and before correctness inspection on the H7 validation tranche.

## Motivation

The H6 postmortem found that the frozen M3 choice specialist was wrong on 49/150 choice decisions in the H6 tranche, and the gold label was already among the baseline top two labels in 41/49 of those errors. H6's global action-semantics rewrite caused too many regressions, especially in agent_trace_observability.

H7 therefore does NOT replace the baseline choice specialist. It keeps the frozen M3 choice output and allows a conservative second-pass referee to switch only between the baseline top two labels when the original rubric/state provide an explicit, auditable distinction.

## Hypothesis

H7 — conservative top-two choice boundary referee.

Most recoverable M3 choice errors are ranking errors between the top two candidate labels, not failures to surface the correct label at all. A blinded pairwise referee that sees only the original grouped case plus the two candidate option descriptions can correct some of these errors while a strict evidence license prevents broad regressions.

## No H6 global rewrite

H7 must not reuse the H6 action-semantics delta as a replacement prompt. The frozen M3 choice specialist remains the baseline generator.

## Referee input construction

For every choice question in the fresh H7 tranche:

1. Run the frozen M3 choice specialist first.
2. Require a valid probability distribution with a unique maximum and a unique runner-up.
3. Take the top-two option labels and their exact original option descriptions.
4. Canonicalize pair presentation by original option order, NOT by baseline rank.
5. Do NOT expose:
   - baseline winner identity,
   - baseline probabilities,
   - rank ordering,
   - gold,
   - correctness,
   - prior H6 outputs.
6. Preserve the complete original mixed grouped case.

Referee sidecar shape:

```json
{
  "choice_boundary_audit": {
    "version": "top-two-evidence-v1",
    "comparisons": [{
      "question_id": "<original qid>",
      "option_labels": ["<earlier original option>", "<later original option>"],
      "option_descriptions": {
        "<label1>": "<exact original description>",
        "<label2>": "<exact original description>"
      }
    }]
  }
}
```

## Frozen H7 referee instruction

For each comparison, use only the original state, question, and the two exact option descriptions.

Identify the smallest explicit factual distinction that separates the two candidate options for this question. Preserve qualifiers, scope, conjunctions, exclusions, and temporal wording literally.

For each candidate option:
- list the explicit facts that must be true for that option to fit better than the other candidate;
- mark each fact as established, contradicted, or unknown from the supplied state;
- quote the exact state text supporting each established or contradicted assessment.

Return a licensed preference only when:
1. the preferred option has at least one explicit distinguishing condition established by the state;
2. the competing option has at least one explicit distinguishing condition contradicted by the state OR the preferred option is strictly more specific and every additional explicit condition it requires is established;
3. the preference does not rely on missing information, possibility, generic caution, or assumptions outside the supplied state.

If those requirements are not met, return no licensed preference.

Return the ordinary grouped response plus the structured boundary audit in the supplied schema.

## Frozen router

For each eligible choice question:
- baseline answer = frozen M3 choice answer.
- referee may switch only between the baseline top two labels.
- switch from baseline winner k to runner-up j only if ALL are true:
  1. exactly one valid audit matches the qid and top-two pair;
  2. referee returns licensed_preference = j;
  3. preferred distinguishing conditions list is nonempty;
  4. every preferred distinguishing condition is marked established and has a nonempty exact state quote;
  5. either:
     a. at least one distinguishing condition for k is marked contradicted with a nonempty exact state quote; OR
     b. referee marks j as strictly_more_specific = true and every additional explicit condition for j is established;
  6. referee ordinary choice distribution is valid and has unique maximum at j.
- otherwise retain baseline exactly.
- ties, malformed outputs, missing audits, abstentions, ambiguous pairs, or request failures retain baseline.
- noul and score are copied byte-identically from the frozen baseline routing.

No confidence threshold, workflow-specific rule, label-specific rule, case-specific exception, retry-selection, or post-gold tuning is allowed.

## Fresh TRAIN validation tranche

Use a fourth fresh TRAIN tranche only.

Exclude:
- old dev20,
- H4 fresh100,
- H5 fresh100,
- H6 fresh100.

Expected unique exclusions = 320 cases total.

Select:
- 100 cases total,
- 25 per workflow,
- rank within workflow by:
  SHA256("laya-choice-h7-validation-v1\n" + workflow + "\n" + case_id)
- take first 25/workflow.

## Evaluation

Primary endpoint:
- choice hard accuracy, H7 routed output vs frozen M3 choice baseline.

Secondary:
- corrections,
- regressions,
- switch precision,
- per-workflow choice accuracy,
- agent_trace_observability choice accuracy.

Bootstrap:
- paired case bootstrap stratified by workflow,
- 20,000 replicates,
- seed 20261004.

## Promotion gate

Promote H7 only if ALL:
1. overall choice improvement >= 3.0 percentage points;
2. corrections > regressions;
3. switch precision >= 60%;
4. agent_trace_observability choice does not regress;
5. paired bootstrap 5th percentile > 0;
6. noul and score outputs are byte-identical to frozen baseline routing;
7. all baseline/referee/routed outputs are frozen before correctness inspection.

If H7 fails or is inconclusive, retain the M3 choice specialist and do not tune H7 on the same tranche.
