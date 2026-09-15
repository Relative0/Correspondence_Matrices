# Production prompt: the full advanced CM continuation

Prepared 2026-09-14. This is a reusable prompt; saving it does not start video
production or authorize service calls. Prefer continuing in the existing CM
video task, which retains the notation decisions, source checks and production
history. This file also supports a fresh task if needed.

## Prompt to execute when production is requested

Work in `C:\Users\brian\Documents\CM_Computation`. Act as a mathematics reviewer,
teacher, scriptwriter and video producer. Produce the **full proposed advanced
continuation, lessons 10–23**, with a separate narrated MP4 for every lesson and
a combined advanced-course MP4. Do not stop after the suggested first wave
10–12. Use stages internally for review and recovery, then complete the entire
authorized set. Add or split lessons if teaching clarity warrants it; retain
a mapping from the original 14 topics to the final lessons and avoid gaps.

### Read before authoring

Read applicable AGENTS.md files and these sources completely:

- `docs/CM_NOTATION_STANDARD_V3.md` and its inherited v2 standard.
- `docs/video_factory/deep_series/foundational_cm_tutorial_series_v2/README.md`
- `docs/video_factory/deep_series/foundational_cm_tutorial_series_v2/TEACHING_AND_SOURCE_REVIEW_V2.md`
- `docs/video_factory/deep_series/foundational_cm_tutorial_series_v2/ADVANCED_VIDEO_PROPOSAL_V2.md`
- `docs/video_factory/deep_series/foundational_cm_tutorial_series_v2/VALIDATION_V2.md`

Inspect relevant portions of the existing curriculum, visual renderer, narration
pipeline, layout checks and finalizer: `docs/video_factory/cm_tutorial_*_v2.*`.
Reuse proven components through successor code; do not edit frozen dependencies.
Inspect the shared episode Bible for topic ownership, without renumbering or
rewriting that shared curriculum as part of this local companion-course task.

Primary mathematical source: https://www.b-theory.com/CorrespondenceMatrices.pdf.
A reviewed snapshot is retained at
`docs/video_factory/deep_series/foundational_cm_tutorial_series_v2/sources/CorrespondenceMatrices_source_2026_09_14.pdf`.
Also consult https://relative0.github.io/Correspondence_Matrices/ and the actual
repository implementation for implementation-specific claims. Record source
versions. Validate derivations independently rather than copying printed claims.

### Required topic coverage and initial teaching order

Use the detailed examples, prerequisites and page references in the advanced
proposal; the full scope is:

| Lesson | Topic | Required teaching example |
|---|---|---|
| 10 | Swap operands by transposing a CM | `[⇒]` to `[⇐]`; track the zero, declared axes and reversed measurement. |
| 11 | Negate inputs versus output | Distinguish row swap, column swap and bit complement; work all three on implication. |
| 12 | Compose and decompose over XOR | `[∨] = [∧] ⇕ [⇕]`, then cancellation and overlapping terms. |
| 13 | Remove shared features: CM quotient | Define binary `A∧¬B`; OR minus AND yields XOR, reversed order yields zero. |
| 14 | Combine rules in a shared ordered basis | Verify `(X⇒Y) ⇕ (X∨Y) = ¬Y`; normalize differing operand order first. |
| 15 | Complement and factor logical matrices | Define symbolic complement and asymmetric factors; reconstruct a two-variable LM. |
| 16 | Measure with an LM | Work a verified matched selector example; distinguish symbolic formula, relation and scalar valuation. |
| 17 | Generalize tensor construction | Progress 2×2, 4×4, 8×8 with declared operand grouping and an addressed entry. |
| 18 | Transform and combine larger CMs | Derive permutations before moving entries; check all 16 four-variable assignments. |
| 19 | Explicit CM versus repository CM-IR | Expression graph, materialized layout and identity key; distinguish structural from semantic identity. |
| 20 | Build, query and validate in code | Actual public API for `(A∧B)⇕(C∨D)`; three layouts, lookup and all-input oracle check. |
| 21 | Packed evaluation and output cost | Tiny visible bit batch; eager/lazy choices; scalar, count and full-vector output contracts. |
| 22 | Fair performance and preparation cost | Label hypothetical break-even arithmetic; empirical claims require current reproducible evidence. |
| 23 | A bounded end-to-end application | Small configuration/access-policy example, output contract, compilation and scalar-oracle verification. |

Start from the existing nine foundations as prerequisites. Briefly reintroduce
the needed notation in each standalone lesson. Reorder or insert bridging
material when necessary before unfamiliar operations; do not merely slice a
long narration into arbitrary segments. Suggested lengths in the proposal are
guides, not padding requirements. Produce a curriculum map explaining ownership
and prerequisite changes, plus a source-to-scene evidence map.

### Teaching and notation requirements

- Begin with a concrete question and explain why the operation helps. Define
  every symbol before use. Connect each abstract formula to one visible example.
- Pair bracketed CM operator names with numeric arrays and declared axes. Define
  `[θ]` before assigning it; retain complete small matrices during calculations.
- Implication **between expressions too** uses short double `⇒`, requested as
  LaTeX `\Implies`. Follow the rendering mapping in standard v3. No single right
  arrow for implication/inference. Use equality where the calculation is equality.
- XOR is `⇕` / `\Updownarrow`, never `⊕` / `\oplus`. Impax is the actual centered
  overlay of `⇔` and `⇕`, centered both vertically and horizontally.
- Keep ordinary multiplication, Boolean AND/XOR matrix multiplication,
  elementwise operations, tensors and symbolic valuation explicitly distinct.
  Show intermediate arrays, dimensions, paired entries and the reduction step.
- Reveal steps with matching narration and highlight the corresponding entries.
  Use available space to explain the operation. Avoid unexplained formula jumps
  or a long sequence of static equations without worked interpretation.
- Include a five-second practice pause and an explained answer in every lesson.
  End by connecting the result to the next lesson, without relying on that
  transition for the current lesson to be understandable on its own.

### Known mathematical issues to handle

The printed page-12 example identifies `(X⇒Y) ⇕ (X∨Y)` as `¬X`. Under the stated
true-first X-row/Y-column axes, its matrix is `01/01 = [¬R]`, hence **¬Y**. The
counterexample X=0,Y=1 disproves the printed ¬X result. Recheck independently,
teach the corrected identity and record the source discrepancy. Verify the
later page-12 chain's middle operator before reuse. Do not alter the source PDF.

The quotient/backslash operation here is binary set difference `A∧¬B`, not
ordinary division, unary NOT or integer remainder. Verify LM measurement and
higher-dimensional identities symbolically and by exhaustive small assignments
before writing confident narration. Physical quantum computation and general
performance advantages do not follow from notation or a small example.

### Production, voice and authorization boundaries

Preserve all historical packages, especially the frozen foundation v1 and v2
deliveries. Do not correct or regenerate those videos for the new arrow rule.
Create an unused successor package, preferably
`docs/video_factory/deep_series/advanced_cm_tutorial_series_v1/`, and new
production scripts. If that package already exists, inspect its status and
resume safely or select a successor; never overwrite a frozen delivery.

Use one Brian identity throughout: `Fu3xLoDFv9UvgA2FXCUS`,
`eleven_multilingual_v2`, stability 0.85, similarity_boost 0.8, style 0,
use_speaker_boost true, speed 0.95; existing pipeline seed 5132026. Prefer
full-lesson synthesis and continuity context as supported by the pipeline.
Do not change voice, model or settings between scenes. Keep request receipts
and exact scripts. Reuse source recordings only after exact text and settings
checks. Voice identity is verifiable; perceived tone still needs listening.

Carry forward the user's explicit ElevenLabs/Brian and root `.env` key-access
authorization, within its applicable scope and any approved budget. Never print
the key, read unrelated secrets or commit receipts containing credentials.
Before the new full set's paid synthesis, total the final script characters and
estimate usage against the applicable approval. If the larger batch materially
exceeds that scope or budget, finish scripts, visual previews and local checks
first, then request only the additional synthesis spend with a concrete estimate.
Do not infer a new spending ceiling. Avoid new service charges until that
dependency is resolved; do not repeat approvals already covering the operation.

No RunPod, publishing, cloud deployment, commits or pushes. Use local rendering
and existing tools. Do not start automations or separate tasks without a request.

### Required deliverables and completion checks

Deliver every proposed topic as finished lesson video(s), plus:

- Individual MP4s, captions, complete scripts and visual specifications.
- A combined advanced-course MP4 with chapter markers and matching captions.
- A local review index linking each lesson, and prerequisite/renumbering map.
- Downloadable runnable examples for code lessons, tested against current APIs.
- Source/errata notes, narration settings and usage receipts without secrets.
- Mathematical checks, visual-layout reports, timing/audio/caption QA and final
  hashes. Verify frozen earlier manifests remain unchanged.

Exhaustively test tractable truth assignments and all displayed derivation
steps, rather than checking only that formulas occur in HTML. Inspect rendered
operator and derivation frames, including the new short double arrows. Decode
all final videos, check subtitle bounds and practice pauses, and review voice
consistency and narration-to-highlight alignment. Report any unperformed
subjective listening review honestly. Use the project interpreter for tests.
Review Git status/diff before reporting completion, separating existing changes.

Do not describe proposals, silent previews or incomplete narration as finished
videos. If a remaining external authorization is required, provide the complete
reviewable local preparation and a precise continuation state. Otherwise finish
the full set and link the individual-video index prominently. Keep progress
updates concise and recommend the next human review at delivery.
