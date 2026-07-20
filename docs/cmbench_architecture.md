# CM Bench Transitional Architecture

`cm_bench.py` is still the compatibility CLI and benchmark orchestrator, but stable helper code is now split into `cmbench/` modules.

## Current Layout

- `cmbench/config.py`: typed `BenchmarkConfig` plus CLI namespace conversion.
- `cmbench/context.py`: per-run caches for backend availability, bitset environments, grids, layouts, and truth tables.
- `cmbench/backends/bitset_utils.py`: bitset equivalence utility and legacy row schema.
- `cmbench/backends/robdd_dd.py`: dd-backed ROBDD build, ordering, extraction, correctness, and equivalence helpers.
- `cmbench/expr/eval.py`: assignment evaluation and sampled correctness helpers.
- `cmbench/expr/diagnostics.py`: expression and truth-table diagnostics.
- `cmbench/expr/generators.py`: random expression styles and benchmark-expression filtering.
- `cmbench/expr/equivalence.py`: equivalence-pair generation and no-reinflate payload comparison.
- `cmbench/expr/families.py`: expression-family generation and structural reuse diagnostics.
- `cmbench/expr/partial_contexts.py`: partial-context generation, reference arrays, and fixed-context bitset evaluation.
- `cmbench/cli.py`: safe CLI helper logic for presets, size/depth parsing, config creation, and context creation.
- `cmbench/reporting/summary_tables.py`: summary-table printers for normal, equivalence, partial-context, expression-family, and operator-difference outputs.
- `cmbench/reporting/csv_io.py`: small CSV write helper for future output extraction.
- `cmbench/results/*`: skipped-result schemas, flattening, and aggregation helpers.

## Benchmark Workflows

- Normal single-expression benchmarking still runs through `run_bench()` and `time_backends_on_expr()` in `cm_bench.py`, with Phase 5 helpers for option computation, diagnostic initialization, bitset environment preparation, trial generation, and per-trial row assembly.
- Equivalence, partial-context, and expression-family benchmarks still live in `cm_bench.py`, but now depend on extracted expression and ROBDD helpers.
- Operator-difference and CM-transformation workflows remain largely monolithic, but their CLI settings now flow through `BenchmarkConfig` instead of direct global `args` reads.

## Result Schema Strategy

CSV compatibility is preserved by keeping public row keys unchanged. New modules return the same legacy dictionaries as the original helpers, and tests assert representative schema subsets rather than exact column ordering.

To validate schema compatibility after a backend or workload change, run:

```powershell
pytest -q tests/test_single_expr_schema_stability.py tests/test_run_bench_output_compatibility.py
```

For no-reinflate and cached-execution columns, use a config with `cm_compare_no_reinflate=True`, `cm_eval_repeat > 1`, and `cm_compile_once_per_expression=True`.

## Adding Backends

Add backend-specific logic under `cmbench/backends/` when it can avoid importing `cm_bench.py`. Keep the returned row keys identical to the legacy keys used by CSV output, then import the helper back into `cm_bench.py` only as a compatibility name or runner dependency.

## Adding Workloads

New workload helpers should prefer `BenchmarkConfig` and `BenchmarkRunContext` parameters over global state. Put expression generation or diagnostics under `cmbench/expr/`, skipped-row schemas under `cmbench/results/`, and print-only reporting under `cmbench/reporting/`.

## Remaining Monolith Areas

- `time_backends_on_expr()` remains the largest function. Phase 5 split option/diagnostic setup, but CM materialized/no-reinflate/remote/symbolic paths are still embedded.
- `run_bench()` still owns the large aggregation spec. Phase 5 split preparation and per-trial execution, but summary aggregation should move later behind output compatibility tests.
- Operator-difference helpers still mix expression generation, backend timing, and aggregation, though direct `args` coupling has been removed.
- Full argparse parser construction still lives in `main()`.

## Verification

Typical local checks:

```powershell
python cm_bench.py --help
pytest -q
python cm_bench.py --sizes 3 --trials 1 --max-depth 2 --out-prefix smoke --print-summary
python cm_bench.py --bench-equivalence --sizes 3 --trials 1 --max-depth 2 --out-prefix smoke_equiv --print-summary
python cm_bench.py --bench-partial-contexts --sizes 4 --trials 1 --max-depth 2 --partial-contexts 3 --out-prefix smoke_partial --print-summary
python cm_bench.py --bench-expression-family --sizes 4 --trials 1 --max-depth 2 --family-size 4 --out-prefix smoke_family --print-summary
```

Use `scripts/profile_cm_bench.md` for profiling-oriented commands.
