# Kickoff V2 — Fable: Audit a Third-Party Agent's Code Changes AND Its Results, Then Re-Run the Benchmarks

> Paste everything below the line into a fresh Fable agent. It supersedes
> `FABLE_AUDIT_AND_SPEEDUP_KICKOFF.md` for the audit portion (that file remains the source
> of the benchmark task-spec you must ultimately fulfill).

---

You are joining the **Correspondence Matrices (CM)** project in
`C:\Users\brian\Documents\CM_Computation`. The situation is unusual, so read carefully:

1. An Opus session (2026-07-21) produced the committed state through `fe73f82`
   (n=18–24 feasibility campaign, pre-publication audit, C1a flat evaluator, fair-bitset
   control). Its map is `CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md`.
2. The original audit brief `FABLE_AUDIT_AND_SPEEDUP_KICKOFF.md` was then run by a
   **different LLM (not you, not Opus)**. That agent **modified library, harness, schema,
   test, and report files and left everything UNCOMMITTED** in the working tree, along with
   its own reports and ~25 new CSV/script artifacts.
3. **Nothing that agent did has been reviewed.** Your mission: audit its code changes AND
   its results; keep what is genuinely good; fix or revert what is not; then re-run the
   benchmark program the original kickoff called for, on the code state you end up
   endorsing. You are the reviewer of record — be adversarial toward *both* prior agents'
   work, including the committed Opus baseline.

## Step 0 — The third-party work is already preserved; start from the snapshot branch

The unreviewed third-party changes have ALREADY been committed (verbatim, for preservation
only — **the commit is not an endorsement**) on the branch **`audit/third-party-snapshot`**;
`main` deliberately does NOT contain them. Begin with:

```bash
git checkout audit/third-party-snapshot   # the code state you are auditing
git log --oneline -3                      # confirm: snapshot commit on top of main
git diff main --stat                      # the full third-party diff
```

Do your audit on this branch. When done, put the **accepted** end state onto `main` as one
or more clean, well-messaged commits (this repo's history is direct-to-main). Nothing gets
lost, nothing unreviewed lands on `main` silently.

## The third-party agent's claims (each one is an audit target, not a fact)

From its handoff summary and its reports (`CM_AUDIT_REVIEW_2026-07-21.md` in repo root;
`deliverables_n22_24/CM_flat_liveness_speedup_report.md`):

- C1. Correctness re-verified: 30 expressions through n=24, ~134M exhaustive rows/method,
  zero failures (CM output, raw bitset, recursive CM-IR, C1a flat); `dd.autoref` OK.
- C2. Env-build cliff confirmed on BOTH interpreters (n=20: 14.0 s → 136 ms on 3.13;
  19.3 s → 115 ms on 3.10).
- C3. **A fairness bug in the pre-existing harness:** in the `--large-n-safe` path the
  "bitset" comparator evaluated the **canonicalized CM DAG** (`eval_cm_node_bitset(node_nr,
  output_vars, ...)`, `cm_bench.py` ~1785 at commit `fe73f82`) instead of the raw AST — so
  prior "CM vs matched bitset" reduced-scope ratios compared CM against itself-ish. It
  changed the comparator to a flattened **raw AST** over the matched scope, and made
  `--cm-flat-eval` select raw-flat at ordinary sizes too.
- C4. The inherited "parity to ~1.4× faster vs best-practice bitset" claim is **not
  robust**: kernel-level parity to ~1.2×, but the public wrapper
  (`materialize_hybrid_no_reinflate`) is typically **1.09–1.43× slower** for tiny reduced
  outputs.
- C5. Decline selection bias confirmed; summary now has
  `cm_hybrid_no_reinflate_declined_count` (schema + flatten + stability tests updated).
- C6. Last-use slot freeing implemented for BOTH flat programs. At n=22: CM-flat 2.02×
  faster, raw-flat 1.45× faster; peak allocation ↓15.2× (CM) / ↓25.4× (raw). n=24 timing
  neutral-to-slightly-negative despite the memory win (reported honestly).
- C7. Final suite 159 passed (376.8 s).

## What it actually changed (verified inventory, `git diff fe73f82` on the snapshot)

| File | Nature of change |
|---|---|
| `bitset_backend.py` (+131) | `_last_use_releases` liveness pass + release logic in `FlatProgram`/`eval_cm_node_flat`; NEW raw-AST flat evaluator promoted to library code (`compile_expr_flat`, `get_expr_flat_program`, `eval_expr_flat_bitset`). |
| `cm_bench.py` (+48/−?) | The C3 comparator change in the large-n path of `time_backends_on_expr` (~1795–1856); raw-flat selection at ordinary sizes; declined-count aggregation in `run_bench`. |
| `cm_ir.py` (+46) | Changes inside `materialize_hybrid_no_reinflate` (~1454–1503) incl. a deleted line ~1554 — determine exactly what: wrapper fast-path? declined recording? Verify the guard and repr codes are untouched. |
| `cmbench/results/schema.py` / `flatten.py` | `declined: bool|None` field → `{base}_declined` column. |
| `tests/test_bitset_backend.py` (+32), `tests/test_single_expr_schema_stability.py` (+2) | New tests for the above. |
| Prior reports/docs (`CM_c1a_flat_eval_report.md`, `CM_convergence_findings.md`, `CM_tierC_rescope_report.md`, `FABLE_CM_HANDOFF.md`, `FABLE_CM_SPEEDUP_AGENDA.md`) | Third-party caveat banners / scope corrections — review these edits for accuracy too. |
| NEW: `CM_AUDIT_REVIEW_2026-07-21.md`, `CM_flat_liveness_speedup_report.md`, ~20 `CM_audit_*/CM_flat_liveness_*/CM_env_build_*` CSVs, 5 `*_2026_07_21.py` scripts in `deliverables_n22_24/` | Its evidence — re-run its scripts, don't just read them. |

## Your audit protocol (per change: KEEP / FIX / REVERT, each with written rationale)

1. **Read the diffs line-by-line** (`git diff fe73f82 -- <file>`), not the reports first —
   form your own view of what each change does before reading its justification.
2. **C3 is the highest-stakes item.** Confirm from the `fe73f82` source that the old
   comparator really was the CM DAG; decide whether raw-AST-flat over matched scope is the
   right fair baseline; then determine the **blast radius**: which previously published
   numbers (the n=18–24 headline `bitset cached` columns and 1.7–1.8× ratios in
   `CM_n16_24_headline.csv`, `CM_n22_24_feasibility_report.md`,
   `CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md` §2.1) change under the corrected baseline,
   and re-issue those tables.
3. **C4 reconciliation.** The Opus C1a report §3(B) shows the wrapper at 0.72–1.12× vs
   recursive bitset; the third party says the wrapper is 1.09–1.43× **slower** than its fair
   baseline for tiny outputs. Reproduce both measurements, identify why they differ
   (baseline choice? wrapper overhead? sizes?), and state the single defensible headline.
4. **C6 liveness freeing:** verify bit-exactness of the release logic (a slot freed too
   early = wrong results — build adversarial DAGs with high fan-out/reuse to try to break
   it), confirm the n=22 speedups and the honest n=24 neutral result, and check the release
   metadata is recomputed correctly when a cached `FlatProgram` is reused across different
   `(vars_key, fixed)` bindings.
5. **C1/C2/C5/C7:** re-run its audit scripts (`deliverables_n22_24/*_2026_07_21.py`) as-is
   first; if a script embeds a flaw, document it and run a corrected version. Re-run
   `python -m pytest -q` (system Python 3.10.11) yourself — expect 159 passed; the venv
   (`.\.venv\Scripts\python.exe`) is Python 3.13.5 for benchmarks.
6. **Schema changes (C5):** confirm `_declined` doesn't break CSV column stability
   (`tests/test_single_expr_schema_stability.py`, `tests/test_run_bench_output_compatibility.py`)
   and that the summary actually surfaces the declined count.
7. **Then complete the original mission** (`FABLE_AUDIT_AND_SPEEDUP_KICKOFF.md` Parts 1–2)
   on your endorsed code state: the same benchmark families the other LLM was supposed to
   run — exhaustive correctness incl. flat kernel, env-cliff, C1a before/after vs BOTH
   bitset baselines, decline behavior, plus any further speedups you judge worthwhile
   (numpy-words for ≥2^16-bit widths is the top open candidate; `FABLE_CM_HANDOFF.md` §6
   dead ends stay closed).

## Output documents (keep SEPARATE from the other LLM's reports — do not edit its files except to annotate factual errors)

- `CM_FABLE_AUDIT_V2_<date>.md` (repo root): per-claim verdicts (C1–C7:
  confirmed/refuted/partial + evidence), per-change decisions (KEEP/FIX/REVERT + why),
  the C3 blast-radius re-issued tables, and the reconciled performance headline.
- `deliverables_n22_24/CM_FABLE_BENCHMARKS_<date>.md` + CSVs: your re-run benchmark
  results in the style of the existing reports (medians ≥5 trials, instrumentation off,
  oracle outside timed windows, honest caveats).
- If you reject or rewrite any third-party change, the rationale goes in YOUR documents;
  leave its reports intact as the record of what it claimed.

## Ground rules (unchanged)

- Every kernel change **bit-identical** to `eval_expr_tt` (prove it; sampling only where
  exhaustive is infeasible, and say so). `pytest` stays **159/159** on system Python.
- Fairness: CM claims are made against the **flattened** raw-AST bitset baseline, never only
  the recursive walk. Large-n (≥18) per-eval ratios carry ±30–50% session variance — use
  paired/interleaved measurement and report spread, not single medians.
- Negative results, well measured, are deliverables. Do not reopen `FABLE_CM_HANDOFF.md` §6.
- Commit accepted work to `main` in logical commits with messages that say what was
  audited, kept, fixed, and reverted — the git history is the audit trail.

## Read order

1. `CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md` — the committed baseline's map.
2. The diffs: `git diff fe73f82 --stat` then per-file — form your own opinion FIRST.
3. The third party's `CM_AUDIT_REVIEW_2026-07-21.md` and
   `deliverables_n22_24/CM_flat_liveness_speedup_report.md`.
4. `FABLE_AUDIT_AND_SPEEDUP_KICKOFF.md` — the benchmark program you must ultimately deliver.
5. `deliverables_n22_24/CM_ARCHITECTURE_AND_AUDIT.md` §4/§6.2/§8.1 and
   `CM_c1a_flat_eval_report.md` §4.1 — the committed evidence base you are re-checking.

Begin with Step 0 (snapshot), then the C3 fairness-bug verification — it has the largest
blast radius on published numbers. Ask if scope is ambiguous; otherwise proceed.
