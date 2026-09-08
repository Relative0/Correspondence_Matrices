# Visual and production specification — operator CMs v2

Status: teacher-audited proposed contract; no render authorization

## Learner promise

The learner can build a 2×2 operator CM from four input cases and derive why
four independently binary outputs produce sixteen two-input Boolean rules.

## Teaching-first visual sequence

Start with one object, not the gallery:

```text
two input switches → four identified cases → one complete CM → sixteen patterns
```

The full gallery is a result of the count, never the unexplained hook.

## Persistent visual grammar

- Amber: X row state; cyan: Y column state.
- White: current output; violet outline: the complete rule.
- Every cell retains its state-pair identity `11, 10, 01, 00`.
- Use the paper order: rows `X, ¬X`; columns `Y, ¬Y`.
- A matrix outline and operator label appear only after all four cases are set.

## Required compositions

| Beat | Visible action | Learning function |
|---|---|---|
| Definition | Two switches claim four cells | Ground the grid in input cases |
| AND | Four evaluations populate one matrix | Separate an entry from a complete rule |
| Count | Four binary cell choices yield sixteen patterns | Derive `2^4`, not merely state it |
| Examples | Six familiar patterns illuminate | Attach meaning without demanding memorization |
| Asymmetry | Implication's zero moves after operand swap | Show why declared order matters |
| Retrieval | Unnamed XOR is read from agreement/disagreement | Practice semantic reading |
| Close | One CM reconnects to its four cases | Consolidate the unit of representation |

## Restraint and accuracy

- Do not open on Figure 1 or the phrase “sixteen what?”
- Do not first show conventional truth-table order and then rearrange it; this
  adds an unnecessary transformation. Introduce the paper order directly.
- Name at most six patterns in the gallery; teach implication separately.
- Reconstruct source figures as legible vector art rather than screenshots.
- Exact matrices in paper order:

```text
AND [[1,0],[0,0]]   OR [[1,1],[1,0]]   XOR [[0,1],[1,0]]
equivalence [[1,0],[0,1]]   implication X→Y [[1,0],[1,1]]
```

Reject any preview that calls one cell an operator, calls the sixteen patterns
sixteen assignments, hides the state order, or introduces repository layouts.
