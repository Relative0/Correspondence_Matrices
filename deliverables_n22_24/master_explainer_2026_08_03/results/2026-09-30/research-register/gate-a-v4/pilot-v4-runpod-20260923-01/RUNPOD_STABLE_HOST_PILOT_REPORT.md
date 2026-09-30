# Runpod stable-host pilot report — pilot-v4-runpod-20260923-01

## Decision

**Gate A remains NO-GO.** The requested exploratory Runpod pilot did not start: Runpod rejected the single confirmed Secure Cloud request with `SUPPLY_CONSTRAINT` before allocating a pod. This is a retained setup failure, not a stability-control result and not an environment qualification.

No smoke check, pilot measurement, confirmatory schedule, secondary schedule, natural-corpus pairability operation, or performance-result inspection occurred.

## Attempted configuration

The sole selected offer was NVIDIA RTX A5000 in Secure Cloud, on-demand and non-interruptible, advertised at `$0.27/hour` immediately before submission. The request specified one GPU, at least 4 vCPU, at least 16 GiB RAM, 20 GiB local container disk, no network volume, the Ubuntu 24.04 PyTorch image `runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404`, and only `8000/http` for later evidence retrieval.

Runpod returned no pod ID and reported: `There are no longer any instances available with the requested specifications. Please refresh and try again.` No billable runtime was allocated, so task compute cost is `$0.00`; no Runpod billing line exists to retrieve for the rejected request. The unused one-time transfer sender was stopped and its task-created CLI directory was removed.

## Evidence

- Original handoff package SHA-256: `93c556a4c15099c260919287e95809079bf8d5ff21b8117e4155fd0482a7306a` — verified before extraction.
- Extracted deliverable manifest: 68 of 68 hashes matched locally.
- Audited source snapshot SHA-256: `cbaa4ff1d28964bb4f786f97bd6ea3de0a686c00d3e40031f15335779d6fd3e8`.
- Remote bootstrap SHA-256: `0d905adfb073b1e91dd6728b2e6476b3c4c9a05bb2d2d98d66507d082e9c7157`.
- One-time transfer wrapper SHA-256: `f50cd621aa243092e9ff1bddd029ac07a12879ee63f37253d307083efff8420b`.
- Downloaded official `runpodctl` binary SHA-256: `026be0b38d0cc7e68bd2ff21042ebce71b726d0086b160772933d6cea38691f8`; it was used only to prepare the one-time sender, never persisted or configured with a saved credential.
- Redacted Runpod response record: `setup_failures/runpod_setup_failure_20260923T111623Z.md`.

## Precise next repair prompt

Run one prospective successor attempt only after the selected Secure Cloud offer is actually available and the user reconfirms the new billable request. Preserve this rejected A5000 supply-constraint record. Re-query availability using operational properties only; select one different prospective non-interruptible Secure Cloud host class if necessary, record its advertised configuration and price before deployment, and use a new `pilot-v4-runpod-YYYYMMDD-NN` identity. Do not retry individual cases, compare hosts by timing outcomes, inspect confirmatory results, or launch more than one paid pod. If a full pilot eventually runs and fails the unchanged all-200-control rule, retain it and propose Protocol v5 prospectively rather than modifying v4.
