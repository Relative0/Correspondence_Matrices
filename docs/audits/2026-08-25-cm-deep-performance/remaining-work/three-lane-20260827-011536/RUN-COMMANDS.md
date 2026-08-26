# Three-Lane Campaign Commands

Run from `C:\Users\brian\Documents\CM_Computation`. Every evidence-producing
tool refuses to overwrite its output; use new paths for reruns.

## Workload manifest

```powershell
.\.venv\Scripts\python.exe scripts\cm_validate_workload_manifest.py `
  --input "docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\WORKLOAD-MANIFEST-TEMPLATE.json" `
  --output "docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\WORKLOAD-MANIFEST-TEMPLATE-VALIDATION.json"
```

## DP-R2 diagnostic

```powershell
.\.venv\Scripts\python.exe scripts\cm_output_budget_policy_probe.py `
  --output "docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\DP-R2-OUTPUT-BUDGET-PROBE.json" `
  --supports 8 10 12 14 --repetitions 7
```

## DP-R3 quick smoke

```powershell
.\.venv\Scripts\python.exe scripts\cm_trace_overhead_study.py `
  --output-prefix "docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\dpr3_trace_overhead_smoke" `
  --supports 8,12 --rounds 3 --sample-every 16
```

This is an exactness/integration smoke, not an overhead estimate. Use the
already established longer paired protocol for any overhead claim.

## Dependency-free Python 3.13 tests

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  cmbench\reporting\provenance.py cmbench\tracing\workload_manifest.py `
  scripts\cm_validate_workload_manifest.py scripts\cm_output_budget_policy_probe.py `
  scripts\cm_benchmark_provenance.py scripts\cm_trace_overhead_study.py `
  tests\test_cm_workload_manifest.py

.\.venv\Scripts\python.exe -m unittest -v `
  tests.test_cm_workload_manifest tests.test_cm_workload_opportunity `
  tests.test_cm_workload_tracing
```

## Focused and full regression

```powershell
python -m pytest -q -p no:cacheprovider `
  --basetemp "docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\pytest-expanded-focused" `
  --junitxml "docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\focused_pytest.xml" `
  tests\test_cm_workload_manifest.py tests\test_cm_workload_opportunity.py `
  tests\test_cm_workload_tracing.py tests\test_output_budget.py `
  tests\test_config_context_usage.py tests\test_workload_provenance_columns.py `
  tests\test_partial_context_bench.py tests\test_expression_family_bench.py `
  tests\test_context_caches.py tests\test_cm_persistent_ir_cache.py `
  tests\test_bench_integration.py tests\test_cm_benchmark_audit_integrity.py

python -m pytest -q -p no:cacheprovider `
  --basetemp "docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\pytest-full" `
  --junitxml "docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\full_pytest.xml"
```
