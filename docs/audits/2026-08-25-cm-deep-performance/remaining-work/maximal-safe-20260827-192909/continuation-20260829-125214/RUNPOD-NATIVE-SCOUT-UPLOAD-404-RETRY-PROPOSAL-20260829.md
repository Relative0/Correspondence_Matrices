# RunPod native-scout upload-status 404 retry amendment

Date: 2026-08-29  
Status: authorized by the user's bounded campaign instruction

## Saved failure being amended

The V7 attempt created pod `3o7r0za7cm72yn`, validated the requested Secure
2-vCPU/4-GB/zero-volume resources, and observed both HTTP health endpoints as
ready. The immediately following read-only `/upload` status request returned
HTTP 404. No source bytes were uploaded. The controller deleted the owned pod;
both inventories were empty. Estimated compute was `$0.0005285193`.

## Exact V8 change

V8 preserves the exact V6 37-file native-scout payload, 63 focused tests,
144-cell P5 smoke, pinned image and dependencies, 256-KiB chunks, 12-GB
container disk, integer-zero pod volume, no network volume, ownership-only
cleanup, 20-minute lifetime and 18-minute cleanup deadline.

Only the host transport changes: after health is ready, a 404 from the
read-only `/upload` status endpoint is retried every two seconds within the
existing five-minute upload deadline. POST chunk acknowledgement rules remain
unchanged and ambiguous writes still fail closed.

The phase cap remains `$0.10`. The aggregate campaign ceiling is `$10.00`, as
explicitly authorized by the user, and includes earlier attempts and any
subsequent reviewed retry. Finishing below that amount is expected and
preferred. This controller performs exactly one create request.

## Authorization basis

The user explicitly authorized closing the three native-representation gaps
and the subsequent real-corpus, scaling, measurement, reproduction and website
work, with automatic retries when total testing cost remains below `$10`.
No email, deployment, repository push, persistent volume, or unrelated cloud
work is authorized.
