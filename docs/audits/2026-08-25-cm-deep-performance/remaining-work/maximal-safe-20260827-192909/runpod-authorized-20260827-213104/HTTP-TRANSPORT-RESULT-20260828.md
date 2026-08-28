# HTTP CPU smoke attempt — creation succeeded, workload did not run

Recorded August 28, 2026. **One actual create request was made and its
authorization is consumed. No replacement is authorized or queued.**

Runpod accepted the small REST v1 CPU creation request. The controller then
refused a storage mismatch before uploading any source: the request specified
a 10-GB pod volume, but the returned metadata reported 0 GB. The owned pod
was deleted immediately, and independent postflight checks verified absence.
There is no new installation, focused-test, memory-study, or benchmark result.

## Local startup and Windows watchdog correction

`http-execute-001/RUN.json` records `creation_attempted=false`. Its watchdog
acknowledged the exact state, but the original check compared its executing
Python PID with the Windows virtualenv redirector's launcher PID. A trivial
child reproduced the difference. Both guards exited cleanly. This local
startup consumed no create request; its controller and output remain intact.

The new `runpod_http_smoke_controller_v2.py` uses the distinct
`http-execute-001b` directory. It binds the actual worker PID to the launcher
using the reported parent relationship, retains both identities, and checks
liveness through a read-only Windows process handle. It never uses
`os.kill(pid, 0)` on Windows. Before the actual create, launcher PID 23656 was
bound to worker PID 32556, whose parent was 23656 and whose handle was live.

## Actual cloud outcome

All times below are UTC on August 28, 2026.

| Event | Observed result |
| --- | --- |
| Create request | 08:38:23.218567, `POST https://rest.runpod.io/v1/pods`, HTTP 201 |
| Pod identity | `eidn8uu97y3b6q`, name `cm-http-smoke-cd6483629ede` |
| Request ID | `req_95690fdf-c796-4257-887a-0221e5e50406` |
| CPU/resources | cpu3c, 2 vCPU, 4 GB RAM, $0.06/hour, 12-GB container disk |
| Image/ports/cloud | Approved pinned image, only 8080/http and 8081/http, SECURE confirmed through v2 |
| Failed predicate | `volumeInGb=0`, while 10 GB was requested and required |
| Workload | Zero source files uploaded; no remote setup, tests, or study |
| Teardown | DELETE returned 204; both inventories empty at 08:38:28.702949 |
| Watchdog | `controller_cleanup_verified`, no errors; both guards released and exited |

The resource predicate was diagnosed using a copy of the sanitized metadata:
changing only the volume field from 0 to 10 made the remaining checks pass.
No actual run record, response, executed controller, or guard was modified.

Creation success establishes that this credential and request could create
this CPU pod at that time. It does not isolate the cause of the earlier HTTP
500 responses. The immediate metadata observation does not establish that
CPU pod volumes are unsupported, or whether a later response would differ.
The historical successful launcher requested 10 GB but did not verify the
actual returned pod-volume size; its request is not evidence of allocation.

## Independent postflight and cost

`HTTP-FINAL-VERIFICATION-20260828-084114-539259.json` records independent checks
at 08:41 UTC: both v1/v2 pod details returned 404 and both inventories were
empty. Both guard process handles reported exited. No cloud mutation was
made by this verification helper.

The Aug 27–29 UTC day-bucket billing query returned zero records and zero
CPU/GPU/disk/total charges. **Billing may lag; this is not a final invoice.**
The observed $0.06/hour rate and 6.062932-second controller interval give an
estimated compute cost of **$0.00010105**, excluding storage. This estimate
is recorded separately from billing and does not assert a zero final charge.

## Verification and preserved evidence

- `HTTP-WINDOWS-WATCHDOG-CHECK-33385197.json`: 25 offline transport cases,
  four PID-binding cases, and a real trivial launcher/worker liveness probe
  passed. No credential, network request, or workload was used in these checks.
- `HTTP-FINAL-LOCAL-VALIDATION-20260828-084644-262089.json`: all 65 approved
  files / 691,789 bytes still match their hashes; seven helper/controller
  files parse successfully; both controllers, bootstrap and preflight match
  their respective frozen records. There are no staged files.
- `http-execute-001b/RUN.json`, `POD-RESOURCE-CHECK.json`,
  `WATCHDOG-PROCESS-BINDING.json` and `TRANSPORT-FREEZE.json` retain the
  observed run details. The original `http-execute-001` directory is preserved.
- Executed v2 controller SHA-256:
  `44f727d81bb63cea47355fd483d4c38916f318b9efb58cf8c209b696e8917152`.
- Bootstrap SHA-256:
  `404be8b58a69386587953ce07d885637dc49d72ee9bcff5d3a8836d4eee04691`.

The independent website task also reviewed the run and added separate offline
tests; its test claims are not substituted for this task's recorded checks.
Full regression, estimator calibration, and compatibility replay remain
unrun here. Nontrivial local computation did not substitute for Runpod.

Repository snapshot: `main` at
`6ce1f3fbc49df93e11ea53e7d1c24de3ac4885d7`. The existing five campaign
implementation/test changes and concurrent master-explainer changes remain
untouched by this transport continuation. No stage, commit, push, publication,
credential-file edit, or unrelated resource mutation occurred.

## Next approval boundary

`HTTP-EPHEMERAL-RETRY-AMENDMENT-20260828.md` proposes one additional create
using the existing 12-GB container disk and no pod volume, with the same
image, approved bundle, workload, HTTP transport and cleanup controls. It
retains the existing aggregate HTTP/campaign spending caps. It is **not
authorized or launched**. No separate task or handoff is required.
