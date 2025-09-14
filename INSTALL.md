## Installation Guide for CM_Computation

This document explains how to set up a clean, reproducible environment for running the CM_Computation benchmarks and generating reports. It covers Windows, macOS, and Linux, includes optional backends, and provides troubleshooting steps.

---

## 1) Prerequisites

- Python: 3.10 – 3.13 (64-bit recommended)
- Pip: ensure it’s up to date (python -m pip install --upgrade pip)
- Git (optional): if you’re cloning the repository

Notes on optional backends:
- pyeda (Espresso) is pure Python and typically installs without compilers.
- dd (dd.autoref) installs prebuilt wheels on common platforms. If a wheel isn’t available, Windows may require Microsoft C++ Build Tools, and Linux may require basic build toolchains.

---

## 2) Create and activate a virtual environment

It’s best practice to isolate dependencies. From the project root:

### Windows (PowerShell)
`powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
`

### macOS / Linux (bash/zsh)
`ash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
`

To deactivate later, run deactivate.

---

## 3) Install required packages

By default the repo includes equirements.txt, which covers core dependencies (NumPy, SymPy, pandas) and optional backends (pyeda, dd) so you can run the complete benchmark suite out-of-the-box.

`ash
pip install -r requirements.txt
`

If you want a minimal CM + SymPy setup only, create a local file (e.g., equirements-min.txt) with just:
`
numpy>=2.0.0
sympy>=1.12
pandas>=2.2.0
`
Then install:
`ash
pip install -r requirements-min.txt
`

You can always add optional backends later:
`ash
pip install pyeda dd
`

---

## 4) Verify the installation

With your virtual environment activated:

`ash
python - << 'PY'
import numpy, sympy, pandas
print('NumPy:', numpy.__version__)
print('SymPy:', sympy.__version__)
print('pandas:', pandas.__version__)
try:
    import pyeda
    print('pyeda:', pyeda.__version__)
except Exception:
    print('pyeda: (not installed)')
try:
    import dd
    print('dd (present)')
except Exception:
    print('dd: (not installed)')
PY
`

You should see versions for the installed packages. It’s fine if optional ones are reported as  not installed when you intentionally skipped them.

---

## 5) First run

Try a small depth sweep and generate an HTML report (works even without optional backends):

`ash
python cm_bench.py \
  --sizes 4,8,16 \
  --trials 3 \
  --depth-sweep 2,3 \
  --verbose --print-summary --cm-lazy \
  --out-prefix bench_quick \
  --html bench_quick.html
`

- This writes per-depth CSVs (ench_quick_d{depth}_raw.csv and _summary.csv) and a consolidated ench_quick.html.
- The console summary shows median timings per backend and correctness flags (OK/NO/--).

For the full recommended command from the README:

`ash
python cm_bench.py --sizes 4,8,16 --trials 10 --depth-sweep 2,3,4,5 \
  --verbose --print-summary --cm-lazy \
  --out-prefix bench_sweep --html bench_sweep.html
`

---

## 6) Backend selection

You control which backends run via CLI flags (see README for full details):

- --cm-lazy            Use the optimized lazy CM builder (recommended)
- --no-sympy           Disable SymPy simplify backend
- --no-robdd           Disable tiny in-repo ROBDD from TT
- --no-dd              Disable dd.autoref (requires package dd)
- --no-espresso        Disable Espresso via pyeda
- --no-bdd-sop         Disable canonical BDD?SOP baseline (auto-limited to n = 8)

Examples:
- CM + SymPy only (no dd, no Espresso): add --no-dd --no-espresso
- CM only: add --no-sympy --no-robdd --no-dd --no-espresso --no-bdd-sop

---

## 7) Reproducibility

- Use --seed <int> (default 123) to keep the random expression set consistent across runs.
- CSVs record timings and correctness flags per trial; the HTML consolidates medians and OK/NO summaries.

---

## 8) Performance tips

- Prefer --cm-lazy for faster CM compilation at higher depths.
- BDD?SOP is intentionally capped at 
 = 8 to avoid long runs.
- The assignment grid used for correctness checks is cached per 
 to avoid recomputation and keep timing fair.
- If you only care about CM and SymPy, omit optional backends to reduce import overhead and installation time.

---

## 9) Troubleshooting

- I typed a command and got a Python syntax error: You likely ran a shell command inside the Python REPL. Exit the REPL with exit() and run the command from your shell (PowerShell/Terminal).
- ModuleNotFoundError: pyeda or dd: Install them via pip install pyeda dd or ensure your virtual environment is active.
- Windows C/C++ build errors when installing dd: Ensure you’re on a supported Python version and try pip install --upgrade pip wheel. If a wheel is unavailable, install Microsoft C++ Build Tools and retry.
- CSV/HTML files aren’t created: Confirm you are in the project root and have write permissions. The tool prints Wrote … paths after each run.
- Performance feels slow at depth 5 with SymPy on 16 vars: this can happen with some random trees. Reduce --trials, or omit --depth-sweep 5 for quick iteration.

---

## 10) (Optional) Conda environment

If you prefer Conda/Mambaforge:
`ash
conda create -n cmbench python=3.11 -y
conda activate cmbench
python -m pip install --upgrade pip
pip install -r requirements.txt
`

---

## 11) Updating dependencies

- To upgrade all packages to the latest allowed by equirements.txt:
`ash
pip install --upgrade -r requirements.txt
`
- To lock exact versions for long-term reproducibility, export your environment:
`ash
pip freeze > requirements.lock.txt
`

---

## 12) Where to go next

- See README.md for a detailed overview of command-line flags, backend descriptions, and how correctness is computed without polluting timing.
- Open ench_*.html in your browser to review results and verify correctness at a glance.
