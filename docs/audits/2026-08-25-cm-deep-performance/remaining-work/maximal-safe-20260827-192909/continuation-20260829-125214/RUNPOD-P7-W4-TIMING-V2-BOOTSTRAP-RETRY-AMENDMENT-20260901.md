# P7 W4 timing scout: V2 bootstrap-compatibility retry amendment

Date: 2026-09-01  
Status: exact retry scope under the standing failed-run authorization

## Preserved failed attempt

The original W4 controller created pod `fixszqtou7pal8` at the exact approved
2-vCPU/4-GB/$0.06-per-hour/12-GB-container/zero-volume resources. The bounded
transport accepted 4,194,304 of 4,314,433 encoded payload bytes, then returned
HTTP 400 while validating the final chunk. No source archive was extracted and
no tests or benchmark cells ran. The controller deleted the owned pod with HTTP
204; both Runpod inventories were empty afterward. Estimated compute cost was
`$0.000998864511648814`.

The exact defect is local and reproduced offline: the frozen W4 client includes
both `CM_SETUP_DEADLINE` and `CM_EXECUTION_DEADLINE`; bootstrap V2 allowed only
the setup deadline even though the frozen W4 remote program consumes the
execution deadline. The complete payload therefore failed its environment-key
allowlist after the first sixteen chunks were acknowledged.

## Only compatibility change

Preserve bootstrap V2. Create bootstrap V3 by adding exactly
`CM_EXECUTION_DEADLINE` to the payload environment allowlist. Do not change the
uploaded source/test bundle, remote benchmark program, cases, arms, schedules,
metrics, deadlines, resource limits, evidence limits, cleanup behavior, or
statistical scope.

## Exact retry scope

- Reuse the exact previously authorized 96-file bundle: manifest SHA-256
  `9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74`,
  bundle SHA-256
  `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
- Reuse remote program SHA-256
  `dfb40c8b82c788c55b9662b250ceaa000787697825bc845443ffeadd1dd4c913`.
- Run the same 39-or-more focused tests and immutable 12-case W4 freeze.
- Run P7 IR: 12 cases × 8 blocks × 4 arms = 384 cells.
- Run P7 relation: 12 cases × 10 blocks × 5 arms = 600 cells.
- Total: 984 primary development-scout cells in fresh processes.
- Use one Secure `cpu3c`-compatible 2-vCPU CPU pod, 12-GB container storage,
  zero pod volume, zero network volume, and no source/system builds.
- Keep the 20-minute lifetime, `$0.10` retry-phase cap, `$5.00` attributable
  campaign cap, ownership-bound watchdog/deletion, bounded chunks/evidence,
  and no replacement within this retry controller.
- Preserve W8 confirmation cases untouched. This remains a diagnostic
  development timing/RSS scout, not the principal P7 result and not an
  external-method comparison.

## Authorization basis

Brian previously authorized the exact W4 workload and exact 96-file upload. He
also explicitly authorized up to `$5` for additional runs, reruns, and failed
runs that need rerunning without another request, and on reconnection directed
this task to continue. This amendment consumes at most one additional create
for the isolated bootstrap compatibility correction described above.
