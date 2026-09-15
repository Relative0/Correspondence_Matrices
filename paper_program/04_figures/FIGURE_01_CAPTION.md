# Figure 1 — Boolean operator evaluation and notation

**Working caption.** A correspondence matrix acts as a Boolean operator. The
logical state of `X` is written as the bra `⟨X|=[X,¬X]`, and the logical state
of `Y` as the ket `|Y⟩=[Y,¬Y]^T`, both in true-first order. After assigning
`X=1` and `Y=0`, the contraction `⟨1|[⇕]|0⟩` evaluates to one. Here `∧`
forms term products and `⇕` reduces the terms, so the operation is XOR–AND
contraction over `GF(2)`, not ordinary real-arithmetic multiplication. A
specific operator CM is named by its bracketed operator; `[Θ]` denotes a
declared generic operator CM, and for `Θ:=⇕`,
`[Θ]=[⇕]=[[0,1],[1,0]]`.

The notation also records a matrix relationship: the XOR CM `[⇕]` is a
90-degree rotation and entrywise complement of the XNOR CM `[⇔]`. Their
entrywise XOR gives the all-ones Impax CM,
`[\impax]=[⇔]⇕[⇕]=[[1,1],[1,1]]`, whose operation is tautological. “Boolean
superposition” here means entrywise XOR of binary matrices, not quantum
superposition.

**Alt text.** Four connected panels. The first writes X as a bra and Y as a ket
and shows their evaluated true-first states for X true and Y false. The second
defines a generic bracketed CM and assigns it the bracketed up-down-arrow XOR
operator matrix. The third evaluates the compact bra-ket expression using
XOR–AND contraction and obtains one. The fourth rotates the diagonal XNOR
matrix by 90 degrees to obtain the off-diagonal XOR matrix, then combines the
two entrywise to obtain the tautological all-ones `\impax` matrix. Both Impax
occurrences use the centered overlay glyph rather than the word “Impax.”
