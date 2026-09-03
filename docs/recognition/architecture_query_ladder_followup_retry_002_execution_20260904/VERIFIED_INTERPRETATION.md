# Verified architecture query-ladder interpretation

Date: 2026-09-04
Status: verified one-host result; cross-machine replication still required

Retry 002 completed all 27,648 scheduled cells and the independent verifier found zero
semantic, schedule, source/artifact, or memory-field mismatches. Every q1/q4/q16/q64
cell returned the exact explicit residual-relation artifact.

## Task-time results

Values above 1.0 mean the candidate is faster than Python R2. Intervals are case-cluster
bootstrap intervals conditional on this one Linux/GCC host.

| q | arm | median task ms | speedup over R2 (95% CI) | case wins | minimum case |
|---:|---|---:|---:|---:|---:|
| 1 | `r2_topological_liveness` | 0.328 | 1.000 (reference) | — | 1.000 |
| 1 | `cm_ir_bigint` | 0.709 | 0.451 (0.437–0.465) | 0 | 0.327 |
| 1 | `cm_ir_words` | 0.820 | 0.394 (0.383–0.405) | 0 | 0.296 |
| 1 | `cse_flat_bigint` | 0.407 | 0.823 (0.816–0.831) | 0 | 0.762 |
| 1 | `cse_flat_words` | 0.503 | 0.663 (0.655–0.670) | 0 | 0.607 |
| 1 | `current_projection` | 0.536 | 0.618 (0.586–0.649) | 0 | 0.343 |
| 1 | `direct_bitset_restriction` | 0.346 | 0.837 (0.703–0.951) | 18 | 0.034 |
| 1 | `native_fused_slots` | 0.453 | 0.727 (0.705–0.751) | 0 | 0.598 |
| 4 | `r2_topological_liveness` | 0.519 | 1.000 (reference) | — | 1.000 |
| 4 | `cm_ir_bigint` | 0.898 | 0.562 (0.545–0.577) | 0 | 0.400 |
| 4 | `cm_ir_words` | 1.090 | 0.465 (0.452–0.480) | 0 | 0.330 |
| 4 | `cse_flat_bigint` | 0.580 | 0.898 (0.894–0.902) | 0 | 0.873 |
| 4 | `cse_flat_words` | 0.755 | 0.683 (0.675–0.692) | 0 | 0.615 |
| 4 | `current_projection` | 0.730 | 0.711 (0.680–0.741) | 0 | 0.423 |
| 4 | `direct_bitset_restriction` | 0.532 | 0.846 (0.711–0.964) | 18 | 0.032 |
| 4 | `native_fused_slots` | 0.612 | 0.819 (0.787–0.853) | 4 | 0.607 |
| 16 | `r2_topological_liveness` | 1.092 | 1.000 (reference) | — | 1.000 |
| 16 | `cm_ir_bigint` | 1.415 | 0.752 (0.740–0.763) | 0 | 0.641 |
| 16 | `cm_ir_words` | 1.803 | 0.587 (0.572–0.601) | 0 | 0.450 |
| 16 | `cse_flat_bigint` | 1.094 | 1.004 (1.000–1.009) | 27 | 0.978 |
| 16 | `cse_flat_words` | 1.474 | 0.733 (0.722–0.743) | 0 | 0.629 |
| 16 | `current_projection` | 1.222 | 0.831 (0.794–0.868) | 4 | 0.613 |
| 16 | `direct_bitset_restriction` | 1.106 | 0.864 (0.721–0.988) | 20 | 0.033 |
| 16 | `native_fused_slots` | 1.035 | 0.985 (0.928–1.046) | 37 | 0.621 |
| 64 | `r2_topological_liveness` | 3.166 | 1.000 (reference) | — | 1.000 |
| 64 | `cm_ir_bigint` | 3.154 | 0.969 (0.964–0.973) | 2 | 0.925 |
| 64 | `cm_ir_words` | 4.258 | 0.690 (0.674–0.705) | 0 | 0.556 |
| 64 | `cse_flat_bigint` | 2.872 | 1.100 (1.089–1.113) | 54 | 1.031 |
| 64 | `cse_flat_words` | 3.948 | 0.756 (0.740–0.769) | 0 | 0.638 |
| 64 | `current_projection` | 3.190 | 0.877 (0.815–0.936) | 17 | 0.521 |
| 64 | `direct_bitset_restriction` | 2.969 | 0.897 (0.756–1.030) | 40 | 0.030 |
| 64 | `native_fused_slots` | 2.581 | 1.049 (0.969–1.139) | 36 | 0.567 |

The first sampled native point above R2 is q64 by point estimate. No sampled point has a case-bootstrap lower bound above 1.0.
This is an observed four-point ladder, not an interpolated universal break-even threshold.

## Memory and isolation

All 27,648 rows have verified isolated-child RSS and lifecycle fields.
All had zero nonnegative incremental RSS (0 nonzero rows) because child peak RSS
was below the inherited parent baseline. Absolute peak RSS is descriptive for this host, but these
incremental measurements are not suitable for fitting a memory router.

Explicit cache cleanup consumed 0.23%
of retry task time, versus 83.05% for the invalid inherited-heap collection in attempt 001.
Full fork/IPC/exit lifecycle time is retained separately and is not used to rank backend task time.

## Decision boundary

This run permits a one-host q-ladder interpretation and descriptive host-memory reporting. It does not
permit selector fitting, neural claims, default routing changes, a website update, or a cross-machine claim.
The frozen native minimum-case 0.95 floor and all unfavorable cells remain visible. A separate physical-machine/compiler replication is still required before preparing public task-labelled sections.

## Execution

The retry Pod ran for 158.913 seconds at
$0.06/hour, with estimated compute cost
$0.002649. Combined estimated compute cost for
attempt 001 and retry 002 is $0.011583.
Controller cleanup and an independent post-run query both found empty v1/v2 inventories.
