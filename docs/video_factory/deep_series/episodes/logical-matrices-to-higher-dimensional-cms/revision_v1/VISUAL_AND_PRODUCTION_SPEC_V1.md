# Visual and production specification — logical matrices v1

Status: proposed contract; no render authorization

## Learner promise

The learner can distinguish an expression-valued LM from a binary CM, explain
positive valuation, and trace the paper's construction path to one larger 4×4
CM.

## Persistent visual system

Keep one matrix frame and one cell identity through each transformation:

- Violet expression tile: LM entry.
- White binary tile: valued CM entry.
- Gold `V_T` scan: positive valuation.
- Amber/cyan: left/right logical states.
- Dashed tensor braces: construction, never mere decoration.

The persistent process rail is:

```text
2×2 LM → tensor/projection → compound 4×4 LM → V_T → 4×4 CM
```

## Required compositions

| Beat | Visible mathematical action | Misconception prevented |
|---|---|---|
| LM opening | Binary cells become expression cells | LM is not just another name for CM |
| Base LM | Four state conjunctions populate exact positions | Expressions do not appear arbitrarily |
| Valuation | `V_T` changes each expression tile to one bit | CM does not appear by an unexplained morph |
| Projection | 2×2 diagonal projection grows into tensor structure | 4×4 paper CM is not introduced as a reshape |
| Substitution | `A=W XOR X`, `B=¬Y AND Z` enter the structure | Compound logic owns the larger object |
| Modifier | Outer implication selects retained components | Operator composition is visible |
| 4×4 result | Exact matrix rows settle | Worked result is checkable |
| Retrieval | One LM cell persists across valuation | Entry type distinguishes LM from CM |
| Boundary | Square paper sequence and rectangular repo preview separate | Paper and repository rules do not merge |

## Exact worked example

Use the paper's example:

```text
(W XOR X) implies (¬Y AND Z)
```

The valued 4×4 result must be:

```text
1100
1110
0011
1011
```

Show the paper measurement order as left `(Y,W)` and right `(X,Z)`. The renderer
must not relabel the rows `W,X` and columns `Y,Z` merely because that split is
more familiar from the repository example.

## Notation policy

- Lead with plain-language states and expressions.
- Show `|X⟩`, `⟨Y|`, tensor-product, modifier, and `V_T` symbols only beside an
  already visible action.
- Define the paper's `Y ↓ Z` as `¬Y AND Z` when first shown.
- Say “exclusive-or” in narration; `XOR` is acceptable on screen.

## On-screen text

No paragraph text. Central formulas should fit on one line. Break the 4×4
construction into visible layers rather than shrinking the paper's full indexed
equation onto screen.

## Accuracy gates

Reject any asset that:

- calls an expression-valued LM a binary CM;
- says positive valuation is ordinary matrix multiplication;
- introduces the paper 4×4 matrix by reshaping a truth column;
- hides variable/state order;
- calls the compound 4×4 result one of the sixteen elementary operator CMs;
- presents 2×8 or 8×2 as the paper's formal general construction.

## Sound and pacing

Use one quiet valuation sweep and one tensor-expansion sound. No decorative
continuous music. Hold the LM/CM retrieval comparison for four seconds. Final
voice requires human selection from matched auditions.

