# CM video factory — Level 1 report

Date: 2026-08-30
Status: **Level 1 gates and exactly approved v4 remote proof production passed; pod deleted and reconciled**

The exactly approved v2 attempt created one disposable CPU pod, passed exact
resource and bootstrap checks, then failed before rendering because IVC runtime
schemas were absent from the bundle. The pod was deleted and final absence was
verified. The replacement v4 attempt rendered and downloaded all three proofs,
passed independent local post-run QA, and was also deleted and reconciled. No
persistent deployment, commit, push, publication, or credential disclosure was
performed.

## Delivered system

- `ADR-001-CM-VIDEO-FACTORY.md` records the ownership boundary: CM owns
  evidence/editorial truth, POP owns reusable deterministic scientific scenes,
  and IVC owns orchestration, encoding, observation, and review artifacts.
- Strict JSON contracts cover sources, claims, glossary entries, visual data,
  video briefs, catalog entries, series maps, jobs, results, and batches. Valid
  and invalid fixtures exercise the contracts and semantic guards.
- The evidence layer contains 22 hash-bound sources and 27 claims. Numeric
  chart values are generated from retained machine artifacts, not retyped into
  renderer code. Superseded claims are rejected from ordinary briefs.
- POP has a theme-driven `cm_science` content pack with expression-matrix,
  representation-comparison, transform-comparison, boundary, ratio, and result
  primitives. Its planned provenance is location-independent.
- IVC accepts the portable POP `video_spec` request, validates runtime duration,
  and uses project/environment-relative library, font, card-art, and POP paths.
- The catalog contains 44 candidates, two learning paths, and a 10-video first
  wave marked **proposed, not approved**.

## Three local proofs

All outputs are silent H.264/yuv420p, 1920×1080 at 30 fps. Each has a resolved
spec, immutable render job, provenance, gap/cadence reports, encoded
observations, five sampled frames, a contact sheet, source/claim map, validation
report, review checklist, and reproduction command.

| Proof | Duration / frames | MP4 SHA-256 | Result |
|---|---:|---|---|
| `cm-foundation` | 5.8 s / 174 | `1b8d4602fb205a6bfc35a9eff1c875ced4669e5e98962d7488f3941e293dd88d` | passed |
| `explicit-cm-vs-cm-ir` | 7.0 s / 210 | `e86e35a568e74142a9c13962209d1a4a5f94af750a007234b15873ef53194927` | passed |
| `cm-ir-vs-cse-flat` | 12.9 s / 387 | `43d976814b5766531513a136a396cd1e79937f4c8c50b9632f4bf6af589ce9f3` | passed |

Each proof rendered twice to byte-identical MP4 bytes. Observer/provenance hashes
agree; all three have zero gaps, valid opening/middle/final frames, no audio,
and no technical findings. Visual review confirmed safe zones, caption fit,
legibility, stable color semantics, complete settling, no clipping/overlap, and
clear comparison boundaries. IVC emits a long-hold warning for the second and
third proofs because it sees the POP animation as one generated slot; encoded
motion measurement and frame review confirm the internal reveals are active.

## Proposed first production wave

The wave remains editorially unapproved:

1. What a correspondence matrix is
2. Explicit dense CM versus CM-IR
3. Plain CSE versus sharing-aware CSE-flat
4. CM-IR versus CSE-flat: common ground and extra transformations
5. Preparation, kernel, wrapper, and end-to-end time
6. Corrected B2/B4 V3 kernel result
7. EPFL AND/INV parity and its mechanism
8. How to read a CM/comparator ratio
9. How an audit changed the headline
10. D8 Linux confirmation: exact but unprofitable

The final item is the required honest negative promotion result. The complete
prerequisite/evidence/complexity records and both learning paths are in
`video_catalog.json`, `series_map.json`, and `VIDEO_CATALOG.md`.

## Test and QA record

- Factory schema/evidence/semantic suite: **8 passed**.
- RunPod allowlist, worker, resume, controller, ownership, watchdog readiness,
  frozen-bundle identity, and cleanup fakes: **9 passed**.
- IVC generator/assembly/adapter focused suite: **59 passed**.
- POP non-slow focused suite: **34 passed, 2 deselected**; low-resolution
  `cm_science` render: **1 passed**.
- POP full suite: **313 passed, 82 skipped, 5 xfailed, 4 failed**. Three failures
  were local PATH discovery of FFmpeg and passed when rerun against the bundled
  FFmpeg. The remaining failure is the pre-existing machine-local Windows SAPI
  `Microsoft David Desktop` null-reference voice-selection failure; the three
  silent proof renders do not use SAPI.
- Encoded proof QA: **3 passed**; two consecutive renders were byte-identical.
- Bundle construction: two consecutive archives were byte-identical. Extracted
  manifest verification passed for all 156 files; the exclusion/content scan
  found no Windows absolute paths, `.env*`, credential/key patterns, databases,
  caches, `node_modules`, proof MP4s, historical runs, or unrelated corpora.
- Clean extracted-bundle worker smoke: **passed from the v4 archive** for `cm-foundation`; the
  technical contract, output hashes, preview hashes, and expected MP4 hash all
  passed from the packaged code and data.
- Local Docker smoke: **not run** because the local Docker client cannot reach a
  Docker engine. The exact v4 Debian bootstrap and worker subsequently passed on
  RunPod, including FFmpeg, fonts, dependency locks, Playwright, and Chromium.
- Remote post-run QA: **3/3 MP4s and 15/15 preview frames passed** independent
  local hash, stream, dimensions, rate, codec, pixel format, duration, silence,
  payload, PNG-dimension, and nontrivial-pixel checks. Contact-sheet review
  passed legibility, fit, settling, boundary clarity, clipping, and overlap.

## Portable RunPod package

- Batch: `cm-video-level1-proof3-v1` (proof-only, exactly three videos)
- Batch manifest SHA-256:
  `88e986da255f82cc00b7231fb678bb6397c970eb59775c562b333821c9649f3d`
- Archive: `runpod/dist/cm-video-level1-proof3-linux-v1-c36710478f773012.zip`
- Archive SHA-256:
  `c36710478f77301244ffa76cfc16de291e0cdfca31f3990504cb6250aa43b7ad`
- Payload SHA-256:
  `e5f87d5a2c2a9ec1f9e8cb0e0350cb81d39d70d804e67613141929b3bac4f281`
- Size: 419,939 bytes; 156 allowlisted files.
- State: the v4 archive was uploaded only to pod `q7ty5inrxx7w9r`, results were
  downloaded and verified, and the pod was deleted. No persistent volume or
  remote copy remains. The superseded v2 archive likewise existed only on its
  now-deleted owned pod.

The worker verifies package, batch, job, and spec hashes; writes append-only
progress JSONL; and atomically publishes a result. The batch runner bounds
concurrency, isolates failures, times out jobs, and resumes only unfinished jobs
whose job and bundle payload hashes still match. The controller is
provider-neutral and locally fake-tested: it binds authorization, bundle, job,
result, resource shape, per-pod token hash, lifecycle log, owned-pod cleanup,
and terminal inventory reconciliation. It makes no request without an injected
approved client.

The v4 post-approval gate verifies the immutable archive itself: archive hash,
all 156 manifest entries, payload hash, embedded batch bytes, proof jobs, and
runtime schemas. Later unrelated worktree changes cannot mutate this frozen
artifact and therefore do not invalidate an otherwise exact approval.

The independent deadline watchdog now must acknowledge its credential session,
clean owned-name inventory, authorization ID, pod name, deadline, and controller
state hash before the controller can issue a create. Its stdout/stderr are also
retained for diagnosis without recording the credential value.

## Passed v4 remote production

- Proposal: `cm-video-proof3-cpu-remote-v4`
- Pod: `q7ty5inrxx7w9r`; exact `cpu5c`, 4 vCPU, 8 GB RAM, Secure Cloud,
  30 GB container disk, zero persistent volume, pinned image digest.
- Authenticated quote: **$0.14/hour**, availability **HIGH**.
- Frozen archive, all 156 entries, payload, embedded batch, jobs, and schemas:
  **passed before create/upload**.
- Bootstrap, three serial renders, result download, and local hash validation:
  **passed**.

| Remote proof | Duration | Linux MP4 SHA-256 |
|---|---:|---|
| `cm-foundation` | 5.8 s | `c444db09c285389213c4b39a5001712ec9a091ce2aff9cb30b292b1dcf088711` |
| `explicit-cm-vs-cm-ir` | 7.0 s | `3f3e3b4b2640d83d5fd6cea88d76c07cace88eb743d248ac50e3a59ceca7c4a7` |
| `cm-ir-vs-cse-flat` | 12.9 s | `1253c1b3a59a959b1426e098d5f4d8c87aa756f1551b692d4908d2bd3e062149` |

The Linux MP4 byte hashes differ from the local Windows encodes because the
FFmpeg builds differ. The decoded visual content, timing, format contract,
payload identity, and sampled frames passed; cross-platform byte identity is
not claimed.

- Elapsed: 354.120 seconds; v4 compute estimate: **$0.013772**.
- V2 plus v4 compute estimate: **$0.021916**, excluding any later provider
  billing adjustments.
- Cleanup: delete returned HTTP 204; controller reconciliation, watchdog exit,
  and an independent postflight all verified the owned pod absent.
- Billing: the official pod-billing request returned HTTP 200 but no matching
  record yet. Billing can lag, so zero visible records is not reported as zero
  final cost.

## Reconciled v2 remote attempt

- Proposal: `cm-video-proof3-cpu-remote-v2`
- Pod: `qxb4pb4exeuzx5`; exact `cpu5c`, 4 vCPU, 8 GB RAM, Secure Cloud,
  30 GB container disk, zero persistent volume, pinned image digest.
- Authenticated quote: **$0.14/hour**, availability **HIGH**.
- Terminal result: failed before rendering because
  `ivc/schemas/orchestration_response.schema.json` was not packaged.
- Elapsed: 209.422 seconds; estimated compute cost: **$0.008145**.
- Cleanup: delete returned HTTP 204 and final owned-pod absence was verified.
- Credential handling: existing `RUNPOD_API_KEY` controller reference only;
  its value was not printed, copied, persisted, or logged, and was used only
  for authenticated requests to RunPod.

## Repository state

The CM worktree was already heavily dirty and continued receiving unrelated
live edits during this task. Source-hash guards detected those edits; the
factory was rebuilt and validated against the current bytes before this report.
All new factory artifacts are confined to `docs/video_factory`.

The shared PoP `Tools` repository started clean for `POP-Video-Creator` and
`Master-Video-Creator`; changes there are the CM renderer, portability adapter,
IVC portability/integration fixes, and their tests. The unrelated
`Artifact-To-Video` worktree was already heavily dirty and was not modified.
Nothing was staged, committed, pushed, reverted, migrated, deployed, or
published. `STATE_INVENTORY.md` records the final scoped status and diff review.

## Consumed authorization boundary

`runpod/preflight.json` now records the passed and reconciled v4 result. The v2
and v4 single-create authorizations are both consumed. V3 was invalidated
before any cloud call. No retry, replacement, or additional pod is queued or
authorized by these completed proposals.
