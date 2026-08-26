# CM Real-Workload Intake Contract

Use this contract before starting cache, family, context, selector, Numba,
CUDD, or SIMD performance work.

## 1. Name the workload

Record:

- workload owner and application/repository;
- caller boundary that requests CM work;
- exact requested artifact: complete packed truth vector, remaining-variable
  vector, symbolic query, one assignment, equivalence result, or another named
  interface;
- cold/warm process lifetime and expected repetition;
- data-content approval for anonymous metrics and, separately, replayable
  expressions/contexts if later required;
- memory, latency, and cache budgets.

Do not label BX1, B2, EPFL, Berkeley ABC i10, generated families, or generated
context grids as a real workload.

## 2. Capture metrics first

Tracing stays off by default. For a benchmark-compatible caller, use a new
refuse-overwrite path and default one-in-16 sampling:

```powershell
.\.venv\Scripts\python.exe cm_bench.py <the-real-workload-options> `
  --cm-trace-jsonl docs\audits\YYYY-MM-DD-cm-workload\metrics.jsonl `
  --cm-trace-sample-every 16 `
  --cm-trace-max-bytes 1048576 --cm-trace-max-files 1
```

An external application should emit through an explicit caller-owned
`TraceSink`. Do not add global telemetry to `CMIRBuilder`. The adapter must hash
workload/expression/context identities, use only the V1 allow-list, contain
writer failures, and preserve the application's exact result on trace failure.

## 3. Validate, summarize, and screen

```powershell
.\.venv\Scripts\python.exe scripts\cm_validate_workload_trace.py `
  --input <metrics.jsonl> --output <metrics-audit.json>

.\.venv\Scripts\python.exe scripts\cm_replay_workload_trace.py `
  --input <metrics.jsonl> --output <logical-summary.json>

.\.venv\Scripts\python.exe scripts\cm_screen_workload_trace.py `
  --input <metrics.jsonl> --output <opportunity-screen.json> `
  --workload-label <approved-label> --evidence-class real `
  --context-stream-kind natural
```

Use `--complete-workload` only when the owner confirms the trace covers the
entire smaller workload. Use `--complete-family-population` only when every
available real revision is included. The tool records these as declarations;
it cannot verify provenance from anonymous data.

## 4. Minimum opportunity targets

- Cache: 10,000 prepare requests or a declared complete smaller workload, at
  least two process lifetimes, and a working-set phase change.
- Family: 200 real version transitions across 20 family IDs, or a declared
  complete smaller revision population.
- Context: 500 transitions across five natural streams, in actual order.
- Selector/kernel: 50 independent formulas and 500 calls at `k=13..16`; the
  selector itself additionally needs `k=13..15` opportunity `O >= 3%`.

Absence is a useful result. Do not manufacture volume with loops or generated
variants.

## 5. Upgrade capture only for the selected lane

- Cache: bounded full access order, cache key, artifact/retained bytes,
  preparation cost, lookup/serialization costs, and process boundaries.
- Family: parent version, change set/digests, options, support changes, and
  approved replayable serialized expressions.
- Context: approved variable-index/value assignments, phase boundaries,
  overlap, query/output kind, and manager/process lifetime.
- Selector: current decision plus equivalent per-call counterfactual backend
  timings on a frozen shadow slice.
- Native: observed `q`, kernel share, output conversion, import/JIT/copy costs,
  and memory budgets.

Replayable data has a different privacy/content contract from metrics-only V1.
Preregister and approve it separately.

## 6. Runpod boundary

Runpod is appropriate only after the screen selects a heavy lane. Every pod
needs exact authorization for image, uploads, dependencies/source builds,
price, lifetime, total cap, and teardown. The three RP-D0 authorizations are
consumed. Do not create a fourth pod implicitly.

