# What an explicit correspondence matrix is — proposed script v2

Status: editorial proposal; not yet content-approved  
Target duration: 5:30–6:30  
Target delivery: conversational, 135–145 WPM, paragraph-sized synthesis units

## 0:00–0:25 — Same answers, new addresses

**Voiceover**

These are sixteen answers from one Boolean function. Here they are as a list.
Now as a four-by-four grid. And now as two rows of eight. None of the answers
changed. Only their addresses did. That two-dimensional layout is an explicit
correspondence matrix—an explicit C M.

**Visual**

Open directly on sixteen numbered output chips. Morph the same chips from a
vertical truth-table output column into 4×4, then 2×8. Keep chip identities
visible throughout. No title card before the transformation.

## 0:25–0:58 — Precise definition

**Voiceover**

Choose an ordered set of variables for the rows and another ordered set for the
columns. A complete assignment then splits into two bit strings. The first
chooses a row. The second chooses a column. The cell at those coordinates stores
the function's exact output for that assignment. “Explicit” and “dense” mean
that every cell in the declared layout is present.

**Visual**

Label a persistent row rail `R` in amber and column rail `C` in cyan. Show one
four-bit assignment dividing into two colored pairs and meeting at a white cell.

## 0:58–1:50 — Build the 4×4 matrix

**Voiceover**

Let's build one. Our rule is: open parenthesis A and B close parenthesis,
exclusive-or, open parenthesis C or D close parenthesis. We'll place A and B on
the rows, and C and D on the columns. In each pair, read the left bit first, so
the addresses run zero-zero, zero-one, one-zero, one-one.

Two row variables give four row addresses. Two column variables give four
column addresses. So the matrix has four times four, or sixteen, cells—one for
every assignment of A, B, C, and D.

Now watch the truth table fold. For each row of the table, A B chooses the
matrix row, C D chooses the column, and the output bit moves into that cell.
The list is changing shape, not meaning.

**Visual**

Keep the fully parenthesized expression above a 16-row truth table. Color A/B
amber and C/D cyan. Build binary headers `00, 01, 10, 11`; add small decimal
indices `0, 1, 2, 3`. Physically move all sixteen output chips into the grid.
The settled rows must be `0111`, `0111`, `0111`, `1000`.

## 1:50–2:42 — Follow one assignment forward

**Voiceover**

Take the assignment one-zero-one-one. A B is one-zero, which is row two. C D is
one-one, which is column three. Now evaluate the rule: one AND zero is zero; one
OR one is one; and zero exclusive-or one is one. So cell row two, column three
contains one.

Notice what the matrix lets us do. We can locate the value from two coordinated
indices without losing the assignment that produced it.

**Visual**

Use four large bit chips: `A=1 B=0 C=1 D=1`. Animate `AB=10₂ → row 2` and
`CD=11₂ → column 3`. Cross the two cursors only after evaluating the expression,
then reveal `M[2,3]=1`.

## 2:42–3:18 — Read coordinates backward

**Voiceover**

We can also start from coordinates. Row three carries A B equals one-one.
Column one carries C D equals zero-one. Together the coordinates name assignment
one-one-zero-one, and the cell stores zero. It is the coordinates—not the zero
by itself—that recover the assignment. Many different cells can contain the
same output bit.

**Visual**

Start on `M[3,1]=0`; trace outward from the coordinate labels to `AB=11`,
`CD=01`, and then `ABCD=1101`. Briefly illuminate other zero cells to defeat
the false-inverse misconception.

## 3:18–4:05 — Your turn

**Voiceover**

Try one before the cursors move. A equals one, B equals one, C equals one, and D
equals zero. Which row? Which column? And what output belongs there?

*[Five-second retrieval pause.]*

A B is one-one, so choose row three. C D is one-zero, so choose column two. The
rule gives one exclusive-or one, which is zero. The answer is M of three comma
two equals zero.

**Visual**

Show `1110` and the three questions. Hide all cursor motion during the full
pause, then reveal `row 3`, `column 2`, and `M[3,2]=0` in that order.

## 4:05–4:58 — The split controls shape, not function

**Voiceover**

The row-and-column split is part of the matrix's identity. Put only A on the
rows and B, C, D on the columns, and the same function becomes a two-by-eight
layout. Put A, B, C on the rows and D on the columns, and it becomes eight by
two. The assignment one-zero-one-one moves to a different coordinate, but its
output stays one.

In general, if R contains r binary variables and C contains c, the explicit
matrix has two-to-the-r rows and two-to-the-c columns. Changing the split or
order changes the addresses and possibly the shape. It does not change the
Boolean function.

**Visual**

Morph 4×4 to 2×8 to 8×2 while the sixteen identified chips retain their values.
Track assignment `1011` across all three layouts. Keep a small persistent
`same 16 outputs` equality ribbon.

## 4:58–5:32 — What “dense” does not promise

**Voiceover**

Because the layout is explicit, every declared cell is materialized. That can
be useful when this two-coordinate organization is the output you want to
inspect or use. But the word matrix does not imply matrix multiplication, and
dense does not automatically mean compact, solver-like, or fast. Those are
different questions that need their own evidence.

**Visual**

Keep the matrix dominant. Apply four small boundary stamps around it:
`exact layout`, `not matrix multiplication`, `not automatic compression`, and
`no speed claim`. Do not introduce a CM-IR graph, packed vector, benchmark, or
solver interface.

## 5:32–5:48 — Close

**Voiceover**

An explicit C M is the same exact Boolean function, laid out over ordered row
and column variables. The split determines the address. The coordinates name
the assignment. And the cell stores its exact output bit.

**Visual**

Return to assignment `1011`, the crossing indices, and `M[2,3]=1`. Pull back to
the complete labeled matrix. End on the object, not a series map.
