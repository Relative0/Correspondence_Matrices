# GPU-host fallback for the same CPU smoke — awaiting approval

Prepared 2026-08-28 Bangkok. No GPU pod has been created. This is a proposed hardware/budget amendment to CM-MEMORY-SMOKE-20260827-192909, not an authorization record. Brian authorized higher spending for CPU retries, but the earlier package explicitly excluded GPU pods. A separate concise approval question has been sent; do not infer its answer.

## Reason and current offer

Both CPU8 REST v2 and REST v1 creation attempts failed with HTTP 500 before returning a pod ID. The v1 response exposed an upstream response-parsing error. Its internal cause remains unknown; a GPU request could encounter the same problem. Current CPU availability alone does not explain the errors.

At 2026-08-27 18:31:41 UTC, the authenticated exact-type catalog query for one **NVIDIA RTX PRO 4000 Blackwell**, `product=POD`, `cloud=SECURE`, returned LOW availability in EU-RO-1 and **$0.57/hour**. The 18:43 UTC refresh returned the same quote/availability. See `GPU-FALLBACK-RTX-PRO-4000-DETAIL.json` and `CPU8-FINAL-BILLING-AND-GPU-QUOTE.json`. The cheaper RTX 4000 Ada and A40 detail queries had reported NONE. Quotes must be rechecked immediately before any authorized creation.

## Exact proposed effect

Create at most one disposable Secure Cloud pod with one NVIDIA RTX PRO 4000 Blackwell. Run the already-approved CPU tests/study; do not run a GPU kernel or add GPU-specific software. Require at least two vCPU and 4 GB system RAM, record the actual allocation, and keep this host separate from other timing results.

- Maximum compute rate: **$0.58/hour**. Maximum total smoke-campaign cost: **$0.20**, including storage and any earlier observed smoke charges. Maximum lifetime: **20 minutes**. At the ceiling plus the existing $0.002/hour storage reserve, 20 minutes projects to $0.194.
- Container disk remains at most 10 GB. No persistent/network volume, public port, SSH/Jupyter service, template, private-registry credential, account key in the worker, or global networking.
- Same frozen image: `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`.
- Upload only the same 65 entries from `RUNPOD-UPLOAD-MANIFEST-FINAL.json`; verify all byte hashes before upload and on the worker. No website, secret, corpus, or real-workload data.
- Install only the same 13 exact wheels from `RUNPOD-WHEEL-LOCK.json` using the unchanged requirements lock, `--require-hashes --only-binary=:all:`. No pip upgrade, source build, apt install, optional backend, or extra resolver package.
- Execute only the existing focused `tests/test_output_budget.py` command and the unchanged k=6,8, mixed-chain/alternating-tree, no-context, cold/warm, three-repetition study. Expected success remains 70 focused tests and 312 window rows representing 72 recorded representation repetitions.
- Keep BLAS threads at one, setup deadline five minutes, focused tests two minutes, study five minutes, each study child 30 seconds, and collected evidence at most 16 MiB. Abort earlier to preserve cleanup and cost reserves.

Before creation, require the CPU8 v1 request's final reconciliation, fresh empty inventories, sufficient credit, the new exact offer, and no unaccounted earlier smoke charges. Establish the network-tested independent watchdog and temporary Windows idle-sleep guard before creation. The laptop must remain plugged in, online, awake, and open; the guard cannot override explicit or lid-triggered sleep.

Use the documented GPU creation path, record the request ID and actual resource/price response, and verify identity and bounds immediately. Terminate only this campaign's pod in `finally`; the watchdog starts cleanup at 18 minutes. Independently verify postflight and billing. No automatic replacement or alternate GPU type. An uncertain creation response must be reconciled before any further resource request.

No GPU controller has been executed. Larger calibration, corpus replay, full pytest, policy/default activation, and optional backend work remain outside this proposal.

## Concise approval

I authorize the same approved smoke on one Secure NVIDIA RTX PRO 4000 Blackwell pod, at most $0.58/hour, $0.20 total and 20 minutes, with the unchanged image, 65-file bundle, 13 pinned wheels, commands, and teardown safeguards described above.
