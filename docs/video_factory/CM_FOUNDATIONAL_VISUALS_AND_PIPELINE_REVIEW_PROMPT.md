# CM foundational videos and full-pipeline review — next-agent prompt

**Prepared:** 2026-09-12  
**Workspace:** `C:\Users\brian\Documents\CM_Computation`

## Copy-paste prompt

Act as the incoming lead scientific editor, mathematics/domain reviewer,
teacher, cognitive-load reviewer, motion-graphics director, narration editor,
and CM video-pipeline engineer. Work in:

`C:\Users\brian\Documents\CM_Computation`

Carry this review through to concrete, versioned recommendations. Do not stop
at a generic list of ideas. Begin read-only, preserve unrelated work, and read
all applicable `AGENTS.md` instructions. Do not commit, push, publish, call
RunPod, create cloud resources, or use paid services. This task authorizes
local inspection, analysis, and preparation of versioned script/visual
revisions; it does not authorize another production render.

## First understand the project and series

Read this handoff completely before reviewing individual scenes:

`docs/video_factory/CM_VIDEO_SERIES_CURRENT_STATE_HANDOFF_PROMPT.md`

It records the newest completed videos, supersession rules, the 51-episode
shared Bible, the proposed 53-episode sequence, the earlier first-five batch,
and the current production boundaries.

Then read:

- `docs/video_factory/RUNPOD_DEEP_SERIES_MASTER_PROMPT_V2.md`
- `docs/video_factory/deep_series/episode_content_bible.json`
- `docs/video_factory/deep_series/EPISODE_CONTENT_BIBLE.md`
- `docs/video_factory/deep_series/foundational_cm_revision_v3/CROSS_EPISODE_AUDIT_V3.md`
- `docs/video_factory/deep_series/foundational_cm_revision_v3/SERIES_ORDER_DELTA_V3.json`
- `docs/video_factory/deep_series/foundational_cm_revision_v3/CONTENT_BIBLE_DELTA_V3.json`
- `docs/video_factory/deep_series/foundational_cm_revision_v3/PREREQUISITE_CLEANUP_DELTA_V3.md`
- `docs/video_factory/deep_series/foundational_cm_revision_v4/TEACHER_SCRIPT_AND_VISUAL_AUDIT_V4.md`
- `docs/video_factory/source_registry.json`
- `docs/video_factory/claim_registry.json`
- `docs/video_factory/glossary.json`
- `docs/video_factory/sources/CM_PAPER_SOURCE_NOTE_2026_09_01.md`

The shared Bible still contains 51 episodes with content identity
`e7c9c86b5c82fa02af16c20d6929be7c2766aaa835f540ab75c6835cc765877a`.
The latest suggested sequence contains 53 episodes by inserting:

1. `operator-cms-from-truth-tables`
2. `logical-matrices-to-higher-dimensional-cms`

between `live-support-ambient` and `what-is-explicit-cm`. That 53-episode
delta is proposed but has not been formally applied to the shared Bible. Do
not silently rewrite the Bible or generated catalog. Recommend a versioned
reconciliation if needed.

The larger curriculum has nine arcs:

1. Evidence-status orientation.
2. Boolean functions and CM foundations.
3. CM-IR representation, identity, canonicalization, and persistence.
4. Packed, eager/lazy, pair-aware, hybrid, and parallel execution paths.
5. Raw AST, CSE, CSE-flat, CM-IR, instructions, operations, and memory.
6. Measurement boundaries, ratios, break-even, retained benchmarks,
   corrections, and comparison protocol.
7. Toolbox selection and applications in configuration, circuits, policy, and
   representation choice.
8. The CRSE recognition-research sequence.
9. Source hashes, provenance, and reproduction.

Use the full 53-item order in the handoff file as the sequence checksum. The
three foundational videos under review are a small part of that curriculum.
Protect their narrow lesson ownership so later videos still have distinct
work to do.

## The four referenced review artifacts

The user referred to four attached visuals:

1. **Symbol specimen** — this is a shared typography/notation QA still, not a
   fourth episode and not a fourth script:
   `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/symbol_preflight/symbol_specimen.png`
2. **Operator-CM animatic**:
   `docs/video_factory/deep_series/foundational_cm_production_v2/episodes/operator-cms-from-truth-tables/previews/operator-cms-from-truth-tables.silent-animatic.mp4`
3. **Logical-matrix animatic**:
   `docs/video_factory/deep_series/foundational_cm_production_v2/episodes/logical-matrices-to-higher-dimensional-cms/previews/logical-matrices-to-higher-dimensional-cms.silent-animatic.mp4`
4. **Repository-layout animatic**:
   `docs/video_factory/deep_series/foundational_cm_production_v2/episodes/what-is-explicit-cm/previews/what-is-explicit-cm.silent-animatic.mp4`

Review the symbol specimen as a cross-episode visual system. Review the three
animatics as previews, but also watch the actual newest narrated masters below.
The masters, scripts, captions, and QA reports are more authoritative than an
isolated preview frame.

## Current scripts and visual specifications

### A. Why there are sixteen 2x2 operator CMs

- `docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v3/SCRIPT_V3.md`
- `docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v3/VISUAL_AND_PRODUCTION_SPEC_V3.md`
- Narrated master:
  `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/operator-cms-from-truth-tables/operator-cms-from-truth-tables.narrated-master.mp4`
- Captions and narration report:
  `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/narration/operator-cms-from-truth-tables/`

This episode owns four ordered input cases, the derivation `2^4 = 16`, one
complete 2x2 matrix per two-input Boolean function, the named operator table,
state ordering, and a limited introductory use of ket-bra decomposition.

### B. From logical matrices to higher-dimensional CMs

- `docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v3/SCRIPT_V3.md`
- `docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v3/VISUAL_AND_PRODUCTION_SPEC_V3.md`
- Narrated master:
  `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/logical-matrices-to-higher-dimensional-cms/logical-matrices-to-higher-dimensional-cms.narrated-master.mp4`
- Captions and narration report:
  `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/narration/logical-matrices-to-higher-dimensional-cms/`

This episode owns expression-valued logical matrices, positive valuation,
ket-bra/outer-product and tensor construction, and the paper's worked 4x4 CM.
It must keep the paper's square formal construction distinct from the
repository's rectangular layout API.

### C. What a correspondence matrix is / repository explicit-CM layout

- `docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/SCRIPT_V4.md`
- `docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/VISUAL_AND_PRODUCTION_SPEC_V4.md`
- Narrated master:
  `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/what-is-explicit-cm/what-is-explicit-cm.narrated-master.mp4`
- Captions and narration report:
  `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/narration/what-is-explicit-cm/`

This episode owns ordered row and column variable lists, assignment-to-cell
addressing, and the 4x4, 2x8, and 8x2 layouts of one unchanged Boolean
function. It supersedes the older first-five version for current review.

Shared production verification:

- `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/LOCAL_VERIFICATION_V3.json`
- `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/POSTFLIGHT_V3.json`

The masters are 1920x1080, 30 fps H.264, with 48 kHz mono AAC narration,
embedded English captions, WebVTT sidecars, symbol-safe DejaVu rendering, and
full-decode QA. The offline Kokoro `af_heart` voice is provisional and still
requires human judgment.

## The pipeline being built

Understand the pipeline as gated layers, not as a single render script:

1. **Evidence and terminology** — source registry, claim registry, glossary,
   retained benchmark records, source hashes, evidence status, and scope.
2. **Curriculum** — episode Bible, lesson ownership, prerequisites, series
   order, stable examples, duration tiers, and cross-episode repetition audit.
3. **Authoring contracts** — episode JSON, chapters, claim maps, narration and
   caption contracts, visual/storyboard specifications, and retrieval checks.
4. **Compilation** — `deep_series_chapter_compiler.py` turns chapters into
   executable render contracts; WP1 records this contract layer.
5. **Rendering** — `foundational_cm_production.py` handles the current
   symbol-safe foundational implementation; the broader system integrates the
   versioned POP/IVC render tooling rather than creating disposable slide
   generators.
6. **Narration and captions** — `foundational_cm_narration.py` performs offline
   neural synthesis, cue fitting, 48 kHz normalization, caption creation, and
   muxing.
7. **Local review** — animatics, contact sheets, symbol specimen, scene timing,
   repetition checks, sparse-layout checks, content/evidence validation, and
   human editorial review.
8. **Immutable production planning** — content-approved scripts and contracts
   are packaged with hashes, bounded resource requirements, cost limits, and
   explicit exclusions.
9. **Separately authorized remote execution** — the RunPod controller may
   create only the exact approved resource, upload the frozen bundle, monitor a
   detached job, download a bounded archive, verify it, and delete the owned
   pod.
10. **Postflight and release gate** — frame/media hashes, full decode, audio,
    captions, symbols, cue timing, inventory cleanup, and final human review.
    Passing technical QA creates a review master; it does not authorize
    publication.

Important implementation entry points and reports include:

- `docs/video_factory/README.md`
- `docs/video_factory/ADR-001-CM-VIDEO-FACTORY.md`
- `docs/video_factory/deep_series_chapter_compiler.py`
- `docs/video_factory/deep_series/wp1/WP1_REPORT.md`
- `docs/video_factory/foundational_cm_production.py`
- `docs/video_factory/foundational_cm_narration.py`
- `docs/video_factory/runpod/foundational_three_v3_execute.py`
- `docs/video_factory/runpod/foundational_three_v3_finalize.py`
- `docs/video_factory/tests/test_foundational_cm_braket_narration.py`

## Review method

Apply these six lenses to the shared specimen and each episode:

1. **Domain correctness:** Verify every mathematical statement, state order,
   truth pattern, matrix entry, bra/ket orientation, tensor/outer-product step,
   assignment coordinate, and distinction between paper and repository
   semantics. Bind conclusions to the source and claim registries.
2. **Teaching:** Check whether a motivated first-time learner can state the
   central idea, follow the worked example, answer the retrieval question, and
   distinguish this lesson from its neighbors.
3. **Cognitive load:** Identify moments with too many symbols, labels, matrices,
   or simultaneous movements. Recommend staging, highlighting, progressive
   disclosure, pauses, and recap only where they improve comprehension.
4. **Attention and motion:** Replace passive boxes and unused space with causal
   transformations. Every movement should populate, map, compare, construct,
   address, test, or reveal something named in the narration.
5. **Dialogue and audio:** Remove mechanical phrasing, repeated sentence
   templates, throat-clearing, and narration that reads labels. Improve
   conversational cadence, emphasis, pronunciation, silence, and cue fit.
6. **Accessibility and typography:** Check contrast, caption timing, table
   readability, matrix brackets, glyph coverage, font size, color-independent
   meaning, and whether displayed notation remains readable at normal video
   size.

Honor these editorial rules:

- Open with the concept or a concrete question, not a list of disclaimers.
- Use one primary idea per narration cue.
- Preserve a distinct persistent visual object for each episode.
- Avoid generic three-box rows, repetitive card grids, decorative motion, and
  large empty areas that communicate nothing.
- Do not pad duration. Add detail only when it resolves a real conceptual gap.
- Keep cross-episode recap short; do not reconstruct a neighboring lesson.
- Use bra-ket/ket-bra notation where it explains basis dyads, outer products,
  tensor construction, or the first 4x4 origin. Do not place it under every
  later matrix merely as decoration.
- Do not call the sixteen operator matrices “sixteen answers.” They are the
  sixteen complete two-input Boolean functions under the declared ordering.
- Keep fact, conceptual example, measured result, revised result, negative
  result, and not-promoted result visibly distinct.

## Required output

Create a versioned review package without overwriting the current scripts,
specifications, animatics, or masters. It must contain:

1. A short executive verdict for the shared symbol specimen and each of the
   three episodes: keep, revise lightly, or revise substantially, with reasons.
2. A scene-by-scene table containing timestamp, current teaching purpose,
   correctness finding, attention/cognitive-load finding, dialogue edit,
   visual edit, and expected learner benefit.
3. A cross-episode repetition and ownership audit showing what should remain,
   move, or be cut.
4. A mathematical verification appendix with recomputed operator patterns,
   paper 4x4 construction, repository coordinates, and exact source locators.
5. A shared visual-system audit for the symbol specimen, mathematical fonts,
   matrix/table layout, color, highlighting, and caption-safe areas.
6. A prioritized enhancement list divided into:
   - must fix before another render;
   - high-value improvement;
   - optional polish.
7. New versioned script and visual-spec candidates only where the audit
   justifies them. Suggested next versions are operator-CM revision v4,
   logical-matrix revision v4, and `what-is-explicit-cm` revision v5. Preserve
   the existing versions unchanged.
8. A bounded local preview plan identifying only the scenes that need new
   stills or a low-resolution animatic before full rendering.
9. A decision on whether the provisional voice can remain for the next review
   pass, needs pronunciation/pacing changes, or should be replaced before any
   new production proposal.
10. A final readiness verdict. If the work is ready, prepare an immutable local
    review manifest. Do not prepare or execute a paid rendering authorization
    unless the user asks later.

Be concise but specific. Quote only the small portions of voiceover that need
editing. Prefer exact replacements and concrete visual actions over general
advice such as “make it more engaging.”
