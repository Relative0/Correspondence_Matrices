# Benchmark Gap Analysis: What Should CM Be Tested Against Next?

Date: 2026-08-01
Repo state: `main` = `b6ce6b2`, worktree clean (untracked kickoff `.md` files only, unmodified).
Benchmark interpreter: `.\.venv\Scripts\python.exe` 3.13.5, numpy 2.3.2, dd 0.6.0.
Supersedes and reprioritizes `CM_REMAINING_TESTS_AND_RESEARCH_PRIORITIES_2026-07-25.md`.

No campaign was launched. No pod was started. No tracked file was modified, no historical CSV
overwritten, no report edited. Everything labelled "measured" was produced by read-only
scouting this session and is reproducible (Appendix B).

---

## Headline

The existing roadmap treats the corpus as a **statistical** weakness — too few formulas per
stratum. That is true, and it is the smaller half of the problem.

Two larger things are wrong, and both were found by probing rather than reading:

**1. The corpus selects against the regime where CM is strong.** On formulas with real
subexpression sharing, CM's compiler is not 5% better than the published baseline — it is two
orders of magnitude better. Measured on an 8×8 multiplier middle output bit (`k`=16, exact
packed equality asserted against the BitSet control):

| formula | CM flat ops | raw-AST flat ops | CM eval | BitSet eval | ratio |
|---|---:|---:|---:|---:|---:|
| XOR chain, k=16 (= corpus `controlled_live_16`) | 1 | 15 | 28.5 µs | 37.2 µs | 0.768 |
| multiplier middle bit, k=16 | 109 | 26,157 | 409 µs | 52,571 µs | **0.008** |
| XOR chain, k=12 | 1 | 11 | 11.4 µs | 15.4 µs | 0.740 |
| multiplier middle bit, k=12 | 49 | 759 | 107 µs | 939 µs | 0.114 |

The 240× program compression survives a full JSON round-trip, so CM's hash-consing is
**structural/content-addressed, not `id()`-based**. It is a real capability. Every corpus
formula is a depth-≤4 random tree (negligible sharing) or a chain (zero sharing), so the
capability is invisible in 100% of published results.

**2. But CM's compile cost is governed by the tree unfolding, not by the DAG — and not by
`live_k` at all.** `CMIRBuilder.build` (`cm_ir.py:806-824`) is a plain recursion with **no
memo**; it re-walks every node of the unfolded tree. Measured on multiplier output bits:

| formula | DAG nodes | tree unfolding | unfold factor | CM compile | resulting CM ops |
|---|---:|---:|---:|---:|---:|
| 4×4 mult, bit 5 | 64 | 1,099 | 17× | 4.1 ms | 37 |
| 5×5 mult, bit 6 | 104 | 6,887 | 66× | 27.1 ms | 64 |
| 6×6 mult, bit 6 | 121 | 8,627 | 71× | 32.4 ms | 74 |
| 6×6 mult, bit 7 | 152 | 43,251 | **285×** | **164.6 ms** | 97 |

Compile time is dead linear in tree nodes (~3.8 µs/node) while the DAG barely moves. CM spends
164 ms to discover a 97-operation program it then evaluates in microseconds.

**These two findings pull in opposite directions, and that tension is the real research
question.** CM's *evaluation* is DAG-proportional and excellent; CM's *compilation* is
tree-proportional and can be five orders of magnitude more expensive than the evaluation it
enables. Neither is visible on a corpus of shallow trees and chains.

**The single sharpest attack on the thesis:** the published baseline `compile_expr_flat`
(`bitset_backend.py:465-494`) has *no memo table at all*. CM's 128× advantage above may be
nothing more than "CM performs common subexpression elimination and the baseline is denied
it." A hash-consed baseline is the control that decides this, and it is cheap. Ranked **E2**.

---

## Part 0 — The kickoff's seed hypotheses, checked

| seed hypothesis | verdict |
|---|---|
| "Corpus is the binding limitation… inferential unit is 7, not 49" | **Confirmed and worse.** 31 distinct expressions across 49 records; each controlled stratum is **1** distinct formula (`sha d5b65d38ee9c`, seed 0) re-bound into 7 ambient sizes. Inferential unit is **1**. |
| "median `live_k` about 5" | **Partly wrong.** Corpus median is **9**; 5 is the `sparse_depth4` sub-family only. |
| "XOR-dominated" | **Confirmed.** 431 of 555 operator instances (77.7%); 82.3% of binary ops. All four non-sparse families are 100% XOR. |
| "BDD-hard and order-sensitive families entirely absent" | **Confirmed, but the motivation is a category error.** See F7: inside CM's admissible region BDD blowup is *provably impossible*. Order sensitivity is the live half. |
| "CUDD measured only at construction" | **Confirmed**; CUDD build is 20–80 µs, the same order as CM/BitSet packed eval (6–24 µs). |
| "extraction is wrong axis, query workloads are right" | **Half wrong.** Single-op query is also losing: packed answer is a table lookup vs ~30 µs for an existing `dd.autoref` point query. The right framing is *operation closure*, and even that is bounded by F7. |
| "Non-BDD baselines never benchmarked" | **Confirmed as never benchmarked**; cause misdiagnosed. Adapters exist. numba is **not** confined to 3.10: `pip install --dry-run` in `.venv` resolves `numba-0.66.0-cp313` + `llvmlite-0.48.0-cp313`, no source build. `pysat` 1.8 already installed. |
| "Explicit output may be the wrong contract" | **Wrong diagnosis.** At `live_k`≥6 both published arms call the *identical* `_eval_words`; they differ only in which `FlatProgram` is handed to it. The contract is fine; the baseline's *compiler* is the issue. |
| "Unexplained local/remote discrepancy" | **Confirmed and explained** — a fixed-overhead × platform interaction (F4). |
| "Statistics need clustering" | **Confirmed and sized:** 17–77 distinct formulas per stratum depending on the true between-formula σ. |

Two hypotheses I add, both measured: (a) the corpus selects against CM's real strength;
(b) CM's cost model is not a function of `live_k` (F3), which is the variable organizing every
published result.

---

## Part 1 — What the current evidence actually establishes

### F1. The controlled strata contain one formula each

49 records, **31 distinct expressions**. `controlled_live_8/12/16` are each one left-associated
XOR chain, seed 0, one SHA, re-bound into 7 ambient `n`.
`CM_v4audit_packed_eval_summary_runpod.csv` reports `formulas=7`;
`v4audit_packed_eval_2026_07_24.py:103` computes `len({r["id"] for r in sel})` and ids are
`{family}-n{n}-i{idx}-{sha12}`, so the seven ids differ only in the ambient-`n` token while
sharing one SHA. The column is arithmetically correct as an id count and is **wrong by a factor
of 7** as a sample size.

The pod's tight `p10–p90` `[1.318, 1.343]` is *within-formula* timing precision. Variance
decomposition over both raw CSVs:

- between-formula σ(log ratio): **0.065** (pod) / 0.084 (local)
- within-formula σ: 0.045 (pod) / 0.167 (local)
- at `live_k`=5 (6 distinct formulas) per-formula means span 2.759 → 3.638, a **1.32× spread
  inside one stratum**
- observed pairwise spread at `live_k`=8 between two distinct formulas: 1.169 vs 1.508 (**29%**)

Sample size (one-sample on per-formula mean log-ratio, α=.05, power .80):

| effect | σ_b=0.065 | 0.10 | 0.15 | 0.25 |
|---:|---:|---:|---:|---:|
| 3% | 42 | 93 | 206 | 565 |
| **5%** | **17** | 36 | 77 | 209 |
| 8% | 8 | 16 | 32 | 85 |

Claimed effects are 5.6% (`live_k`=16) and 9.1% (`live_k`=12, pod). Formulas present: **1**.
At N=40 with σ_b=0.10 the `live_k`=16 interval widens 3.1× to [0.915, 0.974]; at σ_b=0.15
— plausible once operators vary — both strata cross 1.0.

**Do not spend replicates on ambient `n`.** Across-ambient-`n` σ inside each controlled stratum
is 0.009–0.017, *smaller than* the round-to-round timing σ of 0.021–0.030. The corpus spent all
7 replicate slots on the factor with the least variance and 0 on formula identity, the factor
with the most. Convert that budget 1:1 into distinct formulas.

### F2. The published win is associative flattening, on the operator where the baseline is weakest

`cm_ir.py:31` `ASSOCIATIVE_OPS = {"AND","OR","XOR"}`. Verified flat-program step counts:

| chain operator, k=16 | CM ops | BitSet ops |
|---|---:|---:|
| XOR / AND / OR | **1** | 15 |
| IMP / EQV | 15 | 15 |

The corpus is 82% XOR by binary-operator count. On IMP/EQV the two programs are structurally
identical and CM can only lose, by its wrapper cost.

Uncontrolled factors measured at **fixed** `k`=16, fixed 31 AST nodes, fixed support — each
larger than the 5.6% effect being reported:

| factor varied | ratio swing |
|---|---|
| operator (xor 1.456 → and 1.560 → or 1.568 → imp 1.687 → eqv 1.895) | **30%** |
| association shape (left chain vs balanced) | 8–12% |
| subexpression redundancy added | ratio → **0.44–0.56** (CM 2× *faster*) |

(Absolute levels differ from the pod — a slower, blocked-schedule local box — so only the
contrasts are evidence. Direction is consistent at k=8, 12, 16.)

### F3. CM's cost is not governed by semantic live support

The headline finding above. `CMIRBuilder.build` has no memo (`cm_ir.py:806-824`), so compile is
Θ(tree unfolding). Materialization *is* memoized (`cm_ir.py:1211`, keyed by
`(CMNode, fixed_key, allow_collapse)`), so evaluation is DAG-proportional. The defect is
precisely and only in `build`.

This falsifies the cost model that organizes every published number: the `live_k` stratification
of `CM_v4audit_packed_eval_summary_runpod.csv` measures an incidental property of *tree-shaped
random formulas*. On any input with reconvergent fanout — i.e. any real circuit — `live_k`
predicts nothing about CM's cost.

**The obvious fix does not work, and this was measured.** Adding an id-keyed memo to `build`
does not restore DAG-proportionality: `self._interned` is keyed by deep nested tuples
(`key = ("IMP", left.key, right.key)`, `cm_ir.py:796`) which Python re-hashes structurally on
every lookup — `hash(root.key)` alone moved 0.018 ms → 2.43 ms across a 2× DAG rise — and
`cm_ir.py:527/670/744` sort commutative args by those same deep keys. The real fix is a
key-representation change with canonicalization-semantics risk.

A hard prerequisite for testing any of this: `cm_expr_serde.expr_to_json` is tree-recursive with
no ref/defs mechanism, so **the frozen-corpus format cannot represent a circuit at all**.

### F4. The local/pod discrepancy is a systematic platform interaction

Per-formula medians, 42 formulas, both raw CSVs:

- pod ratio / local ratio, geometric mean **1.390** — CM looks 39% worse on the pod
- **11 of 42 formulas sign-flip**
- mechanism: the pod is faster for both backends but unequally — at `live_k`=1–5 BitSet gains
  **4–5×** from the pod while CM gains only **~2×**; by `live_k`=16 both gain ~0.37 and the
  ratios converge (0.944 pod vs 0.925 local)
- the interaction is itself a function of `live_k`, and at `live_k`=12 the two machines land on
  **opposite sides of parity** (local 0.948 CM-faster, pod 1.091 CM-slower)

**Execution-order bias is ruled out** using existing data (`rnd % 2` alternation,
`v4audit_packed_eval_2026_07_24.py:76-82`): <1% pod, <5% local. Dead direction, useful negative.
Design nit worth fixing regardless: `ROUNDS=7` with `rnd % 2` gives an unbalanced 4:3 order
split, so the reported median sits in the majority arm.

**Unmeasured and load-bearing: pod-to-pod variance.** `CM_v4fix_runpod_audit.json` records only
`cpu_flavor cpu3c` / `vcpu_count 4`, no CPU model or cgroup quota, while
`cm_runpod_deploy.py:170-182` requests `vcpuCount 2`. Nothing establishes that two "cpu3c" pods
are the same silicon.

### F5. The headline runs a blocked schedule that maximizes cache hits

`bitset_backend.py:562` `_WORDS_ENV_CACHE_MAX = 4`; `:563` `_WORDS_SCRATCH_WIDTHS_MAX = 2`. The
harness evaluates one formula 200× back-to-back — a guaranteed 100% hit rate. Probe: pooled
ratio moves **2.866 → 2.085 (27%)** under round-robin interleaving.

*Correction to the probing agent's mechanism claim:* the proposed explanation ("BitSet leans on
the env cache harder than CM") does not hold — the env cache is **shared**; CM's words path
routes through the same `_eval_words`. The 27% movement is real; its attribution is open. No
published ratio carries a schedule label.

### F6. The comparison is conditioned on survival

The corpus marks 42 records `run` and **7** `skip_guard_gt16` — the entire `actual_all_live_xor`
family, `live_k` 20–32, i.e. the hardest cases. `v4audit_packed_eval_2026_07_24.py:44-50` writes
them out as blank rows *before* timing. `CM_v4audit_symbolic_build_raw_runpod.csv` shows CUDD
building **all 49/49**, `cudd_status=ok`, in 20–80 µs — including the 7 CM refuses. The published
ratio is survivorship-conditioned and the survival rate is exactly what the output contract
determines. Refusal has never been an outcome variable.

The guard is a parameter, not a wall: `hybrid_threshold` and `max_full_output_vars` are keyword
arguments (`v4audit_packed_eval_2026_07_24.py:60-63`); raising them works unmodified and packed
equality held at `k`=16, 18, **20**. `k`=22 raises `OutputBudgetExceeded (max_output_bytes=262144)`
— a second parameter. Single-shot at `k`=20: xor ratio 1.283, imp ratio 0.646 — a large
operator × `live_k` interaction at the edge of the censored region.

*A claim I withdraw:* an earlier probe appeared to show `output_budget.py`'s temporary-bytes
model was 2.7× optimistic (unsafe). Adversarial review found the probe called
`estimate_explicit_output` **without** `operation_slots`, i.e. it compared reality against an
estimate the system never computes. The finding is retracted; budget calibration is not
currently evidenced as a defect.

### F7. Inside CM's admissible region, BDD blowup is provably impossible

The maximum ROBDD size over `n` variables is `(1+o(1))·2ⁿ/n` — at `n`=16, ~4096 nodes; at
`n`=20, ~52k. CM's explicit artifact at `live_k`=16 is 2¹⁶ bits. So wherever CM produces an
artifact at all, the BDD is *provably smaller than the truth table CM must build*, by a factor
of ~`k`. Confirmed on the canonical hard instance: the 8×8 multiplier middle bit is **1025 BDD
nodes** (777 interleaved), built in 68 ms by pure-Python `dd.autoref` (CUDD is typically 10–50×
faster).

Worse for the thesis: across the multiplier family the BDD grows ~2.3× per +2 variables while
CM's 2^k grows 4×. **CM's cost grows faster than the BDD's on the family chosen precisely
because BDDs blow up on it.** Adding multipliers or HWB to the corpus at `live_k`≤16 will not
produce a CM-vs-BDD win; it produces a CM loss with extra steps.

**The live half is order sensitivity**, and it is sharp. Ripple-carry adder carry-out, function
held fixed, only the labelling permuted (verified this session):

| m | n | blocked nodes | interleaved nodes | ratio |
|---:|---:|---:|---:|---:|
| 10 | 20 | 2,047 | 30 | **68×** |

Blocked is exactly `2^(m+1)−1`, interleaved exactly `3m`. **CM on the identical pair moved
1.78×** — ~15× less order-sensitive than a fixed-order BDD, but *not invariant*. The residual is
unexplained; candidate mechanism is `align_to_vars` (`cm_ir.py:968-993`) inserting transposes.

### F8. The CUDD order-search column is contaminated by in-band validation

I initially attributed the ~64–103 ms `cudd_best10_order_search_us` to manager churn. That was
wrong. It is `validate_dd_bdd_correctness` running **inside** the timed trial region:
`robdd_dd.py:398` starts the clock, `:420-428` validates, `:447` closes;
`v4audit_symbolic_build_2026_07_24.py:46-63` passes `correctness_samples=64` to all five calls.
Per trial: build 15.7–63.5 µs, order generation ~24 µs, **unaccounted ~6,300–6,900 µs** ≈ 64 ×
~100 µs, flat in `nominal_n` and in AST depth.

Every statement derived from `cudd_best10_*_search_us` is inflated by ~two orders of magnitude.
The attribution on `dd.cudd` specifically is still not fully settled: the disproof of "manager
churn" was measured on `dd.autoref`, where a manager is a Python dict.
Separately, `self_xor_false` (`v4audit_query_workloads_2026_07_24.py:69`) is a degenerate
ITE-cache hit and measures nothing.

---

## Part 2 — Ranked experiments

Ranked by **expected change in belief per unit cost**, with a hard preference for designs whose
*negative* result is as informative as the positive. Rank ≠ run order; see Part 5.

---

### E1 — Does CM's cost model survive circuit-shaped (DAG) inputs?

**Rank 1.**

**Question.** Does CM's total cost scale with the input's DAG size — as "cost is governed by
semantic live support" requires — or with the exponentially larger tree unfolding?

**Hypothesis (falsifiable).** H0: CM total time is Θ(DAG nodes) and independent of unfolding
factor. **Already contradicted** by F3 (compile is linear in tree nodes at ~3.8 µs/node across a
17×→285× unfolding sweep while the DAG moves 64→152). The experiment converts a probe into a
measured scaling law across circuit families, and — the part that is genuinely open —
establishes whether it is *fixable*.

**Why not covered.** `cm_ir.py:806-824` `build` has no memo; the precedent exists 300 lines up
at `cm_ir.py:160` (`_structural_digest` carries an id-keyed memo). Every published stratum is
tree-shaped random formulas, where unfolding factor ≈ 1, so the defect cannot appear. No repo
artifact separates compile from evaluation as a function of sharing.

**Design.**
- *Corpus:* circuit-derived DAGs with controlled unfolding factor 1→300×: multiplier output
  bits, ripple/carry-select adders, ISCAS-style cones, reconvergent-fanout ladders. Stratify by
  measured unfolding factor (`tree nodes / DAG nodes`), not family.
- *Arms:* (a) CM compile, (b) CM materialize, (c) BitSet prepare, (d) BitSet eval — all four
  timed separately, never summed into one ratio. Plus a post-fix arm if a key-representation
  change is attempted.
- *Timing boundary:* compile and evaluate reported as separate columns; total cost reported as a
  function of evaluation count.
- *Unit:* distinct circuit, clustered. *Sample:* 40 circuits across 5 unfolding deciles.

**Success interpretation.** If CM tracks the DAG once a fix lands, CM earns a legitimate and
genuinely distinctive claim — cost `2^live_k` independent of circuit depth, which a BDD cannot
claim. That would be the strongest positive result available to the project.

**Failure interpretation.** If CM tracks the unfolding (the current evidence), then the cost
model is wrong for every real circuit workload, `live_k` stratification measures an artifact of
tree-shaped random generation, and CM cannot be applied to EDA-style inputs without a compiler
change. That is a concrete, actionable P0 engineering finding *and* it invalidates the
organizing variable of the published results.

**Cost.** Local for CM/BitSet (~2–3 h). Implementation is the real cost and is **larger than it
looks**: a DAG-aware serde (`expr_to_json` is tree-recursive — hard blocker), a circuit
generator module, and — if the fix is attempted — a key-representation change, since an id-keyed
memo alone was measured *not* to restore DAG-proportionality (deep-nested-tuple rehashing). Budget
~1 week for the fix; the *measurement* of the defect is ~1 day and does not require the fix.

**Prerequisite implementation.** Yes, substantial. Run the pre-fix measurement first — it is a
bug report, not an experiment, and should not carry a 40-circuit cluster bootstrap.

---

### E2 — The redundancy ladder: is CM a structural layer, or is it CSE?

**Rank 2.**

**Question.** Once the raw-AST baseline is given the two textbook optimizations CM performs for
free — structural hash-consing and n-ary associative flattening — does any CM advantage remain?

**Hypothesis.** H0: on high-sharing formulas CM's advantage over a hash-consed,
flattening baseline is ≥2×. H0 dies if the top rung closes the gap to within the between-formula
noise band.

**Why not covered.** No baseline in the repo performs CSE. `compile_expr_flat`
(`bitset_backend.py:465-494`) is a plain recursion with no memo and strictly binary arg tuples;
CM's `compile_flat` (`bitset_backend.py:248-277`) memoizes on `id(cur)` and emits n-ary args.
Every published CM-vs-BitSet number is CM-with-CSE versus baseline-without-CSE.
`CM_experiment_A_related_families_report.md` tests *cross-expression* cache reuse, not
*within-expression* CSE, and uses the same non-memoizing control.

**Design.** Ladder: Rung 0 = today's `compile_expr_flat`; Rung 1 = +structural hash-consing;
Rung 2 = +n-ary flattening; Rung 3 = CM's flat program. All four must return the identical
bigint, asserted before timing. **Primary arm kernel-vs-kernel** (`eval_cm_node_words` vs
`eval_expr_words_bitset`, both terminating in the identical `_eval_words`) — do *not* use
`materialize_hybrid_no_reinflate`, which is an output-admission API, not a kernel. Preparation
timed separately for both sides. Corpus: sharing-ratio sweep 0→0.99. Unit: expression SHA,
cluster bootstrap. Sample: 30 per sharing decile × 7 rounds.

**Success interpretation.** If Rung 3 stays ahead of Rung 2 as sharing rises, CM's compiler does
something hash-consing plus flattening does not, and the project has a real order-of-magnitude
result it has never published — on the corpus it never built.

**Failure interpretation.** If Rung 2 ≈ Rung 3, CM's measured advantage *is* CSE plus
associativity — two optimizations available to any evaluator in ~150 lines — and the structural
layer has no distinctive operational content on the explicit-output contract. Decisive negative;
the honest residual claim becomes "a competent Boolean AST compiler with a well-tested
explicit-output path", which is true and much narrower than what is written today.

**Cost.** Local only, 0 pod-hours. Implementation ~150–200 lines (two passes as a scratch
module). ~1–2 days including validation; run ~30 min.

---

### E3 — Cluster-replicated headline on distinct formulas, with corrected arms

**Rank 3.**

**Question.** Does the stratum result (1.330 / 1.091 / 0.944) survive when the inferential unit
is a distinct Boolean function and both arms are the same call shape?

**Hypothesis.** H0: per-stratum median over ≥30 distinct formulas lies within the F1 noise band
of the published value **and preserves sign relative to parity**.

**Why not covered.** F1. Additionally the arms differ in shape: the CM arm is
`materialize_hybrid_no_reinflate(node, support, fixed=…, hybrid_threshold=16, allow_reduced_output=False, max_full_output_vars=16, flat_eval=True, words_eval=True)`
while the BitSet arm is a bare `eval_expr_words_bitset(expr, support, fixed=…)`. Inside the timed
region and with no counterpart in the control, the CM wrapper (`cm_ir.py:1589-1670`) performs a
function-local import, a `_cm_node_count` DAG walk, budget estimation, and result wrapping.

**Design.** ≥30 distinct formulas per band {8, 12, 16}, exact-support rejection-sampled, with
**operator mix as a crossed factor** {XOR-dominant, AND/OR-dominant, IMP/EQV-dominant} — F2
shows operator alone moves the ratio 30%, five times the effect being measured. Primary arm
kernel-vs-kernel; wrapper cost reported as a separate admission column, never folded into the
headline ratio. Even round count. Cluster bootstrap on expression SHA.

*Prior art to extend rather than re-derive:* `CM_flat_liveness_wrapper_paired_summary.csv`
already contains an unpublished decomposition — `cm_live_over_raw_live` = 0.97–1.06 (kernel
parity) and `cm_wrapper_over_raw_live` = 1.09–2.21 (wrapper penalty) at n=4..16.

**Success.** The published values become publishable for the first time. If operator mix is
significant, `live_k` is demoted from *the* explanatory variable to one of several, and every
"controlled live support" framing (V4 §C1, roadmap P10) must be restated.

**Failure.** If intervals straddle parity — likely, given F1 and F2 — "CM modestly ahead at
controlled 12/16" is **retracted as unsupported**, not disproven. It is the only stratum where CM
leads.

**Cost.** Local ~45 min; one pod replicate ~5 min pod time. Implementation ~60-line corpus
generator + arm swap, ~1 day.

---

### E4 — Charge preparation to both sides: the amortization crossover

**Rank 4.** Cheap, and it targets the only stratum CM leads.

**Question.** With compilation charged to both backends, how many evaluations per compiled
formula does CM need to cross below BitSet?

**Hypothesis.** H0: `N ≤ 10` in the strata where V4 reports CM ahead. Scouting puts `N` at
**125–238** at `live_k`=16 (independently derived at ~221 pod / ~128 local) and **undefined** at
`live_k`=8 on both machines and at `live_k`=12 on the pod. H0 is close to dead; the experiment
converts an estimate into a measured per-formula, per-platform curve.

**Why not covered.** `v4audit_packed_eval_2026_07_24.py:54-56` hoists
`compile_expr_to_cm_ir` out of the timed loop and records `compile_us`; line 89 computes
`paired_ratio = cm_s/bs_s` with no compile term. `compile_us` is in the raw CSVs and **absent
from every summary and figure**. There is no `bitset_prepare_us` column anywhere — one of the two
terms needed for a total-cost statement was never recorded. Measured this session: CM compile
126–731 µs vs BitSet prepare 24–66 µs (5–11×).

*Novelty caveat:* `CM_ir_cost_report.md` §3–4 already documents that `hybrid_no_reinflate` is
compile-dominated (ratio/bitset 3.71–18.44 at n=4..16). This experiment's contribution is the
**crossover count on the headline corpus and strata**, not the discovery that compile matters.

**Success.** Small `N` → CM's lead is operational and the amortization objection closes with data.

**Failure.** `N` ≈ 10² → the V4 sentence must be restated as a steady-state asymptote with its
workload condition attached. Any workload evaluating each formula fewer than ~200 times sees CM
lose at every `live_k`. **Note the counterpoint:** on the multiplier (high sharing) the same
accounting gives break-even at **5 evaluations** (CM compile 262 ms → 109 ops; BitSet prepare 68
ms → 26,157 ops; eval 0.409 vs 52.57 ms). So the amortization verdict is corpus-dependent, which
is itself the point.

**Cost.** Local only, ~40 min, **no new tracked code**.

---

### E5 — Schedule regime: blocked vs interleaved

**Rank 5.**

**Question.** Is the published ratio a property of the code or of the harness's blocked schedule?

**Hypothesis.** H0: per-stratum ratio is invariant within ±5% to schedule. A probe already moved
the pooled ratio 27%.

**Why not covered.** F5. No published number carries a schedule label.

**Design.** ~120-line scratch driver; three schedules (blocked, round-robin, Zipf locality);
per-call timing; `cache_info()` captured per stratum so the mechanism is *measured* rather than
asserted (F5's correction); both interpreters.

**Success.** Schedule-invariance retires one of the most obvious "your benchmark is unrealistic"
objections with data.

**Failure.** Every packed-eval ratio needs the label "blocked schedule, warm support cache" plus
a second number for interleaved workloads.

**Cost.** Local only, ~45 min, no tracked-code change.

---

### E6 — A compiled evaluator as a third arm on the packed contract

**Rank 6.**

**Question.** On the identical packed contract, corpus, and boundary, does a compiled packed-word
evaluator beat **both** CM and numpy-words BitSet?

**Hypothesis.** H0: neither is more than 2× off a compiled kernel.

**Why not covered.** `numba_backend.py:92-125` is a `uint8` row loop invoked under `build_tt` and
checked against the dense reference — it competes on the **dense byte-per-row** contract, never
on the packed-bits contract that produced the headline.

**Design.** A **2×2**, not a third arm: {CM flat program, raw-AST flat program} × {numpy
`_eval_words`, numba kernel}, all four returning the identical bigint, asserted before timing.
Without this factorization a numba win is uninterpretable — it would conflate "which program"
with "which executor".

**Success.** Within ~2× → the packed numpy family is near the practical floor and CM/BitSet
parity is a comparison between two good implementations.

**Failure.** 5–10× faster on the *same program* → the headline is a comparison between two slow
things, and CM's contribution is honestly "program compression" (E2) rather than "evaluation
speed".

**Cost.** Local only. `pip install numba` into `.venv` (verified resolvable, cp313 wheels, ~1
min). Kernel ~40–60 lines. ~4–6 h.

---

### E7 — Is CM actually order-independent?

**Rank 7.** The only genuinely *positive* structural claim available.

**Question.** Holding the function fixed and permuting only the variable labelling, how much does
CM's cost move versus CUDD's, and does CM's dispersion grow with `n`?

**Hypothesis.** H0: CM's within-function dispersion `D = p95/p5` over K relabellings is ≤2× and
does **not** grow with `n`. Falsified if `D_CM` grows — and a concrete mechanism exists:
`align_to_vars` (`cm_ir.py:968-993`) inserts transposes. F7 already measured a **1.78×** residual
on the adder pair, so H0 is not free.

**Why not covered.** Every corpus family is order-insensitive by construction (XOR chains are
BDD-linear under every order). `--robdd-order-policy` and `--robdd-dynamic-reordering` exist for
the BDD side; there is no variable-relabelling hook for CM.

**Design.** Families with analytically known separations (ripple-adder carry-out: exactly
`2^(m+1)−1` blocked vs `3m` interleaved) plus random relabellings, K=100. **Run at m=8 / n=16**,
where CM is admissible on every entry point — at m=10 / n=20 the packed artifact is 128 KiB,
over the 64 KiB benchmark budget and inside `DEFAULT_OUTPUT_BUDGET` (256 KiB) only via the direct
API. **Sifting is a mandatory CUDD baseline**, otherwise the comparison is against a strawman
fixed order.

*Tautology risk to design around:* "CM is order-independent" is close to true by construction, so
the informative quantity is the **residual** `D_CM` and its growth in `n`, not the CM-vs-CUDD
gap.

**Success.** `D_CM` flat while `D_CUDD` grows: a pre-registered, falsifiable invariance property
that fixed-order BDDs provably lack. This is the strongest positive result the project can obtain.

**Failure.** `D_CM` grows with `n`: CM is not order-independent, the residual has a named
mechanism (transposes), and the framing must be restated as implementation-order sensitivity with
a fix path.

**Cost.** CM/BitSet local ~30 min. CUDD half needs a pod, ~1–2 pod-hours. Implementation: a
relabelling hook, ~80 lines.

---

### E8 — Platform replication gate

**Rank 8.**

**Question.** Is the pod/local sign flip a genuine platform interaction, or inside between-pod
variance that has never been measured?

**Design.** Run the **gate first**: 5 fresh `cpu3c` pods, identical frozen script and corpus. If
the between-pod spread at `live_k`=8 covers 1.05–1.35, the "sign flip" dissolves into instance
noise and the rest is unnecessary — a cheap and genuinely possible outcome. Only if the gate
passes, run {Python 3.10, 3.13} × {local, pod}. Add an environment-provenance sidecar (platform,
python, numpy + config hash, CPU model, git SHA) to every benchmark writer.

**Success/failure.** Gate fails → F4's mechanism story is wrong; publish and stop. Gate passes →
no crossover can be stated without naming a machine, and the roadmap's P9 two-machine replication
**already exists unreported** in `CM_v4audit_packed_eval_raw.csv` + `_runpod.csv`; publishing the
`live_k`-dependent interaction table is a zero-cost P9 deliverable.

**Cost.** Pod required but trivial — the V4 pod campaign was ~40 s of compute; 5 pods ≈ a few
pod-minutes. **Needs Brian's authorization.** Local arm ~25 min. Check the pod worker redeploy
note in `CM_LATENT_FIXES_2026-07-23.md` first.

---

### E9 — The feasibility frontier and the above-guard contract

**Rank 9.**

**Question.** Where does each backend actually refuse, and above CM's guard — where CM produces
no artifact and CUDD still holds a BDD — at what query volume `M*` does building the diagram pay
for itself?

**Why not covered.** F6: refusal is never an outcome variable; the 7 hardest records are dropped
before timing. Nothing measures the above-guard region under a matched contract.

**Design.** Sweep `k`=10..22 × {XOR, AND/OR, mixed} × {packed, dense}; report a feasibility
frontier per backend — **the only comparison that does not require artifact parity**, and
therefore the only honest three-way chart available. For the above-guard arm, use *batched*
queries on both sides: a per-assignment `manager.let` loop measures Python binding overhead, not
a BDD property, and would rig the result.

**Success/failure.** `M*` large → the structural layer has a quantified story precisely where it
refuses to build. `M*` small → CM has no advantage above its guard under any matched contract,
and its domain is exactly `live_k`≤16 explicit artifacts — a clean, publishable scope statement.

**Cost.** Local ~1 h; CUDD arm ~2 pod-hours. Implementation ~80 lines (`robdd_query_batch` +
matched CM batch runner).

---

### E10 — CUDD metric repairs (cheap rider, not a campaign)

**Rank 10.** Three defects, all small, all required before any CUDD number is published again:

1. **Hoist `validate_dd_bdd_correctness` out of the timed span** (`robdd_dd.py:397-428`), add
   `robdd_validation_time_s`, and report a four-way per-trial decomposition (order generation |
   manager construct+declare | build | validation). <30 LOC. Do not frame it as
   published-vs-corrected — the attribution on `dd.cudd` is not settled (F8).
2. **Replace `self_xor_false`** (`v4audit_query_workloads_2026_07_24.py:69`) with a two-function
   equivalence check.
3. **Add cube-enumeration extraction** (`pick_iter`) behind the existing `tt_extract_method`
   parameter, and restate the 0.364 s datapoint against the *packed table* deliverable, not
   against a cube list.

**Cost.** ~1 day; local for (2) and the (3) pilot, bundled pod-hour for CUDD-labelled numbers.

---

## Part 3 — Agreements, disagreements, reprioritizations vs the 11-priority roadmap

**Agree, unchanged**
- **P9 (formula-clustered statistics)** — correct, now *sized* (F1). Its two-machine replication
  has already happened and was never reported; publishing the interaction table is free.
- **P11 (robustness / independent verification)** — correct, untouched by this analysis.

**Disagree / demote**
- **P1 (real independently-sourced workloads) — demote from Priority 1.** Right eventual goal,
  but F3 says CM cannot currently *accept* a circuit: the serde is tree-recursive and compile is
  tree-bound. Acquiring EDA datasets before E1 would measure a known implementation defect at
  dataset prices. E1 is the prerequisite, not the alternative.
- **P6 (BDD-hard families) — split, and retire half.** The hardness half is a **category error
  inside CM's admissible region** (F7: ROBDD ≤ ~2ⁿ/n, so at `live_k`≤16 no BDD can blow up, and
  CM's 2^k grows *faster* than the BDD on multipliers). Retire it. Keep and promote the
  order-sensitivity half as E7.
- **P8 (same-environment CUDD downstream campaign) — substantially rescope.** The nine-leg
  campaign is not worth its pod cost: single-op measurements structurally cannot produce a BDD
  win, and the corpus cannot answer any crossing question. Replace with E10 (cheap) + E9.
- **P10 (high-live-support scaling above 16) — demote as standalone.** "Do not extrapolate three
  points" is established. Fold the useful part into E9's frontier. Keep the verified facts: the
  guards are keyword arguments and packed equality holds to `k`=20.
- **P7 (automatic multi-backend routing) — demote hard.** A router needs a cost model; F3 shows
  the current cost model is wrong. Building it now would learn the corpus's artifacts.
- **P2 (canonical CM equivalence) — demote.** A formalization task, not a benchmark; the roadmap
  already concedes it must first show the artifact offers something ROBDDs do not.

**Reprioritize up (absent or under-weighted)**
- **E1 (circuit/DAG cost model) to Priority 1.** Absent from the roadmap entirely. It is a P0
  engineering defect *and* it falsifies the variable that organizes every published result.
- **E2 (CSE ladder) to Priority 2.** Absent. The only work that can falsify the thesis itself.
- **E4/E5 (amortization, schedule) to immediate.** ~40 min each, no tracked-code change, both
  attack the validity of already-published numbers.

---

## Part 4 — Not worth testing, and why

- **"BDD-hard families where CM wins."** Category error by theorem inside `live_k`≤16 (F7).
  Retire the motivation; do not add multipliers to the corpus *as a CM-favourable stress test*.
  (They are still valuable as high-sharing inputs for E1/E2 — a different purpose.)
- **Espresso.** Permanent category error: it produces a minimized cover, not a 2^k output. The
  existing wiring is already confounded — `cm_bench.py` starts the espresso clock *before*
  building a full truth-table string and calling `truthtable2expr`, so "espresso time" contains
  the entire thing CM competes on plus minimization CM never does. `expr_simplify.py:49-75`
  `bdd_sop` is minterm-string concatenation over the full truth table — neither a BDD nor
  minimization. Delete from comparison; do not repair.
- **SymPy as a competitor.** It will lose by orders of magnitude and everyone knows it. Keep as a
  correctness oracle only.
- **SAT (pysat) as a standalone campaign.** No CM claim is at risk. Worth at most a 1–2 h
  footnote after E2/E6, and only on the 7 guard-skipped records where feasibility is the only
  available question.
- **Expanding the ambient-`n` grid.** Actively wasteful: across-ambient-`n` σ is *smaller than
  timing noise* (F1). Convert the budget to distinct formulas 1:1.
- **More rounds/repeats to tighten intervals.** They shrink an interval that already has zero
  coverage for the population "formulas with live support 16".
- **More zero-mismatch counts on the existing corpus.** 294 packed-equal pairs over 31 distinct
  expressions does not become stronger evidence at 588.
- **Execution-order bias.** Killed by measurement this session from existing data (<1% pod, <5%
  local). A genuine negative.
- **Output-budget calibration as framed.** The apparent defect was a probe artifact (F6,
  retracted). Do not fund on current evidence.
- **GPU, distributed, naive multiprocessing, sparse-truth-table default, approximation.** Already
  rejected in `CM-PERFORMANCE-AUDIT.md`; nothing found here disturbs those rejections.

---

## Part 5 — The three most likely to disprove something

Run order, cheapest-decisive first: **E4 → E5 → E1(measure-only) → E2 → E3**.

### 1. E1 — the circuit/DAG cost model

**Would disprove:** that CM's cost is governed by semantic live support.

**What would not survive:** the organizing variable of every published result. The `live_k`
stratification of `CM_v4audit_packed_eval_summary_runpod.csv`, the sparse `live_k`=1..16 strata,
and the entire rationale for stratifying by support would be revealed as properties of
tree-shaped random generation. Measured evidence already points this way: compile is linear in
tree unfolding across a 285× sweep while the DAG moves 2.4×. It also blocks P1: CM cannot be
applied to circuit-derived workloads until `build` is DAG-proportional, and the obvious fix was
measured *not* to achieve that.

### 2. E2 — the redundancy/CSE ladder

**Would disprove:** that CM is a *structural layer*, as opposed to an AST compiler performing
hash-consing and n-ary flattening.

**What would not survive:** the central framing of the paper and of
`CM_ARCHITECTURE_AND_AUDIT.md`. If a ~150-line hash-consed baseline matches CM everywhere, then
every CM-vs-BitSet number ever published — including the 128× multiplier result measured this
session — is a statement about the *baseline's* missing memo table. Symmetric experiment: a
positive result is equally consequential and hands the project a real order-of-magnitude win it
has never reported.

### 3. E3 — cluster-replicated headline

**Would disprove:** "CM is approximately at Bitset parity and sometimes modestly faster when the
comparison is controlled by actual support and output scope" — the V4 publication headline.

**What would not survive:** the sentence "CM modestly ahead at controlled 12/16". It rests on one
XOR chain per stratum (F1); its 5.6% effect is smaller than the 30% swing from operator alone
(F2) and than the observed 29% between-formula spread at fixed `live_k`; its sign is
platform-dependent (F4, opposite sides of parity at `live_k`=12); and its mechanism is
associative flattening on an 82%-XOR corpus, which by construction cannot generalize to IMP/EQV.
I expect intervals straddling parity — a **retraction for insufficient evidence**, not a
demonstration that CM is slower.

Also would not survive: the `formulas` column of the summary CSV as labelled, and any figure
keyed on nominal `n` (`v4audit_public_chart_data_2026_07_24.js` plots `wrapper/cm_over_bitset`
1.05→0.84 against n=16..32, a variable V4 itself states is not the workload size).

### What *would* survive all three

The correctness results. 294 packed-equal pairs with zero mismatches, the multi-oracle support
verification, the guard behaviour, and the typed output contract are real and are not threatened
by anything in this document. The weakness throughout is in the **performance claims and the
corpus that generated them**, not in the implementation's correctness.

And one thing likely to survive *and grow*: CM's program compression on shared structure. 240×
fewer operations than the published baseline on an 8×8 multiplier, break-even at 5 evaluations
under full total-cost accounting, is a better result than anything currently published — it has
simply never been measured, because the corpus contains nothing with shared structure.

---

## Appendix A — Corrections and provenance

Corrections to my own or the brief's earlier statements, made because they change conclusions:

- **CUDD order-search cost.** I first attributed `cudd_best10_order_search_us` to manager
  setup/teardown. It is in-band `validate_dd_bdd_correctness` with `correctness_samples=64`
  (`robdd_dd.py:398/420-428/447`). Attribution on `dd.cudd` specifically remains unsettled — the
  disproof of "manager churn" was measured on `dd.autoref`.
- **Output-budget calibration.** A probe suggested the temporary-bytes model was 2.7× optimistic
  (unsafe). Retracted: the probe called `estimate_explicit_output` without `operation_slots`,
  comparing reality to an estimate the system never computes.
- **BDD-hard framing.** My initial ranking proposed BDD-hard families as a regime where CM would
  separate from CUDD. That is a category error inside `live_k`≤16 (F7). Reframed to
  order-sensitivity (E7) and to high-sharing corpus material for E1/E2.
- **Schedule mechanism.** "BitSet leans on the 4-entry env cache harder than CM" does not hold —
  the cache is shared. The 27% movement stands; the mechanism is open.
- **Amortization novelty.** `CM_ir_cost_report.md` §3–4 already documents compile dominance;
  E4's contribution is the crossover count on the headline strata.
- **Brief corrections.** Corpus median `live_k` is 9, not 5. The controlled-stratum inferential
  unit is 1, not 7. numba is not confined to Python 3.10.
- **Measurement caveats.** My one-shot cold local probe produced ratios far worse for CM than the
  published 7-round interleaved local run; only its *structural* quantities (op counts,
  preparation costs) are used. Multiplier timings are one local machine, min-of-5 blocks of 200,
  exact packed equality asserted every run; the 240× op compression is deterministic and
  machine-independent, the 128× timing figure is indicative. BDD node counts are canonical and
  backend-identical to CUDD; `dd.autoref` build *times* are pure-Python upper bounds.

## Appendix B — Reproduction

```bash
.\.venv\Scripts\python.exe -c "import json;recs=[json.loads(l) for l in open('deliverables_n22_24/v4audit_corpus_2026_07_24.jsonl')];print(len({json.dumps(r['expression'],sort_keys=True) for r in recs}),'distinct of',len(recs))"
```

Associative-flattening asymmetry, compile-vs-unfolding scaling, multiplier and adder probes: full
scripts are in the session scratchpad
(`C:\Users\brian\AppData\Local\Temp\claude\C--Users-brian-Documents-CM-Computation\6a8095ab-5377-4a23-94f3-fe3fd9259180\scratchpad`).
None were committed; none write to the repo.

## Appendix C — Cost summary

| ID | Experiment | Impl. prereq | Local | Pod | Rank |
|---|---|---|---|---|---:|
| E1 | Circuit/DAG cost model | DAG serde + generator (+ key-repr fix) | 2–3 h | none | 1 |
| E2 | Redundancy/CSE ladder | ~200 LOC (1–2 d) | ~30 min | none | 2 |
| E3 | Cluster-replicated headline | ~60 LOC + arm swap (1 d) | ~45 min | ~5 min | 3 |
| E4 | Amortization crossover | none | ~40 min | optional | 4 |
| E5 | Schedule regime | none (~120 LOC scratch) | ~45 min | none | 5 |
| E6 | Compiled third arm | pip + ~60 LOC | ~1 h | none | 6 |
| E7 | Order dispersion | ~80 LOC relabel hook | ~30 min | 1–2 pod-h | 7 |
| E8 | Platform replication gate | provenance sidecar | ~25 min | ~5 pod-min | 8 |
| E9 | Feasibility / above-guard | ~80 LOC | ~1 h | ~2 pod-h | 9 |
| E10 | CUDD metric repairs | <30 + ~120 LOC | ~2 h | bundled | 10 |

**Ranks 1–5, the decisive set: ~3 days implementation, ~4 hours of runs, zero pod-hours.**
E1's measurement half needs no fix and no pod, and is the single highest-value day available.
