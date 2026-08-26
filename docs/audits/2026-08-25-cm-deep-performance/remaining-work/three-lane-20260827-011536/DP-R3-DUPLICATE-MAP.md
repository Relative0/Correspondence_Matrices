# DP-R3 Pre-change Duplicate Map

Recorded: 2026-08-27

## Measured duplication

The same deterministic file-SHA-256 operation exists in three active paths:

| Location | Implementation | Current caller role |
|---|---|---|
| `scripts/cm_benchmark_provenance.py` | Whole-file `read_bytes()` | Audit source hashes and exact-source snapshot manifests |
| `cmbench/tracing/replay.py` | Streaming, 1 MiB chunks | Trace input provenance |
| `scripts/cm_trace_overhead_study.py` | Streaming, 1 MiB chunks | Trace-overhead result provenance |

All three return the lowercase hexadecimal SHA-256 digest of the exact file
bytes. No caller depends on the buffering strategy. The whole-file variant can
temporarily retain the complete source file, while the streaming variants have
a fixed-size buffer.

## Bounded decision

Consolidate only this operation into `cmbench/reporting/provenance.py`, using
the existing streaming behavior. Keep `scripts.cm_benchmark_provenance` as a
compatibility re-export because accepted benchmark drivers and tests import it
there. Add the shared module to exact-source snapshot lists for every migrated
audit driver.

Do not consolidate JSON writing, result schemas, corpus selection, timing
windows, source-snapshot copying, expression hashing, or trace validation.
Those mechanisms have different contracts and are outside DP-R3.

## Acceptance measurement

- the shared helper must equal `hashlib.sha256(payload).hexdigest()` across a
  payload larger than one chunk;
- the compatibility import must resolve to the shared function;
- source-snapshot/refuse-overwrite regression tests must pass;
- the trace-overhead quick smoke must remain below 30 seconds and preserve
  exact outputs and result hashes.
