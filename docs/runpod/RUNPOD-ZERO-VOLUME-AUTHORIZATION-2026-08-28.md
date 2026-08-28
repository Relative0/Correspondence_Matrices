# Zero-volume memory-smoke retry: authorization and review

Final status: the single approved attempt completed with 70 remote tests
passing and 312 successful rows. The pod was deleted; separate 09:05 UTC
checks confirmed absence and guard exit. The create authorization is
consumed, with no replacement queued. See the
[result and independent evidence audit](RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md).

## Authorization recorded at 08:58 UTC, August 28, 2026

Brian replied **“Yes, please continue, I authorize”** in `Audit CM website
evidence` to the explicit question about one further attempt allowing zero
separate pod volume while retaining the 12-GB container disk, frozen
workload, 20-minute lifetime and spending caps. This supersedes the earlier
statement that another exact allocation approval was still required. It
does not erase or replenish the already consumed first HTTP create.

The existing `Run CM safe work campaign` task
(`01a0432e-f946-7481-ae27-e1ad756e28a5`) remains the sole launch owner.
The approval was relayed to it with the exact scope. This website-audit
task will review and test the amendment locally and reconcile its results;
it will not start a second controller or pod. One create is shared across
tasks, not one per task.

Use the owner's stricter
[zero-volume amendment](../audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/runpod-authorized-20260827-213104/HTTP-EPHEMERAL-RETRY-AMENDMENT-20260828.md):

- One additional Secure CPU create: two vCPUs, at least 4 GB RAM,
  compute no more than $0.25/hour; fresh offer and account checks.
- Exactly 12 GB container disk, zero separate pod volume, no network
  volume. Verify these actual returned resources before source upload.
- At most **$0.10 aggregate for both HTTP attempts** and **$0.20 for the
  campaign**. Reserve at least $0.01 for the prior allocation, or higher
  attributable billing, plus at least $0.01/hour for new storage. Refuse
  unexplained accounting gaps. This grants no budget increase.
- Same digest-pinned Python image, 65-source-file manifest, 13 locked
  binary wheels, focused output-budget tests and k=6,8 memory smoke.
  No expanded benchmark, corpus, dependency, or source build.
- Same token-authenticated HTTPS-proxy transport, ports 8080/8081,
  at-most-once worker execution, bounded evidence and timeouts.
- Independent acknowledged watchdog before creation, cleanup at 18
  minutes and maximum 20-minute lifetime. Maintain the awake/AC host
  requirement and reconcile ambiguous creation through that horizon.
- Private use of the already authorized credential loader only. Do not
  expose, hash, copy, edit or upload account credentials.
- New controller/output identities, preservation of all prior records,
  owned-pod-only deletion and independent cleanup/billing checks.

The separate 12-file feature-model measurement bundle is not included.
No automatic replacement, GPU fallback, support message, publication,
commit or push is authorized by this continuation.

## Pre-create independent review, 09:01 UTC

The complete new preflight and v2-to-v3 controller diff were reviewed. The
request and actual-resource validator both require zero pod volume; the
validator refuses absent, Boolean, floating-point and string substitutes
for that integer zero. Container size, network-volume, image, identity,
placement, port, price and watchdog checks remain. The frozen remote worker
creates its own `/workspace/cm-memory-smoke/run-output` directory, so it
does not require data to persist across a restart. This source review is
not proof that the eventual worker's filesystem is writable.

Both quoted and actual resource prices include the prior-cost reserve in
the $0.10 aggregate cap. Billing is grouped by pod ID, with detail amounts,
record counts, unique pod count and component totals reconciled; unknown
charges refuse creation. The reserve remains even when no bill is visible.
The v1 grouped fields were checked against the
[official billing API](https://docs.runpod.io/api-reference/billing/GET/billing/pods).

Added `tests/test_cm_runpod_ephemeral_independent.py`: **12 independent
fake-input tests**. Together with the existing 49 setup, lookup and
transport tests, **all 61 passed** in the project virtualenv:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_cm_runpod_*.py' -v
```

These tests cover strict storage responses, retained storage boundaries,
reserve omission, quoted/actual cap agreement, delayed or higher charges,
unknown attribution, malformed counts and amounts, inconsistent totals,
nonredirecting grouped read-only requests, prior cleanup and preserved
source identities. They do not run a pod or validate real proxy behavior.

| Reviewed file | SHA-256 |
| --- | --- |
| `runpod_http_smoke_controller_v3.py` | `3296099d0d6c30e83698d1638d7cdc4001fd9158ffce3d68d0d599ee44d4654f` |
| `http_transport_preflight_v2.py` | `2a784ed20486d85b7484bfe7de037c6872256ef1e6ef10895deae61b6223193b` |
| `http_transport_bootstrap.py` (unchanged) | `404be8b58a69386587953ce07d885637dc49d72ee9bcff5d3a8836d4eee04691` |
| `tests/test_cm_runpod_ephemeral_independent.py` | `0b2c7ff707a33a4e2907ce91559fd272eb17e47303c0b3171dbd714a88d63cf5` |

The sole owner received the passing review before its create; no blocking
finding remained for this exact amendment. Its fresh live preflight,
watchdog gate and one-create limit still apply. This review did not edit
the owner's controllers, authenticate, launch a resource or upload files.
Execution and cleanup were subsequently reconciled in the result audit
linked above; the following first-attempt reference remains historical.

The [first-attempt audit](RUNPOD-HTTP-RETRY-INDEPENDENT-AUDIT-2026-08-28.md)
remains historical evidence: HTTP 201, zero-versus-ten-GB storage refusal,
no source upload, verified deletion, and 49 local tests passing. It is not
a remote benchmark result.
