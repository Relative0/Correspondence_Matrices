# The repository's explicit row-column CM layout — script v4

Status: teacher-audited editorial proposal; not yet content-approved  
Target duration: 3:35–3:50  
Target delivery: conversational, concrete, 135–145 WPM

## 0:00–0:24 — Give every output a coordinate

**Voiceover**

A four-input Boolean function assigns one output to each of its sixteen input
assignments. The repository can arrange those assignment-output pairs in a
matrix by choosing which input bits name the rows and which name the columns.

Let us build that layout and follow one assignment all the way to its cell.

**Visual**

Show the fixed rule and one tracked card before revealing the other fifteen:

```text
F(A,B,C,D) = (A AND B) XOR (C OR D)
tracked assignment: 1011 → 1
```

Keep the function and tracked card on a stationary invariant rail.

## 0:24–0:56 — The layout contract

**Voiceover**

Choose the ordered row list A, B and the ordered column list C, D. A complete
assignment now supplies two row bits and two column bits. Read each pair
most-significant bit first, and each becomes an index from zero through three.

For assignment one-zero-one-one, A-B is one-zero, so the row index is two.
C-D is one-one, so the column index is three. The assignment belongs at
coordinate two, three.

**Visual**

Split the intact `1011 → 1` card into temporary index guides while leaving the
original card visible:

```text
R=[A,B]: 10₂ → row 2
C=[C,D]: 11₂ → column 3
order: MSB-first
```

Cross the row and column cursors at `(2,3)`.

## 0:56–1:32 — Materialize the 4×4 matrix

**Voiceover**

Two row variables produce four rows, and two column variables produce four
columns. Place every assignment's output at the coordinate determined by its
A-B and C-D bits. The completed rows are zero-one-one-one, repeated three
times, followed by one-zero-zero-zero.

At our tracked cell, the output is one: A AND B is zero; C OR D is one; and
zero XOR one is one. In this project, the completed dense row-column truth
matrix is called a repository explicit CM layout.

**Visual**

Reveal headers `00, 01, 10, 11` on both axes. Place the tracked card first,
then fill the remaining identified cards in a single controlled wave. Settle on:

```text
0111
0111
0111
1000
```

Keep `M[2,3]=1` highlighted and retain a small `repository layout` badge.

## 1:32–2:04 — Coordinates need a key

**Voiceover**

Now suppose someone gives us only coordinate two, three. Can we recover the
assignment? Not yet. We need the ordered row list, the ordered column list,
and the bit-order convention.

Restore A-B on the rows, C-D on the columns, and most-significant bit first.
Now row two decodes to one-zero and column three to one-one, giving assignment
one-zero-one-one. The coordinate locates a case; the value stored there is the
function's output for that case.

**Visual**

Temporarily remove the axis key while keeping `(2,3)` visible. Restore `R`, `C`,
and `MSB-first` one at a time, then reconstruct `1011`. Keep the cell value
visually separate from the decoded assignment.

## 2:04–2:34 — Retrieval

**Voiceover**

Your turn. With A-B on the rows and C-D on the columns, where does assignment
one-one-one-zero go, and what is stored there?

*[Four-second retrieval pause.]*

The row bits one-one give row three. The column bits one-zero give column two.
The function returns zero, so M of three comma two is zero.

**Visual**

Show `1110` and three prompts: `row? column? output?`. Reveal `3`, `2`, and `0`
only after the pause, with a short evaluation available in captions.

## 2:34–3:16 — Repartition without changing the function

**Voiceover**

The split need not be even. Put A on the rows and B-C-D on the columns. The
shape becomes two by eight. Our same assignment now lands at row one, column
three, and still stores one.

Put A-B-C on the rows and D on the columns. The shape becomes eight by two.
The same assignment lands at row five, column one, still storing one.

The function has not changed: every complete assignment keeps its output. The
ordered partition changes the shape and the coordinates. These rectangular
forms are repository-supported row-column truth layouts; they are distinct
from the paper's square logical-matrix construction.

**Visual**

Track the single intact card across three layouts:

```text
AB / CD      4×4     (2,3) → 1
A / BCD      2×8     (1,3) → 1
ABC / D      8×2     (5,1) → 1
```

Morph only the layout rail. The invariant rail must not move or change.

## 3:16–3:40 — Dense and close

**Voiceover**

Dense means that every cell in the requested layout is materialized. With four
input variables, these layouts each contain sixteen cells, however rows and
columns divide them.

The function determines each assignment's output. The ordered row and column
lists determine where that assignment-output pair appears. That is the
repository's explicit layout contract.

**Visual**

Show all cells filled in each shape, then return to the unchanged `1011 → 1`
card with its three coordinates beneath it. No CM-IR, packed-output, solver, or
performance preview is needed.
