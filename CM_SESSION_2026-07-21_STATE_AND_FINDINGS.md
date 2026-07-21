# CM Session 2026-07-21 — State, Updates & Findings (consolidated handoff)

> Single entry point for everything done in the 2026-07-21 session: the n=22/24 feasibility
> extension, the full pre-publication audit, the CM↔Bitset convergence study, and the C1a
> flat-evaluator implementation + fairness control. Pairs with the older
> [`FABLE_CM_HANDOFF.md`](FABLE_CM_HANDOFF.md) (system map) and
> [`FABLE_CM_SPEEDUP_AGENDA.md`](FABLE_CM_SPEEDUP_AGENDA.md) (older agenda), which remain
> valid for architecture but predate this session.
>
> Commits this session (on `main`): `86301e0` (n=18–24 campaign + audit), `f60e36a` (C1a
> flat evaluator), `b20ba35` (fair-bitset control). Working tree clean.

---

## 0. TL;DR — what changed and what to believe

1. **Feasibility extended to n=22 and n=24.** The CM `hybrid_no_reinflate` reduced-output
   path is feasible and bit-correct **iff `live_k ≤ 16`** (the `--cm-max-full-output-vars`
   guard). Runtime tracks the *reduced live-variable count*, not nominal `n`.
2. **A code change (R3, from the prior session) was the real enabler of n>16**, not anything
   in this session — a vectorized bitset env-build. Re-measured and confirmed here.
3. **C1a flat evaluator implemented** (`--cm-flat-eval`), verified bit-exact, `pytest` 159/159.
   It closes the cached-regime gap: CM per-eval now **at or below** the raw-bitset baseline.
4. **Honest headline (do not overstate):** against a *fair* flattened-bitset control, CM is
   **parity to ~1.4× faster**, i.e. "matches best-practice bitset and adds structure" — the
   "2× vs bitset" figure only holds against the *recursive* bitset walk.
5. **Environment caveats a reviewer will check:** the `.venv` is **Python 3.13.5** (not the
   3.10.11 stated in older docs); the test suite runs on **system Python 3.10.11**; **CUDD
   does not run on this Windows box** (only pure-Python `dd.autoref`).

---

## 1. Environment (verified this session)

| Item | Value |
|---|---|
| Benchmark interpreter | **Python 3.13.5**, `.\.venv\Scripts\python.exe`, numpy 2.3.2, dd 0.6.0 |
| Test interpreter | **Python 3.10.11** (system), pytest 9.0.2 — the venv has no pytest |
| `python -m pytest -q` | **159 passed** (~7 min), confirmed after the C1a change |
| CUDD (`dd.cudd`) | **not importable** on native Windows; harness `robdd_backend = dd.autoref` |
| RunPod | pod `x82z2pbpofhcgz` left **EXITED**; unused this session (0 pod-hours) |

---

## 2. The five findings, each with its report and the numbers that matter

### 2.1 n=22/24 feasibility → [`deliverables_n22_24/CM_n22_24_feasibility_report.md`]
- CM reduced no-reinflate is feasible/correct at n=18–24 **iff `live_k ≤ 16`**; cost tracks
  `live_k` (sub-20 µs cached at n≥18), flat in nominal `n`.
- **0 mismatches across 40,000 sampled-oracle checks** (n=16–24).
- Guard declines `live_k > 16` (the `cm_ir.py:~1491` `ValueError`) — by design, not a bug.
- Tables: `CM_n16_24_headline.csv`, `CM_n16_24_guard_rate.csv`, `CM_n16_24_scaling.csv`.

### 2.2 Pre-publication audit → [`deliverables_n22_24/CM_ARCHITECTURE_AND_AUDIT.md`] (the big one)
- **Why n>16 was impossible before / what changed:** the old `_build_bitset_env_cached` used
  an O(n·2^n) pure-Python big-integer loop (on the hot path of *every* bitset eval).
  Re-measured: **120 ms (n=16) → 1.4 s (n=18) → 20.6 s (n=20) → >2 min (n=22/24)**. R3
  (commit `041fd18`, prior session) vectorized it with `numpy.packbits`; now **2.8 s at
  n=24**, output **bit-identical**. Table: `CM_env_build_cliff.csv`.
- **Exhaustive correctness:** 74 expressions, n=16–24, **all 2^n rows** — CM-reduced, raw
  bitset, and CM-IR bitset all bit-identical to the independent `eval_expr_tt` oracle
  (`CM_correctness_audit.csv`).
- **"Decline" / selection bias (§6.2 — important for the paper):** at `--max-depth 4`
  (the paper's setting) a depth-d tree has ≤ 2^d leaves, so **≤16 live vars regardless of n**
  → 0% declined but *nothing is a genuine >16-var function*. At depth ≥5 a growing fraction
  declines, and the summary median is a **NaN-skipping median over survivors only** (no
  explicit decline count). `CM_decline_rate_by_depth.csv`.
- **How to compute >16-var functions (§8.1):** the guard is already a parameter —
  `--cm-max-full-output-vars N` (or API `max_full_output_vars=None`). Demonstrated exact full
  output to n=24 (555 MB, 4.1 s). RAM wall ~n=26–28. **Caveat:** in that regime CM's output
  *is* the full 2^n table (same kernel as bitset) — no reduced advantage.
- **Correction logged:** an earlier report line said "ROBDD unavailable on Windows." Precise
  truth: **CUDD** unavailable; **ROBDD via `dd.autoref` ran and is correct** (`exact_tt`).

### 2.3 Convergence study → [`deliverables_n22_24/CM_convergence_findings.md`]
- Full-output, full-arity, cached per-eval, **recursive kernel**: CM/Bitset ratio falls
  **1.67× (n=16) → 1.31× (n=24)**, monotonic. `CM_convergence_fulloutput.csv`.
- Structural floor ≈ **0.5×**: the canonicalized CM IR DAG has ~half the nodes of the raw
  Expr tree (interning/sharing), so once per-node overhead amortizes CM does *fewer*
  big-integer ops. This motivated C1a.

### 2.4 C1a flat evaluator → [`deliverables_n22_24/CM_c1a_flat_eval_report.md`]
- Lower the interned DAG once to a linear postorder program (`compile_flat`), execute with a
  slot interpreter + per-`(vars_key, fixed)` bound templates. Opt-in `--cm-flat-eval` /
  `flat_eval=True`; recursive kernel stays default + reference. Code in `bitset_backend.py`
  (`FlatProgram`, `compile_flat`, `get_flat_program`, `_bind_flat_program`,
  `eval_cm_node_flat`), hook in `cm_ir.py`, flag in `cm_bench.py`/`cmbench/config.py`.
- **Verification: 1,104-check sweep, 0 failures** (flat == recursive == oracle over all 2^n
  rows, incl. fixed vars, thresholds 3/7, reduced-output n=20/24); **pytest 159/159**.
- **Cached depth-4, flat/bitset:** 1.12 / 1.00 / 1.00 / **0.72** at n=4/8/12/16 (was
  2.47/2.29/1.73/1.53 recursive). Full-output: 0.85–0.97× at n=16–24.
  `CM_c1a_cached_before_after.csv`, `CM_c1a_convergence_before_after.csv`.

### 2.5 Fair-bitset control (§4.1 of the C1a report) → `CM_fair_bitset_control.csv`
- Built a **flattened raw-AST bitset** (the speedup a bitset user could apply with no CM
  machinery), verified bit-exact. Generic flattening speeds raw bitset ~1.3–1.8× at small n.
- **Against the fair flat baseline, CM = 0.73–1.06× (cached), parity to ~1.4×.** The residual
  win is DAG subtree sharing. **Publish as "CM matches/modestly beats best-practice bitset,"
  not "2×."**
- **Variance warning:** at n≥18 full-output, per-eval ratios swing ±30–50% between sessions
  (allocator/machine state at 2^20-bit widths) — treat large-n ratios as **≈ parity**, never
  quote as precise constants.

---

## 3. How to reproduce / run things

```bash
PY=./.venv/Scripts/python.exe          # Python 3.13.5
# Reduced-path feasibility (headline), n up to 24:
$PY cm_bench.py --sizes 16,18,20,22,24 --trials 8 --max-depth 4 --seed 123 \
  --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 100 \
  --cm-hybrid-threshold 7 --large-n-safe --cm-max-full-output-vars 16 \
  --sampled-correctness 1000 --no-dd --no-espresso --no-sympy --no-robdd \
  --no-bdd-sop --no-numba --out-prefix bench_headline

# Turn ON the C1a flat evaluator: add  --cm-flat-eval
# Compute a GENUINE >16-var function (guard raised): --cm-max-full-output-vars 24 --cm-hybrid-threshold 64
# Tests (system python, NOT venv):  python -m pytest -q     # expect 159 passed
```
- Correctness oracle is always `eval_expr_tt` (`cm_exprlib.py`), kept **outside timed windows**.
- `bench_*_raw.csv` / `_summary.csv` are gitignored; paste headline numbers into reports.
- All session tables/reports live in `deliverables_n22_24/`.

---

## 4. Open threads / next work (ranked)

1. **Last-use slot freeing in `FlatProgram`** — the flat `values` list holds every 2^n-bit
   intermediate (same issue that hurts the raw-flat bitset control). Free dead slots at their
   last use; likely also fixes the **n=22 full-output outlier**. Small, contained.
2. **numpy-uint64 word backend** for widths ≥ 2^16 bits (Tier-C C1b-lite) — the remaining
   lever at n=22/24 full output; slots behind the same `FlatProgram`.
3. **Wrapper fast path** — with a 6 µs kernel at n≤12, `materialize_hybrid_no_reinflate`'s
   ~4–6 µs diagnostics plumbing is now co-equal (that's the 1.12× at n=4).
4. **Bitset-side speedups** (be fair): the flat-raw executor is one; also worth exploring a
   numpy-word raw evaluator, and whether the numba stack machine (existing control) is the
   right flat-vs-flat baseline for the paper.
5. **Guard/decline surfacing** — add an explicit `cm_hybrid_no_reinflate_declined_count` to
   the summary so deep-expression selection bias can never hide.

---

## 5. Full artifact index (`deliverables_n22_24/`)

| File | What |
|---|---|
| `CM_ARCHITECTURE_AND_AUDIT.md` | Master audit: what changed, exhaustive correctness, env cliff, decline/selection-bias, guard history, how to exceed 16 vars. |
| `CM_n22_24_feasibility_report.md` | n=22/24 feasibility write-up. |
| `CM_convergence_findings.md` | Full-output CM/Bitset ratio → parity; structural node-count floor. |
| `CM_c1a_flat_eval_report.md` | C1a implementation, before/after, **§4.1 fairness control**. |
| `CM_correctness_audit.csv` | 74-expr exhaustive correctness. |
| `CM_env_build_cliff.csv` | Old vs new env-build cost (the enabler). |
| `CM_decline_rate_by_depth.csv` | Decline rate + live_k by n × depth. |
| `CM_n16_24_{headline,guard_rate,scaling}.csv` | Feasibility tables. |
| `CM_methods_comparison.csv` | CM vs bitset vs dd vs oracle. |
| `CM_convergence_fulloutput.csv` | Recursive-kernel convergence table. |
| `CM_c1a_{cached,convergence}_before_after.csv` | C1a before/after. |
| `CM_fair_bitset_control.csv` | Flattened-raw-bitset fairness control. |
| (repo root) `CM_n20_feasibility_report.md` | n=18/20 report (has a correction banner). |
