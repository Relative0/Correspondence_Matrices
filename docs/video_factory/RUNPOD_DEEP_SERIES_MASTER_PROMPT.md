# CM deep-series — one-shot development and RunPod production prompt

Date: 2026-08-31  
Status: ready to copy into this Codex task or a new Codex task with the same
workspace  
Default authorization: local authoring, implementation, validation, and
deterministic local previews only. This prompt does not itself authorize a
RunPod API call, pod creation, upload, paid service, publication, commit, or
push.

## Important execution distinction

The current CM RunPod package is a deterministic render worker. It accepts
immutable JSON jobs and produces hash-bound media; it does not understand a
prose prompt and it does not author scripts or storyboards.

This prompt therefore targets a coding/production agent with access to the CM
workspace. That agent may run on Brian's computer or inside a separately
authorized RunPod development environment. The recommended path is to author
and validate scripts, storyboards, and low-cost previews locally, then submit
only immutable production render jobs to RunPod. One agent invocation may
orchestrate the whole workflow, but the cloud step still requires a new exact
authorization block.

The prior `cm-video-proof3-cpu-remote-v1` through `v4` proposals are historical
proof records. Their permissions are consumed and must not be reused for this
series.

## Copy-paste prompt

```text
Act as the lead scientific editor, curriculum architect, scriptwriter, motion
designer, production engineer, and QA lead for the Correspondence Matrices
(CM) deep video series. Work autonomously through every authorized phase. Do
not stop after producing an outline: build complete scripts, scene contracts,
storyboards, deterministic visual assets, previews, render packages, and QA
records. Preserve unrelated work in every repository.

WORKSPACE

Evidence and editorial authority:
C:\Users\brian\Documents\CM_Computation

Production orchestrator:
C:\Users\brian\Documents\PoP\Tools\Master-Video-Creator

Scientific motion-graphics renderer:
C:\Users\brian\Documents\PoP\Tools\POP-Video-Creator

Auxiliary source-artifact renderer, only for deliberate document/page scenes:
C:\Users\brian\Documents\PoP\Tools\Artifact-To-Video

EXISTING BASELINE TO VERIFY

- `docs/video_factory/video_catalog.json` contains 45 candidates: 44 proposed
  concept episodes and one rendered long-form flagship.
- `docs/video_factory/source_registry.json`, `claim_registry.json`, and
  `glossary.json` are the evidence contracts. JSON is authoritative.
- `docs/video_factory/episodes/cm-flagship-representation-to-evidence-v1`
  contains the seven-chapter pilot contracts and release record.
- The local flagship is 420.021 seconds, 1920x1080 at 30 fps, H.264/yuv420p,
  AAC 48 kHz stereo, with 42 sentence-level captions and offline narration.
- Its recorded MP4 SHA-256 is
  `5765ddc9987360cd03956a83470606a07be67e536da127818623f20862452546`.
- Its recorded release identity is
  `cd453fe5a308d31e63fcc58b5c3c503aa90f8070a5f53c482641e4cbff9d32bf`.
- `docs/video_factory/runpod` is a disposable CPU-first renderer package. It
  does not contain an authoring agent and it must receive immutable jobs.
- The local flagship's visual and technical QA passed. Public-facing editorial
  listening approval remains a human decision.

Verify these facts from the files and hashes before relying on them. If the
source tree has legitimately changed, refresh derived identities rather than
reverting the source.

PRIMARY OBJECTIVE

Develop the 44 unproduced catalog concepts into a coherent, deep, evidence-
bound video curriculum. Produce one complete episode package for every concept
and ensure every important concept introduced in the flagship is taught in at
least one dedicated episode. The result must be substantially more explanatory
and visually informative than the pilot. It must replace under-filled card
slides with worked examples, diagrams, transformations, comparisons, and
progressive visual explanations wherever those devices improve understanding.

Do not manufacture length. Depth must come from definitions, mechanisms,
worked examples, boundary cases, evidence, limitations, and connections to
other concepts.

SERIES SCOPE — EXACTLY 44 REQUIRED EPISODES

Treat the 44 non-flagship entries in `video_catalog.json` as the minimum locked
coverage set. Preserve their stable `video_id` values. A concept may receive
additional companion episodes only when the first episode would otherwise
combine two genuinely independent lessons. Do not silently omit, merge away,
or rename an existing ID.

Track 1 — Foundations, 6 episodes

1. `why-boolean-computation` — Why Boolean computation matters
2. `expression-truth-function` — Expression, truth table, and Boolean function
3. `live-support-ambient` — Live support versus ambient variables
4. `what-is-explicit-cm` — What a correspondence matrix is
5. `what-cm-does-not-claim` — What CM does not claim to be
6. `explicit-cm-vs-cm-ir` — Explicit dense CM versus CM-IR

Track 2 — Representations, 8 episodes

7. `cm-ir-nodes-sharing` — CM-IR nodes, sharing, and roots
8. `canonicalization-interning` — Canonicalization, interning, and normalization
9. `eager-lazy` — Eager and lazy CM paths
10. `pair-aware` — Pair-aware CM collapse
11. `hybrid-partial` — Hybrid versus partial-hybrid materialization
12. `parallel-cm` — Parallel CM materialization
13. `packed-words-selection` — Packed bitsets, words, and width selection
14. `cm-ir-persistence` — CM-IR persistence and version identity

Track 3 — Comparators, 6 episodes

15. `raw-ast` — Raw AST evaluation as an ablation
16. `cse-plain-language` — Common subexpression elimination in plain language
17. `cse-vs-cse-flat` — Plain CSE versus sharing-aware CSE-flat
18. `cm-ir-vs-cse-flat-mechanism` — CM-IR versus CSE-flat: common ground and
    extra transformations
19. `instruction-operations-memory` — Instructions, primitive operations, and
    memory traffic
20. `no-fastest-chart` — Why one blended fastest-method chart is dishonest

Track 4 — Performance, 8 episodes

21. `measurement-boundaries` — Preparation, kernel, wrapper, and end-to-end time
22. `reuse-break-even` — Reuse and break-even economics
23. `b2b4-corrected` — Corrected B2/B4 V3 kernel result
24. `b2b4-runpod` — Three-pod B2/B4 replication
25. `epfl-parity` — EPFL AND/INV parity and its mechanism
26. `selector-width-limit` — Why width alone did not select the engine
27. `exact-comparison-protocol` — Truth digests, alternating schedules,
    clustering, and intervals
28. `correction-story` — How an audit changed the headline

Track 5 — Toolbox, 1 episode

29. `toolbox-map` — CM, CSE, BitSet, BDD, SAT, Espresso, and SymPy: different
    questions

Track 6 — Applications, 4 episodes

30. `configuration-models` — Configuration and feature-model workloads
31. `circuits` — Circuit workloads: structure, truth, and exact controls
32. `policy-rule-systems` — Policy and rule systems with related revisions
33. `representation-decision` — Which representation should I try?

Track 7 — Recognition, 7 episodes

34. `recognition-question` — What the CRSE recognition program asks
35. `recognition-c2` — C2 variable-size decomposition: exact control, learned
    failure
36. `recognition-c3-c5` — C3-C5 natural cuts: improvements without held-out
    promotion
37. `recognition-c6` — C6 packed exact source ANF: what advanced and what did
    not
38. `recognition-d-tasks` — Milestone D task routing: mixed boundaries
39. `recognition-d8` — D8 Linux confirmation: exact but unprofitable
40. `recognition-d9` — D9 abstention policy: safe, charged, not promoted

Track 8 — Evidence literacy, 4 episodes

41. `read-a-ratio` — How to read a CM/comparator ratio
42. `scope-boundaries` — Why scopes and boundaries matter
43. `conceptual-vs-measured` — Conceptual animation versus measured result
44. `source-hash-reproduction` — How a video is bound to source hashes

TARGET LENGTH AND TOTAL SCALE

Version the duration contracts instead of weakening or silently changing the
existing Level 2 schemas.

- Existing `visual_short` entries become focused explainers of 5-7 minutes.
- Existing `core_explainer` entries become core episodes of 8-12 minutes.
- Existing `deep_dive` entries become deep episodes of 14-20 minutes.
- Narration should normally average 115-135 spoken words per minute, leaving
  deliberate visual reading time.
- Expected script ranges are approximately 650-900 words, 1,000-1,550 words,
  and 1,800-2,600 words respectively.
- The 44-episode minimum therefore represents approximately 346-506 finished
  minutes, or 5 hours 46 minutes to 8 hours 26 minutes.

Length is a target band, not a quota. A complete six-minute lesson is better
than a padded ten-minute lesson. A deep episode may exceed twenty minutes only
when its chapter outline demonstrates a genuine additional teaching need.

NON-NEGOTIABLE OPERATING RULES

1. Read every applicable `AGENTS.md`, project instruction, README, schema, and
   current production report before editing its repository. Use each project's
   virtual environment and match surrounding conventions.
2. Begin read-only. Record root, branch/HEAD, relevant tool versions, and
   concise `git status --short` for each touched repository. Preserve all
   unrelated changes. Do not commit or push unless Brian separately asks.
3. Never read, print, copy, persist, hash, log, or bundle secrets. If an
   approved RunPod controller is later used, refer only to the existing
   `RUNPOD_API_KEY` environment variable; never expose its value.
4. No benchmark rerun is authorized by this prompt. Use retained evidence.
   If an episode needs unsupported data, use a visibly conceptual example or
   block the claim; do not invent a numeric result.
5. No paid voice, image, music, video, model, or review service is authorized
   by this prompt. Reuse the approved local/offline narration path or produce
   narration-ready masters and caption/audio contracts.
6. No upload, pod creation, remote execution, or cloud deletion is authorized
   until the exact authorization block described below is approved. Preparing
   a proposal and content-addressed bundle is allowed.
7. Never reuse a historical proof controller's consumed one-create allowance.
   A production series needs a new proposal ID, new authorization identity,
   new bundle hash, and new batch-manifest hash.
8. Every factual or numeric statement must resolve to an allowed claim and
   source locator. Keep fact, measurement, interpretation, hypothesis,
   conceptual example, revised result, negative result, and not-promoted
   status visually distinct.
9. Never collapse explicit dense CM, CM-IR, a benchmark evaluator arm, and a
   public wrapper into one object. Never collapse plain CSE and CSE-flat.
10. Keep preparation, construction, evaluator kernel, wrapper, extraction,
    persistence/reload, and end-to-end task time separate.
11. Ratios must show numerator, denominator, favorable direction, workload,
    boundary, and uncertainty. Never turn a scoped result into a universal
    winner claim.
12. Determinism is required: fixed seeds, frame-derived progress, half-open
    frame intervals, immutable normalized inputs, content-addressed caches,
    atomic results, and no wall-clock text in frames.
13. Reuse IVC and POP capabilities. Add versioned contracts or reusable scene
    primitives where needed; do not create a parallel one-off video system.
14. Generated media is a production candidate until automated QA, encoded-
    frame review, caption/audio QA, and human editorial review are complete.
    Do not publish anything.

CURRICULUM AND CONTINUITY CONTRACT

Create `docs/video_factory/deep_series/series_manifest.json` and a generated
Markdown twin. Include all 44 episode IDs, track order, prerequisites,
duration target, audience, learning objective, status, complexity, execution
route, and content hash.

Create two learning paths:

- General path: Foundations -> selected Representations -> CSE comparison ->
  measurement boundaries -> applications -> evidence literacy.
- Technical/research path: all Foundations -> all Representations -> all
  Comparators -> all Performance -> all Recognition -> source reproduction.

Use a small set of persistent examples so viewers can transfer understanding
between videos. At minimum define:

- one repeated-subexpression Boolean expression used across AST, CSE,
  CSE-flat, CM-IR, instruction, and memory scenes;
- one explicit small truth table and CM layout used across live-support,
  explicit-CM, packed-word, and exactness scenes;
- one configuration or feature-model example;
- one circuit example;
- one versioned policy/rule example;
- one tiny recognition/decomposition graph that remains visibly conceptual
  unless bound to retained measured evidence.

Give these examples stable IDs and place their validated definitions in
`docs/video_factory/deep_series/examples`. Never let the same stable example
silently change variables, semantics, or result between episodes.

EPISODE PACKAGE CONTRACT

For every episode create:

`docs/video_factory/deep_series/episodes/<video_id>/`

with at least:

- `episode.json`: versioned episode contract and hashes;
- `script.md`: complete human-readable narration, not an outline;
- `narration_contract.json`: sentence-level cue IDs, text, pronunciation,
  timing target, chapter, and caption identity;
- `caption_contract.json` and a generated `.vtt` preview;
- `storyboard.json`: every scene and visual beat with timing and assets;
- `visual_director.md`: episode-specific look, continuity, diagrams, motion,
  color semantics, and forbidden shortcuts;
- `claim_map.json`: every script sentence or scene that makes a claim, bound
  to claim IDs, source IDs, locators, type, status, scope, and boundary;
- `asset_manifest.json`: input and generated asset paths, licenses where
  applicable, sizes, hashes, and generating command/primitive;
- chapter contracts and renderer briefs;
- `production_plan.json`: local/RunPod route, resource estimate, retry class,
  cache identities, and expected outputs;
- a low-cost storyboard contact sheet or animatic;
- after rendering, `release_manifest.json`, QA report, review contact sheet,
  and a human review checklist.

All authoritative JSON must have strict schemas and reject unknown fields
where practical. Markdown, scripts, and contact sheets are review surfaces;
they do not override JSON evidence contracts.

SCRIPT CONTRACT

Every complete script must contain these teaching functions in a natural
order, with headings in `script.md` even if the headings are not narrated:

1. Hook: a concrete problem, surprising distinction, or decision the viewer
   can recognize.
2. Promise and prerequisites: what will be clear by the end and what earlier
   episode supplies necessary background.
3. Plain definition before acronyms and implementation detail.
4. A concrete worked example that changes state on screen while narrated.
5. Mechanism: show how the representation or operation works, not merely what
   it is named.
6. Contrast: compare the nearest confusing concept on the same example.
7. Boundary or limitation: what the lesson does not establish.
8. Evidence panel when retained evidence exists, or an explicit conceptual
   label when it does not.
9. Retrieval check: ask the viewer to predict, classify, or explain one state
   before revealing the answer.
10. Recap and bridge: return to the opening problem and point to the next
    useful episode without pretending there is one universal best method.

Additional script rules:

- Define CM, CM-IR, CSE, CSE-flat, AST, ANF, BDD, SAT, and other acronyms on
  first use within any episode intended to stand alone.
- Use short spoken sentences around dense diagrams. Do not narrate a wall of
  text.
- Put essential meaning in narration and captions, not only in color.
- Include pronunciation overrides for technical tokens and abbreviations.
- Use matched wording for matched comparisons. Do not use celebratory language
  for a mixed, negative, or not-promoted scientific result.
- Run three documented editorial passes: conceptual completeness,
  script-to-visual alignment, and evidence/claim audit.
- A script is not `validated` if any planned scene says only "show boxes" or
  "add diagram later." Every scene must identify the actual entities, state
  transition, visual primitive, narration cue, and evidence type.

VISUAL DIRECTION — SERIES-WIDE

The desired look is precise scientific motion design: dark neutral field,
bright but restrained method colors, high-contrast typography, diagram-first
composition, stable visual identities, and visible evidence status. It should
feel like an animated technical notebook or laboratory instrument, not a deck
of corporate cards.

Keep the flagship's useful language—chapter identity, claim/source footers,
boundary badges, ratios, DAGs, matrices—but increase the explanatory density
and the amount of meaningful motion.

Use one series-wide semantic system:

- CM, explicit CM, CM-IR, AST, CSE, CSE-flat, BitSet/packed execution, BDD,
  SAT, and recognition components retain stable colors and shapes.
- Facts/confirmed measurements, conceptual illustrations, hypotheses, revised
  results, mixed/negative outcomes, and not-promoted outcomes retain distinct
  badges and textures.
- Preparation, kernel, wrapper, persistence, and end-to-end boundaries retain
  distinct labeled bands.
- Use position, labels, shape, and texture in addition to color. Meet readable
  contrast and color-blind-safe requirements.

THE THREE-BOX RULE

A row of three passive boxes is not an explanation. It is allowed only when
all of the following are true:

- each box names a specific entity or state and contains information needed
  for the lesson;
- arrows, shared elements, transformed values, or aligned axes show the
  relationship between the boxes;
- the scene changes progressively—input, transformation, consequence—rather
  than appearing as three labels at once;
- narration refers to visible changes, not merely reads the box titles;
- the scene settles long enough to inspect the result;
- a worked example, diagram, trace, table, or measured panel supplies the
  concrete meaning.

Never hold three generic cards in a single row for more than eight seconds.
If a relationship can be shown as a graph, matrix, pipeline, timeline,
transformation, split-screen trace, or small multiple, use that device.

VISUAL DENSITY AND PACING GATES

- The settled teaching content should normally occupy roughly 55-85 percent
  of the safe content area. Empty space is acceptable when it deliberately
  isolates one object or creates a before/after reveal; it is not acceptable
  as a default layout.
- Use one primary focal element and no more than two secondary focal groups at
  a time. More filled space must not mean clutter.
- Introduce a meaningful visual beat every 3-8 seconds and a new visual state
  or camera/composition relationship every 8-20 seconds.
- Do not hold a static full-frame slide longer than 20 seconds. A longer scene
  must evolve through highlights, construction, evaluation, comparison, or
  annotation.
- Use concise on-frame labels. Paragraphs belong in narration/captions, not in
  boxes.
- Every abstract episode needs at least one worked example, one mechanism
  diagram, one comparison or boundary view, and one recap map.
- Core episodes need at least two distinct explanatory visual systems. Deep
  episodes need at least three, two worked examples or one example plus a
  measured case study, and a chapter-level visual roadmap.
- Show equations, expressions, tables, graphs, and benchmark points by
  progressive construction. Do not reveal a dense finished diagram and then
  talk over it.
- Keep claim/source footers readable without making them the visual subject.
  Provide full source detail in sidecars and concise IDs in-frame.
- Design 16:9 masters first. Create 9:16 derivatives only after an explicit
  scene-safe reflow contract; do not crop the center of a dense 16:9 diagram.

REQUIRED REUSABLE VISUAL PRIMITIVES

Implement or extend versioned, data-driven primitives rather than one-off
episode code. The library must support at least:

- Boolean expression construction and animated evaluation;
- truth-table row construction and output reveal;
- live-support highlighting against ambient variables;
- variable partitioning and explicit CM layout/indexing;
- CM dense-size growth and materialization cost illustration;
- AST repeated-subtree highlighting;
- structural hashing, CSE interning, shared DAG construction, and root reuse;
- eligible associative-chain flattening for CSE-flat;
- CM-IR canonicalization, normalization, node merging, roots, and persistence;
- eager, lazy, pair-aware, hybrid, partial-hybrid, and parallel execution
  timelines limited to their retained implemented/formal status;
- packed word/bitset layout, word width, tail handling, and selector decisions;
- synchronized AST/CSE/CSE-flat/CM-IR traces on the same expression;
- preparation -> artifact -> repeated kernel -> wrapper -> extraction ->
  persistence -> end-to-end boundary pipeline;
- instruction, primitive-operation, allocation, and memory-traffic counters
  linked to the visual computation;
- one-time versus per-use cost and break-even/reuse animation;
- ratio plot with numerator/denominator, favorable direction, scope, boundary,
  workload, confidence interval, and parity line;
- exact comparison protocol: truth digest, alternating schedule, machine/run
  clusters, interval, and reconciliation;
- audit/supersession timeline showing an earlier headline, discovered defect,
  corrected artifact, retained old scope, and new wording;
- toolbox decision map that distinguishes representation, simplification,
  satisfiability, enumeration, symbolic manipulation, and repeated evaluation;
- configuration/feature graph, circuit graph, and versioned policy/rule graph;
- recognition/decomposition graph with train/validation/test separation and
  visible promotion/no-promotion decisions;
- source -> locator -> claim -> script cue -> scene -> render -> release hash
  provenance chain.

TRACK-SPECIFIC VISUAL REQUIREMENTS

Foundations

- Begin with real Boolean decisions, then move expression -> assignments ->
  function -> representation.
- Use a small truth table viewers can follow row by row.
- Make live support visible by fading ambient variables that cannot affect the
  output, then show the storage/work implication without claiming a benchmark.
- Build an explicit CM from partitions and indices; do not introduce it as a
  labeled rectangle.
- Show CM's non-claims through matched counterexamples, not a disclaimer wall.
- End explicit CM versus CM-IR with two visibly different artifacts, costs,
  and suitable questions.

Representations

- Construct CM-IR nodes from an expression, intern a repeated node, and retain
  multiple roots.
- Show canonicalization, interning, and normalization as separate operations;
  never animate them as synonyms.
- Compare eager/lazy, pair-aware, hybrid/partial, and parallel paths with the
  same input and clearly label whether a step is implemented, formal,
  experimental, or conceptual.
- Animate packed words at the bit, word, and workload levels; make width and
  live support separate variables.
- For persistence, show source identity, canonical artifact identity,
  serialization, reload verification, and version delta.

Comparators

- Use one stable repeated-subexpression example across raw AST, plain CSE,
  CSE-flat, and CM-IR.
- Show exactly which nodes are reused, which associative chain is flattened,
  and which additional CM-IR normalization or merging is present.
- Couple operation/instruction/memory counters to the evolving graph so the
  viewer can see where counts change.
- The no-fastest-chart episode must show why boundary/workload panels cannot
  be collapsed into one rank without losing meaning.

Performance

- Use the same boundary pipeline in every episode.
- Break-even must show a one-time preparation line, repeated-use slope, and
  crossing or non-crossing condition.
- Corrected B2/B4, three-pod replication, and EPFL parity must use only
  machine-extracted values, show their distinct scope, and avoid pooled
  universal conclusions.
- Selector-width must show width as one feature among structural/reuse/cost
  signals, not as a failed universal law.
- Exact comparison protocol must animate why digest checking, alternation,
  clustering, and intervals answer different validity threats.
- Correction story must preserve the accepted older scoped result while
  showing why the broader headline changed.

Toolbox and applications

- Organize tools by the question they answer, not by a winner podium.
- Every application episode starts with a concrete task and maps it to
  representation, operation, repeated-use pattern, evidence boundary, and
  limitation.
- The representation-decision episode must be an interactive-looking decision
  flow whose branches are explicit questions; it may not be a static matrix of
  vague pros and cons.

Recognition

- State the frozen experimental question, exact control, data split,
  comparator, result, limitation, and promotion decision for every milestone.
- Separate engineering success from scientific generalization.
- Negative, mixed, and not-promoted results receive the same visual care as
  favorable results. Avoid green completion language when a milestone did not
  promote.
- Preserve the sequence from recognition question through C2, C3-C5, C6,
  milestone D, D8, and D9 so each episode is standalone but the program remains
  legible as one falsifiable research arc.

Evidence literacy

- Teach ratio direction with two numerical toy examples before any retained
  project ratio.
- Let the viewer move a boundary marker and see how the claim wording must
  change.
- Use unmistakably different styling for conceptual animation and measured
  data, then include a classification retrieval check.
- Build the full source-hash provenance chain and demonstrate how a changed
  source invalidates a downstream brief/job without implying that Git hashes
  alone establish scientific truth.

AUTHORING AND PRODUCTION PHASES

Phase 0 — Inspect and freeze the working baseline

- Read project instructions and production reports.
- Record repository states without modifying unrelated files.
- Validate current source/claim/glossary/catalog schemas and hashes.
- Inventory existing renderer primitives, episode/chapter/audio contracts,
  cache behavior, RunPod bundle limits, and known pilot QA findings.
- Write `deep_series/BASELINE.md` with verified facts and detected changes.

Phase 1 — Version the contracts

- Add versioned series, episode, script, storyboard, visual-director,
  asset-manifest, production-plan, and coverage schemas as needed.
- Preserve Level 1 proofs and the Level 2 flagship. Do not mutate their locked
  release identity.
- Extend duration support through a new schema version or tier contract.
- Add fixtures and tests for missing scripts, empty scenes, generic-box
  placeholders, unsupported claims, missing source locators, stale hashes,
  invalid prerequisite cycles, duration/word mismatch, missing visual beats,
  and illegal execution routes.

Phase 2 — Build the coverage and learning plan

- Convert all 44 catalog entries to the deep-series manifest.
- Create a concept-to-episode coverage matrix. Every important term, mechanism,
  evidence result, limitation, and research milestone in the flagship must map
  to one or more dedicated episodes and script sections.
- Resolve prerequisites and detect cycles.
- Define persistent examples and track-level continuity.
- Generate a proposed release order, but do not equate order with approval.

Phase 3 — Write all 44 complete scripts

- Author the full spoken script for every episode within its target tier.
- Create sentence-level narration and caption cues while authoring; do not
  bolt captions on after rendering.
- Bind every factual sentence to the claim map.
- Perform the three editorial passes and retain a compact pass report.
- Generate a series-wide terminology and pronunciation consistency report.
- Block only the affected sentence/scene when evidence is insufficient; do not
  invent support or discard an otherwise valid episode.

Phase 4 — Direct and storyboard every episode

- Turn every script into chapters, scenes, and 3-8-second visual beats.
- Specify actual diagrams, examples, entities, state changes, data, captions,
  and transitions. Ban placeholder direction.
- Reuse primitives and persistent examples. Add a reusable primitive only
  when two or more scenes need it or the concept cannot be taught accurately
  with the current library.
- Compute pacing, text density, safe-zone, and estimated render complexity.
- Produce contact-sheet storyboards before production render.

Phase 5 — Implement missing reusable visuals

- Extend POP's data-driven CM subject and IVC adapter in small, tested changes.
- Keep scientific values outside renderer source code; load validated extracts.
- Add fast low-resolution fixtures for every new primitive.
- Run existing focused tests plus new schema, semantic, primitive, adapter,
  cache, Windows-path, Linux-path, and failure tests.

Phase 6 — Local preview gate for all episodes

- Generate a low-cost storyboard contact sheet for every episode.
- Generate low-resolution animatics where motion/timing is essential to review.
- Run automated checks for missing scenes/assets, unsupported claims, generic
  three-box layouts, excessive empty area, text overflow, clipping, safe zones,
  caption identity, duration, and visual-beat cadence.
- Render one representative full-resolution chapter for each distinct visual
  archetype before broad final rendering.
- Fix systemic problems in the primitive/library, then regenerate affected
  episodes by content hash rather than applying 44 manual patches.

Phase 7 — Route work locally or to RunPod

Use this default routing unless measurement justifies a change:

- schemas, source/claim checks, scripts, storyboards, diagrams, contact sheets,
  and batch planning: local;
- low-resolution animatics: local;
- full 1080p low-complexity/focused episodes: local when a timed sample predicts
  completion within a reasonable unattended window;
- full 1080p medium/high-complexity episodes: disposable RunPod CPU worker after
  exact authorization;
- generative image/video or GPU work: disabled unless separately proposed and
  approved with model, license, inputs, outputs, and cost;
- Windows SAPI narration and audio mastering: local;
- final mux, encoded-media observation, and human review packet: local.

The remote worker receives scripts only as immutable inputs to already-resolved
render jobs. It must not be trusted to reinterpret the editorial plan.

Phase 8 — Prepare one content-addressed production batch

- Normalize every validated episode, chapter, renderer brief, asset, caption,
  and narration contract.
- Package only allowlisted inputs required by the Linux worker.
- Exclude credentials, `.env*`, caches, local audio credentials, unrelated CM
  research corpora, historical run logs not needed for rendering, and generated
  output media.
- Build immutable `render_job` entries and a resumable batch manifest.
- A single orchestration invocation may process the entire series, but each
  chapter remains independently cached, verified, retryable, and failure-
  isolated.
- Time representative local renders and compute a conservative CPU-hour,
  output-size, transport-size, and cost estimate. Do not claim all 44 finals
  fit an old proof budget.
- If one pod cannot safely complete within the authorized timeout, propose
  explicit hash-bound waves. "Single shot" means one orchestrated, resumable
  production command—not one fragile uncheckpointed process.

RUNPOD AUTHORIZATION GATE

Remote execution remains disabled until Brian approves an exact block with all
of these fields:

- proposal ID, for example `cm-video-deep-series-production-v1`;
- exact job count and ordered video/chapter IDs;
- bundle SHA-256 and batch-manifest SHA-256;
- exact image/digest, CPU flavor, vCPU, RAM, disk, volume, region/cloud type;
- current quoted hourly rate and quote time/source;
- maximum total RunPod spend in USD;
- maximum pod creates and maximum parallel pods;
- timeout, per-job timeout, retry count, and no-progress watchdog;
- transport/upload/download effects;
- expected outputs and local verification;
- delete-on-terminal behavior and owned-inventory reconciliation;
- whether any other paid service is involved, default `none`.

Do not infer authorization from this prompt, the prior $5 proof allowance,
possession of `RUNPOD_API_KEY`, or a historical v1-v4 approval. Stop and ask for
one exact approval if no current matching block exists. A changed bundle,
manifest, resource, job list, cost cap, create count, or cleanup behavior
invalidates approval.

Phase 9 — Execute only an exactly approved batch

- Re-run source, claim, schema, bundle, batch, price, and test gates.
- Use only the approved create count and resource shape.
- Upload only the allowlisted hash-bound bundle.
- Run bounded concurrency. Prefer two Chromium workers initially because the
  flagship's four-worker run produced a timeout; increase only after a measured
  stable sample and within approved resources.
- Cache and verify each completed chapter. Retry only failed unfinished
  hash-identical jobs within the approved retry/cost ceiling.
- Stop on a changed input, hash mismatch, missing progress, resource mismatch,
  cost ceiling, timeout, or unverified output.
- Download and verify all results before deleting the owned pod.
- Delete only the owned resource and reconcile final owned inventory.

Phase 10 — Local audio, assembly, and release-candidate QA

- Synthesize narration locally through the existing offline provider unless
  Brian approves a different exact voice plan.
- Fit cues to planned windows without time-compressing speech into
  unintelligibility. Prefer revising timing or script.
- Mux chapter audio/captions, then concatenate only passing chapters.
- Validate 1920x1080, 30 fps, H.264/yuv420p, AAC 48 kHz stereo, duration,
  decodability, cue count/identity, output hashes, and manifest hashes.
- Inspect encoded—not merely source—opening, early explanation, worked
  example, dense diagram, evidence panel, boundary panel, recap, and final
  frames for every episode.
- Produce per-episode and series contact sheets plus a human listening/editorial
  checklist.
- Mark outputs `production_candidate`, not `published` or `editorially_approved`.

AUTOMATED ACCEPTANCE GATES

The series is not complete unless:

- all 44 required IDs have a complete script, claim map, storyboard, visual
  director, contracts, assets, production plan, and review surface;
- every important flagship concept maps to a dedicated episode section;
- all prerequisites resolve and the graph is acyclic;
- every factual/numeric script statement resolves to an allowed claim/source
  locator and current source hash;
- superseded claims appear only in visibly marked correction/history contexts;
- all retained numeric chart values are programmatically extracted;
- no scene retains an unresolved placeholder;
- no passive three-box row violates the three-box rule;
- every abstract concept has a worked example and mechanism diagram;
- target word count, cue timing, scene duration, and visual beats agree within
  declared tolerances;
- text fits, safe zones pass, critical meaning is not color-only, and settled
  diagrams are readable at 1080p;
- all new renderer and orchestration tests pass without regressing focused
  existing tests;
- every final render has verified stream properties, captions, hashes,
  provenance, and decoded-frame review;
- remote jobs, if any, remain within their exact authorization and final owned
  RunPod inventory is empty;
- no output is published, no paid non-RunPod service is called, and no secret
  enters a file, log, manifest, command, or response;
- final `git status --short` and `git diff --stat` are reviewed separately for
  each repository, without attributing unrelated changes to this task.

FAILURE AND RESUME POLICY

- Persist a content-addressed phase ledger and per-episode status.
- A failure in one episode must not invalidate completed hash-identical work in
  another.
- Retry only deterministic infrastructure failures within the authorized
  limit. Do not retry failed evidence or schema gates until inputs are fixed.
- Resume from the first incomplete phase/episode/chapter after verifying every
  cache identity.
- Report affected episode IDs, exact gate, and safe next action. Never hide a
  missing episode by reducing the denominator.

EXPECTED DELIVERABLES

1. Verified baseline and deep-series architecture note.
2. Versioned deep-series schemas and tests.
3. 44-episode series manifest, prerequisite graph, learning paths, and
   flagship concept-coverage matrix.
4. Complete scripts, narration/caption contracts, claim maps, storyboards,
   visual direction, assets, and production plans for all 44 episodes.
5. Reusable visual primitives and tested IVC/POP integration required by those
   episodes.
6. Storyboard contact sheets and selected animatics/full-resolution archetype
   proofs.
7. Content-addressed local/RunPod routing plan and immutable production batch.
8. If and only if exactly authorized, verified final render results with full
   RunPod lifecycle and observed-cost records.
9. Local audio/assembly outputs, per-episode release manifests, encoded-media
   QA, and human review packets.
10. A final series production report listing complete, blocked, failed, and
    human-review-required episodes; output paths/hashes; tests; remote cost and
    cleanup; and the single next decision.

PROGRESS AND HANDOFF STYLE

Lead updates with concrete completed artifacts and counts. Keep working while
safe in-scope work remains. Do not ask Brian to choose matters already fixed by
the catalog, evidence contracts, or this prompt. Ask only when a decision would
change scientific wording, voice/publication, exact paid execution, resource
creation, or another material external effect.
```

## Recommended use

Use this prompt in the current task first. The current task already knows the
factory state, the pilot's weaknesses, and the consumed proof authorizations.
A new task is useful only for isolating the long multi-episode implementation
from unrelated conversation; if used, paste the entire prompt and root it at
`C:\Users\brian\Documents\CM_Computation`.

The next implementation pass should complete the 44 scripts and storyboards
before proposing a broad paid render. This makes the RunPod workload immutable,
reviewable, resumable, and costable instead of asking a render worker to invent
the curriculum while the meter is running.
