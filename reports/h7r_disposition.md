# H7R disposition — failed without gold scoring

H7R is rejected by an impossibility bound before any TRAIN-gold access.

Execution audit facts:
- frozen H7 baseline reused unchanged;
- 137 eligible choice comparisons;
- strict frozen router licensed 0 switches;
- routed output contains 100 cases / 500 grouped decisions;
- all 350 noul/score answers are byte-identical to baseline;
- no gold, evaluator, scoring, or tuning occurred.

Because the router made 0 choice switches, every routed choice answer is identical to the frozen baseline choice answer. Therefore H7R's choice hard accuracy must be exactly equal to baseline accuracy on this tranche, regardless of gold.

The preregistered H7 promotion gate requires:
1. overall choice improvement >= 3.0 percentage points;
2. corrections > regressions;
3. switch precision >= 60%;
4. agent_trace_observability does not regress;
5. paired bootstrap 5th percentile > 0;
6. noul/score byte-identical;
7. outputs frozen before correctness inspection.

With 0 switches:
- overall choice improvement is exactly 0.0 pp;
- corrections = 0;
- regressions = 0;
- bootstrap paired improvement is identically 0 for every resample;
- gates 1, 2, and 5 necessarily fail.

Accordingly:
- do NOT access H7 TRAIN gold;
- do NOT run the evaluator;
- retain M3 choice specialist;
- preserve this fourth fresh TRAIN tranche as unopened-gold evidence.

Final disposition:

H7R FAILED BY ZERO-SWITCH IMPOSSIBILITY; RETAIN M3 CHOICE SPECIALIST
