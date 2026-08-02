# CM Gap Series — Consolidated Audit, Erratum, and Corrected E3 (2026-08-02)

State: `main` = HEAD = `origin/main` = `4c51429`; production repair committed at
`12defc4`. This pass adds uncommitted working-tree changes only (listed in §6);
no commit, push, amend, reset, or history rewrite was performed, and no
historical report or result artifact was edited or overwritten.

Machine evidence for every claim below:
`cm_gap_consolidated_validation_2026_08_02.json` (regenerable via
`cm_gap_consolidated_validation_probe_2026_08_02.py`), the post-fix adversarial
probe re-run `cm_gap_repair_merge_review_results_consolidated_rerun_2026_08_02.json`,
and the corrected E3 artifacts (§4). Benchmarks: `.venv\Scripts\python.exe`
(3.13.5, numpy 2.3.2); tests: system Python 3.10.11.

Decision at end: **READY FOR INDEPENDENT REVIEW**.

---

## 1. Verdicts on the externally reported findings (F1–F7)

Each finding was independently reproduced before any fix (prefer-refutation
protocol; one was in fact refuted).

| # | finding | verdict | evidence |
|---|---|---|---|
| F1 | E3 seeds process-randomized (`hash(family) % 9973`) | **CONFIRMED** | three PYTHONHASHSEED subprocesses gave three different seed vectors; the archived corpus is not regenerable from its driver. Fixed in the corrected driver (blake2b seeds from explicit integer family/shape codes); byte-identical corpora across hash seeds 0/1/31337 (`tests/test_e3_corpus_determinism.py`) |
| F2 | E3 strata syntactic, not semantic, support | **CONFIRMED, numbers reproduced exactly** | independent packed-truth influence check over the archived 96: exact-support 17/16/20 by stratum (53 total), 43 reduced, 5 constants (3× k8-mixed-shared, 2× k12-andor_dom-shared). Restricted re-analysis of archived blocked ratios matches the reported table to ±0.003 (k8 0.928/0.969 CI [0.871,0.986]; k12 0.924/0.960 [0.866,0.978]; k16 0.961/0.965 [0.930,0.990]; all 0.939/0.969 [0.910,0.967]) |
| F3 | `tree_occurrences` mislabeled (counts identity-DAG nodes) | **REFUTED** | the id-memoized function *propagates multiplicities*: on a depth-10 `Xor(g,g)` ladder (identity DAG = 11 nodes) it returns 2047 = 2¹¹−1, the exact unfolded count. The archived values were correct. The corrected driver still adopts the required richer accounting (identity/structural/unfolded, factors, depth, fanout) |
| F4 | Compact interning regresses foreign-node behavior | **CONFIRMED (all four sub-findings), FIXED** | pre-fix: `AND(x0,x0)` from two builders stayed binary; `XOR(y,y)` did not collapse to 0; equal public keys returned distinct node objects; mixed internal/foreign failed to dedupe; foreign ids registered with no retention (stale-id hazard demonstrated). Fix in §3.5; regression suite `tests/test_foreign_node_interning.py` (11 tests) |
| F5 | Reproduction commands overwrite archived evidence | **CONFIRMED, FIXED** | both final drivers write fixed archived filenames. Corrected driver: `--out-dir` + refuse-if-exists unless `--overwrite` (`tests/test_e3_output_safety.py` proves the default cannot overwrite); the adversarial probe was re-run through a wrapper redirecting `OUT` to a new file, archived result untouched |
| F6 | Repository-state descriptions stale | **CONFIRMED** | nine 2026-08-02 documents describe an uncommitted diff on `b6ce6b2`; the work is committed (`12defc4`, `4c51429`) and pushed. Erratum E1; no historical file edited |
| F7 | Digest-equality and v2-canonicality claims overreach | **CONFIRMED, FIXED** | (a) `_persistent_digest` docs claimed digest equality *implies* structural identity; corrected to a documented probabilistic assumption (blake2b-128, no equality fallback, ≈2⁻⁶⁴ birthday bound at 2³² entries vs the cache's 10⁴ cap) — behavior unchanged by design (an O(subtree) equality fallback would defeat the cache; accepted residual risk, now stated). (b) v2 reader accepted unreachable definitions; it now rejects them (which provably forces root-last), keeps accepting alternate topological orderings, and documents accepted input as "valid but possibly noncanonical" with normalization via re-serialization. New tests in `tests/test_expr_serde_v2.py` |

## 2. Erratum (corrections of record; historical files unmodified)

- **E1 — repository state.** `CM_GAP_FINAL_REPAIR_AND_E3`, `..._IMPLEMENTATION`,
  `..._MERGE_REVIEW(+HANDOFF)`, `..._REPAIR_HANDOFF`, `..._FINAL_REPAIR_HANDOFF`,
  `..._DEEP_FOLLOWUP(+HANDOFF)`, and `CM_FINAL_REVIEW_PROMPT` state the repair
  is uncommitted on `b6ce6b2`. Correction: the production repair was committed
  as `12defc4` and the deliverables as `4c51429`, both on `origin/main`. Written
  at those documents' creation time the statements were true; they are stale, not
  fabricated.
- **E2 — archived E3 is superseded.** The corpus behind
  `CM_GAP_FINAL_REPAIR_AND_E3` §Phase C does not satisfy its stated design:
  only 53/96 formulas have the claimed semantic support and 5 are constants
  (including `e3-k8-mixed-shared-4`, the report's "extreme rewrite-collapse"
  exhibit — it is the constant-0 function). All Phase-C numbers, including the
  headline 0.843 [0.780, 0.894], are superseded by §4 below.
- **E3 — driver defects.** The superseded driver's seeds were process-random
  (F1), its outputs overwrote archived files when re-run (F5), and its
  "cold total" was a warm-process, warm-cache compile+evaluate (relabelled
  `warmenv_compile_eval` in the corrected driver).
- **E4 — A1 soundness language.** "Digest equality … implies an identical
  commutative-sorted structural uid graph" (report §A1 and the old docstring)
  overstates: identification is up to blake2b-128 collision and is treated as
  identity without a fallback. The two-regime design argument is otherwise
  upheld.
- **E5 — v2 acceptance language.** "References must point strictly backwards …
  O(n) validation" implied accepted ⇒ canonical. Accepted input was (and
  remains) broader than the serializer's output; the contract is now documented
  and unreachable definitions are rejected.
- **E6 — probe result hygiene.** `cm_gap_repair_merge_review_results_2026_08_02.json`
  was historically updated in place ("living verification record"). It is frozen
  as of this pass; post-fix runs write new files
  (`..._consolidated_rerun_2026_08_02.json`).
- **Upheld against refutation:** F3's mislabeling claim is wrong (§1); the
  archived occurrence counts and the 60,000-occurrence raw-arm guard were valid.

## 3. Phase 1 — production-code audit by area (committed repair `12defc4` + this pass's fixes)

Working definitions: "probe" = the adversarial merge-review probe re-run
post-fix (new output path); "suite" = full system-Python pytest run (§7).

1. **Sharing-aware associative flattening — CONFIRMED.**
   Correctness: probe semantic fuzz 0/300 differential failures (cm_new ≡
   cm_legacy ≡ cse ≡ raw packed outputs); 49/49 corpus canonical keys
   unchanged; dedicated suite green. Performance: headline case executed ops
   368→167 (= CSE), prep 403 ms → 3.0 ms. API: default-on, legacy via
   `share_aware_flatten=False`. Residual risk (pre-existing, documented):
   re-associated (not commuted) chain variants remain separate guard classes.
2. **Representation-independent `memo_by_uid` — CONFIRMED.**
   Structural uids from `_shared_assoc_uids` merge separately allocated equal
   subtrees; probe cache-safety leg (tree-expanded, dataclass-equal copy must
   produce identical canonical key) 0 failures.
3. **Per-compilation identity memo — CONFIRMED.**
   Lifetime-safe by construction (memo holds the Expr strongly; state dropped
   on build exit); probe memo stress 0/200 failures under gc/id-recycling
   pressure; memo-off flag reproduces legacy output (pinned by tests).
4. **Persistent compile path — CONFIRMED-WITH-CORRECTION.**
   Probe: `keys_differ: False`, persistent ≡ normal executed ops; 9-test
   consistency suite green. Corrections: E4 language (F7a); and the subtree
   regime feeds cache-hit nodes (foreign to the per-call builder) into
   `make_*` — pre-fix this rode on digest-canonicalization returning one
   object per structure and left an eviction-window id-reuse hazard; the F4
   fix (below) closes it structurally. Residual: collision assumption (E4);
   concurrency documented unsupported.
5. **Compact internal interning — CONFIRMED-WITH-CORRECTION (F4).**
   The Phase-B speedups are real and retained (probe headline: tree compile
   152 µs class; pathological prep 3.0 ms class). The confirmed regression —
   foreign nodes registered by bare identity — is fixed by **structural
   adoption**: `_node_uid` misses (impossible for internal nodes, which
   register at intern time) route to `_adopt_foreign`, an iterative post-order
   find-or-create of this builder's structurally identical twin (exact shape,
   no re-canonicalization), registering the foreign id under the twin's uid
   and pinning the foreign object in `_foreign_keepalive` for the builder's
   lifetime. Internal compilation keeps the O(1) fast path untouched; foreign
   input pays O(subtree) once per object (the historical deep-hash cost).
   Restores: `AND(x,x)==x`, `OR(x,x)==x`, `XOR(x,x)==0`, complement collapse,
   equal-key ⇒ same interned node, mixed ≡ all-internal, and id-reuse safety.
6. **Executed-operation accounting — CONFIRMED.**
   Probe instrumented leg: declared vs *counted* primitive ops exact for both
   the words and bigint executors across cm/cm_legacy/cse/cse_flat/raw arms;
   `program_metrics` purity (A3) retained.
7. **Structural-CSE baseline — CONFIRMED.**
   Subprocess independence check: never imports `cm_ir`. Linear structural
   hash-consing; `flatten=True` splices only single-consumer chains. Used as
   the *reference implementation* for corrected-corpus truth functions, with
   a CM-vs-CSE bit-equality assertion at every admission.
8. **v1/v2 serde — CONFIRMED-WITH-CORRECTION (F7b).**
   Probe serde fuzz: 0 round-trip failures, 0 non-ValueError escapes over 400
   mutations. v1 byte-shape pinned; deep v1 iterative. v2 reader strengthened
   as in §1/F7.

## 4. Corrected E3 (authoritative replacement for the archived Phase C)

Design actually delivered (verified property-by-property in the corpus):
192 formulas = 3 exact-semantic-support strata (k ∈ {8,12,16}) × 4 operator
families × 2 shapes × 8; every stratum has 64 formulas with semantic support
exactly {x0..x{k−1}} (influence measured on the complete packed truth
function), 192/192 distinct structural hashes *and* distinct truth-function
SHA-256s per stratum, family membership measured on structural binary-op
classes (dominant ≥60%; mixed: ≥3 types, none >50%), tree arm with no
repeated non-leaf structural subtree, shared arm with sharing factor ≥1.5,
all under the 60,000-unfolded cap so the raw ablation runs everywhere.
Deterministic pilot (4/cell, 13.6 s) passed the 60-minute widening gate;
full run 26.6 s wall. Corpus SHA-256
`8a6da87c…f92f6e68a` (matches results `_meta`); seeds/corpus byte-stable
across PYTHONHASHSEED.

Primary result — repaired CM kernel / structural-CSE kernel, bare
`_eval_words`, per-formula paired log ratios, stratified bootstrap (family ×
shape cells fixed), 2000 draws:

| stratum | n | blocked geomean [95% CI] | median | round-robin geomean [CI] | σ_log |
|---|---:|---|---:|---|---|
| live_k=8 | 64 | **0.871** [0.844, 0.895] | 0.920 | 0.887 [0.863, 0.909] | 0.18 |
| live_k=12 | 64 | **0.869** [0.851, 0.886] | 0.904 | 0.893 [0.875, 0.910] | 0.14 |
| live_k=16 | 64 | **0.925** [0.913, 0.939] | 0.932 | 0.936 [0.926, 0.946] | 0.08 |
| all | 192 | **0.888** [0.876, 0.899] | 0.923 | 0.905 [0.894, 0.915] | 0.14 |

Families (blocked geomeans across strata): xor_dom 0.748–0.853, andor_dom
0.867–0.927, impeqv_dom 0.966–0.979 (k8 CI [0.918, 1.005] and k16
[0.954, 1.000] include/touch parity), mixed 0.882–0.948. Shapes: tree
0.918–0.950, shared 0.803–0.901. Interaction extremes: xor_dom×shared 0.736;
impeqv_dom×tree 0.995 [0.980, 1.009] (parity). Blocked and round-robin agree
within ~2% everywhere and are never pooled.

**Mechanism (corrected).** On exact-support formulas CM's semantic rewrites
almost never compress *executed primitive operations*: executed-op ratio
cm/cse has median 1.000 (family geomeans 0.914–0.973; only 34% of formulas
see any compression; min 0.474). What CM does compress is *instruction
count* via n-ary chain merging (flat-instruction ratio geomean 0.693; 0.455
in xor_dom), and log kernel ratio correlates with log instruction ratio at
r = 0.824. Adding sharing-aware flattening to the CSE baseline closes almost
the whole gap: cm/cse_flat kernel geomean **0.985**. The archived narrative
("advantage tracks executed-op compression from semantic rewrites,
right-skewed by rewrite-collapse") was an artifact of the degenerate corpus —
its collapse exhibits were constants and reduced-support functions.

**Costs.** CM preparation is 4.30× CSE (geomean; range 2.0–6.1). Break-even
vs CSE kernel gains: median 78.5 evaluations over the 162/192 formulas that
break even; **30/192 never break even** (17 impeqv_dom, 9 mixed, 4 andor_dom;
24 trees, 6 shared; none xor_dom). Wrapper overhead median 23 µs, reported
separately; it still dominates small-k harness-boundary comparisons.
`warmenv_compile_eval` totals are warm-process numbers, not cold starts.

**Scope.** One local Windows box; results generalize only to this balanced
synthetic generator (`e3-corrected-2026-08-02.1`); a CI excluding parity is
not a universal CM claim.

## 5. Phase 4 — claim disposition

| claim | disposition |
|---|---|
| V4 C1 "CM modestly ahead at controlled live_k 12/16" | **SUPERSEDED (second supersession).** Corrected statement: on 192 exact-support synthetic formulas, the repaired CM *kernel* is 7–13% geomean faster than plain structural CSE (all-corpus 0.888 [0.876, 0.899]), operator-dependent (parity on IMP/EQV-dominant trees), and ≈parity (0.985) against CSE+sharing-aware-flattening; the wrapper boundary still reverses the sign at small k. Neither the original C1 sentence nor the archived-E3 restatement (0.843) should be cited |
| 128×/240× multiplier compression | **RETRACTION STANDS.** Post-repair CM executes exactly the CSE op count on that case (368→167); the historical multiplier was executed-op-miscounting + a no-CSE baseline + pathological pre-repair prep |
| Repaired CM vs strong CSE at the kernel boundary | **CORRECTED.** Real but modest: 0.888 geomean, CI excluding parity in every stratum; mechanism is n-ary instruction merging, *not* semantic op-compression (median executed-op ratio 1.000); ≈1.5% residual vs a flattened CSE baseline |
| Total-cost / amortization | **RETAINED-WITH-CORRECTION.** Prep multiple 4.30× geomean; break-even median 78.5 evals; 30/192 formulas never break even (concentrated impeqv/tree). Workload-dependence stands |
| Platform / schedule claims | **RETAINED.** Blocked vs round-robin within ~2%, never pooled; local-box scope; no cross-platform claim (pod replication remains prepared-not-executed) |
| Compile/DAG-scaling claim | **RETAINED.** Sharing-aware flattening + memo: pathological prep 403 ms → 3.0 ms on the probe headline; compact interning keeps unshared-tree compiles at the 152 µs class (probe re-verified post-F4-fix) |
| BDD-boundary conclusions | **UNRESOLVED here (out of scope).** No new evidence this pass; the 07-24 matched CUDD results stand on their own terms |

Public-facing claims should not be updated until this corrected E3 passes the
independent review this pass is staged for.

## 6. Working-tree changes made by this pass (all uncommitted)

Production (3 files): `cm_ir.py` (F4 structural adoption + `_foreign_keepalive`;
F7a docstring), `cm_expr_serde.py` (F7b reachability validation + contract
docs), `tests/test_expr_serde_v2.py` (+3 tests, additive).
New tests (3 files): `tests/test_foreign_node_interning.py` (11),
`tests/test_e3_output_safety.py` (5), `tests/test_e3_corpus_determinism.py` (1).
New deliverables: corrected E3 driver/corpus/results/summary, pilot directory,
validation probe + JSON, probe-rerun JSON, this report, the file index, and the
master handoff (absolute paths in
`CM_GAP_FILE_INDEX_AND_SUPERSESSION_2026-08-02.md`).
Preserved untracked: `deliverables_n22_24\CM_FINAL_REVIEW_PROMPT_2026-08-02.md`,
`.claude\`. `bitset_backend.py` is untouched by this pass.

## 7. Tests and verification

- Full system-Python suite (`python -m pytest tests -q --basetemp
  tmp\pytest_cm_consolidated`): **326 passed, 0 failed (+4 subtests), 414 s**
  — the prior 306 plus the 20 tests added by this pass, all post-fix.
  (Note: the six collection errors initially observed were caused by the
  basetemp *parent* directory not existing — environmental, reproduced and
  cleared by creating `tmp\`; the archived "306 passed" figure was accurate.)
- Adversarial probe re-run post-fix (new output path): fuzz 0/300, corpus
  49/49 identical keys, instrumented metrics exact, memo stress 0/200,
  persistent ≡ normal, serde fuzz clean, CSE independent.
- Corrected E3: 192/192 packed-equal across cm/cse/cse_flat/raw and the
  wrapper; truth-SHA re-verified against the corpus at measurement time.
- Corpus determinism: byte-identical across PYTHONHASHSEED 0/1/31337.
- Output safety: default run refuses existing targets (test-proven).
- `git diff --check`: clean. `git status` reviewed; only the files in §6.

## 8. Unresolved risks and external work (not executed)

- blake2b-128 collision assumption in the persistent cache (documented, E4).
- Re-associated chain variants remain separate guard classes (pre-existing).
- Corrected E3 remains single-machine, synthetic-generator-scoped; EPFL
  external corpus (download) and pod replication (E8 gate) remain **prepared
  but blocked on authorization** — commands and stop rules in
  `CM_GAP_FINAL_REPAIR_AND_E3_2026-08-02.md` §External work.
- The uncommitted working tree needs Brian's review + commit decision
  (suggested decomposition in the master handoff).

**READY FOR INDEPENDENT REVIEW**
