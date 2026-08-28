# Runpod next-step transport and scope review — 2026-08-28

Current outcome: a separately approved zero-volume HTTP retry subsequently
completed with 70 passing tests and 312 successful rows, followed by verified
cleanup. Read the [successful-smoke audit](RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md)
and [working setup handoff](RUNPOD-SETUP-HANDOFF-2026-08-28.md).
The proposal and first-attempt records below are historical, not an
instruction to replay a consumed create or ask for an already used approval.

First-attempt update: the single 65-file HTTP retry was authorized and implemented
by `Run CM safe work campaign`. Its corrected controller created one pod
(HTTP 201 at 08:38 UTC), refused a reported zero-GB pod volume versus the
approved ten GB, uploaded no test bundle and deleted the pod. Final 08:41
UTC checks confirmed both inventories empty and detail 404s. The attempt is
consumed; no replacement is queued. All 49 setup/lookup/transport tests pass.
Read [the current independent audit](RUNPOD-HTTP-RETRY-INDEPENDENT-AUDIT-2026-08-28.md)
and [coordination record](RUNPOD-HTTP-RETRY-COORDINATION-2026-08-28.md).
The proposal/preparation descriptions below retain their earlier scope.

Status: local review only. No launch, upload, support message or new
authenticated request was made for this review. It incorporates the other
task's completed root-loader check rather than repeating it.

## What is established

The other task's root-loader check at 08:08 UTC and this task's campaign-key
check at 08:09 UTC both returned HTTP 200/zero pods from the v1/v2 inventories,
and HTTP 404 for `jvhxwl5bk4bmut`. The root evidence was inspected at 08:18 UTC;
see [the evidence and source identities](RUNPOD-READONLY-ACCESS-2026-08-28.md).
Different loader paths have not resolved visibility. This does not identify
the account, establish key equality/create permission, or explain the prior
HTTP 500 creation failures.

The previous CPU v1 controller embeds the ZIP, manifest and bootstrap in
the create request. The successful historical controller sends a smaller
bootstrap request and uploads source later. Source inspection confirms that
the proposed retry also changes vCPU count, container disk, pod volume and
ports relative to the failed CPU8 request. It is a **recovery/compatibility
test with multiple changed factors**, not a controlled experiment isolating
request size. A success would show that the amended combination works; a
failure would preserve another useful request ID, not prove a capacity or
credential diagnosis. No actual amended request size is available until its
adapter is implemented and frozen.

## Keep the two jobs separate

| Item | Other task's memory smoke | This task's measurement verification |
| --- | --- | --- |
| Frozen source files | 65 | 12 plus source manifest |
| Workload | Focused output-budget tests and k=6,8 memory smoke | 17 runner tests and 28 scheduled functional-pilot cells |
| Dependencies | Existing 13 hash-locked binary wheels | Remote dependency validation still required |
| New transport proposal | Small REST v1 create, then authenticated HTTPS upload | No reviewed remote transport/controller yet |
| Remote provenance | Must preserve smoke contract and verify worker identity | Runner still labels execution local; requires a source revision and new bundle identity |
| Current cloud result | Earlier creation attempts failed before a pod ID | Never uploaded or run remotely |

Do not put the measurement pilot into the memory-smoke source bundle, extend
its workload, share an unreviewed result directory, or borrow its upload or
spending approval. A connection test succeeding does not qualify either
job's benchmark claims. No public website result should claim a remote pass
until that job's retrieved evidence has passed its own audit.

## Existing one-pod proposal reviewed, not changed

The proposal belongs to the other task and was not edited here:

```text
C:\Users\brian\Documents\CM_Computation\docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\runpod-authorized-20260827-213104\HTTP-TRANSPORT-RETRY-PROPOSAL-20260828.md
```

Reviewed SHA-256:
`6601be2c3e73c9d2d5e4e151220b00c0d9a07c76537466edb65d41618fa35eaa`.

Its proposed bounds are one Secure CPU pod, two vCPUs, at least 4 GB RAM,
at most $0.25/hour, $0.10 additional and $0.20 campaign total including
storage/prior costs, and at most 20 minutes from creation. It proposes
12 GB container disk, a 10 GB pod volume, and only 8080/http and 8081/http;
no GPU, SSH, network volume or automatic replacement. The pinned image,
65-file workload and 13-wheel lock stay unchanged. These are proposed bounds,
not a quote, new authorization, or an assertion that a controller exists.

The current [REST v1 schema](https://docs.runpod.io/api-reference/pods/POST/pods)
documents CPU selection, entrypoint/start arguments, exposed ports and pod
storage fields. That is schema support, not server-side validation of this
specific image, payload or account eligibility. Runpod distinguishes a
pod volume retained until pod deletion from an independent network volume;
the latter is outside this proposal.
[Storage documentation](https://docs.runpod.io/pods/storage/types).

## Required checks before an approved attempt

1. Use one launch owner and one fresh durable attempt identity. Re-read the
   other task's status immediately before acting. An exclusive claim must
   prevent both tasks from executing the same proposal; an existing claim
   or uncertain creation result must not trigger a second POST.
2. Review/freeze a new transport adapter and bootstrap without modifying
   executed controllers or the approved source files. The historical
   controller is not reusable unchanged: it retries flavors and its saved
   result request is not token-authenticated. This retry permits one create
   request and requires authentication for all sensitive worker routes.
3. Use a fresh per-pod bootstrap token, never the account API key, for proxy
   upload/execution/progress/results. Require exact expected origins, TLS,
   no redirects, bounded uploads/results, archive traversal/duplicate/link
   rejection, file/hash allowlist checks, and a fixed workload. Test missing
   and wrong token rejection, replay/duplicate execution refusal, truncated
   uploads, bad hashes, malformed responses and timeout paths with fakes.
   Runpod's proxy makes an exposed service publicly accessible; HTTPS is
   transport protection, not application authorization.
   [Port security guidance](https://docs.runpod.io/pods/configuration/expose-ports).
4. Obtain the exact transport/storage/upload/spending authorization. Then
   check a fresh quote and reserve, actual returned CPU/RAM/image/rates,
   ports/storage, and absence of unrelated resources before upload. Refuse
   mismatches; neither the default schema nor an old price is a live quote.
5. Arm and verify the independent deadline/cleanup process before creation;
   retain no-ID/timeout ambiguity through the full horizon. A host-side
   watchdog depends on the host remaining powered, awake and connected; it
   is not a provider-enforced spend cap. Terminate only the owned pod, verify
   deletion, and inspect billing separately without treating lag as zero cost.
6. Retrieve bounded evidence, verify hashes and workload results, and report
   each failed/refused/unfinished stage. Do not relabel a connectivity pass
   as memory-study completion or CM performance superiority.

This review does not certify an adapter that has not yet been implemented.
The root-lookup helper's 10 new passing offline tests cover only read-only
diagnostics. The separate memory-smoke retry remains the next proposed
resource-changing step; this task has not queued a duplicate.

## Local verification of this continuation

All 26 setup/lookup tests passed under the existing project virtualenv:
16 existing credential-free readiness tests and 10 new fake-client lookup
tests. The new tests also passed separately. No dependencies were installed,
no real credential was loaded by these tests, and no remote benchmark ran.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_cm_runpod_*.py' -v
```

Only the new test file and this task's local documentation were changed.
The other task's helper, loader, executed controllers, proposal and result
files were read but left unchanged. No commit, push or publication occurred.
