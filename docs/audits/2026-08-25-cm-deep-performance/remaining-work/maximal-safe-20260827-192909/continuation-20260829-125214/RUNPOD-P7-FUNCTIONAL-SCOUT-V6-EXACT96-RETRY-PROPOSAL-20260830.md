# Runpod P7 functional scout V6 exact-96 transport-fix retry proposal

## Purpose

Complete the reviewed, non-performance 36-cell P7 functional scout using the
same exact private 96-file payload the user explicitly authorized. The prior V2
create validated the requested pod but failed locally before upload because its
preflight module did not export `PRIOR_HTTP_RESERVE`; the controller deleted the
pod within six seconds and both inventories were empty. This retry changes only
the local preflight/controller binding and uses a new output identity.

## Frozen payload and workload

- Manifest: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json`.
- Manifest SHA-256: `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`.
- Exactly 96 files and 19,484,163 uncompressed source/test bytes.
- Bundle SHA-256: `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
- Bundle size: 3,197,013 bytes.
- All 42 focused tests and the immutable offline gate must pass.
- Run 16 `p7-ir` and 20 `p7-relation` functional cells in 36 fresh supervised
  process groups. Exact scalar-oracle agreement, source identity, resource
  cleanup, complete ledgers, and all runner checksums are mandatory.
- Performance measurement and ranking remain prohibited.

## Reconciled related attempts

- V1 `1xh6csc4oxy067`: dependency-closure failure; deleted.
- V2 `r044pqp2vgp7cy`: local missing-export failure before source upload; deleted.
- V3 `2fzt8mu6ji6nmw`: a different 156-file package passed focused tests but its
  offline freeze check failed; evidence retrieved and pod deleted.
- V4 freeze-closed: refused at preflight because another owned create was live;
  it sent no create request and uploaded nothing.

## Resources, budget, and cleanup

Use one Secure 2-vCPU/4-GB CPU pod with the pinned Python 3.13.15 amd64 image,
12 GB ephemeral container storage, zero pod volume, and no network volume. Hard
lifetime is 1,200 seconds with controller/watchdog cleanup at 1,080 seconds.
This controller retains the stricter `$0.10` phase and `$0.20` related-campaign
caps inside the user's standing `$5` incremental campaign ceiling. The V2
unpriced six-second pod is conservatively charged as one minute. One create is
allowed in this controller, with no replacement; owned deletion and empty v1/v2
inventories are required on every outcome.
