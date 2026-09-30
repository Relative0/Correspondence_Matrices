# Runpod stable-host pilot report — pilot-v4-runpod-20260924-01

## Decision

**Gate A remains NO-GO.** A Secure Cloud L4 pod was allocated, but its runtime did not reach the one-time package receiver after repeated passive status checks. The pod was terminated before the frozen package transferred. This is a retained provisioning failure, not an exploratory stability result.

No smoke check, pilot measurement, confirmatory schedule, secondary schedule, natural-corpus pairability operation, or performance-result inspection occurred.

## Environment and lifecycle

- Runpod pod ID: `3ld2nogd4dw7ht`; machine ID: `wy7yhuaipv58`; pod-host ID: `3ld2nogd4dw7ht-64411783`.
- Requested cloud type: Secure Cloud, on-demand, non-interruptible; GPU offer: NVIDIA L4, 24 GiB; advertised rate: `$0.49/hour`.
- Requested resources: one GPU, at least 4 vCPU, at least 16 GiB RAM, 20 GiB local container disk, zero GiB network volume, and `8000/http` only for post-run evidence retrieval.
- Requested image: `runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404`.
- Provisioning response written: `2026-09-24T11:01:08Z`.
- Termination verified: `2026-09-24T11:12:26.6398211Z`; the provider returned `deleted: true`, and a subsequent `pod get` returned `404 not_found`.

The required exact cost is pending provider posting: a scoped Runpod billing query for this pod from `11:00Z` through `11:15Z` returned `[]`. No cost is inferred from that empty result.

## Evidence and integrity

- Original package SHA-256: `93c556a4c15099c260919287e95809079bf8d5ff21b8117e4155fd0482a7306a`.
- The extracted handoff directory verifies all 68 deliverable hashes.
- Audited source snapshot SHA-256: `cbaa4ff1d28964bb4f786f97bd6ea3de0a686c00d3e40031f15335779d6fd3e8`.
- `provisioning_response.json` records the redacted request and allocation response. No SSH key, API key, transfer code, or secret-bearing output was retained.

## Next repair prompt

Do not run another paid pod in this task. Preserve the prior 2026-09-23 pre-allocation supply constraints and this 2026-09-24 stalled-runtime termination as setup failures. Before any future Runpod attempt, investigate the compatibility of the selected image and the Runpod one-time receiver through non-billable documentation or a deliberately approved setup method, then make only one newly authorized prospective deployment with a new `pilot-*` identity. Preserve unchanged v4 inputs and thresholds, and do not inspect or execute confirmatory performance work.
