# Frozen C7 second-machine timing protocol

Status: **prepared locally; cloud execution not yet authorized for this exact package**.

## Scientific contract

- Dataset: the unchanged 40-case C7 Yosys artifact with SHA-256
  `3ca1ae22fd79bac68c37e78fe497701cb100713b0077130e5263cb1f66145864`.
- Source: five external `YosysHQ/yosys-bench` generator families pinned at
  commit `52ff6fa991f2ab509618d8aaad02f307aac78848`; training use is false.
- Methods: set source ANF, uncached packed source ANF, cold cached packed ANF,
  warm-stream cached packed ANF, direct big-integer truth-vector ANF, and NumPy
  truth-vector ANF.
- Timing: nine repetitions, one CPU thread, deterministic rotated method order,
  with medians, p95, maxima, per-case samples, and cold/warm cache telemetry.
- Correctness: independent NumPy and direct-bitset truth checks before timing;
  canonical exact partition checks for every measured method and case.
- Reporting: ranking preservation is reported, not required for validity. Zero
  semantic mismatches is required.
- Claim boundary: second-machine timing of the unchanged sealed C7 cases, not a
  new-source generalization result and not a production promotion.

## Proposed Runpod envelope

- One new Secure Cloud CPU pod; no replacement attempt.
- Pinned image:
  `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`.
- CPU/RAM: exactly 2 vCPU and at least 4 GB RAM; no GPU.
- Storage: 12 GB ephemeral container disk, 0 GB pod volume, no network volume.
- Setup dependency: install only
  `numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f`
  as a binary wheel with pip `--require-hashes`.
- Transport: token-gated HTTPS bootstrap on ports 8080/8081.
- Package: exactly 14 hash-bound files totaling 322,080 source bytes, as listed
  in `c7_linux_upload_manifest.json`; exclude credentials, `.git`, the source
  checkout, temporary files, unrelated deliverables, and prior outputs.
- Results: bounded to 16 MiB and limited to runtime/dependency records, logs,
  measurements, per-case results, summary, and artifact manifest.
- Lifecycle: 10-minute cleanup deadline, 12-minute reconciliation horizon,
  owned-pod deletion, and no automatic replacement.
- Price ceiling: $0.25/hour.
- Total cost ceiling: **$0.05**, including a conservative storage reserve.
  Refuse before creation if the projected ten-minute bound exceeds it.
- Network effects: Runpod lifecycle calls, upload to the owned pod, the single
  pinned NumPy wheel fetch during setup, bounded result retrieval, and owned-pod
  deletion. No publication or external dataset fetch.

The controller must bind a new explicit authorization record to the SHA-256 of
this protocol and the upload manifest before one create request is allowed.
