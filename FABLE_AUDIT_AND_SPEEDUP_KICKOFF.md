# Kickoff — Fable: Audit the 2026-07-21 CM Findings, then Speed Up CM *and* Bitset

> Paste everything below the line into a fresh Fable agent. It is standalone; the detail
> lives in the referenced files.

---

You are joining an ongoing research project on **Correspondence Matrices (CM)** for Boolean
computation, in `C:\Users\brian\Documents\CM_Computation`. Your predecessor (an Opus session
on 2026-07-21) extended feasibility to n=22/24, ran a pre-publication audit, implemented a
flat evaluator (C1a), and — importantly — *walked back* an over-strong "CM beats bitset 2×"
claim after a fairness control. **Your job has two parts: (1) adversarially audit those
findings for legitimacy before they are published, and (2) find further speedups for BOTH CM
and the bitset baseline.** Assume nothing is correct until you have re-derived it; your value
is skepticism plus new speed.

## Environment (verify first — a prior doc was wrong about this)

- Benchmarks run on **`.\.venv\Scripts\python.exe` = Python 3.13.5** (numpy 2.3.2, dd 0.6.0).
- Tests run on **system `python` = 3.10.11, pytest 9.0.2** (the venv has no pytest):
  `python -m pytest -q` must stay **159 passed**.
- **CUDD does not import on this Windows box**; the only BDD engine is pure-Python `dd.autoref`.
- Correctness oracle is always `eval_expr_tt` (`cm_exprlib.py`), kept **outside timed windows**.

## Read first, in this order

1. [`CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md`](CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md)
   — consolidated map of everything the last session did, with the honest headlines and every
   artifact path. **Start here.**
2. [`FABLE_CM_HANDOFF.md`](FABLE_CM_HANDOFF.md) §1–3 & §6 (system map, cost profile, and the
   **proven dead ends you must not reopen**), and [`FABLE_CM_SPEEDUP_AGENDA.md`](FABLE_CM_SPEEDUP_AGENDA.md).
3. `deliverables_n22_24/CM_ARCHITECTURE_AND_AUDIT.md` (esp. §2 env-build cliff, §4 exhaustive
   correctness, §6.2 decline/selection-bias, §8.1 exceeding 16 vars).
4. `deliverables_n22_24/CM_c1a_flat_eval_report.md` (esp. **§4.1 fairness control**) and
   `CM_convergence_findings.md`.
5. Code you will audit/optimize: `bitset_backend.py` (the flat evaluator + `eval_cm_node_bitset`
   + `_build_bitset_env_cached`), `cm_ir.py` (`materialize_hybrid_no_reinflate`, the guard,
   `set_flat_eval_default`), and the C1a flag path in `cm_bench.py` / `cmbench/config.py`.
   Relevant commits: `86301e0`, `f60e36a`, `b20ba35`.

## Part 1 — Audit the findings (be adversarial; re-derive, don't trust)

Confirm or refute each, with fresh measurement, and write `CM_AUDIT_REVIEW_<date>.md`:

1. **Correctness is real, not sampled luck.** Re-run an independent exhaustive check
   (all 2^n rows) that CM reduced output, raw bitset, CM-IR bitset, **and the C1a flat kernel**
   equal `eval_expr_tt` at n up to 24. Independently re-verify `dd.autoref`. Try to *break*
   the flat evaluator: deep expressions, all-constant/annihilating subtrees, single-var,
   all-fixed, `live_k == threshold` boundary, repeated vars, XOR/EQV/IMP chains.
2. **The env-build cliff really is the n>16 enabler.** Reproduce old vs new
   `_build_bitset_env_cached` timing and bit-identity. Check nothing *else* silently gates n>16.
3. **The C1a speedup is honest.** Re-run the before/after AND the **fair flat-raw bitset
   control**. Verify the bound-program cache stores only *inputs* (never outputs) — i.e. it is
   not accidentally memoizing results and inflating the win. Confirm the "parity to ~1.4× vs
   best-practice bitset" framing survives; if the large-n ratios are as variance-dominated as
   claimed (±30–50%), quantify that with repeated sessions/medians and say so.
4. **The decline/selection-bias story.** Confirm that at `--max-depth 4` nothing exceeds 16
   live vars, that deeper runs silently median over survivors, and that the guard never emits a
   wrong/oversized output. Consider adding the `..._declined_count` summary column.
5. **Environment integrity.** Confirm the 3.13.5-vs-3.10.11 split and that results are stable
   across both interpreters (run the key micro-benchmarks under system 3.10.11 too; flag any
   divergence — numpy 2.x behaviour, big-int perf, etc.).
6. **Framing hygiene.** Flag any remaining place (reports, memory, commit messages) that
   overstates CM vs bitset. The publishable claim is *capability + structure + parity*, not raw
   speed dominance.

## Part 2 — Speed up CM *and* Bitset (keep it fair)

The whole point is a fair comparison, so improve both sides and always re-measure against the
*flattened* bitset baseline, not just the recursive one.

**CM candidates (ranked by the last session):**
1. **Last-use slot freeing in `FlatProgram`** — free dead 2^n-bit intermediates at their last
   use (liveness at lowering). Likely also fixes the n=22 full-output outlier. Highest leverage.
2. **numpy-uint64 word backend** for widths ≥ 2^16 bits (Tier-C C1b-lite), width-selected,
   behind the same `FlatProgram`.
3. **Wrapper fast path** — a diagnostics-off route so `materialize_hybrid_no_reinflate` doesn't
   add ~4–6 µs around a 6 µs kernel.

**Bitset candidates (do not neglect — fairness):**
4. A **flattened raw-AST bitset** with the same last-use freeing and/or numpy-words — this is
   the honest lower bound; if it speeds up, CM must beat *it*, not the recursive walk.
5. Whether the numba stack machine is the right flat-vs-flat control for the paper.

**Rules:** every kernel change stays **bit-identical** (prove it with the oracle sweep) and
**behind a flag** if it changes defaults; `pytest` stays **159/159**; extend
`cmbench/results/schema.py` if you add columns; medians over ≥5 trials, instrumentation off for
headline numbers; **do not reopen** `FABLE_CM_HANDOFF.md` §6 dead ends. A well-measured
*negative* result (e.g. "numpy-words loses below 2^13 bits") is a valid deliverable.

## First concrete steps

1. Read the five items above; run `python -m pytest -q` to confirm the 159/159 baseline on the
   current tree.
2. Reproduce ONE audit item end-to-end (suggest the exhaustive correctness sweep incl. the flat
   kernel) to validate your harness understanding before going wide.
3. Prototype **last-use slot freeing** behind the existing flat path, prove bit-exactness, and
   produce a before/after against BOTH bitset baselines.
4. Write `CM_AUDIT_REVIEW_<date>.md` (audit verdicts) and, for any speedup, a short
   before/after report in the style of `deliverables_n22_24/CM_c1a_flat_eval_report.md`.

Ask for clarification if scope is ambiguous. Otherwise, begin with the audit.
