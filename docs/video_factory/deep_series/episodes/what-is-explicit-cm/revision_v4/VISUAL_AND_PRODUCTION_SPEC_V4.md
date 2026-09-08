# Visual and production specification — repository explicit CM layout v4

Status: teacher-audited proposed contract; no render authorization

## Learner promise

The learner can map a complete assignment to a matrix coordinate, state the
metadata needed to decode that coordinate, and predict what changes when the
ordered row/column partition changes.

## Two-rail visual grammar

Invariant rail: function, complete assignment, output.  
Layout rail: ordered `R`, ordered `C`, MSB-first convention, shape, coordinate.

Amber encodes rows, cyan columns, and white the tracked assignment-output card.
The learner first sees one tracked card; the full set of sixteen appears only
when the matrix is materialized.

## Required compositions

| Beat | Visible action | Learning function |
|---|---|---|
| Concrete hook | `1011 → 1` waits beside the function | Give the indexing task a purpose |
| Contract | Assignment splits into row and column bits | Make coordinate construction causal |
| 4×4 build | Tracked case lands first; remaining cases fill | Move from one example to the complete layout |
| Missing key | Coordinate remains while metadata disappears | Show why a coordinate has context |
| Retrieval | Learner maps `1110` | Practice the complete operation |
| Repartition | Same card crosses 4×4, 2×8, and 8×2 | Separate invariant mapping from layout |
| Dense close | Every cell fills in all three shapes | Define dense with no performance tangent |

## Exact values

For `F=(A AND B) XOR (C OR D)`, `R=[A,B]`, `C=[C,D]`, MSB-first:

```text
row-major: 0111011101111000
rows: 0111 / 0111 / 0111 / 1000
1011: (2,3) → 1
1110: (3,2) → 0
```

Repartitioning `1011 → 1`:

```text
AB/CD 4×4 (2,3)   A/BCD 2×8 (1,3)   ABC/D 8×2 (5,1)
```

## Restraint and rejection conditions

- Do not open with all sixteen cards or a recap of the prior sixteen matrices.
- Use “ordered lists,” “coordinate,” “row index,” and “column index”; do not use
  “set” or “address.”
- Keep the paper/repository boundary to one sentence after the mechanism is
  understood.
- Do not preview CM-IR, packed output, solvers, or performance in this lesson.
- Reject anonymous output chips, missing axis metadata, the incorrect vector
  `0001111011100001`, or any unqualified claim that 2×8 and 8×2 are the paper's
  formal construction.
