# Mechanism, early progression, and comparator audit

Audit date: 2026-09-18. This is a bounded audit contribution covering N1, P01–P07, P07B, supplied Gate-A S1/S2 evidence, and relevant pinned public-repository source. Source files were read without alteration. Paths beginning `primary/` below are relative to `audit_p1_p13_20260918`; paths in individual evidence citations are relative to `primary/ASTRA_P1_P13_AUDIT_PACKAGE` unless otherwise stated.

## Verdict

The reduction in sparse-ANF work is real for the supplied deliberately favorable workload and is substantially stronger after propagation of ancestor signatures. It is ordinary two-input Boolean truth-function composition applied to compound DAG operands, combined with demand-driven lowering and a heuristic sharing-aware cost estimate. It is not evidence of a unique CM operation that a generic truth-table optimizer cannot reproduce.

The supplied Gate-A addition makes that last distinction unusually strong: independently reading its raw CSV confirms identical CM/generic multiplication counts, pair terms, peak monomials, and output digests on all 10,389 admitted cases. Its timings are explicitly single-pass diagnostics. This demonstrates equivalence of the tested generic and CM implementations on that corpus; it does not prove every possible optimizer will have identical work or speed.

The early data support the architectural narrative but do not isolate representation cost perfectly. Mandatory ANF statistics remain inside all P-series timings, even with `collect_stats=False`. Direct does more intermediate work, so profiling overhead can disproportionately favor folds. Conversely, P6 performs an unnecessary complete reachable-node traversal inside its timed lowering, even with selector statistics disabled, disadvantaging CM. P7 silently omits one statistics update retained by P6. These are concrete reasons to run a matched production-kernel ablation before attributing the remaining gap exclusively to pair telemetry or moving only that component to C.

## What the code actually computes

### Source and output representations

`03_N1_BASELINE/n1_gatep_harness.py:32` defines nodes with `nid`, `op`, `args`, and `value`. `Factory._make` at line 46 interns `(op, tuple(child_ids), value)`. The source is therefore an ordered, structurally interned DAG rather than an unshared expression tree. `Factory.bin` at line 59 eliminates constants and exact identical-operand cases but intentionally preserves order. In particular, `AND(a,b)` and `AND(b,a)` are distinct source nodes. No cached semantic support or monomial estimate is maintained in the ordinary factory.

Sparse ANF is a Python `set[int]`: each integer is a monomial bitmask, zero denotes the constant monomial, symmetric difference is polynomial XOR, and monomial multiplication uses bitwise OR to implement Boolean idempotence. `mul_poly` at line 423 enumerates every pair of monomials and toggles the resulting mask. `lower_anf` at line 437 memoizes polynomials by source node ID; it does not memoize products between different source nodes, remove polynomial-level zero/one/idempotence work, or discover broader Boolean identities.

The four-bit token uses bit index `2*x+y`, ordered `00,01,10,11`, whereas the manuscript presents a true-first matrix. This is a declared representation change, not a mathematical inconsistency. For token entries `t00,t01,t10,t11`, the polynomial is

`t00 XOR (t10 XOR t00)*A XOR (t01 XOR t00)*B XOR (t11 XOR t10 XOR t01 XOR t00)*A*B`.

The final coefficient is 1 exactly when token parity is odd. This determines whether one nonlinear product is necessary for a generic two-input ANF realization. It is not a statement about the degree of the compound operands or minimum multiplicative complexity of the whole circuit.

### Why propagated signatures help

P4 stores a signature `(base_a_id, base_b_id, token)` for a source node even when it never rewrites that node. It tries the left child's propagated pair before the right child's pair, aligns direct bases, `NOT(base)`, and same/swapped signatures, and composes exact four-bit functions. See `P04/n2_p4_harness.py:115`, `:130`, and `:177`. There is one retained propagated pair; this is not arbitrary cut enumeration, a global canonical form, or superoptimization.

P1/P2 can lose ancestor opportunities when an intermediate local rewrite is rejected. P3 inspects only shallow source shells. P4 propagates semantic information independently of local profitability, so an ancestor can still contract a long shell. Demand-time acceptance occurs before recursive ANF lowering. Once accepted, the lowerer calls the base operands directly and skips the intermediate shell (`P04/n2_p4_harness.py:306`; `P06/n2_p6_harness.py:307`). Source-node memoization preserves the sharing of bases still demanded elsewhere.

This is a useful compiler principle: retain semantic facts without committing to eager rewrites, then choose profitable contractions when demand is known. Counting fewer accepted folds can coincide with much larger savings because a high ancestor fold replaces many possible descendant folds.

### Mathematical scope relative to the paper

`02_BACKGROUND/operator-level-boolean-computation-with-correspondence-matrices.txt:244` states a structural theorem for distinct declared row/column variables; lines 250–253 and 322–326 explicitly exclude compound operands treated as opaque from that particular admission rule. Gate-P constructs moderately complex, shared `A` and `B` (`03_N1_BASELINE/n1_gatep_harness.py:632`) and uses them as signature bases. Thus P-series semantics extend beyond the paper's narrow structural compiler contract.

The extension is sound by elementary substitution: if `H(x,y)=Phi(F(x,y),G(x,y))` for all four Boolean assignments, then for every valuation `v`, `H(A(v),B(v))=Phi(F(A(v),B(v)),G(A(v),B(v)))`. The values of A and B need not be statistically or logically independent. Correlation can make the four-point signature stronger than necessary, but cannot invalidate an identity valid on all four points. Node-ID alignment avoids confusing merely similar operands. The manuscript's true-first convention, P-series false-first token, and pure-Boolean phase `star` convolution must remain distinct. No phase or quantum algebra is used in these lowering kernels.

### Profitability is a heuristic, not a guarantee

P1 freezes cap 4096, minimum estimated savings 16 pair terms, and relative savings thresholds 20% for shared children and 10% otherwise (`P01/n2_p1_harness.py:24`; preregistration lines 11–35). The keeping estimate is parent nonlinear pair work plus child shell work only for source fanout one; folding costs at most a single estimated base product. P4/P6 use the same thresholds with propagated child tokens (`P04/n2_p4_harness.py:266`; `P06/n2_p6_harness.py:281`).

Fanout is the number of edges of unique reachable source parents, not the number of construction requests, expression occurrences, or future optimized demands. This correctly counts a cache hit as no new edge. It is conservative but imperfect: several source parents may themselves be bypassed, or a shared product may already be computed. The estimates ignore cancellations and polynomial sparsity correlations, omit XOR/allocation/matching cost, and subtract estimated costs rather than rigorous lower/upper savings bounds. Saturation is a valid size cap for the tested support <=12, since at most 4096 monomials exist; it is not a general upper bound for larger support. A rejected fold is not proved unprofitable and an accepted fold is not proved faster.

Explicitly, write `nl(t)=t11 XOR t10 XOR t01 XOR t00`, `M(t,a,b)=min(4096,c0+ca*m(a)+cb*m(b)+cab*m(a)*m(b))`, `L=M(t_left,a,b)`, and `R=M(t_right,a,b)`. Then `K=nl(parent)*L*R + I(left_shell and uses(left)==1)*nl(t_left)*m(a)*m(b) + I(right_shell and uses(right)==1)*nl(t_right)*m(a)*m(b)`, `F=nl(composed)*m(a)*m(b)`, `B=K-F`. Accept iff `B>0`, `B>=16`, and `B/max(1,K)>=0.20` when either immediate source child has use count>1, otherwise `>=0.10`. Propagation stores a legal composed token even when these acceptance inequalities fail.

## Independent reconstruction of early raw results

`mechanism_raw_check.py` reads the combined raw JSONs and recomputes counts and median-based ratios. Its output `mechanism_raw_check.json` includes source hashes. No historical harness or result file is modified. All early supplied symbolic rows have `ok=True`; this checks record consistency, not a new full historical replay.

Across the same 36 Gate-P cases:

| Arm | Accepted/rewrite folds | Consumed demand folds | Sum multiplications | Sum pair terms | Sum ANF nodes evaluated |
|---|---:|---:|---:|---:|---:|
| Direct | 0 | n/a | 522 | 17,670 | 932 |
| P1 | 110 | n/a (rewritten graph) | 342 | 12,058 | 674 |
| P2 | 110 planned | 41 | 366 | 12,150 | 726 |
| P3 | 58 | 58 | 455 | 15,014 | 877 |
| P4 native-only | 58 | 58 | 455 | 15,014 | 877 |
| P4 propagated | 29 | 29 | 203 | 624 | 486 |
| P5 / P6 / P7 | 29 each | 29 each | 203 each | 624 each | 486 each |

These are summed-work diagnostics, not geometric means. P4's matched native/propagated experiment is particularly informative: the native-only work exactly reproduces P3, while propagated metadata sharply reduces pair work. A mere timer artifact cannot explain this deterministic operation-count change. The reduction 17,670→624 is ~96.5% in this corpus's summed pair terms, not a universal complexity bound.

Raw case-balanced timing ratios, each optimizer divided by its simultaneous direct baseline:

| Phase | Lowering only | Construction + lowering | Cases faster end to end | Natural accepted folds |
|---|---:|---:|---:|---:|
| P4 | 0.5752 | 2.2259 | 3/36 | 0 |
| P5 | 0.6544 | 1.2898 | 8/36 | 0 |
| P6 | 0.6641 | 1.2444 | 7/36 | 0 |
| P7 | 0.6671 | 1.3052 | 6/36 | 0 |

These do not measure the same machines' timeless implementation constants; they are historical within-experiment comparisons. P4/P5 lower-only ratios exclude metadata construction by design. Construction-inclusive measurements clone an existing source DAG through a fresh factory and lower it; they exclude BLIF parsing, original expression generation, input I/O, oracle construction, digest serialization, and truth conversion. They should be described as DAG-materialization/compilation pipelines, not file-to-result application latency (`P04/n2_p4_harness.py:426`; `P06/n2_p6_harness.py:440`).

N1 and P1 have different timing boundaries. N1 natural cold runs include parsing, support discovery, oracle work and correctness in a single wall interval (`03_N1_BASELINE/n1_gatep_harness.py:546`). P1's Gate-P schedule times `run_arm` externally, so `elapsed_ns` includes truth conversion/digest/reporting; direct is not a Gate-P timing arm in P1 (`P01/n2_p1_harness.py:40`, `:374`). P2/P3 explicitly retain compile-only components. Historical “speedup across versions” must not substitute unlike endpoints.

## Baseline fairness findings

1. **Timed reporting overhead is material and unequal in amount.** `base.update_peak` scans every polynomial with `max(m.bit_count() for m in p)` (`03_N1_BASELINE/n1_gatep_harness.py:433`). Many branches call it inside an operation and again after memoization. `mul_poly` increments counters even in ordinary timing. This is shared code, but direct's extra intermediates incur extra observer work. It does not falsify lower arithmetic counts, but can inflate their runtime consequence.

2. **CM pays an unnecessary traversal even when reporting is disabled.** `P06/n2_p6_harness.py:253` constructs `P6Stats(output_unique_nodes=base.reachable_nodes(root))` before checking `collect_stats`. Equivalent unconditional calls exist in P4, P5 and P7. Direct computes its reporting traversal after the lower timer. This disadvantages CM and directly contradicts a literal claim that the P4+ timed lowerer performs no source scan. The prohibited scan is unnecessary for decisions, but it is still executed for the statistic.

3. **P7 is not strictly a storage-only runtime ablation.** `P06/n2_p6_harness.py:343` updates `ast.peak_cache_entries` for every node; `P07/n2_p7_harness.py:301` omits it. P7 also omits `update_peak(q)` inside an `orn` reduction level. The principal benchmark work metrics remain equal, and normal generated sources do not require `orn`; nevertheless P7/P6 elapsed time has a small extra code difference. Their “mandatory equivalence” lists do not include peak cache entries, so the check misses this.

4. **Ordinary interning is deliberately weaker than common commutative CSE.** Source argument order is preserved. The frozen late dispatch requires at least five shells for one canonical unordered pair; with only AND/OR/XOR and canonical operand ordering, an interned factory can have at most three such unique shells. Thus this predicate targets representational duplication as well as algorithmic opportunity. Canonicalization is a new baseline experiment, not an allowed change to an exact P13-equivalence telemetry test. The sibling pure-Python audit independently tested this on all 36 cases: 5 annotated cases→0 under frozen gate, yet always-P6 still greatly reduces pair work. Its `python_diagnostics/dispatch_diagnostics.*` holds the results; do not mistake a failed frozen detector for a failed fold mechanism.

5. **Direct sparse ANF is a legitimate but basic baseline.** It lacks product caching shared across AND/OR on the same operands, trivial polynomial zero/one cases, and `P*P=P` in the Boolean polynomial quotient. It uses recursive dictionaries despite dense node IDs. It supports no generic cut or semantic-node canonicalization. Stronger versions should share their kernel improvements with folded arms, including any early exits, memo policies, statistics settings and conversion costs.

6. **N1 generic is semantically inclusive, not an unrelated stronger compiler.** `fold_frontend(mode='generic')` executes the same same-pair token composition as CM, then tries primary-support<=2 retabulation (`03_N1_BASELINE/n1_gatep_harness.py:254`, `:296`). It adds support discovery and evaluation costs. Beating that arm's runtime alone can mean avoiding its extra exploration, not gaining a uniquely CM transformation. Its P1 raw summed pair work is 10,299, versus CM unconditional 10,435 and P4 propagated 624. The architectures and selectors differ, so this does not rank fully optimized generic versus CM strategies.

7. **Which metadata are incremental depends on the input contract.** Dense node IDs, op tags, child references, and structural interning keys already exist here. A compiler may also already maintain fanout, but this factory does not; charging its construction is correct under this contract. Source pair groups, pair multiplicity, frozen dispatch feature ratios, structural ANF estimates, and propagated truth signatures are additional unless a documented host IR actually supplies them. An “available for free” scenario must explicitly provide these to every arm or report amortization over reuse.

## Concrete untested improvements

These should be separate arms, not silently installed into historical results:

| Priority | Exact site | Proposed change | Effect/semantic impact | Preregistration consequence |
|---|---|---|---|---|
| High | N1 `lower_anf`, `mul_poly`, `update_peak`; P6 `lower_p6` | Separate production timings from ANF and selector counters, including unconditional reachable-node count | Same polynomial and decisions; timing no longer includes symbolic audit work | Freeze identical stats policy for both arms in new timing protocol |
| High | N1 `Factory.bin`, `_make` | Canonicalize operands for commutative operators with identical local identities | Same Boolean function; different DAG, fanout, dispatch/features and work | New baseline/corpus-view protocol; frozen P13 dispatch should be reported separately |
| High | P6 `lower_p6` accepted branch at line 311, P3 `apply_tf_poly` at line 103 | Inspect ANF coefficient mask before demanding base A/B; constants need neither, projections need one | Same function, fewer demands/folds/work; require reporting new counts | New optimizer arm; frozen decision equivalence no longer the right requirement |
| High | N1 `mul_poly` at line 423 | Matched zero/one/idempotence shortcuts and memoized repeated source-pair products | Same polynomial, lower work; compare cache/allocation overhead | New shared ANF-kernel arm, not optimized-only change |
| Medium | P4/P5/P6 `_make` and propagation | Propagate complemented token through general NOT, supported by Boolean identity | Same function, more candidates; negate token with XOR15 | New candidate policy, correctness and natural-firing holdout |
| Medium | P6 `lower_p6` memo, N1 direct memo | Dense-ID memo list with sentinel distinct from empty polynomial | Same results/demand decisions if implemented faithfully; may allocate more | Representation ablation with equal setup/allocation charging |
| Medium | P4 `_candidate_from_children`, P6 `_propagate_pair` | Retain a small cut frontier or canonical semantic `(pair,token)` identities | More opportunities, more metadata; not essentially free | New search budget and corpus/discovery split required |
| Low initially | Token kernels | Specialized implementations for all16 functions; factor shared intermediate products | Same result, possible allocation savings, extra code complexity | Freeze lookup table and shared direct/optimized applicability |

The coefficient-directed demand optimization is already present in the supplied Gate-A predecessor: `gatea/Computation_and_Benchmarks/src/cmbench/anf.py:196` only visits operands whose linear or nonlinear coefficient is set. P-series `p3.apply_tf_poly(composed, rec(a), rec(b), ast)` eagerly computes both arguments even for constant/projection tokens. Thus this is a concrete, previously available implementation improvement, not generic speculation.

## P7B correction and remaining caveat

Read `P07B/P7B_TIMING_CORRECTION.md` and the corrected `run_dispatch` at `P07B/n2_p7b_harness.py:102`. The fixed time is `probe_ns + selected_backend.pipeline_ns`; the wrapper includes verification/conversion and is stored separately. Threshold selection used the sum-of-components model already, so the stated explanation for retaining T=17 is internally consistent. The immutable gate's original validation summary must not be read as corrected validation; `validation_corrected.json` exists for that purpose.

The correction does **not** align memory endpoints. `run_dispatch` starts `tracemalloc`, calls the whole backend wrapper with `memory=False`, and stops only after its truth conversion, digest and reporting have finished. Direct/P6 memory timing stops before these operations. Consequently P7B dispatch peak memory is not a strict same-boundary comparison, even though pipeline time is corrected. This should be corrected in a new run or clearly annotated in any publication table; existing files should remain preserved.

The probe computes full reachable fanout, per-pair sets of tokens, pressure, and shell count (`P07B/n2_p7b_harness.py:65`). No threshold-specific early exit occurs. Calibration therefore correctly shares one threshold-independent probe timing despite preregistration wording about per-threshold timing. The corrected report's failed policy result is consistent with the implementation: substantial probe overhead is paid even for abstention, and pair pressure does not estimate the ANF work that would be avoided.

## Gate-A and pinned repository context

Independent CSV reconstruction (`mechanism_raw_check.json`) finds 10,500 attempted rows, 10,389 all-arm admitted rows, 3,750 S1 and 6,639 S2. There are 111 nonadmitted rows: 108 with no successful arm, plus three with partial success. No admitted independent-evaluator failure or S2 exact-support failure is recorded. All admitted CM/generic digests and three principal symbolic metrics match exactly. This confirms the negative CM-specificity result without relying on its summary.

S1 is a two-primary-variable fold ladder; S2 adds a parity support guard around a mixed core. The corrected S2 construction does guarantee the requested semantic support: the core starts with degree>=2 atoms, and Boolean polynomial addition/multiplication of polynomials without degree-one monomials cannot create a degree-one monomial, so the explicitly added parity terms survive. That support guarantee also makes S2 a specific synthetic distribution, not representative random real-world circuits. Budget failures must remain visible; admissions alone are not the whole workload population.

`generic_2support_frontend` uses the same local composition primitive as CM plus retabulation (`gatea/.../src/cmbench/optimize.py:181`). Its docstring calls the support semantic, but the implementation computes the union of child variable sets at line 213; this is syntactic support, potentially an overestimate after cancellation. It does not enumerate all internal two-boundary-node cuts. Therefore “strong generic comparator” should name the precise method rather than imply state-of-the-art synthesis.

The public snapshot at commit `1145537c9e2274ae7622dad5b68a7d612b27bb7e` includes a materially stronger structural candidate:

- `pinned_repository/cmbench/recognition/cut_fusion.py:235`, `optimize_cut_fusion`, enumerates bounded cuts of up to two structurally identified compound expressions, propagates through NOT, uses a frozen minimum-template pool covering all16 functions, and tracks cut interiors to avoid invalid dependency lifting.
- It conservatively rejects shared cut interiors (`:344`) and accepts only whole-program reductions of at least two executed bigint ops and 10%, with no increase in peak live word buffers (`:404`). This is sharing-aware and stronger in search scope but may reject profitable P-series shared folds.
- Its output/cost contract is packed-vector CSE/CM programs, not sparse ANF. A fair comparison must charge conversion/preparation and lower all candidates through a common ANF backend, or report separate vector-evaluation results. Simply quoting its bigint savings is not an ANF comparison.
- `pinned_repository/cmbench/recognition/exact_dispatcher.py:11`, `:49` chooses among set ANF, cached packed-source ANF and truth-vector→ANF using bounded structural product estimates. This broadens reasonable competitors: for support8–12, dense truth-vector plus Möbius transform is a natural artifact-equivalent alternative if all conversion costs are included.
- `pinned_repository/cmbench/recognition/computation_experiment.py:436`, `:486` distinguishes direct, CSE, CM IR and explicit truth-relation tasks and charges candidate generation/verification where applicable. These contracts are useful templates, not performance results for the P-series corpus.

Natural P1 selection takes the smallest and largest admissible BLIF cones by `(source_nodes,depth,root)` with support9–12 and at most128 LUT nodes (`P01/n2_p1_harness.py:263`). This is deterministic and not selected on timing/fold incidence, but it is small and biased toward size extremes. Zero accepted folds in ten repeatedly reused cones means this sample measures abstention overhead. It does not prove that larger arithmetic/control networks lack profitable cut structure. Use whole-circuit/family splits before searching for natural firing cases, report prevalence among all sampled cones, and keep the firing stratum predeclared by structural features rather than measured wins.

## Exploratory diagnostic delivered

`stats_free_diagnostic.py` performs no timing. It constructs independent namespace copies and uses an auditable AST transformation to remove ANF statistics writes, calls to `update_peak`, disabled selector-reporting blocks and the unconditional reporting-only reachable-node traversal. Actual algebra, sharing/benefit conditions, source objects and original modules remain unchanged. It retains empty statistics containers solely to preserve APIs. Generated functions, unified diffs, source hashes and a list of removed statements are in `stats_free_generated/`.

`stats_free_verification.json` records 92 fresh cases: 80 seeded random formulas and12 separately generated Gate-P examples at depths2/4/6/8, seed20283281. Original direct, transformed direct, original P6 and transformed P6 produced equal exact polynomial sets, and transformed outputs matched the bitset oracle in every case. This is bounded exploratory correctness evidence, not a timing claim or new preregistered result. The root auditor controls any timing session to avoid concurrent benchmark interference.

## Inspection checklist and limits

Successfully inspected primary implementation hot paths and timing wrappers in all nine requested early files: N1, P01, P02, P03, P04, P05, P06, P07, P07B; also N1 sharing diagnostic, P7B timing correction, P1–P7B preregistration sections, P4 independent verification script, P5/P7 profile excerpts, P1–P7 combined raw results, P7B corrected-wrapper/source and result/schema evidence, natural selection implementation, the operator manuscript text (especially semantic and scope sections), Gate-A optimizer/backend/generator protocol/runner and full raw combined CSV, and the pinned cut/computation/exact-dispatcher implementations.

Inspection is not a full execution of every archived test/harness or an independent rerun of historical timing; the new run is the92-case ablation correctness check. P08–P13, the six full BLIF input files, late profiles and overall statistical analysis are assigned to sibling/root auditors. This report does not claim those files were read by this sub-auditor. The user's phase PDF is optional mathematical context and is outside this bounded contribution.

## Research implication

The strongest positive finding is that propagating correct low-dimensional semantic information through locally unprofitable regions can prevent very expensive intermediate ANF expansion. That mechanism survives the critique that CM notation is unnecessary. The strongest surviving alternative explanation is narrower: observed runtime ratios combine useful contraction with Python interpreter/counter overhead, source representation choices and a highly favorable repeatedly reused workload. The next decisive experiment should freeze a fair production ANF kernel and a commutatively canonical source view, benchmark propagated versus equally informed generic contraction, and evaluate on fresh structural holdouts. Compiling telemetry may then be a useful engineering ablation, but freezing the existing orientation-sensitive policy in C does not by itself answer whether the optimizer is robust or broadly useful.
