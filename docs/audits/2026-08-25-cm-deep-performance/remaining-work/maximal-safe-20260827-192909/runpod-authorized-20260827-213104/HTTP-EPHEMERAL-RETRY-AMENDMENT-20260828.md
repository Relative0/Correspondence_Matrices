# Proposed single retry using container storage only

State: **not authorized, not launched**. Prepared August 28, 2026, after the
single create recorded in `HTTP-TRANSPORT-RESULT-20260828.md` was consumed.

## Reason

Creation now succeeds, but the pod reported 0 GB of pod volume against the
10-GB request, causing a safe stop before upload. The smoke creates its own
working directory, needs no persistence across restarts, and retrieves its
bounded evidence before deletion. A container-storage-only request is the
next candidate; it is not a claim that CPU volumes are unsupported or that
the remaining bootstrap/workload will succeed.

## Exact proposed target and effect

- Make at most **one additional REST v1 create request** in the currently
  authorized Runpod account, solely for this shared CM smoke. No duplicate
  in another task, create retry, automatic replacement, or GPU fallback.
- Use one disposable Secure CPU pod: **2 vCPU, at least 4 GB RAM**, cpu3c,
  cpu3m or cpu5c chosen from a fresh quote, compute at most **$0.25/hour**.
- Request and verify **12 GB container disk, `volumeInGb=0`, and no network
  volume**. Use `/workspace/cm-memory-smoke` as an ordinary container
  directory. No persistent storage is required or authorized.
- Keep **$0.10 aggregate spending for both HTTP attempts** and **$0.20 for
  the entire smoke campaign**, including storage and prior costs. This
  amendment grants no budget increase. Reserve at least **$0.01** for the
  completed HTTP allocation while its billing may lag; if attributable
  billing is higher, use that higher amount. Reserve at least $0.01/hour
  for new storage. Refuse creation unless the maximum 20-minute cost plus
  prior costs/reserves fits both caps; stop on unexplained accounting gaps.
- Maximum lifetime **20 minutes from the create request**, with an
  independent watchdog ready and acknowledged before creation and cleanup
  at **18 minutes**. Retain both Windows launcher/worker identities and
  read-only process-handle liveness checks. Keep the host open, on AC,
  awake and online. Reconcile ambiguous creation through the full horizon.
- Expose only **8080/http and 8081/http** through Runpod's HTTPS proxy.
  Use a fresh per-pod token for upload, execute, progress and results;
  execute the workload at most once. No SSH, Jupyter, or arbitrary commands.
- Preserve the pinned image exactly:
  `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`.
- Upload only the unchanged **65-file / 691,789-byte** approved source/test/
  lock manifest after identity, resource, price and authenticated readiness
  checks. Preserve the reviewed standard-library transport bootstrap and
  original remote workload code. Do not upload website files, real workload
  data, dotenv files, or account credentials.
- Install only the existing **13 hash-locked binary wheels**, run
  `pip check`, the focused `tests/test_output_budget.py` suite, and the
  existing k=6,8 memory smoke. Preserve its setup/test/study timeouts,
  cold/warm schedules, three repetitions, BLAS limit of one and 16-MiB
  evidence cap. No full regression, calibration expansion, corpus download,
  source build or additional dependency is authorized.
- Use `cm_runpod_config.load_runpod_config()` privately for authorized API
  lifecycle/preflight checks. Never print, hash, copy, edit or upload the
  account key; never send it to the worker or proxy.
- Retrieve evidence, delete only this attempt's owned pod in `finally`,
  and independently verify both inventories, pod absence, guard release
  and billing. Preserve all earlier controllers, artifacts and unrelated
  resources. No email, support message, publication or git operation is
  included.

## Local preparation required before any new create

After approval, create a new controller and unique run directory; do not
edit or rerun the consumed v1/v2 controllers. Change the requested and
validated pod-volume size together to zero, retaining all other identity,
image, resource, price, port, credential and ownership checks. Extend the
trivial offline resource/budget cases. The existing preflight's zero-record
billing gate must explicitly account for the completed HTTP pod and reserve
its possible delayed charge; it must not discard a known prior allocation.
Freeze the new code and repeat source/lock validation before launch.

## Approval request

Authorize exactly one additional CPU smoke create using 12 GB container
storage and no pod volume, with the same approved files, image, wheels,
workload and HTTP transport, within the existing **$0.10 aggregate HTTP /
$0.20 campaign caps** and **20-minute lifetime**, followed by deletion and
independent cleanup verification as specified above.
