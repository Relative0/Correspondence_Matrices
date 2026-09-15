# Title and terminology memo

Date: 2026-09-14  
Prospective author: **Brian Theory**

## Selected title

> **Operator-Level Boolean Computation with Correspondence Matrices**

Selected by Brian Theory on 2026-09-14. This title is concise, accessible, and
keeps the paper centered on the operator interpretation without making the
still-conditional empirical boundary part of the title.

## Recommended terminology

Replace **common-frame fusion** with **operand-aligned fusion**.

A frame is the complete interpretation of a `2 x 2` token: the two operands,
their row/column order, their polarity, and each axis's truth-state order. Two
tokens share a common frame only when all of that metadata agrees. The phrase
is mathematically legitimate, but it is not self-explanatory and can sound like
image registration or coordinate mechanics. “Operand-aligned fusion” tells a
computing reader what the step actually does.

Recommended main-text sentence:

> Before two CM tokens are fused, their operands must be aligned to the same
> variables, order, polarity, and basis convention; fusion then applies the
> outer Boolean connective entrywise.

Use **signed operand alignment** for the transformation step,
**exact-frame token fusion** for the standalone 4-bit operation, and
**direct four-assignment retabulation** for the compiler's remaining fallback.
The implemented structural path aligns signed row/column variables and
recursively fuses tokens with matching canonical pair metadata.

Recommended first-use footnote:

> This paper writes exclusive-or as `⇕` (LaTeX `\Updownarrow`) rather than the
> more common circled-plus symbol. In the declared true-first frame, the XOR CM
> `[⇕]` is a 90-degree rotation and entrywise complement of the XNOR CM `[⇔]`;
> moreover, `[⇔] ⇕ [⇕]` is the all-ones, tautological `[\impax]` CM. The term
> “superposition” refers here only to this entrywise Boolean operation.

## Ranked title candidates

1. **Correspondence Matrices as Boolean Operators: Operand-Aligned Fusion and Its Performance Boundary**  
   Best balance of concept, candidate contribution, and empirical honesty.

2. **Computing with Boolean Operators: Correspondence Matrices, Formula-Valued Logical Matrices, and Verified Fusion**  
   Most accessible; makes the LM-to-CM story visible, but “verified” requires
   the compiler proof and frozen tests.

3. **From Formula-Valued Logical Matrices to Correspondence Matrices: Valuation, Alignment, and Operator Fusion**  
   Best if the LM construction remains substantial. It risks implying that the
   paper's main contribution is the symbolic lift rather than the compiler.

4. **Correspondence Matrices for Propositional Computation: Typed Operators and Verified Fusion**  
   Clear and venue-neutral; slightly less distinctive.

5. **Operator-Level Boolean Computation with Correspondence Matrices**  
   **Selected.** Short, accessible, and centered on Brian Theory's intended distinction.

6. **Correspondence Matrices: Boolean Operator Evaluation, Alignment, and Fusion**  
   Descriptive and safe; useful before the empirical result is known.

7. **A Boolean Operator Calculus for Correspondence Matrices**  
   Elegant but should be used only if the paper contains a closed set of
   transformations, composition rules, and a proved normalization procedure.

## Historical fallback considered before signed alignment was implemented

> **Correspondence Matrices as Boolean Operators: Two-Variable Tokenization and Performance Boundaries**

This was the narrower fallback before the structural path was added. It is no
longer the selected title or the best description of the current pair compiler.

## Terms to avoid or qualify

- Avoid “matrix multiplication” without immediately writing **XOR-AND
  contraction over `GF(2)`**.
- Use `⇕` (LaTeX `\Updownarrow`) for XOR throughout the paper. Define it as XOR
  at first use and briefly explain that `[⇕]` is the 90-degree rotation and
  complement of `[⇔]`; do not substitute `⊕` or `\oplus`.
- Name a specific operator CM with bracketed operator notation, such as `[⇕]`.
  Use `[Θ]=[[Θ_11,Θ_10],[Θ_01,Θ_00]]` for the generic numeric CM, where
  `Θ_xy:=x Θ y` in true-first order, and set `[Θ]=[⇕]` when `Θ` is XOR.
  Reserve `C_f` or `[f]` as compact
  function-indexed appendix aliases rather than competing main-text names.
- Use `[\mathcal{M}_{X\Theta Y}]` for the formula-valued LM and display either
  its full indexed `2 x 2` formula matrix or the declared shorthand
  `\Theta_{ij}\otbktwo{X_i}{Y_j}`. Do not collapse this symbolic object into
  the numeric `[Θ]` notation before valuation.
- Describe `[\impax]=[⇔] ⇕ [⇕]` as an **entrywise Boolean superposition** and
  immediately say that Impax is tautological. Avoid an unqualified
  “superposition,” which can incorrectly suggest a quantum claim.
- Avoid equating LM entries with ANF coefficients or polynomials.
- In related work, use **formula-valued LM** for Brian Theory's object and
  **STP logical structure matrix** for Zhao-Gao-Cheng's numeric object; both
  traditions use “logical matrix” differently.
- Use “logical measurement pairing” only with the adjective **nonphysical** and
  interpret its output as a Boolean compatibility constraint.
- Use “rotation” as visual shorthand; theorem statements should identify
  transpose, row swap, column swap, or their composition.
- Avoid “novel matrix representation of logic.” The defensible candidate is the
  typed normalization/fusion pipeline and its measured boundary.
