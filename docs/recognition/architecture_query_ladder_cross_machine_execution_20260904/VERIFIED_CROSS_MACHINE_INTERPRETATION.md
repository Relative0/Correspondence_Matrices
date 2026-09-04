# Verified cross-machine query-ladder interpretation

Date: 2026-09-04
Status: exact separate-host/compiler replication complete

Both runs completed the same 27,648-cell frozen q1/q4/q16/q64 schedule. The
independent verifier found zero semantic, schedule, source/artifact, or memory-field
mismatches on both hosts, and the Clang result was reverified locally byte-for-byte.

The comparison uses within-host speedups over Python R2. Absolute timings are not
compared across unlike CPUs, and the host and compiler changed together, so their
individual causal effects cannot be separated.

| q | GCC/EPYC 9655 best fixed | Clang/EPYC 9575F best fixed | CSE-flat/R2, GCC → Clang | native/R2, GCC → Clang | native minimum, GCC → Clang |
|---:|---|---|---:|---:|---:|
| 1 | `r2_topological_liveness` | `r2_topological_liveness` | 0.823x → 0.820x | 0.727x → 0.721x | 0.598x → 0.600x |
| 4 | `r2_topological_liveness` | `r2_topological_liveness` | 0.898x → 0.897x | 0.819x → 0.805x | 0.607x → 0.605x |
| 16 | `cse_flat_bigint` | `r2_topological_liveness` | 1.004x → 0.995x | 0.985x → 0.961x | 0.621x → 0.603x |
| 64 | `cse_flat_bigint` | `cse_flat_bigint` | 1.100x → 1.090x | 1.049x → 1.026x | 0.567x → 0.549x |

## Interpretation

The best fixed arm agreed on three of four query counts. Python R2 remained the
best fixed arm at q1/q4 on both hosts, and CSE-flat bigint remained best at q64.
At q16, CSE-flat narrowly led on the GCC host but narrowly trailed R2 on the
Clang host, so q16 is a threshold-straddling sample rather than a portable
crossover. At q64, CSE-flat stayed faster than R2 on both hosts
(1.100x and 1.090x), won
54 and 54 of 54 cases, and
kept its minimum above 1.0 (1.031x and
1.013x).

Native q64 changed from 1.049x to
1.026x over R2, while its minimum changed from
0.567x to 0.549x.
The observed C36 cohort stayed favorable but the fresh cohort stayed unfavorable:
1.328x → 1.301x
versus 0.933x →
0.911x.
The complete JSON retains every arm, case-cluster interval, cohort split, and
unfavorable minimum. This supports a portable task map, not a universal native default.

The isolated-child incremental RSS field remained zero for every row on both hosts.
It therefore remains descriptive evidence and cannot calibrate a memory router.

## Boundary

The separate-host/compiler evidence gate is complete. This analysis does not fit a
selector, train a neural model, change production routing, or itself authorize a
website edit or publication. A public update must retain the historical Windows/MSVC
1.472x result and label these Linux task-specific results by host, compiler, and contract.

## Execution

The Clang replication used Pod `gv80d48w0afk3m` at
$0.07/hour and cost an estimated
$0.002916. The cumulative estimate for the
incomplete first ladder attempt, GCC retry, and Clang replication is
$0.014499.
Controller cleanup and the later independent inventory both found empty v1/v2 inventories.
