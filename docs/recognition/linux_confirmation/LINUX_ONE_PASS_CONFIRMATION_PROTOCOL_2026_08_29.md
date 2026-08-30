# Frozen Linux one-pass confirmation protocol

Status: prepared locally; cloud execution not yet authorized for this exact package.

## Scientific contract

- Cases: the unchanged 32-case D5 EPFL artifact, support 9-12, training use false.
- Rule pack: the inert 16-row `boolean-aig-factor-core/v2` proof artifact.
- Policy: exactly one bottom-up pass, then flattened CSE construction and 128
  packed executions. No rewrite is the comparator.
- Rounds: five, with deterministic randomized arm order.
- Correctness: scalar enumeration of every case outside timing; any mismatch
  invalidates the run.
- Reporting: charged rewrite/build/kernel time, five-round sequence ratio,
  case p05/p95, and per-circuit medians.
- Confirmation criterion: zero mismatches and median five-round no-rewrite time
  divided by one-pass time greater than 1.0.
- Claim boundary: cross-machine confirmation on unchanged cases, not a new-source
  generalization result.

## Proposed Runpod envelope

- One new Secure Cloud CPU pod; no replacement attempt.
- Pinned image: `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`,
  the verified amd64 image used by the successful zero-volume HTTPS campaign.
- CPU/RAM: exactly 2 vCPU and at least 4 GB RAM; no GPU.
- Storage: 12 GB ephemeral container disk, 0 GB pod volume, no network volume.
- Transport: the existing token-gated HTTPS bootstrap on ports 8080/8081.
- Package: only the hash-bound upload manifest in this directory; exclude all
  credentials, `.git`, temporary files, unrelated deliverables, and prior run outputs.
- Lifecycle: 10-minute cleanup deadline, 12-minute reconciliation horizon,
  owned-pod deletion, no automatic replacement.
- Price ceiling: $0.25/hour.
- Phase and campaign cost ceiling: **$0.05 total**, including a conservative
  storage reserve. Refuse before creation if the projected bound exceeds it.
- Network effects: Runpod API lifecycle, upload to the owned pod, bounded result
  retrieval, and owned-pod deletion only. No publication or third-party dataset fetch.

The prior structural, corpus, and zero-volume controllers are consumed and must
not be rerun. A new controller must bind an explicit authorization record to the
hash of this protocol and the generated upload manifest before one create is
allowed.
