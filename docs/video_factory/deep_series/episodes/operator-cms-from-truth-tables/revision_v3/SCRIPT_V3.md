# Why there are sixteen 2×2 operator CMs — script v3

Status: paper-audited bra-ket revision; narrated review candidate  
Target duration: 3:39  
Target delivery: warm, explanatory, 132–142 WPM

## 0:00–0:24 — One rule, four cases

**Voiceover**

A two-input Boolean rule can be written as one small grid. The rows tell us
whether X is true or false. The columns do the same for Y. That gives four
cells—one for every possible pair of input states.

Fill each cell with the rule's output, zero or one. The complete two-by-two
pattern is that rule's correspondence matrix, or C M.

**Visual**

Begin with switches `X` and `Y` beside one empty 2×2 grid. Toggle through the
four state pairs and let each pair claim one labeled cell:

```text
             Y=true   Y=false
X=true          11       10
X=false         01       00
```

## 0:24–0:58 — Build AND

**Voiceover**

Take AND. It returns one only when both inputs are true. So the top-left cell,
the X-true, Y-true case, gets a one. The other three cases get zero.

One cell records one case. All four cells together record the complete rule.
The paper orders the rows as X then not-X, and the columns as Y then not-Y.
Keeping that order visible prevents the bits from becoming an anonymous
pattern.

**Visual**

Evaluate AND on four persistent state cards and populate the matrix one cell at
a time. After the fourth value, outline and label the complete matrix `AND`:

```text
[1 0]
[0 0]
```

Then add the secondary notation `|1⟩⟨1|` below it as a preview, without yet
asking the learner to interpret it.

## 0:58–1:27 — Four basis dyads

**Voiceover**

Here is what that compact notation means. The paper writes the true state as
ket one, a column vector one-zero, and false as ket zero, zero-one. Transposing
a ket gives a bra, which is a row vector.

Take a ket times a bra as an outer product. The paper also writes this with a
tensor-product sign. The four possible pairs produce four two-by-two matrices,
each with exactly one active cell. These are the four basis dyads.

**Visual**

Build the vectors, then expand all four outer products. Keep the equivalence of
the two paper notations visible:

```text
|i⟩ ⊗ ⟨j| = |i⟩⟨j|

|1⟩⟨1| = [1 0]   |1⟩⟨0| = [0 1]
            [0 0]               [0 0]

|0⟩⟨1| = [0 0]   |0⟩⟨0| = [0 0]
            [1 0]               [0 1]
```

Call these objects `basis dyads`, not four logical operators.

## 1:27–2:05 — From four choices to sixteen operators

**Voiceover**

Any operator C M is an exclusive-or sum of the basis dyads whose positions
contain one. AND uses only ket-one bra-one. OR uses the first three dyads.
Exclusive-or uses the two off-diagonal dyads.

Each of the four positions may independently be zero or one: two choices,
four times. Two to the fourth power is sixteen. So there are sixteen complete
two-input rules, not sixteen answers to one rule.

**Visual**

Show `2 × 2 × 2 × 2 = 2⁴ = 16`, then settle into a legible 4×4 operator table
modeled on Figure 1 of the paper. Every tile contains, in this order:

1. the familiar name or defining expression;
2. the 2×2 matrix;
3. its ket-bra dyadic expansion.

Use the paper's four-column grouping: constants and parity; single-feature
rules; implication-family rules; operand projections. Highlight AND, OR, XOR,
and equivalence. Long dyadic sums may wrap to two lines but must remain
readable at 1920×1080.

## 2:05–2:45 — Patterns encode behavior

**Voiceover**

Now the table has meaning. All zeros means always false. OR is off only at the
false-false position. Equivalence is on when the inputs agree. All ones means
always true.

Order matters most for an asymmetric rule. X implies Y is false only when X
is true and Y is false. Swap the operands, and that zero moves to the other
off-diagonal position.

The matrix does not discover an operator's name. It records four ordered
outputs; the name is shorthand for that complete behavior.

**Visual**

Keep the full table faintly present while enlarging false, OR, equivalence, and
true in sequence. Then compare `X → Y = [[1,0],[1,1]]` with
`Y → X = [[1,1],[0,1]]`; animate only the zero moving. The ket-bra expansions
remain secondary and do not reappear after this scene.

## 2:45–3:13 — Retrieval

**Voiceover**

Try reading one without its name. This grid returns zero when the inputs agree
and one when they differ. What rule is it?

*[Four-second retrieval pause.]*

It is exclusive-or: zero, one, one, zero in the paper's cell order. In the
dyadic table, it was the sum of the two off-diagonal basis matrices.

**Visual**

Show `[[0,1],[1,0]]` with state labels but no name. During the pause, pulse the
agreement diagonal, then the disagreement diagonal. Reveal `XOR` after the
response. Briefly show `|1⟩⟨0| ⊕ |0⟩⟨1|`, then remove the notation.

## 3:13–3:39 — Language checkpoint and close

**Voiceover**

One language check: these are sixteen different functions, each with four
input cases. Later, one four-input function will itself have sixteen input
assignments. The number is the same; what we count is different.

Retain this: one cell is one case's output. One complete two-by-two C M is one
two-input rule. The four basis dyads are simply a compact way to build any of
those rules.

**Visual**

Hold one matrix beside its four state cards. Add:
`4 cases per two-input rule → 16 possible rules`. End by replacing the four
bits with four expressions to preview the logical-matrix lesson.
