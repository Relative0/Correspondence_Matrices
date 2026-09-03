# Architecture comparison retry 002 — verified interpretation

Date: 2026-09-03  
Scope: exact non-neural CM-family comparisons on Linux/GCC  
Status: **verified complete; no routing, selector, training, website, or publication change**

## Outcome

The independent verifier accepted all 19,646 scheduled rows with zero semantic, schedule, source, or artifact mismatches. The single RunPod was deleted; both final inventories were empty. Estimated compute cost was $0.003092.

Speedups below use paired accounted-total time, cluster by frozen case, and show a deterministic case-cluster bootstrap 95% interval. They are conditional on this one execution host.

## Lane A — complete explicit relation

| Candidate | Speedup over dense CM | Speedup over current direct BitSet | Median total |
|---|---:|---:|---:|
| `cm_dense_full_reinflation` | 1.000x | 0.883x | 4.108 ms |
| `cm_packed_bigint` | 1.049x | 0.926x | 3.909 ms |
| `cm_packed_words` | 1.033x | 0.912x | 3.966 ms |
| `cm_hybrid_no_reinflate` | 1.008x | 0.889x | 4.083 ms |
| `cm_ir_recursive_packed` | 1.053x | 0.930x | 3.874 ms |
| `structural_cse_flat` | 1.111x | 0.980x | 3.671 ms |
| `raw_flat` | 1.124x | 0.992x | 3.621 ms |
| `direct_expression_bitset` | 1.133x | 1.000x | 3.570 ms |

The current direct-expression BitSet was faster than the best fixed CM-family arm (`cm_ir_recursive_packed`) in all 78 runnable cases. The CM arm's speedup over BitSet was 0.930x [0.922x, 0.937x]; values below 1 mean it remained slower. The same CM arm was 1.053x faster than dense CM, so the packed/recursive architecture is useful but is not the complete-vector winner.

## Lane B — repeated restrictions

| Candidate | Speedup over R2 | Speedup over projection | Median total |
|---|---:|---:|---:|
| `r2_topological_liveness` | 1.000x | 1.034x | 7.308 ms |
| `cm_ir_bigint` | 1.003x | 1.038x | 7.314 ms |
| `cm_ir_words` | 0.842x | 0.871x | 8.590 ms |
| `cse_flat_bigint` | 1.050x | 1.086x | 6.937 ms |
| `cse_flat_words` | 0.883x | 0.913x | 8.260 ms |
| `current_projection` | 0.967x | 1.000x | 7.396 ms |
| `direct_bitset_restriction` | 0.905x | 0.936x | 7.184 ms |
| `native_fused_slots` | 1.055x | 1.091x | 6.730 ms |

Native fused slots were 1.055x [1.017x, 1.095x] over R2 overall and 1.179x on the 18-case observed C36 cohort, but only 0.997x on the 36 fresh cases. The minimum case was 0.812x (`fresh-tree-andor-k8-r1`), below the frozen 0.95 floor. Native therefore remains guarded/opt-in.

This run does **not** establish q1/q4/q16 break-even points. Every timed Lane B row executes q64; q1/q4/q16 are prefix correctness digests, not separately timed cells. A corrected follow-up freeze is required before making query-count crossover claims.

## Lane C — related multi-root outputs

- Python sharing-aware union versus separate roots: 1.147x [1.127x, 1.167x]; all 12 cases favored union.
- Native union versus separate arenas: 1.238x [1.209x, 1.264x]; all 12 cases favored union.
- Native union versus Python union: 1.003x [0.953x, 1.047x]. The aggregate was near parity and the fresh width-8 cases regressed, so the supported conclusion is union sharing, not unconditional native superiority.

## Lane D — smaller task-specific queries

| Task / lifecycle | Fastest fixed backend | Speedup over CM |
|---|---|---:|
| `equivalence_delta/fresh_engine` | `cnf/fresh_engine` | 8.239x |
| `equivalence_delta/resident_engine` | `cnf/resident_engine` | 13.214x |
| `exact_count/fresh_engine` | `cnf/fresh_engine` | 8.023x |
| `exact_count/resident_engine` | `cnf/resident_engine` | 15.543x |
| `partial_context/fresh_engine` | `sat/fresh_engine` | 16.232x |
| `partial_context/resident_engine` | `sat/resident_engine` | 15.526x |
| `sat_status/fresh_engine` | `sat/fresh_engine` | 14.699x |
| `sat_status/resident_engine` | `sat/resident_engine` | 13.266x |
| `version_history/fresh_engine` | `sat/fresh_engine` | 14.809x |
| `version_history/resident_engine` | `sat/resident_engine` | 13.093x |
| `witness/fresh_engine` | `cnf/fresh_engine` | 5.380x |
| `witness/resident_engine` | `cnf/resident_engine` | 3.923x |
| `structural_reload` | `cnf` | 2.200x |

The task-matched controls win these bounded smaller-query lanes. CM remains useful as an exact diagnostic/reference representation, not a universal replacement for CNF/CSE/SAT task paths.

## Limits and next boundary

- Per-row RSS is the process-wide `ru_maxrss` high-water mark and is nondecreasing through the run; it cannot support per-arm memory routing or memory-win claims.
- The result is one verified Linux/GCC host execution. The freeze still requires a separate cross-machine replication before public cross-machine claims.
- No selector was fitted and no neural conclusion is permitted. The q64 native result itself contains case-specific regressions, while the previously exposed C36-only portfolio had no useful selector headroom.
- Before any `expert.html` update, freeze and run separately timed q1/q4/q16/q64 cells and add per-cell memory measurement if memory comparisons are intended. Retain the historical Windows-only 1.472x result unchanged and label any new section by task, source freeze, platform, and date.
