# Handoff to Codex — Review of the 2026-08-02 Gap-Repair Implementation

Project root: `C:\Users\brian\Documents\CM_Computation`
Base revision: `main` = `b6ce6b2` with **uncommitted working-tree changes** (the repairs
under review — do not commit them; review the diff in place via `git diff`).
Benchmark interpreter: `.venv\Scripts\python.exe`; tests: system Python 3.10.

## Read first — all of these

New (this implementation round):

1. `deliverables_n22_24\CM_GAP_REPAIR_IMPLEMENTATION_2026-08-02.md` — implementation report.
2. `deliverables_n22_24\cm_gap_repair_benchmark_2026_08_02.py` — corrected benchmark driver.
3. `deliverables_n22_24\cm_gap_repair_results_2026_08_02.json` — benchmark results.
4. `deliverables_n22_24\CM_gap_repair_before_after_2026_08_02.csv` — before/after summary.
5. This file.

Deep-follow-up round (the audit these repairs implement):

6. `deliverables_n22_24\CM_GAP_DEEP_FOLLOWUP_2026-08-02.md`
7. `deliverables_n22_24\cm_gap_deep_followup_2026_08_02.py`
8. `deliverables_n22_24\cm_gap_deep_followup_results_2026_08_02.json`
9. `deliverables_n22_24\CM_GAP_DEEP_FOLLOWUP_HANDOFF_2026-08-02.md`

Your earlier round:

10. `deliverables_n22_24\CM_GAP_AUDIT_2026-08-01.md`
11. `deliverables_n22_24\cm_gap_audit_probe_2026_08_01.py`
12. `deliverables_n22_24\cm_gap_audit_probe_results_2026_08_01.json`

Production diff to review (uncommitted): `cm_ir.py`, `bitset_backend.py`,
`cm_expr_serde.py`, `tests/test_cm_optimizations.py`, plus five new test files
(`tests/test_program_metrics.py`, `tests/test_share_aware_flatten.py`,
`tests/test_build_memo.py`, `tests/test_expr_serde_v2.py`, `tests/test_bitset_cse.py`).

## What was implemented (attack each)

1. **`program_metrics`** (`bitset_backend.py`) — executed-op accounting: word executor
   NOT=1, IMP/EQV=2, n-ary=max(1, arity−1); bigint executor NOT=2, IMP/EQV=3,
   n-ary=arity−1; plus loads, argument edges, peak live scratch buffers. Verify the
   constants against `_eval_words` and `_eval_prepared_flat` line by line.
2. **Sharing-aware flattening** (`cm_ir.py`) — a syntactic-fanout prepass
   (`_shared_assoc_uids`, structural-equivalence merged, edges counted once per
   deduplicated parent) marks multi-consumer associative subexpressions; the
   canonicalizer keeps them as nodes instead of splicing. Claimed properties to test:
   all 49 published corpus formulas keep bit-identical canonical keys; fanout-1
   behavior unchanged (wide-associative tests); executed word ops on the 8×8
   sequential central bit drop 368 → 167; node-level rewrites (XOR parity, complement)
   still fire across the guard. Known accepted gaps: commutative-equal but
   syntactically different duplicates are not merged; the persistent-cache compile
   path still always-splices.
3. **Per-compilation memo** (`cm_ir.py` `_BuildState`) — id-keyed but holding
   `(expr, node)` strong pairs, discarded when the outermost `build` returns. Try to
   construct an id-reuse or state-leak failure (`tests/test_build_memo.py` has a
   GC-stress test; find a case it misses).
4. **v2 defs/ref serde** (`cm_expr_serde.py`) — backwards refs only, duplicate-def
   rejection, iterative both ways, v1 auto-detected. Fuzz it.
5. **CSE production baseline** (`bitset_backend.compile_expr_cse`) — int-keyed,
   iterative, optional sharing-aware flatten that must never change executed-op counts.
6. **Corrected benchmark driver** — separated parse/prep/kernel/wrapper/cold/repeated
   boundaries, full metadata, ≥20-formula summarization rule. Check no column mixes
   wrapper and kernel and that `flat_instructions` is never presented as executed ops.

## Headline results you should independently reproduce

- mult seq nb8 bit8: executed word ops 368 → 167 (== CSE); kernel 545 → 287 µs
  (CSE 292); prep 341 ms → 9.9 ms (CSE 0.47 ms). All arms packed-equal.
- Family geomeans (n ≥ 20 strata): cm_new/cse kernel 0.847 (high-sharing DAGs) and
  0.913 (random depth-4 trees); cm_new/cm_old prep 0.639 and **1.511** — the second is
  an accepted regression (prepass+memo overhead on unshared trees); challenge whether
  it is acceptable.
- Compact-key residual after the repairs: 2.7–12.3× (kept scratch-only; recommend or
  veto its production implementation).
- Full test suite: 290 passed on system Python 3.10.

## Rules

- Do not commit, push, start pods, download external corpora, or edit historical
  reports/CSVs or any `*2026_08_02*` artifact — respond in new files under
  `deliverables_n22_24\` with your own date-stamped names.
- Benchmarks with `.venv\Scripts\python.exe`; tests with system Python 3.10.
- Prefer refutation; assert packed equality before timing; keep deterministic counts
  separate from timings.

## Deliverables requested

1. Verdict per implemented item (1–6): CONFIRMED / CONFIRMED-WITH-CORRECTION /
   REFUTED / UNRESOLVED, with reproduction.
2. A line-by-line review of the `cm_ir.py` diff for canonicalization-semantics leaks
   (especially: any input where the guard changes Boolean output, breaks key
   determinism, or degrades interning in a way packed equality would not catch).
3. A go/no-go recommendation on: (a) merging compact intern-ID keys next,
   (b) wiring the guard into the persistent compile path, (c) making
   `eval_expr_words_cse` the default baseline in future benchmark harnesses.
4. Whether the published C1 and multiplier claims should be retracted, restated, or
   retained, given the corrected before/after data.
