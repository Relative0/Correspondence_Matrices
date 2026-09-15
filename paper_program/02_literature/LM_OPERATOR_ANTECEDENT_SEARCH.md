# Focused LM and Boolean-operator antecedent search

Search date: 2026-09-14  
Purpose: test whether the matrix-operator interpretation, Boolean outer-product basis, or formula-valued LM lift can carry a novelty claim

This was a focused claim-defeating search, not a systematic review. Searches targeted Boolean-algebra-valued matrices, formula-valued matrices, logical-vector outer products, operator/operand interaction, bra-ket Boolean logic, polarity matrices, and valuation homomorphisms.

## Findings

### C. R. Edwards (1972)

C. R. Edwards, “The Logic of Boolean Matrices,” *The Computer Journal* 15(3), 247-253, [DOI](https://doi.org/10.1093/comjnl/15.3.247).

The publisher abstract describes a Boolean matrix algebra for manipulating many logical functions simultaneously, with a logic-circuit interpretation and computer manipulation. This defeats any broad claim that Boolean matrix computation or simultaneous manipulation of logical functions began with CMs.

### Ki Hang Kim (1982)

Ki Hang Kim, *Boolean Matrix Theory and Applications*, Dekker, 1982, ISBN 9780824717889, [bibliographic record](https://books.google.com/books/about/Boolean_Matrix_Theory_and_Applications.html?id=UeDuAAAAMAAJ).

This is a high-priority source lead. Standard summaries attribute to it the Boolean outer product of logical vectors, with AND replacing scalar multiplication, and its appendix treats matrices over arbitrary Boolean algebras. Those ingredients are close to the historical LM base matrices `|X_i><Y_j|`. The exact pages must be checked from a primary copy before the final literature review; this audit does not treat the inaccessible page text as fully verified.

### August Stern (1988; 2000)

August Stern, *Matrix Logic: Theory and Applications* (1988), [publisher record and DOI](https://doi.org/10.1016/C2009-0-14445-8), and the “M(atrix) Logic” chapter in *Quantum Theoretic Machines* (2000), [publisher chapter](https://www.sciencedirect.com/science/article/pii/B9780444826183500838).

The publisher material presents truth tables as operators, states that outer products of true/false logical states generate a matrix basis for logical operators, and discusses direct interaction among logical connectives. This is a close antecedent to both the operator emphasis and the outer-product basis idea. Stern's algebra and interpretation differ from the CM XOR-AND 2 x 2 contraction, but the conceptual operator claim is not new.

### Mizraji, Cheng/Zhao, and Eigenlogic

The already-audited vector-logic and semi-tensor-product sources remain decisive:

- Mizraji supplies real-vector matrix operators for connectives and formula-level calculi.
- Cheng, Zhao, and collaborators supply logical structure matrices, swap/negation transformations, exact XOR-AND Boolean matrix products, and pointwise truth-table combination.
- Eigenlogic supplies the stronger projector/eigenvalue/Born-rule framework against which physical “measurement” language must be delimited.

## Exact-LM search result

This pass did **not** locate a clearly identical published construction combining all of the following:

1. the formula-valued matrix
   `[[f(X,Y), f(X,¬Y)], [f(¬X,Y), f(¬X,¬Y)]]`;
2. positive valuation to the numeric 2 x 2 connective CM;
3. valuation commuting with entrywise operator fusion and formula-valued contraction; and
4. interpreting a general bra-LM-ket result as a relational compatibility formula.

That is only a provisional search result. The individual ingredients - Boolean-algebra-valued matrices, logical-vector outer products, operator bases, valuation homomorphisms, and bra-ket matrix logic - are established. The exact assembly may be a distinctive formulation without being a strong standalone novelty.

## Program disposition

- Do not claim novelty for Boolean matrix operators, XOR-AND products, logical-vector outer products, operator bases, or interaction of connectives.
- Present the LM as a compact symbolic lift and explanatory bridge, conditional on a typed proof and final source verification.
- Do not split off an LM/measurement paper now. A later paper is warranted only if the relational pairing yields a nontrivial characterization theorem, algorithm, or representation result beyond the established ingredients.
- Keep the first paper's headline contribution on operand-frame normalization, verified compiler fusion, and the measured performance boundary.

## Remaining source checks

1. Obtain and inspect the relevant Kim pages from a primary copy.
2. Inspect the full Stern operator-basis chapter and identify the closest exact equations.
3. Run citation chaining from Edwards, Kim, Stern, Mizraji, and Cheng for later Boolean-operator calculi.
4. Search compiler and logic-synthesis literature for signed alignment of swapped/negated operand pairs before entrywise fusion.
