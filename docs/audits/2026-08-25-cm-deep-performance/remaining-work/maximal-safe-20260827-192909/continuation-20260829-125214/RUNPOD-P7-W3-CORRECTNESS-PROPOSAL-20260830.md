# Runpod P7 W3 full correctness/oracle scout proposal

## Purpose

Execute the execution plan's full non-performance W3 gate after the exact-96
Linux functional scout passed. This run covers every one of the 58 P7-eligible
regression/development cases and every applicable frozen P7 arm once. It sizes a
later timing proposal but does not rank arms or support a performance claim.

## Frozen payload

- Reuse the exact 96-file private payload already explicitly authorized and
  disclosed to Runpod.
- Manifest: `RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json`.
- Manifest SHA-256: `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`.
- Exactly 19,484,163 uncompressed source/test bytes.
- Bundle SHA-256: `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
- Bundle size: 3,197,013 bytes.

## Frozen workload and success gate

- Verify all package/source checksums and run all 42 focused tests.
- Generate source-bound independent oracle records for all 58 cases.
- `p7-ir`: 58 cases x one block x four arms = 232 isolated cells.
- `p7-relation`: 58 cases x one block x five arms = 290 isolated cells.
- Total: 522 cells and 522 fresh supervised process groups.
- Require exact oracle equality, complete ledgers, unique worker processes,
  unchanged source, bounded output, positive coarse resource observations, and
  verifier success.
- Retain typed failures. A semantic mismatch fails the run.
- Record only coarse run/resource information for later sizing.
- `performance_measurement=false`; no arm ratios, rankings, or comparative
  performance conclusions are permitted.

## Resources, budget, and cleanup

Use one Secure 2-vCPU/4-GB CPU pod with the pinned Python 3.13.15 amd64 image,
12 GB ephemeral container storage, zero pod volume, and no network volume. Hard
lifetime is 1,200 seconds with controller/watchdog cleanup at 1,080 seconds.
The controller retains the stricter `$0.10` phase and `$0.20` related-campaign
caps inside the user's standing `$5` incremental campaign ceiling. One create
is allowed, with no replacement inside this controller. The exact-96 functional
gate, its independent audit, live empty inventory, current offer, and current
budget must all revalidate immediately before create. Owned deletion, 404 detail
checks, and empty v1/v2 inventories are required after the run.
