# Approved GPU fallback — final result

**Attempted; provider creation failed. No remote smoke result. Cleanup verification is complete.**

Brian approved one Secure NVIDIA RTX PRO 4000 Blackwell for the unchanged smoke, at most $0.58/hour, $0.20 campaign total including storage and prior observed smoke charges, and 20 minutes. The 65-file bundle, 13 pinned wheels, image, commands, and evidence limits were unchanged.

## Actual attempt

- Request: `POST https://api.runpod.io/v2/pods` at **2026-08-27 19:19:41.497 UTC** (02:19 Bangkok August 28).
- Fresh offer: **$0.57/hour**, LOW availability in EU-RO-1. Both inventories were empty; credit/spend-limit checks passed; earlier pod-billing records and amounts were zero.
- Result: **HTTP 500**, “failed to create pod”, **no pod ID**.
- Request ID: `req_5353d7a7-aeaf-40ac-9a1d-5a6e3f3cd636`.
- Evidence: `gpu-execute-001/RUN.json`, `ACCOUNT-PREFLIGHT.json`, and `LIVE-OFFER.json` in that attempt directory.

This reproduces a creation failure on GPU hardware after the CPU v2/v1 failures. It does not establish that all capacity is taken. Request handling/size, image/configuration support, account eligibility, and placement remain unresolved. Raising the hardware price did not fix this attempt.

## Cleanup and cost

The independent watchdog ran at **19:37:36.755 UTC**, found no pod, and reported no recovery errors. **26 independent snapshots** from both API versions all succeeded and found zero pods, including the final check after the full 20-minute horizon.

A further check at **19:40 UTC** found both inventories empty. The pod-billing API returned **zero records and $0 CPU/GPU/disk/total charges** for its resolved August 27 UTC day bucket. This snapshot may lag and is not a finalized invoice.

All controller/watchdog/reconciliation idle-sleep guards were released; no persistent power settings changed. No replacement is queued. See `GPU-FINAL-RECONCILIATION.json` and `GPU-FINAL-OUTCOME.json`.

## What was verified

The GPU controller passed **10 trivial local fake-client checks**, covering success cleanup, HTTP 400/500, wrong GPU/count, excessive or NaN price, public ports, insufficient RAM, and prior-cost budget refusal. They read no credential, made no network requests, and ran no workload.

All **65 approved source hashes** still match. The remote bootstrap and earlier executed CPU controllers remain unchanged. The new controller SHA-256 is `a354887723389f05ebc3612014bfa484400a6e4148d8052425fbbd5403d58460`.

No installation, 70-test focused run, 312-row study, calibration, corpus replay, or full regression result was obtained. No nontrivial computation ran locally. No source, policy/default, or website changes were made in this continuation. Repository state remains `main` at `6ce1f3fbc49df93e11ea53e7d1c24de3ac4885d7`; unrelated dirty files were preserved. See `GPU-CONTROLLER-CHECKS.json` and `GPU-FINAL-REPOSITORY-STATE.json`.

## Next step

`RUNPOD-SUPPORT-DRAFT-GPU.md` contains the three exact request IDs and sanitized request details. **It has not been sent.** Runpod support should trace the underlying failure before another paid attempt; contacting support requires Brian's explicit confirmation.

Current primary references checked on August 28 Bangkok: [GPU creation schema](https://docs.runpod.io/api-reference-v2/pods/create-a-pod), [pod detail schema](https://docs.runpod.io/api-reference/pods/GET/pods/podId), and [environment-variable documentation](https://docs.runpod.io/pods/templates/environment-variables). The live authenticated outcomes above are preserved locally. The schema exposes the request fields but does not settle the upstream payload/image/account failure.
