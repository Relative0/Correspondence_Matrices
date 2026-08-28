# Approved Runpod smoke — provider-blocked

Date: 2026-08-27. The approved smoke did not produce remote test or memory results. No production default or implementation source changed during this execution attempt.

## What happened

Brian approved CM-MEMORY-SMOKE-20260827-192909, then explicitly authorized using the credential file supplied in the campaign directory. Windows had named it `.env.txt`; it was renamed to `.env.runpod.local` in the same directory so the existing Git ignore rule protects it. The key was used only for Runpod API authentication, never printed, committed, or included in worker inputs.

All 65 approved source/test/lock hashes matched. The official Python image tag resolved to the approved Linux amd64 image digest. The live catalog initially quoted CPU3C at $0.06/hour for 2 vCPU and 4 GB RAM. The requested pod had 10 GB container disk, no persistent volume, no GPU, and no public ports.

One actual creation request was sent to the v1 API at approximately 14:46:35 UTC. It returned HTTP 500 without a pod ID. That request transmitted the approved compressed source bundle to the Runpod control plane; receipt or extraction by a worker was never verified. The initial controller did not preserve the provider's complete error body, so the precise cause of that HTTP 500 is unknown.

The controller's immediate postflight and two independent checks found zero pods. A current-API retry was prepared under the same approval, with no resource, source, image, or spending-cap increase. Three retry preflights stopped before sending a creation request because CPU3C was unavailable. Retained catalog responses show capacity fluctuating between HIGH, LOW, and NONE; one response reported NONE for every listed CPU flavor. A paired fresh/reused-session check found the same capacity in both sessions and zero cookies, providing no evidence of a client-session cause.

**Actual creation requests: one. Confirmed pod IDs: none. Remote evidence received: none.** No second creation request, full regression, corpus replay, calibration study, or larger run occurred.

## Cleanup and verification

An independent hidden watchdog was started before the creation request and retained during reconciliation. Its deadline lookup failed because the detached process could not resolve the Runpod hostname; it did **not** complete a successful postflight. That limitation is retained in `watchdog.log`. The watchdog had checked process readiness, but not its own network access, before creation; that is a controller readiness gap.

The independent account inventory at 15:09:03 UTC, over 22 minutes after the creation request, contained zero pods. The DNS failure was then followed by an approved read-only inventory outside the sandbox at **15:12:18 UTC (22:12:18 Bangkok)**; it independently confirmed **zero pods**. No unrelated resource was changed. Do not treat the failed watchdog check as successful teardown evidence.

The controller's cost field is an estimate based on confirmed runtime, not a billing invoice. No pod runtime was confirmed and billing was not queried; do not relabel the estimate as an independently verified charge.

Local verification in this attempt was limited to trivial controller checks: syntax, the 65-file archive/hash round trip, command argument round trip, SSE completion parsing, owned-pod teardown with a fake client, evidence reconstruction, and incomplete-evidence refusal. `controller-unit-fixtures/` contains illustrative test data, not Runpod results. The earlier 70 passing focused tests remain local evidence only.

The current v2 controller now requires the detached watchdog to complete an authenticated network probe before it writes its ready marker. It also retains and retries deadline-lookup errors instead of exiting without a result. Four additional fake-client checks passed for startup DNS refusal, transient recovery, owned-pod-only termination, and persistent failure remaining unknown. See `WATCHDOG-HARDENING-CHECKS.json`. These are local functional tests; the hardened detached process has not been launched against Runpod, and a live network probe is still required before the next creation request. Executed controller sources remain preserved separately.

## Continuation

Authentication is now configured in the ignored file described above. The existing single-smoke approval remains recorded; no broader campaign is approved. When Secure CPU capacity is stable, recheck account-zero, current price, frozen hashes, and the pinned image before retrying this same smoke. Keep the 20-minute lifetime, $0.20/hour compute, $0.10 total, and all upload/dependency restrictions. Never replace or terminate an unrelated pod.

Use the current-API controller only after reviewing its retained checks and this provider failure. A watchdog network probe must pass in the actual detached execution context before a future creation request; a ready file alone is insufficient. Use the required sandbox escalation if that context cannot resolve or reach Runpod, and retain bounded retry/error reporting at the deadline. A fresh run label is required; output folders are never reused. The memory candidate remains diagnostic-only, and no compatibility or performance conclusion can be drawn from this failed execution attempt.

Machine-readable evidence: `SUMMARY.json`, `FINAL-POSTFLIGHT.json`, `REPOSITORY-FINAL.json`, `CONTROLLER-UNIT-CHECKS.json`, `CONTROLLER-FINAL-CHECKS.json`, `CONTROLLER-V2-CHECKS.json`, and the per-attempt `RUN.json` / `LIVE-OFFER.json` files.
