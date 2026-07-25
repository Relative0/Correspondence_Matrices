# Final Implementation Summary

Date: 2026-07-26

## Outcome

The audit and continuation implemented one measured compile optimization,
fixed three correctness/reporting defects, added a central explicit-output
budget, added reproducible benchmark tooling and raw data, declared the
development test dependency, and added 29 regression tests.

Final verification:

```text
python -m pytest -q
223 passed in 135.56s
```

The scoped code commit `4be1543` independently passed its clean index snapshot:

```text
188 passed in 109.57s
```

## Code changes

| File | Change |
|---|---|
| `cm_ir.py` | Replaced quadratic AND/OR complement scans with constant-time set membership |
| `bitset_backend.py` | Isolated mutable words scratch per thread to prevent concurrent corruption |
| `cm_bench.py` | Stopped reporting unvalidated large-\(n\) results as correct; sampling now controls status |
| `cmbench/expr/partial_contexts.py` | Preserved fixed values in `full-vars` reference enumeration |
| `cmbench/output_budget.py` | Added representation-aware output/temporary-byte admission and typed status/refusal contracts |
| `cm_build.py`, `cm_build_lazy.py`, `cm_build_pair.py` | Applied bounded dense-output admission to public builders |
| `cm_remote_worker.py`, `cm_remote_executor.py`, `cm_runpod_protocol.py` | Carried byte limits and typed statuses through local/remote execution |
| `cmbench/config.py` | Added explicit output and temporary-byte configuration |
| `scripts/cm_performance_audit.py` | Added smoke/local/large core benchmarks with exact validation, wall/CPU time, dispersion, GC, allocation, RSS, environment, and raw JSONL |
| `requirements-dev.txt` | Declared pytest for the existing development suite |

`bitset_backend.py`, `cm_bench.py`, and `cm_ir.py` already contained substantial
uncommitted V4 changes before this audit. Only the scoped changes described
above belong to this audit; unrelated working-tree changes were preserved.

## Tests added

- `tests/test_cm_ir_wide_associative.py`
  - wide unique-operand retention;
  - complement order independence;
  - exact truth-table equivalence.
- `tests/test_words_thread_safety.py`
  - synchronized raw-AST and CM-node words execution.
- `tests/test_large_n_correctness_status.py`
  - unvalidated `None`, sampled pass, and sampled failure.
- `tests/test_partial_full_vars_reference.py`
  - fixed-axis broadcast semantics.
- `tests/test_output_budget.py`
  - dense and packed boundary decisions;
  - pre-allocation refusal and explicit reduced output;
  - temporary-memory admission;
  - equivalence and remote typed statuses;
  - old/new remote field round trips.

## Benchmark tooling and data

The dated audit directory contains:

- controlled `before_*` and `after_*` JSON/JSONL;
- final batched CPU/throughput and unbatched memory/RSS results;
- cold/warm results;
- whole-pipeline CSV and cProfile data;
- focused before/after cProfile files;
- a machine-readable manifest.

No unstable performance assertion was added to pytest.

## Measured optimization

| Case | Before | After | Speedup |
|---|---:|---:|---:|
| AND width 128 | 22.063 ms | 14.105 ms | 1.56× |
| AND width 256 | 58.606 ms | 31.033 ms | 1.89× |
| AND width 512 | 145.749 ms | 64.893 ms | 2.25× |
| OR width 512 | 112.321 ms | 55.248 ms | 2.03× |

The focused 512-term AND cProfile improved 4.96× and eliminated about 1.30
million complement predicate calls. Exact structural signatures and truth
outputs were unchanged. Peak traced allocation was unchanged.

This is a wide-compilation improvement, not a claim that every CM workload is
2× faster.

## Correctness results

- Prior shared-scratch probe: 12/12 synchronized calls corrupt in the first
  round.
- Final shared-node probe: 0 mismatches in 600 synchronized calls.
- Large-\(n\) execution without an oracle: now `None`, not `True`.
- Zero-mismatch independent sampling: `True`.
- Any sampled mismatch: `False`.
- `full-vars` partial reference now repeats the conditioned function across
  fixed-variable axes.

## Compatibility implications

- Public file formats and column names are unchanged.
- Large-\(n\) correctness values may change from misleading `True` to `None`
  when validation did not run. This is an intentional semantic correction.
- Historical generated CSV files were not rewritten.
- Thread-local scratch preserves results and concurrent throughput, but scratch
  memory now scales with active evaluation threads.
- Correct `full-vars` partial-context benchmark outputs may differ from prior
  incorrect runs.
- No default engine threshold or output representation changed.
- Direct APIs now refuse explicit artifacts above 256 KiB unless the caller
  supplies a different budget. Benchmark and remote paths use the stricter
  64 KiB plus legacy 16-variable defaults.

## Dependencies and configuration

- No new runtime dependency.
- `pytest>=8.0` is now declared only through `requirements-dev.txt`.
- New CLI/config limits are `cm_max_output_bytes` (64 KiB by default) and
  optional `cm_max_temporary_bytes`.
- Worker count and cache-size defaults remain unchanged.

## Unresolved

1. Large caches are entry-bounded rather than byte-bounded.
2. Threaded remote-worker concurrency is not admission-controlled.
3. CLI imports dominate short runs.
4. Frozen corpus replay does not cover all workflows and contains correlated
   repeated expressions.
5. `n=0` semantics are undefined.
6. Tiled output, real-domain workloads, same-environment CUDD queries, and
   cross-platform CI remain future work.

See `CM-OPTIMIZATION-BACKLOG.md` for ordered prerequisites and validation
criteria.
