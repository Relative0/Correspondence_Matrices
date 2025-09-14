## CM_Computation – Boolean backends, benchmarks, and correctness checks

This repo contains a compact framework for generating random Boolean expressions and benchmarking multiple ways to compute them. It focuses on a Correspondence-Matrix (CM) method and compares it against other backends such as SymPy logic simplification, a tiny in-repo ROBDD, optional dd.autoref (from the dd package), and Espresso (via pyeda). All backends are validated by truth-table equivalence checks that do not contaminate timing measurements.

### What you can do here
- Build an ambient CM representation (matrix) of a Boolean expression quickly and memory-efficiently (with a lazy compiler).
- Evaluate, simplify, or canonicalize the same expressions using multiple backends.
- Benchmark per-backend performance across numbers of variables and expression depths.
- Verify correctness with explicit truth-table comparisons and per-backend OK/NO status.
- Generate detailed CSVs and a pretty HTML report summarizing timings and correctness.

---

## Project layout (root)
- cm_bench.py – main benchmark driver; orchestrates expression generation, backend runs, timing, correctness checks, CSVs, and HTML.
- cm_build.py – eager CM builder used as fallback if lazy is disabled.
- cm_build_lazy.py – lazy CM compiler (recommended): broadcasts shapes during AST combines and materializes once at the end.
- cm_normalize.py – canonical lift, bit-permutation utilities (with LRU-cached permutation indexers), and pointwise CM ops.
- cm_exprlib.py – typed AST for Boolean expressions and vectorized truth-table evaluation (eval_expr_tt), plus Tseitin CNF (used only in theory here).
- expr_simplify.py – SymPy conversion and simplify wrapper; a canonical (non-minimized) BDD?SOP baseline.
- equirements.txt – minimal set of packages to run all backends (optional ones included).

Output artifacts (created by cm_bench.py):
- *_raw.csv – per-trial rows (timings and correctness for each run).
- *_summary.csv – per-n_vars medians and aggregate OK columns.
- *.html – a consolidated, styled report suitable for sharing.

---

## Installation

### 1) Create and activate a virtual environment (Windows PowerShell)
`powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
`

### 2) Install dependencies
`powershell
pip install -r requirements.txt
`

The optional backends are:
- pyeda (enables Espresso minimization and validation)
- dd (enables dd.autoref BDD backend)

If you prefer CM+SymPy only, you can remove those from equirements.txt.

---

## Quick start

Run a depth sweep at depths 2,3,4,5 across 4, 8, and 16 variables, with 10 trials each, using the lazy CM compiler. Print a console summary and write an HTML report:

`powershell
python cm_bench.py --sizes 4,8,16 --trials 10 --depth-sweep 2,3,4,5 --verbose --print-summary --cm-lazy --out-prefix bench_sweep --html bench_sweep.html
`

What you get:
- Per-depth CSVs: ench_sweep_d{depth}_raw.csv, ench_sweep_d{depth}_summary.csv
- A consolidated HTML report: ench_sweep.html with one table per depth (timings + correctness)
- A verbose progress log in the console for each backend and trial

---

## Command-line reference (cm_bench.py)

### Core arguments
- --sizes 4,8,16
  - Comma-separated list of numbers of variables to test.
  - For n = 16, CM builds a full truth table and enables correctness checks that rely on it.
- --trials 10
  - Number of random expressions per (n, depth).
- --max-depth 3
  - Maximum expression tree depth (if you are not using --depth-sweep).
- --depth-sweep 2,3,4,5
  - Comma-separated list of depths to sweep; each depth is run independently, and gets its own CSV pair. If this flag is omitted, only --max-depth is used.
- --seed 123
  - RNG seed to reproduce runs.
- --verbose
  - Print a progress line for each backend as it runs.
- --print-summary
  - Print a formatted table to the console for each depth.
- --out-prefix bench_sweep
  - Prefix for output CSV files.
- --html bench_sweep.html
  - Optional: write an attractive consolidated HTML report with one table per depth (styled and shareable).

### Backend toggles
- --cm-lazy
  - Use the lazy CM builder (recommended). Without it, the eager builder (cm_build.py) will be used.
- --no-sympy
  - Disable SymPy simplify backend.
- --no-robdd
  - Disable the tiny in-repo ROBDD built from the truth table.
- --no-dd
  - Disable the optional dd.autoref backend (requires the dd package).
- --no-espresso
  - Disable Espresso backend (requires pyeda).
- --no-bdd-sop
  - Disable the canonical BDD?SOP baseline. Note: even when enabled, it is automatically limited to n = 8 to avoid excessive runtime.

### Performance notes and limits
- The benchmark builds full truth tables for n = 16 to validate correctness; for larger n the TT-based checks are skipped by design.
- BDD?SOP validation is intentionally capped at n = 8.
- Espresso (pyeda) and SymPy correctness checks evaluate against the TT via NumPy vectorization; these checks run outside the timed windows of each backend.

---

## What each backend does
- **CM (Correspondence Matrix)**
  - A 2^(|R|) × 2^(|C|) bit matrix representing the function in a canonical product space. The lazy compiler performs broadcast-only alignment at combine time and materializes once at the end, saving memory traffic on deep trees.
  - Timing reported: compilation time (matrix construction). Correctness reported as CM_OK by comparing the CM truth table to an independent vectorized evaluation (eval_expr_tt).
- **SymPy**
  - Converts the AST to SymPy, calls simplify_logic(..., form= dnf), and validates by evaluating the simplified expression over the TT grid.
  - Timing includes only the SymPy simplification (not the validation grid evaluation).
- **ROBDD (Python)**
  - A tiny in-repo BDD built from the truth table (TT). Size and build time are reported. ROBDD_OK is OK when constructed from TT (it must match by construction).
- **dd.autoref (optional)**
  - Builds a BDD from the AST using the dd package; timing and node count are reported. (This is optional and depends on the dd package.)
- **Espresso (optional)**
  - Runs Espresso via pyeda to simplify the TT, converts the result to SymPy, evaluates it on the TT grid, and reports correctness.
- **BDD?SOP baseline**
  - A canonical DNF string derived from the TT (not minimized). Converted to SymPy and validated against the TT.
  - Automatically disabled at n > 8.

All correctness checks are done with vectorized evaluation and are not included in the timed sections for each backend.

---

## Output columns – how to read the summary
For each 
_vars, the console and HTML tables report:
- Timings (median of non-NaN per-trial values):
  - CM_med_s, ROBDD_med_s, dd_med_s, Sympy_simpl_med_s, BDD_SOP_med_s, Espresso_med_s
- Sizes:
  - ROBDD_nodes_med, dd_nodes_med
- Correctness flags:
  - CM_OK, Sympy_OK, Sympy_OK_count/trials, ROBDD_OK, BDD_SOP_OK, Espresso_OK
    - OK means the evaluated truth table equals the CM truth table.
    - -- means not applicable (e.g., backend disabled or not run for this n).
    - NO means a mismatch (should be investigated; random expressions can produce edge cases worth inspecting).

Additionally, the *_raw.csv has per-trial rows that include the randomly generated expression (in a compact string form), and per-trial correctness booleans.

---

## Examples

### A quick smoke test
`powershell
python cm_bench.py --sizes 4,8,16 --trials 3 --max-depth 3 --verbose --print-summary --cm-lazy --out-prefix bench_quick --html bench_quick.html
`

### Turn off Espresso and dd (keep CM + ROBDD + SymPy only)
`powershell
python cm_bench.py --sizes 4,8,16 --trials 10 --max-depth 4 --verbose --print-summary --cm-lazy --no-espresso --no-dd --out-prefix bench_core --html bench_core.html
`

### Disable SymPy as well (CM + ROBDD only)
`powershell
python cm_bench.py --sizes 4,8,16 --trials 10 --max-depth 3 --verbose --print-summary --cm-lazy --no-sympy --no-espresso --no-dd --out-prefix bench_cm --html bench_cm.html
`

---

## Reproducibility & fairness
- Randomness is controlled by --seed (default 123). Use the same seed to reproduce a run.
- Each backend’s primary timing excludes its correctness check and excludes TT grid assembly (the TT grid is cached per n for fairness and speed; correctness checks apply it uniformly across backends).
- CM correctness (CM_OK) is validated independently against eval_expr_tt to ensure the CM pipeline is self-consistent.

---

## Troubleshooting
- Command not recognized or Python code showing in your console: Make sure you’re running the commands from PowerShell, not from the Python REPL. If you see >>>, type exit() first.
- pyeda or dd not found: Install from equirements.txt or run pip install pyeda dd.
- Very slow runs at 16 vars with BDD?SOP: That backend is automatically limited to n = 8.
- CSVs/HTML not appearing: Ensure the working directory is the project root and that you have write permissions.

---

## How it works (quick technical notes)
- The lazy CM compiler aligns sub-expressions by variable name using size-1 axis insertion and NumPy broadcasting. It avoids intermediate duplication during recursive combines and materializes at the end into the canonical (2^|R|, 2^|C|) bit matrix.
- cm_normalize.py caches bit-permutation index arrays via unctools.lru_cache to lower overhead when (re)ordering axes repeatedly.
- Correctness uses vectorized NumPy truth-table evaluation (eval_expr_tt) in the same MSB-first convention (x0 slowest-changing bit) across all backends.

---

## License
This repository includes third-party libraries under their respective licenses (SymPy, pyeda/Espresso, dd). The benchmark glue code here is provided as-is for experimentation and evaluation.
