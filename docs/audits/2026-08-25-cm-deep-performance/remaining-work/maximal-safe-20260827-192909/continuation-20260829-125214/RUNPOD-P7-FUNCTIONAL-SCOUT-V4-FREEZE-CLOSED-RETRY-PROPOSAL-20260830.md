# RunPod P7 functional scout V4 all-freeze-source retry proposal

## Purpose

Complete the non-performance P7 functional scout after two fail-closed package
audits. V1 stopped at collection because direct Python dependencies were absent.
V3 passed all focused tests but stopped when the immutable offline verifier found
that not every frozen case source was present. Neither attempt executed a P7 cell
or supports a performance claim. Both pods are deleted.

## Frozen package and workload

- Manifest-bound 212-file/24,705,826-byte source/data package, manifest SHA-256
  `490ff60e5f7d0ad3545d16b9d72ea84a39e3549e27952741683edbac131017c1`.
- Immutable 4,203,964-byte ZIP, SHA-256
  `cc75275cff77a52f319fbd5713d03faff8fa26cb0887b3df8e5a83728e70a352`.
- All 152 original payloads remain byte-identical. The added payloads are direct
  runtime dependencies and every source identity referenced by the frozen P6 V4
  corpus, including confirmation and regression CNFs.
- An isolated extracted-tree gate passes all 32 focused tests plus 16 subtests.
- The immutable P7 offline verifier passes checksums, execution readiness, dry
  run, source manifest identity, and the no-performance-measurement assertion.
- Run two development cases and two blocks for `p7-ir` (16 cells) and
  `p7-relation` (20 cells). All 36 cells use fresh supervised process groups and
  must exactly match the scalar oracle calculated outside the timed span.
- This remains a functional scout. Performance measurement and ranking are
  prohibited.

## Resources, cost and cleanup

Use one secure 2-vCPU/4-GB CPU pod, pinned Python 3.13.15 image, 12 GB ephemeral
container disk, zero pod volume, and no network volume. Hard lifetime is 1,200
seconds with forced cleanup at 1,080 seconds. Phase cost must remain below $0.10
and all related work below the user's $1 cap. One create is allowed in this
controller; deletion and empty v1/v2 inventories are mandatory on every outcome.
