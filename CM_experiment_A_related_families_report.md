# CM Experiment A: Related Expression Families

## 1. Executive Summary

Experiment A is implemented as `--bench-expression-family`. It generates related Boolean-expression families, records structural reuse diagnostics, and benchmarks total family workload time for bitset recompute, CM no-reinflate without persistent cache, CM no-reinflate with persistent structural-hash cache, and dd-backed ROBDD symbolic build.

On the completed smoke run, the generated families had high measured structural reuse (`reuse_ratio` about 0.83-0.84). CM persistent subtree caching improved CM at `n=8` by about `1.08x`, but did not improve CM at `n=4`. Bitset recompute remained much faster on this small exact truth-table workload. ROBDD/autoref symbolic build was competitive with CM at `n=8` and faster at `n=4`.

The full Windows/autoref main run from the prompt was started, but did not complete after multiple minutes with the requested `family_size=50`, `trials=5`, and `robdd_order_sweeps=10`; it was stopped cleanly. CUDD was not run on this native Windows environment.

Final verdict: **Results depend strongly on structural reuse**. The cache now exploits shared subtrees, but the completed smoke data does not show CM cache approaching bitset.

## 2. Audit

| Capability | Present / Missing | Evidence | Plan |
|---|---|---|---|
| Bitset evaluation | Present | `bitset_backend.eval_expr_bitset`, used by family workload | Reuse one bitset env per `n` |
| CM no-reinflate | Present | `cm_ir.materialize_hybrid_no_reinflate` | Time compile and evaluate separately |
| CM persistent structural-hash cache | Present, updated | `cm_ir.compile_expr_to_cm_ir_persistent` now caches subtrees, not only roots | Record hits, misses, final cache size |
| Compiled IR reuse flag | Present | `compile_expr_to_cm_ir(... reuse_cache=...)` | Kept out of family cache comparison to preserve no-cache semantics |
| ROBDD/dd backend | Present | `run_robdd_dd_backend` | Use build-only timing unless extraction is explicitly enabled |
| Structural hash | Present | `expr_structural_hash` | Used for family hashes and subtree-overlap diagnostics |
| Expression styles | Present | `random_expr_for_style` supports `mixed_no_constants`, etc. | Reused as family base/subtree generator |
| Expression diagnostics | Present | `expr_complexity_diagnostics`, `truth_table_diagnostics` | Extended with family-level diagnostics |
| CSV output | Present | existing raw/summary CSV flow | Added family raw/summary schema |
| Tests | Present | `tests/test_expression_family_bench.py`, updated persistent-cache test | Full suite passes |

## 3. Benchmark Semantics

This is a family workload benchmark, not a one-expression benchmark. Each row represents processing all variants in a related family. Timed totals exclude correctness checking where practical. Bitset recomputes every variant. CM no-cache compiles and evaluates every variant without persistent structural cache. CM cache enables persistent subtree-level compiled-IR reuse across variants. ROBDD/autoref builds each variant separately; shared-manager ROBDD support is available through `--family-robdd-shared-manager` but was not used in the smoke run.

## 4. Family Diagnostics

Completed smoke command:

```bash
python cm_bench.py --bench-expression-family --sizes 4,8 --trials 2 --max-depth 4 --expr-style mixed_no_constants --family-size 10 --family-variant-style composition_mix --family-shared-blocks 3 --family-force-shared-substructure --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --robdd-dd-backend autoref --robdd-order-policy best-of-k --robdd-order-sweeps 5 --print-summary --out-prefix smoke_family_related
```

| n | family_size | variant_style | reuse_ratio | unique_subtree_hashes | repeated_hashes | notes |
|---:|---:|---|---:|---:|---:|---|
| 4 | 10 | composition_mix | 0.8421 | 123.5 | 41.5 | forced shared substructure |
| 8 | 10 | composition_mix | 0.8342 | 124.0 | 45.5 | forced shared substructure |

## 5. Main Results

| n | family_size | bitset_total | cm_no_cache_total | cm_cache_total | robdd_build_total | speedup_cache_vs_no_cache | ratio_cm_cache_vs_bitset |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 10 | 0.000399 | 0.008349 | 0.008876 | 0.005372 | 0.932 | 22.17 |
| 8 | 10 | 0.000367 | 0.015173 | 0.014025 | 0.015797 | 1.082 | 38.26 |

All reported ok-rates were `1.0` for bitset, CM no-cache, CM cache, and ROBDD/autoref on the completed smoke run.

## 6. Interpretation

Structural reuse is present: subtree reuse ratio is above `0.83` for both smoke sizes. The updated persistent cache records subtree hits (`120.5` median hits at `n=4`, `113.0` at `n=8`), so the experiment is now measuring shared substructure rather than only whole-expression equality.

CM cache improves CM at `n=8`, but the small smoke run does not show a decisive workload-level win. At `n=4`, cache overhead exceeds saved compile work. Bitset remains far ahead for these exact truth-table sizes. ROBDD/autoref symbolic build is faster than CM at `n=4` and similar at `n=8`.

CUDD results are not claimed because `dd.cudd` was not run here. The larger Windows/autoref run likely needs a longer dedicated benchmark window or smaller ROBDD sweep count.

## 7. Slide Recommendations

Use these labels:

- `CM no-reinflate, no cache`
- `CM no-reinflate + structural-hash cache`
- `Bitset recompute`
- `ROBDD/autoref symbolic build`
- `ROBDD/CUDD symbolic build` only when `dd.cudd` imports and is actually run

## 8. Final Verdict

**Results depend strongly on structural reuse.** Subtree-level cache reuse is now implemented and visible in diagnostics. In the completed smoke run, CM cache improves CM only at `n=8` and still does not approach bitset total workload time.

## 9. Cleanup and Implementation Fixes

Follow-up cleanup removed the duplicate root-only `compile_expr_to_cm_ir_persistent(...)` definition from `cm_ir.py`. The retained implementation is the recursive subtree-level persistent cache: it hashes every subtree with `expr_structural_hash(e)`, checks `_PERSISTENT_IR_CACHE` per subtree, records persistent hits/misses, stores compiled subtree IR, and updates `ir_persistent_cache_size`.

Experiment A now also has `--family-no-robdd`, a family-mode flag that skips ROBDD timing and records `family_robdd_status=skipped`. This keeps CM-cache-focused runs from being dominated by ROBDD/autoref build loops or order sweeps. Existing one-shot and equivalence benchmark modes are unchanged.

Tests were added/updated for persistent-cache accounting and family ROBDD skipping:

- repeated equivalent expressions produce persistent hits,
- related expressions with shared subtrees produce subtree-level hits,
- cache size increases and is reported by `cm_ir_persistent_cache_stats()`,
- `clear_cm_ir_persistent_cache()` clears the cache,
- family CSV output records skipped ROBDD status with `--family-no-robdd`.

Verification:

```bash
python -m compileall cm_bench.py cm_ir.py tests
python -m pytest -q
```

Result: `78 passed in 37.79s`.

Native Windows results remain labeled `ROBDD/autoref symbolic build` when ROBDD is included. No CUDD result is claimed unless `dd.cudd` imports and runs.

## 10. Follow-up A1/A2/A3 Results

All follow-up runs used `--family-no-robdd`, so ROBDD fields are intentionally skipped. These are CM-cache-focused family workload totals.

### A1 scaled composition-mix

Command used the preferred `--family-no-robdd` variant with `sizes=8,12,16`, `trials=3`, `family_size=25`, `family_variant_style=composition_mix`.

| n | family_size | reuse_ratio | bitset_total | cm_no_cache_total | cm_cache_total | cache_speedup | cm_cache_vs_bitset | cache_hits | cache_misses |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 25 | 0.9005 | 0.001788 | 0.090322 | 0.086206 | 1.062 | 47.10 | 443 | 448 |
| 12 | 25 | 0.8917 | 0.002848 | 0.107345 | 0.108327 | 0.952 | 39.38 | 502 | 512 |
| 16 | 25 | 0.8828 | 0.013267 | 0.152551 | 0.163582 | 0.957 | 12.33 | 550 | 580 |

### A2 high-reuse shared-block

Command used the preferred `--family-no-robdd` variant with `sizes=8,12,16`, `trials=3`, `family_size=25`, `family_variant_style=shared_block_mix`.

| n | family_size | reuse_ratio | bitset_total | cm_no_cache_total | cm_cache_total | cache_speedup | cm_cache_vs_bitset | cache_hits | cache_misses |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 25 | 0.9117 | 0.001157 | 0.070139 | 0.051812 | 1.298 | 46.26 | 243 | 242 |
| 12 | 25 | 0.9053 | 0.001828 | 0.077303 | 0.057531 | 1.256 | 31.36 | 250 | 260 |
| 16 | 25 | 0.9020 | 0.007222 | 0.104781 | 0.088949 | 1.178 | 11.71 | 248 | 268 |

### A3 family-size sweep

Commands used the preferred `--family-no-robdd` variant with `shared_block_mix`, `trials=3`, and family sizes `10`, `25`, and `50`. The required `n=12` sweep was fast, so the optional `n=16` sweep was also run.

| n | family_size | reuse_ratio | cm_no_cache_total | cm_cache_total | cache_speedup | cache_hits | cache_misses | cache_size_final |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 10 | 0.8191 | 0.026663 | 0.025932 | 1.041 | 165 | 189 | 189 |
| 12 | 25 | 0.9047 | 0.083841 | 0.060530 | 1.385 | 250 | 258 | 258 |
| 12 | 50 | 0.9314 | 0.121966 | 0.095119 | 1.334 | 384 | 369 | 369 |
| 16 | 10 | 0.8113 | 0.037424 | 0.038785 | 1.109 | 165 | 197 | 197 |
| 16 | 25 | 0.9000 | 0.090378 | 0.075337 | 1.200 | 248 | 270 | 270 |
| 16 | 50 | 0.9298 | 0.196186 | 0.191411 | 1.025 | 387 | 384 | 384 |

## 11. Interpretation

CM cache speedup grows from family size `10` to `25` in the shared-block sweep, but it does not monotonically improve at `50`. At `n=12`, speedup rises from `1.04x` to `1.39x`, then settles at `1.33x`. At `n=16`, the best result is `1.20x` at family size `25`, with little benefit at size `50`.

`shared_block_mix` shows stronger CM benefit than `composition_mix`. A1 composition-mix is mixed: only `n=8` is above `1.0x`, while `n=12` and `n=16` are slightly slower with cache. A2 shared-block is consistently positive across all three sizes, ranging from `1.18x` to `1.30x`.

CM cache still does not approach bitset total workload time on these exact truth-table workloads. Even in the best A2 cases, CM cache is roughly `11.7x` to `46.3x` slower than bitset recompute. Cache overhead is still material, especially when expressions are small or when the family size is not large enough for reuse to amortize lookup and bookkeeping.

The implementation is ready for Experiment B from an Experiment A infrastructure perspective: family workload generation, subtree-level persistent caching, correctness checks, skip-light backend selection, and CSV summaries are in place. The next experiment should keep backend selection explicit and avoid letting ROBDD/autoref order sweeps dominate CM-focused measurements.

## 12. Final Experiment A Verdict

**CM cache improves CM but does not approach bitset.**

The strongest follow-up signal is `shared_block_mix`, where CM cache gives consistent workload-level speedups (`1.18x-1.30x` in A2, up to `1.39x` in A3). The broader composition mix remains small or inconclusive. Bitset remains the dominant exact truth-table execution baseline for these sizes.
