# P7 W5 final incomplete closure

Date: 2026-09-03
Status: **closed as an incomplete historical campaign**

This record closes P7 W5 without running its three remaining frozen shards.
It does not alter the contemporaneous interim status or the successful IR-A
evidence.

## Admissible historical evidence

The completed `p7-ir-a` shard remains admissible for the exact frozen source
that it executed:

- 928/928 primary cells and 64/64 anchor cells completed;
- 992 fresh workers were observed;
- archive SHA-256:
  `6d9a288000349563929b472daec08245d06acc5d39221e81af58bfda6b52a87b`;
- estimated charge: `$0.0058755`;
- the owned pod was deleted and final inventories were empty.

The source-bound details remain in
`RUNPOD-P7-W5-INTERIM-STATUS-20260901.md` (SHA-256
`66e02cbf6e9636b2d2bccb0046eb0f9c6385d1bfa7c7095fe82aa5098f08a55f`).

## Unrun shards

The following shards are permanently recorded as not run:

- `p7-ir-b`;
- `p7-relation-a`;
- `p7-relation-b`.

They must not be resumed under the old W5 authorization or presented as a
complete W5 campaign.

## Why the campaign is closed

The W5 upload manifest (SHA-256
`9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`)
no longer represents current source. A bounded reconciliation found these
three changed package inputs:

| Path | Frozen bytes / SHA-256 | Current bytes / SHA-256 |
|---|---|---|
| `bitset_backend.py` | 37,979 / `06a9a24a0bc1e579840d0349803353c08b86f7dd15bc7f9bad7d557d9f0c9cdf` | 38,464 / `4b80a27fa4de67bf35fb13d76ea9d6cd679bfb6dafc8b554741f4987c49bcbdc` |
| `cm_exprlib.py` | 5,626 / `a11937d372b13b5e06e07422edabe0b16c76d17f29c7c27f3109b5f44a97c040` | 5,923 / `2dae42d07256c8f6b01a4ef054cc35658544607c0338f5a4a8dac76629fbdac1` |
| `cmbench/comparative/contracts.py` | 12,011 / `589fad08a3da43a7154a00c3cd1dac38c31239892b15ee11a1c7726811893a89` | 12,119 / `11b9a54ac3d5ebbe871c49180319ff12eca5ee627ed08c6149a6889f2c8510e0` |

Running only the remaining frozen shards would answer a historical-source
question, leave W5 permanently asymmetric, and still not refresh the current
CM/BitSet/CSE comparison. That spend is not scientifically justified.

## Decision boundary

- No combined W5 timing table or method decision is permitted.
- IR-A may be cited only as partial historical evidence with its frozen-source
  identity.
- The current-source four-lane comparison is a new campaign and requires its
  own freeze and authorization.
- No cloud resource was created, changed, or charged by this closure.
