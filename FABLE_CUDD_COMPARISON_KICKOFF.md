# Kickoff — Next Agent: In-Depth CM vs CUDD (BDD) Comparison

> Paste everything below the line into a fresh agent session. Placeholders marked
> `<<TO FILL: …>>` will be completed by Brian Theory (Droncheff) before launch — do not
> guess their values; if any is still unfilled when you start, ask for it first.
>
> Project contact: **Brian Theory (Droncheff)**.

---

You are joining the **Correspondence Matrices (CM)** project in
`C:\Users\brian\Documents\CM_Computation`. The project has just completed a full
adversarial audit (Fable Audit V2, 2026-07-22, commits `f4cac02`/`4f99fbf`/`a8f17bb` on
`main`). Your mission: produce the first **rigorous, fair, in-depth comparison of CM
against CUDD-backed ROBDDs**, extending the fairness discipline this project has already
established for the Bitset baseline.

## Why this comparison, and why now

Everything published so far compares CM against a flattened raw-AST **bitset** — the
best-practice *explicit* representation. CUDD is the strongest widely-accepted *implicit*
representation (canonical ROBDDs with a mature C engine). CM's claimed value —
"exact, compressed answers via canonical structure, engines swappable underneath" — is
philosophically much closer to a BDD package than to a bitset, so the CM-vs-CUDD
comparison is the one reviewers will demand. The prior sessions could not run it: **CUDD
does not import on this Windows box** (`dd.cudd` absent; only pure-Python `dd.autoref`
works here, and cross-engine timing against it is explicitly ruled invalid in
`CM_ARCHITECTURE_AND_AUDIT.md` §7).

## Environment (verify before believing anything, including this section)

- This box: Windows 10, benchmark venv `.\.venv\Scripts\python.exe` = Python 3.13.5
  (numpy 2.3.2, dd 0.6.0 **without** CUDD); tests on system Python 3.10.11
  (`python -m pytest -q` must stay green — 159 passed as of `a8f17bb`).
- CUDD environment: **<<TO FILL: where CUDD runs — WSL distro / Linux host / container,
  its Python and dd/CUDD versions. Note there is a DIFFERENT VERSION of
  <<TO FILL: dd? CUDD? Python?>> there than on Windows — record both versions in every
  results file.>>**
- CUDD-side documents/artifacts and any prior CUDD measurements live at:
  **<<TO FILL: paths/locations of the CUDD docs and prior results>>**.
- Because CM (this box) and CUDD (other environment) cannot run in one process, the
  comparison design MUST address cross-environment fairness explicitly (see Protocol §3).

## Read first, in this order

1. `CM_SESSION_2026-07-21_STATE_AND_FINDINGS.md` — project map.
2. `CM_FABLE_AUDIT_V2_2026-07-21.md` — audit verdicts; the C3 fairness-bug story is the
   cautionary tale your design must not repeat (never compare CM against a comparator
   that is secretly CM-shaped or secretly handicapped).
3. `deliverables_n22_24/CM_FABLE_BENCHMARKS_2026-07-21.md` — the current honest numbers
   and variance discipline (medians ≥5 trials, paired/interleaved, repr-mix disclosure).
4. `deliverables_n22_24/CM_ARCHITECTURE_AND_AUDIT.md` §7 (threats to validity — esp. the
   cross-engine caveat) and `FABLE_CM_HANDOFF.md` §6 (dead ends; BDD flat-output
   extraction note: build-only BDD timings are NOT comparable to flat-output methods).
5. Code: `cm_ir.py` (canonicalization + `materialize_hybrid_no_reinflate`),
   `bitset_backend.py` (flat + words kernels), `cmbench/backends/robdd_dd.py` (the
   existing dd adapter — your starting point for a CUDD adapter).
6. CUDD-side docs: **<<TO FILL: list>>**.

## What to compare (the axes that matter)

CM and ROBDDs are both canonical, structure-exploiting representations. Compare them on
ALL of these axes, not just wall-clock — several are where the interesting differences
live:

1. **Build/compile cost**: expression → interned CM DAG (+ flat program) vs expression →
   CUDD BDD (record variable order used; try both natural order and CUDD's dynamic
   reordering on/off — reordering time counts as build cost when enabled).
2. **Representation size**: unique CM DAG nodes + flat-program slots vs BDD node count
   (`dag_size`). Also peak memory both sides.
3. **Full-output extraction** (the regime bitsets win): time to produce the complete
   2^n packed truth table from an already-built representation. For CUDD this means
   enumerating satisfying paths or evaluating all cubes — known to be its weak spot;
   measure it honestly rather than assuming.
4. **Reduced/live-variable output** (CM's flagship): CM's `live_k ≤ 16` guarded reduced
   result vs BDD support + cofactor enumeration over the support. Both packages can
   report support cheaply — compare support-discovery time AND reduced-table extraction.
5. **Query workloads where BDDs shine — do not cherry-pick against CUDD**:
   equivalence checking (pointer-compare after canonical build, both sides),
   satisfiability / model counting (`sat_count`), restriction/cofactoring
   (CM `fixed=` bindings vs `bdd.let`), and incremental re-query on the same built
   object. CM's bound-template cache vs CUDD's computed-table both matter here.
6. **Structure sensitivity**: families where BDDs are provably small (symmetric
   functions, comparators), provably large under bad orders (multipliers — keep n small),
   and this project's standard families (depth-4/6/8 `random_expr`,
   `random_expr_balanced_all_vars`, XOR chains, sparse mixed chains). Expect the verdict
   to be family-dependent — report it that way.
7. **Scaling in n vs scaling in live_k**: the audit showed CM's runtime tracks
   2^live_k, not nominal n. Establish the analogous law for CUDD (node count tracks
   structure/order, not n) and characterize where each collapses.

## Protocol (non-negotiables inherited from the audit, plus cross-env rules)

1. **Correctness first, timing second.** Every CUDD result must be verified bit-identical
   to `eval_expr_tt` (exhaustive to the largest feasible n, sampled + support-verified
   above; state which). Reuse `deliverables_n22_24/audit_2026_07_21.py` patterns; the
   oracle stays outside timed windows.
2. **Identical expression corpora on both sides.** Serialize the exact `Expr` trees
   (seeded generation + a serialized corpus file committed to the repo) so the CUDD
   environment evaluates literally the same formulas. Never regenerate independently.
3. **Cross-environment timing hygiene.** CM-on-Windows vs CUDD-on-<<TO FILL>> wall-clock
   ratios are confounded by hardware/OS. Mitigate and DISCLOSE: (a) run the
   **bitset baseline in BOTH environments** as a portable yardstick and report
   CM/bitset and CUDD/bitset ratios rather than raw cross-box times wherever possible;
   (b) if the CUDD environment can also run CM (pure Python + numpy — it should),
   prefer same-box CM-vs-CUDD as the primary comparison and use the Windows numbers only
   as corroboration; (c) record CPU model, RAM, Python/numpy/dd/CUDD versions in every
   CSV.
4. **Engine matching.** CM gets its best engine (flat + words where it wins); CUDD gets
   its best settings (reordering choice disclosed; computed-table warm vs cold both
   measured). No side runs a strawman configuration — the C3 lesson.
5. **Variance discipline.** Medians over ≥5 trials × ≥5 sessions for headline numbers,
   paired/interleaved ordering, spreads reported, no single-constant claims.
6. **Honest negatives are deliverables.** If CUDD dominates a regime (it will somewhere —
   likely equivalence/satisfiability queries on order-friendly functions), that goes in
   the headline table with the same prominence as CM wins.
7. `pytest` stays green on system Python; any new library code lands behind flags with
   bit-exactness proven; schema extensions go through `cmbench/results/schema.py` (+
   flatten + stability tests), following the `declined`-column precedent.

## Deliverables

- `CM_CUDD_COMPARISON_<date>.md` (repo root): design, per-axis results, family-dependent
  verdict, threats to validity, and a single honest headline paragraph in the house
  style ("capability + exactness + structure at parity speed" was the Bitset verdict —
  state the CUDD analogue, whatever it turns out to be).
- `deliverables_cudd/` : corpus file(s), per-axis CSVs (with environment columns), the
  runner scripts for BOTH environments (re-runnable as-is), and the CUDD adapter.
- A follow-up-agenda section: what a reviewer will attack next.
- Update `CM_SESSION_*` handoff pointers and the memory index note for the next session.

## First concrete steps

1. Verify both environments (versions, CUDD import, CPU); fill or demand the
   `<<TO FILL>>` blanks; run `python -m pytest -q` baseline.
2. Build the shared corpus file + serializer (commit it before any timing).
3. Port `cmbench/backends/robdd_dd.py` to a CUDD adapter in the CUDD environment; prove
   correctness against the oracle on the corpus.
4. Run axis 1–2 (build cost + representation size) first — they are timing-hygiene-light
   and establish the structural picture that explains everything after.
5. Only then do timed axes 3–5, with the bitset yardstick running in both environments.

Ask Brian Theory (Droncheff) if scope is ambiguous; otherwise begin with Step 1.
