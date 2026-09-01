# Runpod P7 W5 principal development campaign

Date: 2026-09-01
Status: authorized by Brian's instruction to commit W4 and continue W5, under
the standing $5 Runpod campaign and failed-run/rerun authorization

## Purpose

Run the frozen full P7A/P7B development ablation after W3 correctness and W4
resource/noise gates. This is developmental performance evidence; the W8
LogikBench confirmation cohort remains untouched.

## Frozen workload

- Parent V4 freeze SHA-256:
  `54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd`.
- Reuse the exact previously authorized 96-file private source/test bundle:
  manifest SHA-256
  `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`,
  bundle SHA-256
  `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
- Install only the existing 13 hash-locked binary wheels.
- Retain the W3 `development-epfl-sqrt-31cdaf5d0213` typed feasibility
  exclusion. Its policy-independent oracle generation exceeded 780 seconds;
  it is a recorded non-success in completion/frontier reporting and is not
  retried inside a 20-minute W5 allocation.
- Partition the remaining 57 independent cases 29/28 within frozen role and
  source-kind strata using SHA-256(case ID), without consulting comparative
  timing.
- Run IR at the frozen 8-block minimum: 928 and 896 primary cells.
- Apply W4's predeclared 5% noise rule and run relation at the frozen 20-block
  maximum: 2,900 and 2,800 primary cells.
- Run the same separately labeled two-case synthetic/natural diagnostic anchor
  in every allocation: 64 cells on IR pods and 100 cells on relation pods.
  Anchor rows are not counted as independent primary formulas.
- Total: 7,524 primary cells and 7,852 cells including repeated diagnostics.

## Allocation and transport limits

- Four sequential creates, one immutable shard per controller invocation.
- One Secure 2-vCPU CPU pod per shard, at least 4 GB RAM.
- Pinned Python 3.13.15 amd64 image and exactly two admitted CPUs.
- 12 GB container storage, zero pod volume, zero network volume.
- HTTP-only bounded 256-KiB resumable upload chunks.
- 20-minute hard lifetime, controller cleanup at 18 minutes.
- $0.10 cap for each shard and $5 attributable campaign cap.
- No source builds and no system-package installation.
- One create per controller. A failed run may be repeated only with a fresh
  run identity under Brian's standing rerun authorization; never create a
  replacement inside the same controller.
- Exclusive sequential launch ownership, identity-bound cleanup, empty
  inventory preflight, watchdog acknowledgement before POST, and final
  inventory/billing reconciliation.

## Acceptance gates

Every planned cell must be terminal and `ok`, match its independent oracle,
retain full-output semantics, use a unique fresh worker process, preserve source
hashes, and pass retrieved plan/ledger/checksum verification. The typed W3
feasibility exclusion remains visible. Diagnostic anchors are analyzed only for
between-allocation drift. No confirmation claim or CM-vs-external-method claim
is permitted from W5.
