# CM notation standard v4

Effective 2026-09-15. Additive successor: all nonconflicting rules in
[v3](CM_NOTATION_STANDARD_V3.md) remain applicable. Preserve frozen historical
and video artifacts; apply this update to the current paper program and future
paper-derived figures, captions, and prose.

## Uppercase operator variable

Use uppercase `Θ` (LaTeX `\Theta`) for the generic logical operator variable
everywhere in the paper. Do not use lowercase `θ` or `\theta` in paper prose,
formulas, captions, or figures.

- Generic operator and CM: `Θ`, `[Θ]`.
- Example assignment: `Θ:=\Updownarrow`, hence `[Θ]=[\Updownarrow]`.
- Generic numeric CM: `[Θ]`; do not add an unnecessary `f` or `xy` subscript
  to the whole matrix.
- In true-first truth-assignment order, define
  `Θ_{xy}:=x\Theta y` for `x,y\in\{1,0\}` and display
  `[Θ]=[[Θ_{11},Θ_{10}],[Θ_{01},Θ_{00}]]`.
- The ordered truth vector is written directly as
  `\operatorname{vec}([Θ])=(Θ_{11},Θ_{10},Θ_{01},Θ_{00})`; do not introduce
  an opaque `t_f` label in an introductory figure.
- The formula-valued LM may retain polarity-position indices
  `i,j\in\{1,2\}` in `\Theta_{ij}\otbktwo{X_i}{Y_j}`. State the distinction
  between these position indices and the numeric CM's truth-assignment indices.

Internal source-code identifiers such as `theta` are implementation details and
need not be renamed. Preserve lowercase notation in frozen historical sources;
do not rewrite quoted or archived documents.

## Figure presentation refinements

- Render symbolic bra and ket definitions at the same font and size as their
  evaluated state vectors.
- Leave `\langle X|[\Theta]|Y\rangle` uncluttered. Explain XOR reduction and
  AND term products in adjacent prose rather than a bra-ket subscript.
- Typeset the centered `\impax` overlay tightly inside its brackets, with no
  inserted space between the bra, CM, and ket.
- In conceptual figures, call `[Θ]` an **operator** or **CM**, not a token.
  Reserve “token” for a specifically defined compiler implementation type.
- When applying operand-swap Rule 1, show the bra-ket identity explicitly:
  `\langle Y|[\Theta]|X\rangle=\langle X|[\Theta]^T|Y\rangle`.
- Label logical expressions with `\mathcal L`, using subscripts such as
  `\mathcal L_1` and `\mathcal L_2`.
