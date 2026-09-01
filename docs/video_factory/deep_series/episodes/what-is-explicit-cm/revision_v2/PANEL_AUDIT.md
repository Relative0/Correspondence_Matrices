# Expert-panel audit — What an explicit correspondence matrix is, revision v2

Date: 2026-09-01  
Status: revision proposal; no render or publication authorization  
Current released candidate preserved: `../output/what-is-explicit-cm.mp4`

## Decision

Rebuild episode 5 around one continuous worked problem. Do not patch the
current ten-minute edit and do not regenerate it from the generic v2 authoring
templates. The scientific definition is sound, but the narration and visual
contracts behave like audit artifacts rather than a lesson.

Target **5:30–6:30**, approximately **650–800 naturally spoken words**, with
inspection and retrieval pauses only where the learner has something concrete
to inspect or answer. The duration is determined by the teaching arc, not by
the current `core_episode` word or composition quota.

## Evidence from the current candidate

- Final duration: 599.988 seconds.
- Source narration: 1,077 declared words, 67 cues, 66 spoken cues.
- Voice: 66 separately synthesized Microsoft Mark/Windows SAPI clips.
- Spoken audio occupies about 393.6 seconds of roughly 596.5 seconds of cue
  windows, leaving about 202.8 seconds of trailing silence.
- The 24 scenes cycle through exactly three visual primitives eight times each:
  `expression_matrix`, `representation_compare`, and `boundary`.
- The contact sheet repeatedly returns to the same expression/matrix split and
  the same `Assignment → Index → Pack → Read` card row.
- Exact-duplicate validation passes, but semantic duplication does not. The
  script repeats long production templates such as “The example definition and
  output meaning stay fixed,” “Holding that element fixed,” “The invariant
  is,” and “The accompanying view makes this step concrete.”
- Full narration sentences are burned into the lower rail while the same words
  are spoken, even though an optional caption track also exists.

The current factory's minimum word, composition, and state-change quotas are a
root cause. They reward filler and cosmetic motion. For the pilot, replace them
with instructional-function gates: orient, construct, demonstrate, predict,
reveal, contrast, retrieve, and transfer.

## Panel synthesis

The panel comprised an educational-video director/editor, a learning-science
reviewer, and a repository-grounded CM domain reviewer. All three independently
recommended:

1. Use the truth table becoming a matrix as the episode's single visual object.
2. Remove internal claim-registry and production language from narration.
3. Remove the live-support/ambient detour; episode 4 owns that lesson.
4. Add the matrix dimension rule and show that changing the partition changes
   shape and addresses, not the Boolean function.
5. Demonstrate a complete assignment-to-cell trace and an immediate retrieval
   check.
6. Replace isolated SAPI sentence clips with paragraph-sized, conversational
   narration from a human or high-quality neural voice.

One learning-review draft mistakenly evaluated assignment `1011` as output
zero. Independent recomputation and the repository's correct executable bit
sequence confirm:

```text
F = (A AND B) XOR (C OR D)
1011 -> (1 AND 0) XOR (1 OR 1) -> 0 XOR 1 -> 1
row AB=10 (2), column CD=11 (3), M[2,3]=1
```

The verified row-major truth sequence is `0111011101111000`, giving rows
`0111`, `0111`, `0111`, and `1000`.

## Content disposition

### Keep

- An explicit CM is a dense, exact truth-layout representation.
- The row/column variable partition and declared order determine cell addresses.
- The stable function `F=(A AND B) XOR (C OR D)`.
- One 4×4 construction with A,B on rows and C,D on columns.
- The distinction “layout changes; function does not.”
- One short boundary: dense does not automatically mean compact, solver-like,
  or fast.

### Add

- Explicit dependence on **ordered** row and column axes.
- `2^|R|` rows, `2^|C|` columns, and `2^(|R|+|C|)` cells for binary variables
  covered by those axes.
- The concrete equations `row = 2A+B` and `column = 2C+D` for this declared
  MSB-first order.
- A forward trace, a reverse-coordinate trace, and one learner retrieval trace.
- A 2×8 / 4×4 / 8×2 morph showing the same sixteen outputs under different
  partitions.
- A learner-facing reason for the representation: two-coordinate addressing
  exposes row and column slices of the exact function.

### Cut or move

- “This episode has one job,” “watch for the label,” “now isolate,” “matched
  before-and-after,” “not a substituted workload,” “the invariant is,” and
  similar authoring scaffolds.
- Spoken scope, measurement-boundary, uncertainty-field, content-ownership,
  and provenance metadata. Keep those in machine-readable contracts.
- Packed-vector and timing-ratio discussion; later episodes own them.
- Live support and inert-axis removal; episode 4 owns them.
- Detailed CM non-claims and explicit-CM-versus-CM-IR comparisons; episodes 6
  and 7 own them.

## Required correctness fixes

1. Rename the learner-facing title from “What a correspondence matrix is” to
   **“What an explicit correspondence matrix is.”** The broader label `CM`
   can denote different artifacts elsewhere in the project.
2. Replace “reading a cell backward recovers the row and column bits” with
   “reading the cell's coordinates backward recovers the axis bits.” The output
   value alone is not invertible.
3. Qualify generalized cell interpretation by the declared ordered axes and any
   fixed context.
4. Never say an inert declared axis disappears from the same explicit matrix.
   Materialization preserves it through repeated rows or columns; removing it
   creates a separate reduced-support view.
5. Replace the invalid sequence `0001111011100001` in
   `../preview.renderer_brief.json` when v2 previews are regenerated. Do not
   reuse that preview as technical evidence. The executable production
   contracts use the correct sequence `0111011101111000`.

## Learning and attention gates

- The first 30 seconds must show the promised transformation and match the
  title; YouTube's retention guidance treats the first 30 seconds as a distinct
  intro checkpoint and recommends moving compelling later material earlier.
- Apply coherence, signaling, temporal contiguity, segmenting, conversational
  style, and the human-voice principle. These are summarized in Mayer's
  evidence review of multimedia instruction.
- No central screen may repeat a full spoken sentence. Use short labels,
  equations, coordinates, and prompts; retain full captions as an optional
  track.
- At least 70% of learner-facing screen time must advance or test the persistent
  truth-table/matrix object. Decorative or generic cards do not count.
- Every pause longer than 1.5 seconds must be an intentional prediction,
  inspection, or transition beat.
- No visual layout may recur without a changed instructional function.

References: [YouTube audience-retention guidance](https://support.google.com/youtube/answer/9314415),
[Mayer, “Applying the science of learning to medical education”](https://doi.org/10.1111/j.1365-2923.2010.03624.x).

## Gate to rendering

Do not render v2 until the script, visual specification, proposed claim delta,
and narration sample have human approval. A local low-resolution animatic is
the next safe review artifact. RunPod, paid voice, publication, commit, and push
remain unauthorized.
