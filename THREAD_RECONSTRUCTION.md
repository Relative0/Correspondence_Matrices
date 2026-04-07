# Thread Reconstruction

## 1. Executive Summary

- The thread centered on making the `CM_Computation` benchmark project understandable and runnable: dependency reconstruction, comprehensive docs, backend enablement questions, and interpretation of benchmark output.
- The workspace now contains the requested documentation artifacts:
  - `README.md`
  - `INSTALL.md`
  - `requirements.txt`
- The authoritative benchmark implementation is the root `cm_bench.py`, not `Updates to Integrate/cm_bench.py`.
- The user's long benchmark command maps to the root script and is supported there.
- The earlier confusion around optional algorithms and `NaN` output is explained by code-level gating:
  - some backends are optional by dependency,
  - some are disabled by `--no-*` flags,
  - some are automatically skipped above certain `n`,
  - backend exceptions are caught and converted to missing values.
- What is verified as real:
  - core CM benchmarking exists,
  - optional `dd`, `Espresso`, `SymPy`, ROBDD, and BDD->SOP code paths exist in the root script,
  - docs and requirements files exist in the repo.
- What remains conceptual or incomplete:
  - no verified script unification between the root and `Updates to Integrate` variants,
  - no proof in this pass that all optional backends were successfully installed and executed,
  - the existing docs appear broadly aligned with the root script but contain some formatting artifacts and at least one code/doc mismatch.

## 2. System Reality (Ground Truth)

### Authoritative script

- `cm_bench.py` at the project root is the real benchmark driver for the thread's later questions.
- It supports:
  - `--sizes`
  - `--trials`
  - `--seed`
  - `--max-depth`
  - `--depth-sweep`
  - `--out-prefix`
  - `--print-summary`
  - `--verbose`
  - `--no-robdd`
  - `--no-espresso`
  - `--no-bdd-sop`
  - `--no-sympy`
  - `--no-dd`
  - `--no-bitset`
  - `--no-numba`
  - `--cm-lazy`
  - `--cm-layout`
  - `--cm-hybrid-threshold`
  - `--cm-compare-hybrid`
  - `--cm-parallel`
  - `--cm-parallel-workers`
  - `--cm-parallel-min-n`
  - `--cm-parallel-min-nodes`
  - `--cm-parallel-chunk-rows`
  - `--cm-parallel-no-reuse-pool`
  - `--cm-parallel-no-shared-memory`
  - `--cm-parallel-shared-min-cells`
  - `--cm-debug-stats`
  - `--experiment`
  - `--html`

### Non-authoritative variant

- `Updates to Integrate/cm_bench.py` is a reduced variant.
- It only measures CM timing and writes a much smaller summary.
- It does not implement:
  - `--depth-sweep`
  - `--html`
  - `--no-robdd`
  - `--no-espresso`
  - `--no-bdd-sop`
  - `--no-sympy`
  - `--no-dd`
- It hard-codes aggregate backend availability fields such as `backend_dd` and `backend_espresso` to `False`.
- It imports `pysat`/`dd`/`pyeda` probes, but those do not become active benchmark backends there.

### Commands that map to real code

- This user-supplied command is valid for the root script:

```bash
python cm_bench.py --sizes 4,8,16 --trials 10 --depth-sweep 2,3,4,5 --verbose --print-summary --cm-lazy --out-prefix bench_sweep --html bench_sweep.html
```

- That same command does not match `Updates to Integrate/cm_bench.py`, because the reduced variant lacks `--depth-sweep` and `--html`.

### Documentation and dependency state

- `README.md` exists and is written around the root `cm_bench.py` feature set.
- `INSTALL.md` exists and documents environment setup and backend toggles.
- `requirements.txt` exists and contains:
  - `numpy>=2.0.0`
  - `sympy>=1.12`
  - `pandas>=2.2.0`
  - `pyeda>=0.28.0`
  - `dd>=0.5.9`
- This requirements file matches the root script's active dependency surface better than the reduced integration script.

## 3. Timeline (Most Recent -> Oldest)

### Reconstruction and clarification phase

- The final request asked for a deep reconstruction of the thread using both prior summary and live code verification.
- The second pass established that some earlier assumptions were stale:
  - docs and requirements already exist,
  - the root benchmark script is richer than the open integration copy,
  - backend behavior must be read from the root script for the later user questions to make sense.
- Outcome:
  - the thread state is best understood as a documentation/setup/interpretation effort around the root benchmark script, with an unresolved duplicate-script situation.

### NaN diagnosis phase

- The user asked why `espresso`, `dd`, and `bdd` columns contained `NaN`.
- Code review showed these columns become `NaN` whenever the underlying per-trial values remain `None`, and medians are computed only over non-null values.
- Root causes identified from code:
  - dependency unavailable,
  - backend disabled by flag,
  - backend skipped by size thresholds,
  - backend raised an exception and the exception was swallowed.
- Outcome:
  - `NaN` is a code-defined "not produced" result, not necessarily a numerical failure.

### Optional backend enablement phase

- The user asked to "turn them all on" and specifically questioned whether `Espresso` is computational.
- Code verification established:
  - `Espresso` is a real computational backend in the root script via `pyeda`.
  - `dd` is a real computational backend in the root script via `dd.autoref`.
  - `SymPy` and the in-repo ROBDD path are also real benchmark backends in the root script.
- The deeper conclusion was that most backends were already auto-enabled when available; the practical issue was environment/setup and script selection, not missing CLI switches.
- Outcome:
  - the problem space shifted from "implement enablement" to "understand gating and ensure dependencies are installed."

### Documentation request phase

- The user requested:
  - a detailed `README`,
  - a comprehensive installation guide,
  - a requirements file for recreating the virtual environment.
- The current repo state shows those artifacts now exist.
- Based on content, they are targeted at the root script and the long benchmark command the user supplied.
- Outcome:
  - documentation and dependency files are present by the end state of the thread.
- Remaining caveat:
  - the docs are not perfectly clean or perfectly synchronized with code.

### Initial dependency reconstruction phase

- The earliest visible request asked for a requirements file sufficient to rebuild the virtual environment and install all libraries needed to run the project.
- Final verified repo state shows `requirements.txt` exists and includes the core and optional benchmark packages.
- Outcome:
  - environment reconstruction is at least partially addressed in repository artifacts.

## 4. Implementations (Verified)

### `cm_bench.py`

- Current role:
  - primary benchmark driver at repo root.
- Verified behavior:
  - generates random Boolean expressions,
  - times multiple backends,
  - records per-trial results,
  - aggregates median timings and boolean correctness summaries,
  - supports depth sweeps,
  - writes CSV outputs,
  - optionally writes an HTML report.
- Verified backend logic:
  - CM compile path from `cm_build.py` or `cm_build_lazy.py`
  - in-repo ROBDD-from-truth-table path
  - `dd.autoref` path
  - `SymPy` simplify path
  - `Espresso` path through `pyeda`
  - BDD->SOP baseline via `expr_simplify.bdd_sop`

### `Updates to Integrate/cm_bench.py`

- Current role:
  - reduced or staging benchmark script.
- Verified behavior:
  - benchmarks only CM time,
  - writes raw and summary CSVs,
  - has a smaller CLI,
  - marks non-CM backend availability as false in aggregate output.
- Important implication:
  - it cannot be treated as the implementation behind the user's long command or later backend questions.

### `cm_build.py`

- Current role:
  - eager CM compiler.
- Verified behavior:
  - compiles expression AST nodes into a symbolic CM IR with `cm_ir.compile_expr_to_cm_ir`.
  - materializes a correspondence matrix with `cm_ir.materialize_cm`.
  - supports `materialize_mode` selection (`numpy`, `hybrid`, `partial_hybrid`) and a `hybrid_threshold` for bitset collapse.
- Purpose:
  - baseline/eager CM construction path when `--cm-lazy` is not used.

### `cm_build_lazy.py`

- Current role:
  - lazy CM compiler used by the root benchmark when import succeeds and `--cm-lazy` is supplied.
- Verified behavior:
  - builds the same CM IR as `cm_build.py`,
  - exposes cache controls for the IR alignment plan cache,
  - materializes via the same `materialize_mode`/`hybrid_threshold` controls.
- Purpose:
  - optimized CM compilation path for deeper trees / larger runs.

### `cm_ir.py`

- Current role:
  - canonical intermediate representation (IR) for CM compilation and materialization.
- Verified behavior:
  - compiles Boolean expressions into an IR DAG,
  - aligns subresults by variable set,
  - supports hybrid materialization that can collapse small-live-variable subproblems using the bitset backend.

### `cm_normalize.py`

- Current role:
  - CM normalization and layout support.
- Verified behavior:
  - creates canonical row/column layouts,
  - caches row/column bit permutation indexers with `lru_cache`,
  - provides matrix lifting and pointwise Boolean operations.
- Purpose:
  - structural support for the CM compilation pipeline.

### `cm_exprlib.py`

- Current role:
  - AST and Boolean evaluation utilities.
- Verified behavior:
  - defines `Var`, `Not`, `And`, `Or`, `Xor`, `Imp`, `Eqv`,
  - generates random expressions,
  - evaluates expressions over full truth tables,
  - includes Tseitin CNF utilities.
- Important clarification:
  - while Tseitin/CNF helpers exist, the authoritative root benchmark script does not currently benchmark a SAT backend.

### `expr_simplify.py`

- Current role:
  - simplification helpers used by the benchmark driver.
- Verified behavior:
  - converts ASTs to `SymPy` and calls `simplify_logic`,
  - provides `bdd_sop()` that builds a canonical non-minimized SOP string from the truth table.
- Purpose:
  - benchmarkable simplification baselines outside CM.

### `README.md`

- Current role:
  - high-level project overview and usage guide.
- Verified behavior:
  - documents the root benchmark script and the long example command,
  - explains flags and backends,
  - describes output files and troubleshooting.
- Verified caveats:
  - contains visible formatting/encoding artifacts in the current file contents,
  - includes at least one likely mismatch with code: it claims raw CSV includes expression strings, but `cm_bench.py` does not append an expression field to output rows.

### `INSTALL.md`

- Current role:
  - setup guide for virtual environment creation, dependency installation, verification, and backend selection.
- Verified behavior:
  - covers Windows and Unix-like setup,
  - points users to `requirements.txt`,
  - documents backend-disabling flags and a recommended first run.
- Verified caveats:
  - contains formatting/encoding artifacts in current contents,
  - broadly matches the root script but has not been runtime-validated in this pass.

### `requirements.txt`

- Current role:
  - environment reconstruction file.
- Verified behavior:
  - includes packages needed for core and optional root-script backends.
- Important clarification:
  - it does not include `pysat`, which is consistent with the root script because SAT is not an active benchmark backend there.

## 5. Backend / Algorithm State

### CM

- Implemented: yes
- Where:
  - `cm_bench.py`
  - `Updates to Integrate/cm_bench.py`
  - `cm_build.py`
  - `cm_build_lazy.py`
  - `cm_normalize.py`
- Activation state:
  - always part of the benchmark when truth-table construction is allowed by the script path in use.
  - lazy path is selected by `--cm-lazy` only if `cm_build_lazy.py` imports successfully.
- Notes:
  - in the root script, CM correctness is checked against `eval_expr_tt`.

### ROBDD (in-repo Python BDD from TT)

- Implemented: yes, in the root script only
- Activation state:
  - active when `n <= 16` and `--no-robdd` is not used.
- Effective usage:
  - real benchmark backend in the root script.
- NaN causes:
  - skipped automatically when `n > 16`,
  - disabled by `--no-robdd`.

### `dd.autoref`

- Implemented: yes, in the root script only
- Activation state:
  - active when package `dd` imports successfully and `--no-dd` is not used.
- Effective usage:
  - real optional benchmark backend.
- NaN causes:
  - `dd` package missing,
  - `--no-dd` passed,
  - runtime exception inside the guarded backend block.

### Espresso

- Implemented: yes, in the root script only
- Activation state:
  - active when `pyeda` imports successfully,
  - `n <= 16`,
  - `--no-espresso` is not used.
- Effective usage:
  - real optional computational backend.
- NaN causes:
  - `pyeda` missing,
  - `--no-espresso` passed,
  - automatic skip for `n > 16`,
  - exception during Espresso/SymPy conversion/evaluation.

### SymPy

- Implemented: yes, in the root script and helper module
- Activation state:
  - active when `n <= 16` and `--no-sympy` is not used.
- Effective usage:
  - real benchmark backend.
- NaN causes:
  - skipped for `n > 16`,
  - disabled by `--no-sympy`,
  - exception in import/simplification/evaluation.

### BDD->SOP

- Implemented: yes, through `expr_simplify.bdd_sop()` and invoked from the root script
- Activation state:
  - active when `n <= 8` and `--no-bdd-sop` is not used.
- Effective usage:
  - real but intentionally restricted baseline.
- NaN causes:
  - automatic skip for `n > 8`,
  - disabled by `--no-bdd-sop`,
  - exception during generation or evaluation.

### SAT / `pysat`

- Implemented as an active benchmark backend: no
- Code reality:
  - `Updates to Integrate/cm_bench.py` probes `pysat` and `Minisat22`,
  - but that script does not time or report a SAT backend in practice,
  - the authoritative root script does not expose SAT benchmarking at all.
- Conclusion:
  - SAT is not part of the real benchmark surface discussed later in the thread.

### Code-level truth about `NaN`

- In the root script, backend timings begin as `None`.
- If a backend is skipped or fails, the timing remains `None`.
- Aggregation uses `safe_median(s.dropna().median())`.
- Summary formatting prints `nan` for missing float medians.
- Therefore `NaN` in summary/output means "no successful timed values were produced for that backend/group", not necessarily "the algorithm computed an invalid numeric result."

## 6. Work That Was Considered But Not Done

- Script unification:
  - no verified consolidation of `cm_bench.py` and `Updates to Integrate/cm_bench.py`.
- Backend forcing in code:
  - no verified change that removes dependency-based gating or size-based skips.
- Full runtime validation:
  - this pass did not execute the benchmark to confirm all optional backends run end-to-end in the current environment.
- Documentation cleanup:
  - docs exist, but there is no verified cleanup of their formatting artifacts or factual drift.
- Output-schema cleanup:
  - no verified fix for summary/report inconsistencies such as the missing `backend_robdd` aggregate field.

## 7. Confirmed Completed Work

- The repository contains a benchmark driver with real multi-backend support at `cm_bench.py`.
- The repository contains supporting CM infrastructure:
  - `cm_build.py`
  - `cm_build_lazy.py`
  - `cm_normalize.py`
  - `cm_exprlib.py`
  - `expr_simplify.py`
- The repository contains user-facing setup/docs artifacts:
  - `README.md`
  - `INSTALL.md`
  - `requirements.txt`
- The long benchmark command discussed in the thread maps to the root `cm_bench.py`.
- The source-level explanation for optional backends and `NaN` output has been reconstructed and verified against code.

## 8. Gaps / Risks

- Duplicate-script risk:
  - users can easily confuse `cm_bench.py` with `Updates to Integrate/cm_bench.py`.
  - the focused/open file during the thread was the reduced integration variant, even though the user's later command targets the root script.
- Documentation drift risk:
  - existing docs broadly describe the root script, but at least one claim appears inaccurate relative to code.
  - formatting/encoding artifacts may reduce usability or readability.
- Environment uncertainty:
  - optional backend availability still depends on the active environment.
  - the existence of `.venv` contents suggests some packages may already be installed, but that does not prove the intended runtime environment is complete.
- Reporting inconsistency:
  - `print_summary_table()` references `backend_robdd`, but `run_bench()` does not populate that field.
  - consequence: the printed `ROBDD?` availability indicator is unreliable and likely always shows `N`.
- Backend gating can be mistaken for failure:
  - `NaN` values can arise from intentional skip logic rather than broken algorithms.
  - `Espresso`, `SymPy`, and ROBDD are automatically TT-gated at `n <= 16`; BDD->SOP is gated at `n <= 8`.
- Integration-directory divergence:
  - `Updates to Integrate` contains alternate copies of benchmark support files.
  - those copies are not obviously synchronized with the root versions and should not be assumed equivalent without explicit reconciliation.

