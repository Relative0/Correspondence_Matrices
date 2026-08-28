# Commands and reproducibility

> **2026-08-28 update:** The actual successful zero-volume smoke used `runpod-authorized-20260827-213104/runpod_http_smoke_controller_v3.py`, with `http_transport_preflight_v2.py` and independent `verify_http_ephemeral_outcome.py`. It passed 70 tests and 312 exact/ok window rows and was deleted. See [the result](runpod-authorized-20260827-213104/HTTP-EPHEMERAL-RESULT-20260828.md) and [continuation](RUNPOD-CONTINUATION-20260828.md). The v3 output name is consumed and must not be reused. Earlier no-launch/no-inventory statements below are historical preparation notes; the larger command remains unauthorized.

Run from C:/Users/brian/Documents/CM_Computation. Output paths below identify retained runs; they must not be reused or deleted. Choose a fresh directory/name for any permitted rerun.

## Actually executed locally

- Read the user attachment, all 15 ordered authority documents, applicable AGENTS search, scoped sources and current git state.
- Metadata-only interpreter/dependency inspection: venv Python 3.13.5; system Python 3.10.11 for pytest.
- scripts/cm_validate_workload_manifest.py against the retained template, writing WORKLOAD-TEMPLATE-VALIDATION.json.
- Tiny pre-change defect reproduction, saved in PRECHANGE-DEFECTS.json and REFUSAL-ESTIMATE-PRECHANGE.json.
- Pre-change selected pytest: 6 expected regression failures, prechange_pytest.xml.
- Focused tests after successive fixes: 60 / 64 / 68 / 69 / 70 passed. Final authoritative invocation:

~~~powershell
python -m pytest -q tests/test_output_budget.py -p no:cacheprovider --basetemp docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/.pytest_release_focused --junitxml docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/release_focused_pytest.xml
~~~

- Virtualenv py_compile on changed implementation/driver.
- Three tiny driver iterations; final command:

~~~powershell
.\.venv\Scripts\python.exe scripts/cm_memory_estimator_study.py --output-dir docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/local-smoke-final
~~~

- Official public PyPI JSON metadata reads only. A connection-reset failure was retried with the required sandbox approval. No package/source download or install ran.
- Wheel selection and Python 3.13.15/Linux dependency-marker closure from retained metadata.
- JSON/JSONL/CSV/JUnit parsing and source/upload hash verification; final validation is recorded in VALIDATION.json.
- git diff --check, git diff review, git status --short; no staging/commit/push.

## Next authorized smoke

See RUNPOD-AUTHORIZATION.md. It has the exact first-smoke commands and the lifecycle prerequisites. No launcher was executed and no pod inventory was queried.

## Larger study design — NOT AUTHORIZED

The driver supports this design only on Runpod, after the smoke is reviewed and a new exact source/corpus upload package is approved:

~~~sh
python scripts/cm_memory_estimator_study.py --execution runpod --supports 6 8 12 16 --families mixed-chain shared-diamond wide-and alternating-tree reconvergent-xor --contexts none half all --schedules cold warm --repetitions 5 --corpora bx1 b2 epfl --output-dir /workspace/cm-memory-study/NEW-UNUSED-DIRECTORY
~~~

This command's per-child deadline and 20-minute internal study deadline may leave explicit skipped rows. Do not raise caps or remove refusals to force completion. Its archive needs accepted corpus files and the existing context/frozen-truth helpers, which are intentionally absent from the first smoke upload package.

Full pytest also remains unrun and Runpod-only. Freeze a complete test/source/fixture manifest and optional-dependency plan first; do not infer a full-suite pass from the 70 focused tests.
