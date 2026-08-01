# CM Final Repair, Compact-Key Gate, and Corrected E3 Replication

Date: 2026-08-02
Base: `main` = `b6ce6b2`, all changes uncommitted in the working tree (no commit/push).
Benchmarks: `.venv\Scripts\python.exe` (3.13.5, numpy 2.3.2). Tests: system Python 3.10.11.
Driver: `cm_gap_final_repair_e3_2026_08_02.py` → `cm_gap_final_repair_e3_results_2026_08_02.json`,
`CM_gap_final_repair_e3_summary_2026_08_02.csv`, corpus `CM_gap_e3_corpus_2026_08_02.jsonl`.
Adversarial re-verification: `cm_gap_repair_merge_review_probe_2026_08_02.py` (re-run after
every phase; results file updated in place — it is this round's living verification record).

Decision at end: **READY FOR FINAL REVIEW**.

---

## Phase A — merge-review concerns and dispositions

| merge-review concern | disposition |
|---|---|
| 1. Persistent path legacy flattening | **FIXED (A1)** — persistent and normal paths now produce identical canonical keys and graph shapes; verified by probe (`keys_differ: False`, 167==167 executed ops) and a new 9-test consistency suite |
| 2. Unshared-tree compile overhead | **ACCEPTED, remeasured (A5/B)** — repaired-vs-legacy flags ≈1.50× on depth-4 trees (memo ≈1.09×, prepass ≈1.38×; ~145 µs absolute mean); compact interning (Phase B) made the *absolute* tree compile faster than the pre-B baseline (152 vs 168 µs) |
| 3. Commutative-equivalent duplicates not merged | **FIXED (A4)** — prepass uid keys now sort commutative operands; `Xor(a,b)`/`Xor(b,a)` (and AND/OR/EQV analogues, nested permutations, separately allocated parents) are one guard class; duplication eliminated, keys equal to the identity-shared form; corpus keys unchanged |
| 4. Deep v1 `RecursionError` | **FIXED (A2)** — both v1 serializer and deserializer are now iterative (preferred option 1); tested at 0.5×, 1×, 10× the recursion limit; malformed deep input fails with `ValueError`; v1 output byte-shape unchanged (pinned by test); v2 validation untouched |
| 5. `program_metrics` `word_plan` side effect | **FIXED (A3)** — observationally pure (reuses an existing plan, never stores one); state-snapshot test added |
| 6. `build_memo` not in reuse-cache key | **RETAINED (A5)** — no semantic or canonical-output difference exists (memo-on/off identity already pinned by `test_memo_off_flag_reproduces_legacy_visit_pattern`, and the persistent path adds `test_build_memo_flag_does_not_change_output_or_fragment_cache`); performance-only options must not fragment caches |

### A1 design and soundness (the substantive piece)

The persistent path (`compile_expr_to_cm_ir_persistent`) was rebuilt as follows:

- **Cache keys** are commutative-canonical, **association-preserving** digests
  (`_persistent_digest`: blake2b-128, operand digests sorted for AND/OR/XOR/EQV, IMP
  ordered, **no chain flattening**), prefixed with the flattening option (`s1:`/`s0:`).
  The old key (`expr_structural_hash`) flattens associative chains and is provably too
  coarse under sharing-aware canonicalization: two re-associations of the same chain
  around a shared subchain canonicalize *differently*, so hash-equal entries could serve
  the wrong shape. Digest equality in the new scheme implies an identical
  commutative-sorted structural uid graph — exactly the guard's equivalence classes
  after A4 — and hence an identical compile (this is why **A4 is a prerequisite of A1**).
- **Two caching regimes**, chosen per expression by the prepass:
  *no shared associative classes* → guarded canonicalization is context-free (identical
  to always-splice), so subtrees are cached and reused individually — preserving the
  historical related-expression reuse behavior and the existing
  `test_cm_persistent_ir_cache` semantics (commutative-variant hits, subtree hits,
  `assertIs` identity); *shared classes present* → canonical shape is context-dependent,
  so only the root is cached and compilation delegates to `CMIRBuilder.build`, which is
  normal-path-equivalent by construction.
- **Cross-regime safety**: a digest match across regimes is impossible — if a cached
  subtree had internally shared classes, any superexpression containing it would also
  have shared classes and would never take the subtree path; conversely a context-free
  expression cannot digest-match a root entry whose class graph contains shared classes.
- No process-global object-id state; the digest memo is per-call and id-keyed only while
  the caller holds the expression; eviction/size/diagnostics behavior retained.

Tests added (`tests/test_persistent_path_consistency.py`, 9 tests): shared XOR/AND/OR
DAGs (normal≡persistent keys, programs, metrics, packed output; both flag settings),
subchain preservation (6 executed ops), separately-allocated copies and tree-expanded vs
defs/ref representations all agreeing, commutative-variant hit that must equal the
variant's own normal compile, cold-miss/warm-hit counters, option-change isolation,
memo-flag non-fragmentation, eviction bound + correct recompile, 60-round GC/id-reuse
pressure. Concurrency is not claimed by the API and is documented as unsupported.

### Phase A gate

- Targeted suites: 106 passed (+4 subtests).
- Full system-Python suite: green (background gate run, exit 0; final post-B run below).
- Adversarial probe: fuzz 0/300, cache-safety 0, corpus 49/49 identical keys, packed
  equality everywhere, instrumented metrics exact, memo stress 0 failures,
  **persistent == normal** (167 == 167, `keys_differ: False`).

## Phase B — compact internal keys: **GO** (productionized)

Three options evaluated: (1) **child intern uids for internal lookup, public structural
`CMNode.key` retained** — implemented; (2) stable structural digests with equality
fallback — rejected (digest computation is O(subtree) per new node, no asymptotic win
over the one-time deep hash, plus collision-handling complexity); (3) no change —
control, measured.

Implementation (~60 lines in `cm_ir.py`): `_interned` is keyed by `(op, child intern
uids)` tuples instead of deep structural tuples; a builder-local `_uid_of_node` map
(nodes kept alive by `_interned`; foreign nodes registered by identity — semantically
safe, documented); the `seen`/`negated_bases` sets and XOR parity `counts` in
`make_and/or/xor` hold uids instead of CMNodes, removing the O(subtree)-per-node
first-hash cost. Public keys, arg order (still sorted by `node.key`), rewrite semantics,
and diagnostics counters are unchanged. Within a builder, compact-lookup equality is
provably equivalent to deep-key equality (induction over interned children).

Gate results (baseline = post-Phase-A):

| criterion | result |
|---|---|
| ≥2× on two materially different high-sharing families | **3.57×** (mult seq nb8: 11.9→3.3 ms), **5.74×** (ladder d12: 4.0→0.70 ms); also 2.34× (mult bal nb8) |
| no material regression on random unshared trees | improved: 168→152 µs mean |
| 0 differential failures | probe fuzz 0/300 + full suite green |
| 0 canonical-key changes on the 49-formula corpus | 49/49 identical |
| identical normal and persistent output | `keys_differ: False`, ops equal |
| no collision/nondeterminism | lookup keys are exact structural identifiers (no lossy hashing); uids never serialized; public keys unchanged → cross-process determinism unaffected |
| reviewable | one contained hunk-set in `cm_ir.py` |

Cost decomposition on mult seq nb8 (instrumented): interning 10.7→0.8 ms, canonicalize
0.7→0.5 ms, rewrite 3.5→0.5 ms, live-vars 1.4→1.0 ms.

### Cumulative before/after (legacy flags = pre-repair behavior, same code)

| case | executed word ops | prep µs legacy → final (CSE) | kernel µs legacy → final (CSE) |
|---|---:|---:|---:|
| mult seq nb8 bit8 | 368 → **167** (=CSE) | 426,803 → **3,171** (552) — **135×** | 572 → **300** (327) |
| mult bal nb8 bit8 | 296 → **167** | 28,752 → **2,827** (533) | 505 → **323** (325) |
| ladder d12 | 31 → 31 | ~65,000† → **703** | unchanged |
| random depth-4 trees (24) | unchanged | ≈1.50× flags-relative; 152 µs absolute mean | unchanged |

† ladder d12 legacy estimated from the d11 measurement series (65 ms at d11); the
directly measured post-A → post-B step is 4,036 → 703 µs.

## Phase C — corrected E3 replication

Corpus: **96 distinct formulas** (96 distinct structural hashes; serialized with v2
docs, seeds, and metadata in `CM_gap_e3_corpus_2026_08_02.jsonl`): strata live_k
∈ {8, 12, 16} × operator families {xor_dom, andor_dom, impeqv_dom, mixed} × shapes
{low-sharing tree, shared DAG} × 4. Formula identity is the inferential unit. All arms
packed-bit-equal on every formula before timing; wrapper output equality checked too.

Primary result (repaired CM kernel / structural-CSE kernel, per-formula paired log
ratios, cluster bootstrap over formulas, 2,000 draws):

| stratum | n | blocked geomean [95% CI] | blocked median | round-robin geomean [CI] | σ_log (df) |
|---|---:|---|---:|---|---|
| live_k=8 | 32 | **0.768** [0.631, 0.886] | 0.867 | 0.784 [0.669, 0.883] | 0.53 (31) |
| live_k=12 | 32 | **0.860** [0.799, 0.914] | 0.905 | 0.878 [0.820, 0.929] | 0.20 (31) |
| live_k=16 | 32 | **0.906** [0.844, 0.955] | 0.946 | 0.912 [0.851, 0.960] | 0.18 (31) |
| all | 96 | **0.843** [0.780, 0.894] | 0.928 | 0.856 [0.803, 0.900] | 0.35 (95) |

Subgroups (blocked geomeans): xor_dom 0.70–0.76, andor_dom 0.80–0.92, impeqv_dom
0.92–1.00 (parity — IMP/EQV get no flattening or parity rewrites), mixed 0.66–0.97;
trees 0.94–0.96, shared DAGs 0.63–0.86. Blocked and round-robin agree within ~2%
everywhere (never pooled; the schedule question stays closed).

**Mechanism and honesty notes.** The kernel edge tracks executed-op compression from
CM's *semantic rewrites* (executed-op ratio cm/cse: 0.80 xor_dom, 0.94 andor_dom, ~0.96
impeqv_dom), plus n-ary in-place accumulation on chains. The distribution is
right-skewed by rewrite-collapse cases — the extreme being `e3-k8-mixed-shared-4`
(CM compiles to **0** executed ops; ratio 0.057), which is why medians (0.87–0.95) are
reported alongside geomeans and why σ_log at k=8 is 0.53. Costs stay asymmetric: CM
preparation is 4.3× CSE geomean; break-even vs CSE is median 62 evaluations among the
78/96 formulas where CM's kernel is strictly faster and **never** for the other 18.
Wrapper overhead (median 26 µs) is reported separately and still dominates small-k
harness-boundary comparisons. Local box only; no cross-platform claim.

**E3 conclusion.** With formula and operator diversity as the inferential unit, the
repaired CM kernel is modestly but genuinely faster than a strong structural-CSE
baseline at the kernel boundary (all-corpus geomean 0.843, CI excluding parity in every
stratum), with the advantage concentrated exactly where CM's algebra does work
(XOR-heavy, shared, rewrite-rich inputs) and vanishing on IMP/EQV-dominant formulas.
The steady-state claim is defensible; the total-cost story remains workload-dependent
(prep multiple + break-even reported per formula).

## Revised disposition of published claims

- **V4 C1 "CM modestly ahead at controlled live_k 12/16"** — supersede rather than
  merely retract: the corrected, formula-clustered statement is "repaired CM's *kernel*
  is 6–23% faster geomean than a structural-CSE baseline across live_k 8–16 (CIs
  excluding parity), operator-dependent (parity on IMP/EQV-dominant), on one local
  machine; the harness/wrapper boundary reverses the sign at small k and must be
  reported separately." The original sentence (single formula per stratum, wrapper arm,
  weak baseline) should not be cited.
- **128×/240× multiplier compression** — retraction stands; corrected chain: raw
  baseline lacked CSE; instruction counts were not executed ops; CM ≡ CSE+flatten
  op-for-op; post-repair CM executes exactly the CSE op count (167) and wins the
  multiplier kernel only via execution details (300 vs 327 µs), while preparation is
  135× cheaper than pre-repair but still ~6× the CSE baseline on that case.

## Test results (complete)

- Full system-Python suite after all phases: **306 passed, 0 failed** (+4 subtests,
  388 s). Includes 15 new Phase A tests (9 persistent-consistency, 4 deep-v1 serde,
  1 metrics purity, 1 commutative-equivalence guard) on top of the prior 291.
- Adversarial probe after Phase B: all sections green (fuzz 0/300, corpus 49/49,
  metrics instrumented exact, memo stress 0/200, persistent≡normal).
- E3 driver: 96/96 formulas packed-equal across all arms and the wrapper.
- `git diff --check`: clean.

## Production files changed (cumulative working-tree diff)

`cm_ir.py` (guard, memos, A4 uid sorting, A1 persistent rewrite + `_persistent_digest`,
Phase B compact interning), `bitset_backend.py` (metrics incl. A3 purity, CSE baseline),
`cm_expr_serde.py` (v2 schema, A2 iterative v1), `tests/test_cm_optimizations.py`
(3 widened assertions). New tests: `test_program_metrics.py`,
`test_share_aware_flatten.py`, `test_build_memo.py`, `test_expr_serde_v2.py`,
`test_bitset_cse.py`, `test_persistent_path_consistency.py`.

## Remaining blockers

None for this scope. Open follow-ups (non-blocking): E3 breadth (only 4 formulas per
cell; widen before publication), external corpus validation, cross-platform replication,
and the documented approximation that *re-associated* (as opposed to commuted) chain
variants remain separate guard classes — measured limitation, concrete case in
`test_share_aware_flatten.py` history: `Xor(H, c)` vs an interleaved re-association can
still duplicate; commutative permutations no longer do.

## External work — prepared for approval (NOT executed)

**EPFL combinational benchmark suite** (needs download authorization):

```bash
git clone --depth 1 https://github.com/lsils/benchmarks.git external/epfl-benchmarks
```

Expected content: `arithmetic/` (incl. `multiplier.aig`, ~27k AIG nodes) and
`random_control/` in AIGER/BLIF/Verilog. Record: repo commit SHA, per-file SHA-256
(`certutil -hashfile <file> SHA256`), byte sizes. Cost: ~50 MB download, zero compute.
Plan: ASCII-AIGER (`aigtoaig -a`) or direct binary-AIGER parse → v2 defs/ref docs;
extract output cones with live support ≤ 16 via cone-of-influence; stop rule: if no
cone with live_k ∈ [8,16] exists in a circuit, record and skip (no synthesis).

**Pod replication (E8 gate)** (needs pod authorization): 5 × `cpu3c` pods via
`cm_runpod_deploy.py`, frozen E3 corpus + driver, ~5 pod-minutes each, est. < $1 total;
stopping rule: abort a pod if setup exceeds 15 min or the driver exceeds 2× local
runtime; record CPU model, cgroup quota, image digest per pod (the
`CM_LATENT_FIXES_2026-07-23.md` worker-redeploy note applies).

## Proposed commit decomposition (do not execute)

1. `feat(cm): sharing-aware flattening with per-compilation structural memo` —
   `cm_ir.py` (guard + `_BuildState` + A4 uid sorting), `tests/test_share_aware_flatten.py`,
   `tests/test_build_memo.py`, `tests/test_cm_optimizations.py`.
2. `feat(cm): consistent persistent compile path` — `cm_ir.py` (`_persistent_digest`,
   persistent rewrite), `tests/test_persistent_path_consistency.py`.
3. `perf(cm): compact intern keys for builder lookup` — `cm_ir.py` (Phase B hunks).
4. `feat(bench): executed-op metrics and structural-CSE baseline` — `bitset_backend.py`,
   `tests/test_program_metrics.py`, `tests/test_bitset_cse.py`.
5. `feat(serde): v2 defs/ref DAG schema; iterative v1` — `cm_expr_serde.py`,
   `tests/test_expr_serde_v2.py`.
6. `bench(data): gap-repair audits, merge review, and corrected E3 artifacts` —
   `deliverables_n22_24/*2026_08_02*` (and the 2026-08-01 audit inputs if Brian wants
   them tracked).

Each message should end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
per repo convention. (Hunk-level splitting of `cm_ir.py` across commits 1–3 requires
`git add -p`; if that is more ceremony than wanted, commits 1–3 can collapse into one
`feat(cm)` commit without loss of reviewability — the report sections map the hunks.)

## Recommended next action

Brian reviews and commits (decomposition above), then: widen E3 cells (8–10 formulas
per cell) for publication-grade CIs, request EPFL download + pod approvals to run the
prepared external and cross-platform legs, and restate the public C1/multiplier text
per the disposition section.

**READY FOR FINAL REVIEW**
