# CM Remaining-Test Orchestration Results

Date: 2026-08-26  
Campaign: `orchestration-20260826-213058`

## Executive result

The immediately runnable local gates passed. The trace machinery is correct
and bounded across all three integrated benchmark boundaries. No repository
artifact is a real ordered request/version/context stream, so cache policy,
incremental-family, partial-context economics, selector acquisition, and
native-kernel performance work stopped at their preregistered entry gates.

No dependency was installed, no Runpod pod was created, and no performance or
reuse claim is made from the synthetic trace smoke.

## Regression results

| Check | Runtime | Result |
|---|---|---|
| Trace-focused unit suite | project `.venv`, Python 3.13.5 | 12 passed in 1.394 s |
| Focused trace/integration pytest set | system Python 3.10.11, pytest 9.0.2 | 59 passed in 42.69 s |
| Complete repository pytest suite | system Python 3.10.11, pytest 9.0.2 | 380 passed plus 4 subtests in 114.69 s |

The first attempt to invoke pytest from the project virtual environment failed
immediately with `No module named pytest`. The campaign retained the existing
environment and used the established system test interpreter instead of
installing anything. The project virtual environment was used for the 12-test
unit run and all benchmark/trace commands.

JUnit outputs:

- `focused_pytest.xml`
- `full_pytest.xml`

## Sampled trace mechanics

All runs used deterministic seed `20260826`, metrics-only schema
`cm-workload-trace/v1`, one-in-16 sampling, a 1 MiB bound, one output file, and
disabled optional BDD/Numba dependencies.

| Boundary | Raw benchmark rows | Trace events | Expression observations | Drops | Validation / replay | Enabled correctness |
|---|---:|---:|---:|---:|---|---|
| Single expression | 51 | 11 | 8 | 0 | pass / pass | `cm_ok=True`, `bitset_ok=True` on every row |
| Expression family | 34 | 30 | 24 | 0 | pass / pass | BitSet and uncached-CM family rates `1.0` on every row |
| Partial context | 34 | 30 | 27 | 0 | pass / pass | BitSet, restricted BitSet, uncached CM, and cached CM rates `1.0` on every row |

Every validator reported `metrics_allowlist_pass`. Optional ROBDD, CUDD, and
Numba fields are skipped/disabled by protocol and are not test results.

The traces are deliberately sampled and anonymous. The replay artifacts are
logical summaries, not exact request-order cache simulations.

## Gate decisions

- **Real-workload trace:** not run; no named real request stream or owner exists
  in the repository.
- **Cache policy:** deferred; sampled metrics cannot reproduce exact access
  order, cold/warm process transitions, or byte-budget pressure.
- **Incremental family compilation:** deferred; the synthetic generator is not
  a real edit/version history.
- **Partial-context economics:** deferred; the synthetic sliding-window smoke
  validates mechanics but not a natural context stream.
- **Feature selector:** deferred; there is no new independently frozen family
  or demonstrated real `k=13..15` opportunity. The prior Berkeley ABC i10
  held-out failure remains authoritative.
- **Numba/CUDD:** not run; RP-D0 ended at the source-only PLY 3.10 dependency
  gate, and there is no workload or new dependency/cloud authorization.
- **SIMD:** deferred by design until a workload-backed Numba path first wins.

## Exact commands

Focused pytest:

```powershell
python -m pytest -q -p no:cacheprovider `
  --basetemp "C:\Users\brian\.codex\visualizations\2026\08\25\01a037e1-d087-7282-ad91-695522b65c9f\pytest-orchestration-focused-system-20260826-213058" `
  --junitxml "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\focused_pytest.xml" `
  tests\test_cm_workload_tracing.py tests\test_config_context_usage.py `
  tests\test_workload_provenance_columns.py tests\test_partial_context_bench.py `
  tests\test_expression_family_bench.py tests\test_context_caches.py `
  tests\test_cm_persistent_ir_cache.py tests\test_bench_integration.py `
  tests\test_cm_benchmark_audit_integrity.py
```

Full pytest:

```powershell
python -m pytest -q -p no:cacheprovider `
  --basetemp "C:\Users\brian\.codex\visualizations\2026\08\25\01a037e1-d087-7282-ad91-695522b65c9f\pytest-orchestration-full-20260826-213058" `
  --junitxml "docs\audits\2026-08-25-cm-deep-performance\remaining-work\orchestration-20260826-213058\full_pytest.xml"
```

Project-runtime unit gate:

```powershell
.\.venv\Scripts\python.exe -m unittest -v tests.test_cm_workload_tracing
```

The exact three benchmark commands and validator/replay commands are preserved
in `RUN-COMMANDS.md`. All output names were new and refuse-overwrite behavior
remained enabled.

## Repository integrity

- Branch / HEAD remained `main` /
  `0f833bc389778f7f915deb7acd4499d207e0ec21`.
- `cm_ir.py` SHA-256 remained
  `ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`.
- Pre-existing unrelated work was preserved.
- No commit or push was performed.

## Next launch condition

The next valuable campaign begins with a named real workload using default
one-in-16 metrics tracing. A short bounded full trace may be preregistered only
if exact cache replay is necessary and its data-content owner approves it.
Runpod should be used only after that evidence selects a heavy downstream lane.
