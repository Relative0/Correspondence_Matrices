# CM_Computation

See the original paper here:
https://www.b-theory.com/CorrespondenceMatrices.pdf

This repository benchmarks and validates several Boolean-expression backends, centered on the Correspondence Matrix (CM) representation. The code in this repo is the source of truth for the benchmark flow, compiler options, and correctness checks.

## Publication materials

- **[Research library: read on GitHub or download](docs/research/README.md)** — Simple One-Pager, Technical Summary, all eight CM use cases, benchmark datasets/protocols, feature-model audits, and the verified Runpod memory smoke. Includes an offline interactive-explainer download and raw reproducibility material.
- [Master explainer](deliverables_n22_24/master_explainer_2026_08_03/index.html) — the fully sourced 2026-08-03 campaign website; see the [2026-08-25 correction report](deliverables_n22_24/corrections_2026_08_25/CM_BENCHMARK_AUDIT_CORRECTION_REPORT_2026-08-25.md) for the later B2/B4 structural-CSE result and updated scope.
- [Plain-language version](deliverables_n22_24/master_explainer_2026_08_03/layperson.html), [investor brief](deliverables_n22_24/master_explainer_2026_08_03/investor.html), and [expert summary](deliverables_n22_24/master_explainer_2026_08_03/expert.html).
- [Benchmark refresh claim map](deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md) — the authoritative map of confirmed, revised, and superseded claims.
- [Website build report](deliverables_n22_24/master_explainer_2026_08_03/CM_MASTER_EXPLAINER_BUILD_REPORT_2026-08-03.md), [publication-stabilization report](deliverables_n22_24/master_explainer_2026_08_03/CM_WEBSITE_PUBLICATION_STABILIZATION_2026-08-24.md), [visual/editorial expansion report](deliverables_n22_24/master_explainer_2026_08_03/CM_WEBSITE_VISUAL_EDITORIAL_EXPANSION_2026-08-24.md), and [UX/progressive-disclosure report](deliverables_n22_24/master_explainer_2026_08_03/CM_WEBSITE_UX_PROGRESSIVE_DISCLOSURE_2026-08-24.md).

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

RunPod execution is optional and never selected by default. It delegates the no-reinflate CM path to a remote worker that calls the same compiler/evaluator APIs:

```powershell
python cm_remote_worker.py --host 0.0.0.0 --port 8080
python cm_bench.py --cm-exec-target runpod --cm-compare-no-reinflate --sizes 4 --trials 1
python cm_runpod_smoke_test.py
```

Configure RunPod with `.env.runpod` or environment variables based on `.env.runpod.example`:

```env
RUNPOD_API_KEY=
RUNPOD_POD_ID=
CM_RUNPOD_BASE_URL=
CM_RUNPOD_PERSISTENT_ROOT=/workspace/cm-computation
CM_RUNPOD_START_TIMEOUT_SECONDS=300
CM_RUNPOD_STOP_AFTER_RUN=false
```

The direct RunPod smoke test checks only connectivity and worker discovery before any remote CM execution is attempted:

```bash
python cm_runpod_smoke_test.py
```

Expected status output:

```text
RunPod API: OK / FAILED
Pod status: RUNNING / STOPPED / UNKNOWN
Proxy URL: OK / FAILED
CM worker: FOUND / NOT FOUND
Next step: deploy cm_remote_worker.py if worker not found
```

If the proxy is serving JupyterLab instead of the CM worker, the smoke test reports: `RunPod pod reachable, but CM worker service is not deployed yet.`

`--cm-runpod-start` and `--cm-runpod-stop` manage pod lifecycle when `RUNPOD_POD_ID` and `RUNPOD_API_KEY` are configured. `--cm-runpod-fallback-local` is required for fallback; otherwise unavailable RunPod execution is reported as offline and not silently replaced with local results. RunPod benchmark output labels readiness wait, request roundtrip, remote CM execution time, and total wall time separately.

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

