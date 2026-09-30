# Pre-submission review panel report

**Manuscript:** *Operator-Level Boolean Computation with Correspondence Matrices*  
**Author:** Brian Theory  
**Review status:** Simulated multidisciplinary review; no external person has been contacted.  
**Consensus recommendation:** Major revision.

## Panel composition

1. **Boolean algebra, matrix logic, and semi-tensor-product reviewer** — tests the definitions, proofs, LM/CM distinction, prior-art boundary, and soundness claims.
2. **Compiler and performance-evaluation reviewer** — tests the compiler contribution, baselines, cost model, reproducibility, and whether the proposed experiments can support the claims.
3. **Applied-computing editor and advanced-reader reviewer** — tests accessibility, paper order, figure communication, venue fit, and the interests and objections of adjacent communities.

The panel treats the manuscript as a working paper, not as a finished submission, because its Results section is deliberately unfilled.

## Consensus

The strongest defensible contribution is not that truth values can be reshaped into matrices, nor that logical operators can be represented by matrices. It is the integrated compiler method built around:

- compact four-bit Boolean operator tokens;
- explicit, typed operand frames;
- signed-variable normalization by transpose and row/column permutation;
- entrywise fusion only after exact frame agreement;
- a stated semantic invariant and an explicit fallback boundary;
- careful separation of the operator token, framed pair surrogate, CM IR, flat program, and dense truth-relation output.

The paper is candid about its limits and already distinguishes coefficient-space linearity from linearity in the logical inputs. Those are significant strengths. The main risk is novelty: several component operations have close antecedents in matrix logic, Boolean matrix methods, NPN transformations, LUT truth-table manipulation, and logic synthesis. Publication therefore depends on presenting the typed compiler integration precisely and demonstrating a reproducible positive performance region.

## Submission blockers

### 1. Correct the Rule 1 display in Figure 4

The valid operand-exchange identity is

\[
\langle Y|[\Theta]|X\rangle
=\langle X|[\Theta]^{T}|Y\rangle.
\]

The figure's further displayed equality to \(\langle X|[\Theta]|Y\rangle^{T}\) is not generally equivalent under ordinary transpose semantics: transposing a scalar does not remove the required transpose of \([\Theta]\). Remove that last equality unless a different operation is explicitly defined.

### 2. Complete the empirical campaign

The current paper cannot substantiate a compiler or performance contribution while the Results section is empty. The final study must separately report:

- structural normalization/fusion compilation time;
- direct four-assignment retabulation time;
- four-bit token query time;
- compile-plus-\(K\)-queries time;
- packed and dense output materialization;
- memory, timeout, rejection, and fallback behavior;
- the frequency of structural success, retabulation, and ordinary-IR fallback.

Repeated evaluation needs special care: after either compiler path has produced the same four-bit token, query costs are essentially the same. Reuse therefore amortizes differences in compilation cost; it is not a distinct token-evaluation advantage.

### 3. Add the closest compiler and logic-synthesis literature

The related-work audit must directly cover:

- truth-table and LUT composition;
- input negation, permutation, output negation, and NPN equivalence;
- cut-based Boolean-network rewriting;
- AIG-based rewriting and sharing;
- bit-parallel or bit-sliced truth-table evaluation;
- constant folding, partial evaluation, hash-consing, and common-subexpression elimination;
- Boolean function canonicalization and small-domain superoptimization.

Without these comparisons, a synthesis reviewer may reasonably interpret the row/column transforms and four-bit fusion as renamed standard truth-table operations. The proposed distinction should be the typed operand-frame calculus, exact admission rules, fallback semantics, and measured compiler integration.

### 4. Add a direct four-bit packed evaluator baseline

The current phrase “sharing-aware scalar and packed-bit evaluator” is too broad. Include a critical direct baseline that evaluates the formula AST once over four bit masks, producing the four truth values in parallel. This is probably the closest simple non-CM comparator for the pairable domain.

### 5. Reorder the paper around the computational result

The title promises operator-level computation, but the compiler payoff presently arrives after the representation map and LM theory. A more accessible order is:

1. CM convention and XOR–AND evaluation;
2. operand frames and signed transformations;
3. the concrete aligned-fusion example and theorem;
4. pair compiler, artifact types, soundness, and fallback;
5. related-work comparison;
6. evaluation and results;
7. formula-valued LMs and logical pairing as a symbolic extension;
8. limitations and conclusion.

If the LM material remains before the compiler result, the manuscript can look like a broad foundations or quantum-analogy paper, where its novelty case is weakest.

## Mathematical and notational corrections

1. **Repair the LM index system.** Separate position indices from truth-assignment indices. One clear convention is
   \[
   b_1=1,\quad b_2=0,\qquad c_{ij}:=\Theta_{b_i b_j},
   \]
   use \(i,j\in\{1,2\}\) in LM sums, and reserve \(\Theta_{xy}\) for \(x,y\in\{0,1\}\).
2. **Fix the type of the Impax pairing.** The early equation \(\langle X|[\impax]|Y\rangle=1\) appears before formula-valued states are defined. Use quantified lowercase bits there or move the formula-valued statement after its definitions.
3. **Make the ANF conversion concrete in the declared truth order.** State
   \[
   a_\varnothing=\Theta_{00},\quad
   a_X=\Theta_{00}\mathbin{\Updownarrow}\Theta_{10},\quad
   a_Y=\Theta_{00}\mathbin{\Updownarrow}\Theta_{01},
   \]
   \[
   a_{XY}=\Theta_{00}\mathbin{\Updownarrow}\Theta_{10}
   \mathbin{\Updownarrow}\Theta_{01}\mathbin{\Updownarrow}\Theta_{11}.
   \]
   This prevents a Möbius transform from being applied directly in the wrong vector order.
4. **Declare one reproducible STP convention.** Select an explicit delta-vector encoding and column order, then state the permutation from the paper's true-first vector.
5. **Use a formally bra-indexed component** in the Boolean contraction, or define a neutral component function used by both bras and kets.
6. **Define the 90-degree rotation entry map.** Make clear that rotation is a visual/exact observation for XOR and XNOR, while the general operand transforms are transposition and permutation.
7. **State pair-compiler admissibility.** Cover repeated-variable cases, whether row and column variables must differ, and fixed substitutions.
8. **Split the soundness result.** Give a structural alignment-and-fusion theorem, an exact-retabulation lemma, and a top-level compiler theorem that combines them.

The LM section would gain a concrete semantic theorem from the identity

\[
\langle A|[\mathcal M_{X\Theta Y}]|B\rangle
\equiv (A\Leftrightarrow X)\mathbin{\Theta}(Y\Leftrightarrow B),
\]

subject to the repaired indexing convention.

## Cost-model and experimental corrections

- Signed-literal alignment is \(O(k)\) when a negation chain of length \(k\) must be inspected, followed by an \(O(1)\) four-bit transform.
- State the current implementation's possible \(O(N^2)\) worst case explicitly and distinguish AST occurrences from unique DAG nodes.
- Substantiate the claimed \(O(H)\) auxiliary space. Very deep Python trees may also encounter recursion limits before the planned 4095-node skewed cases complete.
- In the explicit-output bound \(\Theta(2^n)\), define \(n\) as the number of requested unfixed Boolean output axes.
- Two-variable formulas represent only 16 semantic functions. Large two-variable ASTs measure syntactic redundancy and compilation behavior, not growing semantic complexity.
- A two-variable ROBDD is necessarily tiny. Retain it for completeness, but treat it as more informative on multipair or compound workloads.
- Call an implementation an “external baseline” only if it is actually external; otherwise use “non-CM comparator.”
- Freeze the workload corpus, random seeds, run manifest, machine state, timing boundaries, garbage-collection policy, process startup policy, thread counts, affinity policy, hash seed, and attrition rules before the confirmatory run.
- Justify the proposed 20% time-improvement and 10% peak-memory thresholds rather than presenting them as self-evident.
- Report all failed generations, timeouts, and unsupported cases. “Where generation succeeds” must not become silent benchmark attrition.

## Evidence and reproducibility additions

- Add pair-compiler pseudocode.
- State exact truth tables and implication argument order for every supported primitive.
- Exhaustively test the semantics of fixed substitution.
- Independently verify the true-first/false-first layout conversion.
- Keep the correctness oracle independent from CM token construction.
- Add metamorphic tests for double negation, double transpose, row/column permutation involution, complement involution, and aligned-fusion equivalence.
- Archive source revision, environment, configuration, corpus, seeds, raw results, failures, and the analysis script.
- Expand threats to validity into construct, internal, external, conclusion, and implementation validity.

## Presentation recommendations

- Add a claim-comparison table with rows for CMs, formula-valued LMs, Edwards, Mizraji/vector logic, STP, ANF, and logic-synthesis truth tables. Useful columns include scalar algebra, operator shape, operand encoding, frame metadata, transforms, formula-valued entries, operator fusion, and implementation evidence.
- Define the custom outer-product notation once by displaying the resulting \(2\times2\) matrix.
- Give one evaluated example of the “Boolean compatibility formula.”
- Prefer **logical pairing** as the primary term and present “logical measurement” as the author's interpretation. This reduces an unnecessary quantum-computing distraction.
- Bring the appendix observation about OR–AND one-hot selection into the main text. XOR is important here because it defines the declared \(\mathrm{GF}(2)\) coefficient algebra and behavior beyond one-hot selection, not because one-hot scalar selection uniquely requires XOR.
- Treat Impax and the XOR/XNOR rotation as concise notation and structure examples unless a compiler consequence is demonstrated.
- Use vector exports of the figures for the submission version. The current raster previews are legible, but small mathematical text will reproduce better as vector graphics.

## Interested audiences and likely objections

### Strongest prospective audiences

- Boolean logic synthesis and electronic-design automation;
- symbolic computation and computer algebra;
- compiler optimization and verified rewriting;
- formal methods and propositional-reasoning tools;
- Boolean-network and semi-tensor-product researchers;
- matrix/vector logic and Eigenlogic researchers;
- bit-parallel and specialized Boolean-computation implementers;
- logic educators and advanced students interested in operator visualizations.

### Likely reactions

- **Logic-synthesis practitioner:** interested in the four-bit operator compiler, but will demand direct NPN/LUT/truth-table/AIG comparisons.
- **Applied-computing researcher:** wants completed end-to-end results, code and data availability, workload provenance, and explicit failure regions.
- **Mathematical logician:** likely to find the current identities elementary unless the LM theory is developed substantially further.
- **Theoretical computer scientist:** likely to require a more general theorem, complexity consequence, or stronger algorithmic result.
- **Advanced graduate reader:** can follow the CM selection example, but needs the compiler motivation and concrete fusion result before the dense representation and LM sections.
- **Soundness-oriented editor:** will value the explicit fallback and artifact boundaries, but will require the Rule 1 correction, repaired indexing, and a completed Results section.

## Recommended human review panel after the revision

After the mathematical corrections and benchmark freeze, recruit five independent readers by role:

1. one researcher in matrix/vector logic or Boolean matrix algebra;
2. one STP or Boolean-network researcher;
3. one logic-synthesis or EDA researcher familiar with NPN/LUT/AIG methods;
4. one compiler benchmarking or performance-methodology researcher;
5. one advanced graduate student or applied-computing editor for accessibility.

Give each reader a focused questionnaire. Ask the first two about mathematical antecedents and type distinctions, the next two about incremental novelty and empirical fairness, and the last reader about whether the computational story is understandable without the historical manuscript.

## Paper-program recommendation

The smallest immediate program remains one accessible paper, but with the compiler result moved forward and the LM material labeled as a symbolic extension. The longer-term coherent program is two papers:

1. an experimentally grounded correspondence-matrix alignment and fusion compiler paper;
2. a formula-valued LM, valuation, and logical-pairing paper, but only after its semantic results are deepened.

The current manuscript should not be submitted unchanged. Its next gate is mathematical correction plus a frozen empirical protocol; the gate after that is completed results and a final novelty review against logic-synthesis practice.
