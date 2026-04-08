# CM_Computation

See the original paper here:
https://www.b-theory.com/CorrespondenceMatrices.pdf

This repository benchmarks and validates several Boolean-expression backends, centered on the Correspondence Matrix (CM) representation. The code in this repo is the source of truth for the benchmark flow, compiler options, and correctness checks.

## What the project does

- Builds CM representations for Boolean expressions with eager, lazy, pair-aware, and parallelized compilation paths.
- Compares CM against SymPy, a small in-repo ROBDD, optional `dd.autoref`, Espresso via `pyeda`, a bitset evaluator, a Numba evaluator, and a canonical `BDD->SOP` baseline.
- Verifies backend correctness against explicit truth-table evaluation without contaminating the main timing windows.
- Writes per-trial CSV output, per-size summary CSV output, and an HTML report.

## Project layout

- `cm_bench.py`: main benchmark driver and report generator.
- `cm_build.py`: standard CM compiler through the shared CM IR.
- `cm_build_lazy.py`: lazy CM compiler that defers materialization.
- `cm_build_pair.py`: experimental pair-aware CM compiler for row/column two-variable subproblems.
- `cm_parallel.py`: parallel CM materialization path.
- `cm_normalize.py`: layout, lifting, permutation caching, and pointwise CM operations.
- `cm_exprlib.py`: Boolean AST, random expression generation, and vectorized truth-table evaluation.
- `cm_token.py` / `cm_pair.py`: small utilities used by the pair-aware path.
- `cm_render.py` / `cm_lm.py`: helper utilities for rendering and language-model related experiments.
- `expr_simplify.py`: SymPy simplification and `BDD->SOP` baseline support.
- `requirements.txt`: optional and required Python dependencies.

Output artifacts written by `cm_bench.py`:

- `*_raw.csv`: per-trial timings, correctness flags, and diagnostic fields.
- `*_summary.csv`: per-`n_vars` medians and aggregate status flags.
- `*.html`: consolidated benchmark report.

## Installation

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

Optional packages:

- `pyeda` enables the Espresso backend.
- `dd` enables the `dd.autoref` backend.
- `numba` enables the Numba evaluator.

## Quick start

Run a small depth sweep with the lazy compiler, console summary, and HTML output:

```powershell
python cm_bench.py --sizes 4,8,16 --trials 10 --depth-sweep 2,3,4,5 --verbose --print-summary --cm-lazy --out-prefix bench_sweep --html bench_sweep.html
```

This produces:

- `bench_sweep_d{depth}_raw.csv`
- `bench_sweep_d{depth}_summary.csv`
- `bench_sweep.html`

## Command-line notes

Important core flags:

- `--sizes 4,8,16`
- `--trials 10`
- `--max-depth 3`
- `--depth-sweep 2,3,4,5`
- `--seed 123`
- `--verbose`
- `--print-summary`
- `--out-prefix bench_name`
- `--html bench_name.html`

CM-specific flags:

- `--cm-lazy`: use the lazy CM compiler instead of the eager path.
- `--cm-pair`: run the baseline CM path through the pair-aware compiler when possible.
- `--cm-layout {balanced,legacy_square}`: choose the row/column layout strategy.
- `--cm-compare-hybrid`: also benchmark hybrid and partial-hybrid CM materialization modes.
- `--cm-hybrid-threshold N`: threshold used by hybrid materialization.
- `--cm-parallel`: enable the parallel CM path.

Backend toggles:

- `--no-sympy`
- `--no-robdd`
- `--no-dd`
- `--no-espresso`
- `--no-bdd-sop`
- `--no-bitset`
- `--no-numba`

## Backend summary

- `CM`: the standard correspondence-matrix build and truth-table extraction path.
- `CM pair`: experimental pair-aware acceleration for subexpressions that reduce to one row variable and one column variable after fixed assignments are applied.
- `CM hybrid` / `CM partial hybrid`: alternative materialization modes for the same CM IR.
- `CM parallel`: parallelized CM materialization.
- `Bitset`: packed-bit evaluator used as a fast comparison point.
- `Numba`: JIT-backed truth-table evaluator when `numba` is installed.
- `SymPy`: symbolic simplification with vectorized validation.
- `ROBDD`: small in-repo ROBDD built from the truth table.
- `dd.autoref`: optional BDD package backend.
- `Espresso`: optional `pyeda` minimization path.
- `BDD->SOP`: canonical, non-minimized SOP baseline, automatically limited to `n <= 8`.

All correctness checks are performed outside the main timed windows.

## Output columns

The summary tables report medians for timing and size columns plus aggregate correctness flags such as:

- `CM_OK`
- `CM_hybrid_OK`
- `CM_partial_hybrid_OK`
- `CM_parallel_OK`
- `Bitset_OK`
- `Numba_OK`
- `Sympy_OK`
- `ROBDD_OK`
- `BDD_SOP_OK`
- `Espresso_OK`

When `--cm-pair` is enabled and pair collapses actually occur, the summary also includes:

- `pair_attempts`
- `pair_collapses`
- `pairable_ratio`
- `pair_nodes_total`

`OK` means the backend matched the CM truth table. `NO` means a mismatch. `--` means the backend did not run for that configuration.

## Example commands

Quick smoke test:

```powershell
python cm_bench.py --sizes 4,8,16 --trials 3 --max-depth 3 --verbose --print-summary --cm-lazy --out-prefix bench_quick --html bench_quick.html
```

Core run without Espresso or `dd`:

```powershell
python cm_bench.py --sizes 4,8,16 --trials 10 --max-depth 4 --verbose --print-summary --cm-lazy --no-espresso --no-dd --out-prefix bench_core --html bench_core.html
```

Pair-aware CM run:

```powershell
python cm_bench.py --sizes 4,8 --trials 5 --max-depth 4 --cm-pair --no-dd --no-espresso --print-summary
```

## Technical notes

- The lazy CM compiler aligns subexpressions by variable name using shape insertion plus NumPy broadcasting, then materializes once at the end.
- `cm_normalize.py` caches permutation metadata with `functools.lru_cache` to reduce repeated layout overhead.
- The pair-aware compiler now honors fixed assignments and forwards diagnostics and materialization options through the standard CM compiler when it cannot collapse a subtree into a token pair.
- Truth-table evaluation uses a consistent MSB-first convention where `x0` is the slowest-changing bit.

## Troubleshooting

- If a command appears in a Python REPL, exit the REPL first and run it from PowerShell.
- If `pyeda`, `dd`, or `numba` are missing, install them with `pip` or via `requirements.txt`.
- If HTML or CSV output does not appear, make sure you are running from the repository root and have write permission.
- If a backend is very slow at higher variable counts, disable it with the corresponding `--no-*` flag and compare the remaining backends first.

## License

This repository depends on third-party libraries under their own licenses, including SymPy, `pyeda`/Espresso, `dd`, and optionally Numba. The project code here is intended for experimentation, validation, and benchmarking.

