# The repository's explicit row-column CM layout — script v3

Status: editorial proposal; not yet content-approved  
Target duration: 4:40–5:05  
Target delivery: conversational, precise, 135–145 WPM

## 0:00–0:28 — Same function, declared layout

**Voiceover**

This is one four-variable Boolean function. It has sixteen possible input
assignments, and each assignment has exactly one output. Keep those sixteen
assignment-output pairs in view—we are going to change where they appear, but
not what the function says.

One quick reminder: the preceding sixteen operator matrices were sixteen
different two-input functions. These are sixteen assignments of one
four-input function. Same number, different objects.

**Visual**

Show the fixed rule

```text
F(A,B,C,D) = (A AND B) XOR (C OR D)
```

Build sixteen cards labeled by complete assignments `0000` through `1111`,
each permanently attached to its output. Use a small two-line contrast badge;
do not replay the operator-CM gallery.

## 0:28–0:57 — Ordered row and column lists

**Voiceover**

The repository asks for two ordered variable lists. Let the row list be A, B,
and the column list be C, D. A complete assignment now supplies two row bits
and two column bits. Reading each pair most-significant bit first gives row and
column indices from zero through three.

The order is part of the contract. Change it and the same assignment may move
to a different coordinate.

**Visual**

Place persistent rails beside the cards:

```text
R = [A,B]     amber
C = [C,D]     cyan
order = MSB-first
```

Split `1011` into amber `10` and cyan `11`, but do not place it yet.

## 0:57–1:33 — Materialize the 4×4 layout

**Voiceover**

Two row variables give two-squared, or four, rows. Two column variables give
four columns. The repository aligns the outputs to the declared order A, B, C,
D, then arranges the A-B bits as the row index and the C-D bits as the column
index.

Every assignment-output card occupies one cell. In this project, the resulting
four-by-four dense row-column truth matrix is called a repository explicit CM
layout.

That name describes the implementation artifact. It is not the logical-matrix
construction used by the originating paper.

**Visual**

Build headers `00, 01, 10, 11` on both axes. Move all sixteen identified cards
into the grid. Require the settled rows:

```text
0111
0111
0111
1000
```

Keep a small `repository layout` qualifier attached to the grid.

## 1:33–2:09 — Follow one assignment forward

**Voiceover**

Take assignment one-zero-one-one. Its A-B bits are one-zero, so the row index
is two. Its C-D bits are one-one, so the column index is three.

Evaluate the rule once: one AND zero is zero; one OR one is one; zero
exclusive-or one is one. So this assignment-output pair belongs at row two,
column three, and the stored value is one.

**Visual**

Keep the complete `1011 → 1` card intact on the invariant rail. Derive
`AB=10₂ → row 2` and `CD=11₂ → column 3`, cross the cursors, and reveal
`M[2,3]=1`.

## 2:09–2:45 — A coordinate needs context

**Voiceover**

Now reverse the question. Suppose I show only coordinate two, three. Which
assignment is it?

Not enough information. We need the row list, the column list, their internal
order, and the bit-index convention. Restore A-B on the rows, C-D on the
columns, most-significant bit first, and coordinate two, three decodes to
one-zero-one-one.

The cell's value is still a separate fact. Many coordinates can store one, and
many can store zero.

**Visual**

Remove all axis metadata while leaving `(2,3)` visible; show `assignment = ?`.
Restore the three contract labels one at a time and decode the assignment only
after the last returns. Briefly illuminate other cells containing 1.

## 2:45–3:19 — Retrieval

**Voiceover**

Try one. With A-B on the rows and C-D on the columns, where does assignment
one-one-one-zero go, and what value is stored there?

*[Four-second retrieval pause.]*

A-B is one-one, so row three. C-D is one-zero, so column two. One AND one is
one; one OR zero is one; and one exclusive-or one is zero. M of three comma two
is zero.

**Visual**

Show `1110` and prompts `row? column? output?`. Hold every cursor during the
pause. Reveal `row 3`, `column 2`, and `M[3,2]=0` sequentially.

## 3:19–4:13 — Change the partition

**Voiceover**

The repository does not require an even split. Put only A on the rows and B,
C, D on the columns. The result has two rows and eight columns. Our unchanged
assignment one-zero-one-one now gives row bit one and column bits zero-one-one,
so its coordinate is one, three. Its output remains one.

Put A, B, C on the rows and D on the columns. The shape becomes eight by two.
The same assignment now has row bits one-zero-one—index five—and column bit
one—index one. Its coordinate is five, one. Its output is still one.

The Boolean mapping did not change. The ordered partition, matrix shape, and
coordinates did. These rectangular matrices are repository-supported
row-column truth layouts; the paper's stated general higher-dimensional
construction is square.

**Visual**

Track the intact `1011 → 1` card through:

```text
AB / CD      4×4     (2,3)
A / BCD      2×8     (1,3)
ABC / D      8×2     (5,1)
```

Keep the invariant rail fixed. Change only the `R`, `C`, shape, and coordinate
fields on the layout rail. Label all three `repository row-column layouts`.

## 4:13–4:39 — What dense means

**Voiceover**

Dense means every cell in the requested output layout is materialized. Here,
four variables require sixteen cells no matter how those cells are split
between rows and columns.

That fact alone does not answer questions about compactness, solving, or speed.
Those belong to the next lesson. And it does not make this dense array the same
object as CM-IR or a packed truth output; their dedicated comparison comes
afterward.

**Visual**

Fill every cell and label `16 assignments → 16 materialized cells`. Preview the
next two episode icons for no more than five seconds; do not explain their
mechanisms here.

## 4:39–4:56 — Close

**Voiceover**

The Boolean function fixes which output belongs to each complete assignment.
The repository's ordered row and column lists determine where that pair
appears. Change the partition and the matrix changes; the function does not.

**Visual**

Return to `1011 → 1`. Show its three coordinates simultaneously beneath the
unchanged card. End with the invariant and layout rails both labeled.
