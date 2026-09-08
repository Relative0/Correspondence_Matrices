# Correspondence Matrices paper — video-source note

Date checked: 2026-09-01  
Source: Brian Droncheff, *Correspondence Matrices; Algorithms for Propositional
Logic*, version 1.0.1, May 29, 2018  
Primary URL: https://www.b-theory.com/CorrespondenceMatrices.pdf  
Retrieved PDF SHA-256: `7a9958a2ec34e61318855a3e8054d668c7d9654de3316c4fe546f7db7a2503a9`

## Status and scope

This is an author manuscript introducing the paper's CM/LM framework. No
journal or conference publication record was established during the
foundational audit. Treat standard Boolean-function counts separately from the
paper-specific CM, LM, valuation, measurement, transformation, and
higher-dimensional claims.

## Video-safe primary-source claims

### Section 2.2 and Section 3 — printed pages 4–7

- The paper writes a ket as a column state vector and a bra as its transposed
  row vector.
- In the paper's notation, the dyadic outer product may be written
  `|i⟩ ⊗ ⟨j| = |i⟩⟨j|`.
- The four one-entry CM basis matrices are `|1⟩⟨1|`, `|1⟩⟨0|`,
  `|0⟩⟨1|`, and `|0⟩⟨0|`.
- An operator CM is formed as the XOR sum of the basis dyads at its positive
  entries. For example, AND is `|1⟩⟨1|`, OR is the sum of the first three
  dyads, and XOR is the sum of the two off-diagonal dyads.

### Section 3 and Figure 1 — printed pages 5–7

- A two-input operator is represented by a complete 2×2 binary CM under the
  state order `X, ¬X` by `Y, ¬Y`.
- The four one-entry 2×2 matrices form the CM basis matrices.
- Figure 1 displays sixteen distinct 2×2 correspondence matrices.
- The paper's listed matrices include:

```text
AND             OR              XOR             equivalence
[1 0]           [1 1]           [0 1]           [1 0]
[0 0]           [1 0]           [1 0]           [0 1]

implication     false           true
[1 0]           [0 0]           [1 1]
[1 1]           [0 0]           [1 1]
```

- The paper describes CMs as truth tables “rolled up” and requires compatible
  variables and ordering when comparing them.

### Section 4.1 — printed pages 14–16

- A logical matrix (LM) contains logical expressions.
- The base logical matrix is the ket-bra outer product
  `M_XY = |X⟩⟨Y|`, where `|X⟩=[X,¬X]ᵀ` and `⟨Y|=[Y,¬Y]`.
- The paper states that a CM is the positive valuation of an LM.
- The base LM for conjunction is:

```text
M_XY = [ X∧Y      X∧¬Y  ]
       [ ¬X∧Y     ¬X∧¬Y ]
```

- The paper's equivalence LM is:

```text
M_(X↔Y) = [ X↔Y       X XOR Y ]
          [ X XOR Y   X↔Y     ]
```

- Applying the paper's positive valuation yields the equivalence CM
  `[[1,0],[0,1]]`.

### Section 5.1 — printed pages 19–22

- The paper projects a 2×2 LM into tensor-product structure and substitutes
  compound expressions to build a 4×4 LM.
- Its four-variable construction tensors the two base objects
  `|W⟩⟨X|` and `|Y⟩⟨Z|`. In the measurement form, the row operand is
  `⟨Y|⟨W|` and the column operand is `|X⟩|Z⟩`; therefore the displayed
  row state is `(Y,W)` and the column state is `(X,Z)`.
- Its worked compound expression is `(W XOR X) implies (¬Y AND Z)`, also
  written using the paper's `Y downarrow Z` operator.
- The paper's corresponding valued 4×4 CM is:

```text
1100
1110
0011
1011
```

- The measurement order is left state `Y,W` and right state `X,Z`; ordering is
  explicitly significant.

### Section 5.2 — printed pages 22–23

- The formal induction describes a square `2^n × 2^n` LM for `2n` logical
  subexpressions and the corresponding valued CM.
- The earlier introductory wording about `n!` possible `n × n` matrices is not
  used as the dimensional rule in the videos; the formal induction is cited
  with its scope.

## Repository boundary

The paper does not define the repository API's arbitrary
`2^|R| × 2^|C|` rectangular materialization rule. Repository 2×8 and 8×2
outputs must be called **repository row-column truth layouts** or **repository
explicit CM layouts**, not unqualified paper higher-dimensional CMs.
