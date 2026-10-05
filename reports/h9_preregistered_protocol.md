# H9 preregistered protocol — agent-trace-only dual-referee routing

Status: frozen after H8 TRAIN scoring and before any H9 validation execution or H9 gold inspection.

## Motivation

H8 did not improve overall choice accuracy: baseline and H8 both scored 105/150.

However, H8's 15 frozen switches were highly heterogeneous by workflow:
- agent_trace_observability: +6 net choice corrections, 0 regressions;
- customer_service: -4 net;
- invoice_processing: -2 net;
- security_incidents: 0 net.

The strongest repeated transition was stop -> human_review in agent_trace_observability: 5/5 corrections on the H8 TRAIN tranche.

H9 tests whether the dual-referee mechanism is genuinely useful only inside agent_trace_observability, while retaining the frozen M3 choice specialist everywhere else.

This is a post-H8 hypothesis and MUST be validated only on a new fresh TRAIN tranche.

## Frozen H9 rule

For every choice question:
- if workflow != agent_trace_observability: retain frozen M3 choice answer exactly.
- if workflow == agent_trace_observability:
  - baseline supplies winner k and runner-up j;
  - referee A and referee B are two independent blinded runs on the exact same canonical top-two pair;
  - switch k -> j only if BOTH referees:
    1. are structurally valid;
    2. select j;
    3. have a unique probability maximum at j.
  - otherwise retain baseline exactly.

No label-specific rule is allowed.
No special-casing stop -> human_review is allowed.
No confidence threshold or probability margin is allowed.
No customer/invoice/security routing is allowed.

Noul and score remain byte-identical to baseline.

## Fresh H9 validation tranche

Use a fifth fresh TRAIN tranche.

Exclude:
- old dev20,
- H4 fresh100,
- H5 fresh100,
- H6 fresh100,
- H7/H8 fresh100.

Expected unique exclusions = 420 cases.

Select:
- 100 cases total,
- 25 per workflow,
- rank within workflow by:
  SHA256("laya-choice-h9-validation-v1\n" + workflow + "\n" + case_id)
- take first 25/workflow.

## Execution

1. Run frozen M3 choice baseline on all 100 fresh H9 cases.
2. Build blinded top-two referee inputs exactly as in H8.
3. Run referee A in fresh GPT-6.1 Sol sessions.
4. Run referee B independently in fresh GPT-6.1 Sol sessions.
5. Route only agent_trace_observability choice questions using the frozen H9 rule.
6. Freeze all outputs before H9 gold access.

## Evaluation

Primary:
- overall choice hard accuracy H9 vs baseline.

Secondary:
- agent_trace_observability choice accuracy;
- switch count;
- corrections;
- regressions;
- switch precision;
- per-workflow choice accuracy;
- paired case bootstrap stratified by workflow, 20,000 replicates, seed 20261005.

## Promotion gate

Promote H9 only if ALL:
1. overall choice improvement >= 3.0 pp;
2. corrections > regressions;
3. switch precision >= 70%;
4. agent_trace_observability improves by >= 8.0 pp;
5. customer_service, invoice_processing, and security_incidents outputs remain byte-identical to baseline;
6. paired bootstrap 5th percentile > 0;
7. noul/score byte-identical to baseline;
8. all predictions frozen before correctness inspection.

If H9 fails, retain M3 choice specialist and do not tune H9 on the same tranche.
