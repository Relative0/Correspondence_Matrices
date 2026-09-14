# Historical SymPy audit

An archived file contains substantial differences in the recorded timers. These are historical observations with unlike output contracts, not a contemporary matched-task speed comparison.

Input: [bench_robdd_cm_balanced_all_vars_raw.csv](C:/Users/brian/Documents/CM_Computation/bench_robdd_cm_balanced_all_vars_raw.csv); SHA-256 `c4b2a5748b16d3e5edc69d0ea961c17d2aeb8148ef0b76bc11fc4b382d6fae3c`.

| Nominal variables | Paired rows | Median recorded SymPy time / CM time | Range | Recorded correctness flags |
| ---: | ---: | ---: | ---: | --- |

| 4 | 5 | 5.453 | 2.900–6.437 | both true |

| 8 | 5 | 76.047 | 21.118–195.344 | both true |

| 12 | 5 | 1.638 | 1.516–1.861 | both true |

| 16 | 5 | 1.384 | 0.869–1.665 | both true |


The inspected [adapter](C:/Users/brian/Documents/CM_Computation/expr_simplify.py:39) calls `simplify_logic(..., form='dnf')` with default `force=False`. The [timer](C:/Users/brian/Documents/CM_Computation/cm_bench.py:2239) ends before lambdify, assignment-grid evaluation and truth-vector validation. CM construction and symbolic simplification are different requested outputs. [SymPy's documentation](https://docs.sympy.org/latest/modules/logic.html#sympy.logic.boolalg.simplify_logic) describes the eight-variable default restriction; above it the same call does not perform the same exhaustive simplification. The archive's sharp n8/n12 change is consistent with that mechanism, but historical version binding has not been independently reconstructed.


The [August gap audit](C:/Users/brian/Documents/CM_Computation/CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md:639) criticized these comparator choices. That document is evidence about past interpretation, not an instruction to exclude fair SymPy experiments now. Y02–Y06 propose new task-matched comparisons. No claim that SymPy cannot be used in production is supported here.


The [July V3 audit](C:/Users/brian/Documents/CM_Computation/CM_AUDIT_V3_2026-07-23.md:183) also found an n32 example with semantic support 16. Its ambient-output timing survived, but its all-live interpretation did not. The new scale protocol separately records ambient variables, syntactic support, proved semantic support and output width.
