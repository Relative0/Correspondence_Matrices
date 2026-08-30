# Runpod P7 W3 four-shard correctness retry V2 proposal

## Reconciled transport correction

The first V1 `ir-regression` shard created pod `pnpc0c0t6gu358`, validated its
resources, and then failed closed before source upload because the signed
transport environment contained a fifth key while the pinned bootstrap permits
exactly four. The controller deleted the pod after 51 seconds; zero source files
were uploaded and both inventories were empty. The other three V1 shard
authorizations were never used.

V2 keeps the pinned bootstrap byte-identical. It removes the extra environment
key and binds each shard identity in one of four immutable remote-program files.
The source bundle, manifest, tests, cases, arms, roles, cell counts, scientific
contract, resource request, deadlines, and cost caps do not change.

## Four sequential shards

| Shard | Policy | Role | Cases | Cells |
| --- | --- | --- | ---: | ---: |
| `ir-regression` | `p7-ir` | regression | 24 | 96 |
| `ir-development` | `p7-ir` | development | 34 | 136 |
| `relation-regression` | `p7-relation` | regression | 24 | 120 |
| `relation-development` | `p7-relation` | development | 34 | 170 |

Each shard uses one fresh pod, runs all 42 focused tests and the offline gate,
then runs only its named role/policy ledger with a 780-second stage cap. Later
shards require every prior V2 shard to be complete, verified, deleted, and
cost-reconciled. The four ledgers must total 58 cases per policy and 522 unique
fresh worker processes. Performance measurement and ranking remain prohibited.

## Payload, resources, budget, and cleanup

Reuse the already authorized and disclosed exact 96-file payload: manifest
SHA-256 `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`
and bundle SHA-256
`83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
Authorize four sequential creates, one per named V2 shard, with no replacement
inside any controller. Each uses one Secure 2-vCPU/4-GB CPU pod, the pinned
Python 3.13.15 amd64 image, 12 GB ephemeral container storage, zero pod volume,
no network volume, 1,200-second hard lifetime, and cleanup at 1,080 seconds.
Each retains the `$0.10` phase and `$0.20` related-campaign checks inside the
standing `$5` ceiling. Owned deletion and empty inventories are mandatory.
