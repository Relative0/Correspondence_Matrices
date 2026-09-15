# CM video series — current-state handoff prompt

**State date:** 2026-09-12  
**Workspace:** `C:\Users\brian\Documents\CM_Computation`

## Copy-paste prompt

Act as the incoming scientific editor, curriculum architect, educational-video
reviewer, and production-planning agent for the Correspondence Matrices (CM)
video project. Work in:

`C:\Users\brian\Documents\CM_Computation`

Begin with read-only inspection. Read the applicable `AGENTS.md` instructions
and inspect the repository status before drawing conclusions. Preserve all
unrelated work. Do not commit, push, publish, call RunPod, create a cloud
resource, use a paid service, or expose any credential unless the user later
approves an exact, separately identified action.

Your first task is to understand and report the current video-series state,
then recommend the next small review or production wave. Do not assume that an
older master prompt is completely current.

## Authority and precedence

Use this precedence order when artifacts disagree:

1. The exact scripts, visual specifications, production code, and QA records
   that generated the three newest narrated masters listed below.
2. The versioned foundational-CM v3/v4 audits and deltas.
3. The current shared 51-episode content Bible as the baseline curriculum.
4. `RUNPOD_DEEP_SERIES_MASTER_PROMPT_V2.md` for broad production principles,
   but not as the final word on episode count or the newest foundational work.
5. Generated catalog views. Regenerate rather than hand-edit them when an
   approved source contract changes.

Read these first:

- `docs/video_factory/deep_series/episode_content_bible.json`
- `docs/video_factory/deep_series/EPISODE_CONTENT_BIBLE.md`
- `docs/video_factory/RUNPOD_DEEP_SERIES_MASTER_PROMPT_V2.md`
- `docs/video_factory/deep_series/foundational_cm_revision_v3/CROSS_EPISODE_AUDIT_V3.md`
- `docs/video_factory/deep_series/foundational_cm_revision_v3/SERIES_ORDER_DELTA_V3.json`
- `docs/video_factory/deep_series/foundational_cm_revision_v3/CONTENT_BIBLE_DELTA_V3.json`
- `docs/video_factory/deep_series/foundational_cm_revision_v3/PREREQUISITE_CLEANUP_DELTA_V3.md`
- `docs/video_factory/deep_series/foundational_cm_revision_v4/TEACHER_SCRIPT_AND_VISUAL_AUDIT_V4.md`
- `docs/video_factory/source_registry.json`
- `docs/video_factory/claim_registry.json`
- `docs/video_factory/glossary.json`
- `docs/recognition/LEARNING_ROADMAP.md`
- `docs/recognition/experiment_register.json`

The shared Bible currently has 51 episodes and content identity:

`e7c9c86b5c82fa02af16c20d6929be7c2766aaa835f540ab75c6835cc765877a`

It has not yet absorbed the two proposed foundational episodes. The
foundational v3 delta proposes a 53-episode curriculum by inserting
`operator-cms-from-truth-tables` and
`logical-matrices-to-higher-dimensional-cms` immediately after
`live-support-ambient` and before `what-is-explicit-cm`. Treat 53 episodes as
the latest suggested order, but describe it as a candidate until a new shared
Bible and review identity formally apply the delta.

## Newest completed videos

These are the newest and most relevant review masters. They completed the
approved RunPod proposal
`cm-video-foundational-three-production-remote-v3`, identity
`e15b8b08b7ad0921803176ff48b8024c7105e9b42e17182d409cc0c0c6d2bde1`.
Estimated compute spend was approximately USD 0.5396, the owned pod was
deleted, and local postflight verification passed. Publication was not
authorized.

### 1. Why there are sixteen 2x2 operator CMs

Latest source:

- `docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v3/SCRIPT_V3.md`
- `docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v3/VISUAL_AND_PRODUCTION_SPEC_V3.md`

Latest narrated master:

- `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/operator-cms-from-truth-tables/operator-cms-from-truth-tables.narrated-master.mp4`

This lesson owns the four ordered input-state pairs, the count `2^4 = 16`, one
complete 2x2 matrix per Boolean operator, the full named operator table, and
introductory ket-bra decompositions. Do not call the sixteen objects “sixteen
answers”; they are sixteen complete two-input Boolean functions/matrices.

### 2. From logical matrices to higher-dimensional CMs

Latest source:

- `docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v3/SCRIPT_V3.md`
- `docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v3/VISUAL_AND_PRODUCTION_SPEC_V3.md`

Latest narrated master:

- `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/logical-matrices-to-higher-dimensional-cms/logical-matrices-to-higher-dimensional-cms.narrated-master.mp4`

This lesson owns expression-valued logical matrices, positive valuation, the
paper's ket-bra/tensor construction, and its worked 4x4 CM. Keep the paper's
square construction distinct from the repository's arbitrary rectangular
row/column materialization.

### 3. What a correspondence matrix is / repository explicit-CM layout

Latest source:

- `docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/SCRIPT_V4.md`
- `docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/VISUAL_AND_PRODUCTION_SPEC_V4.md`

Latest narrated master:

- `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/results/what-is-explicit-cm/what-is-explicit-cm.narrated-master.mp4`

This lesson owns ordered row/column variable lists, assignment-to-coordinate
addressing, and equivalent 4x4, 2x8, and 8x2 layouts for the same Boolean
function. It replaces the older first-five version of this episode for current
editorial and visual review.

Shared QA records:

- `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/LOCAL_VERIFICATION_V3.json`
- `docs/video_factory/runpod/foundational_three_v3/remote/runpod-foundational-three-v3-20260901-151230/POSTFLIGHT_V3.json`

All three are 1920x1080, 30 fps H.264 with 48 kHz mono AAC narration,
embedded English captions, WebVTT sidecars, symbol-safe DejaVu rendering, and
full local decode checks. The provisional offline voice is Kokoro `af_heart`.
Human review of voice naturalness, pacing, mathematical readability, teaching
clarity, and attention retention is still required.

## Earlier first-five material

An earlier production rendered chapter videos for:

1. `conceptual-vs-measured`
2. `why-boolean-computation`
3. `expression-truth-function`
4. `live-support-ambient`
5. the older `what-is-explicit-cm`

Those artifacts live under:

`docs/video_factory/runpod/deep_series_first5_v1/remote/runpod-first5-production-v1-20260831-160714/attempt-1/extracted/results`

Do not silently treat that batch as the current release set. The older
`what-is-explicit-cm` is superseded for review by the new narrated master.
Episodes 2-4 still have a proposed, unapplied cleanup in
`PREREQUISITE_CLEANUP_DELTA_V3.md`: remove premature CM layout/indexing and
factory-like narration so those lessons teach only their own prerequisites.
They require versioned revisions and fresh review before being called final.

## Latest suggested 53-episode sequence

### Section 1 — Series orientation

1. `conceptual-vs-measured`

### Section 2 — Boolean functions and CM foundations

2. `why-boolean-computation`
3. `expression-truth-function`
4. `live-support-ambient`
5. `operator-cms-from-truth-tables` — newly inserted; newest master completed
6. `logical-matrices-to-higher-dimensional-cms` — newly inserted; newest master completed
7. `what-is-explicit-cm` — newest master completed; supersedes older review render
8. `what-cm-does-not-claim`
9. `explicit-cm-vs-cm-ir`

### Section 3 — CM-IR representation and identity

10. `cm-ir-nodes-sharing`
11. `canonicalization-interning`
12. `cm-ir-persistence`

### Section 4 — Execution and materialization paths

13. `packed-words-selection`
14. `eager-lazy`
15. `pair-aware`
16. `hybrid-partial`
17. `parallel-cm`

### Section 5 — Comparators and lowering

18. `raw-ast`
19. `cse-plain-language`
20. `cse-vs-cse-flat`
21. `cm-ir-vs-cse-flat-mechanism`
22. `instruction-operations-memory`

### Section 6 — Measurement, evidence, and corrections

23. `measurement-boundaries`
24. `read-a-ratio`
25. `scope-boundaries`
26. `reuse-break-even`
27. `b2b4-corrected`
28. `b2b4-runpod`
29. `epfl-parity`
30. `selector-width-limit`
31. `exact-comparison-protocol`
32. `no-fastest-chart`
33. `correction-story`

### Section 7 — Toolbox and applications

34. `toolbox-map`
35. `configuration-models`
36. `circuits`
37. `policy-rule-systems`
38. `representation-decision`

### Section 8 — CRSE recognition research

39. `recognition-question`
40. `recognition-c2`
41. `recognition-c3-c5`
42. `recognition-c6`
43. `recognition-c9-c11`
44. `recognition-c12-c16`
45. `recognition-c17-c20`
46. `recognition-c21-c22`
47. `recognition-c23`
48. `recognition-d-tasks`
49. `recognition-d8`
50. `recognition-d9`
51. `recognition-d10`
52. `recognition-e1-e2`

### Section 9 — Provenance and reproducibility

53. `source-hash-reproduction`

The recognition research has continued since this sequence was drafted. Audit
the current recognition roadmap, experiment register, retained milestone
reports, and source hashes before scripting episodes 39-52. Do not invent new
results or convert newer exploratory/negative/not-promoted work into promoted
claims. If the later milestones require different partitioning, propose a
versioned curriculum delta rather than silently changing episode ownership.

## Editorial and visual requirements

- Teach the positive concept first; do not open by listing what it is not.
- Give every episode one distinct teaching responsibility and one persistent
  visual object that changes causally through the lesson.
- Avoid repetitive card rows, generic three-box slides, large unused spaces,
  repeated slogans, and narration that merely reads the screen.
- Use diagrams, expressions, assignments, matrices, traces, timelines,
  comparisons, and retrieval pauses when they materially teach the concept.
- Keep mathematical symbols render-safe. Use drawn matrix brackets and an
  audited font. Use bra-ket/ket-bra notation where it explains the initial
  dyads, outer products, tensor construction, or 4x4 origin; do not decorate
  every later matrix with it.
- Preserve the paper's declared state order and the repository's declared
  variable/address ordering. Never let an unlabeled ordering imply semantics.
- Distinguish expression syntax, Boolean function, truth table, operator CM,
  logical matrix, explicit dense CM, packed truth vector, CM-IR, raw AST, plain
  CSE, and CSE-flat.
- Mark conceptual examples as conceptual. Bind factual and measured statements
  to the claim/source registries with their exact scope and boundary.
- Keep overlap brief and purposeful. A recap may orient the learner but may not
  reteach the neighboring episode's owned mechanism.
- Treat the current voice as provisional until a person reviews it. Do not call
  mechanically valid audio pedagogically final.

## Immediate deliverable

Produce a concise current-state report containing:

1. A table of all 53 candidate episodes with status: baseline-only,
   script/contract available, earlier review render, newest narrated master,
   revision required, or source re-audit required.
2. A supersession map showing exactly which earlier scripts/renders should and
   should not be used.
3. Any discovered drift between the 51-episode shared Bible, the 53-episode
   proposed order, registries, catalogs, and current recognition research.
4. A recommended next batch of no more than three episodes, chosen for
   prerequisite continuity and minimal overlap.
5. For that batch only, a local editorial/visual work plan and review gates.

Do not render or spend money as part of this first handoff task. If remote
production later becomes useful, prepare a new exact proposal with immutable
inputs, cost ceiling, cleanup rules, and separate explicit authorization.
