# Runpod P7 W3 final development-tail partitions V6

The V5 17-case `ir-development-b` partition passed all 42 focused tests and the
offline package gate but again exhausted its 780-second oracle/runner stage.
Its source remained unchanged, pod `dop3aggj7vsefp` was deleted, and both
inventories were empty. This proves the second 17-case half still needs finer
functional partitioning; it is not a correctness failure.

V6 retains the already successful IR prefix of 17 cases and partitions the
remaining parent-order tail into 15 ordinary cases plus the EPFL `sqrt` and
`square` cases individually. Relation development uses the same boundaries,
including its previously unexecuted 17-case prefix. The seven sequential
partitions are:

| Partition | Policy | Offset | Cases | Cells |
| --- | --- | ---: | ---: | ---: |
| `ir-development-b-light` | `p7-ir` | 17 | 15 | 60 |
| `ir-development-sqrt` | `p7-ir` | 32 | 1 | 4 |
| `ir-development-square` | `p7-ir` | 33 | 1 | 4 |
| `relation-development-a` | `p7-relation` | 0 | 17 | 85 |
| `relation-development-b-light` | `p7-relation` | 17 | 15 | 75 |
| `relation-development-sqrt` | `p7-relation` | 32 | 1 | 5 |
| `relation-development-square` | `p7-relation` | 33 | 1 | 5 |

Offline validation requires pairwise-disjoint partitions and exact union with
all 34 parent development cases per policy when combined with the completed IR
prefix. On-pod derived freezes retain parent/source identities and permit only
functional correctness claims; performance timing and ranking remain forbidden.

Each partition reuses the already authorized, disclosed exact 96-file bundle
(manifest SHA-256 `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`,
bundle SHA-256 `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`),
runs the 42 focused tests and offline gate, and uses one Secure 2-vCPU/4-GB CPU
pod with the pinned image, 12 GB ephemeral container storage, zero pod/network
volume, 256-KiB chunks, a 1,200-second lifetime, cleanup at 1,080 seconds,
`$0.10` per-phase and `$0.20` related-campaign guards inside the standing `$5`
authorization, one create per controller, no replacement, owned deletion, and
mandatory empty inventories.
