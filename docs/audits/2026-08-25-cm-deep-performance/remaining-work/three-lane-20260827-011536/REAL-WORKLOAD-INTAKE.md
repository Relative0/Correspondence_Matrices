# Real Workload Intake Gate

The repository still has no real application/caller trace. Frozen formulas,
synthetic benchmarks, audit drivers, and the remote benchmark worker are not a
substitute for ordered application traffic.

## What the workload owner must provide

Copy `WORKLOAD-MANIFEST-TEMPLATE.json` to a new, uniquely named JSON file and
replace every `REPLACE_ME` value. Declare:

- application/system and caller boundary;
- requested artifact and exact output-order contract;
- expected evaluations per expression and process/cold-start lifecycle;
- output, temporary-memory, and cache budgets;
- initial capture duration or call count;
- separate approvals for anonymous metrics, replayable expressions,
  replayable contexts, and external upload.

Only `approvals.metrics_capture` is needed for the existing anonymous,
allowlisted metrics trace. Expression/context replay and external upload stay
false unless their distinct data handling has actually been approved.

The initial capture is fixed at one event in 16 and bounded by explicit byte
and file counts. The validator rejects unknown fields, unsupported enums,
negative/unbounded trace storage, or attempts to increase the initial sampling
rate.

## Validate before integration

```powershell
.\.venv\Scripts\python.exe scripts\cm_validate_workload_manifest.py `
  --input "path\to\owner-declared-manifest.json" `
  --output "path\to\new-validation-result.json"
```

The output file is created exclusively and includes the exact input SHA-256.
Proceed only when `validation_status` is `pass` and
`ready_for_metrics_capture` is `true`. A valid template is deliberately
reported as not ready.

## Integration sequence

1. Add the existing opt-in `JsonlTraceSink` at the named caller boundary, not
   as ambient compiler telemetry.
2. Carry the owner-declared workload label and artifact/timing boundary into
   the allowlisted metrics only. Do not record expression text, variable names,
   paths, environment data, credentials, or tokens.
3. Run the quick caller correctness test with tracing off and one-in-16 tracing
   on; returned artifacts and output ordering must be byte-identical.
4. Capture within the declared byte/file limit, validate every JSONL rotation,
   and run `scripts/cm_screen_workload_trace.py` with `--evidence-class real`.
5. Select at most one follow-up lane that clears its accepted volume and
   capability gate. Sampled anonymous metrics cannot be promoted into exact
   cache replay, incremental edit replay, or context-assignment replay.
6. Keep data local unless `approvals.external_upload` is explicitly true and
   the exact destination has separately been authorized.

If the real caller lives in another repository, use a new task with access to
both repositories and preserve this manifest, its validation output, and the
caller repository state in the handoff.
