# Visual and production specification — operator CMs v1

Status: proposed contract; no render authorization

## Learner promise

The learner can explain why two inputs produce four cases, why four binary
outputs produce sixteen functions, and why one complete 2×2 matrix—not one
cell—represents one operator.

## Persistent visual system

Use four assignment cards as the persistent objects. They begin in conventional
truth-table order and move into the paper's declared state order:

```text
             Y       ¬Y
X           11       10
¬X          01       00
```

- Amber: X-side state and row labels.
- Cyan: Y-side state and column labels.
- White: current output/cell.
- Violet outline: complete operator matrix.
- A cell never loses its input-state label while values or operator names
  change.

## Required compositions

| Beat | Visible mathematical action | Attention/retention purpose |
|---|---|---|
| Hook | Figure 1 gallery contracts to one 2×2 matrix | Ask “sixteen what?” before explaining |
| State order | Four truth-table cards move into paper order | Make ordering visible, not verbal-only |
| AND | Four cases populate one matrix | Separate one output from one operator |
| Count | Four binary switches branch into sixteen patterns | Derive, rather than assert, `2^4=16` |
| Gallery | Named operators illuminate within all sixteen | Connect patterns to familiar rules |
| Asymmetry | Implication changes under operand swap | Demonstrate why ordering matters |
| Retrieval | XOR pattern appears without a name | Require semantic reading before recall |
| Handoff | Binary entries become expression tiles | Prepare LM without teaching it early |

## Gallery constraints

- Reconstruct Figure 1 as vector art; do not screenshot the PDF in the video.
- Use the paper's exact positive/negated state ordering.
- Never animate sixteen loose boxes. Every mini-matrix retains its 2×2 border
  and state-order legend.
- Name only the operators used in the script. The other matrices remain
  present as patterns, not a memorization demand.

## On-screen text

Limit central text to state labels, operator symbols/names, four-bit patterns,
and `2 × 2 × 2 × 2 = 16`. Full narration belongs in captions.

## Sound and pacing

- One restrained placement tick per AND cell.
- A four-step rising count for the binary-choice derivation.
- No music required.
- Hold the retrieval matrix completely still for four seconds.
- Final voice requires human-quality audition; SAPI is scratch timing only.

## Accuracy gates

Require exact paper-order matrices:

```text
AND          OR           XOR          equivalence   implication
10           11           01           10            10
00           10           10           01            11
```

Reject any asset that:

- calls sixteen matrices sixteen assignments;
- calls one matrix cell an operator;
- omits the `X, ¬X` and `Y, ¬Y` order;
- silently uses conventional `00,01,10,11` placement in the paper gallery;
- introduces CM-IR, repository rectangles, or performance.

