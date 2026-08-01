# Deep Follow-Up Audit: CM Benchmark Gap Analysis and the Codex Audit

Date: 2026-08-02
Repo state: `main` = `b6ce6b2`, no tracked file modified. New artifacts only in
`deliverables_n22_24/` (`*deep_followup_2026_08_02*`).
Benchmark interpreter: `.venv\Scripts\python.exe` (3.13.5, numpy 2.3.2, dd 0.6.0).
Targeted tests: `tests/test_bitset_backend.py`, `tests/test_cm_ir_wide_associative.py`,
`tests/test_cm_persistent_ir_cache.py` — 18 passed on system Python 3.10.11. The full
suite was not run (nothing in production code was touched); everything else was skipped.
No pod was started. No file was downloaded (EPFL/AIGER acquisition needs approval — see §3).

Inputs audited: `CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md` ("the analysis"),
`deliverables_n22_24/CM_GAP_AUDIT_2026-08-01.md` ("the Codex audit"), its probe and JSON.
Reproduction driver: `cm_gap_deep_followup_2026_08_02.py`; machine-readable results:
`cm_gap_deep_followup_results_2026_08_02.json`. All timed comparisons asserted exact
packed-bigint equality before timing; deterministic program sizes are reported separately
from timings. Timings are one local Windows box and are used for contrasts, not levels.

---

## Executive verdict

Both prior documents are directionally useful and both contain load-bearing errors that
survive into their conclusions.

1. **The Codex CSE refutation (A2) is correct and incomplete — the truth is worse for CM
   than Codex reported.** Adding the missing `CSE + associative flattening` rung shows CM's
   compiled program is *op-for-op identical in executed work* to a syntactic
   CSE+flatten+sort pass on every multiplier topology tested. Moreover, both prior
   documents counted `len(prog.ops)`, which is not an executed-operation count: CM emits
   n-ary ops that the words kernel expands to `arity−1` binary kernel calls. Under executed
   accounting, CM's celebrated "program compression" **inverts**: on the 8×8 sequential
   central bit, CM executes **368** word ops versus **167** for a plain binary hash-consed
   baseline, because associative flattening splices *shared* subchains into every consumer
   and destroys their reuse. CM is ~2× slower than binary CSE at steady state on
   high-sharing arithmetic, and its compile is ~1000× more expensive (370 ms vs 0.37 ms).
   The one CM capability that survives a strong baseline is its local semantic rewrite set
   (XOR parity cancellation, complement collapse, EQV/IMP constant rules): 3–5× on formulas
   with planted redundancy that no syntactic pass can remove.

2. **The identity-memo dispute resolves as "both half right", with two new facts.** The
   memo is a large, real win (31–36× reproduced), so the analysis's "the obvious fix does
   not work" stays refuted. But the memoized arm is measurably super-linear from deep-key
   hashing, and a compact intern-ID prototype is another **5–10× faster** and scales
   cleanly — so the analysis's insistence that key representation is the ultimate fix is
   *also* vindicated as the eventual endpoint. New fact one: **the repo already ships a
   digest-memoized builder** (`compile_expr_to_cm_ir_persistent`, `cm_ir.py:233-297`) that
   achieves identity-memo-class cold compile with zero code change and is ~3× faster than
   the current builder even on sharing-destroyed (tree-JSON) input; neither audit tested
   it. New fact two: Codex's exact `IdMemoBuilder` prototype has a **lifetime hazard** —
   it stores `id(expr) → node` without keeping the `Expr` alive, so a builder reused across
   builds can return a stale node for a recycled id (the repo's own `_structural_digest`
   documents this exact requirement; the prototype violates it). Safe within one `build`
   call; unsafe as written as a persistent builder API.

3. **DAG-preserving ingestion is cheap and it works.** A ~90-line versioned `defs`/`ref`
   schema round-trips sharing exactly, rejects forward/dangling refs by construction
   (cycles are unrepresentable), remains backward compatible with v1 tree JSON, shrinks the
   8×8-scale artifacts ~70–130× on disk, and restores DAG-proportional compile when paired
   with the memo (36.7 ms → 0.97 ms on the depth-10 ladder). The claimed "hard blocker" is
   about one day of real work, not a research problem.

4. **The variance arithmetic dispute goes to Codex, verified independently.** The
   df-correct pooled within-cell σ is 0.1190 (local) / 0.0935 (pod) on 10 residual df, and
   the analysis's 0.084/0.065 are exactly `σ·√(10/21)` — residual SS divided by all 21
   formulas including singletons. Additional new numbers: σ has wide uncertainty
   (95% CI ≈ [0.083, 0.209] local, [0.065, 0.164] pod — the biased pod value sits at the CI
   *lower edge*); subtracting timing noise does not rescue the small values (moment-corrected
   σ ≈ 0.100/0.093); a regression that recovers singleton cells gives *larger* σ (0.15–0.22)
   because the live_k trend is strong and nonlinear. Plan with σ = 0.09–0.15: a 5% effect
   needs ~29–77 formulas per stratum; 3% needs ~75–205; 8% needs ~13–32.

5. **Repeat count is exonerated; the platform gap has a measured fixed-overhead signature.**
   The 1.390 pod/local geomean reproduces from the archived CSVs. The repeat-50 vs
   repeat-200 gap split (1.10 vs 1.50) that looks like a repeat effect is a pure confound:
   repeat was assigned adaptively by measured speed, so the repeat-50 group is the *slow*
   formulas (mean local BitSet 50.6 µs vs 17.0 µs). Correlation of log(gap) with
   log(local BitSet µs) is **−0.86**, and the gap declines monotonically from 2.67 at
   live_k=1 to 1.01 at live_k=16. Everything points at a per-call fixed overhead whose
   pod/local ratio differs from the kernels' — consistent with, but not proof of, F4's
   story. What repeat count *does* on the pod cannot be identified from existing data.

6. **The schedule finding (F5) shrinks to a pooling artifact.** With formula identity
   controlled and per-formula pairing, blocked vs fully interleaved moves the geomean ratio
   0.936 → 0.956 (~2%), with per-formula movement mostly under 10%. The analysis's "27%"
   was a pooled ratio across a changing mixture, not a paired effect. The mechanism is now
   measured rather than open: interleaving 13 distinct supports through the 4-entry words
   env LRU produces a 50% miss rate at ~138 µs per k=16 rebuild, added to *both* arms —
   an additive shared overhead that compresses pooled ratios toward 1.

7. **On BDDs, both prior documents are wrong in different places.** The analysis's "~4096
   at n=16" misuses the `2^n/n` asymptote: the exact maximum ROBDD size at n=16 is
   **8447** nodes, so Codex's measured 4419 contradicts the analysis's number but not the
   theorem. Codex's "interleaving was not uniformly best" is confirmed and strengthened:
   autoref **sifting beats both fixed orders** on every hard 8×8 output bit tested
   (e.g. bit 10: 3560 blocked / 4419 interleaved / **1586 sifted**), so any order
   comparison without dynamic reordering is against a strawman. Task-matched pipelines at
   n=16 (autoref, so build times are upper bounds): equivalence of two multiplier
   topologies is a dead heat *between CM and the BDD* (≈350 ms both) — and both lose by
   ~100× to the binary-CSE flat pipeline (~2 ms end-to-end); model count and full packed
   output favor the packed side heavily once prepared (packed eval 0.14 ms vs 9.3 ms
   pick_iter extraction at n=12); a 32-restriction batch is at parity even against
   pure-Python autoref, which means **CUDD would likely win restriction-heavy workloads**.
   Roadmap P6 should be split, not retired (details in §6).

The correctness story (packed equality everywhere, guard behavior) again survives
untouched; every new arm in this audit was bit-exact against the others.

---

## Q1. CSE and the multiplier headline

**Measured facts** (deterministic; `cse_ladder` section of the JSON):

| case | tree | id-DAG | struct-DAG | CM ops | CM word-ops | CSE ops | CSE+flat word-ops | raw ops |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mult seq nb8 bit8 | 77,739 | 251 | 183 | 147 | **368** | 167 | 368 | 38,869 |
| mult bal nb8 bit8 | 5,107 | 251 | 183 | 149 | 296 | 167 | 296 | 2,553 |
| mult chunk3 nb8 bit8 | 11,119 | 251 | 183 | 148 | 310 | 167 | 310 | 5,559 |
| xor chain k16 | 31 | 31 | 31 | 1 | **15** | 15 | 15 | 15 |
| shared ladder d8 | 2,043 | 43 | 41 | 25 | 25 | 25 | 25 | 1,021 |
| cancel: xor_cancel | 59 | 36 | 30 | **5** | 5 | 18 | 23 | 29 |
| cancel: contradiction | 34 | 33 | 29 | **2** | 2 | 17 | 17 | 17 |
| cancel: eqv_self | 53 | 30 | 27 | **2** | 2 | 15 | 16 | 26 |

Timings (this box, min-of-blocks, all arms bare `_eval_words` on prebuilt programs —
identical call shape; packed equality asserted first):

| case | CM prep | CSE prep | CSE+flat prep | Codex-key CSE prep | CM eval | CSE eval | CSE+flat eval |
|---|---:|---:|---:|---:|---:|---:|---:|
| mult seq nb8 bit8 | 369,941 µs | **369 µs** | 641 µs | 12,365 µs | 610 µs | **313 µs** | 658 µs |
| mult bal nb8 bit8 | 27,785 µs | 517 µs | 974 µs | 1,126 µs | 530 µs | 473 µs | 564 µs |
| shared ladder d8 | 8,545 µs | 64 µs | 100 µs | 257 µs | 60 µs | 56 µs | 52 µs |
| cancel xor_cancel | 423 µs | 59 µs | 66 µs | 53 µs | **9.3 µs** | 27.5 µs | 29.1 µs |

Findings:

1. **The missing rung closes to zero.** `CSE + associative flattening + commutative sort`
   reproduces CM's program op-for-op (identical `len(ops)` *and* identical executed word-op
   counts) on all 22 multiplier cases across three topologies, on the XOR chain, and on
   the ladder. On these inputs CM's compiler *is* CSE plus flattening — the Codex verdict,
   now with the gap fully accounted for rather than left as a 167-vs-147 residual.
2. **`len(prog.ops)` is not an executed-op count** (new defect, present in both prior
   documents). CM's n-ary ops expand to `arity−1` kernel calls (IMP/EQV to 2). The
   analysis's headline "CM 1 op vs raw 15 ops" on the XOR chain is 15 executed ops vs 15;
   the "240×/264× compression" on the 8×8 multiplier is 368 executed vs 38,869 — real, but
   ~106×, and only 2.2× *worse* than what a 150-line binary CSE gets you (167).
3. **Associative flattening is an anti-optimization on shared structure** (new; in neither
   audit). `_canonicalize_commutative_args` (`cm_ir.py:516-532`) splices same-op children
   into the parent regardless of whether the child is shared, so a shared XOR subchain is
   re-executed inside every consumer instead of computed once. That is the entire
   368-vs-167 difference, and it fully explains Codex's observation that CSE evaluated
   1.6–1.8× faster than CM — which their audit left attributed to vague "wrapper/program
   details". Measured per-op kernel cost is nearly identical across arms (~1.6–1.9 µs at
   k=16), so executed-op count is the whole story. Arm asymmetry was checked and excluded:
   `eval_cm_node_words` vs bare `_eval_words` on the same program differ by less than
   measurement noise (`defects.cm_arm_wrapper_vs_bare_us`).
4. **Preparation cost, which Codex never reported, is decisive.** CM compile is ~1000× the
   int-keyed CSE prep on the hard case. Codex's own CSE implementation carries
   nested-tuple keys whose hashing is O(subtree) per lookup — its prep is 12.4 ms where an
   intern-ID-keyed equivalent is 0.64 ms (19×). Their conclusion survives; their baseline
   was itself 19× from clean.
5. **Residual CM capability, precisely scoped.** On formulas with *semantic* redundancy —
   planted XOR cancellation, `p ∧ ¬p`, `EQV(h,h)` — CM's local rewrites collapse programs
   (5/2/2 ops vs 23/17/16 executed for CSE+flat) and win evaluation 3–5×. On random mixed
   shared DAGs with IMP/EQV the effect is small but present (22 vs 28 executed ops). This
   is the honest surviving claim: *a canonicalizing simplifier*, not a faster evaluator
   and not a compression layer beyond CSE.

**Inference.** The fair production stack for this contract is: binary structural CSE with
intern-ID keys + the existing words kernel, with CM's algebraic rewrite set (minus
share-blind flattening) as an optional simplification pass. On multiplier-style inputs,
that stack beats today's CM by ~2× steady-state and ~1000× in preparation.

**Unresolved.** Whether sharing-aware flattening (splice only single-consumer children)
retains canonicalization value without the duplication penalty — testable in a day on the
same driver; predicted executed ops for seq nb8 bit8 = 167 ± small.

---

## Q2. Builder identity memo

**Measured facts** (`builder_memo` section; visits = builder `build()` invocations;
all arms bit-exact against the reference):

| case (in-memory) | tree | id-DAG | current | id-memo | persistent cold | persistent warm | compact |
|---|---:|---:|---:|---:|---:|---:|---:|
| ladder d10 | 8,187 | 53 | 39,799 µs | 1,265 µs | 1,377 µs | 108 µs | **256 µs** |
| ladder d11 | 16,379 | 58 | 65,250 µs | 1,695 µs | 2,009 µs | 106 µs | **217 µs** |
| mult seq nb6 bit6 | 3,627 | 139 | 15,586 µs | 1,533 µs | 1,932 µs | 235 µs | **488 µs** |
| mult seq nb8 bit8 | 77,739 | 251 | 362,106 µs | 10,832 µs | 11,281 µs | 524 µs | **1,000 µs** |

| case (after tree-JSON round trip) | current | id-memo | persistent cold | compact |
|---|---:|---:|---:|---:|
| ladder d10 | 42,147 µs | 47,569 µs | **13,854 µs** | 12,524 µs |
| mult seq nb8 bit8 | 371,340 µs | 434,342 µs | **123,100 µs** | 133,590 µs |

Visit counts confirm mechanism: current = tree occurrences (77,739); id-memo and compact =
identity-DAG nodes (251).

Answers to the four framing questions:

- **Safe, valuable independent optimization?** Yes for cold compile on genuinely shared
  in-memory DAGs (31–36×, reproducing Codex), **with a lifetime caveat**: the prototype
  memoizes `id(expr) → node` without holding the `Expr`. Within a single `build()` call the
  root keeps children alive, so it is safe; a *builder object reused across builds* can hit
  a recycled id after the first expression is garbage-collected and silently return a wrong
  node. `_structural_digest`'s docstring (`cm_ir.py:160-165`) states the exact invariant;
  the production version must store `(expr, node)` or scope the memo per call.
- **Merely hiding deep-key super-linearity?** Partly. The memoized arm still grows faster
  than the DAG (id-memo 10.8 ms at 251 DAG nodes vs 1.7 ms at 58 — ~6.4× time for ~4.3×
  nodes, on wider/deeper keys), and the compact intern-ID builder is a further **5–10×**
  with clean scaling. The analysis was right that key representation is the real endpoint;
  wrong that the memo "does not work"; Codex was right to stage it, wrong to defer the key
  question to "if profiling still justifies it" — this profiling justifies it now.
- **Invalid under mutation/lifetime assumptions?** As written, yes across builds (above).
  `Expr` is a frozen dataclass, so mutation is not the issue; lifetime is.
- **Useful only for a direct Python API?** As things stand, yes — after tree-JSON the
  memo is *worse* than the current builder (434 ms vs 371 ms: pure overhead, zero hits),
  reproducing Codex's 37.9-vs-34.0. It becomes useful for serialized consumers exactly
  when Q3's DAG-preserving format lands.
- **New: the repo already contains most of the first repair.** The untested-by-everyone
  `compile_expr_to_cm_ir_persistent` (`cm_ir.py:233-297`) — a blake2b digest memo keyed by
  id plus a structural persistent cache — matches id-memo cold performance (within ~1.3×),
  gives ~100–500 µs warm recompiles, and is the *only* arm that also helps on
  sharing-destroyed tree input (3× on the 77k-node tree, because digesting is cheap and
  each unique structure is built once). Any staged plan should start by benchmarking and
  hardening this existing path rather than adding a third builder.

---

## Q3. DAG-preserving ingestion

A scratch versioned format was implemented in the driver (`expr_to_json_v2` /
`expr_from_json_v2`), not productionized. Schema: `{"version": 2, "nodes": [...],
"root": i}` with child references as integer indices constrained to `ref < index`.

**Measured facts** (`dag_serde` section):

- Sharing preserved exactly: identity-DAG 53 → 53 (ladder d10), 191 → 191 (mult nb7 bit7);
  a `structural` dedupe mode recovers sharing the constructors lost (191 → 139 defs).
  v1 tree round-trip of the same objects yields 8,187 / 16,499 identity nodes — the
  analysis's "the frozen-corpus format cannot represent a circuit" is confirmed, but as a
  one-day fix, not a blocker.
- Rejection: forward refs, self refs, dangling refs, bad root, bad version all raise
  `ValueError`; cycles are unrepresentable by construction (topological index constraint).
- Backward compatibility: v1 tree documents parse through the same entry point; semantics
  verified by packed equality.
- Compile becomes DAG-proportional through the new path: ladder d10 after v2 round trip
  compiles in **966 µs** with the memo builder vs 36,743 µs for the current builder on the
  same object graph.
- Size: v1 195,574 B → v2 1,550 B (ladder d10); 395,448 B → 5,782 B (mult nb7 bit7).
  Public circuit cones are representable without expansion.

**Not done, and why:** EPFL/AIGER cones. Downloading external benchmark files requires
Brian's approval under this session's rules. The adapter itself is small (AIGER ASCII
`.aag` → v2 defs is mechanical: AND gates + inverter edges → `and`/`not` nodes). When
approved, record suite commit hash and per-cone identifiers (e.g. EPFL `arithmetic/mult`
output index) plus the cone-extraction transform. Until then the multiplier/adder/ladder
generators are the sharing-heavy stand-ins, with the caveat that they are self-built.

---

## Q4. Variance estimator

Independent recomputation (own code, not Codex's; `variance` section):

| quantity | local | pod |
|---|---:|---:|
| pooled within-cell σ of per-formula median log-ratio, df=10 | **0.1190** | **0.0935** |
| reproduction of the analysis's value: √(SS/21) | 0.0821 | 0.0645 |
| 95% CI on σ (χ², df=10) | [0.083, 0.209] | [0.065, 0.164] |
| moment-corrected latent σ (timing noise subtracted) | 0.0999 | 0.0930 |
| regression-on-live_k residual σ (df=19, uses singletons) | 0.1475 | 0.2172 |
| regression slope per live_k unit | −0.044 | −0.153 |

- The analysis's 0.065/0.084 are **exactly** the df-correct σ times √(10/21): residual sum
  of squares divided by all 21 formulas, i.e. singleton cells and the 11 estimated cell
  means treated as free information. Codex's derivation claim is verified to the digit
  (local reproduces 0.0821 vs the analysis's published 0.084; the 2% remainder is a
  mean-vs-median aggregation detail, not a different formula).
- Correct residual df is **10**: cells {2:2, 4:2, 5:6, 6:2, 8:2, 9:2} contribute
  16 formulas − 6 cell means. Five singleton cells contribute nothing to a within-cell
  estimate. The only way to use them is a trend model; doing so gives *larger* σ because
  the live_k trend is strong (pod slope −0.153/live_k) and visibly nonlinear, so 0.15–0.22
  is an upper bound, not an alternative estimate.
- Timing variance should *not* be subtracted for planning: the correction is negligible
  (0.119 → 0.100, 0.0935 → 0.0930) because within-formula round noise is small relative to
  between-formula spread; and a future study's estimator dispersion includes that noise
  anyway unless it uses many more rounds.
- σ itself is highly uncertain at df=10 — note the pod CI's lower edge (0.065) *is* the
  biased value, which explains how an optimistic reading felt plausible.
- Defensible sample sizes (two-sided α=.05, power .80, per-formula median as unit,
  n = ((1.96+0.84)σ/log(1+δ))² + small-sample correction), planning range σ=0.09–0.15:

| effect | σ=0.09 | σ=0.10 | σ=0.12 | σ=0.15 |
|---:|---:|---:|---:|---:|
| 3% | 75 | 92 | 132 | 205 |
| 5% | 29 | 35 | 50 | 77 |
| 8% | 13 | 16 | 22 | 32 |

- Transfer caveat (both audits already agree; re-affirmed): all of this is estimated on
  sparse depth-4 mixed-operator formulas. Nothing licenses transfer to XOR chains or
  circuit cones; treat these as planning priors for a pilot, not as population truth.

---

## Q5. Repeat count and platform interaction

**From archived data only** (`repeat_platform.archived`):

- Pod/local geomean gap 1.3901 over 42 joined formulas — the analysis's 1.390 reproduces.
- Repeat-group split reproduces Codex (repeat-50 group 1.10, repeat-200 group 1.50) —
  **and is fully explained as a confound**: repeat is assigned by measured speed
  (`v4audit_packed_eval_2026_07_24.py:75`), so the repeat-50 group is the slow formulas
  (mean local BitSet 50.6 µs vs 17.0 µs). The gap declines smoothly in live_k
  (2.67 → 1.01 from k=1 to k=16) and correlates −0.86 with log local BitSet time.
- Combined with Codex's same-formula rerun (repeat 200/50 geomean 0.994 locally), the
  attribution is: **repeat count contributes ≈0 of the 1.390 gap on the local side**; the
  gap carries a fixed-overhead-per-call signature that vanishes as kernels grow. Whether
  the pod side has any repeat sensitivity **cannot be identified from existing data** —
  every pod row is repeat 200. Only E8's pod gate can close that, and pod-to-pod variance
  remains unmeasured (F4's honest residual).

**New schedule control** (formula identity, live_k, operator mix, order alternation and
warm caches all held fixed; 13 formulas, one per live_k):

- Blocked geomean ratio 0.936 vs fully interleaved 0.956 — a ~2% paired effect; largest
  per-formula movement ~13%, most under 5%.
- The analysis's "pooled ratio moves 27%" is therefore a **pooling artifact** (mixture
  reweighting), not a per-formula schedule sensitivity. Its own correction (shared cache,
  attribution open) is now closed: interleaving 13 supports through the 4-entry
  `_WORDS_ENV_CACHE` yields a measured 50% miss rate (800/800) vs ~0.1% blocked (8
  misses), at ~138 µs per k=16 words-env rebuild — an additive overhead paid by *both*
  arms, which compresses pooled ratios toward 1 without changing paired ones much.
- Publication consequence downgraded accordingly: results should carry a schedule label,
  but blocked-vs-interleaved is not a threat to the published ratios' sign at any stratum
  tested here.

---

## Q6. The BDD argument

**Measured facts** (`bdd` section; `dd.autoref`, pure Python — build *times* are upper
bounds, node counts are exact and backend-independent):

- **Exact maximum ROBDD size** (min over level widths, terminals included): n=8 → 79,
  n=12 → 767, **n=16 → 8447**, n=20 → 131,071. The analysis's "~4096 at n=16" substituted
  the asymptote `2^n/n` for an exact bound — off by 2.06×. Codex's measured 4419-node
  8×8 output bit therefore contradicts the analysis's number while sitting comfortably
  inside the true bound; nobody's theorem was violated, one document's arithmetic was.
- **Adder order sensitivity is analytic and reproduces exactly**: m=8: 511 blocked / 24
  interleaved; m=10: 2047 / 30 (= `2^(m+1)−1` and `3m`).
- **Sifting beats both fixed orders on every hard multiplier bit tested** (nb=8):
  bit 7: 1025/777/**508**; bit 9: 3013/3537/**1432**; bit 10: 3560/4419/**1586**;
  bit 11: 3255/3872/**1593** (blocked/interleaved/after-sifting; autoref reorder cost
  0.18–0.63 s). Consequences: (a) Codex's node-count corrections reproduce; (b) any CM-vs-BDD
  order statement that omits dynamic reordering is against a strawman — this includes E7's
  design unless sifting is a mandatory arm (the analysis already conceded this).
- **Task-matched pipelines** at the CM-admissible edge (n=16, 8×8 central bit) and n=12:

| task (n=16) | CM | BDD (autoref) | binary-CSE flat |
|---|---:|---:|---:|
| equivalence of two topologies, end-to-end | 353 ms (350 compile + 2.5 eval) | 348 ms (build) + 3.5 µs compare | **≈2 ms** |
| model count after prep | 4 µs | 2.6 ms | 4 µs |
| 32-restriction batch → counts | 10.3 ms | 10.5 ms | ~5 ms (est.) |
| full packed table (n=12) | 0.14 ms | 9.3 ms extract + 19 ms build | 0.1 ms |

  All cross-checked bit-exact (equivalence verdicts, counts, restriction counts, packed
  extraction).

**Verdicts on the two prior positions:**

- The analysis's F7 ("BDD blowup provably impossible inside the admissible region, retire
  BDD-hard families") — the *node-count* premise was numerically wrong and the nodes-vs-bits
  comparison dimensionally sloppy, as Codex said. But its practical core survives this
  audit: at live_k ≤ 16 no tested pipeline produced a BDD-over-packed win, and the packed
  side wins output-shaped tasks by 10–100×.
- Codex's A5 ("pipelines may favor a BDD; retain P6") — directionally supported for
  restriction/composition-heavy workloads: parity against pure-Python autoref implies a
  likely CUDD win there; equivalence via canonicity is free *after* build but the build
  dominates and ties CM.
- **Neither document flagged the real headline: the strong baseline wins the pipelines.**
  Binary-CSE preparation is so cheap that "compile + packed evaluate + compare" beats both
  symbolic contenders by ~two orders of magnitude at n=16 for equivalence and output tasks.

**Priority 6 disposition: split three ways.** (1) Retire "BDD-hard families as a
CM-favorable stress test" — confirmed dead. (2) Keep order-sensitivity work (E7) with
sifting mandatory. (3) Add a narrow "restriction/composition closure" leg where the BDD
side is genuinely promising and CM currently has no counterpart story — pod CUDD, small.

---

## Q7. Existing measurement defects — confirm/refute

| claim | verdict | evidence |
|---|---|---|
| Validation contaminates CUDD order-search/all-in timing | **Confirmed** | `robdd_dd.py:397-471`: `search_started` precedes the sweep loop; `validate_dd_bdd_correctness` (`:420-428`) runs inside every trial; `search_time` (`:471`) and `trial_total_time` (`:447`) include it |
| Isolated CUDD build fields remain valid | **Confirmed** | `build_time` measured at `:410-412` around `expr_to_dd_bdd` only |
| `self_xor_false` is degenerate | **Confirmed** | `v4audit_query_workloads_2026_07_24.py:69-76`: `apply("xor", root, root)` is an ITE-cache identity; measures dispatch, not equivalence |
| CM wrapper overhead mixed into kernel timing | **Confirmed and quantified** | on the controlled formulas the harness arm (`materialize_hybrid_no_reinflate`) vs kernel: live_k=8: 28.4 vs 7.3 µs; k=12: 69.7 vs 14.4 µs; k=16: 144.6 vs 76.7 µs. Kernel ratios are **0.73/0.81/0.77 (CM faster)** while harness ratios are 2.83/3.90/1.44 on this box — the published C1 comparison is wrapper-vs-kernel-shaped, and at low k it is mostly wrapper |
| Blocked scheduling materially affects published ratios | **Refuted as material** | paired effect ~2% geomean (§Q5); the 27% figure was a pooling artifact |
| Refusal above the guard must be reported as an outcome | **Confirmed** | harness writes `skip_guard_gt16` rows before timing (`v4audit_packed_eval_2026_07_24.py:43-50`); survivorship framing stands |

**Additional defects found this session (not in either prior document):**

1. `len(prog.ops)` vs executed word-ops (§Q1) — affects every published op-count claim.
2. Share-blind associative flattening duplicates work (§Q1) — a *code* defect
   (`cm_ir.py:516-532`), not just a measurement one.
3. Codex's `dag_nodes` is identity-based and overcounts the semantic DAG ~37% on
   multipliers (251 identity vs 183 structural) because each partial product constructs
   fresh `Var` objects; any "compile is DAG-proportional" scaling fit against it inherits
   the bias.
4. Codex's CSE baseline carries O(subtree)-hash nested-tuple keys (19× prep penalty
   measured); their pilot never reported CSE prep time at all.
5. The analysis's wrapper-decomposition framing ("both arms call the identical
   `_eval_words`") understated its own E3 point: the CM arm's admission wrapper is not a
   constant tax; it flips the sign of the comparison at k=8–16 on this box.

---

## Verdicts, confidence, and re-ranking

### F1–F8 (analysis findings, after both reviews)

| finding | verdict | confidence | note |
|---|---|---|---|
| F1 corpus/inferential unit | CONFIRMED-WITH-CORRECTION | high | unit=1 per controlled stratum stands; σ values corrected upward (0.094–0.119, wide CI); sample sizes ~2× the analysis's |
| F2 published win = associative flattening on XOR corpus | CONFIRMED-WITH-CORRECTION | high | mechanism right for the corpus; but op-count framing is an artifact, and on shared inputs flattening *hurts* |
| F3 compile is tree-bound, memo "does not work" | CONFIRMED-WITH-CORRECTION | high | tree-bound: yes. Memo verdict: works (31–36×), leaves 5–10× in deep keys; repo's persistent path already ≈ memo |
| F4 platform interaction, fixed-overhead mechanism | CONFIRMED-WITH-CORRECTION | moderate | gap −0.86-correlated with kernel cost; repeat exonerated; pod-side identifiability and pod-to-pod variance still open |
| F5 blocked schedule inflates ratios | REFUTED as material | high | paired effect ~2%; the 27% was pooled-mixture reweighting; mechanism (shared env-cache misses) now measured |
| F6 survivorship conditioning | CONFIRMED | high | unchanged; budget-probe retraction stands |
| F7 BDD blowup impossible in admissible region | REFUTED as stated / core practical claim survives | high | exact n=16 bound is 8447 not 4096; nodes≠bytes≠runtime; but no BDD-over-packed win exists at live_k≤16 in any tested pipeline |
| F8 CUDD search-time contamination | CONFIRMED | high | line-level confirmation |

### The Codex audit's own three headline corrections

| Codex claim | verdict | note |
|---|---|---|
| A2: 128× is baseline weakness, CSE closes it | CONFIRMED, extended | missing rung closes to op-for-op identity; executed-op accounting makes CM *slower* than binary CSE |
| A1/A3: staged repair, memo first, keys "only if warranted" | CONFIRMED-WITH-CORRECTION | keys are warranted now (5–10×); memo prototype has a lifetime bug; repo's persistent builder should be step 0 |
| A5: retain P6, pipelines may favor BDD | CONFIRMED-WITH-CORRECTION | retain only the order-sensitivity + restriction-closure halves; the packed-output half is settled against the BDD; the *strong baseline* wins most pipelines |

### Re-ranked E1–E10 (my ranking, independent of both authors)

1. **E2′ — finish the fair-compiler question on independent inputs.** The two local rungs
   are now closed; what remains is AIGER/EPFL cones (needs download approval) and the
   sharing-aware-flattening variant. Highest belief-change per hour remaining.
2. **E1′ — staged compile repair, re-scoped:** (0) benchmark/harden the existing
   persistent builder; (1) per-call-scoped identity memo with lifetime-safe keys;
   (2) v2 defs/ref serde (built here, ~1 day to productionize); (3) compact intern-ID
   keys (justified now, biggest single win); (4) sharing-aware flattening (also fixes
   the eval regression).
3. **E3 — formula-clustered, operator-crossed replication with kernel/wrapper split.**
   Now doubly required: the wrapper-vs-kernel sign flip means the published C1 sentence is
   not merely under-powered, its arm definition decides its sign.
4. **E4 — amortization crossover**, now three-arm (CM / binary-CSE / BitSet-raw): the
   CSE arm's ~1000× prep advantage changes every break-even count.
5. **E10 — CUDD metric repairs** (unchanged, small, prerequisite to reusing any CUDD number).
6. **E9 — feasibility frontier + a new restriction-closure leg** (the one place a real
   BDD win is plausible; needs pod CUDD).
7. **E7 — order dispersion, sifting mandatory** (this session already provides the fixed-
   order and sifting scaffolding).
8. **E8 — pod replication gate** (unchanged; only source of pod-side repeat/variance answers).
9. **E5 — schedule** — demoted to a labeling requirement; the science question is closed.
10. **E6 — compiled executor 2×2** — still useful as an engineering ceiling; run after the
    fair-compiler dust settles so it factorizes over the right programs.

---

## Tests that should enter the project

1. **Executed-op accounting test**: `expanded_word_ops`-style counter asserted against
   `_eval_words` instrumentation; any published "ops" column must state which count it is.
2. **Fair-baseline equality test**: raw / CSE / CSE+flatten / CM programs bit-identical on
   property-generated expressions including planted-cancellation families (catches
   semantic-rewrite regressions in all four).
3. **Builder sharing regression**: shared-DAG compile must visit ≤ identity-DAG nodes
   (visits counter), with a lifetime test that builds two expressions through one builder
   and forces GC between them (guards the id-reuse hazard).
4. **Serde v2 tests**: sharing preservation, forward/dangling/self-ref rejection, v1
   passthrough, size regression bound.
5. **Statistics guards**: summaries must report distinct-expression counts and residual df;
   reject variance estimates whose denominator exceeds residual df.
6. **Timing-boundary test**: CUDD validation duration emitted separately; build/search
   fields asserted validation-free.
7. **Schedule/provenance metadata**: every benchmark row records schedule policy, repeat,
   cache state, interpreter, CPU model, and git SHA.

## Optimizations, in dependency order

1. Benchmark and harden `compile_expr_to_cm_ir_persistent` as the default compile path for
   benchmark harnesses (exists today; zero new code).
2. Per-call identity memo in `CMIRBuilder.build` with lifetime-safe keys (small,
   independent; supersedes nothing).
3. Land v2 defs/ref serde + AIGER adapter (unlocks circuits end-to-end).
4. Compact intern-ID node keys (measured 5–10× beyond the memo; requires
   canonicalization-order tests first — the compact prototype here is the semantics spec).
5. Sharing-aware associative flattening (splice only single-consumer children) — fixes the
   2× executed-op regression on shared inputs while keeping canonical form.
6. Add binary structural CSE (intern-ID keys) to the BitSet side as the production strong
   baseline; keep `compile_expr_flat` only as a labeled ablation.

## Claims that should not be relied on

- Any op-count or "program compression" figure based on `len(prog.ops)` (all documents).
- "CM is modestly faster at controlled live_k 12/16" — arm-definition-dependent sign
  (kernel vs harness wrapper), single formula, σ underestimated.
- The 27% schedule effect (pooling artifact).
- "CSE runs 1.6–1.8× faster than CM for unexplained wrapper/program reasons" — explained;
  use the executed-op account instead.
- "~4096 max ROBDD nodes at n=16" (exact bound 8447) and any nodes-vs-bits size ratio.
- "An identity memo does not fix compile" *and* "identity memo now, keys later, maybe" —
  both stale; see staged plan above.
- The 0.065/0.084 sigmas and any sample size derived from them.
- Codex's `dag_nodes` values as semantic DAG sizes (identity-based, ~37% high on
  multipliers).

## Claims that now have adequate evidence

- The controlled strata contain one distinct formula each; sample sizes above are the
  planning numbers (σ 0.09–0.15, df-correct, CI'd).
- CM compile is Θ(tree unfolding) on the current default path; DAG-proportional compile is
  achievable (memo/persistent/compact all demonstrated bit-exact).
- CM's compiled multiplier programs are executed-op-identical to CSE+flatten; binary CSE
  beats both in steady state on shared inputs; CM's surviving distinctive capability is
  local semantic rewriting.
- Repeat count does not explain the pod/local gap on the local side; the gap has a
  fixed-overhead signature declining from 2.67× (k=1) to 1.01× (k=16).
- Sifting dominates both fixed multiplier orders at nb=8; packed evaluation wins
  output-shaped tasks at live_k ≤ 16 by 10–100×; restriction batches are the one BDD-
  promising workload.
- Validation contaminates CUDD search timing; isolated build fields are clean.

## Work-category separation

- **Scientific benchmark work**: E2′ on external cones; E3 replication; E4 three-arm
  crossover; E9 frontier + restriction closure; E8 pod gate.
- **Correctness/regression testing**: the seven tests above; the builder-lifetime test is
  the only one guarding a *current* latent hazard (in a scratch prototype, but one Codex
  recommended promoting).
- **Production optimization**: the six-step sequence above; steps 1–2 are safe now, steps
  4–5 need the canonicalization test suite first.
- **Publication/provenance work**: schedule/provenance sidecars, refusal-as-outcome
  reporting, CUDD field repairs, corpus commit authorization, EPFL download approval.

## Execution notes and self-corrections

- No pod, no commit, no push, no historical file edited; new artifacts only under
  `deliverables_n22_24/` with `deep_followup_2026_08_02` names.
- Skipped: full test suite (nothing production-touched; 18 targeted tests pass), EPFL
  download (needs approval), pod-side repeat identification (impossible from data).
- Timing caveats: single Windows box, min-of-blocks; harness-arm absolute overheads here
  (e.g. 21–68 µs wrapper) are larger than the published local run implies — cross-box
  levels are not comparable, contrasts and sign structure are the evidence.
- One negative worth keeping: the arm-shape asymmetry I suspected in Codex's CSE-vs-CM
  *eval* comparison (`eval_cm_node_words` vs bare `_eval_words`) measured as noise-level;
  their eval arms were fair. The unfairness was in the op-count semantics and the missing
  prep column, not the call shape.
