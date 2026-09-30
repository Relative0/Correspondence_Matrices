# Simulated Expert Panel Audit: Operator-Level Boolean Computation with Correspondence Matrices

**Manuscript:** *Operator-Level Boolean Computation with Correspondence Matrices*  
**Draft audited:** post-split initial draft, 22 September 2026  
**Panel type:** simulated multidisciplinary expert panel; no external human reviewers were contacted.

## Executive verdict

The paper is at the right point for an audit. The post-split thesis is now coherent: the paper is about a typed local compiler transformation, not a broad CM/LM foundations calculus. The mathematical core is adequate for a compiler/mechanism paper, but the rule presentation should be made more explicit before a confirmatory benchmark is frozen. The largest remaining submission-level gap is empirical rather than theoretical: protocol v3 (or a rigorously equivalent successor) still needs to be executed if the paper is to make a positive or negative end-to-end pair-compiler claim.

The panel recommends **a small increase in compiler-specific theory, not a return to broad LM theory**, and **a larger increase in direct pair-compiler results**.

## Recommended balance: theory versus results

### Add a little more theory

The present soundness story is basically sufficient, but four additions would materially improve rigor and readability:

1. Add an explicit **primitive-normalization inference rule**. Equations (17) and (18) are inductive rules, but the main text does not currently display the base rule that creates a structural pair token.
2. Add an explicit **local-retabulation inference rule**. Retabulation is described in prose and proved sound, but displaying the rule makes the hybrid semantics easier to follow.
3. Add a short **normalization lemma**: every admitted signed/permuted primitive has a deterministic transport into the declared canonical frame, and that transport preserves its Boolean function.
4. Add a **completeness proposition for the pure structural fragment**: every expression generated from admitted signed primitives by token negation and same-frame supported fusion is accepted by the pure structural compiler and returns the unique canonical token for its function.

These additions would strengthen the compiler paper without duplicating the companion LM foundations manuscript.

### Add more results

The evidence section is intellectually honest, but the pair compiler itself still lacks its decisive end-to-end result. The most valuable additional measurements are:

- protocol-v3 primary comparison against direct packed evaluation;
- structural/hybrid/retabulation/fallback prevalence on natural workloads;
- time breakdown for recognition, support discovery, frame normalization, token fusion, retabulation, and fallback conversion;
- reuse/break-even curves for prepared versus one-shot use;
- results stratified by AST occurrence count `N`, unique DAG nodes `U`, and sharing mode;
- output-type stratification (token, scalar/batch query, packed vector, dense materialization);
- all failures, refusals, and timeouts retained in the denominator.

If protocol v3 is negative, the current paper still has a coherent mechanism/negative-boundary thesis. If it is positive in a narrow region, the paper gains a systems result without changing its novelty boundary.

## Why Equations (17) and (18) are hard to read right now

The notation is mathematically standard for inference rules, but several symbols are introduced at once. In addition, the letter `R` currently means both the **canonical row variable** in `Pair(R,C,t)` and the **retabulated provenance class** in `p in {S,R,H}`. The panel strongly recommends renaming the retabulated provenance to `T` (for tabulated/retabulated), giving provenance classes `S,T,H`.

A short boxed paragraph should explain the judgment before the rules:

> `Gamma |- e Downarrow^p Pair(R,C,t)` means: under compiler environment `Gamma`, expression `e` compiles successfully to four-bit token `t` in canonical operand frame `(R,C)`, with provenance `p`. The token must denote the same two-variable Boolean function as `e` after fixed substitutions.

The horizontal bar in an inference rule should be read as **"if the facts above the bar hold, the compiler is allowed to conclude the fact below the bar."** It is not division.

## Piece-by-piece interpretation of the rules

Let `Gamma=(R,C,F)` contain the canonical row variable, canonical column variable, and fixed substitutions.

The central semantic invariant is:

`E_t(r,c) = e[r/R,c/C]` for every `r,c in B`.

Thus the compiler is not merely returning four bits; it is certifying that those four bits are the truth table of the source subtree in one declared frame.

### Equation (17): negation

Premise:

`Gamma |- a Downarrow^p Pair(R,C,t_a)`

means that `a` has already compiled to a correct token `t_a` in frame `(R,C)`.

Conclusion:

`Gamma |- not a Downarrow^{nu(p)} Pair(R,C,not t_a)`

means that the compiler may compile `not a` by complementing all four token bits. The frame stays the same. The provenance changes only to record how the child token was obtained. If the child was purely structural, the result remains structural; if retabulation exists below this new structural step, the result is hybrid.

### Equation (18): same-frame fusion

Premises:

`Gamma |- a Downarrow^p Pair(R,C,t_a)`  
`Gamma |- b Downarrow^q Pair(R,C,t_b)`

require **both** children to have already reached the **same canonical frame** `(R,C)`.

Conclusion:

`Gamma |- a Phi b Downarrow^{p join q} Pair(R,C,t_a hat(Phi) t_b)`

says that the parent can be represented by applying the outer connective `Phi` entrywise to corresponding token bits. Because every bit position now refers to the same `(r,c)` assignment in both tokens, this is sound. If both children are structural, the parent is structural; if either child contains retabulated ancestry, the parent is hybrid.

## Full worked derivation

Take canonical frame `(X,Y)` with no fixed substitutions and the expression

`e = (X => not Y) XOR (not Y => X)`.

The implication token in true-first order `(11,10,01,00)` is

`[=>] = 1011`.

### Left child

`a = X => not Y`.

It already has row operand `X`, but its column literal is `not Y`. Flipping the column of the implication token gives

`1011 -> 0111`.

So the primitive normalization rule yields

`Gamma |- a Downarrow^S Pair(X,Y,0111)`.

### Right child

`b = not Y => X`.

Its operands arrive in the opposite order. Transpose first, moving from `(Y,X)` to `(X,Y)`, and then flip the column because the second canonical operand is `Y` rather than `not Y`:

`[=>]^T P = 1110`.

Thus

`Gamma |- b Downarrow^S Pair(X,Y,1110)`.

### Fuse with Equation (18)

Both children are now in exactly the same frame. With `Phi = XOR`, fuse corresponding bits:

`0111 XOR 1110 = 1001`.

Therefore

`Gamma |- e Downarrow^S Pair(X,Y,1001)`.

Token `1001` is XNOR/equivalence in true-first order. Hence

`(X => not Y) XOR (not Y => X) = (X <=> Y)`.

The important compiler step was not the four-bit XOR itself. The important step was proving that the two child tokens referred to the same `(X,Y)` coordinates before that XOR was permitted.

### Apply Equation (17)

For `not e`, complement `1001`:

`1001 -> 0110`.

So

`Gamma |- not e Downarrow^S Pair(X,Y,0110)`.

Token `0110` is XOR. Thus negating the compiled XNOR token gives the XOR token without re-evaluating either operand subtree.

## Proposed rule presentation for the paper

The panel recommends displaying four rules rather than only the two inductive rules.

### Primitive normalization

For an admitted signed primitive `Theta(l_1,l_2)`, let `Norm_Gamma` return its correctly transported token `t` in `(R,C)`:

```
Norm_Gamma(Theta(l_1,l_2)) = t
--------------------------------  [Primitive]
Gamma |- Theta(l_1,l_2) Downarrow^S Pair(R,C,t)
```

### Negation

```
Gamma |- a Downarrow^p Pair(R,C,t_a)
-------------------------------------  [Neg]
Gamma |- not a Downarrow^{nu(p)} Pair(R,C,not t_a)
```

### Same-frame fusion

```
Gamma |- a Downarrow^p Pair(R,C,t_a)    Gamma |- b Downarrow^q Pair(R,C,t_b)
-------------------------------------------------------------------------------- [Fuse]
Gamma |- a Phi b Downarrow^{p join q} Pair(R,C,t_a hat(Phi) t_b)
```

### Exact local retabulation

When the strategy permits retabulation and the live support is exactly `{R,C}`:

```
supp_F(e) = {R,C},    t = (e_11,e_10,e_01,e_00)
-------------------------------------------------  [Tab]
Gamma |- e Downarrow^T Pair(R,C,t)
```

The text should immediately state that `[Tab]` is a fallback base case, not a structural recognition result.

A small provenance table would also help:

| child provenance | structural negation | fusion with `S` |
|---|---|---|
| `S` | `S` | `S` |
| `T` | `H` | `H` |
| `H` | `H` | `H` |

This is easier to read than defining `nu` and `join` only in prose.

# Reviewer reports

## Reviewer A - formal semantics and compiler correctness

**Verdict:** minor-to-moderate revision before experimental freeze.

Strengths: the semantic invariant is well chosen; pure structural, retabulated, hybrid, and fallback paths are no longer conflated; the proof structure is valid; the fallback boundary is explicit.

Requested changes:

1. Display the primitive and retabulation rules in the formal system.
2. Rename provenance `R` to `T` to avoid collision with canonical row variable `R`.
3. Define `not t` explicitly as four-bit complement and `t_a hat(Phi) t_b` explicitly as entrywise application.
4. Add a one-page derivation example immediately after the rules.
5. Consider a completeness result for the explicitly generated pure-structural fragment, not only soundness.
6. State whether canonical pair metadata are part of the judgment syntactically or checked by the implementation before the rule fires. The prose implies the latter; make this exact.

## Reviewer B - systems and performance methodology

**Verdict:** theory is sufficient after the rule clarification; results are the main remaining gap.

Strengths: the paper distinguishes token, pair surrogate, IR, flat program, and dense output; it refuses to convert a constant-time local token operation into an end-to-end complexity claim; it separates S1/S2, P14-PY0, later project results, and protocol v3.

Requested changes:

1. Execute protocol v3 or a frozen equivalent before a performance-oriented submission.
2. Report phase-level compiler costs and fallback frequency.
3. Make natural-workload pairability/prevalence a first-class result, even if prevalence is low.
4. Retain `N` and `U` and explicitly distinguish identity sharing from structural equality.
5. Give a rationale for the primary `1.20x` time threshold and `10%` memory threshold, or make them decision thresholds rather than scientific effect-size claims.
6. Consider moving the detailed later-project architecture ratios to an appendix or compact context table if they distract from the pair compiler's direct evidence.

## Reviewer C - logic synthesis / prior-art boundary

**Verdict:** novelty framing is appropriately conservative; no broad theory expansion is recommended.

Strengths: the paper does not claim packed truth functions, NPN transforms, pointwise truth-vector combination, LUT rewriting, or AIG/DAG sharing as new. The manuscript asks the correct representation-specific question: whether explicit frame metadata makes a useful local rewrite cheap, compositional, and auditable.

Requested changes:

1. Add one compact comparison table contrasting the pair compiler with direct four-bit evaluation, generic local truth-function folding, NPN/LUT rewriting, and AIG rewriting along dimensions such as frame metadata, rewrite scope, output artifact, sharing, and fallback.
2. Keep Cheng/Zhao/Xu as the direct antecedent for the raw same-frame pointwise identity.
3. Avoid language suggesting that transpose/row/column operations are themselves novel; novelty should stay at the typed compiler integration/evaluation level.
4. If protocol v3 ties a generic optimizer, interpret that as a general local-function mechanism result rather than a failed experiment.

## Reviewer D - mathematical exposition and editorial structure

**Verdict:** good post-split architecture; the Rules subsection is currently the main pedagogical bottleneck.

Strengths: the paper is much more focused than the pre-split manuscript. The opening frame-mismatch example is strong. The discussion distinguishes structural folding from retabulation and kernel gains from full costs.

Requested changes:

1. Rename subsection 4.1 to **"How to read a pair-compilation judgment"** and explain the notation in words before formal rules.
2. Rename provenance `R` to `T`.
3. Put the worked derivation immediately after the four rules, before the soundness theorems.
4. Add a small graphic or token table showing true-first order `(11,10,01,00)` during the derivation.
5. Keep the companion LM theory out of this paper; cite it rather than reopening that material.
6. Consider trimming some later-project benchmark detail once direct protocol-v3 results exist, so the paper's own experiment remains visually primary.

# Panel consensus and revision order

## P0 - before freezing the next benchmark

1. Rewrite the Rules subsection with explicit Primitive, Neg, Fuse, and Tab rules.
2. Rename provenance classes to `S,T,H` or long-form names.
3. Add the worked derivation and a provenance table.
4. Add the normalization lemma and, if desired, pure-fragment completeness proposition.
5. Re-run the finite correctness suite after any implementation/spec wording changes.

## P1 - before submission

1. Execute the frozen pair-compiler end-to-end evaluation.
2. Add natural pairability/fallback prevalence and phase-level overhead results.
3. Bind source, environment, raw observations, failures, and analysis to an archival package.
4. Update the abstract/results/conclusion to reflect the actual confirmatory outcome without changing the preregistered interpretation.

## P2 - polish

1. Add the compact comparator table.
2. Decide whether later project-wide context stays in the main text or moves to an appendix.
3. Final pass for figure readability, terminology, and venue length.

## Overall recommendation

Proceed. The paper does **not** need substantially more foundations theory. It needs a clearer formal presentation of the compiler rules and, much more importantly, direct empirical results for the compiler described by those rules. The present draft is mature enough to refine the formal specification now and then freeze the confirmatory evaluation.
