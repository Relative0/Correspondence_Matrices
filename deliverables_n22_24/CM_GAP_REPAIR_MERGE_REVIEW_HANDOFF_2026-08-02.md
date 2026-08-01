# Handoff to Codex — Post-Merge-Review State (2026-08-02)

Project root: `C:\Users\brian\Documents\CM_Computation`
State: `main` = `b6ce6b2` with the reviewed, **still-uncommitted** repair diff, now
including one blocking fix applied during the merge review. Decision was
**ACCEPT AFTER LISTED FIXES** (fix already applied and re-verified). Nothing committed.

## Read

Review round (new):

1. `deliverables_n22_24\CM_GAP_REPAIR_MERGE_REVIEW_2026-08-02.md` — the review, verdicts,
   blocking/non-blocking lists, proposed commit scope.
2. `deliverables_n22_24\cm_gap_repair_merge_review_probe_2026_08_02.py` — adversarial probe
   (instrumented op counting, cache-safety fuzz, memo GC stress, serde mutations,
   persistent-path check, CSE subprocess-independence).
3. `deliverables_n22_24\cm_gap_repair_merge_review_results_2026_08_02.json` — probe results
   (post-fix run).

Implementation round: `CM_GAP_REPAIR_IMPLEMENTATION_2026-08-02.md`,
`cm_gap_repair_benchmark_2026_08_02.py`, `cm_gap_repair_results_2026_08_02.json`,
`CM_gap_repair_before_after_2026_08_02.csv`, `CM_GAP_REPAIR_HANDOFF_2026-08-02.md`.
Deep-followup round: the four `*DEEP_FOLLOWUP*2026-08-02*` artifacts. Your round:
`CM_GAP_AUDIT_2026-08-01.md` + probe + results.

## What the review found (verify if you disagree)

- **One blocker, fixed in-diff**: canonical keys were not representation-independent —
  6/300 fuzz cases where a tree-expanded, dataclass-equal copy of a shared DAG keyed
  differently than the original (mid-build `no_splice` mark accrual made later
  *rebuilds* of duplicated subtrees canonicalize differently). Packed outputs were
  never wrong. Fixed with a structural uid memo in `_BuildState` (`cm_ir.py`); post-fix
  fuzz 0/300; corpus keys still 49/49 identical to legacy; regression test
  `test_canonical_key_is_representation_independent` pins seeds 1032/1106/1148/1200/1263.
- All six implemented items otherwise CONFIRMED, including *instrumented* verification
  of `program_metrics` (monkeypatched numpy ufuncs and operator-counting ints matched
  declared counts exactly on every arm).
- Persistent compile path's legacy flattening: judged **not** a merge blocker (opt-in,
  no regression, mixing measured packed-equal) but a required follow-up before that
  path enters any benchmark arm.
- Unshared-tree compile overhead 1.2–1.5× (~15–40 µs): accepted; input-dependent fast
  paths rejected on determinism grounds.
- Full suite post-fix: 291 passed, 0 failed (system Python 3.10).

## Your task, if another pass is wanted

1. Try to break the uid-memo fix: construct an input where first-DFS-encounter order
   of structural classes differs between representations of the same expression, or
   where the uid memo returns a node whose canonical key disagrees with a fresh
   compile. The fuzz generator lives in the probe; extend it (deeper nesting, Var
   `name` attributes, adversarial Not-chains).
2. Audit the review's §5 reasoning that the persistent path cannot corrupt any shared
   cache (check every consumer of CMNode keys and every node-keyed cache).
3. Re-derive one instrumented metrics case by hand from `_eval_words` source.
4. Second the go/no-go table (§7) or dissent with evidence.

Rules as before: benchmarks `.venv\Scripts\python.exe`, tests system 3.10; no commits,
pushes, pods, downloads; no edits to historical reports/CSVs or `*2026_08_02*`
artifacts — respond in new date-stamped files under `deliverables_n22_24\`.
