# Externally owned native-gap V12 result audit

Date: 2026-08-29  
Status: safely reconciled partial readiness result; no performance result

## Scope and authority

V12 was created by a separate workspace task after this task's exact V7
one-create/no-replacement authorization had been consumed. Its authorization
record cites a newer cross-task instruction to continue native-gap work under a
`$10` aggregate ceiling. That conversation is not visible from this task, so
this audit neither adopts nor rejects that authority. This task made no V12
cloud write and queued no replacement.

## Verified result

Pod `omsz7w8fmlhqn0` matched the Secure `cpu3c` contract: two allocated CPUs,
at least 4 GB memory, `$0.06`/hour, pinned image and ports, 12-GB container disk,
integer zero pod volume, and no network volume. The chunked transport uploaded
all 37 frozen files in eleven bounded chunks and the remote source identities
remained exact.

- Focused tests: 65 JUnit testcase elements, 185 suite-reported tests, zero
  failures/errors/skips.
- P5 smoke: 144/144 cells `ok`; its read-only verifier passed.
- Dependency closure and all four Linux control probes passed.
- Native CaDiCaL: seven functional cases passed with native execution and
  complete process-tree measurement/cleanup.
- Native CUDD: four functional cases passed, including exact dump/reload, with
  complete process-tree measurement/cleanup.
- d4: refused before functional cases because its short-lived `ldd` child could
  not satisfy the measurement fence (`d4 dynamic dependencies`).
- No d4 result, perf result, accepted timing, or performance ranking exists.

The evidence archive is 140,108 bytes across 63 members with SHA-256
`de961928bbbf6e047c7cb6b0f313085055d5c8b5343766e3d99f734efec85635`.

## Cleanup and cost

The controller deleted its owned pod with HTTP 204. At 16:15:56 UTC, both v1
and v2 inventories were empty and all 13 known pod detail requests returned
404. The watchdog reported `controller_cleanup_verified`. Both original host
guards exited; Windows had reused the watchdog PID 85 seconds after release for
an unrelated process, which the final verifier distinguished by querying the
current PID occupant's creation time.

Provider billing still had no row for V12. The elapsed-time/rate reserve gives
an attempt bound of `$0.0017731753`; adding it to the corrected prior bound
gives a conservative attributable campaign bound of `$0.0129657686`, within
this task's stricter `$0.10` phase and `$0.20` campaign ceilings. Billing may
lag.

Final read-only reconciliation:

`EXTERNAL-NATIVE-GAP-V12-FINAL-VERIFICATION-20260829-161613-266111.json`

SHA-256:

`b7bf69e269294ec7f9462d862ecaa7de80e8f2466c1caacea127eb4093e7c4d5`

Two earlier V12 verifier receipts are preserved but superseded: they treated a
reused Windows PID as the original watchdog and therefore reported a false
local guard-liveness failure.

## Interpretation

V12 closes the functional-readiness and whole-process-tree measurement gap for
the tested CaDiCaL and CUDD adapters. It does not close d4 readiness and does
not benchmark CM against another method. Any d4 fence correction or comparative
timing run is a distinct create and must use a separately valid authorization
and exclusive launch ownership.
