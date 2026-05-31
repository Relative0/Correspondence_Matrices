# CM Partial Hybrid Report

Date: 2026-04-08

## 1. Audit table

| Area | PRESENT / PARTIAL / MISSING | Notes |
|------|------------------------------|-------|
| CM IR compilation + node structure | PRESENT | `cm_ir.py` defines `CMNode` + `compile_expr_to_cm_ir(...)` and carries `node.vars` for live-var analysis. |
| NumPy-only CM materialization | PRESENT | `cm_ir.py:materialize_ir(..., materialize_mode="numpy")` and `materialize_cm(...)` perform pure NumPy/CM evaluation. |
| Full-collapse hybrid path | PRESENT | `cm_ir.py:materialize_ir(..., materialize_mode="hybrid")` allows bitset collapse only at the root, based on `hybrid_threshold`. |
| Per-node backend decision logic | PRESENT | `cm_ir.py:materialize_ir` selects `bitset` vs `numpy` per node, controlled by `materialize_mode`, `allow_bitset_collapse`, and `hybrid_threshold`. |
| Bitset-evaluate child independently | PRESENT | `bitset_backend.py:eval_cm_node_bitset(...)` evaluates any CM IR node over a supplied `live_vars` set; `cm_ir.py` converts to a CM-compatible hypercube via `bitset_to_bool_hypercube(...)`. |
| Diagnostics (counts + decisions) | PRESENT | Base counters already existed; this change adds decision “reason bucket” counters in `cm_ir.py` and surfaces them via `cm_bench.py`. |
| Benchmark compare support (numpy/hybrid/partial/bitset) | PRESENT | `cm_bench.py --cm-compare-hybrid` runs NumPy-only CM, `hybrid`, `partial_hybrid`, and bitset and writes raw+summary CSVs. |
| Tests for modes + correctness | PRESENT | `tests/test_cm_optimizations.py` and `tests/test_bench_integration.py` cover parity, mode behavior, and benchmark smoke. |

## 2. What current hybrid already did

`materialize_mode="hybrid"` evaluates the **entire root** via bitset when the reduced live-variable count `k` is at/below `hybrid_threshold`; otherwise it evaluates in NumPy/CM (and does not bitset-collapse children).

## 3. Partial-hybrid design

Insertion point: `cm_ir.py:materialize_ir(...)` (shared by eager/lazy/pair/parallel build paths via `materialize_cm(...)`).

Policy:
- `materialize_mode="partial_hybrid"` **never** collapses the root into bitset.
- Child/subnode recursion is allowed to bitset-collapse when `k <= hybrid_threshold`.
- Bitset materializations are converted back to NumPy hypercubes and aligned to the parent’s `live_vars` before combining in NumPy/CM.

Diagnostics additions:
- Stable int counters for: bitset-vs-numpy decisions, cache hits, root-forced behavior, and fixed-var threshold crossings.

## 4. Code changes

- `cm_ir.py`: enforce root-only bitset collapse for `hybrid`; add partial-hybrid decision “reason bucket” counters.
- `cm_bench.py`: include new decision counters in raw CSV and summary medians.
- `tests/test_cm_optimizations.py`: add a test asserting `decision_numpy_root_forced==1` when the partial-hybrid root is threshold-eligible.
- `CM_partial_hybrid_report.md`: this report.

## 5. Tests and validation

Commands run:
- `python -m pytest -q`

Result:
- `29 passed`

## 6. Benchmark configuration

Commands run (SymPy/DD/Espresso/Numba/ROBDD disabled for speed; bitset enabled implicitly by compare mode):
- `python cm_bench.py --sizes 4,8,12,16 --trials 3 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-hybrid-threshold 5 --out-prefix bench_runs/bench_partial_hybrid_t5 --no-sympy --no-dd --no-espresso --no-bdd-sop --no-numba --no-robdd`
- `python cm_bench.py --sizes 4,8,12,16 --trials 3 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-hybrid-threshold 7 --out-prefix bench_runs/bench_partial_hybrid_t7 --no-sympy --no-dd --no-espresso --no-bdd-sop --no-numba --no-robdd`
- `python cm_bench.py --sizes 4,8,12,16 --trials 3 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-hybrid-threshold 9 --out-prefix bench_runs/bench_partial_hybrid_t9 --no-sympy --no-dd --no-espresso --no-bdd-sop --no-numba --no-robdd`

## 7. Benchmark results

Below: threshold = 7 (seconds; medians across trials).

| n | cm (numpy) | cm_hybrid | cm_partial_hybrid | bitset | partial/cm | partial/hybrid | partial/bitset |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 0.000445 | 0.000213 | 0.000214 | 0.000009 | 0.48 | 1.01 | 24.63 |
| 8 | 0.000333 | 0.000213 | 0.000308 | 0.000009 | 0.92 | 1.44 | 33.85 |
| 12 | 0.000342 | 0.000233 | 0.000267 | 0.000012 | 0.78 | 1.14 | 22.23 |
| 16 | 0.000349 | 0.000320 | 0.000307 | 0.000024 | 0.88 | 0.96 | 12.89 |

Diagnostics highlights (threshold = 7; medians):
- `hybrid`: `bitset_materializations=1`, `numpy_materializations=0`, `full_collapse_occurred=1`
- `partial_hybrid`: typically `bitset_materializations≈2`, `numpy_materializations≈1`, `full_collapse_occurred=0`, `decision_numpy_root_forced=1`

Sweep note:
- For thresholds 5, 7, 9 on this small benchmark set, `partial_hybrid` preserved structure (no root collapse) but did not consistently beat `hybrid` on runtime.

## 8. Interpretation

- Did partial hybrid preserve more CM structure than full hybrid? **Yes** (root never bitset-collapses; diagnostics show mixed NumPy+bitset execution).
- Did it reduce full-collapse behavior? **Yes** (`full_collapse_occurred=0` for `partial_hybrid` vs `1` for `hybrid` in these runs).
- Did it improve runtime vs current hybrid? **Not in this benchmark slice** (often slower; sometimes close).
- Did it narrow the gap to bitset? **No** in these runs; bitset remains much faster at flat TT evaluation.

## 9. Clear verdict

`Partial hybrid does not improve on full hybrid`

It is valuable for *structure preservation + instrumentation*, but on this benchmark slice it does not translate into faster runtime than the full-collapse hybrid.

## 10. Remaining limitations

- The decision policy is threshold-only; no cost model for conversion/alignment overhead vs operator cost.
- Bench times at these sizes are extremely small; noise and timer granularity can affect ratios.
- Future work would likely require (a) a better cost model and/or (b) avoiding conversion overhead at CM/bitset boundaries rather than only changing collapse granularity.

