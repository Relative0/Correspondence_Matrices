# Frozen C7 second-machine timing: single-port protocol

Status: **prepared locally; this corrected attempt is not authorized**.

## Basis and correction

The prior authorization was consumed by one pod. That pod matched its resource
envelope but returned HTTP 404 at the dual-port payload endpoint before any
source upload. It was deleted in 29.647 seconds, no replacement was requested,
both final inventories are empty, and the outcome is independently recorded as
`safe_failure_reconciled`.

This protocol uses one authenticated HTTPS ingress on port 8080 for health,
payload upload, run start, progress, and bounded result retrieval. It makes no
change to the scientific workload or 14-file package. A new explicit
authorization is required; the prior authorization cannot activate it.

## Scientific contract

- Dataset: unchanged 40-case C7 Yosys artifact, SHA-256
  `3ca1ae22fd79bac68c37e78fe497701cb100713b0077130e5263cb1f66145864`.
- Source: five external generator families pinned at Yosys-bench commit
  `52ff6fa991f2ab509618d8aaad02f307aac78848`; training use false.
- Methods: set source ANF, uncached packed source ANF, cold cached packed ANF,
  warm-stream cached packed ANF, direct big-integer truth-vector ANF, and NumPy
  truth-vector ANF.
- Timing: nine repetitions, one CPU thread, deterministic rotated method order,
  medians, p95, maxima, per-case samples, and cache telemetry.
- Correctness: independent truth checks before timing and exact canonical
  partition checks for every method and case; zero semantic mismatches required.
- Reporting: representation rankings are reported rather than assumed.

## Proposed Runpod envelope

- One new Secure Cloud CPU pod; no replacement attempt.
- Pinned image:
  `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`.
- Exactly 2 vCPU, at least 4 GB RAM, and no GPU.
- 12 GB ephemeral container disk; 0 GB pod volume; no network volume.
- One exposed HTTPS port: `8080/http`.
- Install only the binary wheel
  `numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f`
  with pip `--require-hashes`.
- Upload only the unchanged 14 hash-bound files totaling 322,080 source bytes
  in `c7_linux_upload_manifest.json`.
- Retrieve at most 16 MiB of runtime records, logs, measurements, per-case
  results, summary, and artifact manifest.
- Ten-minute cleanup deadline and twelve-minute reconciliation horizon.
- $0.25/hour rate ceiling and **$0.05 total cost ceiling**.
- Runpod lifecycle calls, the one pinned NumPy wheel fetch, bounded upload and
  retrieval, and owned-pod deletion only. No dataset fetch or publication.

The controller must bind a separately created authorization record to this
protocol hash and the unchanged package-manifest hash before any create request.
