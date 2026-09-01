# CM deep-series v2 production planning

Status: **local planning complete; executable rendering blocked on infrastructure**

Approved Bible: `51a05667bcafdb1012883b35c04387a8148cd277c18a9cdec7fdd886e2f3d3f4`

Approved review manifest: `d9be639408d03e121cbcac4155cab86d0ff62123ef349a5a50366c9098c78d93`

Approval identity: `bfa4e8ee32a5cf7266e191c9c67c0ec8cd178fbcfffd83f654b0b7761f6a10fe`

This package authorizes no RunPod call, upload, paid service, resource creation, or publication.

## Routing result

- 48 approved episodes
- 188 independently cached chapters
- 1206 storyboard compositions
- 14 focused episodes intended for local frame rendering after smoke qualification
- 34 core/deep episodes intended as deterministic CPU remote candidates only after qualification and separate authorization
- All authoring, validation, planning, offline narration, assembly, mux, and QA remain local

## Blocking infrastructure

The 188 checked-in renderer briefs identify chapter scene IDs and cache identities, but do not yet carry resolved POP scene payloads, exact frame spans, complete input hashes, or expected-output contracts. They are descriptors, not executable jobs.

Build and validate these local work packages in order:

1. **WP1 — Executable chapter render contract.** Add a strict schema and compiler that resolves all storyboard scenes, beats, claims, assets, durations, and frame spans into deterministic POP payloads.
2. **WP2 — Visual primitive completion and preflight.** Implement any missing matrix, DAG, circuit, feature-model, policy, evidence, and recognition primitives plus text-fit/safe-zone checks.
3. **WP3 — Six full-resolution archetype chapter smokes.** Render and encode one local 1080p chapter for each representative visual archetype, then measure throughput and determinism.
4. **WP4 — Narration and audio realization.** Select an explicitly licensed local/offline voice or human recording route and bind cue audio to the existing narration contracts.
5. **WP5 — Assembly, captions, and encoded-media QA.** Add resumable chapter assembly, audio/caption mux, stream inspection, decoded-frame sampling, and final provenance manifests.
6. **WP6 — Immutable bundle and exact remote proposal.** After the local smokes pass, construct the normalized allowlisted bundle, exact ordered chapter jobs, cost model, and approval request.

## Current readiness warnings

- 188 of 188 chapter renderer briefs are descriptors rather than executable resolved render payloads.
- No representative full-resolution chapter master exists yet; current contact sheets, GIFs, and archetype PNGs are editorial previews.
- Narration text/timing contracts exist, but no local voice identity, license decision, or cue-audio realization is bound.
- The episode contracts are not yet integrated with chapter encode, audio/caption mux, decoded-frame QA, and final release manifests.
- 2 live source-registry entries are currently hash-drifted from the frozen registry.
- A current RunPod resource quote was intentionally not collected under this local-only approval.

## Local renderer diagnostic

The existing POP primitives rendered 216 full-resolution diagnostic frames across 6 archetypes in 93.16 seconds.

Repeated identical progress states produced identical hashes. This is a primitive diagnostic, not a full-chapter workload or a remote cost estimate.

## Remote gate

No executable bundle or batch manifest has been created. A later proposal must include a current public price quote, exact resource shape, exact ordered jobs, bundle and batch hashes, cost/create/retry ceilings, cleanup behavior, and a new explicit authorization.
