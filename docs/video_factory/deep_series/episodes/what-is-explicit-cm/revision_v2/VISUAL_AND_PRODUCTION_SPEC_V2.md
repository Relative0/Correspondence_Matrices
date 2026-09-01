# Visual and production specification — explicit CM revision v2

Status: proposed contract; no render authorization

## Learner promise

By the end, a learner must be able to map a four-bit assignment to an explicit
CM coordinate, explain what the cell stores, and predict what changes when the
row/column partition changes.

## Persistent visual object

Use one object throughout: a 16-row truth table whose identified output chips
physically become an explicit matrix. Do not rotate among generic scene
templates. Each new shot must advance the state of this same object or test the
learner's use of it.

Stable encodings:

- row variables, headers, and cursor: amber;
- column variables, headers, and cursor: cyan;
- active assignment and selected cell: white with a distinct outline;
- output zero and one: distinct glyph/texture as well as color;
- conceptual status: one small persistent badge, never repeated in narration.

The active truth table or matrix should occupy 60–75% of the safe teaching
area. Avoid empty right panels and passive three- or four-card rows.

## Required shot functions

| Beat | Instructional function | Required visible action |
|---|---|---|
| Cold open | orient and create curiosity | the same sixteen numbered chips morph list → 4×4 → 2×8 |
| Definition | pre-train terms | one assignment splits into ordered row bits and column bits |
| Construction | show mechanism | all sixteen truth outputs physically fold into labeled cells |
| Forward trace | worked example | `1011 → AB=10₂ → row 2; CD=11₂ → column 3; M[2,3]=1` |
| Reverse trace | repair misconception | `M[3,1]` coordinates recover `1101`; the zero value alone does not |
| Retrieval | generative practice | `1110` appears; cursor waits five seconds; answer reveals in stages |
| Transfer | generalize | track `1011` across 2×8, 4×4, and 8×2 layouts |
| Boundary | delimit the claim | concise stamps around the unchanged explicit matrix |
| Close | consolidate | assignment, two indices, one exact cell, complete matrix |

## Text and motion rules

- Do not burn narration sentences into the composition. Full captions belong
  only in the optional VTT/embedded subtitle track.
- Prefer formulas, axis headers, coordinates, and questions of no more than 12
  words.
- No visual layout may recur merely because another cue began.
- A meaningful state change must alter the learner's model, show a causal step,
  or solicit/reveal an answer. Pulses, fades, and label swaps do not count by
  themselves.
- Every output chip keeps a stable identity through every reshape.
- Use half-open frame intervals and frame-derived deterministic motion as in the
  existing factory.
- Optional restrained sound design: one fold whoosh, bit-placement ticks,
  cursor clicks, and a quiet retrieval-reveal tone. No continuous music is
  required for the pilot.

## Narration contract

- Synthesize paragraph-sized thought units, not isolated sentences.
- Target 135–145 WPM with varied sentence length and natural emphasis.
- Use contractions and direct questions where natural.
- Keep pauses below 1.5 seconds except the explicit five-second retrieval hold
  and brief visual inspections.
- Do not use Microsoft Mark/SAPI for the release candidate. It may be used only
  for a clearly labeled scratch timing track.
- Before final synthesis, produce 20–30 second auditions of at least two
  human-quality local or authorized neural voices using the same passage. Voice
  selection is a human gate.

## Prohibited learner-facing phrases

The following are machine/audit language and must not appear in narration:

- “this episode has one job”;
- “watch for the label”;
- “now isolate”;
- “matched before-and-after view”;
- “not a substituted workload”;
- “the invariant is”;
- “the accompanying view makes this step concrete”;
- “read that statement only within this scope”;
- “the measurement boundary is”;
- “the uncertainty field says”;
- “the nearest confusing lesson” or “this episode owns.”

## Proposed claim delta

Do not edit the shared claim registry until content approval. The v2 package
needs a new fact claim equivalent to:

```json
{
  "id": "cm-ordered-basis-indexing",
  "allowed_wording": "An explicit CM is interpreted relative to declared ordered row and column axes; for binary axes R and C it has 2^|R| rows and 2^|C| columns, and changing the split or order can change shape and cell positions without changing the Boolean function.",
  "type": "fact",
  "status": "proposed",
  "scope": "implemented dense output contract",
  "measurement_boundary": "representation",
  "sources": [
    {"source_id": "src-cm-build", "locator": "eval_cm_boolean"},
    {"source_id": "src-cm-ir", "locator": "materialize_cm reshape to 1 << len(R), 1 << len(C)"}
  ]
}
```

Remove `live-vs-ambient` bindings from this episode unless a direct, necessary
recap survives. The recommended script contains no such recap.

## Pre-render checks

1. Recompute the 16 truth values from the expression and require the exact
   sequence `0111011101111000`.
2. Assert the displayed matrix equals rows `0111`, `0111`, `0111`, `1000`.
3. Assert the worked examples: `1011 → M[2,3]=1`, `1101 → M[3,1]=0`, and
   `1110 → M[3,2]=0`.
4. Reject any preview or contract containing `0001111011100001`.
5. Run semantic near-duplicate detection over narration, not exact-string checks
   alone.
6. Produce a contact sheet dense enough to show every instructional function,
   not merely evenly sampled time points.
7. Review a scratch animatic with captions off and on.
8. Approve the script, claim delta, visual contract, and voice before producing
   a full-resolution candidate.

## Versioning and execution

Preserve all v1 outputs and hashes. Write v2 media under a new versioned output
directory. Local low-resolution animatic work is allowed once the content
package is approved. RunPod or another paid/remote render requires a new,
explicit, cost-bounded proposal; the consumed first-five authorization cannot
be reused.
