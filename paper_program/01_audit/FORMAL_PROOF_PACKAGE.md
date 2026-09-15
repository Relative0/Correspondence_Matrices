# Formal result package for Correspondence Matrices

Date: 2026-09-14  
Prospective author: **Brian Theory**  
Status: appendix-ready mathematical draft; implementation-level claims remain conditional where marked

## 1. Conventions

Let `B = {0,1}`. Write `a ⇕ b` for exclusive-or and `a ∧ b` for
conjunction. The same set becomes the field `GF(2)` when `⇕` is read as field
addition and `∧` as field multiplication. All sums and products below are in
this Boolean/GF(2) algebra unless explicitly identified otherwise.

For `x in B`, define the true-first state

```text
|x> = [x, ¬x]^T,              <x| = [x, ¬x].
```

Index `1` denotes the positive component and index `0` the negative component,
so `|x>_1=x` and `|x>_0=¬x`. For a binary Boolean function
`f : B^2 -> B`, define

```text
          [ f(1,1)  f(1,0) ]
C_f  :=   [ f(0,1)  f(0,0) ].
```

The row and column order is therefore `(1,0)`, not the NumPy-default order
`(0,1)` used by several current implementation paths.

## 2. CM representation and evaluation

### Proposition 1 (representation is a bijection)

The map `f -> C_f` is a bijection between binary Boolean functions and
`2 x 2` matrices over `B`.

**Proof.** A binary Boolean function is completely determined by its four
values on `(1,1)`, `(1,0)`, `(0,1)`, and `(0,0)`. These are exactly the four
entries of `C_f`. Conversely, any four-bit matrix assigns one output to each
of those inputs and therefore defines one binary Boolean function. There are
`2^4=16` objects on each side. `□`

### Proposition 2 (XOR-AND selection semantics)

Define

```text
E_C(x,y) = <x| C |y>_(⇕,∧)
         = ⇕_(r,s in {1,0}) |x>_r ∧ C_(r,s) ∧ |y>_s.
```

Then `E_(C_f)(x,y)=f(x,y)` for every `f,x,y`.

**Proof.** The vector `|x>` has exactly one nonzero component: the component
indexed by `x`. The same is true of `|y>`. Hence all four summands except
`C_f(x,y)` contain a zero factor. The remaining summand is
`1 ∧ C_f(x,y) ∧ 1=C_f(x,y)=f(x,y)`. `□`

**Interpretive consequence.** The displayed operation replaces arithmetic
multiplication with AND and arithmetic addition with XOR. It is not ordinary
integer, real, or complex matrix multiplication. For bit-valued entries it is
precisely matrix contraction over `GF(2)`. Because the states are one-hot,
OR-AND selection happens to return the same scalar, but it does not provide the
same coefficient algebra for general vectors or decompositions.

### Proposition 3 (coefficient-space linearity)

For fixed `x,y`, the map `C -> E_C(x,y)` is a linear functional from
`GF(2)^(2 x 2)` to `GF(2)`:

```text
E_(A ⇕ B)(x,y) = E_A(x,y) ⇕ E_B(x,y),
E_0(x,y) = 0.
```

**Proof.** Distribute AND over XOR in each of the four summands and regroup
the finite XOR. Equivalently, Proposition 2 says that the map selects one
coordinate, and coordinate projection is linear. `□`

This is linearity in the four operator coefficients. It does **not** mean that
the represented Boolean function is linear in its operands. In ANF language,
a function is linear or affine only when its polynomial degree is at most one.

More generally, if the contraction is extended from one-hot states to arbitrary
vectors `u,v in GF(2)^2`, then `u^T C v` is separately linear in `u`, `C`, and
`v` by distributivity. This is the ordinary multilinearity of matrix
contraction over `GF(2)`. The encoding `x -> [x,¬x]^T` is itself affine rather
than linear—it maps scalar zero to `[0,1]^T`, not the zero vector—so this fact
still does not make an arbitrary represented `f(x,y)` linear in `x` and `y`.

### Proposition 4 (basis decomposition and coefficient measurement)

Let `E_rs` be the `2 x 2` matrix containing `1` at position `(r,s)` and zero
elsewhere. Then

```text
C_f = ⇕_(r,s) f(r,s) E_rs,
<r| C_f |s>_(⇕,∧) = f(r,s).
```

**Proof.** At each position `(i,j)`, only the summand with `(r,s)=(i,j)` is
nonzero. The second identity follows from Proposition 2. `□`

## 3. Operand transformations

Let

```text
P = [0 1]
    [1 0].
```

### Proposition 5 (signed operand-permutation identities)

With the declared true-first axes,

```text
C_(f(Y,X))       = C_f^T,
C_(f(¬X,Y))      = P C_f,
C_(f(X,¬Y))      = C_f P,
C_(f(¬X,¬Y))     = P C_f P,
C_(¬f)           = J ⇕ C_f,
```

where `J` is the all-ones matrix, the last XOR is entrywise, and products with
`P` are XOR-AND matrix products (equivalently, direct row/column permutations).

**Proof.** For example, row `x` and column `y` of `P C_f` select row `¬x`
and column `y` of `C_f`, so the entry is `f(¬x,y)`. Right multiplication by
`P` similarly swaps the column index. Transposition exchanges the two input
indices. Applying negation to every output flips every matrix bit, which is
entrywise XOR with `J`. `□`

Here multiplication by `P` can be understood simply as a row or column
permutation. No arithmetic sum of entries occurs. General transformation
theorems should specify transpose and axis permutations; for the particular
XOR/XNOR pair below, a 90-degree geometric rotation is also an exact and useful
description.

### Corollary 5.1 (XOR/XNOR rotation and Impax superposition)

In the true-first frame, let

```text
[⇔] = [1 0]       and       [⇕] = [0 1].
      [0 1]                       [1 0]
```

Then

```text
[⇕] = rot_90([⇔]) = ¬[⇔],
[\impax] = [⇔] ⇕ [⇕] = J,
```

where the second `⇕` is entrywise XOR and `J` is the all-ones matrix.
Consequently `E_[\impax](x,y)=1` for all `x,y in B`.

**Proof.** Rotating either the identity matrix clockwise or counterclockwise
places its two ones on the antidiagonal, giving `[⇕]`. Entrywise complement has
the same result. The supports of `[⇔]` and `[⇕]` are disjoint and together cover
all four entries, so their entrywise XOR is `J`. Proposition 2 then selects a
one for every operand assignment. `□`

This identity motivates the `⇕` symbol and the centered Impax overlay glyph.
“Superposition” here is a Boolean matrix operation, not a quantum state claim.

## 4. Operand-aligned fusion

An **operand frame** records:

1. the two underlying operands;
2. their order on the row and column axes;
3. whether either is negated; and
4. the state/basis ordering on each axis.

Two operator occurrences are **operand-aligned** when these four pieces of
metadata agree. “Common-frame fusion” in earlier planning notes means fusion
after establishing this condition. The term **operand-aligned fusion** is more
explicit and is recommended for the paper.

For any binary Boolean connective `phi`, define entrywise fusion

```text
(C_f [phi] C_g)_(r,s) = phi(C_f(r,s), C_g(r,s)).
```

### Theorem 6 (same-operands fusion)

If `C_f` and `C_g` are applied to the same ordered operands in the same frame,
then

```text
phi(E_(C_f)(x,y), E_(C_g)(x,y))
    = E_(C_f [phi] C_g)(x,y).
```

**Proof.** Both contractions select position `(x,y)`. The left side is
`phi(C_f(x,y),C_g(x,y))`, which is exactly the entry selected from the fused
matrix on the right. The argument does not require `phi` to distribute over
XOR. `□`

### Corollary 6.1 (fusion after signed alignment)

Suppose two subexpressions depend on the same two underlying operands but use
different order or polarity. Apply Proposition 5 to rewrite each token into a
declared target frame. Their outer connective can then be fused entrywise, and
the resulting token has the same truth value as the unfused expression for
every valuation.

**Proof.** Each transformation preserves the value of its source expression
when interpreted in the target frame by Proposition 5. Apply Theorem 6 to the
two transformed tokens. `□`

### Theorem 7 (implemented pair-compiler soundness)

Fix one declared row variable `R` and one declared column variable `C`. When
the pair compiler returns `_Pair(R,C,t)` for a formula `e`, token `t` satisfies

```text
E_t(r,c) = e[r/R, c/C]
```

for all `r,c in B`, after the declared fixed-variable substitutions. Its final
dense lift therefore agrees with ordinary Boolean evaluation on every complete
assignment.

**Proof.** Structural induction over the successful pair construction:

1. For a binary connective applied to signed literals, Proposition 5 proves
   that `cm_align_signed_operands` converts the connective token into the
   positive `(R,C)` frame.
2. If a child pair represents `e`, bitwise token complement represents `¬e`.
3. If two child pairs share `(R,C)`, Theorem 6 proves that `cm_compose` returns
   the token for their outer connective.
4. If structural construction cannot continue but the live support is exactly
   one row and one column variable, the fallback evaluates all four assignments
   and places those four results in the declared token order; Proposition 1
   makes that token exact.

Every successful branch therefore preserves the invariant. If no pair is
returned, the existing CM IR evaluator handles the complete expression. The
final `lift_cm` conversion reverses the true-first token axes into the dense
false-first indexing convention and broadcasts only variables absent from the
pair. Consequently both return paths agree with the source formula. `□`

The recursion terminates because each recursive call receives a strict AST
subexpression. Direct retabulation visits a finite AST under four valuations.
For a fixed `(R,C)` frame the resulting four-bit token is canonical for the
represented truth function by Proposition 1, although the surrounding CM IR
and source formula are not claimed to have a globally canonical syntax.

**Scope boundary.** The implemented structural alignment recognizes signed
row/column **variables** and recursively fuses pair tokens. It does not yet
treat arbitrary multi-variable formulas as two opaque logical operands with
signed-permutation metadata. That broader compiler claim remains future work.

## 5. Logical matrices

Let `F` be the Boolean algebra of formulas modulo logical equivalence. For any
formula `A`, define the formal state

```text
|A> = [A, ¬A]^T,              <A| = [A, ¬A].
```

Throughout this section, “formula-valued LM” means a matrix with entries in
`F`. It is not Zhao, Gao, and Cheng's numeric “logical matrix,” whose columns
are standard basis vectors, nor their `2 x 2^n` logical structure matrix.

Let `X_1=X`, `X_0=¬X`, `Y_1=Y`, and `Y_0=¬Y`. Define the Boolean outer-product
basis

```text
B_rs(X,Y) = |X_r><Y_s|,
```

where matrix-entry multiplication is conjunction. Define the logical matrix

```text
L_f(X,Y) = ⇕_(r,s in {1,0}) f(r,s) B_rs(X,Y).
```

### Theorem 8 (formula-valued polarity-orbit form)

The outer-product definition is equivalent in `F` to

```text
            [ f(X,Y)   f(X,¬Y) ]
L_f(X,Y) =  [ f(¬X,Y)  f(¬X,¬Y) ].
```

**Proof.** The upper-left entry of the outer-product sum is

```text
f(1,1)XY ⇕ f(1,0)X¬Y ⇕ f(0,1)¬XY ⇕ f(0,0)¬X¬Y,
```

which is the disjoint-minterm expansion of `f(X,Y)`. In the upper-right entry,
the two components of every `|Y_s>` are exchanged, yielding `f(X,¬Y)`.
Exchanging the `X` components gives the lower-left entry, and exchanging both
gives the lower-right. `□`

### Theorem 9 (valuation produces a CM in the valuation frame)

For a valuation `v : F -> B`, let `x=v(X)` and `y=v(Y)`. Then

```text
v(L_f(X,Y)) = P^(1-x) C_f P^(1-y).
```

In particular, the positive valuation `v(X)=v(Y)=1` gives
`v(L_f(X,Y))=C_f`.

**Proof.** Apply `v` entrywise to the matrix in Theorem 8. Its entries become
`f(x,y)`, `f(x,¬y)`, `f(¬x,y)`, and `f(¬x,¬y)`. If `x=0`, this is `C_f` with
its rows exchanged; if `y=0`, its columns are exchanged. `□`

### Lemma 10 (logical-state inner product)

For formulas `A,B`,

```text
<A|B>_(⇕,∧) = (A ∧ B) ⇕ (¬A ∧ ¬B) = (A ⇔ B).
```

**Proof.** The two conjunctions are disjoint. Their disjunction is the usual
equivalence formula, and disjunction equals XOR on disjoint terms. `□`

### Theorem 11 (LM coefficient extraction)

For `r,s in {1,0}`,

```text
<X_r| L_f(X,Y) |Y_s>_(⇕,∧) = f(r,s).
```

**Proof.** By Lemma 10, `<X_r|X_p>` is `1` when `r=p` and `0` otherwise; the
same holds for `<Y_q|Y_s>`. Contracting the basis expansion therefore
eliminates every coefficient except `f(r,s)`, whose two remaining state
pairings both equal `1`. `□`

### Theorem 12 (general logical measurement pairing)

For arbitrary formulas `A,B`,

```text
<A|L_f(X,Y)|B>
 = ⇕_(r,s) f(r,s) ∧ (A ⇔ X_r) ∧ (B ⇔ Y_s).
```

**Proof.** Substitute the basis expansion of `L_f`, use associativity and
distributivity of the Boolean-ring operations, and apply Lemma 10 to each
left and right state pairing. `□`

The output is a Boolean compatibility constraint. “Measurement” here is an
algebraic coefficient/relationship extraction, not a physical measurement.

### Theorem 13 (valuation commutes with LM operations and pairing)

If `v : F -> B` is a Boolean-algebra valuation, then for well-typed
formula-valued matrices and vectors,

```text
v(A ⇕ B) = v(A) ⇕ v(B),
v(A ∧ B) = v(A) ∧ v(B),
v(¬A) = ¬v(A),
v(<A|L|B>) = <v(A)|v(L)|v(B)>.
```

**Proof.** The first three equations are the defining homomorphism properties
of a Boolean valuation. A finite XOR-AND contraction is built only from these
operations, so repeated use of the homomorphism identities moves `v` through
the contraction entry by entry. `□`

## 6. LM versus ANF: the frozen distinction

For `n` variables, index valuations by subsets `S` of `{1,...,n}`: the variables
in `S` are assigned `1`, and the others `0`. Let `t_S=f(1_S)` be the truth
vector, and write the algebraic normal form as

```text
f(x_1,...,x_n) = ⇕_(T subseteq {1,...,n}) a_T ∧ product_(i in T) x_i.
```

### Theorem 14 (Boolean Möbius conversion)

The truth values and ANF coefficients satisfy

```text
t_S = ⇕_(T subseteq S) a_T,
a_T = ⇕_(S subseteq T) t_S.
```

Thus the ANF coefficient vector is an invertible Boolean Möbius transform of
the truth vector.

**Proof.** At valuation `1_S`, monomial `product_(i in T)x_i` is `1` exactly
when `T subseteq S`, proving the first identity. Substitute it into the second.
For fixed `U subseteq T`, coefficient `a_U` appears `2^(|T|-|U|)` times. This
count is odd only when `U=T`; every other coefficient cancels in `GF(2)`.
The result is `a_T`. `□`

### Corollary 14.1 (LMs are not ANF coefficient objects)

For two variables, vectorizing `C_f` gives the ordered truth vector. Applying
the transform in Theorem 14 gives the ANF coefficients. By contrast, every
entry of `L_f(X,Y)` is a formula from the polarity orbit of `f`, and a valuation
of the entire LM gives a row/column-permuted numeric CM by Theorem 9.

Therefore:

> **LMs are formula-valued polarity-orbit matrices. Positive valuation produces
> the numeric CM. ANF coefficients instead come from a Boolean Möbius transform
> of the truth vector.**

The objects should not be identified: their entry types, coordinate meanings,
and native operations differ. With fixed conventions they are informationally
interconvertible at the level of the underlying truth function. This is a
type/coordinate distinction, not a claim that one contains more truth-functional
information. It should appear both in the representation figure and in related
work, specifically when discussing Zhao, Gao, and Cheng.

Zhao, Gao, and Cheng's separate linearity results also do not duplicate
Proposition 3: they discuss ANF expressions containing only linear terms and
directions `a` for which `f(x+a) ⇕ f(x)` is constantly `0` or `1`.

## 7. Higher arity and explicit size

### Proposition 15 (entry count)

An explicit table/operator for an arbitrary `n`-variable Boolean function has
`2^n` output bits. It may be represented as an order-`n` tensor of side length
two, a length-`2^n` vector, or—after an even `2m` variable split—a
`2^m x 2^m` matrix.

**Proof.** There are two independent choices for each of `n` Boolean inputs,
so there are `2^n` valuations. The stated tensor, vector, and matrix shapes all
contain exactly `2^n` entries. `□`

No explicit representation of all truth values avoids this worst-case
exponential output size. Compression or symbolic sharing must be analyzed as a
separate representation.

## 8. Proof and claim status

| Result | Mathematical status | Implementation status | Main-paper role |
|---|---|---|---|
| Propositions 1-5 | Complete elementary proofs | 4-bit checks exist | Definitions and clarification |
| Theorem 6 | Complete | `cm_compose` implements standalone exact-frame pointwise fusion | Core identity, not broad novelty |
| Corollary 6.1 | Complete | Transform helpers exist separately | Alignment rule |
| Theorem 7 | Proof drafted for the concrete pair invariant | Signed-variable alignment, recursive token fusion, direct-retabulation fallback, and layout conversion are implemented and property-tested | Candidate contribution within the stated scope |
| Theorems 8-13 | Complete in formulas modulo equivalence | Bounded numeric checks exist; formula engine not yet tied to compiler | Compact LM section/appendix |
| Theorem 14 | Classical result | Finite checker added for two variables | Related-work distinction |
| Proposition 15 | Complete counting proof | Output guards exist | Limitation |

Independent mathematical review is still required before submission, especially
for notation consistency and for any claim that Theorem 7 describes the actual
released compiler.
