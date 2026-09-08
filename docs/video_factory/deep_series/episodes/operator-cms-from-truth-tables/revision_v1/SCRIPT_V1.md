# Why there are sixteen 2×2 operator CMs — script v1

Status: editorial proposal; not yet content-approved  
Target duration: 4:15–4:35  
Target delivery: conversational, curious, 135–145 WPM

## 0:00–0:24 — Sixteen what?

**Voiceover**

There are sixteen correspondence matrices in this picture. But sixteen what?
Not sixteen outputs belonging to one function. These are sixteen different Boolean
functions—every possible rule that can take two true-or-false inputs and return
one true-or-false output.

To see why, we only need four input cases and one small grid.

**Visual**

Begin tightly framed on Figure 1's gallery, reconstructed as clean vector art.
Dim fifteen matrices. Let the remaining 2×2 matrix expand while the question
`sixteen what?` gives way to four labeled input-state cards.

## 0:24–1:02 — Four input cases

**Voiceover**

Call the inputs X and Y. Together they have four possible states: both true;
X true and Y false; X false and Y true; or both false.

The paper places those cases in a two-by-two matrix. Its row state is X, then
not X. Its column state is Y, then not Y. So the four cells, in this order,
stand for X-Y, X-not-Y, not-X-Y, and not-X-not-Y.

Those labels matter. Without them, four bits are just a pattern. With them,
each position names one input case.

**Visual**

Show a conventional truth-table order `00, 01, 10, 11`, then physically move
the four assignment cards into the paper's state order:

```text
             Y=true   Y=false
X=true          11       10
X=false         01       00
```

Keep the row and column labels attached for the rest of the episode.

## 1:02–1:39 — One whole matrix is one operator

**Voiceover**

Take AND. AND is true only when X and Y are both true. So its first cell is one,
and the other three cells are zero.

That single cell is not “the AND operator.” It is AND's output for one input
case. The complete four-cell pattern is the operator's correspondence matrix.

Read it back. True and true gives one. True and false gives zero. False and true
gives zero. False and false gives zero. The matrix contains the whole two-input
truth function.

**Visual**

Populate the AND matrix one assignment at a time:

```text
[1 0]
[0 0]
```

After the fourth value arrives, draw one outline around all four cells and
attach the label `AND`. Briefly contrast `one entry` with `one complete
operator`.

## 1:39–2:20 — Why exactly sixteen

**Voiceover**

Now forget AND's particular answers. For each of the four input cases, a
Boolean function may choose zero or one. Two choices for the first cell, times
two for the second, times two for the third, times two for the fourth:

two to the fourth power. Sixteen complete output patterns. Therefore sixteen
two-input Boolean functions, and sixteen distinct two-by-two operator CMs.

This count is different from the sixteen assignments of a four-variable
function. Here we have four assignments for each function—and sixteen
different functions.

**Visual**

Make the four cells behave as four independent binary switches. Grow a compact
decision tree `2 × 2 × 2 × 2 = 16`, then collapse each completed leaf into one
small 2×2 matrix. Keep labels:

```text
4 assignments per function
16 different functions
```

## 2:20–3:20 — Read the gallery

**Voiceover**

The all-zero matrix is the function that is always false. Flip only the
both-true cell and we have AND. Turn on every cell except both-false and we have
OR. XOR turns on the two cells where X and Y disagree. Equivalence does the
opposite: it turns on the two cells where they agree. The all-one matrix is the
function that is always true.

Some operators are symmetric. Swapping X and Y leaves AND, OR, XOR, and
equivalence unchanged. Implication is not symmetric. X implies Y has the
pattern one, zero, one, one in the paper's cell order. Swap the operands and
the zero moves to a different cell.

The matrix has not guessed an operator name. It records the complete output
pattern under a declared ordering; the logical name follows from that pattern.

**Visual**

Re-form the full sixteen-matrix gallery. Highlight only the named examples in
sequence:

- false `[[0,0],[0,0]]`;
- AND `[[1,0],[0,0]]`;
- OR `[[1,1],[1,0]]`;
- XOR `[[0,1],[1,0]]`;
- equivalence `[[1,0],[0,1]]`;
- true `[[1,1],[1,1]]`;
- implication `[[1,0],[1,1]]`.

For implication, swap the row and column operand labels and animate the zero
moving from the `X=true,Y=false` case to `X=false,Y=true`.

## 3:20–3:58 — Retrieval

**Voiceover**

Your turn. This matrix has zeros on the agreement diagonal and ones on the
disagreement diagonal. Before the name appears, read its four outputs in the
paper's order. What happens when both inputs are true? When only X is true?
When only Y is true? And when both are false?

*[Four-second retrieval pause.]*

Zero, one, one, zero. That is exclusive-or: true exactly when the inputs
disagree.

**Visual**

Show `[[0,1],[1,0]]` with the row and column state labels but no operator name.
Illuminate the cells in the spoken order only after the full pause. Reveal
`XOR` last.

## 3:58–4:22 — Close

**Voiceover**

So the foundation is precise: one cell gives one operator output for one input
state pair. One complete two-by-two matrix gives one two-input Boolean
function. And the sixteen possible four-bit patterns give the sixteen operator
CMs.

Next, we will keep logical expressions inside the cells before turning them
into bits. That is how the paper moves from elementary operator CMs to logical
matrices and larger compound constructions.

**Visual**

Settle on one 2×2 binary CM. Its bits soften into expression glyphs while the
outline and state labels remain fixed, creating the handoff to the LM lesson.
