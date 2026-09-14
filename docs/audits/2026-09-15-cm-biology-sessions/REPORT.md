# Matched biology session implementation and local pilot

The raw-BNet/CM session runner is implemented and validated. The development pilot completed **288 sessions in 189.50 seconds**: **255 successful, three scalar-oracle timeouts, 30 explicit width refusals, and zero exact-output disagreements**. The primary q64 retained-state CM/raw ratio was **1.0025** by family-weighted geometric mean. This provides no 5% development gain signal and does not pass—or qualify for—the heldout acceptance gate. No paid scaling is justified by these results.

## Implementation

`cmbench/biology_sessions.py` implements direct raw BNet AST-to-FlatProgram compilation and an independent prepared CM path. The matched CM path uses CMIRBuilder's interning primitive without algebraic rewriting; the canonical CM ablation uses its normal rewriting methods. Both lower through the same general postorder/common-subexpression normalization and identical FactorizedCountPlan evaluator. The raw path never constructs a CM node. The use of the internal CMIRBuilder primitive is deliberate, tested and source-bound; changes to that internal contract require renewed verification.

Per-equation roots are retained. Clamps omit the selected target equations and fix those target values; conditions retain the equations. Preparation builds plans for the scheduled clamp-target sets before the retained query loop. Rebuild mode releases the previous prepared object before constructing its replacement and charges reconstruction inside each query. Exact counts and full witnesses are returned; witnesses are recovered by the selected evaluator's self-reduction and checked against the original perturbed BNet equations.

The packed arm lowers through CM and explicitly evaluates a packed truth set, bounded by its live variable width. It does not build an unused factorized plan. It remains exponential and is distinct from prepared CM IR. The pilot also includes the explicit scalar oracle and native CaDiCaL enumeration controls. Previously validated AEON/d4/Ganak/CryptoMiniSat controls are preserved in the September 14 audit; they are not falsely reported as newly timed arms in this session pilot.

`cmbench/biology_session_supervisor.py` uses Windows Job Objects. Hard aggregate committed-memory limits, kill-on-close and one allowed CPU's affinity are configured before a suspended child is assigned and resumed. Descendants share the job. Output is bounded while being read; deadlines terminate only the owned job. Whole-job CPU and peak committed memory are recorded, with verified zero active processes after every session. This is **committed memory, not RSS**; Windows' peak accounting can include denied allocation attempts. Unsupported platforms fail without launching a worker. No dependency installation or solver substitution was needed.

## Frozen pilot and coverage

`pilot-002/PLAN.json` binds the executed sources, corpus and frozen query schedules. It selects all 12 development-partition models and eight variants at q1/q8/q64, one repetition each: raw and matched CM, retained and rebuilt; canonical CM retained; explicit packed CM; scalar oracle; CaDiCaL enumeration. The source snapshot under `pilot-002/source/` matches all 13 executed-source digests. Each session has a 10-second deadline, a 1-GiB job limit and a 1-MiB combined output limit; the campaign has a 900-second global ceiling. Arm order is deterministically rotated and recorded, but a single repetition is not a fully counterbalanced experiment.

All 22 closed models are present in the coverage manifest. The seven train and three heldout-candidate models were not performance-timed in this development pilot. Their prior correctness validation is retained; their normalized raw/matched CM program identities were also checked during review. One development model is unsupported by the matched/packed paths, leaving **11 paired models in 10 conservative families** for each successful comparison. Native/scalar caps cause additional refusals. The 30 refused sessions involve models 174 and 199; exact reasons remain in the ledger. Model 199's refusal is not silently removed from population coverage.

The three timeouts are scalar q64 sessions on models 057, 058 and 208. Timeout rows have null outputs, not count zero, and are excluded from completed timing ratios while retained in outcome accounting. All 288 jobs passed cleanup verification. The 255 successful sessions produced **6,086 exact query outputs** and **5,253 validated positive witnesses**. These are checks/measurements, not independent biological datasets. The maximum reported job committed-memory peak was 410,521,600 bytes, within the configured limit.

`pilot-001/PLAN.json` was prepared but never executed. A pre-execution contract check identified that non-plan control arms needed null plan identities, so a successor plan was frozen. No ledger or run was created in pilot-001; it is retained for traceability, not counted as a campaign.

## Performance interpretation

Ratios below one favor CM. These are descriptive single-repetition development results, not confidence intervals or generalization claims.

| Variant | q | Equal-family total-session ratio | Ratio of summed total-session costs |
|---|---:|---:|---:|
| Matched, retained | 1 | 1.0270 | 0.9880 |
| Matched, retained | 8 | 1.0279 | 1.0587 |
| **Matched, retained (primary)** | **64** | **1.0025** | **1.0132** |
| Matched, rebuilt | 64 | 1.0092 | 0.9867 |
| Canonical CM, retained | 64 | 1.0127 | 1.0247 |

Every completed matched pair has identical ordered query-plan hashes, so the warm evaluation algorithm is identical. Differences concern ingress/preparation, retained structure and measurement/cache variation; they do not isolate a new CM warm algorithm. The canonical CM plans differ in all 11 paired models and are explicitly classified as preprocessing/topology confounded. The raw arm would need the same general simplifications before any canonical-path advantage could be attributed to representation.

Primary total-session cost is supervisor-observed wall time, including interpreter startup, worker imports, request parsing, output serialization and shutdown. Worker phase timers are also retained. Startup overhead is substantial: on matched retained q64, the ratio of summed **worker-only** costs is 1.2255, compared with 1.0132 for caller-observed totals. Excluding startup therefore does not reveal a CM gain in this pilot. This sensitivity is a different estimand, not a replacement chosen to obtain a desired answer.

`timing_seconds.warm_queries` denotes the query-loop interval. For rebuild mode it includes reconstruction; `query_timings_seconds.rebuild_preparation` exposes that component. It must not be described as pure warm evaluation in a rebuild comparison. Retained preparation includes building plans, while first mask materialization remains charged to the query that uses it. Per-query count and witness-validation times are also recorded.

`cmbench/biology_session_analysis.py` validates rows and identities, rejects duplicate measurements, detects exact-output disagreement, retains unsupported/censored/unpaired cells and summarizes within-instance repetitions before family weighting. It withholds 95% acceptance intervals for this exposed pilot. Neither its ten assumed independent families nor future repetition counts create a pristine heldout cohort.

## Reporting correction and custody

The first executed worker mistakenly labeled successful scalar/CaDiCaL preprocessing with the common factorized-normalization string. This was metadata only. `REPORTING_ADDENDUM.json` records **57 label corrections** and both ledger hashes. `REPORTING_CORRECTED_LEDGER.jsonl` changes only the preprocessing label and its mechanism-attribution counterpart; exact outputs, witnesses, phases, resources and every other field are identical. The original measured ledger and executed source snapshot remain unchanged. Current worker source fixes the labels and has regression tests. `ANALYSIS.json` and `SUMMARY.json` consume the additive corrected view.

## Verification and next disposition

Final relevant suite: **232 passed, two historical-input skips**, 13.21 seconds. The new surface contributes 58 tests, including Windows hard-limit/descendant-cleanup tests and end-to-end real-worker execution. The prior attribution manifest still verifies unchanged: 85 manifest entries, 40 claim artifacts and 47 statistical sources. No tracked historical file was edited. See `TEST_RESULTS.md` and the delivery manifest for exact commands and hashes.

`NEXT_LOCAL_PLAN.json` freezes a feasible **396-session, 22-model, three-repetition matched retained** replication design with the same source/query bindings, hard limits and 15-minute ceiling. It is **deferred**, not executed: the pilot supplied no development signal and identical warm plans offer no distinct mechanism to confirm. Its all-model extrapolation is uncertain; budget exhaustion must retain explicit not-run cells. This plan is not a paid quote, cloud authorization or heldout acceptance study.

The authorized implementation, correctness checks, pilot, analysis and next-plan preparation are complete. Stop performance scaling here. Revisit in this task only if a concrete representation/preparation mechanism is proposed or an explicit replication is requested; the preserved decisions and evidence avoid restarting discovery. No additional model run or paid compute is currently warranted.

`PORTFOLIO_DISPOSITION.md` maps all 80 families from the September 13 research catalog to completed evidence, conditional triggers and deferred work. The catalog was a research menu rather than an execution checklist. Its blanket 2,400-case cloud target is superseded by the bounded core results. A separate local, task-matched SymPy Y02–Y05 study is the only generally worthwhile next benchmark; it would clean up the historical unlike-task claim and is not needed for the present CM no-go conclusion.
