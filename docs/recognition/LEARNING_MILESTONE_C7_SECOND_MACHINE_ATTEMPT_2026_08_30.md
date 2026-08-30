# C7 second-machine timing attempt

Date: 2026-08-30  
Lifecycle status: **safe failure reconciled**  
Scientific confirmation: **incomplete**

## Outcome

The one explicitly authorized Secure Runpod CPU pod was created and matched the
frozen resource envelope: two vCPU, 4 GB RAM, 12 GB ephemeral disk, no pod or
network volume, no GPU, the pinned Python 3.13.15 image, and a rate of
$0.06/hour.

Both token-gated proxy health checks became ready. The subsequent payload POST
returned HTTP 404 before any source file was uploaded. The controller therefore
aborted immediately, issued no replacement request, and deleted the owned pod.
No C7 workload or NumPy installation ran, so this attempt supplies no
second-machine timing result.

## Reconciliation

- Create requests under the authorization: 1.
- Automatic replacement requests: 0.
- Uploaded source files: 0 of 14.
- Elapsed time after create: 29.647 seconds.
- Estimated compute cost: $0.000494.
- Controller cleanup: successful.
- Independent watchdog cleanup confirmation: successful.
- Final v1 and v2 pod-detail requests: HTTP 404.
- Final v1 and v2 account inventories: empty.
- Frozen controller, authorization, protocol, manifest, and package hashes:
  matched.

The independent final verifier classified the outcome as
`safe_failure_reconciled`. It deliberately records
`scientific_confirmation_complete: false`.

## Transport correction

The retained evidence proves the failure occurred at the proxy payload endpoint,
but it cannot distinguish provider ingress behavior from dual-port routing inside
the pod. A conservative correction is to expose one HTTPS port and serve upload,
run, progress, and result endpoints from one authenticated server. That removes
the only port-selection ambiguity without changing the 14-file scientific
package.

The no-replacement condition on this authorization remains binding. Any corrected
attempt requires a new explicit authorization and a separately hash-bound
protocol. No retry is queued.

## Evidence

- Authorization: `docs/recognition/c7_linux_confirmation/RUNPOD_C7_LINUX_AUTHORIZED_2026_08_30.json`
- Controller record: `docs/recognition/c7_linux_confirmation/runpod-c7-linux-confirmation-execute-002/RUN.json`
- Transport freeze: `docs/recognition/c7_linux_confirmation/runpod-c7-linux-confirmation-execute-002/TRANSPORT-FREEZE.json`
- Watchdog result: `docs/recognition/c7_linux_confirmation/runpod-c7-linux-confirmation-execute-002/WATCHDOG-RESULT.json`
- Final verification: `docs/recognition/c7_linux_confirmation/RUNPOD_C7_LINUX_FINAL_VERIFICATION_20260830-031326-558392.json`

All 18 research tracks and all eight application areas remain preserved.
