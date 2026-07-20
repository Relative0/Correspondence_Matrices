# cm_bench.py Refactor Notes

## Initial Exploration

- Workspace: `C:\Users\brian\Documents\CM_Computation`
- Primary script: `cm_bench.py`
- Current size: 6,227 physical lines
- Top-level functions: 104
- Top-level classes: 0
- Hotspots:
  - `time_backends_on_expr`: lines 2734-3931, 1198 lines
  - `run_bench`: lines 3934-4637, 704 lines
  - `main`: lines 5933-6223, 291 lines

## Required Local Modules

All directive-listed local modules were present in the repository root:

- `bitset_backend.py`
- `cm_build.py`
- `cm_exprlib.py`
- `cm_ir.py`
- `cm_normalize.py`
- `cm_operator_difference.py`
- `cm_parallel.py`
- `cm_remote_executor.py`
- `cm_runpod_client.py`
- `cm_runpod_config.py`
- `expr_simplify.py`
- `numba_backend.py`
- `cm_build_lazy.py`
- `cm_build_pair.py`

## Git Safety

The repository was already dirty before this refactor pass, including modifications to `cm_bench.py`, `cm_ir.py`, and existing tests plus multiple untracked benchmark/report files. Because the worktree was not clean, no safety branch was created or checked out in this pass.

## Phase 1 Baseline

- `python cm_bench.py --help` succeeds.
- Added `cmbench/` package scaffolding for timing, config, context, backend availability, enums, and result schema helpers.
- Added golden expression, truth-table conversion, CLI smoke, and CSV schema smoke tests.
- Migrated `expression_filter_reason` and `generate_benchmark_expr` to accept `BenchmarkConfig`, with the legacy global `args` path kept as a compatibility fallback.

## Phase 2 Exploration

- Date: 2026-06-27
- Git status summary: worktree was already dirty; notable existing changes include `cm_bench.py`, `cm_ir.py`, existing tests, new `cmbench/`, and multiple untracked reports/CSV files.
- Current test status: `pytest -q` passed before Phase 2 edits, `108 passed in 82.21s`.
- Existing cmbench files:
  - `cmbench/__init__.py`
  - `cmbench/availability.py`
  - `cmbench/config.py`
  - `cmbench/context.py`
  - `cmbench/enums.py`
  - `cmbench/timing.py`
  - `cmbench/results/__init__.py`
  - `cmbench/results/flatten.py`
  - `cmbench/results/schema.py`
- Remaining global args count before Phase 2 edits:
  - `getattr(args)`: 196
  - `args.` dot access: 106
- Largest functions still in `cm_bench.py`:
  - `time_backends_on_expr`: 1198 lines
  - `run_bench`: 706 lines
  - `main`: 294 lines
  - `print_summary_table`: 222 lines
  - `run_equivalence_bench`: 211 lines
  - `run_robdd_dd_backend`: 167 lines
  - `time_expression_family_workload`: 154 lines
  - `time_partial_context_workload`: 139 lines
- Optional backend availability issues:
  - `dd.cudd` unavailable: `ModuleNotFoundError("No module named 'dd.cudd'")`
  - `dd.autoref`, PyEDA, SymPy, Numba, lazy CM, pair CM, and RunPod modules available.

## Phase 2 Progress

### Completed

- Added missing `BenchmarkConfig` fields for:
  - `no_bdd_sop`
  - `equiv_pair_style`
  - `equiv_backends`
  - `equiv_compare_repeat`
- Added optional `config` and `ctx` parameters to:
  - `run_bench`
  - `run_equivalence_bench`
  - `run_partial_context_bench`
  - `run_expression_family_bench`
  - `time_backends_on_expr`
- Updated `main()` to pass the validated config and run context into benchmark runners.
- Updated `run_bench` to call `generate_benchmark_expr(..., return_tt_ref=True)` and pass the resulting independent truth table into `time_backends_on_expr`.
- Updated `run_equivalence_bench` to reuse the base expression truth table returned by `generate_benchmark_expr` instead of recomputing `tt_f`.
- Updated `time_backends_on_expr` so supplied `tt_ref` is reused and not recomputed.
- Updated SymPy, Espresso, Numba, BDD-SOP, CM, ROBDD/dd, and bitset correctness checks to prefer independent `tt_ref` when available.
- Added raw result columns:
  - `correctness_reference`
  - `tt_ref_available`
  - `tt_ref_source`
- Added `cmbench/results/equivalence.py` with `skipped_equiv_result()` for legacy skipped equivalence row schemas.
- Replaced repeated skipped dictionaries for bitset, CM, and SymPy equivalence rows.
- Added `cmbench/expr/visitors.py` with `expr_children()` and single-pass `collect_subtree_hashes_fast()`.
- Switched expression-family diagnostics to use `collect_subtree_hashes_fast()`.
- Added Phase 2 tests:
  - `tests/test_config_context_usage.py`
  - `tests/test_truth_table_reuse.py`
  - `tests/test_equiv_skipped_schema.py`
  - `tests/test_expr_visitors.py`
  - `tests/test_correctness_reference_columns.py`

### Deferred

- Full removal of global `args`.
- Full extraction of `time_backends_on_expr`.
- CM backend extraction.
- ROBDD/dd backend extraction.
- Replacing all repeated raw backend result dictionaries.
- Moving CLI parsing into `cmbench/cli.py`.
- Context-level bitset environment cache use in all runners; `run_bench` still keeps a local `bit_env_by_n` cache for compatibility.

### Remaining Global Coupling

- `getattr(args)` before: 196
- `getattr(args)` after: 130
- `args.` dot-access before: 106
- `args.` dot-access after: 83

### Truth Table Reuse

- Where `tt_ref` is now reused:
  - Normal benchmark generation in `run_bench`
  - `time_backends_on_expr` CM correctness
  - no-reinflate CM correctness where exact TT is available
  - SymPy correctness
  - Espresso correctness and simplification source table
  - Numba correctness
  - BDD-SOP correctness
  - bitset correctness
  - ROBDD/dd exact validation and optional extraction comparison
  - base expression table in `run_equivalence_bench`
- Where recomputation remains:
  - `expr_g` in equivalence benchmarks is still evaluated once after pair generation.
  - expression-family workloads still build per-variant truth tables locally.
  - operator-difference and transformation workflows were not touched in this pass.
- Why recomputation remains:
  - Those paths generate additional expressions after the initial expression-generation call or belong to deferred workloads outside this Phase 2 scope.

### Correctness Reference

- CM: exact comparisons now use independent `eval_expr_tt` table when available.
- SymPy: compares against `tt_ref` when available, with CM table only as fallback.
- Espresso: uses `tt_ref` as the simplification source and correctness reference when available, with CM table only as fallback.
- Numba: compares against `tt_ref` when available.
- ROBDD: `run_robdd_dd_backend` receives `tt_ref` from `time_backends_on_expr`.
- Bitset: compares extracted packed output against `tt_ref` when available.

### Tests

- Commands run:
  - `python cm_bench.py --help`
  - `pytest -q tests/test_config_context_usage.py tests/test_truth_table_reuse.py tests/test_equiv_skipped_schema.py tests/test_expr_visitors.py tests/test_correctness_reference_columns.py`
  - `pytest -q`
  - `python cm_bench.py --sizes 3 --trials 1 --max-depth 2 --out-prefix codex_phase2_smoke --print-summary`
  - `python cm_bench.py --bench-equivalence --sizes 3 --trials 1 --max-depth 2 --out-prefix codex_phase2_equiv --print-summary`
  - `python cm_bench.py --bench-partial-contexts --sizes 4 --trials 1 --max-depth 2 --partial-contexts 3 --out-prefix codex_phase2_partial --print-summary`
  - `python cm_bench.py --bench-expression-family --sizes 4 --trials 1 --max-depth 2 --family-size 4 --out-prefix codex_phase2_family --print-summary`
- Results:
  - Focused Phase 2 tests: `7 passed`
  - Full suite: `115 passed in 85.38s`
  - All smoke commands completed and wrote raw/summary CSV files.

## Phase 3 Preflight

- Date: 2026-06-27
- Git status summary: worktree was already dirty from prior phases and existing generated reports/CSV files; no unrelated changes were reverted.
- Baseline test status:
  - `python cm_bench.py --help`: passed
  - `pytest -q`: `115 passed in 89.47s`
- Baseline `getattr(args)` count: 130
- Baseline `args.` count: 83
- Existing cmbench package files:
  - `cmbench/__init__.py`
  - `cmbench/availability.py`
  - `cmbench/config.py`
  - `cmbench/context.py`
  - `cmbench/enums.py`
  - `cmbench/timing.py`
  - `cmbench/expr/__init__.py`
  - `cmbench/expr/visitors.py`
  - `cmbench/results/__init__.py`
  - `cmbench/results/equivalence.py`
  - `cmbench/results/flatten.py`
  - `cmbench/results/schema.py`
- Largest remaining functions:
  - `time_backends_on_expr`: 1212 lines
  - `run_bench`: 721 lines
  - `main`: 300 lines
  - `print_summary_table`: 222 lines
  - `run_equivalence_bench`: 195 lines
  - `run_robdd_dd_backend`: 167 lines
  - `time_expression_family_workload`: 164 lines
  - `time_partial_context_workload`: 140 lines
- Optional backend availability notes:
  - `dd.cudd` unavailable: `ModuleNotFoundError("No module named 'dd.cudd'")`
  - `dd.autoref`, PyEDA, SymPy, Numba, lazy CM, pair CM, and RunPod modules available.

## Phase 3 Progress

### Completed

- Expanded `BenchmarkConfig` coverage for output/reporting fields, CM parallel/debug/profile fields, RunPod local/fallback/stop flags, and additional validation.
- Added `BenchmarkRunContext` cache helpers:
  - `bitset_env()`
  - `eval_grid()`
  - `canonical_layout()`
  - `get_or_compute_tt()`
- Replaced direct global `args` reads in the normal CM timing path, partial-context workload, expression-family workload, and main output/depth handling where direct config equivalents existed.
- Added provenance fields:
  - equivalence raw rows: `equiv_correctness_reference`, `equiv_tt_f_available`, `equiv_tt_g_available`, `equiv_tt_source`
  - partial-context raw rows: `partial_reference_arrays_available_count`, `partial_reference_source`, `partial_correctness_reference`
  - expression-family raw rows: `family_tt_refs_available_count`, `family_tt_ref_source`, `family_correctness_reference`
- Added schema helper modules:
  - `cmbench/results/partial_context.py`
  - `cmbench/results/expression_family.py`
  - `cmbench/results/single_expr.py`
  - `cmbench/results/aggregation.py`
- Extended `BackendResult` with the requested `error()` constructor alias.
- Replaced selected partial/family skipped dictionaries with schema helpers.
- Added profiling harness documentation at `scripts/profile_cm_bench.md`.
- Added Phase 3 tests for config fields, context caches, provenance columns, skipped schemas, aggregation helpers, and `BackendResult` flattening.

### Deferred

- Full extraction of expression generators/diagnostics beyond the existing Phase 2 visitor extraction.
- ROBDD/dd backend extraction into `cmbench/backends/robdd_dd.py`.
- Full CLI extraction.
- Full replacement of local aggregation helper closures inside benchmark runners.
- Full removal of remaining global `args` reads in RunPod control flow, operator-difference workflows, and older compatibility paths.

### Global Coupling Counts

- `getattr(args)` before: 130
- `getattr(args)` after: 46
- `args.` dot-access before: 83
- `args.` dot-access after: 39

### Modules Created or Expanded

- Expanded:
  - `cmbench/config.py`
  - `cmbench/context.py`
  - `cmbench/results/schema.py`
- Created:
  - `cmbench/results/aggregation.py`
  - `cmbench/results/expression_family.py`
  - `cmbench/results/partial_context.py`
  - `cmbench/results/single_expr.py`
  - `scripts/profile_cm_bench.md`

### Functions Moved

- No additional functions were moved in Phase 3. Phase 2's expression visitor extraction remains in use.

### Output Schema Compatibility

- Legacy columns preserved: yes.
- New columns added:
  - `equiv_correctness_reference`
  - `equiv_tt_f_available`
  - `equiv_tt_g_available`
  - `equiv_tt_source`
  - `partial_reference_arrays_available_count`
  - `partial_reference_source`
  - `partial_correctness_reference`
  - `family_tt_refs_available_count`
  - `family_tt_ref_source`
  - `family_correctness_reference`
- Any aliases added:
  - `BackendResult.error()` aliases existing `BackendResult.error_result()`.

### Truth Table / Correctness Provenance

- Single-expression: existing `correctness_reference`, `tt_ref_available`, and `tt_ref_source` retained.
- Equivalence: records whether `tt_f` and `tt_g` were built and whether exact `eval_expr_tt` reference or a skipped large-n path was used.
- Partial-context: records reference array count and source for per-context reference arrays.
- Expression-family: records number of available per-variant truth tables and source.

### Tests Added

- `tests/test_config_phase3_fields.py`
- `tests/test_context_caches.py`
- `tests/test_workload_provenance_columns.py`
- `tests/test_results_skipped_schemas.py`
- `tests/test_aggregation_helpers.py`

### Verification

- Commands run:
  - `python cm_bench.py --help`
  - `pytest -q tests/test_config_phase3_fields.py tests/test_context_caches.py tests/test_workload_provenance_columns.py tests/test_results_skipped_schemas.py tests/test_aggregation_helpers.py`
  - `pytest -q tests/test_expression_family_bench.py tests/test_partial_context_bench.py tests/test_config_phase3_fields.py`
  - `pytest -q`
  - `python cm_bench.py --sizes 3 --trials 1 --max-depth 2 --out-prefix codex_phase3_smoke --print-summary`
  - `python cm_bench.py --bench-equivalence --sizes 3 --trials 1 --max-depth 2 --out-prefix codex_phase3_equiv --print-summary`
  - `python cm_bench.py --bench-partial-contexts --sizes 4 --trials 1 --max-depth 2 --partial-contexts 3 --out-prefix codex_phase3_partial --print-summary`
  - `python cm_bench.py --bench-expression-family --sizes 4 --trials 1 --max-depth 2 --family-size 4 --out-prefix codex_phase3_family --print-summary`
  - `python cm_bench.py --sizes 4 --trials 1 --max-depth 2 --cm-compare-no-reinflate --out-prefix codex_phase3_nr --print-summary`
- Results:
  - Focused new tests: `10 passed`
  - Compatibility focused tests: `13 passed`
  - Full suite after edits: `125 passed in 90.33s`
  - All required smoke commands passed and wrote raw/summary CSV files.

### Known Risks / Follow-Up

- `time_backends_on_expr` and `run_bench` remain large and should be split only with targeted schema tests.
- ROBDD/dd extraction remains a good next candidate, but should be done separately to avoid circular import and optional-backend risk.
- Some direct `args` reads intentionally remain in `main()`, RunPod command handling, and operator-difference workflows.

## Phase 4 Preflight

- Date: 2026-06-27
- Git status summary: worktree was already dirty from prior phase files, generated reports/CSVs, and existing modified files; no unrelated changes were reverted.
- Baseline test status:
  - `python cm_bench.py --help`: passed
  - `pytest -q`: `125 passed in 94.37s`
- Baseline `getattr(args)` count: 46
- Baseline `args.` count: 39
- Existing cmbench files:
  - `cmbench/availability.py`
  - `cmbench/config.py`
  - `cmbench/context.py`
  - `cmbench/enums.py`
  - `cmbench/timing.py`
  - `cmbench/__init__.py`
  - `cmbench/expr/visitors.py`
  - `cmbench/expr/__init__.py`
  - `cmbench/results/aggregation.py`
  - `cmbench/results/equivalence.py`
  - `cmbench/results/expression_family.py`
  - `cmbench/results/flatten.py`
  - `cmbench/results/partial_context.py`
  - `cmbench/results/schema.py`
  - `cmbench/results/single_expr.py`
  - `cmbench/results/__init__.py`
- Largest remaining functions:
  - `time_backends_on_expr`: 1212 lines
  - `run_bench`: 721 lines
  - `main`: 300 lines
  - `print_summary_table`: 222 lines
  - `run_equivalence_bench`: 195 lines
  - `run_robdd_dd_backend`: 167 lines
  - `time_expression_family_workload`: 164 lines
  - `time_partial_context_workload`: 140 lines
- Optional backend status:
  - `dd.cudd` unavailable: `ModuleNotFoundError("No module named 'dd.cudd'")`
  - `dd.autoref` available.

## Phase 5 Progress

### Completed

- Added stronger single-expression schema and selected value stability coverage for normal and no-reinflate rows.
- Added direct bitset equivalence utility tests.
- Added reporting summary-table stdout tests.
- Added CLI output compatibility coverage for raw/summary CSV file naming and representative columns.
- Extracted bitset equivalence checking to `cmbench/backends/bitset_utils.py`.
- Added Phase 5 single-expression helpers in `cm_bench.py`:
  - `SingleExprOptions`
  - `_single_expr_options`
  - `_init_single_expr_diagnostics`
  - `_ensure_tt_ref`
  - `_prepare_single_expr_bitset_envs`
  - `_generate_single_expr_trial`
  - `_run_single_expr_trial`
- Moved summary-table printers to `cmbench/reporting/summary_tables.py`, with compatibility wrappers left in `cm_bench.py`.
- Added `cmbench/reporting/__init__.py` and `cmbench/reporting/csv_io.py`.
- Moved remaining operator/workload mode reads into `BenchmarkConfig`.
- Removed remaining direct `args` reads from `cm_bench.py`.
- Updated `docs/cmbench_architecture.md` for Phase 5 layout and validation guidance.

### Deferred

- Full CM materialized/no-reinflate/remote/symbolic path extraction from `time_backends_on_expr`.
- Full aggregation/output extraction from `run_bench`.
- Full operator-difference module extraction.
- Full argparse parser extraction.

### Global Coupling Counts

- `getattr(args)` before: 15
- `getattr(args)` after: 0
- `args.` before: 6
- `args.` after: 0

### Functions Split

- `time_backends_on_expr`: option computation, diagnostic initialization, and TT reference setup split out.
- `run_bench`: bitset env preparation, trial generation, and per-trial row assembly split out.

### Functions Moved

- `bitset_equivalence_check` moved to `cmbench/backends/bitset_utils.py`.
- `print_summary_table` moved to `cmbench/reporting/summary_tables.py`.
- `print_partial_context_summary_table` moved to `cmbench/reporting/summary_tables.py`.
- `print_expression_family_summary_table` moved to `cmbench/reporting/summary_tables.py`.
- `print_operator_difference_summary_table` moved to `cmbench/reporting/summary_tables.py`.

### Modules Created or Expanded

- Created:
  - `cmbench/backends/bitset_utils.py`
  - `cmbench/reporting/__init__.py`
  - `cmbench/reporting/summary_tables.py`
  - `cmbench/reporting/csv_io.py`
  - `tests/test_bitset_utils.py`
  - `tests/test_reporting_summary_tables.py`
  - `tests/test_run_bench_output_compatibility.py`
- Expanded:
  - `cm_bench.py`
  - `cmbench/config.py`
  - `docs/cmbench_architecture.md`
  - `tests/test_single_expr_schema_stability.py`

### Largest Function Sizes

Before:
- `time_backends_on_expr`: 1212
- `run_bench`: 721
- `main`: 284
- `print_summary_table`: 222

After:
- `time_backends_on_expr`: 1200
- `run_bench`: 696
- `main`: 283
- `print_summary_table`: 4

### Output Schema Compatibility

- Legacy columns preserved: yes.
- New columns added: none to benchmark output rows.
- Any aliases added: none.
- Schema guard coverage now includes representative normal, no-reinflate, cached no-reinflate, correctness-reference, and CLI output-file columns.

### Tests Added

- `tests/test_bitset_utils.py`
- `tests/test_reporting_summary_tables.py`
- `tests/test_run_bench_output_compatibility.py`
- Expanded `tests/test_single_expr_schema_stability.py`

### Verification

- Commands run:
  - `git status --short`
  - `python cm_bench.py --help`
  - `pytest -q`
  - `pytest -q tests/test_single_expr_schema_stability.py tests/test_bitset_utils.py`
  - `pytest -q tests/test_single_expr_schema_stability.py tests/test_bitset_utils.py tests/test_reporting_summary_tables.py`
  - `pytest -q tests/test_config_phase3_fields.py tests/test_cli_helpers.py tests/test_operator_quotient.py tests/test_bench_integration.py -k "operator or equivalence or single_expr"`
  - `pytest -q tests/test_single_expr_schema_stability.py tests/test_bitset_utils.py tests/test_reporting_summary_tables.py tests/test_run_bench_output_compatibility.py tests/test_config_phase3_fields.py tests/test_cli_helpers.py tests/test_operator_quotient.py tests/test_bench_integration.py -k "operator or equivalence or single_expr or tiny_cli_run"`
  - `python cm_bench.py --sizes 3 --trials 1 --max-depth 2 --out-prefix codex_phase5_smoke --print-summary`
  - `python cm_bench.py --bench-equivalence --sizes 3 --trials 1 --max-depth 2 --out-prefix codex_phase5_equiv --print-summary`
  - `python cm_bench.py --bench-partial-contexts --sizes 4 --trials 1 --max-depth 2 --partial-contexts 3 --out-prefix codex_phase5_partial --print-summary`
  - `python cm_bench.py --bench-expression-family --sizes 4 --trials 1 --max-depth 2 --family-size 4 --out-prefix codex_phase5_family --print-summary`
  - `python cm_bench.py --sizes 4 --trials 1 --max-depth 2 --cm-compare-no-reinflate --out-prefix codex_phase5_nr --print-summary`
  - `python cm_bench.py --bench-equivalence --sizes 3 --trials 1 --max-depth 2 --equiv-backends cm,bitset,robdd --out-prefix codex_phase5_equiv_robdd --print-summary`
- Results:
  - Focused new schema/bitset tests: `7 passed`
  - Expanded focused tests: `10 passed`
  - Operator/config focused tests: `18 passed, 19 deselected`
  - Expanded Phase 5 focused tests: `26 passed, 22 deselected`
  - Full suite after edits: `159 passed in 53.68s`
  - All required smoke commands passed and wrote Phase 5 raw/summary CSV files.
  - ROBDD equivalence smoke passed with available `dd.autoref`; `dd.cudd` remains unavailable.

### Known Risks / Follow-Up

- `time_backends_on_expr` is still the main monolith; future work should split CM materialized paths, no-reinflate local/remote paths, bitset/Numba/symbolic backend paths, and row assembly behind the new schema tests.
- `run_bench` still owns the large aggregation spec; future extraction should move aggregation/output writing to package modules behind `tests/test_run_bench_output_compatibility.py`.
- Operator-difference workflows no longer read global `args`, but still should move to `cmbench/workloads/operator_difference.py`.

## Phase 4 Progress

### Completed

- Extracted dd-backed ROBDD helpers into `cmbench/backends/robdd_dd.py` and added `cmbench/backends/__init__.py`.
- Extracted expression evaluation helpers into `cmbench/expr/eval.py`.
- Extracted expression diagnostics into `cmbench/expr/diagnostics.py`.
- Extracted expression generators and benchmark-expression filtering into `cmbench/expr/generators.py`.
- Extracted equivalence pair helpers into `cmbench/expr/equivalence.py`.
- Extracted expression-family generation and subtree helpers into `cmbench/expr/families.py`.
- Extracted partial-context helpers into `cmbench/expr/partial_contexts.py`.
- Added `cmbench/cli.py` for size/depth parsing, preset mutation, config construction, and run-context construction.
- Kept `cm_bench.py` compatibility names by importing extracted helpers back into the script.
- Replaced additional global `args` reads with active `BenchmarkConfig` lookups for fields already represented in config.
- Added developer architecture note at `docs/cmbench_architecture.md`.

### Deferred

- Mechanical splitting of `time_backends_on_expr`; schema test coverage was added first, but the function was not split in this pass.
- Mechanical splitting of `run_bench`.
- Reporting/summary-table extraction.
- Full argparse parser extraction.
- Full operator-difference extraction; a few operator-specific CLI option reads remain as compatibility paths.
- Moving `bitset_equivalence_check` into `cmbench/backends/bitset_utils.py`.

### Global Coupling Counts

- `getattr(args)` before: 46
- `getattr(args)` after: 15
- `args.` before: 39
- `args.` after: 6

### Modules Created

- `cmbench/backends/__init__.py`
- `cmbench/backends/robdd_dd.py`
- `cmbench/cli.py`
- `cmbench/expr/diagnostics.py`
- `cmbench/expr/equivalence.py`
- `cmbench/expr/eval.py`
- `cmbench/expr/families.py`
- `cmbench/expr/generators.py`
- `cmbench/expr/partial_contexts.py`
- `docs/cmbench_architecture.md`

### Functions Moved

- ROBDD/dd:
  - `_dd_cudd_available`
  - `bdd_backend_identity`
  - `select_dd_module`
  - `safe_bdd_node_count`
  - `expr_vars_first_occurrence`
  - `robdd_variable_order`
  - `compact_order_repr`
  - `expr_to_dd_bdd`
  - `_declare_dd_vars`
  - `_try_collect_garbage`
  - `maybe_reorder_dd`
  - `bdd_function_value`
  - `extract_dd_bdd_truth_table`
  - `maybe_extract_dd_bdd_truth_table`
  - `validate_dd_bdd_correctness`
  - `_empty_robdd_dd_result`
  - `_empty_robdd_equiv_result`
  - `run_robdd_dd_backend`
  - `robdd_equivalence_check`
- Expression eval:
  - `eval_expr_assignment`
  - `result_value_for_assignment`
  - `sampled_correctness_check`
- Expression diagnostics/generators/equivalence/families/partial contexts:
  - `expr_complexity_diagnostics`
  - `truth_table_diagnostics`
  - `_expr_used_indices`
  - random expression style generators
  - `expression_filter_reason`
  - `generate_benchmark_expr`
  - `_rewrite_equiv_expr`
  - `generate_equiv_pair`
  - `pair_diagnostics`
  - `_no_reinflate_payload_equal`
  - expression-family subtree helpers and family diagnostics
  - partial-context generation/reference helpers

### Functions Split But Not Moved

- None. This pass prioritized module extraction and schema coverage before splitting the two largest runners.

### Output Schema Compatibility

- Legacy columns preserved: yes.
- New columns added: none.
- Any aliases added: none.
- Schema guard added for representative single-expression row fields, including no-reinflate fields.

### Largest Function Sizes

Before:
- `time_backends_on_expr`: 1212
- `run_bench`: 721
- `main`: 300
- `print_summary_table`: 222

After:
- `time_backends_on_expr`: 1212
- `run_bench`: 721
- `main`: 284
- `print_summary_table`: 222
- `run_robdd_dd_backend`: moved to `cmbench/backends/robdd_dd.py`
- `cm_bench.py` physical lines: 4830

### Tests Added

- `tests/test_robdd_dd_backend_module.py`
- `tests/test_expr_eval_module.py`
- `tests/test_expr_diagnostics_module.py`
- `tests/test_expr_generators_module.py`
- `tests/test_expr_equivalence_module.py`
- `tests/test_expr_families_module.py`
- `tests/test_expr_partial_contexts_module.py`
- `tests/test_single_expr_schema_stability.py`
- `tests/test_cli_helpers.py`

### Verification

- Commands run:
  - `python cm_bench.py --help`
  - `pytest -q tests/test_robdd_dd_backend_module.py tests/test_expr_eval_module.py tests/test_expr_diagnostics_module.py tests/test_expr_generators_module.py tests/test_expr_equivalence_module.py tests/test_expr_families_module.py tests/test_expr_partial_contexts_module.py tests/test_single_expr_schema_stability.py`
  - `pytest -q tests/test_cli_helpers.py tests/test_single_expr_schema_stability.py`
  - `pytest -q tests/test_cli_helpers.py tests/test_robdd_dd_backend_module.py tests/test_expr_eval_module.py tests/test_expr_diagnostics_module.py tests/test_expr_generators_module.py tests/test_expr_equivalence_module.py tests/test_expr_families_module.py tests/test_expr_partial_contexts_module.py tests/test_single_expr_schema_stability.py tests/test_bench_integration.py -k "equivalence or robdd or operator or single_expr"`
  - `pytest -q`
  - `python cm_bench.py --sizes 3 --trials 1 --max-depth 2 --out-prefix codex_phase4_smoke --print-summary`
  - `python cm_bench.py --bench-equivalence --sizes 3 --trials 1 --max-depth 2 --out-prefix codex_phase4_equiv --print-summary`
  - `python cm_bench.py --bench-partial-contexts --sizes 4 --trials 1 --max-depth 2 --partial-contexts 3 --out-prefix codex_phase4_partial --print-summary`
  - `python cm_bench.py --bench-expression-family --sizes 4 --trials 1 --max-depth 2 --family-size 4 --out-prefix codex_phase4_family --print-summary`
  - `python cm_bench.py --sizes 4 --trials 1 --max-depth 2 --cm-compare-no-reinflate --out-prefix codex_phase4_nr --print-summary`
  - `python cm_bench.py --bench-equivalence --sizes 3 --trials 1 --max-depth 2 --equiv-backends cm,bitset,robdd --out-prefix codex_phase4_equiv_robdd --print-summary`
- Results:
  - New module/schema tests: `20 passed`
  - CLI/schema tests: `5 passed`
  - Focused compatibility tests: `19 passed, 23 deselected`
  - Full suite after edits: `149 passed in 91.28s`
  - All Phase 4 smoke commands passed and wrote raw/summary CSV files.
  - ROBDD equivalence smoke passed with `dd.autoref`; `dd.cudd` remains unavailable.

### Known Risks / Follow-Up

- `time_backends_on_expr` and `run_bench` are still large and should be split in a follow-up behind `tests/test_single_expr_schema_stability.py`.
- Operator-difference helpers still own several compatibility `args` reads for options not yet represented in `BenchmarkConfig`.
- `cm_bench.py` keeps imported compatibility names for tests and older scripts; future cleanup can migrate callers to direct `cmbench.*` imports.
- Summary/reporting functions remain in the monolith.

## Phase 5 Preflight

- Date: 2026-06-27
- Git status summary: worktree was already dirty from prior phase edits, generated CSV/report files, new `cmbench/`, `docs/`, `scripts/`, and tests; no unrelated changes were reverted.
- Baseline test status:
  - `python cm_bench.py --help`: passed
  - `pytest -q`: `149 passed in 86.62s`
- Baseline `getattr(args)` count: 15
- Baseline `args.` count: 6
- Baseline largest function sizes:
  - `time_backends_on_expr`: 1212
  - `run_bench`: 721
  - `main`: 284
  - `print_summary_table`: 222
  - `run_equivalence_bench`: 195
  - `time_expression_family_workload`: 164
  - `time_partial_context_workload`: 140
- Existing cmbench package tree:
  - `cmbench/availability.py`
  - `cmbench/backends/__init__.py`
  - `cmbench/backends/robdd_dd.py`
  - `cmbench/cli.py`
  - `cmbench/config.py`
  - `cmbench/context.py`
  - `cmbench/enums.py`
  - `cmbench/expr/diagnostics.py`
  - `cmbench/expr/equivalence.py`
  - `cmbench/expr/eval.py`
  - `cmbench/expr/families.py`
  - `cmbench/expr/generators.py`
  - `cmbench/expr/partial_contexts.py`
  - `cmbench/expr/visitors.py`
  - `cmbench/results/aggregation.py`
  - `cmbench/results/equivalence.py`
  - `cmbench/results/expression_family.py`
  - `cmbench/results/flatten.py`
  - `cmbench/results/partial_context.py`
  - `cmbench/results/schema.py`
  - `cmbench/results/single_expr.py`
  - `cmbench/timing.py`
- Optional backend status:
  - `dd.cudd` unavailable: `ModuleNotFoundError("No module named 'dd.cudd'")`
  - `dd.autoref` available.
