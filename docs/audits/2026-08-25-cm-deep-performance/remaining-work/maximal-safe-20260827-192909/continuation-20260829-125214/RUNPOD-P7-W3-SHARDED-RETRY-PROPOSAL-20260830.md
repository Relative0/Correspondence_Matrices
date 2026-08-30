# Runpod P7 W3 four-shard correctness retry proposal

## Reason for sharding

The one-pod W3 attempt passed 42 focused tests and the offline freeze gate, but
its 232-cell IR command reached the frozen 600-second stage timeout before a
final ledger was published. Source remained unchanged, no relation cell ran,
the owned pod was deleted, and both inventories were empty. This is a workload
sizing failure, not a semantic mismatch.

Retry the unchanged W3 correctness workload as four sequential immutable shards:

| Shard | Policy | Role | Cases | Cells |
| --- | --- | --- | ---: | ---: |
| `ir-regression` | `p7-ir` | regression | 24 | 96 |
| `ir-development` | `p7-ir` | development | 34 | 136 |
| `relation-regression` | `p7-relation` | regression | 24 | 120 |
| `relation-development` | `p7-relation` | development | 34 | 170 |

The four complete ledgers total the original 58 cases per policy and 522 cells.
Each shard has a 780-second worker-stage cap inside a 1,200-second pod lifetime.
Shards run sequentially and a later shard cannot preflight until every earlier
shard is complete, verified, deleted, and cost-reconciled.

## Frozen payload and scientific contract

Reuse the exact 96-file private payload already explicitly authorized and
disclosed to Runpod: manifest SHA-256
`9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`
and bundle SHA-256
`83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
Every shard re-verifies all 42 focused tests, the offline freeze, source hashes,
independent case oracles, complete ledgers, unique fresh worker processes, and
cleanup. Performance measurement and ranking remain prohibited.

## Resources, budget, and cleanup

Authorize exactly four sequential creates, one per named shard, with no
replacement inside any shard controller. Each uses one Secure 2-vCPU/4-GB CPU
pod, the pinned Python 3.13.15 amd64 image, 12 GB ephemeral container storage,
zero pod volume, no network volume, a 1,200-second hard lifetime, and cleanup at
1,080 seconds. Each shard retains the `$0.10` phase and `$0.20` related-campaign
checks inside the user's standing `$5` incremental ceiling. Ownership-only
deletion and empty v1/v2 inventories are mandatory after every shard.
