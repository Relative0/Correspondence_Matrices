# Runpod P7 W3 final correctness continuation V7

The 15 ordinary cases in the second IR-development half completed all 60 cells.
The isolated EPFL `sqrt` case then exhausted the full 780-second stage before
its source-bound scalar oracle package was published. Pod `wtvtfqt2kamwax` was
deleted, inventories were empty, and source identity was unchanged. The oracle
generator is identical for `p7-ir` and `p7-relation`, so a relation-policy retry
of the same `sqrt` case is excluded as predictably infeasible under this study's
fixed limit. This is an oracle-feasibility exclusion, not a CM-arm failure.

V7 runs the remaining feasible partitions sequentially:

| Partition | Policy | Parent offset | Cases | Cells |
| --- | --- | ---: | ---: | ---: |
| `ir-development-square` | `p7-ir` | 33 | 1 | 4 |
| `relation-development-a` | `p7-relation` | 0 | 17 | 85 |
| `relation-development-b-light` | `p7-relation` | 17 | 15 | 75 |
| `relation-development-square` | `p7-relation` | 33 | 1 | 5 |

If these pass, W3 has verified 57/58 cases for each policy and 513/522 planned
case/arm cells. The only missing cells are the four IR and five relation arms
for the same `sqrt` case, explicitly excluded by the independent scalar oracle
limit. No timing comparison or ranking is permitted.

All uploads reuse the already authorized, already disclosed exact 96-file
bundle and V6-validated parent partitions. Resources and safety limits remain
one Secure 2-vCPU/4-GB CPU pod per partition, pinned Python 3.13.15 image,
12 GB ephemeral container storage, zero pod/network volume, 256-KiB chunks,
1,200-second lifetime, cleanup at 1,080 seconds, `$0.10` phase and `$0.20`
related-campaign guards within the standing `$5` authorization, one create per
controller, no replacement, owned deletion, and empty inventories.
