# CM/Bitset Boundary Cost Report

Date: 2026-04-09

## 1. Audit table

| Area | PRESENT / PARTIAL / MISSING | Notes |
|------|------------------------------|-------|
| bitset node evaluation | PRESENT | `bitset_backend.py:eval_cm_node_bitset(...)` evaluates `CMNode` to a packed `int` truth-table bitset over `live_vars`. |
| bitset-to-hypercube conversion | PRESENT | `bitset_backend.py:bitset_to_bool_hypercube(...)` converts packed `int` → NumPy boolean hypercube shaped `(2,) * k`. |
| hypercube axis alignment / permutation / insert | PRESENT | `cm_ir.py:align_to_vars(...)` + cached `_alignment_plan(...)` handle transpose (when needed) and singleton-axis insertion to match a target live-var order. |
| constant zero/one handling | PRESENT | `cm_ir.py:_materialize_ir_tagged.materialize_bitset(...)` returns scalar const for `k=0`, `bits==0`, `bits==full_mask` (and NumPy-side pruning exists for AND/OR/XOR/IMP/EQV). |
| repeated allocation risk | PARTIAL | Boundary conversion allocates: `int.to_bytes(...)` buffer + `np.unpackbits(...)` array + bool conversion; hybrid root materialization also pays `broadcast_to(...)+reshape(...).copy()` in `materialize_cm(...)`. |
| diagnostic support for timing/counts | PRESENT (added) | New `boundary_*` diagnostics in `cm_ir.py` and CSV export in `cm_bench.py`. |
| benchmark compare support (numpy/hybrid/partial/bitset) | PRESENT | `cm_bench.py --cm-compare-hybrid` runs NumPy-only CM, `hybrid`, `partial_hybrid`, `cm_parallel`, and bitset and writes raw+summary CSVs. |

## 2. Current boundary path

### Where the CM↔bitset boundary happens
- The hybridization decision lives in `cm_ir.py:_materialize_ir_tagged(...)` (called via `materialize_ir(...)` / `materialize_cm(...)`).
- When a node is selected for bitset execution, `cm_ir.py` calls:
  1) `bitset_backend.py:eval_cm_node_bitset(cur, live_vars, fixed=...)` → packed `int` bitset
  2) If non-constant: `bitset_backend.py:bitset_to_bool_hypercube(bits, k)` → boolean hypercube
  3) That hypercube is then aligned into the parent’s `live_vars` using `cm_ir.py:align_to_vars(...)` (transpose + singleton-axis insertion).

### `hybrid` (full hybrid root collapse)
- `materialize_ir(..., materialize_mode=\"hybrid\")` calls `rec(..., allow_bitset_collapse=True)` at depth 0.
- Children are evaluated with `allow_bitset_collapse=False`, so only the **root** can collapse into bitset.
- The bitset hypercube produced at the root then crosses back into CM via `materialize_cm(...)`:
  - `align_to_vars(...)` to `target_vars = R + C`
  - `broadcast_to(...)` to full `(2,) * len(target_vars)` shape
  - `reshape(...).copy()` into the final 2D CM matrix

### `partial_hybrid` (child/subnode bitset execution; no root collapse)
- `materialize_ir(..., materialize_mode=\"partial_hybrid\")` calls `rec(..., allow_bitset_collapse=False)` at depth 0, so the root is **forced** to NumPy combination.
- Recursive calls for `not` and `binary` nodes pass `allow_bitset_collapse=True`, so eligible **children/subnodes** can use bitset.
- Each bitset child’s hypercube is aligned to the parent’s `live_vars` via `align_to_vars(...)`, and then combined with NumPy boolean ops (AND/OR/XOR/IMP/EQV).

## 3. Instrumentation added

Instrumentation is recorded into the existing `diagnostics` dict passed into `materialize_cm(...)` / `materialize_ir(...)` and then exported by `cm_bench.py` into raw CSV columns and summary `*_median` columns.

### Timing fields (seconds, float)
- `boundary_bitset_eval_time_s`: time inside `eval_cm_node_bitset(...)` (bitset core evaluation)
- `boundary_bitset_to_hypercube_time_s`: time converting packed bits → boolean hypercube (`bitset_to_bool_hypercube(...)`)
- `boundary_align_time_s`: time spent aligning bitset-origin hypercubes into parent-compatible shapes (and, for hybrid root, includes the final broadcast/reshape/copy path in `materialize_cm(...)`)
- `boundary_dispatch_time_s`: bitset-boundary wrapper time (excluding eval + conversion)

### Count/size fields (int)
- `boundary_bitset_eval_calls`
- `boundary_bitset_to_hypercube_calls`
- `boundary_elements_converted` (sum of `2**k` across conversions)
- `boundary_align_calls`
- `boundary_align_transpose_calls`
- `boundary_align_insert_axes_total`
- `boundary_bitset_const_fastpath_calls`

## 4. Pre-optimization measurements

Command:
`python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 321 --out-prefix bench_runs/bench_boundary_pre_t7 --cm-layout balanced --cm-compare-hybrid --cm-hybrid-threshold 7 --experiment cm_vs_bitset --no-sympy --no-robdd --no-dd --no-espresso --no-bdd-sop --no-numba --print-summary`

Medians pulled from `bench_runs/bench_boundary_pre_t7_summary.csv`:

| n | mode | total_time_s | bitset_eval_s | to_hypercube_s | align_s | dispatch_s | conversions | elements_converted |
|---|------|--------------|--------------|---------------|--------|------------|------------|-------------------|
| 4 | cm_hybrid | 0.000302 | 0.000035 | 0.000020 | 0.000027 | 0.000004 | 1.0 | 8.0 |
| 4 | cm_partial_hybrid | 0.000280 | 0.000030 | 0.000022 | 0.000019 | 0.000006 | 2.0 | 12.0 |
| 8 | cm_hybrid | 0.000247 | 0.000042 | 0.000014 | 0.000040 | 0.000004 | 1.0 | 16.0 |
| 8 | cm_partial_hybrid | 0.000351 | 0.000031 | 0.000027 | 0.000040 | 0.000006 | 2.0 | 12.0 |
| 12 | cm_hybrid | 0.000269 | 0.000025 | 0.000011 | 0.000064 | 0.000003 | 1.0 | 8.0 |
| 12 | cm_partial_hybrid | 0.000215 | 0.000019 | 0.000026 | 0.000050 | 0.000006 | 2.0 | 8.0 |
| 16 | cm_hybrid | 0.000390 | 0.000045 | 0.000015 | 0.000185 | 0.000004 | 1.0 | 32.0 |
| 16 | cm_partial_hybrid | 0.000448 | 0.000033 | 0.000022 | 0.000024 | 0.000006 | 2.0 | 14.0 |

## 5. Bottleneck interpretation

- Is bitset core time the dominant cost?
  - No. In the pre numbers above, boundary alignment is frequently comparable to or larger than bitset eval+conversion, especially for `cm_hybrid` at `n=16` (align dominates).

- Or is surrounding boundary work the dominant cost?
  - Boundary work is a meaningful fraction of hybrid runtime, but it does not explain the full gap to pure bitset. Even pre-optimization, `cm_hybrid` spends more time outside the boundary than inside it.

- Does `partial_hybrid` increase boundary crossings materially?
  - Yes. In these runs, `cm_hybrid` performs ~1 conversion per trial (root collapse), while `cm_partial_hybrid` performs ~2 conversions per trial (child/subnode bitset usage).

- Which component appears most worth optimizing?
  - Boundary alignment/insertion work (especially repeated singleton-axis insertion) was the largest boundary component for the benchmark slice.

## 6. Optimization(s) implemented

### Optimization B: alignment fast-path (reduce singleton-axis insertion overhead)
- File: `cm_ir.py`
- Change: `align_to_vars(...)` / `align_to_vars_with_stats(...)` now use a single `reshape` to insert multiple `1`-sized axes when:
  - no transpose is needed, and
  - the input is C-contiguous
- Fallback to the prior `np.expand_dims` loop for non-contiguous arrays or when shape bookkeeping doesn’t match.

### Optimization A: avoid redundant uint8 copy during bitset unpack
- File: `bitset_backend.py`
- Change: `bitset_to_bool_array(...)` no longer calls `.astype(np.uint8)` on the `np.unpackbits(...)` output (it is already `uint8`).

## 7. Post-optimization validation

Tests:
- `python -m pytest -q` → `30 passed`

Benchmarks:
- `python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 321 --out-prefix bench_runs/bench_boundary_post_t7 --cm-layout balanced --cm-compare-hybrid --cm-hybrid-threshold 7 --experiment cm_vs_bitset --no-sympy --no-robdd --no-dd --no-espresso --no-bdd-sop --no-numba --print-summary`

## 8. Post-optimization results

Before/after medians (pre: `bench_runs/bench_boundary_pre_t7_summary.csv`, post: `bench_runs/bench_boundary_post_t7_summary.csv`).

`before_boundary_s` / `after_boundary_s` is the sum of:
`bitset_eval_s + to_hypercube_s + align_s + dispatch_s`.

| n | mode | before_total_s | after_total_s | before_boundary_s | after_boundary_s | boundary_reduction |
|---|------|----------------|---------------|-------------------|------------------|-------------------|
| 4 | cm_hybrid | 0.000302 | 0.000160 | 0.000087 | 0.000061 | 1.413 |
| 4 | cm_partial_hybrid | 0.000280 | 0.000174 | 0.000077 | 0.000048 | 1.605 |
| 8 | cm_hybrid | 0.000247 | 0.000205 | 0.000100 | 0.000072 | 1.394 |
| 8 | cm_partial_hybrid | 0.000351 | 0.000263 | 0.000104 | 0.000074 | 1.404 |
| 12 | cm_hybrid | 0.000269 | 0.000137 | 0.000103 | 0.000062 | 1.665 |
| 12 | cm_partial_hybrid | 0.000215 | 0.000162 | 0.000100 | 0.000051 | 1.972 |
| 16 | cm_hybrid | 0.000390 | 0.000393 | 0.000249 | 0.000234 | 1.065 |
| 16 | cm_partial_hybrid | 0.000448 | 0.000437 | 0.000084 | 0.000068 | 1.237 |

## 9. Final verdict

`Boundary overhead is real but not the dominant bottleneck`

Justification:
- The boundary components (eval+convert+align+dispatch) are non-trivial and were reduced measurably, improving several `cm_hybrid` / `cm_partial_hybrid` timings.
- However, even after reducing the boundary costs, `cm_hybrid` / `cm_partial_hybrid` remain much slower than pure bitset on this slice; significant time remains in non-boundary NumPy/IR materialization scaffolding and the unavoidable final CM materialization copy for hybrid root collapse.

## 10. Remaining limitations

- `cm_hybrid` root collapse still pays the final `broadcast_to(...)+reshape(...).copy()` in `materialize_cm(...)`, and that cost is part of the CM output contract; removing it would require a larger API/representation change.
- Bitset conversion still allocates intermediate buffers (`int.to_bytes`, `np.unpackbits`, bool conversion). Further improvements would likely need a different bitset representation or a different unpacking path.
- The current instrumentation lumps some root-finalization work into `boundary_align_time_s` for `cm_hybrid`; splitting out `broadcast/reshape/copy` into separate fields could improve attribution if we continue optimizing.

