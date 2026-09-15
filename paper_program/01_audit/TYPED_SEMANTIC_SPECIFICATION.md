# Typed semantic specification for Correspondence Matrices

Date: 2026-09-14  
Prospective author: **Brian Theory**  
Status: working specification for the contribution and proof audit; not manuscript prose

## 1. Purpose and novelty boundary

A correspondence matrix (CM) is not important merely because four truth-table values are reshaped into a 2 x 2 array. Its useful role is that, after the operand encoding and scalar algebra are fixed, the array is an **operator token**: it can be evaluated by contraction, transformed to account for operand polarity/order, and combined with other operator tokens before the operands themselves are evaluated.

That operator interpretation must still be positioned conservatively. Matrix operators for Boolean functions predate the 2018 CM posting in vector logic and semi-tensor-product work. The candidate contribution is therefore the complete typed pipeline:

1. a compact 2 x 2 Boolean operator token with declared axes;
2. XOR-AND contraction against consistently encoded operands;
3. row/column transformations that normalize operand order and polarity;
4. sound entrywise fusion after signed normalization to an identical operand frame;
5. a symbolic logical-matrix (LM) lift whose valuations recover numeric CMs;
6. a compiler realization and measured account of where the method helps or loses.

The first four items are mathematically elementary and overlap prior algebraic representations. Boolean outer products and logical operator bases also predate the historical LM construction. The potentially publishable distinction is their use as one verified normalization-and-fusion method. The LM symbolic layer is a secondary formal contribution only if its exact polarity-orbit and relational-pairing statements survive final source verification.

## 2. Domains and notation

Let `B = {0,1}`. Logical AND is `∧`, logical negation is `¬`, and logical exclusive-or is written `⇕` (LaTeX `\Updownarrow`) throughout the CM notation. When the same bits are regarded as elements of `GF(2)`, field multiplication is AND and field addition is XOR. Thus the displayed CM contraction is **not ordinary real or integer matrix multiplication**, but it is exactly matrix contraction over `GF(2)` for binary entries. The first use must state that `⇕` denotes XOR; a notation footnote should explain the geometric motivation in Section 4 below.

For a truth value `x`, use the true-first one-hot state

```text
|x> = [x, ¬x]^T,       <x| = [x, ¬x].
```

Rows correspond to `X = 1, 0` and columns to `Y = 1, 0`. Every artifact must carry or declare this ordering; conversions to software layouts with another order are explicit operations, not silent conventions.

For a binary connective `f : B^2 -> B`, the proof notation defines its CM by

```text
          [ f(1,1)  f(1,0) ]
[f]  :=   [ f(0,1)  f(0,0) ].
```

For example, `[⇒] = [[1,0],[1,1]]` under this convention.

In accessible main-text displays, use `[Θ]` for the generic numeric CM, with
assignment-indexed entries `Θ_xy:=x Θ y` for `x,y in {1,0}`, and use the bare
bracketed operator for a specific connective, such as `[⇕]`. Thus `C_f` or
`[f]` may remain a compact
appendix alias, but the representation figure uses

```text
[Θ] = [[Θ_11, Θ_10], [Θ_01, Θ_00]] in B^(2x2).
```

The formula-valued LM uses polarity-position indices `i,j in {1,2}`; its
numeric CM uses truth-assignment indices `x,y in {1,0}`. This distinction keeps
the displayed truth vector in the declared order
`(Θ_11,Θ_10,Θ_01,Θ_00)` without conflating truth assignments with matrix
positions.

## 3. XOR-AND operator evaluation

Define the Boolean/GF(2) contraction

```text
E_[f](x,y) := <x|[f]|y>
            = ⇕_(i,j) (|x>_i ∧ [f]_(i,j) ∧ |y>_j).
```

The summation line declares that term products use `∧` and their reduction uses
`⇕`; the bra-ket itself is left uncluttered.

Because each state is one-hot, exactly one summand is active. Therefore

```text
E_[f](x,y) = f(x,y).
```

The proof does not depend on cancellation among several active terms. This observation also explains why OR-AND selection would return the same scalar for one-hot inputs, even though the manuscript's coefficient algebra and decomposition use XOR-AND.

For fixed `x,y`, evaluation is linear in the operator coefficients over `GF(2)`:

```text
E_(A ⇕ B)(x,y) = E_A(x,y) ⇕ E_B(x,y).
```

This is **coefficient-space linearity**. It does not assert that `f(x,y)` is a linear Boolean function of `x,y`, and it is not linearity over the real or complex numbers.

Extended to arbitrary vectors in `GF(2)^2`, the contraction is separately
linear in the bra, operator coefficients, and ket. The truth-state encoding
`x -> [x,¬x]^T` is affine rather than linear because it does not send scalar
zero to the zero vector. These facts must be stated together to prevent an
incorrect claim that every represented Boolean function is linear in its
logical operands.

## 4. Transformations as operand-frame changes

Let

```text
P = [0 1]
    [1 0].
```

Then the following identities hold with the declared axes:

```text
[f(Y,X)]       = [f]^T
[f(¬X,Y)]      = P[f]
[f(X,¬Y)]      = [f]P
[f(¬X,¬Y)]     = P[f]P
[¬f]           = 1 ⇕ [f]       (entrywise)
```

The historical language of 90-, 180-, and 270-degree rotations can remain as visual shorthand, but the theorem language should say **transpose and row/column permutation induced by operand swap or polarity change**. Their computational role is to translate connectives over signed row/column variables into an identical positive operand frame before fusion. The pair compiler now performs that signed-variable normalization and recursively fuses matching pair tokens; it retains four-assignment retabulation as an explicit fallback. Alignment of arbitrary compound operands remains outside the implemented scope.

### 4.1 Bracketed operator notation and the XOR/XNOR geometry

For a binary logical operator `Θ`, write its numeric correspondence matrix as
`[Θ]`. The function-indexed notation `C_f` remains useful in generic theorems,
but operator examples should use brackets:

```text
[Θ] := the CM of Θ,
[Θ] = [⇕] = [[0,1],[1,0]] when Θ is XOR.
```

With true-first row and column axes,

```text
[⇔] = [[1,0],[0,1]],
[⇕] = [[0,1],[1,0]] = rot_90([⇔]) = ¬[⇔].
```

The Impax operator is the tautological operator. Its glyph is a centered overlay
of `⇔` and `⇕`, and its matrix satisfies

```text
[\impax] = [⇔] ⇕ [⇕] = [[1,1],[1,1]].
```

Here “superposition” means entrywise Boolean XOR of the two disjoint numeric
matrices. It does not mean quantum superposition. The paper should use the
established XNOR glyph `⇔` (LaTeX `\Leftrightarrow`); `\Rightleftarrow` is a
different or renderer-dependent command and is not the XNOR symbol used by the
source manuscript.

## 5. Operator fusion

An operand frame comprises the underlying operands, their row/column order,
their polarity, and the truth-state order on both axes. **Operand-aligned
fusion** means that two tokens have been brought into an identical frame before
entrywise combination. This replaces the less transparent planning term
“common-frame fusion.”

Let `f`, `g`, and `phi` be binary Boolean connectives. Define the fused token by applying `phi` entrywise:

```text
[f phi g]_(i,j) := phi([f]_(i,j), [g]_(i,j)).
```

For the same operands in the same frame,

```text
phi(E_[f](x,y), E_[g](x,y)) = E_[f phi g](x,y).
```

The proof is one-hot selection: both evaluations select the same position `(i,j)`, so applying `phi` before or after selection gives the same bit. It is not a claim that arbitrary `phi` distributes over XOR.

The compiler-level rule has a stronger precondition than the scalar identity. The two subexpressions must either already share the ordered operand pair or be soundly transformed into an identical frame. The implementation records canonical row/column variable names in each pair surrogate, absorbs signed-literal order and polarity into the token, and fuses only when those canonical names match. It does not yet establish structural equivalence between arbitrary compound operands.

## 6. Logical matrices as a symbolic lift

Let `F` be the Boolean algebra of formulas modulo logical equivalence. Put
`X_1=X`, `X_2=¬X`, `Y_1=Y`, and `Y_2=¬Y`. For a symbolic operator coefficient
array `Θ`, use the source manuscript's main-text notation
`[M_(X Θ Y)]`—typeset as `[\mathcal{M}_{X\Theta Y}]`—and define

```text
[M_(X Θ Y)] := ⇕_(i,j) Θ_ij |X_i><Y_j|
             = [ X_i Θ_ij Y_j       X_i Θ_ij ¬Y_j  ]
               [ ¬X_i Θ_ij Y_j      ¬X_i Θ_ij ¬Y_j ]
             = [ X Θ Y               X Θ ¬Y  ]
               [ ¬X Θ Y              ¬X Θ ¬Y ].
```

The first expression is the explicit XOR reduction of the outer-product terms;
in the two following matrices, every cell separately XOR-reduces the repeated
`i,j in {1,2}` terms. Letting `iota(1)=1` and `iota(2)=0`, the
position-indexed LM coefficient `Θ_ij` abbreviates the assignment-indexed
CM coefficient `Θ_(iota(i),iota(j))`. Thus the LM sequence
`(Θ_11,Θ_12,Θ_21,Θ_22)` is relabeled as
`(Θ_11,Θ_10,Θ_01,Θ_00)` in the numeric CM.
The manuscript macro is `\Theta_{ij}\otbktwo{X_i}{Y_j}`. The shorter
`L_f(X,Y)` remains an appendix
alias when a theorem is parameterized extensionally by the Boolean function
`f` rather than by symbolic coefficients `Θ_ij`.

This is a polarity-orbit matrix with entries in `F`, not an algebraic-normal-form polynomial. A valuation `v : F -> B` acts entrywise and preserves `¬`, `∧`, and `⇕`. Hence valuation commutes with all well-typed LM Boolean operations and with XOR-AND contraction.

There is a terminology collision to manage. Zhao, Gao, and Cheng use
“logical matrix” for a **numeric** matrix whose columns are standard basis
vectors, and call the unique `2 x 2^n` representative of a Boolean function
its logical structure matrix. That object is not the formula-valued LM defined
here. In comparisons, write **formula-valued LM** and **STP logical structure
matrix** rather than relying on the initials alone.

Under the positive valuation `v_T(X)=v_T(Y)=1`,

```text
v_T([M_(X Θ Y)]) = [Θ].
```

Under a general valuation, `v(L_f(X,Y))` is the row/column-permuted CM determined by the truth values of `X` and `Y`. This gives a precise LM-to-CM relationship: an LM is a symbolic family of polarity-indexed formulas, while a CM is a numeric valuation of that family in a declared frame.

This construction may be a useful symbolic lift, but it is not automatically more expressive than the underlying Boolean function. Boolean outer products of logical vectors and matrix-operator bases are established antecedents. A focused search did not locate the exact formula-valued polarity-orbit/valuation assembly, but that does not establish novelty relative to symbolic vector logic, projector logics, or Boolean tensor formalisms.

## 7. Logical measurement pairing

The term **logical measurement pairing** may be retained if it is defined algebraically and explicitly separated from physical measurement. For a formula `A`, define the formal state `|A> = [A,¬A]^T` and its row form `<A| = [A,¬A]`. For formula-valued bras, LMs, and kets, the XOR-AND contraction returns another Boolean formula or equivalence class in `F`. A valuation of that result equals the corresponding numeric contraction after valuing every component.

The intended interpretation is relational: the result states a compatibility or constraint among the measured formulas and the connective encoded by the LM. It does not establish a quantum observable, Hermiticity, projectors, a Born probability, state collapse, entanglement, or quantum speedup.

Main-text terminology should therefore use one of:

- logical measurement pairing;
- relational Boolean pairing;
- symbolic operator evaluation.

The first is closest to the historical manuscript. A short comparison with Eigenlogic can explain why this use is nonphysical.

## 8. Relation to STP structure matrices and ANF

For an `n`-variable Boolean function, its ordered truth vector has `2^n` entries. In semi-tensor-product work, a logical structure matrix commonly places that truth vector in one row and its complement in a second row, subject to encoding/order conventions. For two variables, vectorizing `[f]` produces the same truth data as the appropriate structure-matrix row.

The algebraic normal form (ANF) is different. Its coefficients multiply square-free monomials in the uncomplemented variables and are obtained from the truth vector by a Boolean Möbius transform. Zhao, Gao, and Cheng use Kronecker products of vectors `[1,x_i]^T` to enumerate that monomial basis; they do not simply tensor already-complete polynomials to create one ever-larger polynomial. Their Theorem 3.2 gives a matrix conversion from the truth-table row to the ANF coefficient row. Their Section 4 then uses “linearity” for functions with only linear polynomial terms and for invariant/variant directions satisfying `f(x+a) ⇕ f(x)=0` or `1`. Neither usage is the coefficient-space linearity of Section 3 above.

Accordingly:

```text
truth vector  <->  vectorized CM  <->  first row of an STP structure matrix
      |
      +---- invertible Boolean transform ----> ANF coefficient vector

formula-valued polarity orbit ---- valuation ----> numeric CM
              (LM)
```

These are related coordinate systems or symbolic lifts, not interchangeable names.

### Frozen representation distinction

The following distinction is a program-level invariant and should appear in
both the representation figure and the related-work text:

> **LMs are formula-valued polarity-orbit matrices. Positive valuation produces
> the numeric CM. ANF coefficients instead come from a Boolean Möbius transform
> of the truth vector.**

This statement is about representation type, not expressive power: the LM,
numeric CM/truth vector, and ANF coefficients all encode or derive from the same
underlying Boolean function. Zhao, Gao, and Cheng's construction is therefore
best described as an ANF/polynomial coordinate system related to a structure
matrix, not as an LM equivalent.

## 9. Higher arity

An explicit `n`-variable Boolean operator requires `2^n` truth entries. The neutral representation is an order-`n` tensor with side length two. It may be flattened to a length-`2^n` vector. For an even split of `2m` variables, it may also be reshaped to a `2^m x 2^m` matrix after the row-variable and column-variable groups are declared.

The historical `n x n`, `n!`, and `2^n x 2^n` claims should not be reused. Higher-arity LMs and CMs belong in the first paper only as a corrected definition and limitation unless a nontrivial tensor theorem or algorithm is proved.

## 10. Candidate theorem package for paper 1

| Result | Main text | Appendix | Novelty role |
|---|---|---|---|
| CM selection semantics | Proposition with visual example | Four-case proof | Foundation; antecedented |
| Coefficient-space linearity | Precise lemma | Bilinearity proof over `GF(2)` | Clarification, not headline novelty |
| Operand-frame transformations | Compact table/figure | Index proof | Enables normalization |
| Operand-aligned operator fusion | Central theorem | One-hot and signed-permutation proof | Foundation for compiler rule; pointwise identity antecedented |
| Normalization-plus-fusion soundness | Central compiler theorem | Induction over rewrite steps | Candidate distinctive contribution |
| LM valuation commutes with operations/pairing | Optional theorem | Homomorphism proof | Potentially distinctive symbolic formulation |
| Complexity and break-even conditions | Main methods/result | Derivations and raw schema | Required for utility claim |

## 11. Claims that remain excluded

- novelty of representing Boolean connectives by matrices in general;
- ordinary real/complex matrix algebra as the CM evaluation semantics;
- equivalence of Boolean difference with ordinary modulo;
- quantum measurement, superposition, collapse, entanglement, or speedup;
- polynomial-size explicit CMs for arbitrary Boolean functions;
- unqualified claims that CM computation is generally faster or smaller.

## 12. Open gates before manuscript drafting

1. Check the LM symbolic-lift and valuation-commutation formulation against closer symbolic vector-logic and Boolean-tensor antecedents.
2. Formalize the exact normalizer used by the implementation, including structural equivalence, variable order, polarity metadata, aliasing, and termination.
3. Prove rewrite-system soundness and connect every code artifact to the typed objects above.
4. Freeze a validation protocol that measures compilation, memory, kernel, wrapper, and end-to-end cost against sharing-aware baselines.
