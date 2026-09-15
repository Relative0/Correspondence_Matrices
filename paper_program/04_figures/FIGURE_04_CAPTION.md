# Figure 4 — Formula-valued LM valuation and logical pairing

**Working caption.** A formula-valued logical matrix has entries in the Boolean
algebra `\mathcal F` of formulas and may be written
`[\mathcal M_{X\Theta Y}]=c_{ij}\otbktwo{X_i}{Y_j}`, with repeated
`i,j\in\{1,2\}` terms reduced by XOR. Here
`c_{ij}=\Theta_{b_i b_j}` with `b_1=1` and `b_2=0`. Pairing it with two logical expressions
produces

`\mathcal P:=\inbkthree{\mathcal L_1}{\mathcal M_{X\Theta Y}}{\mathcal L_2}
=\Updownarrow_{i,j}c_{ij}\wedge
(\mathcal L_1\Leftrightarrow X_i)\wedge
(Y_j\Leftrightarrow\mathcal L_2)`.

Thus `\mathcal P` is a Boolean compatibility formula, not a probability.
Every Boolean valuation `v:\mathcal F\to\mathbb B` commutes with the finite
XOR–AND pairing:

`v(\mathcal P)=
\langle v(\mathcal L_1)|v([\mathcal M_{X\Theta Y}])|
v(\mathcal L_2)\rangle`.

In particular, positive valuation of the LM gives the numeric Correspondence
Matrix `v_T([\mathcal M_{X\Theta Y}])=[\Theta]`. The paper calls this
operation “logical pairing”; its earlier “measurement” language referred only
to algebraic relationship extraction. It does not assert
amplitudes, a Hilbert-space observable, Born probabilities, physical state
collapse, entanglement, or quantum speedup.

**Alt text.** Three connected panels. A formula-valued logical matrix is shown
as an XOR-reduced sum of Boolean outer products. It is paired between bras and
kets constructed from two logical expressions, producing a Boolean formula P
that expresses compatibility. The third panel states that valuing P equals
first valuing the two expressions and the logical matrix and then performing
the numeric bra-ket contraction; positive valuation of the logical matrix gives
the numeric CM `[\Theta]`. A final band explicitly labels this use of
measurement nonphysical.
