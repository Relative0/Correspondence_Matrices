# Runpod P7 W3 bounded development partitions V4

## Reason and scientific contract

The 34-case `ir-development` command exhausted its 780-second stage cap while
constructing its oracle package. It produced no semantic result, left the
uploaded source unchanged, and its owned pod was deleted. The successful
24-case regression shards show that transport, focused tests, offline freeze
gate, fresh-process isolation, evidence retrieval, and cleanup work correctly.

V4 completes functional correctness coverage by dividing each 34-case
development role into two deterministic 17-case partitions. The partition case
IDs come from the parent freeze's realized policy order, at offsets 0 and 17.
On the pod, the remote program derives a functional subset freeze containing
only those cases and the one relevant policy, rebuilds its order ledger with the
existing frozen scheduling function, hashes and validates the derived freeze,
and records the parent/derived identities and selected case IDs. No source file
is modified. Because every functional block executes every arm, order changes
inside a derived subset do not change case/arm coverage. These results permit
correctness claims only; timing comparison and ranking remain prohibited.

| Partition | Policy | Parent offset | Cases | Cells |
| --- | --- | ---: | ---: | ---: |
| `ir-development-a` | `p7-ir` | 0 | 17 | 68 |
| `ir-development-b` | `p7-ir` | 17 | 17 | 68 |
| `relation-development-a` | `p7-relation` | 0 | 17 | 85 |
| `relation-development-b` | `p7-relation` | 17 | 17 | 85 |

The four partitions are sequential. Each later preflight requires all earlier
partitions complete, verified, deleted, and cost-reconciled. Combined with the
successful regression shards, the case-ID unions must reproduce all 58 parent
cases for both policies, with 522 total fresh-process cells.

## Payload, resources, budget, and cleanup

Each partition uploads the already authorized, already disclosed exact 96-file
bundle with manifest SHA-256
`9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`
and bundle SHA-256
`83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
Each runs 42 focused tests, the original offline package gate, and one bounded
functional partition using one Secure 2-vCPU/4-GB CPU pod, the pinned Python
3.13.15 amd64 image, 12 GB ephemeral container storage, zero pod volume, no
network volume, a 1,200-second lifetime, cleanup at 1,080 seconds, a `$0.10`
phase cap, and the existing `$0.20` related-campaign cap inside the standing
`$5` ceiling. Each controller permits one create and no replacement. Owned
deletion and empty v1/v2 inventories are mandatory.
