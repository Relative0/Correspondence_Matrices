# Handoff to Codex — Final Repair, Compact-Key Gate, and Corrected E3 (2026-08-02)

Project root: `C:\Users\brian\Documents\CM_Computation`
State: `main` = `b6ce6b2` with the complete, **uncommitted** repair series in the
working tree. Final status: **READY FOR FINAL REVIEW**. Nothing committed or pushed;
no downloads; no pods.

## Read (new this round)

1. `deliverables_n22_24\CM_GAP_FINAL_REPAIR_AND_E3_2026-08-02.md` — final report:
   Phase A dispositions (persistent path, deep v1, metrics purity, commutative
   equivalence, cache-key), Phase B compact-key GO, Phase C E3 results, claim
   dispositions, commit decomposition, prepared external-work proposals.
2. `deliverables_n22_24\cm_gap_final_repair_e3_2026_08_02.py` — E3 driver.
3. `deliverables_n22_24\cm_gap_final_repair_e3_results_2026_08_02.json` — results.
4. `deliverables_n22_24\CM_gap_final_repair_e3_summary_2026_08_02.csv` — stat summary.
5. `deliverables_n22_24\CM_gap_e3_corpus_2026_08_02.jsonl` — 96-formula corpus (v2 docs,
   seeds, hashes).
6. This file.

Context: the merge-review trio (`CM_GAP_REPAIR_MERGE_REVIEW_2026-08-02.md`, its probe
and results JSON — note the results file was re-run after each phase this round and
reflects the FINAL code), the implementation round
(`CM_GAP_REPAIR_IMPLEMENTATION_2026-08-02.md` + driver + results + CSV), the
deep-followup quartet, and your original audit trio from 2026-08-01.

## What to verify hardest

1. **A1 soundness argument** (report §A1): persistent caching keys on a
   commutative-canonical, association-preserving digest; subtree-level caching only
   when the expression has no shared associative classes; root-level otherwise. Attack
   the two claims: (a) digest-equal ⟹ identical guarded compile (depends on A4's
   comm-sorted uid classes); (b) cross-regime digest matches are impossible. A
   counterexample to either is a blocker.
2. **A4**: commuted duplicates (`Xor(a,b)`/`Xor(b,a)`, nested permutations) are now one
   guard class; *re-associated* variants remain a documented limitation — check the
   boundary is where the report says it is.
3. **Phase B compact interning**: within-builder equivalence of compact-lookup and
   deep-key interning (induction argument); foreign-node registration path; verify
   public keys, arg order, and diagnostics are truly unchanged (corpus 49/49 and the
   full suite say yes — try to construct a divergence).
4. **E3**: audit the corpus generator for family/shape balance and support exactness;
   the bootstrap (formula as resampling unit); the skew note (one formula compiles to
   0 executed ops — check geomean-vs-median presentation is honest); the
   blocked-vs-round-robin separation.
5. Numbers to reproduce: mult seq nb8 prep 426.8 ms → 3.2 ms (135×), kernel 572 → 300 µs
   (CSE 327); ladder d12 compile 703 µs; E3 all-corpus blocked geomean 0.843
   [0.780, 0.894]; full suite 306 passed.

## Rules

Benchmarks `.venv\Scripts\python.exe`; tests system Python 3.10. No commits, pushes,
pods, downloads. Do not edit historical reports/CSVs or any `*2026_08_02*` artifact —
respond in new date-stamped files under `deliverables_n22_24\`.

## Deliverables requested

1. Verdict on Phase A items 1–6 and the Phase B gate (CONFIRMED /
   CONFIRMED-WITH-CORRECTION / REFUTED / UNRESOLVED) with reproduction.
2. Independent opinion on the E3 statistics and on the revised C1/multiplier claim
   language in the report.
3. Approve or amend the proposed commit decomposition.
4. Any blocker found → state it plainly and stop; otherwise second READY FOR FINAL
   REVIEW.
