# Final Review Prompt — CM Gap Repair Series (2026-08-02)

Copy-paste this prompt to the reviewer (Codex, another agent, or a human session).

---

Perform the final acceptance review of the completed CM gap-repair series.

Project root: `C:\Users\brian\Documents\CM_Computation`
State: `main` = `b6ce6b2` with the complete repair series **uncommitted** in the
working tree. Status claimed by the implementer: READY FOR FINAL REVIEW.
Benchmarks: `.venv\Scripts\python.exe` (3.13.5). Tests: system Python 3.10.
Do not commit, push, download external data, start pods, or edit any existing
report/CSV/`*2026_08_02*` artifact. Respond in new date-stamped files under
`deliverables_n22_24\`.

## 1. Code under review (the uncommitted production diff — run `git diff`)

| file | what changed, in review order |
|---|---|
| `cm_ir.py` (+~365 lines) | (a) `CMIRBuilder`: sharing-aware associative flattening — fanout prepass `_shared_assoc_uids` (commutative-sorted uid classes), splice guard in `_canonicalize_commutative_args`, per-compilation `_BuildState` with lifetime-safe id memo and structural `memo_by_uid`; flags `share_aware_flatten`/`build_memo` (default on, False = legacy ablation). (b) Persistent path: `_persistent_digest` (commutative-canonical, association-preserving) and the rewritten `compile_expr_to_cm_ir_persistent` with the two-regime caching strategy. (c) Compact interning: `_uid_of_node`, compact `_intern` lookup keys, uid-based `seen`/`negated_bases`/`counts` in `make_and/or/xor` — public `CMNode.key` unchanged. |
| `bitset_backend.py` (+~204 lines) | `program_metrics` (executed-op accounting, observationally pure); structural-CSE production baseline `compile_expr_cse` / `get_expr_cse_program` / `eval_expr_words_cse` (optional sharing-aware flatten); `compile_expr_flat` relabeled ablation-only. |
| `cm_expr_serde.py` (+~220 lines) | v2 defs/ref DAG schema (`expr_to_json_dag`, auto-detecting `expr_from_json`, full validation); v1 serializer AND deserializer now iterative (no RecursionError on deep documents). |
| `tests/test_cm_optimizations.py` | 3 assertions widened to accept `build_memo_hits` alongside `subtree_cache_hits` (reuse now caught one layer earlier; tested property unchanged). |

New test files (review for coverage and intent):

- `tests/test_share_aware_flatten.py` — guard semantics, representation-independence regression (pinned seeds), commutative-equivalence (A4), legacy-ablation flag.
- `tests/test_build_memo.py` — memo scoping, GC/id-reuse stress, flag identity.
- `tests/test_persistent_path_consistency.py` — normal≡persistent keys/shapes/metrics, subchain preservation, cold/warm, option isolation, eviction, GC pressure.
- `tests/test_program_metrics.py` — metric constants, n-ary/1-ary/IMP/EQV cases, purity.
- `tests/test_bitset_cse.py` — CSE differential equality, flatten-never-adds-ops, deep-tree iteration.
- `tests/test_expr_serde_v2.py` — v2 round-trips, 15 malformed-document rejections, deep-v1 iterative handling.

## 2. Reports and evidence to review (read in this order)

1. `deliverables_n22_24\CM_GAP_FINAL_REPAIR_AND_E3_2026-08-02.md` — **the primary
   document**: Phase A dispositions, the A1 soundness argument (§A1 — review this
   hardest), Phase B compact-key gate results, Phase C E3 statistics, revised
   C1/multiplier claim language, proposed commit decomposition, prepared
   EPFL/pod proposals.
2. `deliverables_n22_24\CM_GAP_REPAIR_MERGE_REVIEW_2026-08-02.md` — the earlier
   merge-gate review (decision, the representation-independence blocker and its fix).
3. `deliverables_n22_24\CM_GAP_REPAIR_IMPLEMENTATION_2026-08-02.md` — original
   implementation round (design decisions, rejected alternatives).
4. `deliverables_n22_24\CM_GAP_DEEP_FOLLOWUP_2026-08-02.md` — the audit that
   motivated every repair (background).

Machine-readable evidence:

- `deliverables_n22_24\cm_gap_repair_merge_review_results_2026_08_02.json` —
  adversarial probe results, re-run against the FINAL code (fuzz 0/300, corpus
  49/49 keys, instrumented metrics exact, persistent≡normal).
- `deliverables_n22_24\cm_gap_final_repair_e3_results_2026_08_02.json` +
  `CM_gap_final_repair_e3_summary_2026_08_02.csv` — E3 results and statistics.
- `deliverables_n22_24\CM_gap_e3_corpus_2026_08_02.jsonl` — the 96-formula E3
  corpus (v2 docs, seeds, structural hashes).
- `deliverables_n22_24\cm_gap_repair_results_2026_08_02.json` +
  `CM_gap_repair_before_after_2026_08_02.csv` — before/after benchmark
  (pre-dates Phases A/B; treat as historical context, not final numbers).

Reproduction drivers (runnable):

- `deliverables_n22_24\cm_gap_repair_merge_review_probe_2026_08_02.py` — the
  adversarial probe (re-run it; every section must stay green).
- `deliverables_n22_24\cm_gap_final_repair_e3_2026_08_02.py` — E3 driver
  (regenerates corpus deterministically; writes fresh results).
- `deliverables_n22_24\cm_gap_repair_benchmark_2026_08_02.py` — corrected
  benchmark driver from the implementation round.

## 3. Specific claims to verify

1. **A1 soundness** (final report §A1): (a) digest-equal ⟹ identical guarded
   compile; (b) cross-regime digest matches impossible. A counterexample to
   either is a blocker.
2. **Compact interning equivalence**: compact-lookup dedupe ≡ deep-key dedupe
   within a builder; public keys, arg order, diagnostics unchanged (corpus
   49/49 is the regression evidence — try to construct a divergence).
3. **Numbers**: mult seq nb8 prep 426.8 ms → 3.2 ms (135×), kernel 572 → 300 µs
   (CSE 327); ladder d12 compile 703 µs; E3 all-corpus blocked geomean 0.843
   [0.780, 0.894] with per-stratum CIs excluding parity; full suite 306 passed.
4. **E3 methodology**: corpus balance (3 strata × 4 op families × 2 shapes × 4),
   formula as inferential/resampling unit, blocked vs round-robin never pooled,
   honest skew handling (one formula compiles to 0 executed ops).
5. **Claim language**: the revised C1/multiplier statements in the final report
   are what the data supports — no more, no less.

## 4. Verification commands

```bash
python -m pytest tests/ -q
```

```bash
.venv/Scripts/python.exe deliverables_n22_24/cm_gap_repair_merge_review_probe_2026_08_02.py
```

```bash
.venv/Scripts/python.exe deliverables_n22_24/cm_gap_final_repair_e3_2026_08_02.py
```

(Expected: 306 passed; probe all green; E3 within noise of the recorded results.)

## 5. Decisions requested

1. Verdict per area (cm_ir guard/memo, persistent path, compact interning,
   metrics, CSE baseline, serde, E3 statistics): CONFIRMED /
   CONFIRMED-WITH-CORRECTION / REFUTED / UNRESOLVED.
2. Approve or amend the proposed 6-commit decomposition (final report, last
   section) — do not execute it.
3. Second or overturn READY FOR FINAL REVIEW. Any blocker → state it plainly
   and stop.
4. Optional: opinion on the two authorization-gated next steps (EPFL download,
   5-pod replication gate) as specified in the final report.
