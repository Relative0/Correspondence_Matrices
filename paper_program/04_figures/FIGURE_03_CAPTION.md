# Figure 3 — Operand-aligned fusion

**Working caption.** Operator-level fusion requires a common operand frame.
The two implication subexpressions
`\mathcal L_1=X\Rightarrow\neg Y` and
`\mathcal L_2=\neg Y\Rightarrow X` initially attach the same signed operands
to opposite matrix axes. Rule 1,
`\langle Y|[\Theta]|X\rangle=\langle X|[\Theta]^T|Y\rangle`, rewrites
`\mathcal L_2=\langle\neg Y|[\Rightarrow]|X\rangle` as
`\langle X|[\Rightarrow]^T|\neg Y\rangle`, placing both subexpressions in the
common frame `(X,\neg Y)`. The aligned operators can then be combined with the
outer XOR entrywise:
`[\Rightarrow]\Updownarrow[\Rightarrow]^T=[\Updownarrow]`. Consequently,
`\mathcal L_1\Updownarrow\mathcal L_2` is represented by the single operator expression
`\langle X|[\Updownarrow]|\neg Y\rangle`. This is an entrywise Boolean fusion,
not an arithmetic matrix product. The rewrite is sound only after variable,
axis order, polarity, and truth-state order agree.

**Alt text.** A four-stage flow diagram. Two implication expressions, labelled
L sub one and L sub two, begin in the reversed frames `(X,not Y)` and
`(not Y,X)`. A displayed bra-ket version of Rule 1 shows that the second CM is
transposed when its operands are swapped into the first frame. The aligned implication
matrix and its transpose are XORed entrywise, yielding the off-diagonal XOR
matrix. A final bra-ket expression uses that single fused operator. A warning
states that entrywise fusion is allowed only when all operand-frame metadata
matches.
