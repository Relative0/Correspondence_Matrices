# CM Gap Repair — Implementation Report

Date: 2026-08-02
Base revision: `main` = `b6ce6b2` (uncommitted working-tree changes only; no commit/push).
Benchmark interpreter: `.venv\Scripts\python.exe` (3.13.5, numpy 2.3.2).
Test interpreter: system Python 3.10.11.

This report covers the scoped production repairs authorized after the 2026-08-01/02
benchmark-gap audits: operation-count metrics, sharing-aware associative flattening,
lifetime-safe build memoization, DAG-preserving serialization, a fair BitSet baseline,
and corrected benchmark boundaries. No historical report or CSV was modified.

---

## Phase 0 — Independent reproduction of the load-bearing claims

All four were re-measured in a fresh process before any production change
(8×8 sequential multiplier central bit unless noted; packed equality asserted first):

| claim | result | verdict |
|---|---|---|
| CM executes ~368 primitive word ops vs ~167 binary-CSE | instructions 147 (CM) / 167 (CSE) / 147 (CSE+flatten) / 38,869 (raw); executed word ops **368 / 167 / 368** / 38,869 | **CONFIRMED** |
| Associative flattening destroys shared-subchain reuse | CSE+flatten reproduces CM op-for-op (147 instr / 368 executed); eval 565 µs (CM) vs 293 µs (CSE); prep 449 ms vs 0.28 ms | **CONFIRMED** |
| Compact keys give a further 5–10× compile | current 374 ms / id-memo 9.8 ms / compact 0.97 ms → **10.2×** over the memo | **CONFIRMED** |
| Harness wrapper flips the controlled-strata sign | kernel ratios 0.718 / 0.758 / 0.692 (live_k 8/12/16, CM faster) vs harness-arm 2.677 / 2.003 / 1.250 (CM slower) | **CONFIRMED** |

With both gating claims confirmed, all phases proceeded.

## Production files changed

| file | change |
|---|---|
| `bitset_backend.py` | +`program_metrics()` (authoritative executed-op accounting); +`compile_expr_cse` / `get_expr_cse_program` / `eval_expr_words_cse` (structural-CSE production baseline, iterative, int-keyed, optional sharing-aware flattening); `FlatProgram` docstring now states `len(ops)` is an instruction count; `compile_expr_flat` relabeled ABLATION BASELINE ONLY |
| `cm_ir.py` | `CMIRBuilder`: per-compilation `_BuildState` (lifetime-safe memo holding `(expr, node)` pairs), syntactic-fanout prepass `_shared_assoc_uids`, splice guard in `_canonicalize_commutative_args`; `build` split into entry + `_build_rec`; new flags `share_aware_flatten`/`build_memo` (default True) threaded through `compile_expr_to_cm_ir(_cached)`; `_COMPILED_IR_CACHE` key now `(expr, share_aware_flatten)`; new diagnostics `build_memo_hits`, `build_shared_assoc_subexprs`, `canonical_splice_suppressed` |
| `cm_expr_serde.py` | +v2 defs/ref DAG schema: `expr_to_json_dag` (iterative, deterministic, structural dedup) and auto-detecting `expr_from_json` with full validation (forward/self/dangling-ref, duplicate-definition, type, root, version rejection); v1 tree schema unchanged and documented as unable to preserve sharing |
| `tests/test_cm_optimizations.py` | two assertions widened to accept `build_memo_hits` alongside `subtree_cache_hits` (identity reuse is now caught one layer earlier; the tested property — shared subtree compiled once — is unchanged) |

New test files: `tests/test_program_metrics.py`, `tests/test_share_aware_flatten.py`,
`tests/test_build_memo.py`, `tests/test_expr_serde_v2.py`, `tests/test_bitset_cse.py`.

New deliverables: this report, `cm_gap_repair_benchmark_2026_08_02.py`,
`cm_gap_repair_results_2026_08_02.json`, `CM_gap_repair_before_after_2026_08_02.csv`,
`CM_GAP_REPAIR_HANDOFF_2026-08-02.md`.

## Design decisions and rejected alternatives

**Phase 2 — sharing-aware flattening.** Two designs were evaluated:

1. **Chosen: build-time fanout-guarded splicing.** An iterative prepass interns every
   subexpression syntactically (small-int keys) and counts consumer edges per structural
   equivalence class — merging separately allocated but structurally equal subtrees, so
   tree-JSON-expanded input is guarded too. During canonicalization, an associative child
   whose class has >1 consumer is kept as a node instead of being spliced. All guard state
   lives in a per-compilation `_BuildState` and is discarded when the outermost `build`
   returns — no object id outlives its referent (the memo holds strong `(expr, node)`
   pairs; the prepass maps are used only while the root argument is alive). Direct
   `make_*` calls outside `build` see no state and behave exactly as before.
   One subtle bug was caught by the new tests during implementation: consumer edges must
   be counted once per *deduplicated structural parent*, not per identity occurrence,
   or duplicated copies of the same parent suppress flattening inside themselves.
2. **Rejected: lowering-time common-sub-multiset extraction.** By lowering time the
   shared subchain no longer exists as a node; recovering it means greedy kernel
   extraction over n-ary argument multisets — approximate, quadratic, and a far larger
   correctness surface than a fanout bit.

Why the chosen design is lower-risk: it flattens exactly as before wherever fanout is 1
(verified: all 49 published corpus formulas produce **bit-identical canonical keys**
with the repair on vs off, and the wide-associative invariant tests pass unchanged);
it changes canonical form only for expressions that contain genuinely multi-consumer
associative subchains — inputs the published corpus does not contain; keys remain fully
deterministic (fanout is a pure function of the input); Boolean semantics are covered by
packed-equality tests against the raw evaluator plus brute-force truth tables. Node-level
rewrites still fire across the guard (e.g. `Xor(h, h)` with shared `h` cancels to const 0
— tested). Timing gains were not accepted at the price of silent semantic change: every
before/after row asserts exact packed equality across all five arms.

**Phase 3 — memoization.** Process-global `id(expr) → node` maps were ruled out (the
audit's id-reuse hazard). The memo is scoped to one outermost `build`, keys keep their
expressions alive, structurally equal but separately allocated objects are distinct memo
entries that converge at the interner (documented), and a GC-stress test compiles and
discards 60 expression graphs through one reused builder, checking every result against
the raw evaluator. Concurrent `build` calls on one builder remain unsupported (as was
already true via `_interned`); this is now stated in code.

**Phase 4 — compact keys: evaluated, not merged.** After memo+guard, the residual versus
the scratch compact-key prototype is still material — 12.3× (mult seq nb8), 6.4×
(ladder d10), 3.3× (mult bal nb8), 2.7× (mixed DAG) — so the optimization is justified as
the next step. It was left as the existing scratch prototype because merging a canonical
key rewrite immediately after landing two canonicalization-adjacent changes fails the
"small, reviewable" bar, and the merge condition in the brief ("only if improvement
remains material after flattening and memo") has now been *measured*, not assumed.

**Phase 5 — serde.** References must point strictly backwards (`ref < index`), making
cycles unrepresentable and validation O(n); duplicate structural definitions are
rejected, so accepted documents are canonical; serializer and deserializer are iterative
(tested on a depth-5000 DAG); deserialization constructs only `cm_exprlib` dataclasses
from validated ints/strings. The v1 tree schema remains readable/writable, with its
inability to preserve sharing documented.

**Phase 6 — baseline.** `compile_expr_cse` is independent of CM (no CM imports, no
canonicalization); with `flatten=True` it uses the same sharing-aware rule, and the tests
assert flattening never changes executed-op counts. On the default-path question: CSE
should become the benchmark baseline arm everywhere (raw stays as a labeled ablation),
because across mixed operators and non-arithmetic sharing it is never semantically
different, never executes more ops, and its prep is the cheapest of all arms. The
historical `eval_expr_words_bitset` entry point itself was left untouched for
comparability with published numbers; new work should call `eval_expr_words_cse`.

## Correctness tests and results

- Full project suite, system Python 3.10: **290 passed, 0 failed** (377 s). Nothing
  skipped or unexecuted.
- That total includes 67 new tests: metrics (7), sharing-aware flattening (10 — shared
  XOR/AND/OR subchains, separately allocated equal subtrees, defs/ref DAG, v1-tree
  round-trip, XOR parity, constants/negation/IMP/EQV around shared nodes, determinism,
  no-sharing invariance, legacy-ablation flag), build memo (7 — GC/id-reuse stress,
  state scoping, diagnostics on/off, repeated compilation), serde v2 (21 incl. 15
  malformed/adversarial documents), CSE baseline (14+ incl. random differential
  equality, deep-tree iteration, flatten-never-adds-ops).
- Corpus regression: all 49 `v4audit_corpus_2026_07_24.jsonl` formulas compile to
  bit-identical canonical keys with the repair on vs off.
- Benchmark-level: every formula row asserts exact packed equality across cm_old,
  cm_new, cse, cse_flat, and (where feasible) raw; the admission wrapper's result is
  separately checked against the kernel result. All true on all 71 formulas.

## Benchmark commands

```bash
.venv/Scripts/python.exe deliverables_n22_24/cm_gap_repair_benchmark_2026_08_02.py
```

(`--skip-slow` drops the two slowest legacy-compile cases.) Tests:

```bash
python -m pytest tests/ -q
```

## Before/after measurements

From `cm_gap_repair_results_2026_08_02.json` / `CM_gap_repair_before_after_2026_08_02.csv`
(71 formulas, all operators, low- and high-sharing, live_k ≤ 16, blocked schedule, warm
caches, repeat 100, min-of-3 blocks; `cm_old` = legacy flags, `cm_new` = repaired):

| case | executed word ops old→new (cse) | prep µs old→new (cse) | kernel µs old→new (cse) |
|---|---:|---:|---:|
| mult sequential nb8 bit8 | 368 → **167** (167) | 340,964 → **9,852** (474) | 545 → **287** (292) |
| mult balanced nb8 bit8 | 296 → **167** (167) | 19,748 → **2,615** (444) | 471 → **274** (348) |
| ladder d10 | 31 → 31 (31) | 31,442 → **1,029** (105) | 57 → 57 (57) |
| chain xor k16 | 15 → 15 (15) | 297 → 366 (62) | 26.2 → 26.2 (31.0) |

Family geomeans (only strata with ≥ 20 distinct formulas are summarized; formula
identity is the inferential unit):

| stratum (n) | cm_new/cse kernel | cm_new/cm_old kernel | cm_new/cm_old prep | cm_new/cse prep |
|---|---:|---:|---:|---:|
| high_sharing_dags (20) | **0.847** [0.57–1.05] | 0.982 | **0.639** | 4.8 |
| random_trees_depth4 (24) | **0.913** [0.63–1.07] | 1.009 | **1.511** | 3.4 |

Other boundaries: admission-wrapper overhead median 21.6 µs (14–108) — reported as its
own column, never folded into kernel numbers; break-even vs the CSE baseline now ranges
from 30 evaluations (mult bal nb8) to 2,050 (mult seq nb8, prep-bound) to ~10⁴ (ladder,
kernel parity). Peak scratch buffers are in the CSV per arm.

Two honest regressions, both understood: (1) random-tree compile is 1.51× slower geomean
(~100–200 µs absolute) — the prepass+memo overhead on inputs with nothing to share;
(2) chain prep gains ~70 µs of prepass. Neither affects kernel numbers or the published
compile-hoisted ratios.

## Remaining risks

1. **Canonical form now depends on within-expression sharing** for inputs that contain
   multi-consumer associative subchains: the same Boolean subformula keys differently
   inside vs outside such a context. This is deliberate and deterministic, verified
   no-op on the published corpus, but any future cross-expression node-key comparison
   across the repair boundary must use `expr_structural_hash` (unchanged), not CMNode
   keys.
2. **The persistent-cache path (`compile_expr_to_cm_ir_persistent`) still uses legacy
   always-splice flattening** — it never goes through `build`. Mixing paths on shared
   inputs yields differently shaped (semantically equal) node graphs. Wiring the guard
   into that path is a follow-up.
3. **Syntactic fanout is an approximation**: commutative-equal but syntactically
   different duplicate subtrees (e.g. `Xor(a,b)` vs `Xor(b,a)`) are not merged by the
   prepass, so duplication can persist in that corner.
4. Compact keys remain unmerged; 2.7–12.3× compile headroom is measured and waiting.
5. `_COMPILED_IR_CACHE` key shape changed (tuple); external code that peeked into the
   private dict by raw Expr key would miss (none exists in the repo).

## Published-claim disposition

- **V4 C1 "CM modestly ahead at controlled live_k 12/16" — restate, do not retain.**
  The comparison is arm-definition-dependent: kernel-vs-kernel CM is *faster* at all
  three controlled strata on this box (0.69–0.76) while the harness arm (admission
  wrapper vs bare kernel) is *slower* (1.25–2.68). Any restatement must name the
  boundary, and remains single-formula-per-stratum until E3-style clustered replication.
- **The 128×/240× multiplier compression headline — retract.** It compared instruction
  counts across incompatible instruction semantics against a no-CSE strawman. The
  corrected statement: CM's multiplier programs are executed-op-identical to
  CSE+sharing-aware-flattening (167 ops); after this repair CM's kernel is at parity or
  modestly ahead of the CSE baseline (family geomeans 0.85–0.91) with a 3.4–4.8×
  preparation multiple.
- **"CM is ~2× slower than binary CSE at steady state" (deep follow-up) — now
  historical.** True of the legacy compiler; repaired CM is 0.85–0.91× vs CSE.

## Next recommended experiment

Formula-clustered, operator-crossed replication (E3) run through
`cm_gap_repair_benchmark_2026_08_02.py`'s arms and boundaries — ≥30 distinct formulas
per controlled stratum, kernel and wrapper reported separately — followed by external
AIGER/EPFL cones through the v2 serde (blocked on download authorization) and, on the
engineering side, productionizing compact intern-ID keys behind the differential test
suite (measured 2.7–12.3× residual).
