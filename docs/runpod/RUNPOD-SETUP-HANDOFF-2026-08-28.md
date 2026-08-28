# CM Runpod setup and cross-task handoff

Current result, 09:05 UTC: **the zero-volume HTTP smoke worked**. One
Secure CPU pod ran the approved 65-file workload, passed all 70 focused
tests and returned 312 successful measurement rows. It was deleted, and
separate inventory/detail and process checks confirmed cleanup. Billing
may lag. The one additional create is consumed; do not rerun its controller.
See the [independent result audit](RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md)
for raw evidence, hashes, findings and remaining measurement limits.

The working retry uses the **project-root `cm_runpod_config` credential
loader**, the pinned Python 3.13.15 image, temporary token-authenticated
HTTPS ports 8080/8081, **12-GB container disk and zero separate pod volume**.
It does not require an existing pod ID, configured worker URL, SSH or
Jupyter. This is a fourth, explicitly amended workflow below, not the
older campaign-specific port-free transport. All 61 local transport/setup/
accounting tests passed; this is separate from the 70 remote focused tests.

Latest authorization, 08:58 UTC: Brian has approved **one further shared
zero-volume retry**, retaining the 12-GB container disk and frozen 65-file
memory-smoke workload. The existing campaign task remains its sole launch
owner. Use the stricter $0.10 aggregate HTTP/$0.20 campaign caps and reserve
the previous allocation's possible delayed charge. See the
[current authorization/review](RUNPOD-ZERO-VOLUME-AUTHORIZATION-2026-08-28.md).
This is not evidence that the new pod or workload succeeded. Earlier
statements below about needing that exact approval are historical.

First-attempt final update, 08:41 UTC: the one shared 65-file memory-smoke retry
created a pod (HTTP 201), but reported zero GB of pod volume rather than
the approved ten. Its owner, `Run CM safe work campaign`, refused the
mismatch before source upload and deleted the pod. Final v1/v2 checks found
empty inventories and pod-detail 404s; billing had no records yet and may
lag. No workload ran. The one creation attempt is consumed; no replacement
is queued. All 49 setup/lookup/independent-transport tests pass. The earlier
local-only watchdog PID failure was corrected in a preserved v2 controller.
See [the independent audit](RUNPOD-HTTP-RETRY-INDEPENDENT-AUDIT-2026-08-28.md)
and [single-attempt coordination](RUNPOD-HTTP-RETRY-COORDINATION-2026-08-28.md).

Update at 08:18 UTC on 2026-08-28: the other task completed the authorized
root-loader check at 08:08 UTC. Its saved evidence was verified here: both
inventories returned HTTP 200 with zero pods, and the supplied ID returned
404. This matches the campaign-loader result below. The lookup is complete;
do not ask for the same credential-use permission again. No additional
authentication or cloud workload was performed in this reconciliation.
See [the access record](RUNPOD-READONLY-ACCESS-2026-08-28.md) and
[the next transport/scope review](RUNPOD-TRANSPORT-REVIEW-2026-08-28.md).

Update at 08:09 UTC on 2026-08-28: Brian authorized private use of the
memory-smoke campaign credential. A new read-only check returned HTTP 200
and zero pods from both inventories, and HTTP 404 for the supplied pod ID.
See [the authenticated access record](RUNPOD-READONLY-ACCESS-2026-08-28.md).
This updates the access status only; no cloud benchmark or creation ran.
The offline observations and original preparation statements below retain
their historical scope. Root-loader credentials were not used in this check.

Observed 2026-08-28. This is a local setup inventory and a reconciliation of
saved run records, not a new authenticated connectivity test. No credential
contents were read, no configuration was changed, and no cloud resource was
created, started, stopped, or uploaded to for this handoff.

## Bottom line

There is no special Runpod connection tied to this conversation in the
inspected workflow. The successful campaigns used local Python scripts and
Runpod HTTP APIs. Another task needs the correct checkout, interpreter,
configuration **loader**, permissions, and account access for the selected
workflow. Four different workflows coexist; their settings are not
interchangeable.

Historical success is real: the August 26 memo replication records three
completed CPU pods, a passed audit, and all three terminated. However, the
earlier August 27/28 continuation recorded CPU and GPU creation failing with
HTTP 500 and no pod ID, plus a supplied pod ID returning 404 under the
campaign credential. The separately authorized zero-volume HTTP smoke above
now provides current successful execution evidence. It does not isolate
the original HTTP 500 cause. The feature-model pilot itself remained local;
do not relabel it as part of this remote memory smoke.

## Start here: safe command

Run this in PowerShell. It reads source files/package metadata and checks
credential-file existence, but never loads credential files or environment
values, imports a Runpod client, makes network requests, or starts a pod.

```powershell
Set-Location -LiteralPath 'C:\Users\brian\Documents\CM_Computation'
.\.venv\Scripts\python.exe -B scripts\cm_runpod_readiness.py
```

Optional: save to a **new** JSON filename with `--output
docs\runpod\your-new-inventory.json`. Existing files, hidden paths, linked
paths, and paths outside the selected project are refused. Do not use a
credential filename as the output.

For another checkout, use `--project-root 'C:\exact\other\checkout'`. The
reported interpreter is the interpreter actually running the command; this
switch does not activate that checkout's virtualenv. Compare both
`project_root` and `runtime.executable`, not just the current directory.

Current reference report:
[runpod-offline-inventory-2026-08-28.json](C:/Users/brian/Documents/CM_Computation/docs/runpod/runpod-offline-inventory-2026-08-28.json).

The report observed Python 3.13.5 from this project's `.venv`, requests
2.34.2, NumPy 2.3.2, python-sat 1.8.dev20, and dd 0.6.0. Pytest is not
installed in this interpreter; the new diagnostic's 16 tests use standard
library unittest. Package metadata does not prove native CUDD availability.
These are observations, not instructions to upgrade a pinned remote image.

## Locations and configuration rules

Project root: `C:\Users\brian\Documents\CM_Computation`.

| Workflow | Code location under project root | Configuration contract |
| --- | --- | --- |
| Historical disposable CPU campaigns | `deliverables_n22_24/cm_selector_runpod_campaign_2026_08_24.py`; `deliverables_n22_24/cm_memo_runpod_campaign_2026_08_26.py` | Uses the root config loader for account credentials. Creates a new pod and derives its proxy URLs; does not need an existing pod ID or worker URL. |
| Older existing HTTP worker | `cm_runpod_config.py`, `cm_runpod_client.py`, `cm_runpod_deploy.py`, `cm_remote_worker.py` | Worker execution needs `CM_RUNPOD_BASE_URL`; lifecycle operations need an account credential and `RUNPOD_POD_ID`. Some operations can automatically start a stopped pod. |
| Historical port-free memory-smoke attempts | `docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/runpod-authorized-20260827-213104/` | Reads its own campaign `.env.runpod.local`, creates a new pod, and retrieves bounded log evidence. No existing worker URL or pod ID is required. |
| Successful amended memory-smoke HTTP retry | Same directory: `runpod_http_smoke_controller_v3.py`, `http_transport_preflight_v2.py`, `http_transport_bootstrap.py` | Uses the root loader privately, creates its own disposable pod and derives two HTTPS proxy URLs. Zero separate volume, fixed payload and at-most-once execution. The single approved create is consumed: inspect its evidence, do not rerun it. |

### Root loader: campaigns and older HTTP worker

`cm_runpod_config.py` reads these paths relative to its own module directory,
not an arbitrary shell working directory, in increasing precedence:

1. `C:\Users\brian\Documents\CM_Computation\.env`
2. `C:\Users\brian\Documents\CM_Computation\.env.local`
3. `C:\Users\brian\Documents\CM_Computation\.env.runpod`
4. `C:\Users\brian\Documents\CM_Computation\.env.runpod.local`
5. Process environment overrides the files.

It selects `RUNPOD_API_KEY`, falling back to `RP_TOKEN`. The older worker
also uses `CM_RUNPOD_BASE_URL` and, for lifecycle operations, `RUNPOD_POD_ID`.
The configured persistent-root default is `/workspace/cm-computation`, while
the legacy deploy bootstrap actually uploads to `/workspace/cm`; do not
silently equate those paths.

In the offline inventory, root `.env.runpod` and `.env.runpod.local` exist;
root `.env` and `.env.local` do not. None of the eight checked Runpod
environment-variable names was present in this diagnostic process. File
contents, nonempty values, equality of keys, and credential validity were
**not** checked.

### Campaign-specific loader: port-free memory smoke

The separate credential location is:

```text
C:\Users\brian\Documents\CM_Computation\docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\.env.runpod.local
```

This path exists. The controller's `read_key()` expects exactly one
nonempty `RUNPOD_API_KEY` entry there. It does not use root dotenv files,
the process environment, or the `RP_TOKEN` fallback for that key. Updating
only a root file therefore does not configure this controller. Do not copy,
read, print, hash, or compare key contents in chat to diagnose this.

The controller directory contains `runpod_smoke_controller.py`,
`runpod_retry_cpu8_controller.py`, `runpod_retry_cpu8_v1_controller.py`, and
`runpod_gpu_smoke_controller.py`. They have different historical requests
and consumed output directories; they are not generic setup commands.

## How the successful historical route worked

The disposable controllers used REST lifecycle requests at
`https://rest.runpod.io/v1`, bearer authentication, Secure Cloud CPU pods,
and an explicit source allowlist. The August 26 run used two-vCPU pods
across cpu3c, cpu3m, and cpu5c with Python 3.13.5/NumPy 2.3.2.

A bootstrap on port 8080 accepted token-gated upload/deploy requests and
launched the worker on port 8081. Addresses were derived from the newly
created pod ID:

```text
https://<new-pod-id>-8080.proxy.runpod.net
https://<new-pod-id>-8081.proxy.runpod.net
```

`CM_BOOTSTRAP_TOKEN`/`X-CM-Token` is a separate per-pod bootstrap credential,
not the account API key. The controller uploaded a hashed source archive,
polled progress/results, checked outputs, and terminated its owned pod.
This route did not require SSH or SCP.

Evidence:
[memo_runpod_audit_2026_08_26.json](C:/Users/brian/Documents/CM_Computation/deliverables_n22_24/memo_runpod_2026_08_26/memo_runpod_audit_2026_08_26.json).
It records `verdict: passed`, `all_pods_terminated: true`, and historical
estimated total cost USD 0.002815. These old pods are not a current worker
pool, and this historical cost is not a current quote or new spending cap.

The earlier memory-smoke attempts intentionally used a different, port-free route:
the approved 65-file bundle is encoded into environment chunks, started
under a digest-pinned image, and collected through bounded log evidence.
It used its approved 13-wheel lock, a 10-GB ephemeral disk, and an independent
cleanup watchdog. Do not switch it to the older upload/worker route merely
to bypass its frozen scope or a provider error.

Brian subsequently authorized the exact HTTP transport and zero-volume
amendments. The successful v3 controller kept the 65-file workload, 13-wheel
lock and independent watchdog, but used root-loader authentication, a
12-GB container disk, zero pod volume, and the reviewed fixed-payload HTTP
bootstrap. It retrieved its evidence before owned-pod deletion. The
successful output identity is `http-ephemeral-execute-001`; none of these
consumed controllers is a reusable connectivity-test command.

## Latest failures and their limits

Read the latest other-task record first; it supersedes older preparation
documents which said the smoke had not yet been authorized:

[RUNPOD-CONTINUATION-20260828.md](C:/Users/brian/Documents/CM_Computation/docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/RUNPOD-CONTINUATION-20260828.md).

It records these actual creation attempts on August 27 UTC:

| Attempt | Outcome | Request ID |
| --- | --- | --- |
| CPU8, REST v2, 18:02 | HTTP 500; no pod ID | `req_4451fa8e-cc81-4e6f-9b96-1df429e3ff1c` |
| CPU8, REST v1, 18:22 | HTTP 500; upstream response-parsing error; no pod ID | `req_9e3ea120-638d-42a7-ab63-5c7d6dc21cf2` |
| GPU fallback, 19:19 | HTTP 500; no pod ID | `req_5353d7a7-aeaf-40ac-9a1d-5a6e3f3cd636` |

There was no remote installation or benchmark result from these attempts.
The saved independent cleanup-horizon checks found empty inventories; they
are timestamped observations, not a live inventory check performed here.
Provider failure, request/image/configuration handling, placement, and
account eligibility have not been conclusively separated. More expensive
hardware did not resolve the recorded attempts.

At 04:29 UTC August 28, supplied pod `jvhxwl5bk4bmut` returned 404 from
both detail endpoints; both inventories returned 200 with zero pods under
that campaign credential. This establishes non-visibility to that credential,
not whether the pod was deleted or belongs to another account/team.

The authorized root-loader check now corroborates the same empty inventory
and 404 result. A credential-loading-path difference has not resolved it.
If Brian still sees this pod in the console, confirm the account/team without
sharing credentials. Do not repeatedly ask to authorize the completed lookup
or diagnose key scope from matching empty responses. Runpod documents the
API key supplied inside a pod as pod-scoped, so it is not interchangeable
with an account key. This is an access distinction to investigate, not a
confirmed diagnosis. [Runpod variables](https://docs.runpod.io/pods/templates/environment-variables),
[account API keys](https://docs.runpod.io/get-started/api-keys).

Do not insert this supplied ID into historical ownership/cleanup manifests.
Adding an existing `RUNPOD_POD_ID` does not fix a controller's failed request
to create a new pod.

The prepared, unsent provider-support draft is:

```text
C:\Users\brian\Documents\CM_Computation\docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\runpod-authorized-20260827-213104\RUNPOD-SUPPORT-DRAFT-GPU.md
```

Review it before sharing. Sending it or making another resource request
requires the appropriate explicit target/effect authorization; this handoff
does not grant that. Do not repeat consumed attempts or endlessly raise caps.

## Why tasks can differ

- A task may run in another checkout. Worktrees isolate checkout state;
  ignored files are not automatically included in a handoff. A virtualenv or
  local dotenv file can therefore be absent. This is a possible explanation
  to check, not a finding that the other task uses a worktree.
  [Official worktree documentation](https://learn.chatgpt.com/docs/environments/git-worktrees).
- The two credential loaders above use different paths and fallback rules.
  Matching environment-variable names does not make them equivalent.
- Interpreter/package availability, filesystem access, and network approval
  can differ. Request the normal scoped approval for an important
  sandbox-blocked operation; do not disable protections or dump credentials.
- Distinguish failure layers: a missing file/import is local; an HTTP 404 for
  one pod is resource visibility; an HTTP 500 is an API response, not evidence
  that the local machine cannot reach the service. None alone proves the
  underlying account/provider cause.
- SSH is not required by either inspected campaign. If a separate workflow
  genuinely requires SCP/SFTP, Runpod's basic proxied SSH does not support
  them; full SSH over an exposed public TCP port is a different setup.
  [Official SSH documentation](https://docs.runpod.io/pods/configuration/use-ssh).

## Copy-paste prompt for the other task

```text
Please reconcile this task's Runpod setup with the CM project's documented
setup, using read-only diagnostics first.

Project: C:\Users\brian\Documents\CM_Computation
Interpreter: C:\Users\brian\Documents\CM_Computation\.venv\Scripts\python.exe
Read the full handoff:
C:\Users\brian\Documents\CM_Computation\docs\runpod\RUNPOD-SETUP-HANDOFF-2026-08-28.md

Run the credential-free offline inventory from that project:
.\.venv\Scripts\python.exe -B scripts\cm_runpod_readiness.py

If this task is in another checkout, report its exact root/interpreter and
compare using --project-root. Do not assume ignored local configuration,
dependencies, task permissions, or process environment are shared.

Identify which workflow we are actually using:
1. Historical disposable CPU HTTP-worker campaigns: root dotenv loader.
2. Older existing-worker client: root loader plus worker URL/pod identity.
3. Historical port-free memory smoke: campaign-specific .env.runpod.local.
4. Successful amended 65-file HTTP smoke: root loader, new disposable pod,
   two token-gated HTTPS proxy URLs, 12-GB container and zero pod volume.
Do not mix these configuration requirements. Do not run deploy/provision,
start/resume, or an old campaign as a connectivity test.

The root loader tries .env, .env.local, .env.runpod, .env.runpod.local,
then the process environment; it accepts RUNPOD_API_KEY or RP_TOKEN.
The historical port-free memory smoke instead reads RUNPOD_API_KEY from:
C:\Users\brian\Documents\CM_Computation\docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-20260827-192909\.env.runpod.local
The smoke creates its own pod, so it needs neither a preexisting pod ID
nor CM_RUNPOD_BASE_URL. Do not read, print, hash, copy, or edit secrets.

Historical August 26 CPU success does not establish current connectivity.
Read the latest RUNPOD-CONTINUATION-20260828.md beside that campaign file:
CPU v1/v2 and GPU creation returned HTTP 500 with no pod IDs; the supplied
pod jvhxwl5bk4bmut was 404 under the campaign credential while inventories
were empty. Preserve those outcomes and distinguish them from setup errors.
The authorized root-loader lookup also completed at 08:08 UTC August 28,
with HTTP 200/zero pods on both inventories and HTTP 404 for the same ID.
This task verified its saved evidence; do not repeat that authorization
request or conclude that matching visibility proves matching keys/accounts.
Read RUNPOD-READONLY-ACCESS-2026-08-28.md and
RUNPOD-TRANSPORT-REVIEW-2026-08-28.md in docs/runpod for the current status.
The proposed 65-file memory-smoke HTTPS transport retry is a separate job
from this task's 12-file measurement-verification bundle. Do not combine
their approvals or launch concurrent duplicate retries.
The single memory-smoke HTTP retry has now been authorized; its owner is
Run CM safe work campaign. The website task independently reviewed its
transport but will not launch another copy. Read the current independent
audit and the owner's newest run records before acting. The first local
http-execute-001 invocation stopped before a pod POST on a watchdog PID
check. Its corrected http-execute-001b invocation then consumed the single
create request: HTTP 201, reported pod volume 0 instead of 10 GB, no source
upload, and verified deletion. Both versions/directories remain preserved.
Final 08:41 UTC inventory/detail checks were clear; billing may lag. No
replacement, new storage contract or second workload is authorized by the
completed attempt. Brian subsequently approved exactly one further
zero-volume attempt at 08:58 UTC. Read
RUNPOD-ZERO-VOLUME-AUTHORIZATION-2026-08-28.md and the owner's newest records
for its status and stricter aggregate caps. The existing campaign task
remains the sole launch owner. That further attempt has now completed:
http-ephemeral-execute-001, pod s2dpiij1msutml, HTTP201 at09:03:07UTC,
70 focused tests passed,312 successful rows, DELETE204 and verified
absence/guard exit at09:04-09:05UTC. Read
RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md for the raw-evidence audit.
It used the root loader and verified the amended storage contract. Billing
may lag; the compute-only estimate is $0.001672, not a final invoice.
All61 local transport/setup/accounting tests passed. The remote smoke is
not full memory calibration, production-estimator acceptance, or a
CM/CUDD/SAT performance comparison. This handoff is not permission to
duplicate its controller, replay a consumed create, or expand the workload.

Inspect newer updates before acting. Preserve concurrent core and website
changes. Do not overwrite historical run directories, ownership manifests,
or frozen bundles. Respect previously completed authorizations without
replaying consumed attempts; this prompt is not a new paid-launch approval.
Do not send the prepared support draft without confirmation of its target
and effect. Report verified facts, unresolved causes, and the smallest safe
next action. Never claim a cloud benchmark ran without retrieved evidence.
```

## Local continuation in this task

The offline diagnostic and its 16 regression tests are implemented. The
corrected next feature-model measurement protocol is prepared separately:

[CONFIGURATION-FM-MEASUREMENT-RERUN-PROTOCOL-2026-08-28.md](C:/Users/brian/Documents/CM_Computation/deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CONFIGURATION-FM-MEASUREMENT-RERUN-PROTOCOL-2026-08-28.md).

That protocol is not an executed benchmark or a claim that any of the 13
measurement gaps is closed. No cloud actions, website publication, commit,
or push were performed for this continuation.

Verification on 2026-08-28: all 16 diagnostic tests and all 21 existing
website/evidence tests passed under the project virtualenv. `git diff
--check` found no whitespace errors in tracked changes (Git emitted existing
line-ending warnings). No full repository/native-backend suite, new timing
experiment, authenticated Runpod check, or browser visual check ran here.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_cm_runpod_readiness.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p '*website.py' -v
```
