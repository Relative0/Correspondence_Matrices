# HTTP memory-smoke retry: independent local review — 2026-08-28

Historical first-attempt report. Brian subsequently approved a distinct
zero-volume attempt, which completed with 70 passing remote tests and
312 successful rows, followed by verified cleanup. See the
[current result audit](RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md).
The records below are preserved and are not that successful run.

## Final outcome: created, refused before upload, deleted

The sole owner's corrected `http-execute-001b` made **one** creation request
at **08:38:23.218 UTC**, receiving **HTTP 201** for pod `eidn8uu97y3b6q`.
Request ID: `req_95690fdf-c796-4257-887a-0221e5e50406`.

Runpod reported **0 GB pod volume instead of the requested/approved 10 GB**.
The other checked resource conditions matched: cpu3c, two vCPUs, 4 GB RAM,
$0.06/hour, 12-GB container disk, the pinned Python image, HTTP ports
8080/8081, Secure placement verified through same-pod v2 detail, and no
independent network volume. A copied-record diagnostic confirms that only
the volume field needed to match for the validator to pass; no actual
evidence was edited. The immediate API report does not distinguish transient
metadata, CPU-specific storage behavior or a provider defect.

The controller refused the mismatch **before uploading the source bundle**.
It deleted only its owned pod (HTTP 204) and verified both inventories empty
at **08:38:28 UTC**, about 6.06 seconds after its recorded creation epoch.
The watchdog finished without errors and both temporary wake guards were
released. A separate final check beginning **08:41:09 UTC** again found
pod-detail 404s and empty v1/v2 inventories, and confirmed both controller
and watchdog workers had exited.

Billing then showed zero records and zero amount for the API's resolved
August 27–29 UTC day bucket. **Billing may lag; this is not a final invoice
or proof of zero cost.** The independently recomputed compute estimate is
about **$0.000101**, excluding storage and provider billing adjustments.

The create body was 4,602 bytes with four environment entries. The separate
245,786-byte source/manifest/workload payload was never sent; only the
authorized bootstrap was carried in the create command. This demonstrates
that this revised combination could create a pod, **not** that request size
alone caused the earlier HTTP 500s. No source-upload success, installation,
remote test, memory-study row or CM speedup is established.

The single actual creation attempt is consumed; no replacement is queued.
The separate 12-file measurement pilot remains outside this workload.
Another allocation requires a new exact one-pod approval, for example for
zero separate pod volume while retaining the 12-GB ephemeral container disk
and unchanged workload/image/ports/budget/lifetime limits. Such a change
would still require review and verification of the writable worker workspace.
Sending a provider-support inquiry is another separately authorized option.

### Verified evidence identities

These records are under
`docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/runpod-authorized-20260827-213104/`:

| Record | SHA-256 |
| --- | --- |
| `http-execute-001b/RUN.json` | `aba56a6a08f090593e6ce04e43ccc9241b172aa1728004bb4a957465b67f2045` |
| `http-execute-001b/POD-RESOURCE-CHECK.json` | `ea2e374f2399ee95e66af7e5fcce9773dacd85de965b0e1421d5889ae7302d97` |
| `HTTP-FINAL-VERIFICATION-20260828-084114-539259.json` | `7c4c4993865a17e7c3591aebaae5db36787b01a460f43e3194e614c8a0661c0c` |

This task reconciled both local invocation records, confirmed that only the
second attempted a create, cross-checked pod identities, deletion and
postflight status, verified the preserved source hashes, and recomputed the
compute estimate. It made no additional authenticated request or launch.

### Final independent tests and Windows correction

The owner's trivial real local-child probe established different launcher
and executing-worker PIDs, linked by the child's parent PID, and observed
the worker alive and then exited through a read-only Windows process handle.
This is consistent with Python's documented Windows venv redirectors.
[Python venv documentation](https://docs.python.org/3.13/library/venv.html).

The corrected `_v2.py` controller binds those identities and checks worker
liveness without disabling the guard or changing interpreter/workload. The
original executed controller remains preserved. The new test revision runs
against v2 and adds two binding cases: **23 transport tests plus 26 existing
setup/lookup tests, all 49 passing**. The historical 47-test pass below is
not 47 additional distinct tests.

Final controller SHA-256:
`44f727d81bb63cea47355fd483d4c38916f318b9efb58cf8c209b696e8917152`.
Final independent test file SHA-256:
`870bf60cb0099f45b52863346b3fcae750b0ead3422f7f9e0fb0d9216416c737`.
The bootstrap is unchanged; both controller versions match their run freezes.
No website benchmark values, production defaults, commits, pushes or
publications were changed by this task.

## Scope and ownership

Brian approved one HTTP transport retry. The existing `Run CM safe work
campaign` task owns its launch and cleanup; the website-audit task reviewed
and tested its code without launching another controller or changing its
in-progress source. See [the coordination record](RUNPOD-HTTP-RETRY-COORDINATION-2026-08-28.md).
The separate 12-file measurement pilot is not part of this workload.

At 08:33 UTC, the sole owner's `http-execute-001` directory had been created
and its temporary controller wake guard recorded. That preparation alone
does not establish pod creation, remote installation, or a benchmark result.
The execution outcome will be reconciled separately below.

## Two pre-launch findings addressed by the launch owner

1. **Request/response field mismatch.** The first validator required
   `imageName`, `computeType` and `cloudType` in returned pod metadata.
   The v1 response documents `image`; CPU flavor and machine placement
   provide additional response-side evidence. The revised validator accepts
   documented response fields, checks image aliases for conflicts, verifies
   Secure placement (with a same-pod v2 lookup when necessary), checks the
   returned pod ID against owned creation evidence, and rejects differing
   image, CPU, GPU, RAM, ports, storage and spending conditions. It does not
   fill actual resource facts from the requested configuration.
   [Runpod v1 response schema](https://docs.runpod.io/api-reference/pods/POST/pods).
2. **Partial watchdog state publication.** The original exclusive JSON open
   made a final filename visible before writing finished. A watchdog could
   observe it and fail to parse incomplete state. Publication now writes and
   flushes/fsyncs a new temporary file, atomically hard-links it to the final
   name without overwriting, then removes the temporary link. The watchdog
   validates the exact state and acknowledges it with its process ID; the
   controller requires that acknowledgment and live process before creating
   a pod. The independent tests verify complete publication, overwrite
   refusal, matching acknowledgment and process liveness, and missing-ack
   timeout without waiting in real time.

Both findings were sent to the launch-owning task before its controller
started. That task made the corrections. This audit did not patch or run
the launch controller itself. The hard-link publication test passed on this
Windows filesystem; this does not establish support on every filesystem.

## Executed independent tests

`tests/test_cm_runpod_http_transport_independent.py` adds **21** small offline
tests. Together with the earlier 16 readiness and 10 read-only lookup tests,
**all 47 tests passed** under the existing project virtualenv.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_cm_runpod_*.py' -v
```

Coverage also includes missing/wrong tokens on sensitive routes; minimal
public health; upload hash/truncation/length/transfer-encoding refusals;
deadline and fixed-port enforcement; no arbitrary run command; at-most-once
worker start; no post-start upload; incomplete-result refusal; child
environment exclusion of provider/account/bootstrap credentials; declared
and streaming result caps; and refusal to target unrelated or ambiguous
pod identities. All HTTP clients, credentials, worker creation and relevant
controller artifacts were fake or mocked. No sockets or cloud workload ran.

The first test pass encountered fixture errors after the concurrent owner
added an owned-ID lookup: the test lacked a fake `POD-IDENTITY` record.
The fixture was corrected to mock that lookup; the production identity check
was not weakened. The final combined run passed.

Source identities observed for the initial 21-test pass (the test file was
subsequently extended for v2 as recorded above):

| File | SHA-256 |
| --- | --- |
| `runpod_http_smoke_controller.py` | `9ef4f954f3c87e2b5046295c8437b0c2283f8979f21063fd946997085fe52012` |
| `http_transport_bootstrap.py` | `404be8b58a69386587953ce07d885637dc49d72ee9bcff5d3a8836d4eee04691` |
| `tests/test_cm_runpod_http_transport_independent.py` | `a617761059351fbea62bbff57a7039fd40a251accb2832ab8db2803bc8a62e7e` |

These tests are a separate agent's local checks of the same project code,
not third-party certification or a remote trial. They do not exercise real
proxy load, loss of host power/network, provider billing enforcement, every
possible API schema, or every parser/resource-exhaustion attack. Host-side
cleanup still depends on the host remaining powered, awake and online.

## First local invocation (historical; no cloud request)

The first local controller invocation, `http-execute-001`, stopped at
08:34:01 UTC before its creation call. `RUN.json` records
`creation_attempted: false`, `pod_created: false`, zero source files
uploaded, and `watchdog did not acknowledge this exact state`. The saved
acknowledgment's state matches the controller state; its process ID is
24084. The launcher-versus-worker PID distinction is being investigated by
the launch owner. Do not diagnose a provider failure from this local gate.

The controller's cleanup check found both inventories empty. No pod POST
was consumed by this invocation. Preserve its directory and frozen source
identity; any corrected local invocation must use a new output identity and
still respect the single actual creation attempt limit. Passing fake-process
tests did not expose this platform-specific launcher identity distinction.

The corrected invocation and verified final outcome are recorded at the top
of this report. Do not classify these local tests or a successful allocation
as a completed Runpod memory study, CM performance advantage, or closure of
the feature-model measurement gaps.
