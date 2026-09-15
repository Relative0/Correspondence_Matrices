# Correspondence Matrices publication-program decision memo

Date: 2026-09-14  
Prospective sole author: **Brian Theory**  
Historical posting: *Correspondence Matrices; Algorithms for Propositional Logic* (2018), DOI 10.13140/RG.2.2.28036.37764

## Decision

Develop **one integrated methods paper**, not a series yet. The paper is a conditional **go** only after the mathematical repairs and an untouched empirical validation are complete. Do not begin polished full drafting from either supplied manuscript.

Selected working title:

> **Operator-Level Boolean Computation with Correspondence Matrices**

Recommended central question:

> How can compact XOR-AND matrix operators be transformed into an identical operand frame and fused soundly, and when do compilation, memory, and interface costs outweigh the saved evaluation work?

This framing makes the operator role explicit without claiming that matrix representations, XOR-AND matrix algebra, or pointwise truth-table combination are new. It also makes negative and boundary results part of the contribution rather than an embarrassment.

## Audience, genre, and length

Primary audience: applied and theoretical computer scientists working in symbolic computation, Boolean-function manipulation, compiler optimization, logic synthesis, and high-throughput evaluation. Secondary audience: mathematically literate computing researchers and advanced students.

Do not target mathematical logicians or quantum-computing researchers as the primary audience. The present work neither advances proof theory/model theory nor supplies a quantum-mechanical model.

Use an accessible, science-style research article:

- 10-14 typeset main-text pages, approximately 6,000-8,000 words;
- a 200-250 word nontechnical abstract;
- intuition and concrete examples before notation;
- four main figures and no wall-of-matrix figures;
- theorem statements in the main text, with most proofs and exhaustive checks in an appendix/supplement;
- a reproducibility package containing code, frozen corpora, raw results, environment details, and correction notes.

Accessibility and technical depth are not opposites here. The main text should explain the representation and the performance question visually; the appendix must make every retained formal claim auditable.

## Proposed contribution package

1. A typed operator definition that distinguishes Boolean logic, `GF(2)` coefficient algebra, XOR-AND contraction, the explicit 2 x 2 operator, the interned CM IR, and the compiled flat program. The basis and variable order travel with each artifact. Specific operators use bracketed names such as `[⇕]`; `[Θ]` is the declared generic form.
2. A transformation calculus in which transpose and row/column permutations express operand swap and polarity change and are used for signed operand alignment. The exact `[⇔]` to `[⇕]` 90-degree rotation and the tautological `[\impax]=[⇔]⇕[⇕]` identity motivate the notation without being presented as headline novelty.
3. A sound same-operands fusion rule for arbitrary binary Boolean outer operators, together with exact syntactic and normalization preconditions. The scalar identity is antecedented; the candidate contribution is the verified compiler procedure built from it.
4. A compact, secondary LM section defining formula-valued polarity-orbit matrices, their valuation into CMs, coefficient extraction, and a nonphysical logical measurement pairing. It explicitly distinguishes LMs from Zhao-Gao-Cheng ANF coordinates. Boolean outer products and operator bases are antecedented.
5. A correctness suite combining proofs, exhaustive binary-token checks, property-based tests, and independently computed truth tables.
6. A fresh empirical evaluation against sharing-aware CSE and appropriate BDD/bit-vector baselines, separating preparation, compilation, kernel, wrapper, memory, and end-to-end costs.
7. A candid performance boundary: workloads and reuse counts for which the representation helps, ties, or loses.

The 2018 posting is prior public work by the same author and must be cited. The new manuscript should include an explicit “relationship to the 2018 version” paragraph listing corrected dimensional claims, removed quantum/modulo claims, the newly formalized compiler transformation, and the new evaluation. Historical bibliographic records remain under Brian Droncheff; the new byline and all new author-facing metadata should say Brian Theory.

## Paper architecture

1. **Problem and result.** A motivating shared-operands example, research question, measured boundary, and contribution list.
2. **CMs as Boolean operators.** Introduce bras, kets, true-first operand states, and bracketed operators `[Θ]`; set `Θ:=⇕` for the lead example. Define `⇕` as XOR at first use, visibly replace arithmetic multiplication/addition with AND/XOR, and identify the algebra as `GF(2)` contraction. Close the opening example with `[⇕]=rot_90([⇔])=¬[⇔]` and `[\impax]=[⇔]⇕[⇕]`, while qualifying “superposition” as entrywise Boolean.
3. **Representation map and antecedents.** Begin with the paper-native symbolic lift `[\mathcal M_{X\Theta Y}]`, value it into `[\Theta]`, and use `\operatorname{vec}([\Theta])` only as the bridge to the external ANF and STP representations. Contrast Mizraji, Cheng/Zhao, and Eigenlogic without implying that ANF or STP is a CM component.
4. **Operand-frame transformations.** Generalize from the motivating XOR/XNOR rotation to explicit transpose and row/column permutations for swap/polarity normalization. Rotation remains an exact special case, not the definition of the general transformation calculus.
5. **Verified operand-aligned fusion.** State the same-operands theorem, signed-variable alignment algorithm, recursive token fusion, soundness conditions, retabulation fallback, and non-match cases. Explicitly exclude arbitrary compound-operand alignment from the implemented claim.
6. **Logical matrices and relational pairing.** Define the formula-valued LM lift, valuation into a CM, and logical measurement pairing; explicitly delimit nonquantum meaning. Keep this section compact and move proofs to the appendix.
7. **Higher arity and representation cost.** Give the corrected tensor/vector dimensions and explain exponential explicit size; reserve stronger tensor claims.
8. **Experimental method.** Frozen implementations, untouched corpus, baselines, endpoints, hardware, timing protocol, and statistics.
9. **Results.** Kernel and end-to-end results together; memory/preparation and break-even reuse; negative cases.
10. **Discussion and limitations.** Dependence on repeated operands, variable ordering, aliasing, antecedented identities, and nonquantum scope.
11. **Conclusion.** A narrow claim about a verified operator normalization/fusion method and its boundary.
12. **Appendices/supplement.** Proofs, exhaustive 16-token tables, LM homomorphism proof, benchmark protocol, raw-result schema, and correction mapping.

## Figure plan

| Figure | Purpose | Form |
|---|---|---|
| 1. Boolean operator evaluation and notation | Show bra/ket states, `[Θ]=[⇕]`, the compact contraction, the `[⇔]` to `[⇕]` rotation, and tautological Impax superposition. | Four-panel conceptual diagram; keep the contraction compact and label AND products/XOR reduction beneath it. |
| 2. Representation map | Show `[\mathcal M_{X\Theta Y}] \xrightarrow{v_T} [\Theta]`, then distinguish `\operatorname{vec}([\Theta])` from the external STP structure matrix and ANF coefficient vector. | Typed conversion diagram with paper-native indexed entries; dashed external-comparison boxes for ANF and STP. |
| 3. Align then fuse | Show two differently ordered/polarized expressions transformed into one operand frame and then fused entrywise. | Before/after data-flow diagram with row/column permutation icons and the operand-alignment precondition. |
| 4. LM valuation and pairing | Show an expression-valued LM, valuation to a numeric CM, and a logical compatibility formula returned by pairing. | Layered symbolic-to-numeric diagram; explicitly labeled “nonphysical.” |
| 5. Performance boundary | Make preparation, compilation, kernel, wrapper, memory, break-even reuse, wins, ties, and losses visible. | Faceted measured plot; use a small cost stack only if it remains legible. |

Optional supplement figures: all 16 binary tokens; transformation orbits; memory growth with variable count. Avoid quantum imagery because it suggests a result the method does not establish.

## Program comparison

| Program | Assessment | Reason |
|---|---|---|
| One integrated compiler-methods paper now | **Recommended; conditional go** | It joins the elementary identity to the algorithm, proof, and evidence that could make it useful. It can honestly publish positive, null, and negative regions. |
| Separate foundations and empirical papers now | **No-go** | The foundations overlap heavily with vector logic and semi-tensor-product structure matrices. Splitting would leave one weak-novelty theory paper and one under-contextualized benchmark paper. |
| One paper now, later LM/tensor foundations paper | **Reserve** | Proceed only if the symbolic LM lift, relational pairing, or corrected higher-arity notation yields a nontrivial theorem or algorithm demonstrably beyond established matrix and projector logics. Measurement vocabulary alone does not justify a second paper. |
| Separate software paper | **Reserve** | Consider only after the package is feature-complete, documented, tested, openly developed, and adopted enough to satisfy a software journal's contribution threshold. |

## Venue strategy

First-fit venue class: a broad, soundness-oriented computer-science research journal. **PeerJ Computer Science** is the clearest initial venue to assess because the topic is squarely computer science and the article can be judged on methodological soundness. **PLOS ONE** is a secondary possibility for a rigorously validated computational-method paper, but its utility criterion means the paper must demonstrate an advantage over existing alternatives rather than recapitulate them. Confirm current fees, format, overlap policy, and editorial fit immediately before submission.

Do not target a flagship mathematical-logic, quantum-computing, or top logic-synthesis venue with the current contribution. Those choices would demand either a genuinely new theorem/calculus or much stronger systems evidence. JOSS is not the first-paper venue: its article is about a mature research-software package, and the present contribution is still a method plus evaluation.

## Readiness gates

| Gate | Pass condition | Current state |
|---|---|---|
| G1. Contribution | Novelty statement survives direct comparison with Boolean matrix algebra, matrix logic, vector logic, Boolean XOR-AND products, structure matrices, ANF/ESOP, LM-like symbolic lifts, BDD, and logic synthesis. | **Not passed**; operator/outer-product claims are now antecedented and the exact LM assembly had no direct match in a focused search, but primary Kim/Stern inspection and the final compiler-specific search remain incomplete. |
| G2. Semantics | Boolean/GF(2)/formula-valued/numeric domains and all dimensions/indexes are consistent. | **Partly passed**; a typed working specification now exists, but it must be reconciled with code layouts and independently checked. |
| G3. Proofs | P01-P05 complete and independently checkable. | **Partly passed**; the appendix-ready package now covers CM semantics, transformations, fusion, the concrete pair-compiler invariant and termination, LM valuation/pairing, ANF separation, and higher-arity counting. Complexity P05 and independent mathematical review remain. |
| G4. Implementation | No unintended mutation/aliasing; property tests and versioned artifacts pass. | **Partly passed**; signed-variable alignment, recursive token fusion, a token-only compilation boundary, and the registered retabulation ablation are implemented. The focused pair/optimization and output-budget suites pass 102 tests, including the XOR/XNOR/Impax identities, 250 seeded random formulas, and caller-input nonmutation through both compact and ordinary fallback paths. A frozen release and broader property coverage remain. |
| G5. Evaluation | Untouched corpus, predeclared endpoints, sharing-aware baselines, uncertainty, and all cost layers reported. | **Protocol frozen; measurements not run**. `EVALUATION_PROTOCOL_V1.md` predeclares workload strata, baselines, endpoints, analysis, practical thresholds, failure reporting, and the confirmatory freeze manifest. The ablation is implemented; the frozen corpus/run manifest and measurements remain. |
| G6. Prior-version disclosure | 2018 posting and later corrections are mapped to the new claims and text. | **Partly passed**; sources archived and mapping specified, manuscript text not written. |
| G7. Reproducibility | Frozen release, raw results, environment, seeds/corpus, and execution instructions publicly archivable. | **Not passed**. |

Full drafting should begin only after G1-G5 pass. It is safe to draft a one-page registered analysis plan, notation specification, and figure prototypes before then because those artifacts directly close the gates.

## Immediate work order

1. Complete the focused LM and compiler-antecedent search, then freeze the revised claim set (G1). The typed semantic specification is drafted but still needs independent checking and code-layout reconciliation (G2).
2. Freeze the concrete complexity and mutation contract for signed-variable alignment, recursive token fusion, direct retabulation, and layout conversion (G3-G4).
3. Freeze the code/corpus/run manifest for `EVALUATION_PROTOCOL_V1.md` (G5).
4. Run the frozen evaluation and decide whether the result clears the utility threshold.
5. Only then draft the full accessible manuscript and appendix in the existing Paper-Workbench project.
