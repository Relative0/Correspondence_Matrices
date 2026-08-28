# Runpod authenticated read-only check — 2026-08-28

Subsequent outcome: the authorized root-loader zero-volume HTTP smoke
completed with 70 passing focused tests and 312 successful rows; owned-pod
deletion and separate absence checks passed at 09:04–09:05 UTC. See
[the result audit](RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md).
The access checks below remain timestamped historical observations, not
a reason to repeat credential authorization or a consumed launch.

## Root-configuration comparison reconciled at 08:18 UTC

Brian authorized the project-root credential lookup and asked to continue.
Before making another request, this task found the other task's completed
08:08 UTC check using `cm_runpod_config.load_runpod_config()`. Its saved JSON
was inspected and hashed. Both APIs returned HTTP 200 with zero pods for
inventory and HTTP 404 for `jvhxwl5bk4bmut`, matching the campaign-key check
below. No redundant authenticated request or further credential read was
made in this reconciliation.

Root-check evidence:

```text
C:\Users\brian\Documents\CM_Computation\docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\runpod-authorized-20260827-213104\ROOT-CONFIG-POD-INSPECTION-20260828-080819-188973.json
```

Evidence SHA-256:
`e6692621092d04b68c2c157dc654dfa7ef632ca934703aea2e24c7a06557cbb2`.
The reviewed current helper `inspect_root_config_pod.py` has SHA-256
`21f2bc524cb5de2bb9925dfc22567e788e2d59dc452a0e6a811948cd647c8f38`;
the current `cm_runpod_config.py` has SHA-256
`ed55485a9adffad023504eaf78e5138ead7de044d71fe028077eed7031f07291`.
These latter two are source identities observed during this review, not a
claim that the earlier run independently recorded its executed source hashes.

The different loader path has not resolved resource visibility. Matching
empty inventories do not establish key equality, account identity, create
permission, or the cause of the creation failures. The root lookup is now
complete; do not request authorization for the same lookup again merely
because an older note describes it as pending.

Ten new offline regression tests passed in
`tests/test_cm_runpod_readonly_lookup.py`. They check GET-only bounded calls,
disabled redirects and incidental credential discovery, exclusion of
unselected private fields, error-body suppression, malformed JSON/inventory,
redacted exceptions, invalid pod-ID refusal before credential loading,
missing-key refusal, and sanitized evidence writing. All used fake clients
and fake credentials; none read credential files or made network calls.
They verify the tested helper paths, not arbitrary response sanitization or
the safety of an unimplemented cloud transport adapter.

## Result at 08:09 UTC / 15:09 Bangkok

Brian explicitly authorized private use of the memory-smoke campaign's
stored API key. The existing inspected helper made four GET requests: pod
detail and pod inventory against each of Runpod's v1 and v2 APIs.

| API | Inventory | Pods visible | Supplied pod `jvhxwl5bk4bmut` |
| --- | --- | ---: | --- |
| v1 | HTTP 200 | 0 | HTTP 404; absent from inventory |
| v2 | HTTP 200 | 0 | HTTP 404; absent from inventory |

The credential is accepted for these inventory requests, and API
connectivity works. There is no existing pod visible through this credential
for the verification workload. The result does not identify an account/team,
prove the key has create permission, explain the previous creation HTTP 500s,
or distinguish a deleted pod from one in another account/team or hidden by
permissions. No pod creation was attempted in this check.

## Evidence and exact code

Sanitized evidence:

```text
C:\Users\brian\Documents\CM_Computation\docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\runpod-authorized-20260827-213104\USER-POD-INSPECTION-20260828-080908-859263.json
```

Evidence SHA-256:
`0531f10f6e8e7c5b4b3f3e149387513d6e43dbc8a69fd29d1181bb16c11d5ff0`.

The helper was `inspect_existing_pod.py`, SHA-256
`c905c32c3377de2cecddfe855add1ad9e3fcee3f5f7426fcb082118bd33439c0`.
Its imported authentication provider was `runpod_gpu_smoke_controller.py`,
SHA-256 `a354887723389f05ebc3612014bfa484400a6e4148d8052425fbbd5403d58460`.
Both source hashes were unchanged after the check. The controller's launch
entry point was not invoked.

The command used the existing project `.venv\Scripts\python.exe` with `-B`
and the helper's `--pod-id jvhxwl5bk4bmut` argument. The shell had the required
network permission. In this process only, the helper's session factory was
wrapped to set `requests.Session.trust_env = False` before any HTTP request.
This prevented discovery of unrelated netrc credentials or environment
proxies. No source file was changed to implement that wrapper.

The helper used TLS verification, disabled redirects, imposed 15-second
request timeouts, and wrote a new evidence filename exclusively. It retained
HTTP statuses/counts and selected non-secret metadata only. No key value,
prefix, length, digest, header or raw provider object was printed or saved.

Credential source used privately, location only:

```text
C:\Users\brian\Documents\CM_Computation\docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\.env.runpod.local
```

## What did not happen

No pod was created, resumed, stopped, modified or terminated. No workload
was run remotely, no files were uploaded, and no configuration, dependency,
power setting or credential file was changed. No billing or live creation
quote was queried. This is not new performance or cloud compatibility
evidence. The 60 local tests and 28 pilot checks retain their existing scope.

## Next step after the completed lookup

The subsequently approved one-CPU HTTP retry received HTTP 201 at 08:38 UTC,
but reported zero-GB pod volume versus the approved ten GB. Its owner refused
the mismatch before source upload, deleted the pod, and verified cleanup;
final 08:41 UTC checks were clear. No benchmark ran. The one creation attempt
is consumed and no replacement is queued. See
[the final independent audit](RUNPOD-HTTP-RETRY-INDEPENDENT-AUDIT-2026-08-28.md).
The 65-file memory smoke and this task's separate 12-file measurement pilot
remain different jobs, and approval of either does not cover the other.

If the supplied pod is still visible in Brian's console, checking its
account/team remains useful, but it is not a reason to repeat key-loading
checks or infer that credential scope caused the creation failures.

Do not repeat paid creation requests or reuse consumed campaign approvals.
Actual upload/launch still requires the exact reviewed bundle, target,
runtime, price/lifetime bounds and independent cleanup gate described in
`RUNPOD-VERIFICATION-GATE-2026-08-28.md`.
