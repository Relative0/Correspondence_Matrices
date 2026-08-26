# CM Remaining-Work Campaign Results

Date: 2026-08-26  
Campaign: `campaign-20260826-154541`  
Branch / starting HEAD: `main` / `0f833bc389778f7f915deb7acd4499d207e0ec21`

## Outcome

Phase 1 produced a dependency-free, off-by-default, metrics-only trace
foundation. It preserves exact benchmark results, refuses overwrite, bounds
bytes and rotation count, validates an allow-listed schema, contains writer
failures, and supports deterministic logical replay summaries without
executing expressions.

Full-rate event capture is too expensive for routine use and is rejected.
The retained opt-in default emits one workload observation per 16 calls. This
sampled mode passed the preregistered whole-call overhead gate, but not the
per-emitted-event gate; it is therefore suitable only for bounded diagnostic
collection, not continuous production telemetry or cache-policy replay.

No CM evaluation, backend selection, output layout, output guard, cache key,
or accepted default dispatch changed. `cm_ir.py` remains byte-identical at
SHA-256 `ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`.

## Implemented surface

- `cmbench/tracing/schema.py`: `cm-workload-trace/v1` event and payload
  allow-list with strict value validation.
- `cmbench/tracing/sink.py`: null sink and bounded, exclusive-create JSONL
  sink with rotation, explicit drops, flush control, and I/O-failure
  containment.
- `cmbench/tracing/replay.py`: corrupt/duplicate detection, deterministic
  multi-session logical ordering, trace hashes, and metrics summaries.
- `cmbench/tracing/integration.py`: anonymous benchmark-boundary observations
  for single expressions, expression families, and partial-context streams.
- `cmbench/config.py`, `cmbench/context.py`, and `cm_bench.py`: explicit opt-in
  trace configuration and CLI. The trace default is sampled at 1/16; full
  capture requires an explicit `--cm-trace-sample-every 1` diagnostic choice.
- `scripts/cm_validate_workload_trace.py` and
  `scripts/cm_replay_workload_trace.py`: refuse-overwrite validation and
  logical replay tooling with input SHA-256.
- `scripts/cm_trace_overhead_study.py`: deterministic paired round-robin
  mechanics/overhead study.
- `tests/test_cm_workload_tracing.py`: schema, privacy, bounding, corruption,
  overwrite, failure-containment, sampling, integration, and exactness tests.

## Overhead results

All three studies used the same deterministic supports (`k=8,12,16`), 101
paired round-robin repetitions per support, identical complete packed output,
and prebuilt expressions. There were zero exact-output mismatches, dropped
events, or trace I/O failures.

| Arm | Events charged | Bytes | Median trace/null ratio | IQR | Decision |
|---|---:|---:|---:|---:|---|
| V1 full, two CM events/call | 607 | 469,065 | 1.3037 | 1.2143–1.4108 | Reject |
| V2 full, one CM event/call | 304 | 246,586 | 1.1173 | 1.0535–1.2219 | Reject |
| V3 deterministic 1/16 sampling | 20 | 16,435 | 1.0052 | 0.9880–1.0329 | Keep as bounded diagnostic |

V3 per-support median ratios were 1.0071 (`k=8`), 1.0075 (`k=12`), and
1.0029 (`k=16`). Its aggregate median delta was 3.4 microseconds per call.
The whole-call ratio passes the `<=1.02` gate. The diagnostic amortized value
per emitted event was about 328 microseconds and fails the 5-microsecond event
gate; this metric includes paired timing noise from the 15 non-emitting calls
per sample and close cost, but is conservatively treated as a failure.

Raw paired rows, summaries, trace JSONL, and trace-audit JSON are preserved in
this directory under the `trace_overhead*` names. The V1 and V2 negative
results were not overwritten after their implementation refinements.

## Correctness and integration validation

| Validation | Result | Time |
|---|---:|---:|
| Venv focused trace unit suite | 12 passed | 1.13 s |
| System-Python trace/config/cache/family/context integration slice | 59 passed | 34.95 s |
| Complete repository suite on final code | 380 passed + 4 subtests | 93.46 s |
| Python compile check for changed Python files | Pass | — |
| `git diff --check` | Pass; line-ending warnings only | — |
| Retained `cm_ir.py` SHA-256 | Exact match | — |

Exact commands:

```powershell
.\.venv\Scripts\python.exe -m unittest -v tests.test_cm_workload_tracing

python -m pytest -q -p no:cacheprovider --basetemp "C:\Users\brian\.codex\visualizations\2026\08\25\01a037e1-d087-7282-ad91-695522b65c9f\pytest-trace-focused-20260826" tests\test_cm_workload_tracing.py tests\test_config_context_usage.py tests\test_workload_provenance_columns.py tests\test_partial_context_bench.py tests\test_expression_family_bench.py tests\test_context_caches.py tests\test_cm_persistent_ir_cache.py tests\test_bench_integration.py tests\test_cm_benchmark_audit_integrity.py

python -m pytest -q -p no:cacheprovider --basetemp "C:\Users\brian\.codex\visualizations\2026\08\25\01a037e1-d087-7282-ad91-695522b65c9f\pytest-full-trace-20260826"

.\.venv\Scripts\python.exe scripts\cm_trace_overhead_study.py --output-prefix docs\audits\2026-08-25-cm-deep-performance\remaining-work\campaign-20260826-154541\trace_overhead_v3_sample16 --supports 8,12,16 --rounds 101 --sample-every 16
```

## Runpod RP-D0 result

The campaign and worker tooling were implemented and their local dry run
passed. The fixed guards were one secure CPU pod, image
`python:3.13.5-slim`, maximum `$0.20/hour`, 20-minute lifetime, and total cap
`$0.25`. The worker downloads binary wheels only for NumPy 2.3.2, Numba
0.67.0, llvmlite 0.49.0, and `dd` 0.6.0; hashes them; records license
metadata; and runs tiny exact Numba packed-word and `dd.cudd` restriction
checks. It makes no performance claim.

After Brian supplied exact authorization, RP-D0 created one secure two-vCPU
`cpu3c` pod at `$0.06/hour`. It stopped at dependency resolution after 45.88
seconds, terminated successfully, and cost `$0.000765`. The independent
postflight inventory reports zero pods.

This is a retained negative dependency finding. PyPI supplied matching CPython
3.13 Linux wheel metadata for NumPy 2.3.2, llvmlite 0.49.0, Numba 0.67.0, and
`dd` 0.6.0. Resolution then failed because `dd` declares
`astutils>=0.0.5`, while PyPI publishes `astutils` 0.0.6 only as a source
distribution. The binary-only rule correctly refused it before installation,
imports, or exactness smokes. Therefore `dd.cudd`, Numba exactness, versions,
and licenses were not accepted by this run; they remain untested rather than
failed.

Primary metadata checked 2026-08-26:

- PyPI `astutils` 0.0.6 lists only a 9.3 kB source distribution, released
  2024-04-15, BSD-3, SHA-256
  `e9a6f31b243ecfc3c7c84dd2f145cf5de83e475b650d2a6b781cfa713ad15427`:
  https://pypi.org/project/astutils/
- The maintained `dd` documentation states that compatible Linux wheels
  contain the compiled `dd.cudd` module and describes its licensing:
  https://github.com/tulip-control/dd

The failed audit and command tails are preserved under
`runpod_dependency_feasibility/`; the live-resource result is preserved in
`runpod_postflight_after_rpd0_inventory.json`.

### RP-D0 Run 2

Brian separately authorized a second pod to build only the pinned pure-Python
`astutils` source distribution. Run 2 used a new preregistration, scripts, and
refuse-overwrite directory and carried the first `$0.000765` as a cost reserve.
It found and downloaded the pinned setuptools 84.0.0 and wheel 0.48.0 wheels,
but the offline build-tool installation failed because wheel 0.48.0 declares
`packaging>=24.0` and the build-tool wheelhouse had omitted that transitive
wheel. The astutils source was never downloaded or executed, and target
dependencies and exactness smokes were never reached.

This is an attributable orchestration defect, not a dependency-feasibility
finding. Run 2 terminated after 32.20 seconds at an incremental cost of
`$0.000537`; cumulative RP-D0 cost is `$0.001302`. The independent Run 2
postflight reports zero pods. PyPI currently publishes packaging 26.3 as a
`py3-none-any` wheel with SHA-256
`d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c`:
https://pypi.org/project/packaging/

Run 2 evidence is preserved under `runpod_dependency_feasibility_run2/`, with
pre/post inventories in `runpod_run2_preflight_inventory.json` and
`runpod_run2_postflight_inventory.json`.

### RP-D0 Run 3 — final verdict

Brian explicitly authorized a third and final pod with packaging 26.3 added to
the offline build-tool wheelhouse. Run 3 verified and installed the pinned
setuptools 84.0.0, wheel 0.48.0, and packaging 26.3 wheels. It then downloaded
and hash-verified the official `astutils` 0.0.6 source distribution and built
the pure-Python wheel `astutils-0.0.6-py3-none-any.whl` (6,620 bytes; SHA-256
`67f0b270ff1da2bea46c104b935ac5e50fe3d31f0887aff27d6b929a3c0b9add`).

Target dependency resolution then failed closed because `dd==0.6.0` requires
`ply>=3.4,<=3.10`. The binary index offered only PLY 3.11, which is outside
that constraint. PyPI's official PLY 3.10 file listing confirms that version
has only the source archive `ply-3.10.tar.gz` (SHA-256
`96e94af7dd7031d8d6dd6e2a8e0de593b511c211a86e28a9c9621c275ac8bacb`):
https://pypi.org/project/ply/3.10/

This is the final RP-D0 feasibility verdict under the authorized contract:
`dd==0.6.0` cannot be installed as a clean dependency-resolved environment
when `astutils` is the only permitted source build. No target installation,
`pip check`, imports, Numba exactness smoke, or `dd.cudd` restriction smoke was
reached. Numba and CUDD therefore remain untested, not failed, and this run
makes no performance claim.

Run 3 used one secure two-vCPU `cpu3c` pod at `$0.06/hour`, ran for 38.77
seconds, cost `$0.000646`, and brought cumulative RP-D0 spending to
`$0.001948`. The pod terminated successfully and the independent postflight
reported zero pods. Evidence is preserved under
`runpod_dependency_feasibility_run3/`, with pre/post inventories in
`runpod_run3_preflight_inventory.json` and
`runpod_run3_postflight_inventory.json`. The third-and-final authorization is
consumed; no further pod is authorized.

## Limitations

- The current traces are mechanics/overhead evidence, not real workload
  traces. They cannot establish cache, family, partial-context, selector, or
  native-kernel economics.
- Sampling destroys complete request order and therefore is not sufficient for
  exact offline cache-policy replay. A bounded dedicated full trace can be
  requested explicitly for a short named workload, with its overhead charged.
- Metrics-only traces do not contain replayable expressions or raw contexts.
- RP-D0 Run 3 corrected the build-tool wheelhouse and successfully built the
  authorized pure-Python `astutils` wheel, but clean target resolution is still
  blocked by the additional source-only PLY 3.10 dependency required by
  `dd==0.6.0`.
- No production selector, cache policy, CUDD path, Numba path, SIMD path, or
  dependency was integrated.

## Recommended next work

1. Stop RP-D0 under the current dependency/source-build contract. A future
   retry would require a wholly new approval for the pinned PLY 3.10 source
   distribution or an explicitly accepted dependency-metadata exception; it
   is not justified without a real native-lane workload.
2. Use default sampled tracing on a named real workload to screen traffic
   shape. Use a short, separately approved full trace only when exact request
   order is needed for cache replay.
3. Do not start RP-C1, RP-N1, selector acquisition, or incremental compiler
   implementation until a real workload clears the entry gates in the
   remaining-work plan.
