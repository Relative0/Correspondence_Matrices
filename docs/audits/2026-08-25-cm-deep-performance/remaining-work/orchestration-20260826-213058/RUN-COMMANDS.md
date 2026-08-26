# CM Remaining-Test Orchestration Commands

Run from `C:\Users\brian\Documents\CM_Computation`. All output paths refuse
overwrite; use a new campaign directory for a rerun.

## Single-expression sampled trace

```powershell
.\.venv\Scripts\python.exe cm_bench.py --sizes 8,12,16 --trials 17 `
  --seed 20260826 --max-depth 5 --expr-style mixed_no_constants `
  --out-prefix "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_single" `
  --cm-trace-jsonl "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_single_events.jsonl" `
  --cm-trace-sample-every 16 --cm-trace-max-bytes 1048576 `
  --cm-trace-max-files 1 --cm-trace-flush-every 1 `
  --no-dd --no-numba --no-sympy --no-espresso --no-bdd-sop --no-robdd
```

## Expression-family sampled trace

```powershell
.\.venv\Scripts\python.exe cm_bench.py --bench-expression-family `
  --sizes 8,12 --trials 17 --seed 20260826 --max-depth 4 `
  --expr-style mixed_no_constants --family-size 8 `
  --family-variant-style composition_mix --family-shared-blocks 4 `
  --family-mutation-rate 0.15 --family-seed 20260826 `
  --family-force-shared-substructure --family-report-hashes --family-no-robdd `
  --out-prefix "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_family" `
  --cm-trace-jsonl "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_family_events.jsonl" `
  --cm-trace-sample-every 16 --cm-trace-max-bytes 1048576 `
  --cm-trace-max-files 1 --cm-trace-flush-every 1 `
  --no-dd --no-numba --no-sympy --no-espresso --no-bdd-sop --no-robdd
```

## Partial-context sampled trace

```powershell
.\.venv\Scripts\python.exe cm_bench.py --bench-partial-contexts `
  --sizes 8,12 --trials 17 --seed 20260826 --max-depth 4 `
  --expr-style mixed_no_constants --partial-contexts 8 `
  --partial-context-style sliding_window --partial-fixed-var-fraction 0.5 `
  --partial-output-mode remaining-vars --partial-reuse-compiled-ir `
  --partial-report-live-vars `
  --out-prefix "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_context" `
  --cm-trace-jsonl "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_context_events.jsonl" `
  --cm-trace-sample-every 16 --cm-trace-max-bytes 1048576 `
  --cm-trace-max-files 1 --cm-trace-flush-every 1 `
  --no-dd --no-numba --no-sympy --no-espresso --no-bdd-sop --no-robdd
```

## Trace validation and logical summaries

Repeat for `single`, `family`, and `context`:

```powershell
.\.venv\Scripts\python.exe scripts\cm_validate_workload_trace.py `
  --input "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_single_events.jsonl" `
  --output "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_single_audit.json"

.\.venv\Scripts\python.exe scripts\cm_replay_workload_trace.py `
  --input "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_single_events.jsonl" `
  --output "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\trace_single_replay.json"
```

