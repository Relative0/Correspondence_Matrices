# CM Workload-Intake Campaign Commands

Run from `C:\Users\brian\Documents\CM_Computation`.

## Opportunity-screen unit tests

```powershell
.\.venv\Scripts\python.exe -m py_compile `
  cmbench\tracing\opportunity.py `
  scripts\cm_screen_workload_trace.py `
  tests\test_cm_workload_opportunity.py

.\.venv\Scripts\python.exe -m unittest -v `
  tests.test_cm_workload_opportunity
```

## Representative synthetic screen

```powershell
.\.venv\Scripts\python.exe scripts\cm_screen_workload_trace.py `
  --input "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_single_events.jsonl" `
  --input "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_family_events.jsonl" `
  --input "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_context_events.jsonl" `
  --output "docs\audits\2026-08-25-cm-deep-performance\remaining-work\workload-intake-20260827-002305\combined_opportunity_screen.json" `
  --workload-label synthetic-three-boundary-smoke `
  --evidence-class synthetic --context-stream-kind synthetic
```

Use a new output path for any rerun; existing outputs are refused.

## Validation suites

```powershell
python -m pytest -q -p no:cacheprovider `
  --basetemp "C:\Users\brian\.codex\visualizations\2026\08\25\01a037e1-d087-7282-ad91-695522b65c9f\pytest-workload-intake-focused-20260827-002305" `
  --junitxml "docs\audits\2026-08-25-cm-deep-performance\remaining-work\workload-intake-20260827-002305\focused_pytest.xml" `
  tests\test_cm_workload_opportunity.py tests\test_cm_workload_tracing.py `
  tests\test_config_context_usage.py tests\test_workload_provenance_columns.py `
  tests\test_partial_context_bench.py tests\test_expression_family_bench.py `
  tests\test_context_caches.py tests\test_cm_persistent_ir_cache.py `
  tests\test_bench_integration.py tests\test_cm_benchmark_audit_integrity.py

python -m pytest -q -p no:cacheprovider `
  --basetemp "C:\Users\brian\.codex\visualizations\2026\08\25\01a037e1-d087-7282-ad91-695522b65c9f\pytest-workload-intake-full-20260827-002305" `
  --junitxml "docs\audits\2026-08-25-cm-deep-performance\remaining-work\workload-intake-20260827-002305\full_pytest.xml"
```

