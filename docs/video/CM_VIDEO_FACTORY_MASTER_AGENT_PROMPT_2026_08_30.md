# CM video factory — master build, catalog, and RunPod production prompt

Date: 2026-08-30  
Status: ready to copy into a new Codex task  
Default authorization: local inspection, design, implementation, tests, and
small deterministic local proof renders only. No paid API, upload, pod
creation, remote execution, publication, commit, or push is authorized by this
prompt.

## Recommended architecture

Use the existing tools as a layered system instead of making an unrelated
video program:

1. **CM_Computation is the evidence authority.** It owns claim status, source
   hashes, benchmark data, terminology, caveats, and the editorial catalog.
2. **POP-Video-Creator is the scientific motion-graphics renderer.** Extend it
   with one data-driven CM subject and reusable scene primitives. The existing
   `crse_neural` subject is a useful first implementation, not the full CM
   renderer.
3. **Master-Video-Creator (IVC) is the production orchestrator.** It should own
   briefs, assembly, formats, caches, provenance, gap reports, encoded-media
   observations, and review. Add or extend a generator adapter rather than
   duplicating those systems.
4. **Artifact-To-Video is an auxiliary source-walkthrough renderer.** Use it
   when a video genuinely needs to pan through an existing webpage or PDF. It
   is not the main scientific explainer engine.
5. **RunPod is an eventual disposable render worker, not the source of truth.**
   First make the pipeline portable and prove it locally. Then prepare a
   content-addressed, resumable Linux bundle. Create a pod only after Brian
   approves the exact batch, resource, creation count, cost ceiling, transport,
   and cleanup effect.

The first remote lane should normally be CPU rendering. Chromium, SVG/canvas,
and FFmpeg do not inherently require a GPU. A GPU lane is justified only by a
separately approved generative-image/video model or measured CPU bottleneck.

## Copy-paste prompt

```text
Act as the lead engineer, scientific evidence editor, and production designer
for a reusable Correspondence Matrices (CM) video factory. Work autonomously
through the authorized local stages below. Build working machinery and local
proofs; do not stop at a speculative design. Preserve all unrelated work.

PROJECTS

Evidence repository:
C:\Users\brian\Documents\CM_Computation

Preferred production orchestrator:
C:\Users\brian\Documents\PoP\Tools\Master-Video-Creator

Preferred scientific renderer:
C:\Users\brian\Documents\PoP\Tools\POP-Video-Creator

Auxiliary source-artifact renderer:
C:\Users\brian\Documents\PoP\Tools\Artifact-To-Video

Other tools to inspect only if the preferred stack cannot meet a documented
requirement:
C:\Users\brian\Documents\PoP\Tools

PRIMARY OBJECTIVE

Build a reusable, evidence-bound program that can turn a catalog of CM video
briefs into high-quality explainer videos. It must cover foundational concepts,
representations and variants (including explicit CM and CM-IR), comparisons
such as CM versus CSE and CSE-flat, the proposed mechanisms behind observed
differences, boundary costs, benchmarks, applications, limits, corrections,
and the experimental CRSE/recognition program. After the machinery is proven,
produce a deep candidate-video catalog and a production plan. Prepare a safe,
portable RunPod render bundle, but do not upload it or create a pod without a
new exact authorization.

This is a two-level project:

- Level 1, this task: build and validate the video factory; generate the
  machine-readable evidence registry and candidate catalog; render a small
  local proof set; prepare a dry-run RunPod plan.
- Level 2, after Brian reviews the machinery: perform a separate deep editorial
  selection pass, lock scripts and visuals for an approved batch, and render
  that exact batch locally or on RunPod.

NON-NEGOTIABLE OPERATING RULES

1. Read every applicable AGENTS.md, CLAUDE.md, README, design document, and
   project-specific instruction before editing its project. Project rules
   override this prompt on conflict. Use each project's own virtualenv.
2. Begin read-only. Record each project root, current branch/HEAD when
   available, virtualenv interpreter, relevant tool versions, and concise
   `git status --short`. Never revert, overwrite, stage, commit, push, or
   reformat unrelated work. The repositories may already be very dirty.
3. Do not read, print, copy, hash, edit, or commit `.env*`, credentials, token
   caches, private keys, or local databases. Never place a secret in a render
   bundle, log, command line, manifest, or chat response.
4. No benchmark reruns are authorized. Reuse retained evidence. If a necessary
   chart cannot be supported from retained machine-readable evidence, label it
   unavailable or conceptual; do not manufacture data and do not start a new
   experiment.
5. No paid model, voice, music, image, video, or review call is authorized.
   Default all local proofs to silent video with complete on-screen captions.
   A future voice pass must lock the exact narration, provider/voice, request
   hash, estimate, and maximum cost before asking Brian for approval.
6. Do not create/start/stop/delete a RunPod resource, make an authenticated
   cloud request, upload a file, or publish a video in the authorized local
   stages. A local credential-free readiness check is allowed. Cloud approval
   must name the exact batch, content hash, pod configuration, maximum creates,
   cost ceiling, transport, outputs, and deletion/cleanup effect.
7. Never reuse or rerun a historical CM RunPod controller whose authorization
   or one-create allowance has been consumed. Historical controllers and run
   names are evidence and design references, not generic launch commands.
8. All scientific claims need traceable evidence. Every numeric chart value
   must be loaded programmatically from a retained machine-readable source,
   never retyped from narrative prose. Every claim records source path,
   SHA-256, locator/field, scope, status, and wording boundary.
9. Distinguish facts, interpretations, hypotheses, and conceptual animations
   visually and in metadata. A proposed mechanism is not an experimental
   result. A negative result is not evidence that all related approaches fail.
10. Keep comparison boundaries honest: preparation, evaluator kernel, public
    wrapper, construction, extraction, persistence/reload, and end-to-end task
    time are different measurements. Never blend them into one speed ranking.
11. Prefer deterministic rendering below an explicitly approved editorial
    plan. Fixed seed, frame-derived progress, content-addressed caches, no wall
    clock in frames, half-open frame intervals, and immutable result manifests
    are required.
12. Use small, reviewable changes. Do not fork a second implementation of a
    capability already provided by IVC or POP-Video-Creator.

INITIAL TECHNICAL FINDINGS TO VERIFY, NOT BLINDLY ASSUME

- Master-Video-Creator already provides brief-to-treatment/director/assembly
  workflows, JSON schemas, generated-media adapters, deterministic assembly,
  multi-format output, OTIO, gap reports, provenance, encoded-media
  observation, review preparation, caching, dry-run cost gates, and resumable
  production packages.
- POP-Video-Creator already provides a deterministic 1920x1080@30 scientific
  renderer. Its `crse_neural` subject and tests demonstrate five evidence-led
  neural/recognition explainer cuts. Generalize through reusable CM primitives;
  do not clone five more one-off directors for every topic.
- The current IVC `popvc` adapter may still have a hard-coded Windows path and
  a subject allowlist that omits `crse_neural`. That is a portability and
  integration defect to fix cleanly before RunPod packaging.
- Artifact-To-Video is best for deterministic walkthroughs of static HTML/PDF
  sources. It is not a replacement for a reusable diagram/benchmark renderer.
- Existing CM RunPod workflows use guarded, hash-bound disposable jobs, but
  their prior one-create permissions are consumed. Borrow the safety ideas,
  not their authorization or frozen workload identity.

PHASE 0 — DISCOVERY AND ARCHITECTURE DECISION RECORD

Inspect the three preferred tools and the relevant CM sources before editing.
Create an architecture decision record (ADR) in a new, clearly scoped video
factory directory under CM_Computation. The ADR must include:

- capability matrix for Master-Video-Creator, POP-Video-Creator,
  Artifact-To-Video, and any genuinely relevant alternative;
- build/extend/reject decision for each;
- exact ownership boundaries among evidence, editorial planning, scene
  rendering, assembly, QA, and remote execution;
- portability gaps, especially absolute Windows paths, subprocess interpreter
  selection, fonts, Chromium, FFmpeg, filesystem separators, and cache paths;
- whether the scientific renderer should be a new IVC generator or an extended
  POP subject behind the existing adapter;
- dependencies and licenses needed in a distributable Linux bundle;
- risks, mitigations, and rejected alternatives;
- a concrete local proof plan and a separate remote-readiness plan.

Preferred decision unless inspection contradicts it:

- extend POP-Video-Creator with one data-driven `cm_science` subject (or a name
  matching its surrounding conventions);
- extend/configure the IVC adapter to invoke it portably and expose its request
  schema;
- let IVC assemble complete videos, manage formats/provenance, and observe the
  encoded result;
- keep evidence and catalog files in CM_Computation;
- call Artifact-To-Video only for deliberately selected source-page scenes.

If project permissions do not allow edits under PoP\Tools, finish discovery and
the ADR, then ask once for narrowly scoped write permission naming the two
exact tool directories. Do not silently copy the projects or build a parallel
engine in CM_Computation.

PHASE 1 — EVIDENCE AND TERMINOLOGY CONTRACT

Build a source registry and claim ledger before building generalized scenes.
Prefer current machine evidence and correction records over older narrative
summaries. Read at least the following classes of source, resolving exact names
and supersession from the repository:

A. Current corrections and comparison evidence

- deliverables_n22_24/corrections_2026_08_25/
  CM_BENCHMARK_AUDIT_CORRECTION_REPORT_2026-08-25.md
- the corrected RunPod pass and its machine-readable evidence
- current deep-performance audit/result records

B. Accepted earlier evidence and its supersession chain

- CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md and addendum
- CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md
- CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md
- CM_GAP_EPFL_VALIDATION_2026-08-03.md and the underlying JSON/CSV
- CM_MASTER_EXPLAINER_PROMPT_2026-08-03.md for narrative structure only where
  newer evidence has changed its numeric interpretation

C. Representation and execution semantics

- README and current research indexes
- cm_ir.py, cm_build.py, bitset_backend.py, serialization/persistence code,
  and focused tests that define actual behavior
- authoritative docs for eager, lazy, pair, hybrid, partial-hybrid, and
  parallel variants; do not infer a variant only from its name

D. CRSE/recognition program

- docs/recognition/README.md, LEARNING_ROADMAP.md, experiment_register.json,
  milestone reports and result JSON
- current top-level research handoffs and Linux confirmation records
- the existing CRSE neural video prompt/renderer only as a presentation and
  integration reference; recheck every claim against the evidence artifacts

E. RunPod safety and transport

- docs/runpod/RUNPOD-SETUP-HANDOFF-2026-08-28.md
- current verification gates, authorizations, outcome audits, and the latest
  offline readiness script
- inspect historical controllers only to extract reusable safety properties

Create validated machine-readable artifacts such as:

- `source_registry.json`: source ID, repository-relative path, SHA-256, type,
  status, date, and supersedes/superseded-by links;
- `claim_registry.json`: stable claim ID, exact allowed wording, plain wording,
  technical wording, type (`fact`, `measurement`, `interpretation`,
  `hypothesis`, `conceptual`), status (`confirmed`, `revised`, `superseded`,
  `exploratory`, `negative`, `not_promoted`), scope, measurement boundary,
  comparator, ratio direction, uncertainty, source IDs and locators;
- `glossary.json`: term, expansion, plain definition, technical definition,
  common confusion, source IDs;
- `visual_data/*.json`: minimal chart-ready extracts generated from original
  retained evidence with a transformation/provenance record.

Validate each file with JSON Schema or an equivalent strict typed model. Reject
unknown fields where practical. Refuse to overwrite an existing production
artifact with different content.

Required truth guards in the claim ledger:

- Do not say broadly that “CM beats CSE.” Define plain structural CSE and the
  stronger sharing-aware CSE-flat comparator.
- Common subexpression elimination computes a repeated expression subtree once
  and reuses it. CSE-flat additionally flattens eligible associative chains.
  CM can add canonical normalization/merging. Any video about the mechanism
  must show which transformation is actually responsible on that workload.
- Current corrected evidence includes a workload on which bare CM/CSE-flat is
  about 0.909 overall with fewer instructions/primitive operations and the
  advantage narrows toward k=16. This is a kernel boundary after compilation,
  not a one-off public-API speedup.
- An earlier accepted workload remains approximately parity (0.9998 with an
  interval spanning one). Both results are valid within their stated scopes;
  neither establishes universal dominance.
- The public CM wrapper is slower in the corrected comparison. Preparation is
  materially more expensive than the comparison compiler in accepted
  evidence. Reuse count and structural reduction determine whether the cost
  can be repaid.
- Ratios below one favor CM only when the ratio is explicitly CM/comparator.
  Label the numerator, denominator, boundary, workload, and uncertainty.
- “CM” may refer to an explicit dense correspondence-matrix representation or
  to a CM-IR compilation/evaluation arm. “CM-IR” is a canonicalized/interned
  DAG intermediate representation. Never let narration or visuals collapse
  these meanings.
- The CRSE learning/recognition work is experimental. For every milestone state
  the actual frozen question, data split, comparator, result, limitation, and
  promotion decision. Never turn a passed engineering verification into a
  scientific generalization, or a held/negative milestone into deployment.

When sources conflict, do not resolve them by averaging or choosing the more
exciting result. Follow explicit supersession first, then newer scoped
correction evidence, then the underlying machine artifact. Record unresolved
conflicts and block the affected claim/video.

PHASE 2 — VIDEO BRIEF AND CATALOG CONTRACT

Define a data-driven `video_brief` schema. A brief must be sufficient to render
without editing Python. It should contain at least:

- schema version and stable video ID;
- series/track, title, one-sentence promise, audience, assumed knowledge,
  prerequisites, duration tier, target formats, and status;
- hook, central question, answer, limits/caveats, and closing takeaway;
- ordered claims by claim ID, with chosen plain/technical wording;
- ordered scenes, each with purpose, visual primitive, data references,
  caption/narration text, duration or timing intent, and transition;
- display rules for scope, boundary, uncertainty, conceptual labels, and source
  footnotes;
- narration mode (`off` by default), pronunciation overrides, and caption
  contract;
- expected output files, local/remote suitability, and estimated render class;
- content hash over the normalized brief plus referenced evidence extracts.

Also define:

- `video_catalog`: every proposed video and its dependencies/status;
- `series_map`: learning paths and prerequisite graph;
- `render_job`: immutable brief hash, tool/source versions, format, resource
  requirements, cache identity, output destination, and retry policy;
- `render_result`: job identity, output hashes, technical observations, preview
  frame hashes, warnings, and pass/fail;
- `batch_manifest`: ordered jobs, aggregate estimates, continuation/resume
  state, and exact approval identity.

Provide human-readable Markdown generated from the JSON; JSON is authoritative.
Add schema fixtures and tests for valid, invalid, superseded-claim, conflicting-
boundary, missing-source, and changed-hash cases.

PHASE 3 — REUSABLE SCIENTIFIC MOTION-GRAPHICS LIBRARY

Build a coherent visual grammar in POP-Video-Creator instead of bespoke video
code. Reuse its existing VideoSpec, timing, encoding, theme, and manifest
contracts. Add only the minimum general primitives needed for the approved
proof set, then expand based on catalog needs.

Candidate reusable primitives:

- Boolean expression/tree with animated evaluation;
- repeated-subtree highlighting and CSE DAG sharing;
- safe associative-chain flattening into an n-ary operation;
- explicit dense CM/truth-layout view with live versus ambient variables;
- canonical/interned CM-IR DAG with node reuse and normalization steps;
- side-by-side AST, CSE, CSE-flat, CM-IR, and flat-instruction views;
- preparation -> compiled artifact -> repeated evaluation -> public wrapper
  boundary pipeline;
- instruction and primitive-operation counters linked to the animated graph;
- benchmark ratio plot with one-line scope/boundary badge and confidence band;
- break-even/reuse animation separating one-time cost and per-evaluation cost;
- support-size sweep and selector/policy decision surface;
- cache/persistence/version-delta flow;
- exact-output/oracle verification panel;
- recognition/decomposition graph with train/validation/test separation;
- result card supporting confirmed, mixed, negative, exploratory, and
  not-promoted outcomes without using celebratory green for every completion;
- source citation footer keyed to claim and source IDs;
- clearly styled conceptual/hypothesis scene.

Design requirements:

- One color meaning everywhere: representation/method identities, evidence
  status, and measurement boundaries must not change meaning between videos.
- Use position, labels, shape, and texture as well as color. Meet readable
  contrast and color-blind-safe requirements.
- Captions and source labels stay within title/action safe zones in both 16:9
  and any approved 9:16 derivative. Avoid tiny table screenshots.
- Animations must teach one relationship at a time. Settle long enough to read
  the result. Never rely on a chart zoom to hide an inconvenient comparator.
- Default master: 1920x1080, 30 fps, H.264/yuv420p, deterministic silent MP4.
  Keep rendering format-aware so IVC can derive approved platform formats.
- No generative image/video model is necessary for the initial scientific
  proofs. Prefer SVG, HTML/canvas, Cairo/Pillow, or the project's established
  renderer. If a generated illustration would materially help later, prepare
  a request and cost estimate separately.
- Every primitive gets unit tests plus at least one fast low-resolution render
  fixture. No renderer obtains scientific values directly from arbitrary prose;
  it receives validated evidence extracts and claim IDs.

PHASE 4 — MASTER-VIDEO-CREATOR INTEGRATION

Make the renderer a first-class IVC generator. Follow IVC's registry,
validation, caching, manifest, and assembly patterns. Do not bypass them with a
shell script that merely concatenates finished MP4s.

At minimum:

- remove the hard-coded POP project path from the runtime contract; resolve it
  by explicit CLI/config value or a safe project-relative/discovery rule, with
  an actionable error when missing;
- select the POP interpreter/project portably on Windows and Linux; never
  assume the current global Python has POP installed;
- expose `cm_science`/`crse_neural` requests in `describe()` and strict
  validation without weakening existing subject validation;
- include renderer version, brief/evidence hashes, command identity, source
  inputs, and tool versions in the generator manifest;
- ensure cache keys include every input that can change pixels or timing;
- return native geometry explicitly and let the established assembler apply
  the target-format policy;
- handle subprocess UTF-8 and failures without leaking environment values;
- add adapter, registry, cache, command construction, Windows path, Linux path,
  invalid request, and existing-subject regression tests;
- add a documented direct render command and an IVC assembly command for each
  local proof.

Use IVC's observation workflow on encoded proofs. If the observer's speech and
face checks do not apply to silent diagram videos, invoke the documented skip
options and retain the applicable encoded duration, dimensions, codec, hash,
representative-frame, cadence, motion, and provenance checks.

PHASE 5 — LOCAL PROOF SET

Produce exactly three small local proof videos before a broad catalog render.
Each should be concise enough for iteration but complete enough to prove the
pipeline. Recommended proofs:

1. `cm-foundation`: from a Boolean expression and truth assignments to the
   explicit CM view, with live versus ambient variables and a strict “what this
   is / is not” ending.
2. `explicit-cm-vs-cm-ir`: show that a dense correspondence matrix and the
   canonical/interned CM-IR DAG are different artifacts with different costs
   and uses.
3. `cm-ir-vs-cse-flat`: show repeated subexpressions, flattening,
   normalization/merging, then separate preparation, bare-kernel, and public-
   wrapper evidence. Include the scoped corrected result and the scoped parity
   result without declaring a universal winner.

If evidence review shows one suggested proof cannot be stated cleanly, replace
it with the nearest foundational topic and document why. Do not render a broad
CRSE catalog here; the existing CRSE neural proof set can be used as a
regression/integration fixture.

For each proof, produce:

- validated brief and normalized content hash;
- source/claim map;
- final assembly spec;
- MP4, provenance, gap/cadence report, and encoded observation bundle;
- contact sheet or individual preview images for opening, early explanation,
  middle, settled comparison, and final frame;
- machine validation report and a short human review checklist;
- exact reproduction command.

Inspect the encoded frames, not only source drawings. Correct clipping,
overlap, unreadable captions, excessive motion, false visual implication,
inconsistent color semantics, incomplete settling, and inaccurate citations.
Do not call a proof final solely because FFmpeg exited zero.

PHASE 6 — DEEP CANDIDATE VIDEO CATALOG

Once the schemas and three proofs pass, generate a broad candidate catalog;
do not render the catalog. The catalog is a proposal for the next deep
editorial task. It must be evidence-aware, dependency-aware, and much more
specific than a list of titles.

Use three duration tiers:

- visual short: approximately 45–90 seconds, one question and one takeaway;
- core explainer: approximately 2–5 minutes, one coherent concept/comparison;
- deep dive: approximately 8–15 minutes, multiple evidence panels and caveats.

For every candidate include audience, prerequisite videos, central question,
what the viewer should be able to explain afterward, claim IDs, required
visuals/data, likely misconceptions, caveats, duration tier, reuse opportunities,
render complexity, and priority. Avoid duplicate videos that differ only by
title; identify which long-form master can generate which shorts.

Cover at least these tracks, but add or remove candidates based on evidence:

1. Foundations
   - why Boolean computation matters;
   - expression, truth table, Boolean function, support/live variables;
   - what a correspondence matrix is;
   - what CM does not claim to be;
   - explicit dense CM versus CM-IR.

2. CM representations and execution variants
   - CM-IR nodes, canonicalization, interning, normalization, lifting, and
     serialization/persistence where implemented;
   - eager, lazy, pair, hybrid, partial-hybrid, and parallel variants, each
     limited to its actual implemented/formal/experimental status;
   - packed words/BitSet execution and width/backend selection;
   - nominal variable count versus live support.

3. Comparators and mechanisms
   - raw AST evaluation;
   - CSE in plain language;
   - plain structural CSE versus sharing-aware CSE-flat;
   - CM-IR versus CSE-flat: common ground and extra transformations;
   - why instruction count, primitive operations, memory traffic, support size,
     and reuse may change outcomes;
   - why no single blended “fastest method” chart is scientifically honest.

4. Cost boundaries and performance evidence
   - compilation/preparation versus evaluator kernel versus public wrapper;
   - reuse and break-even economics;
   - corrected successor evidence and k-dependence;
   - the scoped EPFL/parity result;
   - cross-machine/RunPod replication and what it does and does not prove;
   - selector/policy results and width-only limitations;
   - memory, persistence/reload, version delta, and natural task measurements;
   - how exact truth digests, alternating schedules, clustering, and CIs protect
     the comparison;
   - the project's correction story and why supersession improves credibility.

5. Toolbox and use cases
   - BitSet/flat/words, CM/CM-IR, CSE, CUDD/ROBDD, SAT, Espresso, SymPy and
     other comparators only where the repository has evidence;
   - configuration/feature models, circuits, policy/rule systems, repeated
     related expressions, and any retained natural-task pilots;
   - decision videos: which representation/tool to try for a given question.

6. Recognition/CRSE research
   - the recognition question and why graph learning is being tested;
   - foundation and neural graph milestones;
   - variable decomposition, natural decomposition, direct-cut ranking, and
     variable-conditioned cuts;
   - task computation, proved rules, version cache, profitability, natural
     evaluation/revisions, normalization, Linux confirmation, and policy;
   - negative/mixed/no-promotion results and the precise next falsifiable
     question;
   - separate “what was engineered successfully” from “what generalized.”

7. Meta/evidence literacy
   - how to read a CM/comparator ratio;
   - why scopes and boundaries matter;
   - how an audit changes a headline;
   - conceptual animation versus measured result;
   - how a video is bound to source hashes and reproduced.

Generate at least two useful learning paths: a nontechnical path and a
technical/research path. Identify a first production wave of no more than
8–12 videos, but mark it `proposed`, not approved. The wave should reuse the
new primitives heavily and include at least one honest negative/mixed result,
not only favorable findings.

PHASE 7 — RUNPOD-READY, LOCAL-ONLY PACKAGING

Prepare a portable render-worker design and local dry-run package. Do not make
any cloud/API call. The package must not depend on `C:\...` paths. It must be
content-addressed and able to run in a clean Linux environment.

Required deliverables:

- lockfile or container definition with pinned versions/digests where
  practical, fonts, Chromium/browser dependencies if used, and FFmpeg;
- an explicit allowlist of code, evidence extracts, briefs, schemas, and fonts;
- exclusion audit proving no `.env*`, credentials, caches, unrelated research
  corpora, or historical bulky runs are included;
- `render-worker` command that accepts one immutable `render_job.json`, writes
  progress JSONL, and atomically produces a `render_result.json` plus outputs;
- batch runner with bounded concurrency, resume-by-hash, no duplicate finished
  job, per-job timeout, graceful interruption, and failure isolation;
- local package manifest with every file path/size/SHA-256, bundle SHA-256,
  source revisions, dependency identity, and expected outputs;
- local container or clean-environment smoke for one tiny render if the needed
  tooling is already available; otherwise a fully specified unexecuted test
  and the exact missing prerequisite;
- RunPod preflight proposal stating CPU/GPU choice, exact image, CPU/RAM/disk,
  zero/persistent volume decision, ports/transport, expected duration, current
  price quote source, conservative cost estimate, hard cost ceiling, maximum
  creates, watchdog, download/verification steps, and deletion/cleanup effect;
- a new controller/job identity. Never use a prior CM research run name.

The eventual controller must fail closed and own only the pod it creates. It
must bind upload, job, result, and cleanup to hashes and an authorization ID;
use a per-pod bootstrap token distinct from the account key; verify resource
shape before upload; retrieve and verify all results before approved cleanup;
record append-only lifecycle events; and reconcile owned-pod state on every
terminal path. Design and unit-test these behaviors with local fakes. Do not
perform authenticated inventory checks in this stage.

RUNPOD APPROVAL STOP

At the end of local work, stop and ask Brian to approve or revise one exact
remote proposal. The approval request must state, in one compact block:

- batch ID and number/list of videos;
- bundle SHA-256 and batch-manifest SHA-256;
- whether the batch is proof-only or production candidate;
- exact RunPod resource/image/disk/volume/region constraints;
- maximum pod creations and maximum parallel pods;
- estimated and hard-maximum USD cost based on a current quoted rate;
- exact authenticated effects: create, upload, execute, download, verify,
  stop/delete, and final inventory reconciliation;
- timeout and automatic cleanup behavior;
- whether any paid non-RunPod service is involved (default: none).

Do not treat “use RunPod eventually,” this prompt, any prior authorization, or
possession of credentials as approval. Wait for an exact yes or requested
changes.

PHASE 8 — ONLY AFTER EXACT RUNPOD APPROVAL

When and only when Brian approves the exact proposal:

1. Re-run local source/hash/schema/test/preflight gates and confirm the approved
   identities still match. Any material change invalidates approval.
2. Make at most the approved number of creates. Do not silently replace a
   failed or shape-mismatched pod.
3. Verify the created pod identity and exact resources before upload.
4. Upload only the allowlisted hash-bound bundle.
5. Run the approved batch with bounded concurrency and progress records.
6. Resume only unfinished hash-identical jobs; never rerender passed jobs by
   accident.
7. Download results, verify hashes, run encoded-media QA locally, and retain
   remote logs/evidence needed for audit.
8. Perform only the cleanup action included in the approval. Reconcile owned
   pod inventory and report any ambiguity instead of deleting an unowned pod.
9. Produce a final production report: jobs requested/passed/failed, outputs and
   hashes, costs estimated/observed, pod lifecycle, cleanup outcome, QA
   findings, and videos requiring human revision.

TEST AND ACCEPTANCE GATES

Before calling Level 1 complete:

- all new schemas validate their positive fixtures and reject negative
  fixtures;
- source and claim hashes reproduce, and a changed source invalidates the
  affected brief/job;
- superseded claims cannot enter an approved brief except in a visibly marked
  correction/history scene;
- the POP renderer's existing tests still pass plus focused new primitive and
  subject tests;
- IVC's existing focused generator/assembly tests still pass plus new adapter
  tests;
- the three proof briefs render deterministically twice or use a documented
  byte-stability/visual-stability contract where container metadata prevents
  identical MP4 bytes;
- ffprobe/observer confirms dimensions, frame rate, codec, duration, stream
  layout, provenance hash agreement, and decodable opening/middle/final frames;
- visual review confirms safe zones, caption fit, legibility, color semantics,
  settling, no clipping/overlap, and no misleading comparison boundary;
- every numeric pixel-level chart element traces to a machine artifact;
- the candidate catalog validates and every proposed video has prerequisites,
  evidence status, and a render-complexity estimate;
- the RunPod bundle passes exclusion and hash-manifest audits locally;
- no cloud or paid-service activity occurred;
- final `git status --short` and `git diff --stat` are reviewed separately for
  each touched repository, clearly distinguishing pre-existing changes.

EXPECTED LEVEL-1 DELIVERABLES

1. architecture ADR and capability matrix;
2. source registry, claim ledger, glossary, extraction provenance, and schemas;
3. video-brief/catalog/job/result/batch schemas with fixtures/tests;
4. reusable CM scientific scene library and data-driven subject;
5. portable IVC integration and documentation;
6. three local proof videos with manifests, encoded observations, previews,
   and reproduction commands;
7. deep candidate catalog, learning paths, and proposed 8–12-video first wave;
8. portable local RunPod bundle and credential-free preflight report;
9. test report and independent final state/diff inventory;
10. one exact RunPod approval request, with execution paused.

PROGRESS AND HANDOFF STYLE

Lead progress updates with concrete outcomes. Report blockers only after safe
in-scope alternatives are exhausted. Do not claim a render is final without
encoded-frame inspection. At completion, state exactly what changed, what was
tested, what passed/failed/skipped, the three proof locations, the proposed
first wave, the RunPod bundle hashes, and the single decision Brian needs to
make next.
```

## What the prompt is designed to prevent

- a new standalone video generator that duplicates IVC;
- videos whose numeric claims are copied from a superseded deck;
- collapsing explicit CM, CM-IR, a CM benchmark arm, and the public wrapper
  into one object;
- treating a bare-kernel result as an end-to-end speedup;
- treating CSE-flat as ordinary unflattened CSE;
- bulk rendering before the evidence schema and three proof videos work;
- assuming Windows paths or the developer's current Python exist on RunPod;
- using a GPU merely because RunPod offers one;
- reusing consumed research-job authorization for video rendering;
- paid voice/model calls or pod creation hidden inside an apparently local
  command;
- technical success being mistaken for scientific or editorial approval.

## Suggested execution sequence

Run the prompt as a fresh Codex task rooted at
`C:\Users\brian\Documents\CM_Computation`. Expect the first task to finish at
the RunPod approval stop. The next task should receive only the reviewed first
wave, locked briefs/scripts, bundle hashes, and an exact production
authorization; it should not repeat the whole research/discovery pass unless a
source hash changed.
