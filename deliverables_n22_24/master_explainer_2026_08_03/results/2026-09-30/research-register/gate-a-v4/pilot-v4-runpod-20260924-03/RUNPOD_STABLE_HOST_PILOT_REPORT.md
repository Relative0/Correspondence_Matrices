# Runpod stable-host pilot report — `pilot-v4-runpod-20260924-03`

## Decision

**Gate A remains NO-GO.** The one authorized exploratory Runpod pilot completed, but the unchanged Protocol v4 repeatability rule failed: 194 of 200 case/arm controls passed and 6 failed. Equality at the frozen 0.05 limit would have passed; no limit was relaxed, no outlier was removed, and no case or pilot was rerun.

This was exploratory only. No confirmatory result was run or inspected. No confirmatory, memory, secondary-performance, or natural-pairability schedule ran, and no relative arm speed or favorable-case result was calculated or reported.

## Prespecified stability result

| Arm | Passed | Failed | Maximum MAD/median |
|---|---:|---:|---:|
| `cm_pure` | 96 | 4 | 0.23801345992583745 |
| `direct_packed` | 98 | 2 | 0.2105232640339576 |
| **Total** | **194** | **6** | **0.23801345992583745** |

- Timer-overhead failures: 0.
- Recorded worker affinity: CPU 0.
- Recorded worker nice value: 0; elevated priority was not claimed.
- The untouched pilot used the frozen 100 primary cases, both arms, 11 repetitions, one fresh process per observation, one timed API call, and the unchanged 0.05/0.01 limits.

The permitted summary is `remote_evidence/pilot_control_summary_runpod.json`. The raw exploratory JSON and stdout are retained but were not opened for this report.

## Host and execution record

- Pod: `8v6runmuak40ow`; Secure Cloud; data center `CA-MTL-1`; NVIDIA A40 offer; advertised 9 vCPUs, 50 GB RAM, 20 GB ephemeral container disk, zero persistent volume; `$0.49/hour`.
- Image tag: `runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404`. An immutable digest was not successfully captured for this pod; the failed final CLI capture is retained rather than silently replaced.
- CPU-resource dedication: unknown. The container exposed 96 logical CPUs on two 24-core/48-thread sockets, while the Runpod offer advertised 9 vCPUs.
- Observed CPU: Intel Xeon Gold 6342, 2 sockets, 48 physical cores/96 threads, two NUMA nodes, `schedutil` governor, 800–3500 MHz range, TSC clocksource.
- OS/runtime: Ubuntu 24.04.3 LTS container, Linux 6.8.0-52-generic, Docker/cgroup v1, overlay filesystem, UTC, `C.UTF-8`.
- Initial host load was 10.27/14.37/17.28; CPU pressure `some` was 0.61/1.18/5.65 and `full` was zero. These facts and the shared/dedication ambiguity are candidate explanations for instability, not post-hoc reasons to waive failures.
- Clean venv: Python 3.12; NumPy 2.3.2 wheel SHA-256 `8145dd6d10df13c559d1e4314df29695613575183fa2e2d11fac4c208c8a1f73`.
- Measurement start/end: `2026-09-24T13:52:04Z` to `2026-09-24T13:57:14Z`.
- The untimed smoke check passed source/import/writeability/oracle equality with affinity `[0]`, nice `0`, and no elapsed timing recorded.

## Integrity, transfer, and lifecycle

- Gate A package SHA-256: `93c556a4c15099c260919287e95809079bf8d5ff21b8117e4155fd0482a7306a`; matched after SSH staging.
- Scoped transfer payload SHA-256: `967efe93dc18ef324e8fdca23312fbd107d3e3feb9c29d84078a2031400feed5`; local and remote hashes matched.
- Staged deliverable verification: 68 entries, zero failures.
- Audited source closure: 187 files, zero failures.
- Retained exploratory result SHA-256: `b0c7602c638264897bf68bf2a6ef6bb1dfd04dc5c26224ff0b405b5c3c26af6a`.
- Retrieved evidence archive SHA-256: `969c2b54ed471457e7bdf464e179589b96ca3a1b3117eced9c9fc160d6d58fbf`; expected and downloaded hashes matched.
- Twenty-two non-manifest evidence files verified against the remote inventory with zero failures. The manifest's self-entry was excluded because shell redirection created the manifest before enumeration, so its recorded self-hash describes the initially empty file; this is documented in `remote_evidence_manifest_verification.json`.
- Pod `8v6runmuak40ow` was deleted and confirmed absent from the active list. The task-only Runpod SSH key was revoked and all local private/public key and known-host artifacts were deleted; only non-secret key metadata remains.
- The scoped post-termination billing query returned `[]`. Exact provider cost is therefore pending/unavailable and is not inferred from the advertised hourly rate. Billing has stopped because the pod was deleted.

## Retained setup failures

All earlier Runpod failures remain in their original pilot directories: two Secure Cloud supply constraints (`20260923-01` and `-02`); an allocated L4 whose receiver never became reachable (`20260924-01`); and the `20260924-02` shell/image/utility incompatibilities plus public-relay `room not ready` failures. In this identity, L4 pod `rcsex8h7dif0r0` was terminated when a `sleep infinity` override prevented SSH startup; no transfer or pilot ran on it. None of these setup attempts was treated as a stability result.

## Smallest valid next step

Do not run another unchanged v4 paid-pod pilot or any confirmatory work. The repeated failures now include a completed Runpod host despite correct staging, smoke correctness, affinity, and timer overhead. Draft and review Protocol v5 prospectively with a robust per-observation timing unit that preserves arm-specific preparation, independent reconstruction/cache reset, and fresh-process isolation. Only after the estimand, schema, runner, analyzer, schedules, manuscript language, and adversarial tests are frozen should a new `pilot-*` identity be collected.
