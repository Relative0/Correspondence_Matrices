# One CPU retry through the historical HTTPS upload mechanism

State: proposed, not authorized, not launched. Prepared August 28, 2026.

## Reason for the amendment

The authorized project-root credential lookup completed at 08:08 UTC. Like
the earlier campaign-loader lookup, both inventories were empty and the
supplied pod ID returned 404. This has not established a credential-scope
problem. Historical successful campaigns used a small creation request and
uploaded source after bootstrap readiness; the failed smoke embedded source
in the creation request. Changing that transport is a testable next step,
not a confirmed repair or a claim that the provider is out of capacity.

## Exact proposed effect

- Use the existing project-root credential loader privately for this
  attempt's Runpod API authentication. Do not copy, modify, print, hash,
  upload, or compare credentials. Never send an account key to the worker
  or proxy; use a fresh in-memory per-pod bootstrap token instead.
- Make at most **one** REST v1 create request for a disposable Secure CPU
  pod with **two vCPUs and at least 4 GB RAM**. Select one of cpu3c, cpu3m,
  or cpu5c from a fresh availability/price check before creation. There is
  no create retry, alternate-GPU fallback, or automatic replacement.
- Compute price at most **$0.25/hour**. Additional spending at most
  **$0.10**, and total smoke campaign spending at most the previously
  approved **$0.20**, including observed prior costs and storage. Abort if
  the budget reserve cannot be established. Do not treat delayed billing
  or a no-ID response as conclusive proof of no charge.
- Maximum lifetime **20 minutes from the create request**, with the
  independent host watchdog scheduled earlier and ambiguity reconciliation
  through the full deadline. Keep the host open, on AC, awake, and online.
- Use **12 GB container disk and a 10 GB pod volume mounted at /workspace**,
  matching the historical launcher. The pod volume is deleted with this
  owned pod; create no independently persistent network volume.
- Expose only **8080/http and 8081/http** through Runpod's HTTPS proxy for
  the temporary bootstrap and worker. Require the per-pod token for upload,
  execution, progress and result requests. Health responses must reveal no
  secrets or source. Do not enable SSH, Jupyter or arbitrary remote commands.
- Keep the existing approved image unchanged:
  `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`.
  The historical Python 3.13.5 image and unpinned bootstrap installation are
  not substituted. The bootstrap uses the standard library before setup.
- Carry only the previously approved 65 source/test/lock files, with
  manifest/hash verification before upload and on the worker. Transport
  bootstrap code and manifest metadata must be reviewed and frozen before
  execution. No user corpus, website files, dotenv files, or account secrets.
- Install only the existing 13 hash-locked binary wheels. Run only the
  existing focused output-budget tests and k=6,8 memory smoke. Preserve
  the original setup/test/study deadlines and 16 MiB evidence cap.
- Check actual returned resource identity, rates, ports and storage before
  upload. Stop on a mismatch. Collect evidence in a new directory, terminate
  only this attempt's owned pod in finally, and independently verify cleanup.
  Preserve unrelated resources and all previous evidence.

## Preparation required after approval and before creation

Implement a new transport adapter without editing executed controllers or
the frozen source bundle. Test its bounded authenticated upload, hash
validation, timeout and cleanup paths with local fake clients only. Review
current price, inventory, billing reserve and host watchdog readiness. The
historical controller must not be run unchanged: its dependencies, upload
allowlist, lifetime and result access do not match this smoke's boundaries.

Runpod's current REST schema documents the relevant port and pod-volume
fields: [Create a Pod](https://docs.runpod.io/api-reference/pods/POST/pods)
(reviewed August 28, 2026). It does not establish the cause of the previous
500 responses or guarantee this amended request will succeed.

## Approval

Authorize one CPU smoke retry exactly as above, including the temporary
HTTP ports and pod storage, private root-loader authentication, unchanged
approved workload, $0.10 additional / $0.20 campaign caps, 20-minute limit,
and deletion of the newly created pod and its pod volume afterward.
