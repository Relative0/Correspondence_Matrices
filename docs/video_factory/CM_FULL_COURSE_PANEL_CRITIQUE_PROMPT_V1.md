# Full-course CM critique: multidisciplinary review prompt

Prepared 2026-09-14. Saving this prompt does not start the review.

Recommended execution: a **new, focused critique task**, using **GPT-6 Astra,
high reasoning**. The new task provides a review boundary separate from the
production discussion; it does not by itself make the model independent or
guarantee lower cost. Use one coordinating reviewer applying the perspectives
below. Do not replicate the entire course across eight agents or generate
role-play conversations. No separate agents are required by this prompt.

Astra/high is the recommended reliability/cost tradeoff for the integrated
mathematical and educational judgment here. GPT-5.6 Terra/high is the lower-cost
alternative for a first-pass inventory, but the recommended main review should
resolve subtle mathematical and cross-lesson issues rather than merely identify
surface defects. Do not change model settings automatically. Official model
references: https://developers.openai.com/api/docs/models/gpt-6-astra and
https://developers.openai.com/api/docs/models. API prices are not a measurement
of this Codex task's billed cost or account usage.

## Copy-paste starter

Work in `C:\Users\brian\Documents\CM_Computation`. Read and follow
`docs/video_factory/CM_FULL_COURSE_PANEL_CRITIQUE_PROMPT_V1.md` completely.
Perform its evidence-based multidisciplinary critique of all 23 current CM
lessons and both combined courses. Produce the versioned local review package,
prioritized findings, and provisional revision recommendations. Do not modify
the videos, production sources, narration or frozen packages. No paid services,
secret access, RunPod, publishing, commits or pushes. State actual media-review
coverage and do not portray simulated expert/student perspectives as real
consultation or observed learner results.

## Review objective and authority

Determine how accurately and effectively these videos teach correspondence
matrices to their intended audiences. Evaluate the viewer's experience, not just
whether source code passes tests. Review both individual lessons and the complete
learning sequence, including the transition from paper notation to repository
implementation.

This task authorizes task-relevant read-only inspection, local media extraction,
independent mathematical/code checks, and additive review documents. Use an unused
package such as `docs/video_factory/deep_series/cm_full_course_panel_review_v1/`.
If already present, inspect and safely resume an unfinished review or create a
successor. Preserve frozen reports and all previous versions.

The deliverable is **critique plus proposed changes**, not implemented changes.
Give enough concrete alternatives to assess whether a diagnosis has a useful
solution, but do not rewrite the whole course or regenerate media. No ElevenLabs,
other paid services, uploads, secret access, `.env` reads, RunPod, publishing,
commits, pushes, production changes or automation. Existing narration authorization
does not require or justify synthesis during this critique-only task.

## Exact review corpus

Read applicable AGENTS.md instructions and `docs/CM_NOTATION_STANDARD_V3.md`
with its inherited v2 conventions. The active review targets are:

1. **Lessons 1–9:**
   `docs/video_factory/deep_series/foundational_cm_tutorial_series_v2/`
   - Start with README.md, CURRICULUM_V2.json, individual lesson MP4s,
     SCRIPT_AND_VISUAL_SPEC_V2.md, scene HTML/PNG assets, captions and timing reports.
   - Combined course: `cm_foundations_complete_course_v2.mp4`, approximately 27:13.
   - Delivery identity: DELIVERY_MANIFEST_V2.json.
2. **Lessons 10–23:**
   `docs/video_factory/deep_series/advanced_cm_tutorial_series_v1/`
   - Start with README.md, CURRICULUM_V1.json, individual lesson MP4s,
     SCRIPT_AND_VISUAL_SPEC_V1.md, scene HTML/PNG assets, captions and timing reports.
   - Combined course: `cm_advanced_complete_course_v1.mp4`, approximately 37:13.
   - Runnable examples: `examples/course_examples.py`.
   - Delivery identity: DELIVERY_MANIFEST_V1.json.

Together these comprise 23 lessons, about 64:26 and 225 authored teaching states.
Verify the inventory and durations; do not treat these expected counts as proof.
Do not accidentally review superseded drafts or the foundation-v1 videos.
The combined copies repeat the lesson content: assess their joins, chapter
navigation, continuity and cumulative pacing without duplicating all findings.

Primary mathematical reference:
https://www.b-theory.com/CorrespondenceMatrices.pdf

Retained snapshot:
`docs/video_factory/deep_series/foundational_cm_tutorial_series_v2/sources/CorrespondenceMatrices_source_2026_09_14.pdf`

Supplementary project site:
https://relative0.github.io/Correspondence_Matrices/

Inspect current repository implementations when judging implementation claims,
especially `cm_exprlib.py`, `cm_build.py`, `cm_build_lazy.py`, `cm_ir.py` and
`bitset_backend.py`. Read the shared episode Bible only as needed for topic
ownership; do not expand this critique to every planned episode or revise it.

Avoid dumping FRAME_MANIFEST files into context: they embed repeated font data.
Use the compact curriculum JSON, specific scene files, and timing reports.

## Panel: eight complementary review perspectives

These are structured analytical roles, **not eight real experts**. Do not invent
credentials, named consultants, quotations, interviews, votes or unanimity.
Use the lenses to find distinct failure modes, then consolidate the evidence.

| Perspective | Primary remit | Concrete questions |
|---|---|---|
| Mathematical logician / Boolean algebra reviewer | Correctness, definitions, notation and scope | Are equalities valid for every relevant assignment? Are matrix, entrywise and tensor operations distinguished? Do source corrections hold independently? |
| CM/software engineer and reproducibility reviewer | Actual implementation and runnable claims | Do code examples use the current API? Are graph identity, layout, packed output, lazy behavior and cost claims accurate? Can the example be reproduced? |
| Learning scientist / instructional designer | Prerequisites, sequencing, scaffolding and retention | Is a concept taught before use? Do worked examples fade into independent practice? Are there jumps between knowing notation and being able to use it? |
| Learner walkthroughs | Plausible novice confusion and missing context | Apply three explicitly simulated profiles: a motivated adult with basic algebra; a programmer new to bra-ket notation; and a mathematically trained viewer new to CM conventions. What can each explain or predict at that point? |
| Visual cognition and accessibility reviewer | Attention, cognitive load, legibility and visual semantics | What competes for attention? Do highlights identify the exact terms used? Are labels, color, arrows, contrast, subtitles and matrix sizes usable? |
| Teacher / science storyteller | Motivation, examples, explanation and continuity | Does the learner know what question is being answered and why it matters? Is there a coherent problem-to-solution progression, rather than a list of formulas? |
| Video producer / editor / audio reviewer | Pacing, audiovisual timing, delivery and navigation | Do scene changes match narration? Is Brian perceptually consistent, intelligible and appropriately paced? Are pauses, captions, cuts and chapter joins effective? |
| Assessment designer / evaluation researcher | Evidence of learning and revision validation | Does the exercise require understanding or merely reading a visible answer? Is five seconds appropriate? Can learners transfer the idea to a different case? How could proposed changes be tested with people? |

The coordinating reviewer resolves overlap and disagreements. Mathematical
correctness cannot be outweighed by a majority preference for presentation.
Accessibility problems, learning barriers and cosmetic preferences should not
be conflated. Include effective teaching choices worth preserving.

## Method: inspect first, diagnose second, propose third

### 1. Establish coverage and independent first impressions

Inventory every target lesson, identify hashes, and build a chronological
scene/timestamp map. Record available capabilities for actual audio and video
inspection. Do not equate opening a player, decoding a file, reading a transcript
or viewing a poster frame with watching or listening to the lesson.

Make the first content/learner pass before reading prior author self-evaluations
and QA conclusions. Then consult existing teaching reviews, source/errata notes
and QA reports to reconcile differences. Prior approval and passing tests are
context, not a verdict. Do not repeat a prior critique as an independent finding.

### 2. Review every lesson and every authored teaching state

Read each complete script. Inspect every distinct teaching state, using compact
contact sheets for triage and full-resolution frames for equations, labels,
highlights and any suspected issue. Inspect frames from the actual encoded MP4
at important transitions and exercises, not solely source HTML or PNGs.

Review the temporal experience across each lesson: what becomes visible before,
during and after each spoken step, whether the viewer has time to compute or
read, and whether answers leak before a practice pause. Record exactly which
intervals were played, sampled or only inferred from timing metadata.

When audio perception is available, listen to each lesson, with closer checks at
opening sentences, formulas, edits, pauses and changes in emphasis. Compare
Brian across lessons, not just within one recording. Same voice ID/settings do
not prove perceptual consistency. If audio cannot be perceived, complete all
other review dimensions, mark listening coverage unavailable, and provide a
timestamped human listening checklist. Do not fabricate observations about
prosody, pronunciation or emotion from a transcript or waveform alone.

The phrase “full critique” describes the intended scope. If a review dimension
cannot be completed with the available tools, disclose the gap prominently and
identify the smallest follow-up needed. Do not silently substitute a script-only
critique for audiovisual review or leave unaffected lessons unreviewed.

### 3. Recheck mathematics and implementation independently

Explicitly audit:

- Paper true-first versus repository false-first order, including labels and
  index computations through every transition.
- Numeric CMs, expression-valued LMs, selectors, intermediate vectors and final
  scalars; defined symbols and complete numeric/bracketed representations.
- Boolean matrix multiplication (AND paired entries, XOR products), entrywise
  operations, outer products, tensors, complements and valuations.
- Matched versus unmatched LM measurement; constants versus formulas; the
  interpretation of page-17 factorization and page-12 projection corrections.
- Four-variable/tensor addressing and declared permutations; claims about
  independent bits, subexpressions, matrix dimensions and output size.
- Public API examples, structural versus semantic identity, lazy/materialized
  behavior, packed bit order, hypothetical versus measured costs, policy scope.

Use independent derivations or small exhaustive checks. Existing tests are useful
but cannot validate claims they do not cover. Distinguish a manuscript error,
a tutorial error, an ambiguity, and a deliberate notation convention. Quote the
relevant displayed expression and show a counterexample for an alleged false
identity. Do not infer a source is right because it is the paper, or wrong
because its notation differs from a preferred convention.

### 4. Audit learning progression and visual experience

For each lesson, identify its actual learning objective and prerequisites.
For the full series, build a concept dependency map and find premature concepts,
redundancy, missing bridges and discontinuities. Assess both a sequential learner
and a viewer arriving at an individual lesson from a search/link.

For the three simulated learner profiles, work forward with only what has been
taught so far. At selected checkpoints, predict an answer before reading the
provided explanation. Label resulting confusion as a **hypothesis about a
learner**, not observed student behavior or evidence of learning outcomes.

Review practical screen size, caption interference, density of symbolic lines,
whitespace, exact row/column highlighting, overloaded symbols, notation changes,
reading time and the relationship between narration and visible steps. Empty
space alone is not a defect; identify the missing explanation or useful visual
before recommending more content. Animation is not inherently better than a
clear static step. Prefer teaching value over decorative motion.

The short double implication arrow `⇒` (`\Implies` mapped to a short glyph) is
the established rule for new work. Foundation videos predate this latest rule;
Brian explicitly deferred their correction. Record legacy occurrences together
as a known deferred issue, without inflating severity or duplicating it across
many findings. XOR remains `⇕` / `\Updownarrow`; Impax uses centered overlapping
`⇔` and `⇕`. Do not recommend abandoning these user-required conventions.

### 5. Consolidate findings, then suggest bounded alternatives

For each finding provide:

- Stable ID, lesson/scene, exact local timestamp range, absolute media path,
  frame or script evidence, and affected learner profile(s).
- What the artifact actually does; what is wrong or uncertain; likely impact.
- Primary reviewing perspective, corroborating evidence, confidence and any
  disagreement or alternative interpretation.
- Priority: blocker (false central claim or unusable content), major (substantial
  learning barrier), moderate (local ambiguity/friction), or polish (preference).
- Proposed remedy, why it addresses the diagnosis, rough scope/effort, affected
  dependencies and whether narration regeneration would be needed.
- A concrete acceptance check, and whether it requires genuine learner testing
  or human listening rather than automated checks.

Deduplicate recurring issues: one series-level finding with occurrence references
is better than 23 copies. Do not manufacture a defect in every lesson or impose
an issue quota. Do not bury central mathematical faults inside averaged scores.

For the highest-value 3–5 findings, draft a small before/after narration example
and a corresponding visual/storyboard description. Label these **provisional
alternatives**, not approved corrections. Resolve correctness questions before
polishing a replacement. No production edits, new voice calls or rendering of
replacement videos in this stage.

## Required versioned review package

1. `README.md`: concise overall assessment, strongest teaching choices, principal
   risks, actual coverage limitations and links to the review artifacts.
2. `REVIEW_COVERAGE.csv`: all 23 lessons and combined copies, script/state coverage,
   actual video/audio intervals reviewed, methods, gaps and source hashes.
3. `LESSON_REVIEWS.md`: all 23 lessons, objective/prerequisites, evidence-based
   assessment through the relevant perspectives, preservation notes and finding IDs.
4. `FINDINGS.json` and `PRIORITIZED_FINDINGS.md`: one consistent issue register
   with the fields above, ordered by learner impact and correctness, not cosmetic
   convenience. Include verified positive findings without forced praise.
5. `CURRICULUM_REVIEW.md`: dependency map, audience paths, recommended grouping
   or sequencing changes, and tradeoffs. Existing numbering remains unchanged.
6. `PROVISIONAL_REVISION_OPTIONS.md`: bounded alternatives for top findings,
   recommended implementation batches, dependencies, and acceptance criteria.
7. `HUMAN_VALIDATION_PLAN.md`: a small practical protocol for real viewers,
   including prediction, explanation and transfer tasks, plus any outstanding
   listening review. No recruitment, messages or claimed study results.
8. `NEXT_IMPLEMENTATION_PROMPT.md`: a compact follow-on prompt grounded in the
   prioritized findings, preserving frozen versions and specifying which
   recommendations need Brian's selection. Preparing it does not authorize
   executing it or additional spending.

Keep evidence extracts and any local review scripts in the review package.
Use Markdown/CSV/JSON unless another format materially improves the review.
Do not create a ceremonial report per persona or a scripted panel debate.

## Economy and completion

Load the course inventory once, share one evidence ledger across the review
perspectives, and expand only disputed or difficult findings. Avoid rereading
full font-embedded manifests, duplicate combined-course content, or the entire
repository. Use current source evidence rather than inventing general pedagogical
authority. When an external research claim matters, verify it with an appropriate
primary source; distinguish that evidence from local editorial judgment.

Do not claim measured savings or cache hits. The focused new-task recommendation
is based on limiting production-history carryover and enabling a fresh review
pass, not on a guarantee about billing. A continuation in the existing task is
also valid if it can perform the same independent first pass.

Before finishing, ensure every target has a coverage row and review entry, that
timestamps and paths resolve, findings have evidence and acceptance criteria,
and production manifests remain unchanged. Review Git status/diff and attribute
only your own additive review files. Report gaps honestly rather than declaring
an audiovisual review complete from technical tests alone.

End with the recommended first revision batch or a justified recommendation to
preserve the course pending real learner evidence. Keep implementation separate
until the review is assessed. State whether follow-up should stay in the critique
task or return to the production task, and recommend an economical model/effort
for the concrete work then known.
