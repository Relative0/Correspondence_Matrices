# Corrected architecture query-ladder follow-up

Date: 2026-09-03
Updated: 2026-09-04
Scope: non-neural repeated exact restrictions (architecture comparison Lane B)
Status: retry 002 verified on one Linux/GCC host; cross-machine replication pending

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

## Preparation verification

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

1. Replicate the corrected contract on a separate physical machine/compiler.
2. Only then prepare task-labelled public sections; preserve the historical Windows
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
lifecycle separately. Retry 002 was source-frozen at checkpoint `13d9927`; attempt
001's authorization was not reused.

## Retry 002 one-host result

The exact retry authorization was recorded against request SHA-256
`b1d867502776e855603d9948f3cf5e76226702d8e90a680d5e7387e7c3d17d79`. One Secure CPU
Pod completed all 27,648 cells in 88.074 seconds of workload time. The independent
verifier found zero semantic, schedule, source/artifact, or memory-field mismatches and
confirmed 6,912 rows for each of q1, q4, q16, and q64. The controller deleted the Pod;
its final inventory and a later independent inventory query both found empty v1 and v2
inventories. Estimated retry compute cost was $0.002649, and the combined estimate for
attempt 001 plus retry 002 was $0.011583.

At q1 and q4, Python R2 remained the best fixed arm. CSE-flat bigint was the best fixed
arm at q16 and q64; at q64 it was 1.100x over R2, won all 54 case clusters, and had a
1.031x minimum. Native fused slots first exceeded R2 by aggregate point estimate at q64
(1.049x), but its 95% case-cluster interval was 0.969x–1.139x and its 0.567x minimum
failed the frozen 0.95 floor. The 18 previously observed C36 cases favored native by
1.328x, whereas the 36 fresh cases favored R2 overall (native 0.933x). This is evidence
against a universal native default, not a basis for fitting a selector.

The memory fields verify the isolated-child measurement contract, but the child's peak
RSS was below the inherited parent baseline in all 27,648 rows and the nonnegative
incremental field was consequently zero. Absolute peak RSS remains descriptive for this host and cannot train
a router. Explicit cache cleanup was only 0.23% of accounted task time, confirming that
the 83% attempt-001 collection share was a measurement artifact. The complete analysis
is in
`docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904/VERIFIED_INTERPRETATION.md`.
