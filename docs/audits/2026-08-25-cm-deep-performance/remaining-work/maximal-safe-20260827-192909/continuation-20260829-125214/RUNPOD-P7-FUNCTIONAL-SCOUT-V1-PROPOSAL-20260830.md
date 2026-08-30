# RunPod P7 Linux isolated-cell functional scout V1 proposal

## Purpose

Validate the new P7 isolated-cell runner on Linux before any comparative timing
campaign. This is a functional exactness, supervision, resume-format and evidence
closure scout. It cannot support a performance ranking.

## Frozen package and workload

- Manifest-bound 152-file/11,224,621-byte source/data package, manifest SHA-256
  `fa9e5bf67778412a9e5ebfcc145f378787929d45409fea49d5ade62706170d90`.
- Immutable 1,745,617-byte transport ZIP, SHA-256
  `b57838452a590b89018c1e9dee77fb31b30d2e0931b739da97797ab1a7ca7076`.
- The immutable P6 V4 freeze and P7 offline-gate V4 package must verify in the pod.
- All 32 focused runner, corpus, BLIF and Linux-supervisor tests must pass without
  failure, error or skip.
- Two frozen development cases and two blocks for each policy:
  - `p7-ir`: four arms, 16 isolated cells.
  - `p7-relation`: five arms, 20 isolated cells.
- Every one of the 36 cells runs in a distinct owned process group with bounded
  input/output, deadline, process count and sampled process-tree RSS.
- Every result must match the independently calculated scalar oracle outside the
  timed span. Cleanup, streams, positive primary metrics, source identity and all
  runner checksums must verify.
- Both runner profiles remain `functional`; `performance_measurement` and
  `performance_claim_permitted` must remain false.

## Resources, cost and cleanup

Use one secure 2-vCPU/4-GB CPU pod, pinned Python 3.13.15 amd64 image, 12 GB
ephemeral container disk, zero pod volume and no network volume. The lifetime is
bounded to 1,200 seconds with controller/watchdog cleanup at 1,080 seconds.
Projected phase cost must remain below $0.10 and aggregate campaign cost below the
user's $10 cap. Pod `du48i5xcu9f6rw` and all earlier owned pods must be absent
before creation. One create is permitted; deletion and empty v1/v2 inventories are
mandatory on every outcome.

