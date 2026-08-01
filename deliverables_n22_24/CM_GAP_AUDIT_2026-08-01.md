# Adversarial Audit of the 2026-08-01 CM Benchmark Gap Analysis

Date: 2026-08-01  
Repository revision at kickoff: `b6ce6b2` (`main`)  
Benchmark interpreter: `.venv/Scripts/python.exe`  
Test interpreter: system Python 3.10  
New evidence: `cm_gap_audit_probe_2026_08_01.py` and `cm_gap_audit_probe_results_2026_08_01.json`

## Executive verdict

The gap analysis is directionally right about the corpus, compile/unfolding risk, formula-level
replication, schedule labeling, survivorship, and contaminated CUDD search timing. It overreaches
on its two most important interpretations:

1. The multiplier headline is not evidence that CM has a distinct 128x evaluation capability.
   A structural-CSE baseline reduces the same 8x8 central-bit program from 38,869 raw operations
   to 167, versus 147 for CM, and ran faster than CM in this pilot. The reported advantage is
   primarily the control compiler's missing CSE, with a smaller residual from CM's associative
   canonicalization and wrapper/program details.
2. The compile defect is real, but it is not "precisely and only in `build`" and the memo result
   was overstated. A small identity memo sped a 53-node/8,187-occurrence in-memory DAG from
   34.3 ms to 1.02 ms (33.5x). It cannot help after the current JSON serializer expands the DAG
   to 8,187 distinct objects, and deep structural keys leave the memoized arm mildly
   super-linear. The repair is staged, not all-or-nothing: identity memo now; DAG-preserving
   input next; compact canonical keys if profiling still justifies it.
3. The BDD theorem does not retire BDD-hard tests. The analysis compares BDD *nodes* with packed
   truth-table *bits* and infers pipeline performance from that dimensionally invalid comparison.
   Across 8x8 multiplier outputs, the largest measured ROBDD was not the cited middle bit: it was
   3,560 nodes under blocked order and 4,419 under interleaving. Required downstream operations,
   memory per node, build intermediates, and ordering still matter.

My overall confidence in these three corrections is **high**. Confidence in absolute local
timing ratios is **moderate**; deterministic operation/node counts and exact-equality checks are
**high confidence**.

## A1 — Compile-cost scaling (F3)

**Verdict: CONFIRMED-WITH-CORRECTION. Confidence: high.**

### Evidence

- `CMIRBuilder.build` is unmemoized (`cm_ir.py:806-824`). The current serializer recursively
  emits children and has no definitions/references (`cm_expr_serde.py:17-37`).
- On an 11-point reconvergent ladder, current compile time tracked unfolded occurrences almost
  perfectly: slope 4.04 microseconds/tree node, R-squared 0.9998. At depth 10 the input had 53
  identity-DAG nodes, 8,187 unfolded occurrences, and compiled to 31 CM operations in 34.3 ms.
- The scratch identity-memo builder reduced that case to 1.02 ms. Its log-log slope against DAG
  nodes was about 1.36, consistent with a remaining deep-key cost, but it removed 97% of current
  compile time. Therefore "the obvious fix does not work" is materially misleading.
- JSON round-trip changed 53 shared identities into 8,187 identities. The identity-memo arm then
  took 37.9 ms versus 34.0 ms current. This cleanly separates the two defects.
- `_interned` still uses nested tuple keys (`cm_ir.py:796` and analogous constructors), so a
  compact-key follow-up remains justified after the first two fixes.
- Real benchmark formats do preserve circuit structure. The official EPFL suite distributes
  circuits as Verilog, VHDL, BLIF, and AIGER, including arithmetic, multiplier, and control
  workloads; the suite reports AIG node/level counts rather than expression-tree unfoldings
  ([EPFL benchmark suite](https://www.epfl.ch/labs/lsi/page-102566-en-html/benchmarks/)).

### Correct statement

For the current tree-only serialized path, compile cost is proportional to the serialized tree
unfolding. For an in-memory shared `Expr` DAG, the current builder unnecessarily re-walks shared
objects, and a small identity memo is a large immediate improvement, though not yet a proof of
strict DAG-linear behavior. Total CM cost is not independent of `live_k`: compile/preparation
depends on representation size and sharing, while explicit evaluation/output still depends
exponentially on live support.

### Rank effect

Keep E1 high, but split it into: (1) identity-memo patch with regression tests, (2) DAG-aware
serde/AIGER ingestion, (3) compact key representation only if the residual profile warrants it.
The gap analysis's one-week key-rewrite prerequisite is not supported.

## A2 — 128x multiplier headline (F2)

**Verdict: REFUTED as a distinctive CM result; CONFIRMED as raw-baseline compression. Confidence: high.**

### Evidence

Thirty exact-output cases covered 4x4 through 8x8 multiplication, three neighboring output bits,
and sequential versus balanced partial-row addition. All CM/raw/CSE packed bigints were asserted
identical before timing.

For the 8x8 central output bit in this generator:

| construction | CM ops | raw ops | structural-CSE ops | CM eval | raw eval | CSE eval |
|---|---:|---:|---:|---:|---:|---:|
| sequential | 147 | 38,869 | 167 | 524 us | 69.5 ms | 302 us |
| balanced | 149 | 2,553 | 167 | 434 us | 4.44 ms | 271 us |

The same Boolean function therefore produced raw/CM compression of 264x or 17x solely from
adder topology. Structural CSE made both topologies 167 operations and was about 1.6-1.8x faster
than CM on this case. Across all cases, CSE/CM operation ratio averaged 1.31; CSE execution was
already faster in the 4x4 group and its relative lead increased with width.

The project's asymmetry is exactly visible in code: `compile_expr_flat` recursively emits every
occurrence (`bitset_backend.py:466-495`), while lowering CM uses identity memoization over the
already-interned DAG (`bitset_backend.py:249-278`).

### Correct statement

CM performs valuable structural CSE and associative lowering that the published raw-AST control
does not. The two-orders-of-magnitude number measures the weakness of that control on a particular
tree construction; it is not a function-level or CM-specific advantage. A fair performance claim
must compare CM against structural CSE and, separately, CSE plus associative flattening.

### Rank effect

E2 becomes the top scientific priority, but its two-rung pilot already rejects the strongest
thesis. The next run should validate this result on independent AIG/netlist cones and non-arithmetic
families, not repeat more synthetic multiplier timings.

## A3 — Variance and sample size (F1)

**Verdict: CONFIRMED-WITH-CORRECTION. Confidence: high for the arithmetic, low for transfer.**

Only 16 of 21 sparse formulas lie in `live_k` cells containing more than one formula, producing
10 residual degrees of freedom. Pooled within-`live_k` dispersion of per-formula log-ratio
medians is:

| environment | df-correct pooled sigma | reported smaller sigma | source of smaller value |
|---|---:|---:|---|
| pod | 0.09352 | 0.06454 | `0.09352 * sqrt(10/21)` |
| local | 0.11898 | 0.08211 | `0.11898 * sqrt(10/21)` |

The smaller estimate divides residual sum of squares by all 21 formulas, including five formulas
in singleton cells and the lost degrees of freedom from estimating 11 cell means. Those formulas
contribute zero residual information. It is biased downward and should not be used for power.
A moments correction for within-formula timing variance gives about 0.0916 pod and 0.1003 local;
it does not rescue 0.065. A naive chi-square interval from only 10 df is broad (approximately
0.065-0.164 pod and 0.083-0.209 local), before model uncertainty.

Use sigma 0.10-0.15 for planning (roughly 36-77 formulas for a 5% effect under the analysis's
test assumptions), then update from a pilot. None of these data establish transfer from shallow,
mixed-operator depth-4 formulas to XOR chains or circuit cones.

### Rank effect

E3 remains essential. Formula identity and operator/family must be sampling units; ambient `n`
rebinding and extra timing rounds are not substitutes.

## A4 — Pod/local mechanism (F4)

**Verdict: CONFIRMED-WITH-CORRECTION. Confidence: high that repeat count is not the cause; moderate on mechanism.**

The historical local file contains 224 rows at repeat 200 and 70 at repeat 50; pod uses 200 for
all 294 executed rows. A same-formula local rerun of all 42 formulas at both repeat counts found:

- geometric mean of ratio(200)/ratio(50): 0.994;
- median: 1.001;
- four sign flips, all near parity.

The formulas historically assigned repeat 50 had only a 1.10x pod/local gap, while the repeat-200
group had a 1.50x gap—the opposite of repeat count explaining the pooled 1.39x interaction.
Repeat selection is therefore not the material cause on this machine. The platform interaction
remains real in the archived data, but "fixed overhead" is a plausible interpretation rather
than a closed mechanism. CPU/cgroup provenance and pod-to-pod variance remain unresolved.

### Rank effect

Keep E8, but use it as a publication replication gate after the local scientific controls. No pod
was started in this audit.

## A5 — BDD category-error argument (F7)

**Verdict: REFUTED in its practical conclusion. Confidence: high.**

The asymptotic maximum-ROBDD node-count result does not imply that a BDD is smaller in bytes,
faster to build, or faster/slower for a required pipeline. A BDD node stores a variable and edge
references; a packed truth table stores one bit per assignment. Comparing `~2^n/n` nodes with
`2^n` bits and calling the former smaller by `n` is dimensionally invalid. The asymptotic also
does not justify substituting 4,096 as an exact n=16 maximum: this audit measured 4,419 reachable
nodes for one 8x8 output/order.

Pure-Python `dd.autoref` results across every 8x8 multiplier output (blocked and interleaved
orders) ranged from 3 nodes to maxima of 3,560 and 4,419. The cited bit 7 was 1,025/777 nodes;
the largest outputs were bits 9-11. Build time and ordering behavior also varied by bit, and
interleaving was not uniformly best. These are structural measurements, not CUDD timing claims.

The pipeline question remains task-dependent:

- complete packed output favors a packed evaluator once it is feasible;
- repeated restriction, equivalence, model counting, or symbolic composition may favor a BDD;
- BDD build peak memory/intermediate nodes and ordering must be measured, not inferred from the
  final reduced node count.

### Rank effect

Do not retire roadmap P6. Reframe it as a representation-boundary and operation-closure suite,
with task-matched outputs. E7 remains useful; E9 remains the feasibility/frontier companion.

## A6 — Citation and implementation checks

**Verdict: CONFIRMED-WITH-CORRECTIONS. Confidence: high.**

The named implementation claims are substantively accurate:

- associative set: `cm_ir.py:33` (the report's `:31` is stale line drift);
- deep `IMP` key: `cm_ir.py:796`; unmemoized build: `cm_ir.py:806-824`;
- alignment/transposes: `cm_ir.py:968-993`; materialization memo: `cm_ir.py:1211-1219`;
- wrapper/admission work: `cm_ir.py:1589-1672`;
- CM lowering memo: `bitset_backend.py:249-278`; raw lowering no memo:
  `bitset_backend.py:466-495`; cache sizes: `bitset_backend.py:561-576`;
- CUDD trial validation is inside `trial_total_time` and `search_time`:
  `cmbench/backends/robdd_dd.py:397-471`, emitted at `:551-563`;
- packed harness compile hoist, adaptive repeat, alternating order, id count, and guards:
  `deliverables_n22_24/v4audit_packed_eval_2026_07_24.py:43-109`;
- degenerate self-XOR query: `deliverables_n22_24/v4audit_query_workloads_2026_07_24.py:68-76`;
- requested pod shape: `cm_runpod_deploy.py:170-184`;
- wrapper decomposition columns exist in
  `deliverables_n22_24/CM_flat_liveness_wrapper_paired_summary.csv`;
- compile dominance was already documented in `CM_ir_cost_report.md:42-59`.

The additional consequential mistakes found are the F1 residual-variance denominator, F2's
unfair control inference, F3's "memo does not work" wording, and F7's node-versus-bit comparison.
F8 itself is confirmed: validation contaminates search/all-in time, while isolated build fields
remain usable.

## F1-F8 summary

| finding | verdict | audit view |
|---|---|---|
| F1 corpus/inference | Confirmed with correction | inferential unit problem is real; smaller sigma estimate is biased low |
| F2 associative/raw-baseline headline | Refuted as CM-specific | operation counts are real; advantage collapses against structural CSE |
| F3 tree-bound compile | Confirmed with correction | current serialized path is tree-bound; identity memo is already a 33x fix on a shared DAG |
| F4 platform interaction | Confirmed with correction | repeat count does not explain it; detailed mechanism remains unresolved |
| F5 blocked schedule | Confirmed, attribution unresolved | cache/schedule sensitivity is real; shared-cache story was correctly retracted |
| F6 survival conditioning | Confirmed | refusal must be reported as an outcome; output-budget retraction is appropriate |
| F7 BDD impossibility/category error | Refuted | theorem does not imply byte size or pipeline performance; retain BDD boundary tests |
| F8 CUDD search contamination | Confirmed | validation is inside search/all-in timing; isolated build time is separate |

## Re-ranked E1-E10

1. **E2 — strong-control redundancy ladder.** Finish structural CSE plus associative-flattening
   arms on public DAG/netlist cones. The two-rung pilot already changed the central belief.
2. **E1 — staged DAG compile repair and scaling.** Land/test identity memo, add DAG-preserving
   ingestion, then profile compact keys. Measure compile, lower/materialize, and execution apart.
3. **E3 — formula-clustered, operator-crossed replication.** Required before retaining the
   controlled-12/16 performance sentence.
4. **E4 — amortization crossover.** Cheap and directly changes operational interpretation.
5. **E10 — CUDD metric repairs.** Known measurement defect; small patch; prerequisite to reuse.
6. **E5 — blocked/interleaved/real-locality schedule.** Keep, with measured cache counters.
7. **E8 — platform replication gate.** Needed for publication, but not before local controls.
8. **E9 — feasibility and operation-closure frontier.** Retain; broaden beyond a size-only chart.
9. **E7 — variable-order dispersion.** Valuable positive/negative structural property, with
   dynamic reordering as a mandatory BDD arm.
10. **E6 — compiled executor factorization.** Useful engineering ceiling, but it cannot repair an
    unfair compiler comparison and should follow E2.

E1 and E2 from the original ranking are no longer independent: DAG-aware ingestion and fair CSE
controls should share the same public-netlist corpus and measurement schema.

## Tests and optimizations to add to the project

### Immediate tests

1. Builder identity-sharing regression: construct a shared `Expr` DAG, assert identical output,
   identical CM node semantics, bounded builder visits, and a large compile-time guardrail kept
   out of normal unit tests if unstable.
2. Serde sharing test: add a versioned `defs`/`ref` schema; round-trip must preserve shared-node
   count and reject cycles/dangling references. Retain compatibility with existing tree JSON.
3. Fair-baseline test: raw, structural-CSE, CSE+associative, and CM programs must return the same
   bigint on property-generated expressions and public circuit cones.
4. Formula-clustered statistics test: summaries must count expression SHA/function identity,
   reject singleton-only variance estimates, and expose residual df.
5. Timing-boundary test: CUDD validation must never appear in build/order-search fields; emit a
   separate validation duration.
6. Benchmark schedule metadata: every result records blocked/interleaved/locality policy, repeat,
   cache state, Python/NumPy, CPU, quota, and revision.

### Optimization sequence

1. Add `id(expr)` memoization to `CMIRBuilder.build` without changing canonicalization defaults.
2. Introduce DAG-preserving input/adapter support (AIGER or a versioned internal defs/refs format).
3. Replace deep nested tuple hashing with compact intern IDs/digests only after correctness and
   collision/canonicalization tests exist and residual profiling warrants it.
4. Add structural CSE and associative lowering to the BitSet compiler as a production option and
   retain the raw compiler only as an explicitly labeled ablation.

Public EDA data is appropriate here, not speculative: the EPFL suite contains 23 combinational
circuits across arithmetic and control families and publishes AIGER/BLIF/HDL forms
([EPFL](https://www.epfl.ch/labs/lsi/page-102566-en-html/benchmarks/)); its paper describes the
64x64 multiplier as a 27,062-node, 274-level AIG
([IWLS paper](https://si2.epfl.ch/~demichel/publications/archive/2015/IWLS15.pdf)). Start with
small output cones reduced to live support feasible for exact packed comparison.

## Claims that should not be relied on yet

- "CM is modestly faster at live_k 12/16" as a population claim.
- The 128x multiplier number as a CM-specific or function-invariant advantage.
- "An identity memo does not fix compile" or "a key rewrite is the first required repair."
- "CM cost is governed by live support" or the opposite absolute "live support predicts nothing."
  Compile structure and explicit-output support are separate axes.
- The 0.065/0.084 between-formula sigma values and sample sizes derived from them.
- The fixed-overhead explanation for the pod/local interaction as a closed causal result.
- "BDD blowup is impossible below 16" in any memory, runtime, or pipeline sense.
- Any `cudd_best10_*_search_us` interpretation until validation is hoisted.
- `self_xor_false` as a meaningful equivalence workload.

## Verification

- Probe script completed with 30 multiplier cases, 11 compile-scaling points, 42 formulas at two
  repeat counts, and all multiplier outputs at widths 4-8 under two BDD orders.
- Every CM/raw/CSE multiplier arm asserted identical packed output before timing.
- Probe script passes `python -m py_compile` under the benchmark environment.
- Full project suite did not finish inside a 300-second cap. It reached 32% (95 displayed passes)
  with no failure before timeout. No claim is made about the unexecuted remainder.
- No pod, commit, push, historical report edit, or historical CSV overwrite was performed.
