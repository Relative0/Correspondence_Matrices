# ROBDD Baseline Optimization Report

## 1. Executive Summary

CUDD was not available in this environment. `dd.cudd` failed to import with `ModuleNotFoundError("No module named 'dd.cudd'")`. `dd.autoref` was available and the new fair ROBDD baseline therefore ran as `dd.autoref`.

New ROBDD backend support was added in `cm_bench.py`:

- legacy custom truth-table-to-ROBDD remains as `bdd_time_s` / `bdd_nodes`;
- clearer aliases now label it as `custom_tt_robdd_time_s`, `custom_tt_robdd_nodes`, and `custom_tt_robdd_ok`;
- legacy pure-Python `dd.autoref` AST timing remains as `dd_time_s` / `dd_nodes`, with robust node counting;
- new fair AST-to-dd ROBDD fields are reported under `robdd_*`, with backend identity, order policy, dynamic reordering status, correctness mode, and status/error fields.

The fair label for this environment is:

`ROBDD/dd.autoref, AST build, fixed order`

If `dd.cudd` is installed in a future environment, the same code will label it as:

`ROBDD/CUDD, AST build, fixed order`

## 2. Existing BDD Baseline Diagnosis

| Item | Present / Missing / Broken | Evidence | Planned action |
| --- | --- | --- | --- |
| Custom in-repo ROBDD from truth table | Present | `cm_bench.py` had `BDDTT` under the `ROBDD (Python) from TT` path and emitted `bdd_time_s`, `bdd_nodes`. | Preserved old fields and added `custom_tt_robdd_*` aliases. |
| Legacy `dd.autoref` AST path | Present but broken for node count | Existing code used `dd_nodes = mgr2.size`; installed `dd.autoref.BDD` has no `.size`. | Replaced with `safe_bdd_node_count(manager, root)` and kept timing even if counting fails. |
| CUDD backend | Missing in environment | `import dd.cudd` failed with `ModuleNotFoundError`. | Added runtime selection with `auto`, `cudd`, and `autoref`; CUDD-required runs report `unavailable`. |
| Variable order controls | Missing | Only fixed declaration order existed. | Added fixed, expression occurrence, random, and best-of-k order policies. |
| Dynamic reordering reporting | Missing | No `reorder` / `configure` path was used. | Added requested/available/used flags and separate reorder timing. In this environment it is unavailable because backend is `dd.autoref`. |
| Correctness for new ROBDD backend | Missing | Existing custom ROBDD marked ok from construction; dd path did not validate. | Added exact `eval_expr_tt` comparison for small `n`; sampled validation for large `n` when no full TT exists. |
| Timing semantics | Partly ambiguous | Old custom ROBDD builds from already materialized TT; dd path builds from AST. | New fields separate AST ROBDD build time, reorder time, total, and optional TT extraction placeholders. |

## 3. Implementation Changes

Changed file:

- `cm_bench.py`

Summary:

- Added `select_dd_module`, `bdd_backend_identity`, and runtime CUDD/autoref detection.
- Added `safe_bdd_node_count`, using `Function.dag_size`, manager statistics, or `len(manager)` where available.
- Added `expr_to_dd_bdd` for AST-to-dd conversion, including compatibility with older `dd.autoref` where `Function ^ Function` is unsupported.
- Added variable order helpers for fixed, first occurrence, random, and best-of-k random/static sweeps.
- Added dynamic reordering reporting fields. CUDD is required for actual dynamic reordering in this implementation.
- Added correctness validation outside timed build windows.
- Added CLI flags:
  - `--robdd-dd-backend {auto,cudd,autoref}`
  - `--no-robdd-dd`
  - `--robdd-order-policy {fixed,expr,random,best-of-k}`
  - `--robdd-order-seed INT`
  - `--robdd-order-sweeps INT`
  - `--robdd-dynamic-reordering`
  - `--robdd-reorder-method sift`
- Added explicit CSV fields including `robdd_build_time_s`, `robdd_node_count`, `robdd_backend`, `robdd_order_policy`, `robdd_status`, `robdd_error`, `robdd_ok`, and best/median/worst sweep fields.

## 4. Dependency / Installation Notes

Observed package state for the Python used by `python cm_bench.py`:

| Package | Version / status |
| --- | --- |
| `dd` | `0.5.7` |
| `dd.autoref` | available |
| `dd.cudd` | unavailable |
| `numpy` | `2.2.6` |
| `pandas` | `2.3.2` |
| `sympy` | `1.14.0` |
| `pyeda` | `0.29.0` |

Installation attempts:

- `python -m pip install --upgrade dd`: kept `dd 0.5.7` from the configured package index.
- `python -m pip install "dd[cudd]"`: completed but warned that `dd 0.5.7` does not provide the `cudd` extra.

Final backend used for successful ROBDD runs: `dd.autoref`.

## 5. Benchmark Semantics

`robdd_build_time_s` measures AST-to-ROBDD construction only. It does not include full truth-table extraction.

`robdd_reorder_time_s` is separate. In this environment it is blank because dynamic reordering was unavailable for `dd.autoref`.

`robdd_total_build_plus_reorder_time_s` is build plus any successful reorder time.

Correctness checking is outside the timed build window. For the smoke runs below, correctness mode was `exact_tt`.

The legacy `bdd_time_s` / `bdd_nodes` fields are still the custom fixed-order ROBDD built from an already materialized truth table. They are not an optimized CUDD baseline.

## 6. Benchmark Results

### Fixed order

Command:

```text
python cm_bench.py --sizes 4,8 --trials 2 --max-depth 3 --cm-layout balanced --robdd-dd-backend auto --robdd-order-policy fixed --print-summary --out-prefix smoke_robdd_fixed
```

| n | backend | build_time | nodes | ok | notes |
| --- | --- | --- | --- | --- | --- |
| 4 | dd.autoref | 0.00006295 | 3.5 | True | CUDD unavailable; exact TT check |
| 8 | dd.autoref | 0.00005895 | 3.5 | True | CUDD unavailable; exact TT check |

Explicit autoref fallback:

```text
python cm_bench.py --sizes 4,8,12 --trials 3 --max-depth 4 --cm-layout balanced --robdd-dd-backend autoref --robdd-order-policy fixed --print-summary --out-prefix bench_robdd_autoref_fixed
```

| n | backend | build_time | nodes | ok | notes |
| --- | --- | --- | --- | --- | --- |
| 4 | dd.autoref | 0.000071 | 4 | True | explicit fallback run |
| 8 | dd.autoref | 0.000118 | 6 | True | explicit fallback run |
| 12 | dd.autoref | 0.000097 | 6 | True | explicit fallback run |

### Expression order

Command:

```text
python cm_bench.py --sizes 4,8 --trials 2 --max-depth 3 --cm-layout balanced --robdd-dd-backend auto --robdd-order-policy expr --print-summary --out-prefix smoke_robdd_expr
```

| n | backend | build_time | nodes | ok | notes |
| --- | --- | --- | --- | --- | --- |
| 4 | dd.autoref | 0.00007060 | 3.5 | True | first occurrence order |
| 8 | dd.autoref | 0.00006610 | 3.5 | True | first occurrence order |

### Best-of-k

Command:

```text
python cm_bench.py --sizes 4,8,12 --trials 3 --max-depth 4 --cm-layout balanced --robdd-dd-backend auto --robdd-order-policy best-of-k --robdd-order-sweeps 10 --print-summary --out-prefix bench_robdd_bestofk
```

| n | backend | k | best_time | median_time | worst_time | best_nodes | median_nodes | worst_nodes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | dd.autoref | 10 | 0.00007290 | 0.00008160 | 0.00013780 | 4 | 4 | 5 |
| 8 | dd.autoref | 10 | 0.00012340 | 0.00013850 | 0.00035030 | 6 | 7 | 8 |
| 12 | dd.autoref | 10 | 0.00010670 | 0.00011790 | 0.00018630 | 6 | 7 | 8 |

### Dynamic reordering

Command:

```text
python cm_bench.py --sizes 4,8,12 --trials 3 --max-depth 4 --cm-layout balanced --robdd-dd-backend auto --robdd-order-policy fixed --robdd-dynamic-reordering --robdd-reorder-method sift --print-summary --out-prefix bench_robdd_reorder
```

| n | backend | method | build_time | reorder_time | nodes_before | nodes_after | total_time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | dd.autoref | sift | 0.00007450 | unavailable | 4 | 4 | 0.00007450 |
| 8 | dd.autoref | sift | 0.00011980 | unavailable | 6 | 6 | 0.00011980 |
| 12 | dd.autoref | sift | 0.00010850 | unavailable | 6 | 6 | 0.00010850 |

Dynamic reordering was requested but not used because the selected backend was `dd.autoref`, not CUDD.

### CUDD-required smoke

Command:

```text
python cm_bench.py --sizes 4 --trials 1 --max-depth 3 --cm-layout balanced --robdd-dd-backend cudd --robdd-order-policy fixed --print-summary --out-prefix smoke_robdd_cudd_required
```

Result: `robdd_status = unavailable`, `robdd_error = dd.cudd: ModuleNotFoundError("No module named 'dd.cudd'")`.

## 7. Fairness Assessment Versus CM / Bitset

ROBDD build time is not the same quantity as bitset truth-table execution. The new ROBDD baseline builds a canonical symbolic representation from the AST; it does not force full truth-table materialization.

CM's strength is structure-preserving reduction plus bitset execution and controlled materialization. ROBDD's strength is canonical symbolic representation and equivalence checking. Truth-table extraction from either side should be reported separately when it is part of the comparison.

Random expressions can be unfavorable for ROBDD because node count and runtime are highly order-sensitive. The new order-policy fields make this sensitivity visible instead of hiding it behind one label.

## 8. Recommended Labels for Slides / Paper

Old baseline:

`Custom fixed-order ROBDD from truth table`

New optimized baseline if CUDD works:

`ROBDD/CUDD, AST build, fixed order`

`ROBDD/CUDD, AST build, best-of-k variable order`

`ROBDD/CUDD, dynamic reordering`

Fallback used in this environment:

`ROBDD/dd.autoref, AST build, fixed order`

## 9. Recommended Caveat Text

The in-repo ROBDD result is a custom fixed-order ROBDD built from an already materialized truth table, so it is retained only as a compatibility baseline. The fair symbolic ROBDD comparison is the AST-to-dd baseline, preferably CUDD-backed when `dd.cudd` is available; in this environment it fell back to `dd.autoref`. ROBDD build time excludes full truth-table extraction, and any extraction or correctness validation is reported separately.

## 10. Final Verdict

It is now fairer to compare CM against ROBDD because the benchmark distinguishes the old truth-table-derived custom ROBDD from the AST-to-dd symbolic ROBDD and records the actual backend used.

The fair main baseline should be CUDD when available:

`ROBDD/CUDD, AST build, best-of-k variable order`

In this environment, the fair fallback label is:

`ROBDD/dd.autoref, AST build, best-of-k variable order`

The prior conclusion should be revisited only after CUDD-backed runs are available. Plots and slides should rename old `bdd_time_s` / `bdd_nodes` results to `Custom fixed-order ROBDD from truth table` and use the new `robdd_*` fields for the fair ROBDD baseline.
