# Visual and production specification — logical matrices v2

Status: teacher-audited proposed contract; no render authorization

## Learner promise

The learner can identify an LM by its expression-valued entries, explain that
positive valuation produces a binary CM, and narrate the paper's larger-matrix
construction at a correct conceptual level.

## Persistent visual grammar

- Violet expression tile: LM entry.
- White binary tile: CM entry.
- Gold `V_T` scan: the only transition from expression to bit.
- Amber and cyan: declared left/right states.
- One cell keeps its identity through every transformation.

Persistent rail:

```text
smaller LMs → positioned 4×4 expressions → outer operator → V_T → binary CM
```

## Required compositions

| Beat | Visible action | Learning function |
|---|---|---|
| Definition | Four state expressions enter one frame | Define LM positively before contrasting it |
| Valuation | Equivalence expressions resolve cell by cell | Make LM→CM causal and visible |
| Construction | Smaller LMs supply positioned combinations | Prevent the “reshaped truth vector” model |
| Compound rule | Two inner rules feed outer implication | Expose the expression hierarchy |
| Worked cell | One false implication case is tracked | Anchor the 4×4 result in semantics |
| Full result | Exact rows appear with axes attached | Keep output checkable and ordered |
| Retrieval | One persistent cell changes entry type | Test the defining distinction |
| Boundary | Square paper rail separates from repo preview | Prevent framework conflation |

## Complexity restraint

- Do not display the base LM and equivalence LM simultaneously.
- Introduce tensor/projection terminology only after the positioning action is
  visually understood; do not narrate an unreadable symbolic derivation.
- Reveal one worked 4×4 cell before the full grid.
- Never relabel the example to a more familiar partition. The paper result uses
  rows `(Y,W)` and columns `(X,Z)`.
- Bra-ket notation is optional secondary notation, never the teaching spine.

## Accuracy gates

The worked expression is `(W XOR X) implies (¬Y AND Z)`, and the valued rows
must be `1100 / 1110 / 0011 / 1011`.

Reject any preview that treats valuation as matrix multiplication, calls an LM
binary, grows 4×4 by reshaping a truth vector, hides state order, or presents
repository rectangles as the paper's inductive construction.
