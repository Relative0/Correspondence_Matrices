# Phase 5B benchmark results

The maintained-tool pilot completed **2,100 principal trials**: 70 generated CNFs x ten methods x three repetitions. Train/validation/held-out counts are 600/600/900 trials, representing 20/20/30 instances. Successful semantic and simultaneous partitions agree with the independent model/projection baseline; total failures/timeouts: **0**. No inputs or objective weights were changed from held-out results.

Validation selected **B3**, saved before held-out execution. Primary challenger M5 has paired geometric total-runtime ratio **2.212**, with descriptive paired-instance bootstrap interval **[2.008, 2.428]**. A ratio above one is slower. Its runtime criterion is **FAIL** and separately preregistered practical residual-work rescue is **FAIL**. O is an oracle control, never an algorithmic competitor.

| Method | Median total ms | Mean total ms | IQR ms | Paired geo ratio vs B3 | 95% descriptive interval | Wins / losses | Median SAT calls incl. probes | Failures |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| B0 | 42.452 | 42.353 | 9.621 | 1.091 | [1.013, 1.172] | 10 / 20 | 22.0 | 0 |
| B1 | 37.612 | 41.024 | 11.105 | 1.058 | [0.987, 1.138] | 14 / 16 | 22.0 | 0 |
| B2 | 38.768 | 40.520 | 11.205 | 1.044 | [0.982, 1.112] | 13 / 17 | 16.0 | 0 |
| B3 | 36.668 | 38.800 | 7.225 | 1.000 | [1.000, 1.000] | 0 / 0 | 12.0 | 0 |
| M1 | 88.416 | 89.442 | 14.396 | 2.320 | [2.188, 2.463] | 0 / 30 | 12.0 | 0 |
| M2 | 78.894 | 83.189 | 33.187 | 2.107 | [1.917, 2.329] | 0 / 30 | 12.0 | 0 |
| M3 | 80.979 | 80.940 | 25.272 | 2.067 | [1.885, 2.262] | 0 / 30 | 12.0 | 0 |
| M4 | 86.284 | 87.486 | 30.263 | 2.217 | [2.016, 2.425] | 0 / 30 | 23.0 | 0 |
| M5 | 88.471 | 87.501 | 33.236 | 2.212 | [2.008, 2.428] | 0 / 30 | 23.0 | 0 |
| O | 39.111 | 40.807 | 6.657 | 1.050 | [0.988, 1.122] | 12 / 18 | 5.0 | 0 |


The runtime summaries use per-instance medians over three trials before aggregation. SAT-call columns summarize completed raw trials and include probe calls, so they do not conceal defect preprocessing. The paired machine-readable CSV gives every per-instance comparison. Raw JSONL retains tree search, real SDD sizes, partitions, SAT counters, memory and move traces. No conflict/propagation number is an estimate from encoding size.

## Primary family strata

| Family | Held-out instances | Median M5/B3 ratio | M5 faster instances |
|---|---:|---:|---:|
| bounded_treewidth | 3 | 2.443 | 0 |
| carrier_aligned | 3 | 1.644 | 0 |
| carrier_crossing | 3 | 2.117 | 0 |
| clean_factorable | 3 | 1.742 | 0 |
| indecomposable | 3 | 2.273 | 0 |
| partially_factorable | 3 | 2.389 | 0 |
| random_cnf | 3 | 1.712 | 0 |
| read_once | 3 | 1.971 | 0 |
| redundant_cross | 3 | 2.706 | 0 |
| repeated_module | 3 | 2.412 | 0 |

These are descriptive strata, not a second selection criterion. Each family has n=6,8,10 instances. Many are relabelled copies or size extensions of the same simple module structures present in train/validation; this is not a test of generalization to unseen industrial structures. The random family has independent planted clause draws. Read-once and repeated-module cases cover restricted explicit CNF constructions, not arbitrary operator DAGs.

## Scope and negative boundaries

Real PySDD/Glucose measurements close the tooling gap. They do not close the scale/baseline gap. M searches recompile every candidate, whereas B2 has native dynamic minimization; B3 is a component/min-fill-order balanced construction. The fixed first-six-neighbor policy may miss beneficial moves. These costs and limitations belong to the tested implementation. A negative result does not refute every possible exposure/defect objective or native implementation.

Public documentation CNFs are reported separately in `data/public_control_results.json`; they are public smoke controls, not an industrial benchmark corpus. Separate move diagnostics measure size/exposure/residual-cost tradeoffs after primary timing. The training-only SAT reuse experiment compares actual solver persistence and fresh encodings. Neither supplementary experiment changes the primary decision.

## Completed supplementary diagnostics

All 10,440 move occurrences are covered; 174 measured residual states agree exactly. The separate SAT reuse comparison completes 180 runs/14,220 cut checks with zero discrepancies. Persistent/fresh-same-base paired geometric time ratio is 0.124832. These post-campaign diagnostics and three public smoke checks do not change the primary NO-GO. See SUPPLEMENTARY_DIAGNOSTICS.md.
