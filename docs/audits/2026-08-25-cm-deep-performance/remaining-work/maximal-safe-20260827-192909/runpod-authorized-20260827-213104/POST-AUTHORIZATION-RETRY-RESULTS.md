# Authorized Runpod retry results — 2026-08-27

## Outcome

The explicit authorization to upload the frozen 65-file bundle was accepted. Actual provisioning requests were attempted; the smoke is still blocked by Runpod creation failure. No pod ID, worker logs, installed-wheel evidence, remote JUnit, or memory-study rows were obtained. No nontrivial computation ran locally as a fallback.

| Attempt | Actual outcome | Creation POST sent | Pod ID received |
| --- | --- | --- | --- |
| v2-execute-003 | All-CPU catalog reported no capacity; stopped in preflight | No | No |
| v2-execute-004 | Same preflight refusal | No | No |
| v2-execute-005 | Same preflight refusal | No | No |
| v2-execute-006 | HTTP 400: `globalNetworking is not supported for CPU pods; it requires an NVIDIA GPU` | Yes | No |
| v2-execute-007 | HTTP 500: `failed to create pod` | Yes | No |

The last creation request started at 16:28:29 UTC. Its outcome remains classified as uncertain in the immutable `v2-execute-007/RUN.json`; no further creation request was sent after it. The two POST payloads included only the approved 65-file source/test/lock bundle and its controller metadata, not credentials. Transmission to the provisioning API is not evidence of worker receipt or execution.

## Safety evidence as of 16:33 UTC

- Each launch controller's separate watchdog authenticated to Runpod before permitting creation. This exercised the previously missing live detached network probe.
- The corrected request's immediate finally inventory showed zero pods.
- Independent v1 and v2 inventories both showed zero pods at 16:30:09 UTC and again at 16:32:58 UTC (the latter completed 273 seconds after the creation attempt began).
- The last watchdog is intentionally still armed: PID 29136; owned name `cm-memory-smoke-5662bdbfc0de`; deadline 16:46:29 UTC / 23:46:29 Asia/Bangkok. It may recover and terminate only that exact owned pod. No automatic creation retry is scheduled.
- At this report's creation the watchdog deadline result had not yet been produced. Do not claim that the deadline check or a real pod termination has been verified. A live startup probe does not guarantee later connectivity.
- No billing history was queried. The controller's numerical zero-cost estimate is a fallback when no actual pod/rate was returned, not a verified invoice or proof of no charge.

Evidence: `POSTFLIGHT-V1-V2-20260827-163013.json`, `POSTFLIGHT-V1-V2-20260827-163302.json`, and the attempt-specific `RUN.json`, `watchdog-ready.json`, and `controller-state.json` files. Use the actual filename on disk if checking the earlier postflight timestamp.

## Controller corrections and checks

The all-CPU catalog twice reported all flavors unavailable while the documented exact-CPU endpoint returned CPU3C HIGH availability with the same `product=POD&vcpuCount=2` filters. A third paired sample reported HIGH on both endpoints. Both responses were dynamic; no cause for the disagreement was established. The preflight now queries `/v2/catalog/cpus/cpu3c` directly and rejects absent/unknown availability, wrong CPU identity, invalid vCPU bounds, insufficient RAM, and nonfinite/over-limit prices. The observed quote was $0.06/hour for 2 vCPU and 4 GB RAM.

Nine fake-client capacity/refusal cases passed. Host and remote bootstrap syntax passed. All 65 approved source hashes still matched, totaling 691,789 bytes; generated compressed bundles were 163,940 bytes. The approved workload and dependency lock were unchanged.

The CPU-incompatible `globalNetworking: false` field was removed after Runpod's explicit HTTP 400 response. No networking feature was enabled. No resource, cost, disk, image, dependency, upload, or lifetime cap was relaxed. Current controller SHA-256: `7ae4802481924826401a7ac5e76d1c513d67fc907ff542bcc3cb278088215d09`.

Checks: `CPU-DETAIL-CONTROLLER-CHECKS.json` and `RETRY-007-CONTROLLER-CHECKS.json`. Fake fixtures under `cpu-detail-unit-fixtures/` are not real Runpod observations; one intentionally contains a nonfinite price for a refusal test.

Executed controller versions were preserved as `CONTROLLER-V2-RETRY-003-005-SOURCE.py` and `CONTROLLER-V2-RETRY-006-SOURCE.py`. Existing historical reports remain snapshots of their own attempts, including the earlier upload-authorization rejection; this report records the later successful authorization and provider-side failures.

## Remaining work

The 70-test remote suite, 72 recorded representation repetitions / 312 memory-study rows, actual wheel installation, image/runtime verification, and evidence collection remain unexecuted. No estimator or production policy was accepted from these attempts. Full regression, calibration, held-out studies, corpora, and optional backends remain outside this smoke approval.

Before any future creation request, inspect the final watchdog result and freshly reconcile both pod inventories. Preserve the existing authorization and limits; do not ask for the same upload approval again. Do not infer the HTTP 500's cause from capacity alone or widen the experiment to diagnose it.

Official schema checked: [per-CPU catalog](https://docs.runpod.io/api-reference-v2/catalog/get-a-cpu-type), [pod creation](https://docs.runpod.io/api-reference-v2/pods/create-a-pod). The provider's generic HTTP 500 did not establish whether the underlying cause was account state, placement, payload handling, or another service error.
