# CRSE Milestone D8: frozen Linux one-pass confirmation

Date: 2026-08-29

Retained run: `docs/recognition/linux_confirmation/runpod-linux-one-pass-execute-002`

Final verification: `docs/recognition/linux_confirmation/RUNPOD_LINUX_ONE_PASS_FINAL_VERIFICATION_20260829-092727-102016.json` (`complete`)

## Confirmation contract

D8 ran the unchanged 32-case D5 EPFL artifact and inert 16-row
`boolean-aig-factor-core/v2` pack on Linux under Python 3.13.15 and NumPy 2.3.2.
It compared exactly one bottom-up rewrite pass against no rewrite. Both arms paid
fresh flattened-CSE construction and 128 packed executions in each of five
deterministically randomized rounds. Complete scalar enumeration remained outside
timing and found zero semantic mismatches.

This is independent machine confirmation of the frozen policy, not new-source
generalization. The case file hash was
`ebe582d2b0e3b006dbde48e4314f7aba469e731478fdf8dbe0a5dc1aa95e9a98` and
the pack file hash was
`63393b9a7691710d4730b404bac85a9f377e5f9cd2c09047217353b9a8629915`.

## Result

| Arm | Median charged time | Speed versus no rewrite |
| --- | ---: | ---: |
| No rewrite | 314.893 ms | 1.000x |
| One pass | 338.807 ms | **0.929x** |

The one-pass policy was about **7.6% slower** than no rewrite and failed the
predeclared profitability criterion. Its case-level speedup geometric mean was
0.931x, with p05 0.831x and p95 1.065x. The exact incidence remained unchanged:
433 De Morgan applications, 18 XOR applications, and no factoring applications
in one pass.

The earlier Windows run on the same frozen cases measured 1.050x for the D7
one-pass arm. The sign reversal on Linux shows that this small advantage was not
portable. It does not contradict the older CM-versus-CSE kernel results, which
measure different task and cost boundaries; D8 specifically charges structural
matching, rewriting, CSE construction, and 128 executions.

## Runpod lifecycle

Exactly one Secure CPU pod was created: 2 vCPU, 4 GB RAM, 12 GB ephemeral disk,
zero pod/network volume, and the pinned Python image. The rate was $0.06/hour,
the conservative ten-minute projection was $0.01167, and estimated compute cost
through deletion was $0.00110. The controller deleted the pod 65.7 seconds after
creation. Final v1/v2 inventories were empty and both detail endpoints returned
404. No replacement was attempted and no credential was uploaded.

The immutable protocol and 16-file upload manifest hashes were respectively
`8d0c3fddffc512b192e8ff2cfef7f4f51ffac4f385b8688d77fe2605c5c19b04`
and `86b73c0a1dedfdb276c845e90caeae6b09c60e4ee9ffe5396cd16162d7086f27`.

## Decision

Keep the exact one-pass implementation and Linux result as validated
infrastructure and a negative profitability control. Do not promote unconditional
one-pass rewriting. The next profitability experiment must learn or derive its
gate from separate training sources, freeze environment calibration before the
evaluation slice, and test on a new natural source rather than tune against these
observed EPFL cases.
