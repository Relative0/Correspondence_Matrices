# Learning Milestone C21: task-matched exact GF(2) method table

**Date:** 2026-08-31  
**Status:** retrospective seven-method table independently verified; production promotion refused

## Task contract and corpus

C21 compares methods only when they deliver the same requested computation: the deterministic
best exact CM/GF(2) decomposition artifact. A valid reconstructed factor was not accepted as a
substitute for the global best. Proposal methods therefore retained screened exact completion over
the complete bounded partition set, and their internal reconstruction and completion checks were
charged. The independent exhaustive oracle comparison remained outside the timed span.

The common method input was a canonical expression DAG derived from each frozen C19 LogikBench
cone. The C21 freezer reparsed 51 BLIF files and materialized 96 expression inputs at support 3-6.
An independent verifier reproduced every expression, support, truth vector, and source record with
zero mismatches. C21 did not select cases by timing and did not refit the C19 policy. Because the
C19 corpus had already been inspected, this table is retrospective rather than fresh confirmation.

Each method ran five balanced fresh-engine, single-query rounds:

1. exhaustive CM;
2. screened CM;
3. the compiled frozen C19 screened leaf;
4. an exact truth-ANF interaction min-cut followed by screened completion;
5. packed source-ANF truth construction and exact component proposal followed by screened completion;
6. a fresh fixed-order ROBDD level cut followed by screened completion; and
7. a sound source-interaction cut followed by screened completion.

## Exact task-matched results

All 3,360 timed executions delivered the same exhaustive-best artifact and passed reconstruction.
The table reports sums of per-case median whole-task times.

| Method | Aggregate vs exhaustive | Aggregate vs screened | Median case vs exhaustive | Minimum case vs exhaustive |
|---|---:|---:|---:|---:|
| Source packed ANF | **3.0071x** | **1.0064x** | **2.0349x** | **1.0438x** |
| Compiled screened CM | 3.0006x | 1.0042x | 1.8916x | 0.9553x |
| Screened CM | 2.9881x | 1.0000x | 1.7821x | 0.9821x |
| Truth-ANF min-cut | 2.9508x | 0.9875x | 1.9564x | 0.8412x |
| Source-interaction cut | 2.9073x | 0.9730x | 1.8121x | 0.9059x |
| Exhaustive CM | 1.0000x | 0.3347x | 1.0000x | 1.0000x |
| Fresh ROBDD level cut | 0.7116x | 0.2382x | 0.2816x | 0.0316x |

Packed source ANF was the fastest fixed method. Its advantage over screened CM was only 0.64%, so
the two are effectively close on this machine. The useful distinction is where the time came from:
packed source ANF constructed the exact truth vector directly from the source DAG without first
deserializing an expression and running the ordinary reference evaluator. Its component proposal
was available on only 10 of 96 cases; 86 cases abstained and still completed exactly. The result is
therefore evidence for an alternate exact representation path, not evidence that proposal routing
usually pruned the CM search.

The sound source-interaction graph was connected on all 96 cases and abstained every time. The
truth-ANF min-cut always produced a priority cut but added 2.7% over screened CM in aggregate. Since
screened completion evaluates every exact descriptor and globally orders them, a priority proposal
cannot currently remove the remaining work; it mainly adds proposal cost.

The fresh ROBDD arm is a negative result for this lifecycle. Its per-case cleanup contract calls
garbage collection and dominated the measured path: 1.542 seconds of the 2.115-second sum of
per-case medians. This does not reject resident BDD sessions for repeated queries, but it shows that
a fresh BDD proposal is not competitive for a single decomposition request.

## Support-width and routing headroom

| Support | Cases | Best aggregate method | Speedup over exhaustive |
|---|---:|---|---:|
| `n=3` | 9 | Source packed ANF | **1.303x** |
| `n=4` | 36 | Source packed ANF | **1.540x** |
| `n=5` | 16 | Source packed ANF | **2.535x** |
| `n=6` | 35 | Compiled screened CM | **3.313x** |

Source packed ANF was the per-case winner 49 times; direct screened CM and compiled screened CM
won 16 each, truth-ANF min-cut won nine, and the source-interaction control won six. A post-hoc
width rule choosing source packed ANF for `n<=5` and compiled screened CM for `n=6` would improve
only 1.47% over the best fixed method. The unattainable per-case timing oracle is 5.88% faster than
the best fixed method, leaving 4.35% after that width rule before charging any router. This is weak
headroom for another neural policy and does not justify training yet.

## Memory diagnostic

A separate `tracemalloc` pass covered three cases per support width for every method. Median peak
Python allocations were 34,411 bytes for source packed ANF, 36,190 for screened CM, 35,910 for
compiled screened CM, 47,233 for ROBDD, and 66,829 for exhaustive CM. These are diagnostic Python
allocation peaks, not resident-set measurements.

## Verification and decision

The independent verifier replayed all 96 exhaustive oracles, checked all 96 task contracts, all
3,360 timing rows, all 84 memory rows, four source and eight artifact fingerprints, and recomputed
the summary. It found zero semantic or artifact mismatches.

C21 answers the immediate comparison question: screened CM remains about 3x faster than exhaustive
CM end to end, and packed source ANF is the strongest fixed exact input path by a narrow margin.
BDD and structural/ANF proposals do not presently beat the strongest cheap exact controls under a
fresh single-query lifecycle. The next implementation should add packed source ANF as an opt-in
exact representation arm with screened/exhaustive fallback, then freeze a new source family and
repeat the unchanged table on a second machine. Production promotion remains false.

## Evidence

- Dataset: `docs/recognition/c21_decomposition_table_dataset.json`
- Dataset replay: `docs/recognition/c21_decomposition_table_dataset_verification.json`
- Run: `docs/recognition/runs/c21-task-matched-gf2-table-windows-20260831-001`
- Independent run verification: `docs/recognition/runs/c21-task-matched-gf2-table-windows-20260831-001/independent_verification.json`
- Machine summary: `docs/recognition/learning_milestone_c21_task_matched_gf2_method_table_results.json`

