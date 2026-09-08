# From logical matrices to higher-dimensional CMs — script v2

Status: teacher-audited editorial proposal; not yet content-approved  
Target duration: 3:55–4:15  
Target delivery: calm, precise, 135–145 WPM

## 0:00–0:28 — Expressions before bits

**Voiceover**

A correspondence matrix contains binary outputs. A logical matrix keeps one
step more information: its cells contain logical expressions.

Here are the four input states for X and Y, written directly into their matrix
positions: X and Y; X and not-Y; not-X and Y; not-X and not-Y. Because these
entries are expressions rather than bits, this is a logical matrix—an LM.

**Visual**

Build one 2×2 frame from the same four state cards used in the previous lesson.
Place the expression tiles directly into their cells:

```text
M_XY = [ X∧Y      X∧¬Y  ]
       [ ¬X∧Y     ¬X∧¬Y ]
```

Badge the object `LM: expression-valued`.

## 0:28–1:12 — Positive valuation makes the CM

**Voiceover**

The paper then applies a positive valuation, written V sub T, to each
expression. Under this valuation, a positive variable state receives one and
its complemented state receives zero; the logical operations are evaluated
consistently from those values.

For equivalence, the expression is true in the two agreement positions and
false in the two disagreement positions. After positive valuation, its LM
therefore yields the binary matrix one-zero, zero-one.

That is the central relationship: the LM holds logical expressions; applying
positive valuation entry by entry produces the corresponding binary CM. Shape
and cell order stay fixed while the entry type changes.

**Visual**

First show the paper's equivalence LM:

```text
[ X↔Y       X XOR Y ]
[ X XOR Y   X↔Y     ]
```

Pass a gold `V_T` scan through it. Maintain each cell's identity as the tiles
resolve to `[[1,0],[0,1]]`. Keep a persistent rail:
`LM expressions → V_T → CM bits`.

## 1:12–2:00 — How a larger LM is built

**Voiceover**

To represent a compound rule with four variables, the paper builds rather
than reshapes. First it forms logical matrices for smaller expressions. Then a
tensor-and-projection construction places their combinations into a
four-by-four expression grid. Finally, the outer logical operator determines
which combined expressions remain in the larger LM.

You do not need to perform the tensor algebra here. What matters is what each
stage contributes: the smaller LMs supply expressions; the construction gives
every combined state a declared position; and the outer operator supplies the
compound rule. Only after that does positive valuation turn the larger LM into
a binary CM.

**Visual**

Use a three-stage construction, revealing only the cells needed to understand
each step:

```text
smaller LMs → positioned combinations in a 4×4 LM → outer operator → V_T
```

Show tensor/projection notation as a secondary label beside the positioning
action, not as a full-screen equation. Never make the 4×4 grid appear by
stretching or reshaping a truth vector.

## 2:00–3:04 — Follow the paper's worked example

**Voiceover**

The paper's example asks whether W exclusive-or X implies not-Y and Z. Compute
the two inner expressions first: W XOR X on the left, and not-Y AND Z on the
right. The outer operator is implication, which is false only when its left
side is true and its right side is false.

Those components are combined in the expression-valued four-by-four LM. After
positive valuation, the resulting CM has rows:

one-one-zero-zero;
one-one-one-zero;
zero-zero-one-one;
one-zero-one-one.

The ordering is part of the result. In the paper's measurement form, the row
state is ordered by Y and W, and the column state by X and Z. So a cell can be
interpreted only together with those state labels.

This four-by-four object represents one compound four-variable rule. It is not
one of the elementary two-input operator CMs from the previous lesson.

**Visual**

Build two clearly labeled inner modules:

```text
left:  W XOR X       right: ¬Y AND Z
                 ↓
             implication
```

Track one false implication case through the construction before revealing the
full valued matrix:

```text
[1 1 0 0]
[1 1 1 0]
[0 0 1 1]
[1 0 1 1]
```

Label rows `(Y,W)` and columns `(X,Z)` throughout the reveal.

## 3:04–3:38 — Retrieval

**Voiceover**

Pause on this cell. Before V sub T, it contains an expression. Which object are
we looking at?

*[Four-second retrieval pause.]*

An LM. Now apply the valuation. The same position contains zero or one, and the
resulting object is the CM. The question is not whether the frame looks like a
matrix; it is what kind of entry the frame contains.

**Visual**

Hold one identified cell fixed. On the learner's answer, pass `V_T` through
that cell and change its badge from `LM: expression` to `CM: bit`.

## 3:38–4:06 — Higher dimensions and boundary

**Voiceover**

The paper extends this construction inductively. For an expression built from
two-n logical subexpressions, it gives a square two-to-the-n by two-to-the-n LM
and then its positive valuation.

The next lesson follows a separate repository operation: arranging a complete
truth output into ordered row and column layouts, including rectangles. That
is an implementation layout rule, not this paper construction.

So retain the sequence: expressions in an LM, positive valuation, binary CM.

**Visual**

Grow `2×2 → 4×4 → 8×8` on a rail labeled `paper construction`. Below it,
preview `repository row-column layout` behind a visible separator. End on
`LM → V_T → CM`.
