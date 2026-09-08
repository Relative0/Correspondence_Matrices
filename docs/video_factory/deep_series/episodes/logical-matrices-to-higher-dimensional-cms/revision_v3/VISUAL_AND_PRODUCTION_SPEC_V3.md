# Visual and production specification — logical matrices v3

Status: paper-audited bra-ket revision; narrated review candidate

## Learner promise

The learner can construct a base LM as a ket-bra outer product, explain how a
tensor product of smaller LMs yields a 4×4 expression grid, and identify
positive valuation as the step that produces the binary CM.

## Required mathematical sequence

```text
|X⟩ and ⟨Y| → |X⟩⟨Y| = M_XY
two 2×2 base LMs → tensor product → one 4×4 LM
⟨Y|⟨W| M |X⟩|Z⟩ → declared row/column order
LM expressions → V_T → CM bits
```

## Notation and accuracy

- Use proper `⟨ ⟩ ⊗ ᵀ`, with `|X⟩⟨Y|` as the compact outer-product form.
- For a base LM, explicitly expand `|X⟩=[X,¬X]ᵀ` and
  `⟨Y|=[Y,¬Y]` before displaying the matrix.
- Relate the 4×4 construction with
  `(|W⟩⟨X|)⊗(|Y⟩⟨Z|)=(|W⟩⊗|Y⟩)(⟨X|⊗⟨Z|)`.
- Preserve the paper's measurement form `⟨Y|⟨W| M |X⟩|Z⟩`, with rows
  `(Y,W)` and columns `(X,Z)`.
- Say `four components per side`, not `all four variables in each vector`:
  Y and W choose a row; X and Z choose a column; all four variables identify
  a cell together.
- Positive valuation is entry-wise logical evaluation, never matrix
  multiplication.

## Visual density

- The first scene must animate vector expansion into four expression cells.
- The tensor scene shows both 2×2 inputs, one worked Kronecker block, and the
  resulting 4×4 frame; no empty three-box pipeline.
- The compound-state scene expands both four-component vectors and crosses one
  row/column pair into a four-literal expression.
- The worked example tracks one false implication case before revealing all
  sixteen valued cells.
- Bra-ket notation is teaching content only in the first four scenes; it does
  not decorate the retrieval or repository boundary.

## Rejection conditions

Reject missing axis order, clipped compound vectors, a reshaped truth vector,
an unlabeled 4×4 matrix, tensor and outer product treated as interchangeable in
all contexts, or any claim that repository rectangles are the paper's formal
higher-dimensional construction.
