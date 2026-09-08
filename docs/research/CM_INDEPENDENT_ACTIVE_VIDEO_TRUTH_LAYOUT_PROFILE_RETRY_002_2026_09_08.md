# Independent active-workflow gate retry 002

Date: 2026-09-08  
Status: instrumentation-only correction frozen before retry execution

Attempt 001 sealed the workload, source, gates, 300-row profile schedule, and 24-row
fresh-process memory schedule. All 300 profile rows completed, but the memory controller
stopped before its first row because its adapter called `_LineReader.next`; the existing
H6 infrastructure exposes `_LineReader.get`. The adapter also emitted/read `event`
fields and plain commands while H6 uses `phase` fields and JSON command objects.

The attempt-001 freeze, all 300 profile rows, and the zero-byte memory file are retained.
No memory value or component summary existed when the fault was found. Retry 002 changes
only the adapter method, handshake field, and command decoding. The admitted workflow,
occurrences, oracles, arms, lifecycles, boundaries, repetitions, memory metrics,
materiality thresholds, candidate criteria, exclusions, and continuation decisions are
unchanged. Both profiling and memory are rerun under the new source closure.
