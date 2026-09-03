# Corrected architecture query-ladder follow-up

Date: 2026-09-03
Scope: non-neural repeated exact restrictions (architecture comparison Lane B)
Status: attempt 001 closed incomplete; retry 002 frozen and awaiting exact authorization

## What this phase corrects

Architecture comparison retry 002 timed one q64 trace and retained q1/q4/q16 only as
prefix correctness digests. It also attached process-wide high-water RSS to rows. Those
fields are not sufficient for a break-even curve or per-arm memory comparison.

The follow-up preserves retry 002's 54 runnable Lane-B cases, eight arms, exact residual
artifact, and 16 balanced arm-order blocks. It expands the schedule to four independent
query-count cells per arm/case/block:

- q1: 6,912 cells;
- q4: 6,912 cells;
- q16: 6,912 cells;
- q64: 6,912 cells;
- total: 27,648 cells.

Every decision-bearing cell runs in a fresh Linux fork child. The task timer is inside
the child and excludes process-isolation launch time. The parent records the child's
total peak RSS from `wait4`, the inherited baseline from `/proc/self/statm` immediately
before the fork, and their nonnegative difference. These are descriptive measurements
on that host, not a calibrated cross-machine memory-routing model.

## Verification completed without timing claims

The new functional tests check all eight arms at all four query counts against frozen
oracle checkpoint digests. The 27,648-row schedule and source closure verify exactly.
The 70-file, 3,934,507-byte upload package passed a clean isolated-tree replay without
`PYTHONPATH`, network access, timing evidence, memory evidence, or a decision-bearing
result. Its local functional replay checked 32 arm/query-count cells.

The execution request is
`docs/recognition/architecture_query_ladder_followup_execution_20260903/RUNPOD_AUTHORIZATION_REQUEST_20260903.json`.
It is limited to one Secure CPU Pod, one create with no replacement, 2 vCPU, at least
4 GB RAM, 12 GB ephemeral disk, no persistent volume, a $0.25/hour rate ceiling, a
$0.05 total ceiling, ten-minute cleanup, and twelve-minute reconciliation. The request
does not authorize neural training, selector fitting, routing changes, website changes,
publication, or a Git push.

## Remaining gates

1. Obtain the exact fresh authorization and execute the frozen Linux/GCC package.
2. Independently verify all 27,648 schedules, artifacts, timing sums, and memory fields.
3. Analyze q1/q4/q16/q64 setup-amortization and retain every unfavorable case.
4. Replicate the corrected contract on a separate machine/compiler.
5. Only then prepare task-labelled public sections; preserve the historical Windows
   1.472x result with its date/platform rather than replacing it.

## Attempt 001 disposition

The exact authorized attempt created one Secure CPU Pod at $0.06/hour. It completed
11,744 of 27,648 scheduled cells before the 420-second workload deadline. The controller
deleted the Pod after 536.059 seconds of billed lifetime at an estimated compute cost
of $0.008934; controller cleanup and a later independent inventory check both found no
remaining Pod. No replacement was created.

The incomplete rows are not a performance or memory result, and the independent
verifier did not run. They are retained only for failure diagnosis and retry sizing.
Their stage accounting showed that `gc.collect()` inside each fork child consumed about
257 of 310 accounted seconds (83%). That collection scanned the large heap inherited
from the parent, although the child process immediately exited and released its entire
cell heap. It therefore measured the isolation mechanism rather than backend cleanup.

The corrected implementation clears the declared backend caches inside the task timing,
uses child exit for the remaining cell-heap cleanup, and reports the full fork/IPC/exit
lifecycle separately. Retry 002 is now source-frozen at checkpoint `13d9927`, and its
regenerated 70-file package passed isolated local replay without timing or memory
evidence. Attempt 001's authorization cannot be reused; the exact retry request is
separate and remains ungranted.
