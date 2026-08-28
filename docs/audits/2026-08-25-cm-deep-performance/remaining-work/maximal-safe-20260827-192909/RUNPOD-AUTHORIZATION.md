# Single Runpod safety-smoke authorization package

Package ID: CM-MEMORY-SMOKE-20260827-192909.
State: PREPARED, NOT AUTHORIZED, NOT LAUNCHED.

## Exact requested effect

Create exactly one disposable Secure Cloud CPU pod for the memory/refusal smoke. No GPU, network volume, persistent service, corpus acquisition, optional backend, source build, or automatic replacement pod.

- Image: official python:3.13.15-slim-bookworm, Linux x86_64, normal CPython ABI. The tag is listed in the [official Python image catalog](https://hub.docker.com/_/python). Resolve and record its digest before execution; stop if unavailable or the runtime identity differs.
- Resources: 2 vCPU, at least 4 GiB RAM, at most 10 GiB ephemeral container disk; Secure CPU offer only.
- Maximum quoted compute price: $0.20/hour. Maximum total campaign cost including storage: $0.10.
- Maximum lifetime: 20 minutes from creation; boot/install deadline 5 minutes; tests 2 minutes; study 5 minutes; each study child 30 seconds. Abort earlier if the remaining cost/lifetime reserve is insufficient.
- Upload exactly the 65 source/test/lock entries in RUNPOD-UPLOAD-MANIFEST-FINAL.json to /workspace/cm-memory-smoke. Validate every byte hash before upload and again on the pod. No .env, credentials, .git, website files, external/tmp data, or workload content.
- Download/install exactly the 13 wheels in RUNPOD-WHEEL-LOCK.json (25,707,468 bytes), using runpod-requirements.lock with --require-hashes --only-binary=:all:. No source fallback, --no-deps exception, pip upgrade, additional resolver packages or apt install. The metadata closure passes; real installation is still untested.
- Packages: NumPy 2.3.2, SymPy 1.14.0, mpmath 1.3.0, requests 2.32.5, charset-normalizer 3.4.3, idna 3.10, urllib3 2.5.0, certifi 2025.8.3, pytest 9.0.2, iniconfig 2.1.0, packaging 26.3, pluggy 1.6.0, Pygments 2.19.2. Exact wheel filenames, URLs and SHA-256 values are in the lock JSON.
- Execute only the focused budget tests and the frozen k=6,8 smoke below. Do not run the full corpus/full pytest or add repetitions on this approval.
- Collect only smoke evidence/logs/JUnit, capped at 16 MiB, into a new campaign subdirectory. Keep errors and refused rows.

The larger calibration, held-out/context study, accepted corpus replay and full regression require smoke review and a subsequent exact authorization. This package does not activate production-balanced-v1.

## Remote commands after authorized setup

~~~sh
cd /workspace/cm-memory-smoke
python -m pip install --require-hashes --only-binary=:all: -r runpod-requirements.lock
python -m pip check
python -m pytest -q tests/test_output_budget.py -p no:cacheprovider --basetemp /workspace/cm-memory-smoke/run-output/pytest-temp --junitxml /workspace/cm-memory-smoke/run-output/focused.xml
python scripts/cm_memory_estimator_study.py --execution runpod --supports 6 8 --families mixed-chain alternating-tree --contexts none --schedules cold warm --repetitions 3 --output-dir /workspace/cm-memory-smoke/run-output/memory
~~~

The controller must run commands sequentially, stop on nonzero status, and bound their runtime; these commands alone are not a lifecycle controller. Set BLAS thread counts to one, record CPU/OS/affinity and installed versions, and keep this host separate from local timing summaries. Expected successful study: 72 recorded representation repetitions, 312 per-window rows, plus unrecorded warmups.

## Lifecycle and account boundaries

Use existing authorized authentication without reading .env files or exposing credentials. If no approved client authentication is available, stop for setup before creating a pod. No credential is uploaded into the worker.

Preflight must record current quote and inventory. If unrelated resources prevent the required zero-account baseline, stop without touching them. Establish a separate lifetime watchdog before workload execution. On success, failure, timeout or controller error, collect available bounded evidence and terminate only this campaign's pod in finally. Then verify no campaign pod remains and record the independent account inventory. If another task created resources concurrently, report that fact rather than claiming account-zero or deleting them.

## Copy-paste approval

~~~text
I authorize CM-MEMORY-SMOKE-20260827-192909 exactly as specified in RUNPOD-AUTHORIZATION.md, RUNPOD-UPLOAD-MANIFEST-FINAL.json and RUNPOD-WHEEL-LOCK.json: one disposable Secure CPU pod, python:3.13.15-slim-bookworm, at most $0.20/hour, 20 minutes and $0.10 total; only the listed uploads and pinned binary wheels; no source builds or optional backend/corpus work; focused tests and the stated smoke only; collect evidence, terminate in finally and verify postflight.
~~~
