# CM IR Cost Decomposition + Caching/Reuse Report (Measurement-First)

## 1. Audit table
| Area | PRESENT / PARTIAL / MISSING | Notes |
|------|------------------------------|-------|
| Expr → IR compilation | PRESENT | `cm_ir.compile_expr_to_cm_ir(...)` builds a canonicalized DAG through `CMIRBuilder.build(...)`. |
| Canonicalization/pruning during build | PRESENT | Per-op normalization happens inside `CMIRBuilder.negate/make_and/make_or/make_xor/make_eqv/make_imp` plus `_canonicalize_commutative_args(...)`. |
| Subtree interning/memoization | PRESENT | `CMIRBuilder._intern(...)` interns by structural key and maintains `subtree_cache_hits/misses`. |
| Live-var aggregation | PRESENT | Builder computes per-node `vars` via `_live_vars_union(...)` (which uses `_sorted_unique_vars(...)`). |
| No-reinflate backend | PRESENT | `cm_ir.materialize_hybrid_no_reinflate(...)` returns packed bitset or 1D TT vector and avoids dense 2D CM reinflation. |
| Stable IR stage timing | MISSING (before) / PRESENT (after) | Added `ir_*` timing/counters gated behind `--cm-report-ir-breakdown`. |
| Benchmark-level reuse | MISSING (before) / PRESENT (after) | `--cm-compile-once-per-expression` compiles a `CMNode` once per expression and reuses it across CM modes; adds `*_exec_only_time_s`. |
| Compiled IR cache (Expr → CMNode) | MISSING (before) / PRESENT (after) | `compile_expr_to_cm_ir(..., reuse_cache=True)` and `--cm-reuse-compiled-ir` provide an explicit LRU-style cache. |

## 2. Instrumentation (public diagnostics keys)
Instrumentation is **off by default**. It only records and/or emits IR breakdown fields when `cm_bench.py` enables timing by setting `diagnostics["ir_timing_enabled"]=1`, which happens under:
- `--cm-report-ir-breakdown`
- `--cm-compile-once-per-expression`

### 2.1 Compile / build stage (in `cm_ir.py`)
Recorded in `compile_expr_to_cm_ir_cached(...)` and `CMIRBuilder`:
- `ir_compile_time_s`: total wall time for `CMIRBuilder.build(expr)` (only when `ir_timing_enabled=1`)
- `ir_intern_time_s`, `ir_intern_calls`: time/calls spent in `CMIRBuilder._intern(...)`
- `ir_canonicalize_time_s`, `ir_canonicalize_calls`: time/calls spent in `_canonicalize_commutative_args(...)`
- `ir_rewrite_time_s`, `ir_rewrite_calls`: time/calls spent in per-op rewrite/prune logic (exclusive of interning/canonicalization/live-vars timing)
- `ir_live_vars_time_s`, `ir_live_vars_calls`, `ir_live_vars_total_inputs`: live-var union time/calls and total input var-list sizes
- Cache stats for compiled IR reuse (only when enabled):
  - `ir_compile_cache_hit` (0/1 per call), `ir_compile_cache_hits`, `ir_compile_cache_misses`

### 2.2 No-reinflate execute stage (in `cm_ir.py`)
Recorded in `materialize_hybrid_no_reinflate(...)`:
- `nr_bitset_eval_time_s`, `nr_bitset_eval_calls`: time/calls for `eval_cm_node_bitset(...)` when returning packed bitset
- `nr_fallback_materialize_ir_time_s`: time spent in `materialize_ir(... materialize_mode="hybrid")` in the TT-vector fallback path
- `nr_tt_vector_build_time_s`: time for align/broadcast/flatten when producing a 1D TT vector fallback

### 2.3 Benchmark emission (in `cm_bench.py`)
When `--cm-report-ir-breakdown` is provided, `cm_bench.py` emits per-trial prefixed columns (e.g. `cm_hybrid_no_reinflate_ir_compile_time_s`) into the raw CSV and adds `*_median` aggregates to the summary CSV.

It also emits a derived reporting-only field:
- `*_ir_other_time_s = max(0, ir_compile_time_s - (ir_intern + ir_canonicalize + ir_rewrite + ir_live_vars))`

## 3. Pre-optimization measurements (hybrid_no_reinflate)
Benchmark command:
```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate --cm-hybrid-threshold 7 --cm-report-ir-breakdown --no-dd --no-espresso --print-summary --out-prefix bench_ir_pre_ht7
```

Medians extracted from `bench_ir_pre_ht7_summary.csv`:

| n | total_s | ir_compile | intern | canon | rewrite | live_vars | other | bitset_eval | ratio/bitset |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 0.000160 | 0.000107 | 0.000019 | 0.000006 | 0.000024 | 0.000011 | 0.000045 | 0.000037 | 18.44 |
| 8 | 0.000168 | 0.000120 | 0.000023 | 0.000006 | 0.000022 | 0.000017 | 0.000051 | 0.000032 | 16.27 |
| 12 | 0.000303 | 0.000212 | 0.000040 | 0.000009 | 0.000039 | 0.000032 | 0.000089 | 0.000067 | 7.88 |
| 16 | 0.000195 | 0.000113 | 0.000024 | 0.000006 | 0.000015 | 0.000014 | 0.000053 | 0.000065 | 3.71 |

## 4. Bottleneck interpretation
- In this slice, `hybrid_no_reinflate` time is dominated by **IR compilation/build** (`ir_compile_time_s`) rather than the packed-bitset execution (`nr_bitset_eval_time_s`).
- Within `ir_compile_time_s`, interning + canonicalization + rewrite + live-vars are measurable but still leave a non-trivial `ir_other_time_s` bucket (builder overhead not directly attributed to the instrumented sub-stages).

## 5. Optimizations implemented (explicit flags)
### 5.1 Benchmark-level reuse: compile once per expression
Flag:
- `--cm-compile-once-per-expression`

Behavior:
- Compiles a `CMNode` once per expression and reuses it for `materialize_cm(...)` and `materialize_hybrid_no_reinflate(...)` across CM modes.
- Adds `*_exec_only_time_s` columns so `*_time_s` stays comparable (compile + exec) while the harness can avoid redundant work.

Benchmark command:
```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate --cm-hybrid-threshold 7 --cm-report-ir-breakdown --cm-compile-once-per-expression --no-dd --no-espresso --print-summary --out-prefix bench_ir_post_compile_once_ht7
```

### 5.2 Compiled-IR cache (Expr → CMNode)
Flag:
- `--cm-reuse-compiled-ir`

Behavior:
- Enables `compile_expr_to_cm_ir(..., reuse_cache=True)` for CM compilation paths so identical immutable `Expr` objects can reuse the same compiled `CMNode`.
- This targets redundant compilation in compare modes / repeated workloads.

Benchmark command:
```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate --cm-hybrid-threshold 7 --cm-report-ir-breakdown --cm-reuse-compiled-ir --no-dd --no-espresso --print-summary --out-prefix bench_ir_post_cache_ht7
```

## 6. Post-optimization results
### 6.1 Compare-mode total wall time (CM + hybrid + partial_hybrid + no_reinflate)
This is computed from medians as:
- baseline sum: `cm_time_s + cm_hybrid_time_s + cm_partial_hybrid_time_s + cm_hybrid_no_reinflate_time_s`
- compile-once predicted sum: `cm_ir_compile_time_s + (cm_exec_only + cm_hybrid_exec_only + cm_partial_hybrid_exec_only + cm_hybrid_no_reinflate_exec_only)`
- cache sum: same as baseline sum, but with `--cm-reuse-compiled-ir` enabled

| n | baseline_sum_s | compile_once_sum_s | speedup_compile_once | cache_sum_s | speedup_cache |
|---:|---:|---:|---:|---:|---:|
| 4 | 0.000950 | 0.000627 | 1.52x | 0.000724 | 1.31x |
| 8 | 0.001011 | 0.000627 | 1.61x | 0.000710 | 1.42x |
| 12 | 0.001704 | 0.000881 | 1.93x | 0.000852 | 2.00x |
| 16 | 0.001537 | 0.001161 | 1.32x | 0.001278 | 1.20x |

### 6.2 hybrid_no_reinflate end-to-end + cache-hit signal
Medians for `hybrid_no_reinflate`:

| n | no_reinflate_total_s | ir_compile | bitset_eval | ratio/bitset | ir_cache_hit |
|---:|---:|---:|---:|---:|---:|
| 4 | 0.000160 | 0.000107 | 0.000037 | 18.44 | 0 |
| 8 | 0.000168 | 0.000120 | 0.000032 | 16.27 | 0 |
| 12 | 0.000303 | 0.000212 | 0.000067 | 7.88 | 0 |
| 16 | 0.000195 | 0.000113 | 0.000065 | 3.71 | 0 |

With `--cm-reuse-compiled-ir` (note: for `cm_hybrid_no_reinflate`, this backend runs after earlier CM compiles in the same trial, so it is typically a cache hit):

| n | no_reinflate_total_s | ir_compile | bitset_eval | ratio/bitset | ir_cache_hit |
|---:|---:|---:|---:|---:|---:|
| 4 | 0.000070 | 0.000000 | 0.000042 | 7.57 | 1 |
| 8 | 0.000055 | 0.000000 | 0.000035 | 5.24 | 1 |
| 12 | 0.000075 | 0.000000 | 0.000057 | 2.71 | 1 |
| 16 | 0.000108 | 0.000000 | 0.000076 | 1.62 | 1 |

## 7. Tests and validation
Commands run:
```bash
python -m unittest discover -s tests -v
```

## 8. Remaining limitations
- `ir_other_time_s` is a residual bucket and may include builder overhead not attributed to the explicitly-timed sub-stages.
- `--cm-reuse-compiled-ir` changes benchmark semantics by letting later CM modes reuse the compiled IR from earlier modes; this is why it is off by default and intended for understanding “redundant compile” cost.
- `--cm-compile-once-per-expression` improves wall-clock runtime when running multiple CM modes, but the per-backend `*_time_s` columns remain end-to-end comparable (compile + exec) by construction.

## 9. Verdict
VERDICT: IR compilation dominates `hybrid_no_reinflate` for this benchmark slice, and explicit reuse/caching meaningfully reduces redundant work and narrows the gap to the bitset backend (while not eliminating it).

