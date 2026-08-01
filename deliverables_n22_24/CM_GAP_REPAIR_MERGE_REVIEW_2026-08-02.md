# Merge-Gate Review — 2026-08-02 Gap-Repair Diff

Date: 2026-08-02
Code under review: the uncommitted working-tree diff on `main` = `b6ce6b2`
(`cm_ir.py`, `bitset_backend.py`, `cm_expr_serde.py`, `tests/test_cm_optimizations.py`,
plus five new test files), per `CM_GAP_REPAIR_HANDOFF_2026-08-02.md`.
Review evidence: `cm_gap_repair_merge_review_probe_2026_08_02.py` →
`cm_gap_repair_merge_review_results_2026_08_02.json` (all numbers below).
Benchmarks: `.venv\Scripts\python.exe` (3.13.5, numpy 2.3.2). Tests: system Python 3.10.11.

## Decision

**ACCEPT AFTER LISTED FIXES** — one blocking defect was found, fixed in-diff during this
review (as the brief permits for confirmed merge blockers), re-verified by fuzz and by
the full test suite, and pinned with a regression test. The diff as it now stands is
accepted. No commit or push was performed.

---

## 1. Line review

Every changed hunk in the four modified production/test files and the five new test
files was read. Findings:

- `cm_ir.py` — the builder restructure is contained: per-call `_BuildState`, prepass,
  splice guard, and flag plumbing; direct `make_*` calls outside `build` are provably
  unaffected (state is `None`). **One blocking defect found — see §4.** Non-blocking
  observations: `_bump` is invoked in the suppression path even with `diagnostics=None`
  (no-op, negligible); `ir_compile_time_s` now includes the prepass (correct: it *is*
  compile time).
- `bitset_backend.py` — `program_metrics` constants were checked line-by-line against
  both executors and then *instrumentally* (§2). It caches `prog.word_plan` as a side
  effect — benign and deterministic (identical to what `_eval_words` would compute).
  `compile_expr_cse` key space was checked for collisions: var keys start with a
  string, NOT keys are 2-tuples, binary keys 3-tuples — disjoint. Fanout counting is
  per deduplicated parent (correct); `And(h, h)` counts two edges so a twice-referenced
  child is never spliced (correct).
- `cm_expr_serde.py` — validation is complete for the attack classes tried (§2); the
  `alive` list in `expr_to_json_dag` is redundant (the root argument keeps the graph
  alive) but harmless. Pre-existing, unchanged: deep **v1** documents can still hit
  `RecursionError` rather than `ValueError` (the v2 path is iterative).
- `tests/test_cm_optimizations.py` — the two widened assertions preserve the tested
  property (shared subtree compiled once); acceptable.
- Benchmark driver — timing boundaries are genuinely separated; family summaries use
  kernel/prep columns only; the wrapper is its own column and is never presented as a
  kernel number; instruction vs executed-op columns are distinct; the ≥20-formula
  summarization rule is enforced.

## 2. Independent reproduction of the six implemented-item claims

| item | verdict | evidence |
|---|---|---|
| 1. `program_metrics` accounting | **CONFIRMED** | Instrumented counting — numpy ufuncs (`bitwise_and/or/xor/not`, `copyto`) monkeypatched for the words executor; operator-counting int wrappers fed through `_eval_prepared_flat` for the bigint executor — matched the declared counts **exactly** on all arms (cm_new, cm_legacy, cse, cse_flat, raw) across fuzz cases, the 6×6 multiplier, the XOR chain, and a synthetic 1-ary instruction: `all_word_ok=True`, `all_bigint_ok=True` |
| 2. Sharing-aware flattening | **CONFIRMED-WITH-CORRECTION** | 368→167 executed ops reproduced (both nb8 topologies → 167 == CSE); kernel 601→316 µs (CSE 331) and 493→311 µs (CSE 340); packed equality everywhere. Correction: the canonical-identity defect in §4, found by this review and fixed |
| 3. Per-compilation memo lifetime safety | **CONFIRMED** | 200 rounds through one reused builder with forced GC; **2,196 recycled object ids observed** crossing rounds; 0 failures. Reentrant subclass recursion through `build()`: correct results, state always cleaned |
| 4. v2 serde validation | **CONFIRMED** | 100 valid documents round-tripped bit-exactly (truth-table checked); 400 random mutations: every rejection was a `ValueError`, zero non-ValueError escapes; 31 mutations produced still-well-formed (different) documents and were correctly accepted — validation is well-formedness, not tamper-proofing |
| 5. CSE baseline independence | **CONFIRMED** | Fresh subprocess: compile + flatten + evaluate through the CSE path completes with `'cm_ir' not in sys.modules`; differential packed equality vs cm/raw held in all 300 fuzz cases |
| 6. Corrected benchmark boundaries | **CONFIRMED** (by inspection, §1) | plus corpus regression: **49/49** published formulas keep bit-identical canonical keys with the repair on vs off, all run-policy formulas packed-equal |

## 3. Refutation attempts (summary of what was tried and what happened)

- **Flattening semantics**: 300 random shared DAGs (mixed operators incl. IMP/EQV/NOT,
  4–10 vars, up to ~45 pool steps): packed outputs of cm_new, cm_legacy, cse, cse_flat
  all equal in 300/300. Key determinism per input object: 300/300.
- **Memo lifetime**: id-recycling pressure (above) failed to break it. The memo holds
  `(expr, node)` pairs, so a live entry's id cannot be recycled; the prepass maps hold
  bare ids but every mapped object is kept alive by the root argument for the duration
  of the build — checked against the reentrant case too (foreign graphs simply miss the
  maps and fall back to legacy splicing, which is semantically safe).
- **Metrics**: tried to make declared ≠ executed via n-ary/1-ary/IMP/EQV mixes —
  instrumentation matched everywhere.
- **Serde**: mutation classes — bad refs (negative, forward, self, bool, float, string,
  None), bad ops, bad version, node-shape corruption, duplicate insertion, deletion —
  no validation gap found.
- **CSE independence**: no hidden CM reuse found (subprocess import proof).

## 4. Context-dependent CMNode keys (the one confirmed blocker)

**Found: canonical keys were not representation-independent.** In 6/300 fuzz cases, a
tree-expanded, dataclass-*equal* copy of a shared DAG compiled to a *different*
canonical key than the original. Mechanism: `no_splice` marks accrue during the build;
a structurally duplicated subtree that is *rebuilt* later (rather than memo-hit by
identity) re-runs `make_*` under a larger mark set and can canonicalize differently
than its first build. Packed outputs remained equal in every case — this was a
canonical-identity instability, not a Boolean-semantics bug — but it violated the
review properties for interning/cross-expression reuse and made
`_COMPILED_IR_CACHE` (dataclass-keyed, `reuse_cache=True`) return nodes whose canonical
shape depended on which representation populated the cache first.

**Fix applied in-diff** (permitted corrective edit): `_BuildState` gained a structural
memo `memo_by_uid` (uid → node, uids already computed by the prepass), so `make_*` runs
exactly once per structural equivalence class at its first DFS encounter. The build is
now a pure function of the deduplicated structural graph, identical for identity-shared
and tree-expanded representations. Verified: fuzz re-run **0/300 mismatches**; corpus
keys still 49/49 identical to legacy; all headline numbers intact; regression test
`test_canonical_key_is_representation_independent` added (pins the five failing seeds
plus 30 more). Side benefit: structurally duplicated trees now compile
DAG-proportionally even without identity sharing.

Per-surface answers after the fix:

- **Interning**: safe — a node's key is built from its actual arg keys, so equal keys
  imply equal args and equal semantics; the interner cannot alias differing programs.
- **Cross-expression reuse / `_COMPILED_IR_CACHE`**: safe — canonical output is now a
  pure function of expression structure, matching the cache's dataclass-equality key
  (0/300 post-fix).
- **Persistent-cache reuse**: the persistent path produces legacy-shaped nodes; the two
  paths never share a node-keyed cache (materialization memo and `_flat_program` are
  keyed per node object), and mixing was measured packed-equal. Safe, dedupe-only cost.
- **Serialized caches**: none exist at CMNode level; the corpus/serde layer keys on
  `expr_structural_hash`, which is unchanged.
- **Diagnostics/equality**: differently-shaped semantically-equal nodes compare unequal
  (structural `__eq__`) — affects dedupe rates, never correctness; new counters are
  additive.

## 5. Persistent compile path — blocker determination

**Not a merge blocker.** Grounds: the path is opt-in (`persistent_cache=True`), its
behavior is byte-identical to pre-repair (no regression introduced by this diff), the
probe shows mixing the paths is semantically safe (368 vs 167 executed ops, packed
equal, keys differ, no shared caches), and the limitation is documented in the
docstring and implementation report. It **is** a required follow-up before that path is
used as a benchmark arm or before any cross-path canonical-key comparison is attempted;
until then the two paths must not be mixed within one comparison.

## 6. The unshared-tree preparation regression

Decomposition on 24 random depth-4 trees (flag matrix, mean-of-24, two independent
runs): memo alone ≈ 1.01–1.03×; prepass(+uid memo) ≈ 1.19–1.46×; combined ≈ 1.23–1.46×
here vs 1.51× geomean in the implementation driver — call it **1.2–1.5×, ~15–40 µs
absolute** on formulas of this size. Verdict: **acceptable**. A cheap fast path (skip
the prepass below a size threshold or after a quick duplicate probe) was considered and
**rejected**: any input-dependent skip makes canonical form depend on a heuristic, which
is exactly the class of instability §4 just eliminated; and compile time is hoisted out
of every published kernel ratio. Revisit the constant factor inside the compact-key
work, where the prepass and interning can share one walk.

## 7. Go/no-go verdicts

| question | verdict |
|---|---|
| Accept the current repair (incl. the §4 fix) | **GO** |
| Fix the persistent path before acceptance | **NO** as a precondition; **YES** as the first follow-up, before that path appears in any benchmark arm |
| Make the CSE evaluator (`eval_expr_words_cse`) the standard baseline in future benchmark harnesses | **GO** — independence proven, never semantically different, never more executed ops, cheapest prep; keep `compile_expr_flat` as a labeled no-CSE ablation only |
| Implement compact keys as a separate follow-up | **GO** — measured 2.7–12.3× residual after these repairs; precondition: the differential/property test suite from this review (fuzz + representation-independence + corpus-key regression) runs against it before merge |

## 8. Test results

- Full suite, system Python 3.10, post-fix: **291 passed, 0 failed** (380 s; includes
  the new regression test). A pre-fix full run also passed 290/290 (background record).
- Review probe (benchmark interpreter): all sections green post-fix — instrumented
  metrics exact-match; corpus 49/49 keys + packed equality; fuzz 300/300 with 0
  cache-safety mismatches; memo stress 200 rounds/0 failures/2,196 recycled ids;
  reentrancy ok; serde 0 escapes; CSE subprocess-independent.

## 9. Blocking issues and non-blocking concerns

**Blocking (found: 1; fixed in-diff and re-verified):**

1. Canonical-key representation dependence under mid-build mark accrual (§4) — fixed
   via `memo_by_uid`; regression-tested.

**Non-blocking concerns (accept with follow-ups):**

1. Persistent compile path retains legacy always-splice flattening (§5) — follow-up
   before benchmark use; do not mix paths in one comparison until then.
2. Unshared-tree compile overhead 1.2–1.5× (§6) — accepted; revisit constant factor
   with compact keys.
3. Syntactic fanout approximation: commutative-equal but syntactically different
   duplicates are not merged by the prepass; duplication can persist in that corner
   (semantically safe; bounded by legacy behavior).
4. Deep **v1** tree documents can raise `RecursionError` (pre-existing; v2 is
   iterative — migrate deep inputs to v2).
5. `program_metrics` caches `word_plan` on the program as a side effect (benign;
   document if it ever surprises).
6. `build_memo` flag is not part of the `reuse_cache` key (safe — memo cannot change
   output — but worth a comment if flags ever multiply).

## 10. Files modified during this review

- `cm_ir.py` — the §4 fix (`memo_by_uid` in `_BuildState`; uid lookup/store in
  `_build_rec`). ~25 lines.
- `tests/test_share_aware_flatten.py` — +`test_canonical_key_is_representation_independent`.
- New review artifacts: `cm_gap_repair_merge_review_probe_2026_08_02.py`,
  `cm_gap_repair_merge_review_results_2026_08_02.json`, this report,
  `CM_GAP_REPAIR_MERGE_REVIEW_HANDOFF_2026-08-02.md`.

No historical report or CSV was touched; nothing was committed or pushed; no pods, no
downloads, no compact-key implementation, no E3.

## 11. Proposed commit scope (do not execute without Brian's approval)

Scope: `cm_ir.py`, `bitset_backend.py`, `cm_expr_serde.py`,
`tests/test_cm_optimizations.py`, `tests/test_program_metrics.py`,
`tests/test_share_aware_flatten.py`, `tests/test_build_memo.py`,
`tests/test_expr_serde_v2.py`, `tests/test_bitset_cse.py` (deliverables under
`deliverables_n22_24/` may go in a separate `bench(data)`-style commit, matching repo
convention). Suggested message:

```
feat(cm): sharing-aware flattening, per-compilation memo, executed-op metrics

- CMIRBuilder: fanout-guarded associative splicing with a structural (uid)
  build memo, making canonical output a pure function of expression
  structure; lifetime-safe per-call id memo; ablation flags preserved
- bitset_backend: program_metrics() executed-operation accounting;
  structural-CSE production baseline (compile_expr_cse/eval_expr_words_cse);
  raw compiler relabeled as ablation-only
- cm_expr_serde: v2 defs/ref DAG schema (iterative, validated, deterministic);
  v1 tree schema retained for compatibility
- 68 new tests incl. representation-independence and GC/id-reuse regressions

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

## 12. Second-pass verification (same day, post-fix diff re-reviewed)

A confirmation pass was run against the accepted diff (worktree verified unchanged:
same 4 files, +569/−32):

- Extended cache-safety fuzz on **600 fresh seeds** (2000–2599, wider size range):
  **0** key mismatches, **0** semantic failures across cm_new / cm_legacy / raw /
  cse_flat arms and both serde round-trips.
- New targeted edge attacks, all passed: rewrite-collapsed duplicated structures
  (`Xor(a,a)`→const under shared consumers) keep representation-independent keys;
  shared associative nodes under NOT/IMP/EQV wrappers key identically after tree
  expansion; **builder state is cleaned after an exception mid-build and the builder
  is reusable afterwards** (a case the first pass had not exercised).
- Targeted suites re-run on system Python 3.10: **109 passed, 0 failed**
  (five new test files + `test_cm_optimizations`, `test_cm_ir_wide_associative`,
  `test_bitset_backend`, `test_cm_no_reinflate`, `test_cm_persistent_ir_cache`).

The decision in this report is unchanged: **ACCEPT AFTER LISTED FIXES**, with the one
blocking fix already applied and verified.

## 13. Exact next actions

1. Brian reviews and commits the accepted diff (message above), or requests changes.
2. Follow-up A: wire the sharing-aware guard into `compile_expr_to_cm_ir_persistent`.
3. Follow-up B: implement compact intern-ID keys behind the review's differential
   suite (measured 2.7–12.3× residual).
4. Follow-up C: E3 clustered replication through the corrected driver; EPFL/AIGER
   ingestion pending download authorization; pods pending authorization.
