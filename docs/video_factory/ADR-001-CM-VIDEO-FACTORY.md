# ADR 001 — Evidence-bound CM video factory on the existing POP/IVC stack

**Status:** accepted for Level 1 local implementation
**Date:** 2026-08-30
**Cloud / paid services:** prohibited in this level
**Repositories inspected:**

- `CM_Computation`: branch `main`, HEAD `7a18649e96ea4e9fd1994d0a4310947f60dee64a`
- `PoP/Tools`: branch `main`, HEAD `81af0adec2e74bd0a0fa28a99cc0884dbb9b77ec`
- `Master-Video-Creator`: clean within the inspected Tools worktree
- `POP-Video-Creator`: clean within the inspected Tools worktree
- `Artifact-To-Video`: materially dirty before this task; excluded from edits

The CM repository was already materially dirty, including unrelated modified,
deleted, and untracked research files. All Level 1 CM factory files are isolated
under `docs/video_factory/`. No existing CM or Artifact-To-Video file is an edit
target.

## Decision

Extend POP-Video-Creator's already implemented version-2 neutral engine with one
trusted, strict, data-driven `cm_science` content pack and scene contract. Use
Master-Video-Creator's existing `video_spec` generator to invoke resolved
`deterministic-video-spec/v2` files, then let IVC assemble, cache, record
provenance, and observe encoded outputs.

Do not add CM to the legacy `popvc` adapter. That adapter is intentionally the
legacy POP subject path. The newer `video_spec` adapter already provides the
portable project/interpreter selection, exact theme/content/spec hash binding,
native-geometry reporting, UTF-8 subprocess handling, renderer-manifest
preservation, cache identity, Windows/Linux path behavior, and actionable
configuration errors required by this project.

CM_Computation remains the evidence and editorial authority. The renderer never
opens arbitrary narrative sources; it receives validated scene data plus claim
and source identifiers. Artifact-To-Video remains an optional later input only
for a deliberately selected webpage/PDF walkthrough.

## Capability matrix

| System | Existing relevant capability | Decision | Ownership after this ADR |
| --- | --- | --- | --- |
| CM_Computation | Corrected claim chain, retained JSON/CSV evidence, implementation semantics, recognition register, RunPod safety history | Extend in a new scoped directory | Source/claim/glossary registries, chart extracts, briefs, catalog, jobs/results/batches, bundle identity |
| Master-Video-Creator (IVC) | Strict `video_spec` generator, deterministic assembly, formats, cache, provenance, gap/cadence reports, encoded observation, review and package machinery | Reuse; no speculative code change | Generator invocation, assembly, format policy, encoded provenance/observation |
| POP-Video-Creator | Neutral v2 briefs/specs, strict content packs and scene registry, theme tokens, pure progress clock, Chromium frames, deterministic FFmpeg path | Extend with `cm_science` pack | CM scientific scene validation and pixels; no evidence discovery |
| Artifact-To-Video | Deterministic HTML/PDF inspect-plan-render workflow | Reject as primary; reserve as auxiliary | Selected source-page/paper walkthrough only |
| New standalone renderer | None needed | Rejected | Would duplicate strict contracts, rendering, cache, assembly, and QA |

## Exact ownership boundaries

| Boundary | Owner | Contract |
| --- | --- | --- |
| Evidence status and supersession | CM_Computation | `source_registry.json`, `claim_registry.json` |
| Terminology | CM_Computation | `glossary.json` |
| Numeric chart data | CM_Computation | generated `visual_data/*.json` with source field locators and transformations |
| Editorial selection and learning paths | CM_Computation | `video_brief`, `video_catalog`, `series_map` |
| Scientific scene validation and drawing | POP-Video-Creator | trusted `cm_science` content-pack registrar |
| Immutable pixel contract | POP-Video-Creator | resolved v2 spec and `render_sha256` |
| Generator cache and invocation provenance | IVC | `video_spec` request and generator manifests |
| Final encoding/format/assembly | IVC | assembly spec and provenance |
| Encoded technical QA | IVC plus CM factory checks | render observations, media probe, preview hashes, visual checklist |
| Remote job/batch identity | CM_Computation | immutable render job/result/batch schemas |
| Eventual disposable worker | new local-only package in CM_Computation | hash-bound worker and batch runner; no cloud call in Level 1 |

## Portability findings

- The older IVC `popvc` generator remains a legacy subject adapter, but the
  current `video_spec` bridge contains no user-specific project path. It
  resolves the sibling checkout or `POP_VIDEO_CREATOR_DIR` and accepts
  `POP_VIDEO_CREATOR_PYTHON`.
- Specs outside the renderer/IVC roots require an explicit path-list entry in
  `IVC_VIDEO_SPEC_ROOTS`. Reproduction commands set that value to the CM
  factory root; the portable bundle uses repository-relative roots.
- Windows and Linux subprocess paths are constructed as argument lists. The
  bridge forces UTF-8 and never prints environment values.
- The current task PATH has no `ffmpeg`/`ffprobe`. IVC's Python environment has
  `imageio-ffmpeg 0.6.0`, which supplies FFmpeg 7.1. Encoded observation uses
  the project's supported fallback and reports unavailable ffprobe data rather
  than installing anything.
- Chrome and Edge are installed locally. POP's pinned Node dependency is
  Playwright `1.53.1`; a Linux bundle must install the matching Chromium and
  OS libraries explicitly.
- POP themes currently use portable system font stacks, not packaged fonts.
  Spec/hash determinism is preserved, but cross-machine raster identity is not
  guaranteed until an allowlisted font set is bundled. Level 1 records visual
  stability rather than claiming universal byte-identical frames.
- Cache and output roots are explicit in jobs and bundle commands. No `C:\...`
  path is permitted in the portable manifest.

## Dependencies and distribution posture

Local proof execution uses Python 3.10.11 from IVC's checked-in environment,
Pydantic 2.13.4, jsonschema 4.26.0, Pillow, imageio-ffmpeg 0.6.0 / FFmpeg 7.1,
Node 22.18.0, npm 10.9.3, and Playwright 1.53.1. IVC declares additional
packages for its broader product, but the render worker will install only the
smallest pinned subset exercised by the resolved-spec and assembly paths.

None of the four project roots contains a top-level license file. The projects
describe project-internal research provenance and third-party dependencies
under their own licenses. A distributable public image is therefore blocked
until project-code licensing is explicitly declared and a third-party notice
inventory is generated. A local private dry-run bundle may still be built and
audited.

## Evidence decisions affecting the proof set

- The 2026-08-25 correction makes sharing-aware CSE-flat the primary generic
  comparator. Raw AST remains an ablation.
- The exactly counterbalanced local B2/B4 V3 result is primary locally: bare
  CM/CSE-flat `0.8905696773`, formula-cluster 95% CI
  `[0.8740654100, 0.9072717742]`, compiled evaluator boundary, 216 formula
  clusters. The earlier corrected and three-pod runs remain valid within their
  own schedules and show the requested approximately `0.909` replication
  range (`0.9026–0.9126`).
- The accepted EPFL AND/INV workload remains parity: `0.9998256739`, circuit-
  clustered 95% CI `[0.9747, 1.0249]`, with equal CM/CSE-flat instruction and
  executed-operation counts. Preparation was `4.11x` CSE-flat and 55 of 129
  cases never broke even.
- Dense correspondence matrices and CM-IR are different artifacts. The former
  is an explicit truth-layout output; the latter is a canonicalized/interned
  shared DAG that can evaluate without dense reinflation.
- Recognition/CRSE results are experimental. Current retained work contains
  engineering passes, mixed and negative scientific outcomes, and explicit
  no-promotion decisions. The first three proofs stay foundational.

## Local proof plan

Exactly three silent 1920×1080, 30 fps proofs will be rendered:

1. `cm-foundation`: Boolean expression → assignments → explicit CM, with live
   support separated from the ambient variable universe.
2. `explicit-cm-vs-cm-ir`: dense truth layout versus canonical/interned DAG,
   including different output/cost boundaries.
3. `cm-ir-vs-cse-flat`: repeated structure, safe flattening,
   normalization/merging, then distinct preparation, bare-kernel, and public-
   wrapper evidence with both corrected B2/B4 and accepted EPFL scopes.

Each proof is planned from a validated CM brief, resolved into a POP v2 spec,
invoked through IVC `video_spec`, assembled by IVC, observed from the encoded
MP4, sampled at five checkpoints, and reviewed against a machine checklist.

## Remote-readiness plan

After local proofs pass, create a content-addressed Linux CPU bundle containing
only allowlisted renderer/orchestrator code, schemas, resolved specs, evidence
extracts, jobs, and fonts/dependency metadata. Add an atomic render worker,
bounded resumable batch runner, exclusion audit, file/hash manifest, local fake
controller tests, and one credential-free proposal. Do not upload the bundle,
authenticate, inventory, create, start, stop, or delete any RunPod resource.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Superseded or exciting prose leaks into pixels | Brief validation resolves claim IDs and source hashes; numeric visuals load only generated extracts |
| Measurement boundaries are visually blended | Every measurement scene requires workload, numerator/denominator, boundary, scope, and uncertainty labels |
| Theme colour implies scientific status | Status also uses labels, borders, shapes, and textures; success colour is not used for every completed experiment |
| Dirty repositories cause accidental attribution | New CM directory only; scoped Git state/diff checks per repository; no commit/stage/push |
| New pack bypasses the neutral engine | Trusted catalog registration only; strict Pydantic model; no import path in specs |
| Linux pixels differ due to fonts/browser | Pin browser and bundle reviewed fonts before remote approval; compare preview hashes under a documented visual-stability contract |
| Historical cloud permission is reused | New batch/authorization identity; local fakes only; exact approval block required after bundle hashes exist |

## Rejected alternatives

- Add `cm_science` to legacy `popvc`: rejected because it would couple new
  scientific work to the legacy POP subject allowlist and duplicate the newer
  resolved-spec identity contract.
- Modify IVC before proving a missing behavior: rejected because current code
  already implements the specified portability and strict hashing behavior.
- Use Artifact-To-Video for diagram and benchmark scenes: rejected because it
  renders source artifacts rather than reusable scientific relationships.
- Use a generative image/video model or GPU: rejected for the proof set; SVG,
  HTML/CSS, Chromium, and FFmpeg are sufficient and locally deterministic.
