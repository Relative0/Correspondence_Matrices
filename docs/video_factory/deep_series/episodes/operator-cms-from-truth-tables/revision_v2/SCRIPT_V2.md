# Why there are sixteen 2×2 operator CMs — script v2

Status: teacher-audited editorial proposal; not yet content-approved  
Target duration: 3:05–3:20  
Target delivery: warm, explanatory, 135–145 WPM

## 0:00–0:24 — One rule, four cases

**Voiceover**

A two-input Boolean rule can be written as one small grid. The rows tell us
whether X is true or false. The columns do the same for Y. That gives four
cells—one for every possible pair of input states.

Fill each cell with the rule's output, zero or one, and the complete two-by-two
pattern is that rule's correspondence matrix, or CM.

**Visual**

Begin with switches `X` and `Y` beside one empty 2×2 grid—not the sixteen-matrix
gallery. Toggle through the four state pairs and let each identified pair claim
one cell. Keep the state labels attached:

```text
             Y=true   Y=false
X=true          11       10
X=false         01       00
```

## 0:24–0:58 — Build AND

**Voiceover**

Take AND. It returns one only when both inputs are true. So the top-left cell,
the X-true, Y-true case, gets a one. The other three cases get zero.

Now read the whole grid: true-true gives one; true-false, false-true, and
false-false give zero. One cell records one case. All four cells together
record the complete rule.

This row and column arrangement—X then not-X, Y then not-Y—is the ordering used
in the paper. Keeping it visible prevents the bits from becoming an anonymous
pattern.

**Visual**

Evaluate AND on the four persistent state cards and place the results one at a
time. After the fourth value, outline the entire matrix and label it `AND`:

```text
[1 0]
[0 0]
```

## 0:58–1:34 — Why the count is sixteen

**Voiceover**

AND is one possible rule. How many complete rules are there?

Each of the four cells may independently contain zero or one. That is two
choices for the first case, two for the second, two for the third, and two for
the fourth. Multiply them: two to the fourth power equals sixteen.

So there are sixteen possible four-cell output patterns, and therefore sixteen
Boolean functions of two inputs. Each complete pattern has its own two-by-two
operator CM.

**Visual**

Turn the four identified cells into binary switches. Show the multiplication
`2 × 2 × 2 × 2 = 16`, then let the sixteen completed patterns settle into a
gallery. Do not branch into a large decision tree.

## 1:34–2:17 — Patterns have meanings

**Voiceover**

Some patterns are familiar. All zeros means always false. AND turns on only
the true-true cell. OR turns off only the false-false cell. XOR turns on the
two cases where the inputs disagree. Equivalence turns on the two cases where
they agree. All ones means always true.

The positions matter most for an asymmetric rule. X implies Y is false only
when X is true and Y is false. Swap the operands, and that false case moves.

The matrix does not discover an operator's name. It records the rule's four
ordered outputs; a familiar name is shorthand for that complete behavior.

**Visual**

Reveal only six named patterns inside the gallery: false, AND, OR, XOR,
equivalence, and true. Then enlarge implication `[[1,0],[1,1]]`; animate the
single zero moving when operand labels swap. Keep all unnamed matrices dim.

## 2:17–2:45 — Retrieval

**Voiceover**

Try reading one without its name. This grid returns zero when the inputs agree
and one when they differ. What rule is it?

*[Four-second retrieval pause.]*

It is exclusive-or, or XOR: zero, one, one, zero in the paper's cell order.

**Visual**

Show `[[0,1],[1,0]]` with state labels but no name. During the pause, pulse the
agreement diagonal, then the disagreement diagonal. Reveal `XOR` only after
the response.

## 2:45–3:07 — Language checkpoint and close

**Voiceover**

One useful language check: these are sixteen different functions, each with
four input cases. Later, a four-input function will itself have sixteen input
assignments. The number is the same; what we are counting is different.

For now, retain this: one cell is one case's output; one complete two-by-two CM
is one two-input Boolean rule.

**Visual**

Hold one matrix beside its four state cards. Add a small end card:
`4 cases per two-input rule → 16 possible rules`. Then let one binary entry
change into an expression tile to preview the LM lesson.
