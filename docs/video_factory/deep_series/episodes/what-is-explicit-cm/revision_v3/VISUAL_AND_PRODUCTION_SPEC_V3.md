# Visual and production specification — repository explicit CM layout v3

Status: proposed contract; no render authorization

## Learner promise

The learner can map a complete assignment to a repository matrix coordinate,
state the context required to decode that coordinate, and predict what changes
under a different ordered row/column partition.

## Two-rail visual grammar

Maintain these rails for the entire episode:

### Invariant rail

- expression;
- complete assignment;
- exact output.

### Layout rail

- ordered `R` list;
- ordered `C` list;
- MSB-first convention;
- shape;
- row index;
- column index.

Amber encodes row-side data, cyan column-side data, and white the tracked
assignment-output card and selected cell. Each of the sixteen moving cards must
retain its full assignment ID.

## Required compositions

| Beat | Visible action | Teaching purpose |
|---|---|---|
| Opening | Sixteen labeled assignment-output cards settle | Distinguish these sixteen from operator CMs |
| Contract | `R`, `C`, and order appear before the matrix | Metadata precedes coordinate meaning |
| 4×4 build | All identified cards populate labeled cells | Show repository materialization |
| Forward trace | `1011 → (2,3) → 1` | Practice assignment-to-coordinate mapping |
| Missing context | Axis metadata disappears | Bare coordinate cannot recover assignment |
| Retrieval | `1110` waits before row/column/output reveal | Generative practice |
| Re-partition | Same card moves 4×4 → 2×8 → 8×2 | Separate invariant function from changing matrix |
| Dense | Every requested cell fills | Define dense without performance digression |
| Close | Three coordinates sit under one unchanged card | Consolidate invariant versus layout |

## Exact values

For `F=(A AND B) XOR (C OR D)`, `R=[A,B]`, `C=[C,D]`, MSB-first:

```text
row-major bits: 0111011101111000
rows:           0111 / 0111 / 0111 / 1000
1011:           (2,3) → 1
1101:           (3,1) → 0
1110:           (3,2) → 0
```

Re-partition tracking for `1011 → 1`:

```text
AB/CD    4×4    (2,3)
A/BCD    2×8    (1,3)
ABC/D    8×2    (5,1)
```

## Terminology gates

- Say **ordered lists** or **ordered sequences**, not sets.
- Say **coordinate**, **row index**, and **column index**, not address.
- Say **repository explicit CM layout** or **repository row-column truth
  layout** for the rectangular forms.
- State that the implementation route differs from the paper's LM/valuation
  construction.
- Do not call CM-IR or packed output the same object as the dense matrix.

## Overlap limits

- The operator-CM recap lasts no more than ten seconds and does not replay the
  gallery.
- The paper-construction recap is one sentence and one qualifier badge.
- Compactness, solver behavior, and performance are a handoff only.
- CM-IR and packed output appear as brief preview icons only.

## Sound and pacing

Use placement ticks for the first four cards, then a soft cluster sound for the
remaining twelve. One cursor cross and one re-partition sweep are sufficient.
No constant music. Final narration must use paragraph-sized synthesis and a
human-approved voice audition; SAPI remains scratch-only.

## Rejection conditions

Reject any preview that contains:

- “sixteen answers” without first naming sixteen assignments and outputs;
- “only their addresses changed”;
- anonymous output chips during re-partitioning;
- an unqualified claim that the 2×8 or 8×2 object is a paper CM;
- `0001111011100001`;
- detailed performance, solver, CM-IR, or packed-output instruction;
- passive three-box summaries or central paragraph text.

