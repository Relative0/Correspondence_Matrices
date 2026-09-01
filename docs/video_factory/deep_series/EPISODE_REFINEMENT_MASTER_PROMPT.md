# CM deep-series episode refinement — reusable expert-panel master prompt

Date: 2026-09-01  
Purpose: refine one existing episode at a time before scaling changes across the series  
Default authorization: read-only audit and local authoring only

This prompt does **not** authorize RunPod, another remote service, paid voice or
media generation, publication, commit, push, or mutation of an approved release.

## Copy-paste prompt

```text
Act as the lead editor and production engineer for one episode of the CM deep
video series. Work in the existing Codex task rooted at:

C:\Users\brian\Documents\CM_Computation

EPISODE PARAMETERS

- VIDEO_ID: <video-id>
- CURRENT_EPISODE_DIR:
  docs/video_factory/deep_series/episodes/<video-id>
- REVISION_ID: v2
- REVISION_DIR:
  docs/video_factory/deep_series/episodes/<video-id>/revision_v2
- TARGET_AUDIENCE: curious advanced students; do not assume repository knowledge

PROJECT CONTEXT

The repository implements and studies Correspondence Matrices (CM), explicit
dense CM outputs, CM-IR, Boolean expression evaluation, packed truth-vector
execution, CSE/CSE-flat and related lowering, evidence boundaries, and CRSE
recognition research. Different artifacts and measurement boundaries must never
be collapsed. CRSE is a project label and must not receive an invented
expansion.

The current deep-series factory authored 51 episode packages and produced the
first five candidates. The first-five RunPod production is complete and its pod
was deleted. The current masters passed technical QA but human review found
semantic repetition, recycled imagery, long silent cue tails, and mechanical
offline SAPI delivery. Treat technical QA and editorial quality as separate
gates.

AUTHORITATIVE PROJECT ARTIFACTS

Read and validate, in this order:

1. docs/video_factory/deep_series/EPISODE_CONTENT_BIBLE.md
2. docs/video_factory/deep_series/episode_content_bible.json
3. docs/video_factory/claim_registry.json
4. docs/video_factory/source_registry.json
5. docs/video_factory/glossary.json
6. docs/video_factory/deep_series/coverage_matrix.json
7. the target episode's episode.json, script.md, narration_contract.json,
   storyboard.json, visual_director.md, claim_map.json, editorial_audit.json,
   chapter contracts, final release_manifest.json, MP4, captions, audio, and
   contact sheets
8. docs/video_factory/deep_series/FIRST_FIVE_RELEASE_REPORT.md when the target
   is one of the first five
9. docs/video_factory/RUNPOD_DEEP_SERIES_MASTER_PROMPT_V2.md for historical
   architecture and safety rules, not as an editorial-quality authority

For VIDEO_ID=what-is-explicit-cm, also read:

- docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/PANEL_AUDIT.md
- docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/SCRIPT_V2.md
- docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v2/VISUAL_AND_PRODUCTION_SPEC_V2.md

Do not read or expose secrets. If a later, separately authorized RunPod
controller is used, it may reference only the existing RUNPOD_API_KEY
environment variable. Never print, copy, persist, hash, log, bundle, or transmit
the key except through the already-designed authenticated API mechanism.

PRIMARY OBJECTIVE

Rebuild one episode into a concise, engaging, accurate lesson. Use its duration
to serve its teaching need; do not pad to a tier quota. Preserve the approved
release and create a versioned revision package. Do not generalize changes to
the other 50 episodes until this pilot receives human approval.

EXPERT PANEL

Perform independent reviews from at least these roles, then reconcile them:

1. A senior educational-video director/editor: hook, visual story, pacing,
   pattern interrupts, composition, and attention.
2. A learning-science expert: prior knowledge, cognitive load, coherence,
   signaling, worked examples, retrieval, misconception repair, and 24-hour
   retention.
3. A repository-grounded domain expert: definitions, ordered bases, examples,
   claim wording, source bindings, scope, and neighboring-episode ownership.
4. A production/QA engineer: deterministic rendering, media contracts,
   caption/audio behavior, visual validation, and versioned outputs.

Do not decide truth by vote. When panel findings conflict, compute the example
or inspect the authoritative source and record the resolution.

EDITORIAL METHOD

1. Inventory the current master. Measure runtime, words, spoken cues, actual
   speech versus silent tails, visual primitive frequency, semantic phrase
   repetition, baked text load, and distinct instructional functions.
2. Watch or sample the encoded MP4 and audio; do not rely only on JSON claims of
   quality. Inspect the beginning, every transition, every retrieval pause, and
   the ending.
3. Partition the content into KEEP, CUT, COMBINE, MOVE TO ANOTHER EPISODE,
   CORRECT, and ADD. Protect source-bound facts while removing learner-irrelevant
   audit prose.
4. Write a natural script around one causal or problem-solving arc. Prefer a
   continuous worked object over a parade of cards. Use conversational prose,
   varied sentence lengths, direct questions, and paragraph-sized thought
   units.
5. Write a visual specification in which every scene has an instructional
   function: orient, construct, demonstrate, predict, reveal, contrast,
   retrieve, or transfer. Cosmetic changes do not count.
6. Keep full captions optional. Do not display complete narration sentences in
   the central composition or a permanent lower rail.
7. Propose claim-registry deltas separately. Do not mutate the shared registry
   or approved Bible before human content approval.
8. Generate only lightweight local review surfaces before approval: script,
   shot list, claim delta, voice audition plan, and optionally a low-resolution
   silent animatic if local use remains moderate.

ANTI-MECHANICAL RULES

Reject or rewrite learner-facing phrases such as:

- “this episode has one job”;
- “watch for the label”;
- “now isolate”;
- “matched before-and-after view”;
- “not a substituted workload”;
- “holding that element fixed lets this episode”;
- “the invariant is”;
- “the accompanying view makes this step concrete”;
- “read that statement only within this scope”;
- “the measurement boundary is”;
- “the uncertainty field says”;
- “the nearest confusing lesson” and “this episode owns.”

Do not use word-count, composition-count, or state-change minimums as content
generators. They may be upper-bound diagnostics, not reasons to add narration or
motion. Add a semantic-near-duplicate audit; exact duplicate detection is
insufficient.

VOICE AND SOUND

- Final narration must sound human, conversational, and appropriately engaged.
- Synthesize paragraphs or coherent thought units, not one clip per sentence.
- Use 135–150 WPM as an initial technical-explainer range, then adjust from an
  audition rather than forcing every cue into a preallocated window.
- Pauses longer than 1.5 seconds require a prediction, inspection, or deliberate
  transition.
- Microsoft Mark/Windows SAPI is scratch timing audio only, never the release
  voice.
- Produce two or more 20–30 second voice auditions from the same passage and
  require human selection before final synthesis.
- Use restrained effects only when they clarify an action. Do not use decorative
  music or sound to mask weak pacing.

QUALITY GATES

The revision cannot become a production candidate until all are true:

- all factual wording resolves to allowed claims or an explicitly proposed,
  source-bound claim delta;
- every numeric worked example is independently recomputed;
- the first 30 seconds visually fulfill the title and learner promise;
- no neighboring episode's owned lesson becomes a digression;
- every repeated visual has a new instructional function;
- central onscreen text is limited to labels, formulas, coordinates, and short
  prompts;
- at least one worked example, one faded-completion example, one retrieval
  pause, and one transfer are present when the lesson supports them;
- contact sheets are sampled by instructional function as well as time;
- encoded audio/video/captions pass the existing technical contracts;
- at least one full human watch/listen pass approves accuracy, pacing, voice,
  legibility, and attention;
- the old release remains intact and the new output is versioned.

DELIVERABLES

Write to REVISION_DIR:

- PANEL_AUDIT.md
- SCRIPT_V2.md
- VISUAL_AND_PRODUCTION_SPEC_V2.md
- CLAIM_REGISTRY_DELTA_V2.json
- STORYBOARD_V2.json only after the prose script and visual spec are coherent
- REVIEW_MANIFEST_V2.json containing hashes and validation results
- a low-resolution animatic and review contact sheet only after content review

Also produce a concise change list for any shared factory improvements, but do
not implement or propagate them until this episode is approved as the pilot.

EXECUTION AND COST BOUNDARY

Begin read-only. Preserve unrelated dirty work. Do not commit or push. Do not
publish. Do not call RunPod or any paid/remote service under an old or consumed
authorization. If full production would exceed moderate local use, stop after
the approved local review package and prepare a new immutable, cost-bounded
RunPod proposal that names the exact revision hashes, renderer inputs, maximum
spend, retry count, cleanup behavior, and expected outputs. Execute only after
the user approves that exact proposal.

SUCCESS CONDITION

The work is successful when a learner can state the episode's essential idea,
perform its central operation on a fresh example, avoid its primary
misconception, and explain its boundary—without hearing production metadata or
seeing recycled filler imagery.
```
