# Figure 2 — Representation map

**Working caption.** The two objects at left are native to the present
Correspondence-Matrix framework. The formula-valued logical matrix
`[\mathcal{M}_{X\Theta Y}]` is the XOR-reduced outer-product sum
`c_{ij}\otbktwo{X_i}{Y_j}`, with `X_1=X`, `X_2=\neg X`, `Y_1=Y`, and
`Y_2=\neg Y`. Its four cells are the complete indexed contractions
`X_i\wedge c_{ij}\wedge Y_j`, `X_i\wedge c_{ij}\wedge\neg Y_j`,
`\neg X_i\wedge c_{ij}\wedge Y_j`, and
`\neg X_i\wedge c_{ij}\wedge\neg Y_j`; repeated `i,j` terms are XOR-reduced in each
cell. Positive valuation sends its formula entries
to the numeric Correspondence Matrix
`[\Theta]\in\mathbb B^{2\times2}`. In its true-first assignment indexing,
`\Theta_{xy}:=x\Theta y` for `x,y\in\{1,0\}`, so
`[\Theta]=[[\Theta_{11},\Theta_{10}],[\Theta_{01},\Theta_{00}]]`.
The formula-valued LM uses polarity-position coefficients
`c_{ij}:=\Theta_{b_i b_j}`, where `b_1=1` and `b_2=0`; the
numeric CM uses truth-assignment indices `x,y\in\{1,0\}`. Under the declared
mapping, the LM position sequence
`(c_{11},c_{12},c_{21},c_{22})` is relabeled as the CM
assignment sequence `(\Theta_{11},\Theta_{10},\Theta_{01},\Theta_{00})`.
Vectorizing the CM
gives `\operatorname{vec}([\Theta])=(\Theta_{11},\Theta_{10},
\Theta_{01},\Theta_{00})`, which acts as a
conversion bridge to two external
representations. A Boolean Möbius transform yields algebraic-normal-form (ANF)
coefficients, a general Boolean-polynomial coordinate system; adjoining the
complementary output row yields the numeric STP logical structure matrix used
in the semi-tensor-product literature. ANF coefficients and the STP structure
matrix are shown for comparison and are not components of the CM construction.
In particular, Brian Theory's formula-valued LM is not the numeric object called
a “logical matrix” in the STP literature. The labels `a_\Theta` and `M_\Theta`
are local, operator-indexed names adopted in this figure for accessibility; ANF
and STP sources use differing symbols. The mathematical content is the standard
ANF coefficient expansion and, under the declared true-first output encoding,
the STP structure matrix whose first row is `\operatorname{vec}([\Theta])` and
whose second row is its complement.

**Alt text.** A typed conversion diagram. The paper-native formula-valued LM,
shown as `[\mathcal{M}_{X\Theta Y}]` with four indexed formula entries, points
by positive valuation to a numeric CM `[\Theta]` with assignment-indexed
entries `\Theta_{11},\Theta_{10},\Theta_{01},\Theta_{00}`.
The CM and an ordered truth vector are connected by vectorize and reshape
arrows. The vector `\operatorname{vec}([\Theta])` points to two dashed,
external-comparison boxes: upward
through a Boolean Möbius transform to ANF coefficients and downward by adding
the complementary truth row to an STP structure matrix. A footer says that ANF
and STP are comparison representations rather than parts of the CM framework.
