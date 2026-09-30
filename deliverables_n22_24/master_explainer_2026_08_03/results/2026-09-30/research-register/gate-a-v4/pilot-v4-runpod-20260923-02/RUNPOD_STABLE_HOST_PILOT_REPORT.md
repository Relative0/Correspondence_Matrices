# Runpod stable-host pilot report — pilot-v4-runpod-20260923-02

## Decision

**Gate A remains NO-GO.** Runpod rejected the one authorized successor request before allocating a pod. This is the second retained pre-allocation `SUPPLY_CONSTRAINT` setup failure; it is not an exploratory stability result.

No smoke check, pilot measurement, confirmatory schedule, secondary schedule, natural-corpus pairability operation, or performance-result inspection occurred.

## Attempted configuration

The prospective successor offer was NVIDIA RTX 2000 Ada Generation in Secure Cloud, on-demand and non-interruptible, advertised at `$0.24/hour` immediately before submission. The request specified one GPU, at least 4 vCPU, at least 16 GiB RAM, 20 GiB local container disk, no network volume, the Ubuntu 24.04 PyTorch image `runpod/pytorch:1.0.3-cu1281-torch291-ubuntu2404`, and only `8000/http` for later evidence retrieval.

Runpod returned no pod ID and reported the requested specifications were unavailable. No billable runtime was allocated, so task compute cost is `$0.00`; no Runpod billing line exists for the rejected request. The unused one-time transfer sender was stopped and its task-created CLI directory was removed.

## Retained evidence

- Original package SHA-256: `93c556a4c15099c260919287e95809079bf8d5ff21b8117e4155fd0482a7306a`.
- Extracted deliverable manifest: 68 of 68 hashes matched locally.
- Audited source snapshot SHA-256: `cbaa4ff1d28964bb4f786f97bd6ea3de0a686c00d3e40031f15335779d6fd3e8`.
- The redacted supply-constraint record is `setup_failures/runpod_setup_failure_20260923T113934Z.md`.

## Next repair prompt

Do not probe additional offers in this task. Preserve both rejected pre-allocation requests as setup failures. A subsequent task may make one newly authorized prospective Runpod attempt only after current Secure Cloud availability is verified. It must use a new `pilot-*` identity, retain the unchanged v4 corpus/pilot/harness/runner and thresholds, and avoid all confirmatory performance work. If secure capacity remains unavailable, defer the environment-qualification pilot; do not infer timing stability or modify Protocol v4 from these availability failures.
