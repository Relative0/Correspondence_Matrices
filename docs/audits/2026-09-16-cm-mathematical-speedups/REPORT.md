# CM mathematical speedups: decision and research program

Date: 2026-09-16. Status: research complete; **PROCEED with one bounded Phase-2 experiment**. No optimizer, production change, performance promotion, commit, or cloud run is part of this investigation.

## Decision

Test **two-opaque-operand cut fusion, with exact four-bit truth tokens and lowering to existing flat primitives**. The opportunity is fewer Boolean operations over the same packed truth vectors. It is not a new execution engine, a general canonical form, or a claim that CM matrices outperform bitsets.

The current pair compiler understands signed variable pairs, while the general CM builder performs structural interning and a limited collection of Boolean identities. Neither performs general bounded cut composition over two arbitrary compound operands. A separate proved-rule pack already rewrites compound operands, including XOR macros, De Morgan OR, and common factors. The proposed mechanism must therefore outperform that pack as well as plain CSE and CM-IR. Its distinction is composing all truth functions on a bounded cut without successive pattern-matching passes. This is established logic-synthesis territory, especially DAG-aware AIG rewriting [L1]; the research question is whether this implementation and lifecycle can profit from it.

**Evidence:** exhaustive finite checks found no disagreement; a static census on exposed data found 2,310 cut shells cheaper than their current CM lowering, and 1,821 still cheaper after the existing one-pass rule pack followed by the better of CSE or CM lowering. These are overlapping, local opportunities, not realizable summed graph savings. All positive cases were EPFL: 61/64, versus 0/18 C36. No runtime speedup was measured.

Exactly one implementation candidate is selected. Two conditional longer-term directions survive: resident knowledge compilation for a genuine count/restriction consumer, and hierarchical decision diagrams for supplied repeated modules. Both are **DEFER**, with prerequisites below. Wider cut synthesis, decomposition searches, tensor backends, new ANF routing, incremental campaigns, and learning are not authorized follow-ons to this decision.

### Deliverables

- [Ranked candidates and complete cost/contract table](CANDIDATES.md).
- [Frozen Phase-2 experiment and stop rules](PHASE2_SPEC.md).
- [Copy/paste implementation prompt](IMPLEMENTATION_PROMPT.md).
- [Executable static probe](probe.py), [original evidence](probe-results.json), [additional shell verification](probe-results-verified.json), and [rule-pack-controlled evidence](probe-results-pack-control.json). Earlier observations are retained rather than rewritten.
- [Artifact verifier](verify_audit.py) and [final verification manifest](audit-verification-final.json).

## 1. Scope, custody, and current-state reconciliation

All work stayed in `C:\Users\brian\.codex\worktrees\1949\CM_Computation`. Preflight found detached Codex-managed HEAD `015f5cbb70b112795c08b61c27924c1ee752b9e9`, identical to local `codex/cm-final-consolidation-20260916`. After a successful authorized fetch, `origin/main` was `e35f352a2036db403f5e28ecca2f61550d1db0c7`, an ancestor exactly three commits behind. The worktree was clean before this audit. Fetch initially hit the shared Git metadata sandbox and succeeded through the normal escalation tool; no permission setting was changed.

Read the deep technical dossier, performance audit, remaining gates, continuation dispositions, post-C38 architecture disposition, learning decision surface, both original speedup reports, IR cost report, September 2 investigation prompt, typed semantic specification, formal proof package, and literature matrix. Also checked the later integrated continuation, September 15 attribution/family repairs, overnight assurance, local consolidation, and D5/D7/D9 proved-rule studies. These are historical evidence, not interchangeable current-source descriptions.

Current source was inspected in `cm_build.py`, `cm_normalize.py`, `cm_build_pair.py`, `cm_token.py`, `cm_ir.py`, `bitset_backend.py`, and the relevant comparative, recognition, affine, bucket, and projection modules. Important reconciliations:

| Surface | Current finding | Consequence |
| --- | --- | --- |
| Pair compiler | `_signed_operator_pair` recognizes signed literals; recursive pair composition fuses compatible named row/column frames. Hybrid fallback retabulates a sufficiently small live variable pair. `structural` is a historical alias for hybrid. | Compound-operand cuts are not already a general pair-compiler feature. Do not describe hybrid retabulation as pure structural compilation. |
| Pair axes | Names must be distinct across row/column layout; token axes and dense matrix axes require explicit conversion. | Two occurrences of the same variable cannot be treated as two independent layout axes. |
| CM builder | Structural UID memoization is the default; compact child-UID intern keys and cached node hashes already exist. Public nested keys remain. Sharing-aware associative flattening protects multiple consumers. | Generic interning, cached hashes, and compact-key proposals largely repeat completed work. |
| CM identities | AND/OR constant, duplicate and complement rules; XOR parity rules; IMP/EQV special cases. No general distributive cut solver. | Residual semantic simplification can exist, but must be checked against current lowering. |
| CSE compiler | Iterative structural hash-consing, with ordered child IDs; optional associative flattening. | Structural equality does not identify all functionally equal shells. CSE remains a strong cheaper compiler. |
| Flat execution | CM and CSE lower to the same `FlatProgram` executor. `program_metrics` distinguishes instructions, argument edges, actual word/bigint primitive operations, and live buffers. | A smaller AST or one LUT instruction is not evidence of less executable work. Equal normalized plans supply no CM kernel advantage. |
| Masks/preparation | Periodic byte masks replace the older NumPy-generation avenue; prepared/bound execution and bounded caches exist. September repairs reuse the sharing prepass and wrapper plans. | Do not reopen mask caching, generic resident caching, or wrapper reuse as new mathematical mechanisms. |
| Scalar queries | Factorized, affine, bucket and projected count plans and explicit session adapters exist. Projected counting eliminates hidden variables existentially before selected-variable summation. Dynamic residual-component counting also exists. | “Add projected counts/component caching” is already implemented. A distinct plan must beat these APIs and native controls. |
| Rule rewriting | One-pass proved rule pack, exact cone cache, bounded fixpoint normalizer, calibrated profitability gate, and D10 indexed mux/comparator/carry/XOR motifs exist. | Arbitrary compound metavariables, cheap structural screens and proof-carrying pattern rules are prior work, not this proposal's novelty. |

The latest continuation [R4] supersedes old lists that called projection an unimplemented next step. The overnight assurance [R8] permits reopening only for a changed matched plan or real consumer trace. This proposal satisfies the first condition only as a testable hypothesis; it has not yet established a globally cheaper normalized plan on the census.

## 2. The representations and their contracts

| Representation | What it denotes or stores | What its compactness does and does not buy |
| --- | --- | --- |
| Mathematical CM | An exact Boolean relation, indexed by declared row and column assignments, or a local Boolean operator on operand values. | Algebra specifies semantics independently of storage. Renaming this relation does not remove its information content. |
| Dense generalized CM | A Boolean array over explicit ambient axes, with normalization, lifting and permutation. | Already materializes the truth relation; broadcasts/copies and axis ownership matter. A NumPy Boolean generally uses a byte per entry. |
| Packed truth vector | The same ordered truth relation, stored in bits, e.g. Python bigint or words. | Bit parallelism applies the same primitive to many valuations. Payload still has `2^k` bits. |
| CM-IR | Interned symbolic DAG with CM builder identities and support metadata. | Can remain small when the relation is huge, but is not canonical for arbitrary semantic equivalence. Building it is not dense CM construction. |
| CM-flat | Ordinary flat instructions obtained from CM-IR. | Execution speed depends on resulting primitives, sharing, buffer lifetime and bindings, not on the CM name. |
| Structural CSE-flat | Flat DAG from structural common-subexpression elimination, optionally flattened. | Usually cheaper preparation; no general semantic quotient. It can produce the same program as CM-flat. |
| Query-specific symbolic plan | BDD/SDD/d-DNNF, factorized count plan, affine system, tensor/elimination plan, etc. | May answer count, SAT, restriction or equivalence without enumerating the relation. It changes the output contract unless full materialization is also performed and charged. |

For `k` unfixed ambient Boolean variables, emitting every relation value requires `2^k` bits of information in the worst case and at least `ceil(2^k/W)` machine-word writes. Packed serialization needs `ceil(2^k/8)` bytes; dense byte-valued output needs `2^k` bytes. A tiny circuit, token, or diagram is a compact *description*, not delivery of those entries. Compression can improve compilation, scalar queries or constant factors while leaving this output lower bound intact.

Count, SAT, a witness, a restricted relation, and equivalence are separate contracts. Count does not enumerate witnesses. A full model count over Tseitin variables is not generally a count of original assignments without a suitable unique-extension or projection argument. Projection counts distinct selected assignments even if each has many hidden witnesses. A restriction fixes variables; it is not existential projection.

## 3. Lifecycle and break-even rules

Every candidate is evaluated under

`total(q) = parse + compile + bind + q × execute + output`.

Here `bind` is one-time plan/environment setup. Per-request context validation and binding belong inside `execute`; output includes every required conversion, axis expansion and delivered byte. If the requests differ, replace `q × execute` with their measured sum. Separate timing fields must add to total wall time within declared measurement error; cold import/process startup is reported separately and included in a fresh-process scenario.

Let `H = parse + compile + initial bind + one-time output` and `d = per-query binding + execution + per-query output`. For two methods with stationary workloads and `d_new < d_control`, strict break-even is the smallest positive integer `q` satisfying

`q > (H_new - H_control) / (d_control - d_new)`.

If steady-state execution plus required per-query output is not faster, there is **no finite amortization break-even** for extra setup. A method with cheaper setup could still win small one-shot cases; that is a different claim. Cache hits cannot erase the original setup when a session owns that cost. Fixed-output memoization must be a comparator when the same output is repeatedly requested. Do not infer a smooth threshold from q1/q4/q16/q64 or pool incompatible contracts.

The estimates in [CANDIDATES.md](CANDIDATES.md) are symbolic hypotheses, not measurements. Factors such as Python dispatch, bigint allocation, memory bandwidth and arbitrary-precision count arithmetic can dominate. A primitive count is a causal intermediate, not a latency forecast.

## 4. Mathematical opportunity: operand-frame composition

Let `A` and `B` be any pure total Boolean expressions on physical assignment `x`. Define a four-bit token `T` by its values on operand assignments `(1,1), (1,0), (0,1), (0,0)`, and write

`C_T[A,B](x) = T(A(x), B(x))`.

For a supported binary Boolean operator `Θ`, define pointwise token composition

`R(a,b) = Θ(T(a,b), U(a,b))`.

Then, by substitution,

`Θ(C_T[A,B](x), C_U[A,B](x)) = C_R[A,B](x)`.

This proof needs neither independent operands nor disjoint supports. It holds when `A=B`, `A=NOT B`, or their source variables overlap. It is exact on all four abstract operand valuations, which is stronger than equality on only reachable operand pairs. A swapped or complemented frame is usable only with the corresponding recorded permutation/polarity transformation of its token.

**Recognition rule:** identity of the ordered operand nodes must be established by exact structural IDs or explicit equality proofs. Equal support, equal tokens in different frames, matching hashes without equality, or belonging to the same NPN class do not prove expression equality. Compatible cuts can be composed when their leaf union has at most two exact IDs. A cut boundary is a small set of intermediate signals, not a claim that the whole formula has support two.

Examples with compound `A` and `B`:

- `(A AND B) XOR (A OR B) = A XOR B`.
- `(A ⇒ B) AND (B ⇒ A) = EQV(A,B)`.
- `(A AND B) OR (A AND NOT B) = A`.

The third identity is already recovered by the existing common-factor rule followed by CM identities. It is a semantic illustration and overlap control, not evidence of a new opportunity.

A token denotes one of 16 functions, but there is no hardware or Python guarantee that evaluating it is one cheap instruction. Lower it into a proved template of existing primitives. In the current bigint executor NOT costs two bitwise operations and IMP/EQV three; words have different costs. Compare the replacement against the actual backend's lowering. Our probe chooses the cheapest *among its enumerated templates*, not a globally optimal circuit. In particular, its NAND/NOR entries could be improved by additional templates; no optimum-synthesis claim is made.

Graph economics are separate from local Boolean algebra. Replacing a shared interior does not delete it if another consumer remains. Count actual removable nodes, added nodes, surviving loads and peak live buffers on the whole resulting program. A bound on cut count alone does not bound repeated walks through large shells. The Phase-2 cap therefore also bounds shell size, visits, rewrite count and rebuilds.

## 5. Exact probes and limitations

Executed `probe.py` with Python 3.10.11 on the current Windows host. No project virtualenv was present. Results:

| Check | Result | Interpretation |
| --- | ---: | --- |
| 16 tokens × 16 tokens × 5 operators × 4 operand valuations | 5,120 checks, zero mismatches | Exhaustive local composition table check. |
| All two-input physical truth maps for A and B, all token pairs/operators/assignments | 1,310,720 checks, zero mismatches | Explicitly includes dependent, identical and complemented operands; repetitions do not establish workload diversity. |
| Exact packed evaluation of every audited rebuilt shell | All agree with propagated token | Independent path through the existing expression evaluator checks alignment. |
| EPFL exposed census | 64 cases; 10,146 source nodes; 61 cases with residuals | 2,310 local cut residuals versus CM; maximum shell saving 12 bigint operations. |
| Additional one-pass rule-pack control | 1,821 residual cuts in 61 EPFL cases | Must still test whole-graph scheduling, fixpoint control and setup cost. |
| C36 exposed census | 18 cases; 1,224 nodes; zero residual cuts | Required negative activation control, not dropped from reporting. |

For `A = x0 AND x1`, `B = x1 XOR x2`, the complete analytical replacement comparisons are:

| Shell | Original CSE/CM bigint operations | Replacement operations | Original/replacement flat instructions | Original/replacement live word buffers | Existing one-pass pack then CM |
| --- | ---: | ---: | ---: | ---: | ---: |
| XOR of AND and OR | 5 | 3 | 5 / 2 | 4 / 2 | 5 operations |
| Mutual implications | 9 | 5 | 5 / 3 | 4 / 3 | 9 operations |
| Eliminate B | 7 | 1 | 6 / 1 | 4 / 1 | Already 1 operation |

These are static program metrics; no timing was taken. If the simplified function drops `x2`, ambient output must still duplicate across its declared axis. Semantic support shrinkage does not authorize changing output dimensions.

The census keeps at most eight nontrivial cuts plus the self cut per node, with deterministic truncation. It requires at least one compound leaf and rejects shells with externally shared interior nodes other than the root. It does not optimize the graph. Cuts overlap, original source IDs are not a complete semantic quotient, and whole-root CM or fixpoint rewriting can remove opportunities that survive isolated-shell analysis. The additional D10 indexed motif engine was inspected but not run in this census; its control is mandatory in Phase 2. The exploratory shell walks/recompilations can be quadratic; this code is an audit probe, not the proposed efficient pass. The future 32-node shell cap was not imposed on this census, so its activation rate must be remeasured under that cap.

The corpus was already exposed. Its actual on-disk bytes and source dependencies are hashed in the evidence; no historical validator was weakened. The first artifact records the initial probe; the second adds shell truth verification; the third adds the rule-pack control. Shared fields agree. These runs do not constitute independent confirmation or three performance repetitions.

## 6. Why the other mathematical avenues do not displace this experiment

### Functional decomposition and width

For a partition `(X,Y)`, form rows `f(x,Y)`. If there are `ρ` distinct rows, a bound-set encoding requires at least `ceil(log2 ρ)` bits, and encoding the row class attains that information bound. It does not make the encoder cheap to discover or evaluate. Ashenhurst-style decomposition [L3,L4] and disjoint-support decomposition [L5] are appropriate antecedents. Exact BDD cofactor sharing can expose structure, but constructing a large truth table first loses the hoped-for source-side advantage.

Separator conditioning enumerates at most `2^s` separator assignments and combines independent components. Low separator width can replace whole-support exponential work with exponential work in width. It is already represented by bucket/projected/component controls. A new implementation must change the plan or exploit a new trace, not just rename connected-component factoring.

### Knowledge compilation

ROBDDs give canonical equality at a fixed variable order, and exact restriction/counting on the diagram [L6]. Building the diagram and finding a useful order may be the entire problem. d-DNNF allows efficient counting when decomposability, determinism and variable accounting are preserved [L7,L10]. Existential forgetting can destroy determinism; projected counting is not automatically ordinary d-DNNF counting. SDDs use a fixed vtree and have useful structural bounds [L8], but compressed canonical SDD Apply is not uniformly polynomial [L9]. Never collapse these into “all symbolic queries become cheap.”

CFLOBDDs represent hierarchical repetition and can be exponentially more succinct than same-order BDDs on special families [L11,L12]. The 2026 discussion of “linear structure” means composition of diagram fragments, not affine GF(2) equations. Benefit requires repeated function modules and a compact query/output contract. ZDDs are attractive for sparse families of sets [L13], but Boolean complement, projection, and variable-universe conventions must be explicit. Sparse truth assignments, sparse ANF monomials, and sparse CNF are different properties.

### Algebraic normal form and GF(2)

ANF is the unique multilinear polynomial over GF(2). Addition is XOR; multiplication is AND with `x²=x`; OR is `a XOR b XOR ab` [L14]. A sparse polynomial may be cheaper for assignment evaluation or equality, and affine constraints admit rank-based satisfiability/counting. Multiplication can make a sparse representation dense, and truth-to-ANF conversion already touches exponentially many coefficients. Exact affine plans and packed/source ANF recognition already exist here. M4RI-style elimination [L15] may accelerate a necessary dense rank kernel; it does not justify screening every partition or change the output contract.

### Exact matrix and tensor structure

Do not conflate the following:

| Structure | Exact semantics | Useful query | Trap |
| --- | --- | --- | --- |
| Repeated/complement cofactors | Dictionary of equal/complement row functions | Compact restriction/equivalence and shared evaluation | Finding the dictionary by full enumeration may cost the output already. |
| GF(2) rank factorization `M=UV` | Each entry is parity of component products | Compact entry evaluation, rank/algebra tests | Sum of factors counts parity contributions, not Boolean models. |
| Boolean-semiring factorization | Entry is OR of AND products, a biclique cover | Existence/membership, possibly compact relation | Overlapping rectangles double-count; exact small covers can be hard [L18]. |
| Disjoint Boolean product / Kronecker factors | Separate variable sets combined by AND | Counts multiply; restrictions factor | Unused variables and overlap must be accounted for. |
| XOR of disjoint component functions | Parity composition | Counts from signed imbalances | Independence of variable sets is essential for product formula. |
| Exact integer/rational tensor factors | Ordinary sum/product with exact cancellation | Model counting through contraction | Width, intermediate size and integer bit growth determine cost. |
| Numerical low-rank approximation | Approximate entries | Approximate tasks only | SVD error tolerance is not an exact Boolean certificate. |

For disjoint components with `n_i` variables and `c_i` satisfying assignments, their XOR count is `(2^(sum n_i) - product(2^n_i - 2c_i))/2`, with a further power-of-two factor for unused ambient variables. This derivation uses independence; it does not apply to arbitrary low GF(2) rank. A rank-r GF(2) matrix has at most `2^r` distinct rows, but rank and the number of cofactor classes are different invariants.

Exact tensor contraction reorganizes variable elimination [L16,L17]. Boolean OR/AND contracts existence, GF(2) contraction returns parity, and integer sum/product can count models. Mixed existential and counting elimination requires the correct order. Tensor train SVD [L19] is a numerical compression method, not an exact CM algorithm. Replacing it with exact field elimination still leaves rank growth and extraction cost. A rank certificate alone does not establish a cheaper full relation or projected count.

### Adaptive selection and incremental reuse

A deterministic dispatcher is justified only by verified sufficient conditions and fully charged cost. Learning predicts profitability; it cannot prove semantics. A learned proposal needs exact checking plus an incumbent fallback. Current data lacks the retained, source-blind, materially winning arms required by the existing gate. Incremental dependency tracking [L20] can avoid work when identities and changes are known, but source identity validation, invalidation and retained memory must be paid. Existing structural cone caches, resident plans and the failed changed-cone campaigns are direct controls.

## 7. Historical failures remain binding evidence

| Prior avenue | Retained result | Constraint on this program |
| --- | --- | --- |
| CM vs CSE execution | B1/E3 plan/kernel parity; a historical bare-kernel CM/CSE ratio 0.89057 coexisted with public-wrapper ratio 3.094136. | Require lifecycle and exact contract, not selected kernel ratios. These numbers are historical, not current measurements. |
| C6 ANF hybrid | Packed core 1.31–1.64× medians; hybrid tail gate missed by about 1.4%. | Faster representation kernel is not a passed router/learning result. |
| C16 screen-before-payload | Same deterministic best artifact; about 3.55× Windows / 3.18× Linux. | Payload deferral succeeded; all bounded partition descriptors were still evaluated. |
| C21/C34 ranking | Same exact-best completion; oracle headroom about 1.059× / 1.0035×. | Ranking without omitted certified work has little value. |
| D5 rule pack | Fresh 0.679×, cached 0.879×, gated 1.030× sequence; cold gated 0.834×; q128 gated 1.167×. | Two-operand fusion must earn its recognition/rebuild cost and compare against the pack. |
| D7 fixpoint | One pass 1.050×; fixpoint 0.805× despite extra valid contractions. | More simplification is not necessarily worthwhile. No saturation retry. |
| D9 learned rule policy | 0/33 applications; all abstain; 0.9818× gate, 0.4290× unconditional pass. | Operation reductions and exact proofs alone did not produce useful profitability. |
| D10 indexed motifs | Indexed 0.2747× overall, 0.2417× on motifs, 0.4455× on no-op controls; free oracle 1.0000×. | Cheap screening and synthetic wrapped motifs already failed. A1 needs natural whole-plan savings and cheaper integrated composition, not another general matcher or per-instance dense CM proof. |
| H1/H2/H3 | Sharing repairs landed; compact keys already present; later exclusive-key and dense shares about 7.878% and 3.886%, below gates. | No generic key/dense rewrite campaign. |
| C37/C38 / native execution | Fresh cases about 0.933× vs earlier 1.328×; CSE bigint strongest overall 54-case control; Linux native minimum 0.840× failed floor. | Keep host-specific opt-in evidence; no universal backend or q threshold. |
| Native batch | q96 about 1.078×, below frozen 1.10 gate. | Do not retry with the same work and a lower threshold. |
| Incremental / hardware histories | 3/42 active confirmations and adverse resources; later hardware 0/42 active. | Require a new preregistered active history and consumer before reopening. |
| Projected bucket / arrays | 48-variable adjacent case: Python 28.455 ms vs CUDD 10.127 ms; hidden stars refused; public native timeouts retained. | Projection is implemented, with explicit unfavorable controls. |
| Disk reuse and streaming | Checked JSON reload slower than compile; real pipe memory improvement did not establish throughput gain. | Resident lifetime and output delivery need measured contracts. |
| Later assurance / domain controls | September 15 replay found no new correctness disagreement or new CM mechanism; biology/SymPy matched studies remain no-go. | No blanket new-domain benchmarking. |

The current learning gate requires at least two materially winning exact arms, usable labels at least 80% overall and in each split, source-blind 16/8/8 groups with at least eight groups per label, stable results on two physical hosts, and at least 1.10× fully charged gain on both with feature/inference/verification/fallback costs. No eligible retained dataset was established here. Training is **STOP** under present evidence.

## 8. Verification and final disposition

The corrected focused pytest selection ran 72 tests: **71 passed, one historical corpus-hash failure** in `test_normalization_experiment_slice_is_exact_and_bounded`. The earlier command referenced a nonexistent `tests/test_cm_ir.py`; it collected no tests and was corrected. The actual run covered pair alignment, bitset execution, CSE, IR costs, wide associative IR and normalization experiment tests.

The failed test expected SHA-256 `bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac`. The checked-out CRLF file hashes to `a834c98d04ceb00b0017d1c93816596c8da4d1cbc6409045103e17f31a226744`; converting CRLF to LF in memory exactly equals the HEAD Git blob and its expected hash. No corpus file or validator was changed. This is a pre-existing byte-identity mismatch on this checkout, not a failed Boolean equality test.

After adding the rule-engine controls to the research, `tests/test_rule_normalization.py` and `tests/test_d10_rule_engine.py` produced **9 passed, 4 subtests passed, one historical fixture-hash failure**. The D10 source-backed smoke test rejects `docs/recognition/source_fixtures/yosys-bench-human-decomposition-20260830/LICENSE.txt`: working SHA-256 `44d054188ebd92dbbd86093849ae6779e937bd7e719269b05e2a459690740293`; expected and HEAD-blob SHA-256 `4722e5e40d884575cf601b2eb63904778e66822b5db2d0c4bab7affcdddbd954`. Its CRLF-to-LF conversion also exactly matches the Git blob. Combined focused result: **80 passed, 4 subtests passed, 2 pre-existing byte-hash failures**. Neither historical fixture was changed.

The package verifier checks current source hashes, agreement among retained probe artifacts, aggregate counts, local Markdown targets, Python syntax and notation. The final manifest binds the delivered research files. Final status review found only this new audit directory; no tracked production file was modified. No large performance benchmark or optimizer implementation was run.

**PROCEED:** the single local, capped cut-fusion experiment in the frozen spec. **DEFER:** knowledge compilation and hierarchical representations until their consumer/structure prerequisites exist. **STOP:** broader optimizer, learned router, generic cache work, scale sweep or paid run on this evidence. If the frozen implementation test fails its global savings or lifecycle gate, stop the candidate; do not turn the same results into a new confirmation set.

The next task belongs in this thread because it reuses source findings, controls and proof obligations. GPT-5.6-sol with high reasoning is a reasonable available model for the bounded prototype; no model-cost measurement is claimed. The implementation prompt is a proposal for the next instruction, not permission to implement during this research-only turn.

## Internal evidence references

- R1: [Deep technical dossier](../../research/CM_COMPUTATION_DEEP_TECHNICAL_DOSSIER.md), [performance audit](../2026-09-11-cm-performance/REPORT.md).
- R2: [Remaining gates](../../research/CM_REMAINING_RESEARCH_GATES_2026_09_11.md), [continuation dispositions](../../research/CM_CONTINUATION_RESEARCH_DISPOSITIONS_2026_09_11.md), [post-C38 disposition](../../research/CM_ARCHITECTURE_AUDIT_DISPOSITION_AFTER_C38_2026_09_03.md).
- R3: [Learning decision surface](../../research/CM_LEARNING_DECISION_SURFACE_AND_MEMORY_EVALUATION_2026_09_09.md).
- R4: [Integrated continuation and projection results](../2026-09-11-cm-next-research/REPORT.md).
- R5: [Time attribution follow-up](../2026-09-15-cm-time-attribution-deep-dive/FOLLOWUP_CODE_DIVE.md), [family repair opportunities](../2026-09-15-cm-family-repair/OPPORTUNITIES.md).
- R6: [D5 natural rules](../../recognition/NATURAL_RULE_PROFITABILITY_MILESTONE_D5_2026_08_29.md), [D7 normalization](../../recognition/NATURAL_NORMALIZATION_MILESTONE_D7_2026_08_29.md), [D9 policy](../../recognition/NATURAL_PROFITABILITY_POLICY_MILESTONE_D9_2026_08_29.md).
- R7: [Typed specification](../../../paper_program/01_audit/TYPED_SEMANTIC_SPECIFICATION.md), [formal proofs](../../../paper_program/01_audit/FORMAL_PROOF_PACKAGE.md), [prior literature matrix](../../../paper_program/02_literature/LITERATURE_MATRIX.md).
- R8: [Overnight local assurance](../2026-09-15-cm-overnight-local-portfolio/REPORT.md), [local consolidation](../../research/CM_LOCAL_CONSOLIDATION_REVIEW_2026_09_16.md).
- R9: [D10 indexed rule engine](../../recognition/LEARNING_MILESTONE_D10_INDEXED_RULE_ENGINE_2026_08_30.md).

## Primary literature checked

Bibliographic scope matters: asymptotic representation theorems, synthesis objectives and measured software performance are different evidence. Mathematical examples and proposed experiment costs above are our derivations, not performance claims from these papers.

| ID | Primary source | Relevant result and limitation |
| --- | --- | --- |
| L1 | Mishchenko, Chatterjee, Brayton, [DAG-Aware AIG Rewriting (2006)](https://people.eecs.berkeley.edu/~alanmi/publications/2006/dac06_rwr.pdf) | Small-cut truth functions, precomputed replacements and DAG-aware gain; the closest antecedent. Gate minimization is not Python latency. |
| L2 | Zhou, Wang, Mishchenko, [Fast Adjustable NPN Classification Using Generalized Symmetries (2019)](https://people.eecs.berkeley.edu/~alanmi/publications/2019/trets19_npn.pdf) | Matching under input/output negation and permutation; a transformation witness is required. |
| L3 | [To SAT or Not to SAT: Ashenhurst Decomposition in a Large Scale (2008)](https://cecs.uci.edu/~papers/iccad08/PDFs/Papers/01B.2.pdf) | Symbolic functional-decomposition tests; not a free cofactor encoder. |
| L4 | Tempia Calvino et al., [Practical Boolean Decomposition for Delay-driven LUT Mapping (2024)](https://arxiv.org/abs/2406.06241); Oliveira and Van den Broeck, [Symbolic Functional Decomposition: A Reconfiguration Approach (2026)](https://arxiv.org/abs/2601.08354) | Hardware mapping and parameterized symbolic algorithms respectively; the latter's linear input dependence holds with its width/structure/automaton parameters, not unrestricted Boolean decomposition. |
| L5 | Bertacco and Damiani, [Disjunctive Decomposition of Logic Functions (1997)](https://web.eecs.umich.edu/~valeria/research/publications/IWLS97.pdf) | BDD-based disjoint-support decomposition; complexity measured in BDD size, which may already be exponential. |
| L6 | Bryant, [Graph-Based Algorithms for Boolean Function Manipulation (1986, author version)](https://www.cs.cmu.edu/~bryant/pubdir/ieeetc86.pdf); [CUDD manual](https://www.cs.rice.edu/~lm30/RSynth/CUDD/cudd/doc/node3.html) | Same-order ROBDD canonicity, Apply and practical variable reordering. No guarantee of small diagrams. |
| L7 | Darwiche and Marquis, [A Knowledge Compilation Map (2002)](https://arxiv.org/abs/1106.1819) | Distinguishes succinctness, tractable queries and transformations; supports contract-specific comparisons. |
| L8 | Darwiche, [SDD: A New Canonical Representation of Propositional Knowledge Bases (2011)](https://ocs.aaai.org/ocs/index.php/IJCAI/IJCAI11/paper/viewPaper/3341) | Vtree-based representation and structural size bounds. |
| L9 | Van den Broeck and Darwiche, [On the Role of Canonicity in Knowledge Compilation (2015)](https://ojs.aaai.org/index.php/AAAI/article/view/9423) | Compressed canonical SDDs can lose polynomial-time Apply; needed qualification to L8. |
| L10 | Lagniez and Marquis, [An Improved Decision-DNNF Compiler (2017)](https://www.ijcai.org/proceedings/2017/93) | d4's decomposition/compiler engineering; an external exact scalar-query baseline. |
| L11 | Sistla et al., [CFLOBDDs: Context-Free-Language Ordered Binary Decision Diagrams (2022)](https://arxiv.org/abs/2211.06818); Zhi and Reps, [Polynomial Bounds of CFLOBDDs against BDDs (2024)](https://arxiv.org/abs/2406.01525) | Hierarchical repetition and same-order comparisons; best-case exponential succinctness is family-dependent. |
| L12 | [Do CFLOBDDs Actually Make Use of Linear Structure? (2026)](https://arxiv.org/abs/2605.15552) | Explains interplay of hierarchical and sequential structure; not a claim about GF(2) linearity. |
| L13 | [Zero-Suppressed Sentential Decision Diagrams (2016)](https://ojs.aaai.org/index.php/AAAI/article/download/10114/9973); [Dynamic Boolean Synthesis with Zero-suppressed Decision Diagrams (2025)](https://arxiv.org/abs/2512.07018) | Set-family representations and synthesis use. Original Minato 1993 DOI lookup was not successfully retrieved; no full-text claim is made for it. |
| L14 | Carlet, [Boolean Functions for Cryptography and Coding Theory, author manuscript](https://www.math.univ-paris13.fr/~carlet/book-fcts-Bool-vect-crypt-codes.pdf) | ANF, multilinear Boolean functions and transformations; sparsity depends on basis. |
| L15 | Albrecht, Bard, Pernet, [Efficient Dense Gaussian Elimination over GF(2)](https://arxiv.org/abs/1111.6549) | Exact packed finite-field linear algebra; includes costs beyond rank labels. |
| L16 | Dudek, Dueñas-Osorio, Vardi, [Efficient Contraction of Large Tensor Networks for Weighted Model Counting (2019)](https://arxiv.org/abs/1908.04381); Dudek, Phan, Vardi, [DPMC (2020)](https://arxiv.org/abs/2008.08748) | Graph decomposition, contraction planning and project-join execution. Arithmetic and ordering contracts must match. |
| L17 | Beyersdorff et al., [Proof Systems for Tensor-based Model Counting (2026)](https://ojs.aaai.org/index.php/AAAI/article/view/38430) | Formal perspective on exact counting computations; does not promise low-width contraction. |
| L18 | Amilhastre, Vilarem, Janssen, [Complexity of minimum biclique cover and minimum biclique decomposition for bipartite domino-free graphs (1998)](https://www.sciencedirect.com/science/article/pii/S0166218X98000390); [Boolean Matrix Factorization with SAT and MaxSAT (2021)](https://arxiv.org/abs/2106.10105) | General hardness and exact optimization approaches; approximate/positive-error objectives are excluded here. |
| L19 | Oseledets, [Tensor-Train Decomposition (2011)](https://users.math.msu.edu/users/iwenmark/Teaching/CMSE890/TENSOR_oseledets2011.pdf) | Numerical tensor compression; exact Boolean semantics require a separate argument. |
| L20 | Rust compiler team, [Incremental compilation in detail](https://rustc-dev-guide.rust-lang.org/queries/incremental-compilation-in-detail.html) | Dependency validation and reuse architecture; not CM performance evidence. |
