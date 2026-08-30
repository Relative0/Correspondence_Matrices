# Runpod P7 W3 relation-regression continuation V3

## Reason for the amendment

The V2 `ir-development` shard passed 42 focused tests and the offline package
gate, but its full 34-case oracle construction did not finish inside the frozen
780-second command cap. Pod `alu08d0mlf02ba` was deleted, both inventories were
empty, the source remained unchanged, and the attempt cost estimate was
recorded. This is a sizing failure and supplies no correctness result for that
partition.

The independent 24-case `relation-regression` shard does not depend on a result
from the development partition. V3 therefore reconciles the timeout and its
cost, preserves it as failed evidence, and continues only this smaller frozen
partition. It does not retry or replace the failed development workload.

## Frozen work and limits

Upload the already authorized, already disclosed exact 96-file bundle with
manifest SHA-256
`9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`
and bundle SHA-256
`83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
Run the 42 focused tests, offline gate, and exactly the 24 regression cases of
`p7-relation`: 120 case/arm cells, one fresh process per cell, one block,
functional profile, and no performance ranking.

Use one Secure 2-vCPU/4-GB CPU pod, the pinned Python 3.13.15 amd64 image,
12 GB ephemeral container storage, zero pod volume, no network volume, a
1,200-second hard lifetime, cleanup at 1,080 seconds, a `$0.10` phase cap and
the existing `$0.20` related-campaign cap inside the standing `$5` ceiling.
There is no replacement inside this controller. Owned deletion and empty v1/v2
inventories are mandatory.
