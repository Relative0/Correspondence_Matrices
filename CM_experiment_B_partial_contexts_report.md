# CM Experiment B: Partial Contexts

## 1. Executive Summary

Experiment B is implemented as `--bench-partial-contexts`. It generates one base expression per trial, then evaluates many fixed-variable contexts over either the remaining variables or full variables.

Measured on the autoref run (`bench_partial_contexts_autoref_summary.csv`, 100 sliding-window contexts, 5 trials):

- CM cached partial evaluation saved time versus CM no-cache: 4.39x at n=8, 3.87x at n=12, and 2.05x at n=16.
- CM did exploit live-variable reduction: the median live-variable counts matched the requested 50% remaining variables.
- ROBDD build-once/restrict was faster than cached CM for these sizes.
- Bitset full recompute was also faster than cached CM at n<=16.

Final verdict: `CM benefit depends on context reuse/live-variable reduction`.

## 2. Audit

| Capability | Present / Missing | Evidence | Plan |
|---|---|---|---|
| Bitset expression evaluation | Present | `bitset_backend.eval_expr_bitset` | Reused for full recompute baseline; added fixed-context helper for restricted baseline. |
| CM no-reinflate fixed variables | Present | `materialize_hybrid_no_reinflate(..., fixed=...)` | Used for each context. |
| Compiled CM IR reuse | Present | `compile_expr`, `compile_expr_to_cm_ir`, `evaluate_compiled` | Used to compile once for cached partial contexts. |
| Persistent structural cache | Present | `clear_cm_ir_persistent_cache`, `cm_ir_persistent_cache_stats` | Used for cached CM diagnostics. |
| ROBDD restriction | Present | `manager.let(...)`, `bdd_function_value(...)` | Added build-once/restrict workload. |
| Correctness helpers | Present | `result_value_for_assignment`, `sampled_correctness_check` | Added exact small-n partial references and sampled large-n checks. |
| Partial-context CLI mode | Added | `--bench-partial-contexts` | New mode writes raw/summary CSVs. |

## 3. Benchmark Semantics

Each trial generates one base Boolean expression. The benchmark then generates fixed-variable contexts, evaluates the same expression under each context, and records separate timings for:

- bitset full recompute,
- bitset restricted evaluation,
- CM no-reinflate without persistent cache,
- CM no-reinflate with compiled IR and persistent cache,
- ROBDD/autoref build-once plus per-context restriction.

The autoref run used `remaining-vars`, so outputs are truth tables over variables not fixed by the context.

## 4. Context Diagnostics

| n | contexts | fixed fraction | remaining vars median | context style | overlap ratio |
|---:|---:|---:|---:|---|---:|
| 8 | 100 | 0.50 | 4 | sliding_window | 0.600 |
| 12 | 100 | 0.50 | 6 | sliding_window | 0.714 |
| 16 | 100 | 0.50 | 8 | sliding_window | 0.778 |

## 5. Main Results

| n | contexts | bitset total | cm no-cache total | cm cache total | ROBDD restrict total | cache speedup | notes |
|---:|---:|---:|---:|---:|---:|---:|---|
| 8 | 100 | 0.0020s | 0.0813s | 0.0176s | 0.0029s | 4.39x | CM cache helps, but bitset and ROBDD are faster. |
| 12 | 100 | 0.0031s | 0.0821s | 0.0226s | 0.0063s | 3.87x | ROBDD restriction remains ahead. |
| 16 | 100 | 0.0140s | 0.1308s | 0.0636s | 0.0106s | 2.05x | Bitset is still cheap at this scale. |

## 6. Live-Variable Results

| n | fixed vars median | CM live vars median | CM live vars max | ROBDD restricted nodes median |
|---:|---:|---:|---:|---:|
| 8 | 4 | 4 | 4 | 5.5 |
| 12 | 6 | 6 | 6 | 9.0 |
| 16 | 8 | 8 | 8 | 13.0 |

## 7. Interpretation

CM gains from partial evaluation compared with recompiling/materializing per context. The speedup is real in this run, but it does not beat the strongest baselines at n<=16.

ROBDD restriction is a natural symbolic operation and dominates cached CM in the measured autoref run. Bitset full recompute remains extremely cheap at these sizes, so CM does not win on absolute time here.

Sliding-window contexts create high overlap and repeated context structure, but the current CM path mainly benefits from compiled IR reuse and fixed-variable live-set reduction. Larger expressions, more contexts, or contexts that trigger deeper subtree reuse may be more favorable, but that needs measurement.

CUDD was not run because `dd.cudd` was not importable in this environment.

## 8. Post-cleanup Verification

After the Experiment A cleanup and persistent-cache accounting cleanup, validation passed:

- `python -m compileall cm_bench.py cm_ir.py tests`
- `python -m pytest -q`: 78 passed

The lighter post-cleanup Experiment B run used n=8,12, 50 sliding-window contexts, 2 trials, compiled IR reuse, persistent cache, autoref ROBDD, fixed variable ordering, and no best-of-k sweep.

| n | contexts | bitset total | CM no-cache | CM cache | ROBDD restrict | cache speedup | CM/ROBDD ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 50 | 0.0019s | 0.0920s | 0.0186s | 0.0037s | 4.97x | 5.13x |
| 12 | 50 | 0.0022s | 0.0719s | 0.0174s | 0.0058s | 4.35x | 2.98x |

Cleanup did not change the benchmark conclusion. Cached CM still materially improves over CM no-cache, while bitset and ROBDD restriction remain faster on these small exact-truth-table sizes.

## 9. Fixed-variable Sweep

This sweep used n=12, 100 sliding-window contexts, 3 trials, remaining-variable outputs, compiled IR reuse, persistent cache, autoref ROBDD, fixed ordering, and no best-of-k sweep.

| fixed fraction | bitset total | CM no-cache | CM cache | ROBDD restrict | cache speedup | live vars median |
|---:|---:|---:|---:|---:|---:|---:|
| 25% | 0.0051s | 0.1938s | 0.0697s | 0.0132s | 2.55x | 9 |
| 50% | 0.0063s | 0.1582s | 0.0282s | 0.0122s | 6.24x | 6 |
| 75% | 0.0054s | 0.1579s | 0.0285s | 0.0094s | 5.54x | 3 |

Increasing the fixed fraction from 25% to 50% strongly helped cached CM, reducing median cached time from 0.0697s to 0.0282s and improving cache-vs-no-cache speedup from 2.55x to 6.24x. The 75% point did not further improve cached CM in this run; it stayed near the 50% timing while ROBDD restriction improved to 0.0094s. This supports live-variable reduction as useful for CM, but not monotonically dominant over ROBDD or bitset.

## 10. Context-count Sweep

This sweep used n=12, 50% fixed variables, sliding-window contexts, 3 trials, remaining-variable outputs, compiled IR reuse, persistent cache, autoref ROBDD, fixed ordering, and no best-of-k sweep.

| contexts | bitset | CM no-cache | CM cache | ROBDD restrict | cache speedup |
|---:|---:|---:|---:|---:|---:|
| 25 | 0.0013s | 0.0282s | 0.0082s | 0.0046s | 3.45x |
| 100 | 0.0054s | 0.1559s | 0.0314s | 0.0125s | 5.16x |
| 500 | 0.0175s | 0.6529s | 0.1284s | 0.0404s | 5.08x |

CM compile-once amortization improved from 25 to 100 contexts, then remained roughly flat through 500 contexts. Absolute time still favored bitset and ROBDD restriction. The 500-context point is useful for slides because it shows the CM cache path scaling much better than CM no-cache, but it does not show CM overtaking the competitors.

## 11. Cache Diagnostics

The partial-context raw CSVs emit persistent hits and misses. They do not currently emit a distinct final cache-size field for this mode; for these small runs with no expected eviction, final cache size is inferred from misses.

| run | cache hits | cache misses | final cache size | hit ratio |
|---|---:|---:|---:|---:|
| post-cleanup n=8 | 24 | 40.5 | ~40.5 | 0.372 |
| post-cleanup n=12 | 20 | 46.5 | ~46.5 | 0.301 |
| fixed 25% | 20 | 46 | ~46 | 0.303 |
| fixed 50% | 20 | 46 | ~46 | 0.303 |
| fixed 75% | 20 | 46 | ~46 | 0.303 |
| contexts 25 | 20 | 46 | ~46 | 0.303 |
| contexts 100 | 20 | 46 | ~46 | 0.303 |
| contexts 500 | 20 | 46 | ~46 | 0.303 |

Cache hit ratio did not vary meaningfully across the sweep rows because each run compiled one expression once and reused it across contexts. Runtime improvement therefore correlates more with avoiding per-context compilation and with live-variable/output-size reduction than with changing persistent-cache hit ratio.

## 12. Final Assessment

1. Cleanup did not change the Experiment B conclusions.
2. CM benefit increased substantially from 25% to 50% fixed variables, but did not continue improving at 75% in this run.
3. CM benefit increased from 25 to 100 contexts and then plateaued around 5x versus CM no-cache at 500 contexts.
4. Cache effectiveness did not explain most runtime variation because the hit ratio was nearly constant across sweeps.
5. There is evidence that larger future workloads may favor CM more than the current small-n runs, especially when many contexts amortize compile cost and fixed variables reduce live outputs, but this is not yet evidence that CM beats ROBDD or bitset.
6. Experiment B should be considered complete for the current paper claim: cached CM helps relative to uncached CM, but ROBDD restriction and bitset remain the stronger measured baselines at small n.

## 13. Slide Recommendations

- `CM no-reinflate + cached partial evaluation`
- `ROBDD/autoref restriction`
- `Bitset full recompute`
- `CM no-reinflate no cache`

## 14. Final Verdict

`CM benefit depends on context reuse/live-variable reduction`.

In these measurements, cached CM partial evaluation clearly improves over CM no-cache, but ROBDD restriction dominates partial evaluation and bitset remains fastest at small n.
