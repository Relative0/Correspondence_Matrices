# Runpod continuation — 2026-08-28 Bangkok

## Current outcome — approved zero-volume smoke passed

Brian approved the zero-volume amendment. The single new pod
`s2dpiij1msutml` was created at **09:03:07 UTC**, passed all resource checks,
accepted the 65-file upload, installed the 13 locked wheels and completed
**70 passing tests plus 312 successful/exact window rows (72 recorded
representation calls)**. This is the first retrieved Runpod smoke result
in this campaign. No default or candidate coefficient changed.

DELETE returned 204; both inventories were empty at 09:04:47 UTC.
Independent 09:05:49 UTC checks returned 404 for both HTTP pod IDs through
both APIs, empty inventories and exited guards. Archive/raw/JUnit/source
checks passed. Estimated compute is $0.00167174 for this attempt and
$0.00177279 for both HTTP allocations, excluding storage. Billing still
shows zero records but may lag; this is not a final invoice.

Full outcome and limitations:
`runpod-authorized-20260827-213104/HTTP-EPHEMERAL-RESULT-20260828.md`.
Independent verification:
`runpod-authorized-20260827-213104/HTTP-EPHEMERAL-FINAL-VERIFICATION-20260828-090555-697553.json`.
The runtime affinity exposes two CPUs; the host count of 128 is not the
allocation, and cgroup quota evidence is absent. Candidate underestimates
were 0/72 versus legacy 66/72 in the eligible tiny windows; production
acceptance and real-workload compatibility remain unestablished.

**Both HTTP create approvals are consumed. No further pod or workload is
authorized or queued.** A proposed next structural phase is documented in
`runpod-authorized-20260827-213104/RUNPOD-NEXT-STRUCTURAL-VALIDATION-PROPOSAL-20260828.md`;
it has not run. Larger contexts, full regression and corpus replay remain.
The chronological sections below preserve earlier failures and superseded
approval states. All executed controllers and original evidence are intact.

## Prior outcome — CPU created, storage check stopped upload

The single HTTP create request succeeded at **08:38:23 UTC on August 28**:
HTTP 201, pod `eidn8uu97y3b6q`, cpu3c / 2 vCPU / 4 GB RAM / $0.06/hour.
The controller stopped before upload because the pod reported **0 GB of pod
volume versus the requested 10 GB**. The image, ports, 12-GB container disk,
CPU, RAM, price and SECURE placement matched. **No source was uploaded and
no installation, test or memory study ran.**

DELETE returned 204; both inventories were empty at 08:38:28 UTC. Independent
08:41 UTC checks again found empty v1/v2 inventories and 404 for the owned pod;
both guards had released and exited. Billing showed no records but may lag.
Estimated compute was $0.00010105, excluding storage; this is not a final bill.

**The one actual create authorization is consumed. No replacement is
authorized or queued.** Both controller versions and run directories are
preserved, and all 65 approved source hashes still match. The full result is
`runpod-authorized-20260827-213104/HTTP-TRANSPORT-RESULT-20260828.md`.
Its independent postflight evidence is
`HTTP-FINAL-VERIFICATION-20260828-084114-539259.json` in that directory.

The next candidate is one additional CPU create with the existing 12-GB
container disk and no pod volume. It preserves the image, source, workload,
transport and aggregate budgets, but needs a new exact approval. See
`runpod-authorized-20260827-213104/HTTP-EPHEMERAL-RETRY-AMENDMENT-20260828.md`.
No separate task/handoff is needed. Creation success does not identify the
earlier 500 cause, and one immediate metadata result does not establish that
CPU volumes are unsupported.

The sections below retain chronological investigation and approval history;
their earlier pending/next-step statements are superseded by this outcome.

## HTTP authorization and local startup correction — August 28

Local startup `http-execute-001` stopped **before any create request** because
the Windows virtualenv launcher PID differed from its Python worker PID.
The state and acknowledgment payloads matched, and the difference was
reproduced with a trivial child. Both guards exited cleanly; zero pods were
observed. This startup did not consume the single-create authorization.
The original controller/output remain unchanged. The corrected
`runpod_http_smoke_controller_v2.py` uses `http-execute-001b`, records both
launcher and worker identities, validates their parent relationship, and
checks worker liveness with a read-only Windows process handle. The 25
transport checks, four binding cases, and a real trivial launcher/worker
probe pass. It does not use `os.kill(pid, 0)` on Windows.

Brian approved the exact HTTP transport amendment with "Yes, please run it".
See `runpod-authorized-20260827-213104/HTTP-TRANSPORT-AUTHORIZED-20260828.md`.
This supersedes the older "not authorized" proposal status below. There is
one exclusive create attempt for both coordinating CM tasks; this task owns
it. No duplicate or automatic replacement is permitted.

The new adapter passed 25 offline checks and preserves the approved 65-file
bundle and remote workload. Creation uses a small compressed bootstrap;
source uploads only after resource verification and authenticated readiness.
The preserved local-only startup is `http-execute-001`; the actual cloud
attempt is `runpod-authorized-20260827-213104/http-execute-001b`.
Read its `RUN.json`, watchdog and cleanup records for the actual outcome;
preparation, a passed preflight, or this note does not prove a cloud run.

## Authorized root-loader lookup completed — 08:08 UTC August 28

Brian explicitly authorized the project-root loader to read credentials for
the read-only inventory and supplied-pod lookup, then asked to continue.
`inspect_root_config_pod.py` used `cm_runpod_config.load_runpod_config()` for
private Bearer authentication. No credential value, file content, key hash,
or equality comparison was printed or recorded. No credential file changed.

Both v1 and v2 returned **200 with zero pods** for account inventory and
**404** for `jvhxwl5bk4bmut`. This reproduces the campaign-loader visibility
result using the loader used by the historical successes. It does not prove
that the two keys are equal, that create permission is present, or why pod
creation returned 500. A different local credential-loading path alone has
not resolved the problem. Do not repeat the request to authorize this lookup
or diagnose key scoping from these responses.

Evidence: `runpod-authorized-20260827-213104/ROOT-CONFIG-POD-INSPECTION-20260828-080819-188973.json`.
The helper passed syntax, project-root resolution, and fake HTTP 200/404/500
checks including exclusion of fake credential/environment fields before the
real lookup. The real call made four GET requests only. No resource was
created, changed, started, stopped, or uploaded to.

The remaining useful launch change is the historical small-create/HTTPS-upload
mechanism. It changes exposed ports and pod storage relative to the frozen
port-free smoke approval. A precise one-pod amendment is prepared in
`runpod-authorized-20260827-213104/HTTP-TRANSPORT-RETRY-PROPOSAL-20260828.md`.
It is **not authorized or launched**. It preserves the pinned smoke runtime,
65-file bundle, 13-wheel lock, workload, independent cleanup and total budget;
it does not replay the old benchmark campaign. No more expensive GPU or
automatic replacement is proposed. Approval of credential reading for this
lookup is not treated as approval to expose ports or allocate pod storage.

## Historical successes compared — August 28 investigation

Brian asked to inspect successful runs in the other CM tasks. Task history,
the historical controllers, and their saved evidence were inspected. The
August 25 correction campaign and August 26 one-memo campaign both record
three completed pods, passing acceptance gates, and successful termination.
The memo campaign's raw CSVs were independently checked in this investigation:
each of `hhsiyafmdi2ab3` (cpu3c), `z7xe8rclveprl5` (cpu3m), and
`jcsv6gifsutwqr` (cpu5c) has 272 BX1+B2 rows and 129 EPFL rows, all with
canonical and packed equality. Its recorded cost estimate is $0.002815;
the saved August 26 postflight inventory is empty. These are historical
results, not a new cloud execution or current billing check.

Primary evidence, relative to the project root:

- `deliverables_n22_24/memo_runpod_2026_08_26/memo_runpod_audit_2026_08_26.json`
- `deliverables_n22_24/memo_runpod_2026_08_26/postflight_runpod_inventory.json`
- `deliverables_n22_24/correction_runpod_2026_08_25/correction_runpod_audit_2026_08_25.json`
- `deliverables_n22_24/cm_selector_runpod_campaign_2026_08_24.py`, shared by those campaigns.

| Surface | Successful historical route | Pre-HTTP memory smoke |
| --- | --- | --- |
| Credential loader | `cm_runpod_config.load_runpod_config`: root dotenv paths, then process environment; `RUNPOD_API_KEY` or `RP_TOKEN` | Exactly one `RUNPOD_API_KEY` in the campaign `.env.runpod.local`; no root/environment fallback |
| API authentication | REST v1, Bearer header | Bearer header; CPU v1 and v2 plus GPU v2 have already failed |
| Creation/upload | Small bootstrap request with one per-pod token; source ZIP uploaded after creation through HTTPS proxy | Source ZIP embedded in environment chunks in the creation request; GPU JSON body approximately 246,550 bytes |
| Resources/image | Two-vCPU Secure CPU, `python:3.13.5-slim`; requested 12-GB container disk and 10-GB pod volume, actual pod-volume size not validated | Pinned Python 3.13.15 digest, 10-GB container disk, no pod volume; later larger CPU/GPU attempts |
| Transport | Bootstrap port 8080, worker port 8081; separate upload/progress/results requests | No exposed ports; inline bootstrap and bounded log evidence |
| Existing pod ID | Not needed; ID comes from create response | Also not needed |

Different loader paths do **not** establish that the key values or accounts
differ. No secret contents, key equality, or key scope was checked. The HTTP
500 responses do not isolate capacity, credential eligibility, image,
storage, or payload handling. The successful archive was uploaded separately;
its size is not evidence that the current large creation request is accepted.
Do not treat key scoping as the diagnosed cause or keep raising hardware caps.

The smallest next diagnostic is to use the historical root configuration
loader for read-only pod inventory and the supplied-ID lookup, retaining only
sanitized response metadata. **Private authentication through those root
credential files needs Brian's explicit exception to the no-secret-reading
rule; it has not been performed here.** No key needs to be pasted, compared,
copied, edited, or added to a pod. A subsequent change to the historical HTTP
upload route would require review/authorization of its ports and storage,
while preserving the approved workload, cost/lifetime bounds, and independent
cleanup watchdog. Do not replay an old campaign or consumed attempt.

Only source/evidence reads and a trivial saved-CSV consistency check ran in
this investigation. No authentication, network request, pod mutation, upload,
installation, or benchmark occurred. Concurrent website/source changes and
executed controllers were left untouched.

## Existing pod ID supplied — read-only lookup at 04:29 UTC August 28

Brian supplied `jvhxwl5bk4bmut` and asked whether it needs configuring. Both direct pod-detail endpoints returned HTTP 404, while both account inventories returned HTTP 200 with zero pods, using the previously authorized campaign credential. This establishes that the ID is not visible through that credential; it does not establish whether the pod was deleted, belongs to a different account/team, or is hidden by credential permissions.

Evidence: `runpod-authorized-20260827-213104/USER-POD-INSPECTION-20260828-042916-075330.json`. The new `inspect_existing_pod.py --pod-id ...` helper makes only read-only requests and records selected non-secret metadata. No resource was created, started, stopped, modified, or uploaded to; no active configuration or credential file changed.

The campaign smoke controller creates a new pod and takes the ID from the creation response. It does not require a preexisting local `RUNPOD_POD_ID`, so adding this ID cannot fix those creation HTTP 500 responses. Runpod supplies that environment variable inside a running pod. The separate older `cm_runpod_config.py` client uses it to target an existing worker, but that path also requires a worker URL and would not be the approved port-free smoke workflow. Do not put a user-supplied ID into historical `POD-IDENTITY.json` ownership/cleanup evidence or spoof worker provenance by setting it globally.

Next input: confirm that the pod is still listed in the same Runpod account/team associated with the API key, and whether the key was created in account Settings > API Keys or copied from a pod environment. Runpod documents pod-provided `RUNPOD_API_KEY` values as pod-scoped. This is a possible access distinction, not a confirmed cause of the failed creation requests. Do not paste a key into chat.

Primary references: [Runpod-provided variables](https://docs.runpod.io/pods/templates/environment-variables#runpod-provided-variables) and [account API keys](https://docs.runpod.io/get-started/api-keys).

## Latest outcome — GPU attempt and cleanup complete

Brian approved the exact GPU fallback with “Yes, you can, please do”. The approved smoke was attempted on **one Secure NVIDIA RTX PRO 4000 Blackwell**, capped at **$0.58/hour, $0.20 total and 20 minutes**. At 19:19:41.497 UTC on August 27, creation returned **HTTP 500 without a pod ID**, request ID `req_5353d7a7-aeaf-40ac-9a1d-5a6e3f3cd636`. The fresh quote was $0.57/hour with LOW availability. No remote installation, focused tests, or memory-study result was obtained.

The independent watchdog activated at 19:37:36.755 UTC, found no pod, and reported no recovery errors. All **26** independent inventory snapshots succeeded and found zero pods; the final horizon check completed at 19:39:43 UTC. A further check at **19:40 UTC** again found both inventories empty and zero pod-billing records/charges. Billing may lag and is not a final invoice. All three temporary host sleep guards were released, and no automatic replacement is queued.

The new controller passed 10 trivial offline fake-client cases. All 65 approved file hashes still match, the remote bootstrap is unchanged, and both earlier executed CPU controllers remain preserved. No nontrivial local computation substituted for Runpod. No source, policy, default, website, or workload scope changed.

See `runpod-authorized-20260827-213104/GPU-FALLBACK-RESULT.md`, `GPU-FINAL-OUTCOME.json`, `GPU-FINAL-RECONCILIATION.json`, and `GPU-FINAL-REPOSITORY-STATE.json`. The sanitized `RUNPOD-SUPPORT-DRAFT-GPU.md` contains all three request IDs and has **not** been sent. The CPU history follows; its earlier GPU-pending state has been superseded.

## Current outcome

The approved smoke was actually attempted; this was not merely a documentation handoff. CPU pod creation failed before returning a pod ID, so there is no new remote pytest, installation, or memory-study result. No production default, estimator formula, policy, routing, source/test bundle, or workload scope changed in this continuation. Nontrivial local computation was not substituted for Runpod.

Brian explicitly authorized the frozen 65-file source/test upload and the smoke, then allowed higher spending for CPU capacity. The CPU8 amendment uses eight vCPU, at least 16 GB RAM, at most $0.25/hour, the existing $0.10 total cap, and 20 minutes. Do not ask again for those already-granted CPU/upload permissions. The original preparation documents' statements that cloud access had not occurred are historical, not the current state.

## Actual CPU8 requests

All paths below are under `runpod-authorized-20260827-213104/`.

| Attempt | Request UTC on 2026-08-27 | Result | Request ID |
|---|---|---|---|
| `cpu8-execute-001` / REST v2 | 18:02:14.812944 | HTTP 500, generic failed-to-create response, no ID | `req_4451fa8e-cc81-4e6f-9b96-1df429e3ff1c` |
| `cpu8-v1-execute-001` / REST v1 | 18:22:23.383459 | HTTP 500, upstream response-parsing error, no ID | `req_9e3ea120-638d-42a7-ab63-5c7d6dc21cf2` |

Both requests followed a HIGH CPU3C availability quote at $0.24/hour. Credit and the account spend limit were sufficient. The v1 error was:

```text
create pod: unmarshal to struct { Errors []struct { Message string }; Data json.RawMessage }: invalid character 'I' looking for beginning of value
```

This identifies an API/upstream parsing failure, not its internal cause. Capacity/placement, payload handling, image/configuration support, and account eligibility have not been conclusively separated. There is no evidence that simply increasing the CPU budget will fix it. Runpod's status page reported CPU Cloud operational, last updated 17:51 UTC; this does not invalidate the observed request errors.

The v1 retry followed Runpod's public MCP/CLI CPU path. The MCP client routes CPU creation to v1, while the newer v2 schema exposes CPU configuration. That inconsistency justified trying v1, but is not proof that all current v2 CPU requests are unsupported.

## Cleanup and billing

The v2 watchdog ran at 18:20:11.488 UTC, about 0.44 seconds after its scheduled deadline, and found no pod with no recovery errors. Both API inventories remained empty after the full 20-minute horizon. Its temporary idle-sleep request was released. See `cpu8-v1-continuation-gate/PRIOR-REQUEST-RECONCILED.json`.

The v1 watchdog ran at 18:40:20.421 UTC, about 0.46 seconds after its scheduled deadline, and found no pod with no recovery errors. At 18:42:24 UTC, after the full original 20-minute horizon, independent v1 and v2 requests both returned HTTP 200 with empty inventories. `CPU8-V1-FINAL-RECONCILIATION.json` confirms `owned_pod_absent_after_horizon`. All temporary controller/watchdog/continuation/reconciliation idle-sleep requests were released; the last release was at 18:42:26 UTC. No further CPU creation is queued.

The final 18:43:01 UTC pod-billing snapshot contained zero records, zero unique pods, and zero CPU/GPU/disk/total amount for the API's resolved August 27 UTC day bucket. See `CPU8-FINAL-BILLING-AND-GPU-QUOTE.json`. This is not a finalized invoice and may lag. Controller `estimated_compute_cost_usd: 0` is not independent billing proof when creation returned no ID.

## Local controller changes and checks

The executed v2 CPU8 controller remains preserved at SHA-256 `a7728ee101a3c04cda50d5a8b52e9b1628dc31d2098def0a0ab348587aa0edb2`.

The v1 variant is `runpod_retry_cpu8_v1_controller.py`, SHA-256 `40adb66b61ba59dda9282bf264b6767c738d168ed31abc84c790e1c6c2b3ccac`. It maps the same workload to the documented CPU v1 fields, omits GPU-only/service options, and prefers v1 termination. A trivial fake-client check caught and fixed an `int([])` error in the success exit path; this did not cause the HTTP 500 responses. The remote bootstrap is unchanged.

`CPU8-V1-CONTROLLER-CHECKS.json` records passing syntax, unchanged bootstrap, all 65 source hashes, and fake HTTP 400/500/201 control-flow/cleanup checks. They took under one second, read no credential, made no network request, and created no real pod. Fake fixture directories are not remote workload evidence. No new full pytest, calibration, corpus replay, or GPU computation ran.

`resume_cpu8_v1.py` waited for the first request's complete cleanup horizon before making the one v1 attempt. `finish_cpu8_cleanup.py` performs only final read-only reconciliation. Both use temporary Windows idle-sleep prevention; no persistent power setting was changed. The guard cannot override lid closure, explicit sleep, power loss, or loss of network connectivity.

Recorded invocations, from the project root (consumed output names must not be reused):

```powershell
$env:CM_SMOKE_RUN_LABEL='cpu8-execute-001'
.\.venv\Scripts\python.exe 'docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\runpod-authorized-20260827-213104\runpod_retry_cpu8_controller.py'
.\.venv\Scripts\python.exe 'docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\runpod-authorized-20260827-213104\check_cpu8_v1_controller.py'
.\.venv\Scripts\python.exe 'docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\runpod-authorized-20260827-213104\resume_cpu8_v1.py'
.\.venv\Scripts\python.exe 'docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\runpod-authorized-20260827-213104\finish_cpu8_cleanup.py'
```

The resume helper explicitly sets the child label to `cpu8-v1-execute-001`; it does not reuse the first label. API-bearing commands ran with the required network escalation. The standalone offline checker used mocked clients and no credential access.

## Next step

The GPU fallback was approved and attempted; do not request the same hardware/upload approval again merely because older proposal files say pending. It returned the same generic HTTP 500 as CPU v2. The CPU v1 request exposed an upstream response-parsing error. Capacity/placement, request size, image/configuration handling, and account eligibility remain unresolved; increasing the hardware price did not resolve this attempt.

The useful next step is for Runpod support to trace the request IDs in `RUNPOD-SUPPORT-DRAFT-GPU.md` and confirm the supported correction. Contacting support or sharing the draft requires explicit authorization for that target and effect. No message has been sent. Do not repeatedly allocate replacement pods, change the approved image/upload/dependency scope, or advance to calibration/full regression without the relevant gate. No separate agent/task handoff is needed.

## Repository ownership

At the final repository snapshot (18:41:35 UTC), branch `main` was at `6ce1f3fbc49df93e11ea53e7d1c24de3ac4885d7`, having advanced from `1f51e651cb08ccda3284bd8476e4a9dbaedacf37` during concurrent work. This continuation made no commit. The five earlier campaign implementation/test modifications were unchanged (365 insertions, 46 deletions), and all 65 approved hashes matched at 18:38 UTC. Concurrent master-explainer templates/content/build/generated pages became dirty during this turn; they were neither edited nor attributed to this campaign. This continuation performed no staging, commit, push, publication, dependency install, corpus acquisition, or unrelated resource change. See `CPU8-CONTINUATION-REPOSITORY-STATE.json` and `CPU8-CONTINUATION-LOCAL-VALIDATION.json`.

Primary sources checked: [CPU v1 creation schema](https://docs.runpod.io/api-reference/pods/POST/pods), [Runpod MCP CPU routing](https://github.com/runpod/runpod-mcp/blob/main/src/tools/pods.ts), [current API documentation index](https://docs.runpod.io/llms.txt), and [Runpod service status](https://uptime.runpod.io/). Live quotes and authenticated outcomes are preserved in the local JSON records above.
