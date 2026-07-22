# Fable Audit V2 — Review of the Third-Party Agent's Code Changes and Results

Date: 2026-07-21
Auditor: Fable (this document), reviewing the unreviewed third-party changes preserved on
`audit/third-party-snapshot` (`00c8ac3`) against the committed Opus baseline (`fe73f82`).
Benchmark interpreter: `.venv` Python 3.13.5 / NumPy 2.3.2. Test interpreter: system
Python 3.10.11.

## Executive verdict

**All third-party code changes are KEPT** (no fixes or reverts required), and all seven of
its claims are **confirmed** — most independently re-executed, two confirmed with noted
scope limits. The C3 fairness bug it found in the committed baseline is real, and its blast
radius on the published n=18–24 headline numbers is real and quantified below: the old
"bitset cached" comparator was 1.2–2.2× slower than a fair flattened raw-AST baseline, so
the published tables **understated** the bitset side and must be re-issued (done here).

One genuine audit gap was found in the third party's own verification and closed by this
audit (§C6): its exhaustive correctness suite never actually executed the new
slot-freeing branch, because the gate (`live_k ≥ 18` AND `≥ 64` slots) was not met by any
audit expression. The freeing path *was* checked before timing in its liveness benchmark,
but only on one expression family. This audit force-enabled the freeing branch for every
program and ran 2,909 adversarial checks (both interpreters) — zero failures.

## Per-claim verdicts

### C1 — Correctness re-verified through n=24 — **CONFIRMED (re-executed)**

Re-ran `deliverables_n22_24/audit_2026_07_21.py` unmodified on Python 3.13.5:
30 expressions, 134,086,656 exhaustive rows per method, **0 failures** across CM
reduced/full output, raw bitset, recursive CM-IR, C1a flat, adversarial kernel cases,
`dd.autoref` enumeration, and the bound-cache purity check
(`CM_audit_2026-07-21_py313_fable_*.csv`). The script's methodology was reviewed first:
the oracle (`eval_expr_tt`) is independent and outside all timed windows; the reduced→full
expansion index math is correct for MSB-first ordering; the claimed 134M row count is
arithmetically exact (6 cases × (2^16+2^18+2^20+2^22+2^24)).

*Scope note:* the audit-suite expressions never trip the freeing gate (largest program,
`all_live_xor` at n=24, has 47 slots < 64), so C1 alone does not validate the C6 release
logic. See C6 for the closure of that gap.

### C2 — Env-build cliff on both interpreters — **CONFIRMED**

The script `benchmark_env_build_2026_07_21.py` reconstructs the pre-R3 builder faithfully
(same O(n·2^n) big-int block loop) and verifies bit-identity old-vs-new. Its recorded
results (`CM_env_build_2026-07-21_{py313,py310}.csv`: n=20 14.0 s → 136 ms on 3.13,
19.3 s → 115 ms on 3.10) are consistent with the committed baseline's own measurement
(§2.2 of `CM_ARCHITECTURE_AND_AUDIT.md`: 20.6 s at n=20) and with R3's design. Re-executed
in this session with matching results (see `CM_FABLE_BENCHMARKS_2026-07-21.md`).

### C3 — Fairness bug in the pre-existing large-n comparator — **CONFIRMED; the fix is correct; blast radius quantified**

Confirmed from the `fe73f82` source itself (not the third party's report): in the
`--large-n-safe` path, `time_backends_on_expr` timed
`eval_cm_node_bitset(node_nr, output_vars, fixed={})` — a recursive walk of the
**canonicalized CM DAG** — as the "bitset" comparator. Every published n≥18
"bitset cached" number therefore measured CM's own data structure, not an independent
bitset baseline. The published "CM vs matched bitset" ratios at n=18–24 compared CM
against itself-ish.

The fix (flattened **raw AST** over the matched scope, dropped variables fixed to 0,
`bitset_baseline_kind` recorded in every row) is the right fair baseline:

- It uses no CM canonicalization, interning, or DAG sharing — it is what a competent
  bitset user could build with no CM machinery.
- Matched scope is conservative *against* CM: the baseline receives CM's live-variable
  discovery for free and never pays for it.
- Correctness is preserved: fixing CM-irrelevant variables is validated implicitly — if a
  dropped variable were actually relevant, the equality check against the CM output would
  fail. It never did (all runs, both sessions).

**Blast radius** (paired, interleaved measurement, same session, 8 depth-4 trials/n,
7 rounds, medians; `CM_FABLE_c3_blast_radius_{raw,summary}.csv`):

| n | CM wrapper µs | old comparator µs (CM-DAG recursive) | corrected baseline µs (raw-flat matched) | new/old | CM/old | CM/new |
|--:|--:|--:|--:|--:|--:|--:|
| 16 | 48.0 | 51.5 (raw recursive at n=16) | 42.2 | 0.82 | 0.93 | 1.14 |
| 18 | 10.4 | 17.6 | 8.5 | 0.48 | 0.59 | 1.23 |
| 20 | 12.4 | 20.4 | 9.9 | 0.49 | 0.61 | 1.26 |
| 22 | 13.0 | 23.1 | 10.5 | 0.45 | 0.56 | 1.24 |
| 24 | 6.5 | 10.3 | 7.7 | 0.75 | 0.63 | 0.84 |

- The old comparator inflated the bitset column by 1.2–2.2×. Any prior ratio built on the
  n≥18 "bitset cached" columns of `CM_n16_24_headline.csv` /
  `CM_n22_24_feasibility_report.md` §2 / `CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md`
  §2.1 is superseded by the corrected table above and by
  `deliverables_n22_24/CM_FABLE_BENCHMARKS_2026-07-21.md`.
- The two comparators agreed **bit-for-bit on every trial** (`old_new_always_equal=True`):
  this was purely a fairness bug, never a correctness bug.
- Note the published absolute numbers are not directly comparable to this table: the
  published CM column predates the C1a flat evaluator + wrapper fast path (e.g. 29.8 µs at
  n=18 then, ~10 µs now).
- Caveat carried into the re-issued tables: trials whose `live_k` exceeds the hybrid
  threshold fall to the numpy TT-vector path (repr 4) and can be 30–45× slower than the
  matched-scope bitset baseline on that trial; per-n medians hide this. Disclose the repr
  mix wherever medians are published.

### C4 — "Parity to ~1.4×" not robust; wrapper slower on tiny outputs — **CONFIRMED; reconciled**

The two prior claims measure different things, and both reproduce:

- The Opus C1a report §3 numbers (flat/bitset 0.72–1.12×) compare the CM **flat kernel**
  against the **recursive** raw walk — a baseline the fair-control section (§4.1) of the
  same report already superseded. The third party's banner on §3 is accurate.
- The third party's kernel-vs-kernel numbers (CM-flat / raw-flat ≈ 0.83–0.97 full-arity,
  ≈ parity on cached depth-4) and wrapper numbers (1.09–1.43× slower than raw-flat for
  tiny reduced outputs) are the like-for-like comparison. This session independently
  reproduced the wrapper result in the reduced CLI regime: CM/raw-flat medians 1.23 /
  1.26 / 1.24 / 0.84 at n=18/20/22/24 (vs its 1.15/1.43/1.23/1.09), with wide per-trial
  spread at these µs scales — consistent within disclosed session variance.

**The single defensible headline** (adopted; matches the third party's):
*CM's compiled kernel is at parity with, to modestly faster than, a best-practice compiled
raw-bitset kernel (DAG sharing is the residual advantage); the public wrapper adds fixed
result/scope overhead that leaves it at parity to ~1.4× slower for microsecond-scale
reduced outputs. CM's value at large n is the exact reduced representation and the
explicit feasibility guard, not raw speed.*

### C5 — Decline selection bias + `declined_count` surfacing — **CONFIRMED**

- `audit_decline_2026_07_21.py` reviewed: guard semantics are checked in both directions
  (wrong-guard if accepted with `live_k>16` or declined with `live_k≤16`; oversized-output
  check on the payload). Re-executed (reduced trial count, same seeds — see benchmarks doc);
  results match its recorded distribution (depth 4 never declines; decline rate rises
  steeply by depth 6–8 at n=24).
- The schema change is minimal and correct: `declined: bool|None` in `BackendResult`,
  flattened as `{base}_declined`; `cm_hybrid_no_reinflate_declined` recorded in both
  decline paths of `time_backends_on_expr` (string-prefix match on the guard's ValueError —
  brittle coupling to the message text, but both raise sites share the message and a test
  covers it); `cm_hybrid_no_reinflate_declined_count` aggregated with the pre-existing
  `count_true`. Schema-stability tests updated and passing. End-to-end CLI verification in
  the benchmarks doc.

### C6 — Last-use slot freeing — **code CONFIRMED correct; performance claims CONFIRMED with honest n=24 neutrality**

Code review of `_last_use_releases` / the release loop found no defect:

- Release happens strictly after the consuming op writes its output; the root slot is
  never released; repeated args in one op cannot double-release (the remaining-use counter
  reaches zero exactly once); variadic AND args are all counted.
- The schedule depends only on `ops`, never on the binding, so a cached `FlatProgram`
  reused across different `(vars_key, fixed)` bindings is safe by construction; the eval
  loop mutates a per-call `template.copy()`, so cached bind templates cannot be corrupted.

Because the third party's own audit never executed the freeing branch (gate not met — see
executive verdict), this audit **forced the gate open** (`_FLAT_FREE_MIN_VARS = 0`,
`_FLAT_FREE_MIN_SLOTS = 0`) and ran 2,909 checks on both interpreters, all passing:
shared-fanout and diamond DAGs, ops with repeated arg slots, 400 random fuzz trials with
mixed `fixed` bindings and rebinding of cached programs, exhaustive reduced-scope oracle
comparison, cached-template integrity after release-heavy use, and a static schedule audit
(no slot read after its release point, root never released) over 600+ real programs.
Script: `fable_adversarial_liveness.py` (session scratchpad; reproduced in the benchmarks
doc's methods section).

Performance re-run (its script, unmodified, fresh session): see
`CM_FABLE_BENCHMARKS_2026-07-21.md` — the n=22 win and the honest n=24 neutral-to-negative
result both reproduce in direction; exact multipliers vary with allocator state, as its
report already disclosed.

### C7 — Test suite — **CONFIRMED (re-executed)**

`python -m pytest -q` on system Python 3.10.11 at snapshot state: **159 passed** (399.9 s).
Re-run after this audit's own additions (numpy-words backend + extended assertions folded
into the existing tests): **159 passed** again.

## Per-change decisions

| Change | Decision | Rationale |
|---|---|---|
| `bitset_backend.py`: `_last_use_releases` + release logic | **KEEP** | Correct by review and by 2,909 forced-gate adversarial checks; gated to sizes where it pays; `free_dead_slots=False` preserves the reference behavior. |
| `bitset_backend.py`: raw-AST flat evaluator (`compile_expr_flat`, `get_expr_flat_program`, `eval_expr_flat_bitset`) as library code | **KEEP** | The fair baseline must live in library code to be reusable and testable. No CM machinery used; caching pattern matches the existing `CMNode._flat_program` idiom (frozen dataclass without `__slots__`, verified). Recursion depth is no worse than the existing recursive evaluators. |
| `cm_bench.py`: large-n comparator → raw-AST-flat matched scope; `bitset_baseline_kind` column | **KEEP** | This is the C3 fix. Recording the baseline kind in every row makes the fairness property auditable in the data itself. |
| `cm_bench.py`: `--cm-flat-eval` selects raw-flat at ordinary sizes | **KEEP** | Symmetric treatment: when CM runs its compiled kernel, the baseline gets its compiled kernel. |
| `cm_bench.py`: declined tracking + `declined_count` aggregation | **KEEP** | Prevents the documented selection bias from hiding; minimal footprint. |
| `cm_ir.py`: diagnostics-off wrapper fast path (`flat_fast_path`) | **KEEP** | Verified line-by-line equivalent to the reference path (same live-var derivation, same guard order and messages, same repr codes and output-var selection); falls through to the reference path when the threshold branch isn't taken; `flat_fast_path=False` retains the instrumented path. Fast-path duplication of guard logic is a maintenance liability — acceptable, documented here. |
| `cmbench/results/schema.py` + `flatten.py`: `declined` field | **KEEP** | Additive, default-None, schema-stability tests updated. |
| Tests (`test_bitset_backend.py`, `test_single_expr_schema_stability.py`) | **KEEP** | Correct; note they exercise `free_dead_slots=True` only below the gate (the flag is a no-op there). The forced-gate fuzz in this audit covers the actual release branch; recommend promoting a small forced-gate case into the suite as follow-up. |
| Caveat banners / scope corrections in prior reports (`CM_tierC_rescope_report.md`, `CM_c1a_flat_eval_report.md`, `CM_convergence_findings.md`, `FABLE_CM_SPEEDUP_AGENDA.md`, `FABLE_CM_HANDOFF.md`) | **KEEP** | Reviewed each edit against the underlying data: all accurate, all additive (no original data altered). The agenda's nominal-width vs matched-scope distinction is exactly right. |
| Its reports + CSVs + scripts (`CM_AUDIT_REVIEW_2026-07-21.md`, `CM_flat_liveness_speedup_report.md`, `CM_audit_*`/`CM_env_build_*`/`CM_flat_liveness_*` CSVs, `*_2026_07_21.py`) | **KEEP (as record)** | Scripts re-executed where feasible; methodology reviewed line-by-line; no embedded flaws found. Kept verbatim as the record of what it claimed. |

## What was NOT wrong (for the record)

- No correctness regression anywhere: every prior published *output* was bit-correct; the
  C3 bug affected only the fairness of a timing comparison.
- The committed Opus baseline's own §4.1 fair-control work pointed in the same direction as
  the third party's correction; the bug was confined to the `--large-n-safe` harness path.

## Superseded published numbers

The following published figures are superseded by the corrected-baseline tables in this
document and in `deliverables_n22_24/CM_FABLE_BENCHMARKS_2026-07-21.md`:

- `CM_n16_24_headline.csv` columns `bitset_cached_us` and `ratio_cm_over_bitset` at n≥18.
- `CM_n22_24_feasibility_report.md` §2 headline table (same columns).
- `CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md` §2.1 (the derived ratios), and its §1
  point 4 phrasing "parity to ~1.4× faster", which becomes: kernel parity to a modest
  workload-dependent CM advantage; wrapper parity to a modest bitset advantage on tiny
  reduced outputs.
