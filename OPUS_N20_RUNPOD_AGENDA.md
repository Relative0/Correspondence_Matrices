# N=18/20 RunPod Test Agenda — Supporting Document for Opus

Companion to `OPUS_KICKOFF_PROMPT.md`. This file holds the operational detail: how to run
the pod, what to measure, what will break at n=20, and what the deliverable looks like.

## 1. Why this campaign

Everything measured so far stops at n=16 (`--cm-max-full-output-vars` defaults to 16 —
`cm_bench.py:4513`, guard implemented at `cm_ir.py:1441-1494`). The open question is
whether CM — specifically the no-reinflate reduced-output path — remains correct and
competitive at n=18 and n=20, and how the *comparison methods* (raw bitset, ROBDD, `dd`)
scale alongside it. This is a measurement campaign, not a kernel-development task.

## 2. What n=20 actually costs (know before running)

- A bitset value at n=20 is a **2^20-bit bigint ≈ 128 KB**; a single AND/OR costs tens of
  µs. Per-expression eval is fine. Memory is not a concern for the DAG (10–20 nodes).
- The **oracle `eval_expr_tt` is the expensive part**: 2^20 Python evals per expression,
  roughly seconds-to-tens-of-seconds each. This is exactly what the RunPod worker is for —
  batch it remotely, keep it **outside timed windows** (fairness invariant).
- **Never materialize the full 2^20-row output** on the CM path. Keep
  `--cm-max-full-output-vars 16` so n=18/20 exercise the reduced-output guard; that guard
  *is itself a test subject* (confirm it triggers, confirm results still verify).
- Espresso and sympy at n=20 are impractical — run with `--no-espresso --no-sympy`.
  ROBDD and `dd` should be attempted but **time-boxed**; if a trial exceeds ~120 s,
  record it as a timeout finding rather than waiting.

## 3. RunPod operations (already built — do not rebuild)

- Config lives in `.env.runpod.local` (API key, pod id, worker URL, bootstrap token).
  The last provisioned pod was `x82z2pbpofhcgz` (2-vCPU CPU pod, $0.06/hr), left
  **stopped**; only its 10 GB volume persists.
- Lifecycle: start the pod (RunPod console or REST API) → `python cm_runpod_deploy.py
  --deploy` (mandatory after every restart: the container disk, including the boot-time
  numpy install, is wiped on stop; `--deploy` re-pushes worker files and relaunches the
  worker on port 8081) → run experiments → **stop the pod when done** (non-negotiable
  cost hygiene; verify with `python cm_runpod_deploy.py --status`, expect `EXITED`).
- Sanity check before experiments: `python cm_runpod_smoke_test.py`.
- Remote execution is engaged per-benchmark with `--cm-exec-target runpod`. Raw-CSV
  columns `cm_runpod_remote_exec_time_s` (compute on the pod) vs
  `cm_runpod_total_wall_time_s` (~6 s of proxy/readiness overhead per call) — report the
  former; the wall overhead means remote mode pays off for long batches only.
- If worker code changed locally, `--deploy` is also the update path.

## 4. Experiment matrix (suggested, re-rank as evidence dictates)

1. **Baseline extension sweep**: `--sizes 16,18,20 --trials 5 --cm-eval-repeat 100`
   (repeat matters less at n=20 where evals are 100s of µs, but keep ≥10), balanced
   layout, `--cm-compare-no-reinflate --cm-use-persistent-cache --cm-hybrid-threshold 7`,
   `--no-espresso --no-sympy --no-numba`. Local first for a small pilot (1 trial) to
   validate flags; the full sweep on RunPod.
2. **Regime split at scale**: same sweep with `--cm-profile-cached-exec` and
   `--cm-report-ir-breakdown` (separate runs — instrumentation off for headline numbers)
   to see whether the cached regime is still bitset-eval-dominated at 2^20-bit widths or
   has become bigint-op-bound.
3. **Guard behavior**: confirm `max_full_output_vars=16` routes n=18/20 through the
   reduced-output path (there is an explicit error message at `cm_ir.py:1491-1494` if the
   output width itself exceeds the guard — record how often that fires vs. clean
   reduced-output completion, per expression style).
4. **Comparison methods**: ROBDD and `dd` columns at 18/20 (time-boxed), raw bitset
   always. Espresso/sympy only at n≤12 in a separate control run if a cross-method table
   is wanted.
5. **Stretch (only if 1–4 are clean)**: `--cm-layout` variants and higher `--max-depth`
   at n=18 to see whether node count, not width, drives the residual.

## 5. Ground rules (unchanged from the Fable phases)

- Correctness oracle is `eval_expr_tt`; verify bit-identically, **outside timed windows**.
  At n=20 consider verifying a random subset of trials if full-oracle cost dominates the
  budget — but say so explicitly in the report.
- `python -m pytest -q` must stay **159/159** after any code change (expected: none, or
  flag-only additions). Use `.\.venv\Scripts\python.exe` locally.
- Do not reopen the dead ends in `FABLE_CM_HANDOFF.md` §6.
- Compare medians over ≥5 trials; report with instrumentation off.
- Extend `cmbench/results/schema.py` if you add columns; never remove diagnostics.
- A well-measured negative result ("n=20 infeasible because X, measured at Y") is a valid
  deliverable.

## 6. Deliverable

`CM_n20_feasibility_report.md` in repo root, in the style of the existing `CM_*_report.md`
files: setup, headline table (CM vs no-reinflate vs bitset vs ROBDD/dd at n=16/18/20),
regime analysis, guard findings, RunPod cost/wall-time accounting (pod-hours spent),
explicit verdict on n=20 feasibility, and recommended next steps. Keep the raw/summary
CSVs (`bench_n20_*`); note that `bench*_raw.csv`/`bench*_summary.csv` are gitignored, so
paste headline numbers into the report itself.
