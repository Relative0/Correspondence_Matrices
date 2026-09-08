# Visual and production specification — operator CMs v3

Status: paper-audited bra-ket revision; narrated review candidate

## Learner promise

The learner can build a 2×2 operator CM from four input cases, derive why the
four binary outputs produce sixteen rules, and read the paper's ket-bra basis
notation without mistaking one basis dyad for a complete operator family.

## Teaching-first sequence

```text
four cases → AND → four basis dyads → 16 named operator CMs → retrieval
```

## Bra-ket scope

- Introduce bra-ket only after AND is understood from its truth behavior.
- Define `|1⟩=[1,0]ᵀ`, `|0⟩=[0,1]ᵀ`; their transposes are bras.
- Show the paper's equality `|i⟩ ⊗ ⟨j| = |i⟩⟨j|` and call it an outer
  product or basis dyad.
- State that an operator CM is an XOR sum of the basis dyads corresponding to
  its 1 entries.
- Remove bra-ket after the introductory table, except for one brief retrieval
  reminder.

## Figure-1 reconstruction

Replace the 8×2 thumbnail gallery with a 4×4 table inspired by the paper's
Figure 1. Each tile has a name or expression above, a matrix at center, and a
dyadic expansion below. Use these exact entries in the paper's row/column
order `XY, X¬Y, ¬XY, ¬X¬Y`:

```text
true 1111   false 0000   equivalence 1001   XOR 0110
AND 1000    NOR 0001     X∧¬Y 0100          ¬X∧Y 0010
X→Y 1011    Y→X 1101     OR 1110             NAND 0111
Y 1010      ¬Y 0101      X 1100              ¬X 0011
```

The dyadic expansion for a bit pattern includes exactly the corresponding
members, in position order:
`|1⟩⟨1|`, `|1⟩⟨0|`, `|0⟩⟨1|`, `|0⟩⟨0|`.

## Legibility gates

- Table is 4 columns by 4 rows at 1920×1080; never eight matrices across.
- Operator name ≥ 19 px, matrix bit ≥ 18 px, dyadic line ≥ 15 px at master
  resolution; long sums may wrap once.
- Use proper `⟨` and `⟩`, not ASCII angle brackets.
- Glyph preflight covers `⟨ ⟩ ⊗ ⊕ ᵀ` in both repeated renders.
- Reject clipped dyadic sums, anonymous matrices, hidden state order, or any
  wording that calls the four dyads four operators.
