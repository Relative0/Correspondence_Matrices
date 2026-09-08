# From logical matrices to higher-dimensional CMs — script v1

Status: editorial proposal; not yet content-approved  
Target duration: 5:00–5:20  
Target delivery: conversational, precise, 135–145 WPM

## 0:00–0:24 — A matrix before the bits

**Voiceover**

The last lesson ended with a two-by-two matrix of zeros and ones. But the paper
also uses a matrix whose cells still contain logical expressions. It calls that
object a logical matrix—an L M.

This distinction is the bridge to larger correspondence matrices: expressions
first, positive valuation second, binary C M afterward.

**Visual**

Keep the previous lesson's 2×2 outline and state labels. Replace each binary
entry with an expression tile. Use violet for unevaluated expressions and white
for valued bits. Display the bridge:

```text
logical expressions → positive valuation → binary entries
```

## 0:24–1:10 — What an LM contains

**Voiceover**

Start with the conjunction of X and Y. The paper's basic logical matrix places
four mutually exclusive state expressions in the four positions: X and Y;
X and not Y; not X and Y; and not X and not Y.

Notice what has changed from the operator CM. A CM entry is a binary
coefficient. An LM entry is itself a logical expression. The row and column
state order is still X, not X, by Y, not Y.

The paper can combine these base logical matrices to represent other operators.
For example, its equivalence LM contains equivalence expressions on one
diagonal and exclusive-or expressions on the other.

**Visual**

Build the paper's base LM:

```text
M_XY = [ X∧Y      X∧¬Y  ]
       [ ¬X∧Y     ¬X∧¬Y ]
```

Then show, without deriving every term, the paper's equivalence LM:

```text
M_(X↔Y) = [ X↔Y   X XOR Y ]
          [ X XOR Y   X↔Y ]
```

Keep the `LM: expression-valued` badge visible.

## 1:10–1:50 — Positive valuation

**Voiceover**

Now apply the paper's positive valuation, written V sub T, to every entry. In
that valuation, an unnegated state is positive and its complement is not. The
expressions become zeros and ones.

Applied to the equivalence LM, positive valuation produces the equivalence CM:
one on the agreement diagonal, zero on the disagreement diagonal.

This is the paper's defining relationship: a correspondence matrix is a
positive valuation of a logical matrix. The LM and CM share a shape and an
ordering, but they do not contain the same kind of entries.

**Visual**

Pass a vertical `V_T` scan through the equivalence LM. Each expression resolves
to a bit:

```text
[1 0]
[0 1]
```

Do not morph the LM into a generic truth table. Maintain cell-to-cell identity
through valuation.

## 1:50–2:42 — Growing to four variables

**Voiceover**

For four variables, the paper does more than reshape a column of truth values.
It begins with smaller logical matrices, projects them into tensor-product
structure, substitutes compound expressions, and forms a four-by-four LM.

The simplest displayed construction starts from W and X on one side and Y and
Z on the other. Sixteen conjunctions appear—one for each choice of a variable
or its negation. Those expression-valued cells form a four-by-four logical
matrix.

Then operators can modify and combine those logical components. The important
idea is the construction path:

small logical state matrices, tensor structure, compound LM, positive
valuation, binary CM.

**Visual**

Show the paper's diagonal projection from the 2×2 `M_AB` into the 4×4 tensor
product, then expand to the sixteen expression cells for `WXYZ`. Reveal rows
progressively rather than all at once. Keep the construction rail visible:

```text
2×2 LM → tensor/projection → 4×4 LM → V_T → 4×4 CM
```

## 2:42–3:50 — The paper's worked 4×4 example

**Voiceover**

The paper's worked example is the compound rule: W exclusive-or X, implies,
not Y and Z.

The two inner rules are computed first. Their logical matrices feed an outer
implication modifier. Because implication is false only when its left side is
true and its right side is false, only the corresponding tensor components are
excluded; the retained components combine into the larger LM.

After positive valuation, the paper obtains this four-by-four CM:

one-one-zero-zero;
one-one-one-zero;
zero-zero-one-one;
one-zero-one-one.

Its ordering is part of its meaning. In the paper's measurement form, the left
state is ordered by Y and W, and the right state by X and Z. This is a compound
four-variable matrix, not one of the sixteen elementary two-input operator
CMs.

**Visual**

Build the expression as two inner modules feeding implication:

```text
(W XOR X) → (¬Y AND Z)
```

Show the paper's equivalent notation `(W XOR X) → (Y ↓ Z)` as a secondary
label. Animate the implication modifier selecting the tensor components, then
apply `V_T` and reveal exactly:

```text
[1 1 0 0]
[1 1 1 0]
[0 0 1 1]
[1 0 1 1]
```

Label row state `(Y,W)` and column state `(X,Z)` in the paper's positive/negated
basis order.

## 3:50–4:28 — Retrieval: LM or CM?

**Voiceover**

Pause on one highlighted cell before valuation. It contains a logical
expression, not a bit. Is the object currently an LM or a CM? And after positive
valuation, what kind of entry must occupy that same position?

*[Four-second retrieval pause.]*

Before valuation it is an LM, because its entries are logical expressions.
After valuation the corresponding entry is binary, and the resulting matrix is
the CM.

**Visual**

Split the screen around one persistent cell. Left: violet expression tile in
the LM. Right initially empty. After the pause, pass `V_T` across the divider
and reveal the corresponding white binary entry in the CM.

## 4:28–4:52 — Higher dimensions and the boundary

**Voiceover**

The paper extends this construction by induction. For a logical expression
built from two-n logical subexpressions, it gives a square two-to-the-n by
two-to-the-n logical matrix, followed by the corresponding positive valuation.

That square construction belongs to the paper. The repository we study later
also supports rectangular two-by-eight and eight-by-two output layouts, but by
a different implementation route. We should not pretend those are the same
definition merely because the final objects are matrices of bits.

**Visual**

Grow the square sequence `2×2 → 4×4 → 8×8` without populating decorative cells.
Attach the label `paper construction`. On a separate, dimmed rail preview
`repository layouts: 4×4, 2×8, 8×2`, joined by a visible discontinuity marker.

## 4:52–5:08 — Close

**Voiceover**

The distinction to retain is simple. A logical matrix keeps logical expressions
in its entries. Positive valuation produces the corresponding binary CM. The
paper uses that relationship to build larger square matrices for compound
logic.

Next we will follow the repository's different path and see exactly how ordered
row and column variable lists determine its dense output layout.

**Visual**

Settle the sequence `LM → V_T → CM`, then hand the same compound-function token
to a new rail labeled `repository materialization`.
