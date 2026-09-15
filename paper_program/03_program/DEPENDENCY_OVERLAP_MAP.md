# Manuscript dependency and overlap map

## Recommended paper

**CM-1 — Operator-Level Boolean Computation with Correspondence Matrices**

- Uses: C01-C07, a fully specified version of C11, newly validated C19-C20, and conditionally C12-C13/C24-C25.
- Requires: P01-P06, P07 if the LM section is retained, and readiness gates G1-G7 from the decision memo.
- Excludes: modulo equivalence, physical quantum claims, inconsistent higher-dimensional formulas, broad representation novelty, and superseded headline speedups.
- Relation to 2018 posting: substantial rewrite with explicit disclosure; preserves the motivating notation while changing the research question and contribution.

## Reserved paper, not yet authorized for drafting

**CM-2 — possible LM/higher-arity calculus paper**

- Would deepen C12-C13/C24-C25 and use corrected versions of C15-C17 without repeating CM-1's compact LM section.
- Depends on P08 and on a second novelty search centered on symbolic vector logic, Boolean-algebra-valued matrices, projector/eigenvalue logics, semi-tensor products, tensor decision diagrams, and Boolean tensor decompositions.
- Must contain a theorem, algorithm, or representation-size result that is not merely a reshaped truth table or known structure matrix.
- Does not need CM-1's performance results unless it reuses the compiler.
- Current decision: no-go until an independently publishable contribution exists.

## Overlap controls

| Material | 2018 posting | CM-1 | CM-2 reserve |
|---|---|---|---|
| 2x2 operator examples | Original presentation | One concise motivating example with citation | Background only |
| Uniqueness / 16 operators | Claimed as core | Antecedent definition, not novelty | Background only |
| Linearity / basis | Informal and domain-ambiguous | Typed GF(2) lemma | Only if needed |
| Shared-operands fusion | Informal decomposition identity | Central theorem plus compiler algorithm | Reuse by citation only |
| Quotient / modulo | Introduced | Boolean difference optional; modulo removed | Excluded |
| Logic matrices / measurement | Central analogy | Compact typed symbolic-lift and nonphysical relational-pairing section, conditional on P07 and novelty search | Deepen only if an independent theorem program exists |
| Quantum analogy | Prominent | Explicitly disclaimed | Excluded unless a genuine quantum model is developed |
| Higher dimensions | Inconsistent formulas | Limitation/background only | Entirely rederived and novelty-tested |
| Performance | Speculative | New frozen evaluation; corrected earlier evidence disclosed | Separate only if a new algorithm is evaluated |

The map prevents salami slicing: CM-2 cannot repeat CM-1's definitions, proof, and empirical result as its main contribution. If CM-2 never clears its gate, the program remains complete as one strong paper.
