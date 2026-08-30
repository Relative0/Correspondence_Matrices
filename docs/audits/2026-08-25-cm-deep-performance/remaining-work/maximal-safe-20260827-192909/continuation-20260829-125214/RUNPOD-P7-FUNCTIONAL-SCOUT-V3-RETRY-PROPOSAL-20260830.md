# RunPod P7 Linux isolated-cell functional scout V3 retry proposal

## Purpose

Retry the functional exactness and process-isolation scout after the V1 pod
correctly failed closed at test collection. V1 identified an upload dependency-
closure defect; it did not execute any P7 cells and made no performance claim.

## Reconciled V1 outcome

- Pod `1xh6csc4oxy067` returned three collection errors because the 152-file
  package omitted `cmbench/recognition/features.py`.
- The retrieved source remained unchanged, the controller deleted the pod, and
  both RunPod inventories are empty.
- Estimated V1 compute cost is $0.002207883052031199.
- Isolated local closure gates subsequently found and added the development
  JSONL referenced by the frozen plan and the bitset-engine package imported by
  complete-relation execution. The final package passes all 32 focused tests
  (plus 16 subtests) from an extracted temporary tree.

## Frozen corrected package and workload

- Manifest-bound 156-file/11,591,021-byte source/data package, manifest SHA-256
  `8bdcd14cdbb6116519a0ab2198c9b90acc2dcf5d8ed8830a536090e33c8ead6a`.
- Immutable 1,731,976-byte transport ZIP, SHA-256
  `3f4ae4ad709b029ebedf6b8cab8d4f359f40bf741ae9e3280f4d97a7a0660b17`.
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
- Both profiles remain functional; performance measurement and ranking remain
  prohibited.

## Resources, cost and cleanup

Use one secure 2-vCPU/4-GB CPU pod, pinned Python 3.13.15 amd64 image, 12 GB
ephemeral container disk, zero pod volume and no network volume. The lifetime is
bounded to 1,200 seconds with controller/watchdog cleanup at 1,080 seconds.
Projected retry cost must remain below $0.10 and related RunPod work below the
user's newer $1 cap. All earlier owned pods must be absent before creation. One
retry create is permitted; deletion and empty v1/v2 inventories are mandatory on
every outcome.
