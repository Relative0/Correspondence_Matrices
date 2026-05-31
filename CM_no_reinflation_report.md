# CM No-Reinflation Report

## 1. Audit table
| Area | PRESENT / PARTIAL / MISSING | Notes |
|------|------------------------------|-------|
| Root hybrid bitset collapse | PRESENT | `cm_ir._materialize_ir_tagged(... materialize_mode="hybrid")` can full-collapse at depth 0 via `eval_cm_node_bitset(...)` and sets `full_collapse_occurred=1`. |
| Final CM matrix reinflation path | PRESENT | `cm_ir.materialize_cm(...)` always aligns to `R+C`, broadcasts to `(2,)*k`, reshapes to `(2^|R|, 2^|C|)`, and `.copy()`s. |
| Direct packed bitset return (no CM) | MISSING (before) / PRESENT (after) | Added explicit `materialize_hybrid_no_reinflate(...)` returning packed bitset (`int`) or TT vector without ever producing a 2D dense CM matrix. |
| Direct TT return feasibility | PARTIAL | Previously possible only by post-processing dense CM output (`cm_bench.cm_matrix_to_tt`). Now explicit TT/bitset return exists for the no-reinflate mode. |
| Bench correctness extraction path | PRESENT | `cm_bench.cm_matrix_to_tt(...)` projects the padded CM matrix into `eval_expr_tt` order. No-reinflate mode compares directly against `eval_expr_tt(...)`. |
| Output-contract assumptions | PRESENT | Many call sites expect a dense CM matrix; no-reinflate is explicitly separated and benchmark-only. |
| Final-stage diagnostics | MISSING (before) / PRESENT (after) | Added stable `final_*` diagnostics (performed/time/representation code) for CM and no-reinflate paths. |
| Compare-mode wiring | PARTIAL (before) / PRESENT (after) | New CLI flag `--cm-compare-no-reinflate` adds a third CM compare backend without changing defaults. |

## 2. Current output/materialization contract
The existing CM materialization contract is “return a dense 2D CM matrix”.

Concretely, `cm_ir.materialize_cm(...)`:
1. materializes the CM IR to an internal NumPy representation (`_materialize_ir_tagged`)
2. aligns to the full target var ordering `target_vars = R + C`
3. broadcasts to the full hypercube shape `(2,) * len(target_vars)`
4. reshapes to `(2**len(R), 2**len(C))`
5. forces a dense contiguous output via `.copy()`

This happens even when hybrid full-collapses via bitset at the root: the bitset result is converted to a NumPy hypercube and then reinflated into the full dense CM matrix output shape.

## 3. New mode design
### Insertion point
The minimal clean bypass point is at the **final output layer**, i.e. before `materialize_cm(...)` aligns/broadcasts/reshapes/copies into a dense 2D CM matrix.

### What’s returned
New explicit API: `cm_ir.materialize_hybrid_no_reinflate(node, vars_all, fixed=..., diagnostics=..., hybrid_threshold=...)`

Return representations (documented numeric codes):
- `2`: packed bitset (`int`) in MSB-first `vars_all` order
- `1`: truth-table vector (`np.ndarray` uint8) in MSB-first `vars_all` order

### How reinflation is avoided
- If `live_k <= hybrid_threshold` (where `live_k` is the number of live vars in the CM IR node after applying `fixed`), evaluate **directly to a packed bitset** via `eval_cm_node_bitset(node, vars_all, fixed=...)` and return it.
- Otherwise, fall back to `materialize_ir(... materialize_mode="hybrid")` and only produce a **1D TT vector** via align/broadcast/flatten — never a 2D dense CM matrix.

### Diagnostics
Stable final-output diagnostics are now recorded (when `diagnostics` is provided), including:
- `final_cm_materialization_performed` (0/1)
- `final_cm_materialization_time_s`
- `final_truth_table_materialization_time_s`
- `final_bitset_returned` (0/1)
- `final_output_elements`
- `final_output_representation_code` (0 CM matrix, 1 TT vector, 2 packed bitset)

## 4. Code changes
- `cm_ir.py`: adds `materialize_hybrid_no_reinflate(...)`, `FinalNoReinflateResult`, and stable `final_*` diagnostics; `materialize_cm(...)` now records final CM materialization diagnostics and timing.
- `cm_bench.py`: adds `--cm-compare-no-reinflate`, runs the new backend, propagates diagnostics columns, adds summary medians + ratios, updates console summary and HTML preferred columns.
- `tests/test_cm_no_reinflate.py`: new unit tests for correctness + “no reinflate happened” + mode separation.
- `tests/test_bench_integration.py`: extends the integration test to verify the new summary columns appear only when enabled.

## 5. Tests and validation
Commands run:
- `.\.venv\Scripts\python.exe -m py_compile .\cm_bench.py`
- `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

Result:
- All tests passed.

Note:
- `pytest` is not installed in the repo venv, so `python -m pytest` is not used here.

## 6. Benchmark configuration
All runs:
- `--sizes 4,8,12,16`
- `--trials 3`
- `--max-depth 4`
- `--seed 123`
- `--cm-layout balanced`
- `--cm-compare-hybrid --cm-compare-no-reinflate`
- `--no-dd --no-espresso`

Commands executed:
- `.\.venv\Scripts\python.exe .\cm_bench.py --sizes 4,8,12,16 --trials 3 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate --cm-hybrid-threshold 5 --no-dd --no-espresso --print-summary --out-prefix bench_noreinflate_ht5`
- `.\.venv\Scripts\python.exe .\cm_bench.py --sizes 4,8,12,16 --trials 3 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate --cm-hybrid-threshold 7 --no-dd --no-espresso --print-summary --out-prefix bench_noreinflate_ht7`
- `.\.venv\Scripts\python.exe .\cm_bench.py --sizes 4,8,12,16 --trials 3 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate --cm-hybrid-threshold 9 --no-dd --no-espresso --print-summary --out-prefix bench_noreinflate_ht9`

## 7. Benchmark results
Columns below are medians from the generated summary CSVs. Representation code: `2` = packed bitset, and `final_cm_materialization_performed=0` confirms reinflation was avoided.

### Hybrid threshold = 5
| n_vars | cm_time_s_median | cm_hybrid_time_s_median | cm_hybrid_no_reinflate_time_s_median | bitset_time_s_median | ratio_cm_hybrid_no_reinflate_over_cm | ratio_cm_hybrid_no_reinflate_over_cm_hybrid | ratio_cm_hybrid_no_reinflate_over_bitset | cm_hybrid_no_reinflate_final_cm_materialization_performed_median | cm_hybrid_no_reinflate_final_output_representation_code_median |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 0.0003578 | 0.0001684 | 0.0001204 | 9.29995e-06 | 0.336501 | 0.714964 | 12.9463 | 0 | 2 |
| 8 | 0.0004026 | 0.0002254 | 0.0001716 | 1.13e-05 | 0.42623 | 0.761313 | 15.1858 | 0 | 2 |
| 12 | 0.000343 | 0.0001891 | 0.0001271 | 1.74e-05 | 0.370554 | 0.672131 | 7.30459 | 0 | 2 |
| 16 | 0.0003229 | 0.0002508 | 9.15e-05 | 3.81e-05 | 0.283369 | 0.364833 | 2.40157 | 0 | 2 |

### Hybrid threshold = 7
| n_vars | cm_time_s_median | cm_hybrid_time_s_median | cm_hybrid_no_reinflate_time_s_median | bitset_time_s_median | ratio_cm_hybrid_no_reinflate_over_cm | ratio_cm_hybrid_no_reinflate_over_cm_hybrid | ratio_cm_hybrid_no_reinflate_over_bitset | cm_hybrid_no_reinflate_final_cm_materialization_performed_median | cm_hybrid_no_reinflate_final_output_representation_code_median |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 0.0003945 | 0.0001861 | 0.0001355 | 9.00001e-06 | 0.343473 | 0.728103 | 15.0555 | 0 | 2 |
| 8 | 0.0003766 | 0.0002222 | 0.0001286 | 9.39996e-06 | 0.341476 | 0.578758 | 13.6809 | 0 | 2 |
| 12 | 0.0002993 | 0.0001702 | 0.0001212 | 2.1e-05 | 0.404945 | 0.712103 | 5.77142 | 0 | 2 |
| 16 | 0.000275 | 0.0002405 | 9.63e-05 | 3.91e-05 | 0.350182 | 0.400416 | 2.46292 | 0 | 2 |

### Hybrid threshold = 9
| n_vars | cm_time_s_median | cm_hybrid_time_s_median | cm_hybrid_no_reinflate_time_s_median | bitset_time_s_median | ratio_cm_hybrid_no_reinflate_over_cm | ratio_cm_hybrid_no_reinflate_over_cm_hybrid | ratio_cm_hybrid_no_reinflate_over_bitset | cm_hybrid_no_reinflate_final_cm_materialization_performed_median | cm_hybrid_no_reinflate_final_output_representation_code_median |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 0.0003422 | 0.0001625 | 0.0001118 | 8.2e-06 | 0.32671 | 0.688 | 13.6341 | 0 | 2 |
| 8 | 0.000497 | 0.0002005 | 0.0001789 | 1.28e-05 | 0.35996 | 0.892269 | 13.9766 | 0 | 2 |
| 12 | 0.0003236 | 0.0001796 | 0.0001273 | 2.84e-05 | 0.393387 | 0.708797 | 4.4824 | 0 | 2 |
| 16 | 0.0002692 | 0.00023 | 8.28e-05 | 4.91e-05 | 0.307578 | 0.36 | 1.68636 | 0 | 2 |

## 8. Interpretation
- Avoiding dense CM reinflation **materially improves** the hybrid runtime: `cm_hybrid_no_reinflate` is consistently faster than baseline CM and usually faster than current `cm_hybrid`, with improvements on the order of ~1.1× to ~2.7× vs `cm_hybrid` in these slices.
- The gap to pure bitset **narrows**, but does not disappear: `cm_hybrid_no_reinflate` is still ~1.7× to ~15× slower than the bitset backend in these runs, consistent with remaining overhead in CM IR compilation/reduction scaffolding (the no-reinflate backend still includes CM IR compilation in its timed window).
- Diagnostics confirm the central experimental condition: `cm_hybrid_no_reinflate_final_cm_materialization_performed_median = 0` (no dense CM output) while returning representation code `2` (packed bitset) for these runs.

## 9. Clear verdict
`Avoiding reinflation helps, but substantial non-reinflation overhead remains`

## 10. Remaining limitations
- The no-reinflate backend is benchmark-focused and does not attempt to retrofit the dense CM matrix contract; existing code paths expecting a CM matrix should continue to use `materialize_cm(...)`.
- These benchmarks use random expressions; `live_k` depends on how many variables appear in each expression, so “threshold” behavior is best interpreted in terms of *live variables* rather than the nominal `n_vars`.
- Further narrowing the gap to bitset likely requires reducing CM IR compilation/normalization overhead or caching/hoisting compile work out of the timed window for specific experimental comparisons.

