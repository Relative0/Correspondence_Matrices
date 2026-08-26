# CM Workload-Intake Opportunity Screen Results

Date: 2026-08-27  
Campaign: `workload-intake-20260827-002305`

## Executive result

The repository contains no genuine non-benchmark CM workload to launch. Its
active CM consumers are the benchmark CLI, audit/diagnostic scripts, and the
isolated remote benchmark worker. Historical circuit/formula corpora are valid
benchmark evidence but are not ordered application request, edit/version, or
context streams.

A missing dependency-free workload-opportunity screen was implemented. It
validates trace inputs through the existing strict loader, hashes them, applies
the accepted collection thresholds, deduplicates per-backend measurements of
the same logical call, records missing replay capabilities, and refuses to
promote synthetic or sampled evidence into downstream implementation work.

No CM preparation, evaluation, cache, dispatch, output, trace schema, or API
default changed. No dependency, cloud resource, commit, or push was used.

## Implemented files

- `cmbench/tracing/opportunity.py`
- `scripts/cm_screen_workload_trace.py`
- `tests/test_cm_workload_opportunity.py`

The CLI requires an explicit workload label and declared evidence class:
`real`, `synthetic`, or `unknown`. Provenance is reported as owner-declared and
is never presented as something the anonymous metrics can prove.

## Consumer and workload map

| Surface | Role | Real ordered workload? | Trace status |
|---|---|---|---|
| `cm_bench.py` | Synthetic/frozen-corpus benchmark driver | No | Single/family/context boundaries integrated |
| `cm_remote_worker.py` | Isolated benchmark request compiler/evaluator | No | Remote benchmark result metrics; not a workload owner |
| `scripts/cm_*audit*.py`, selector and ablation scripts | Audit/research tooling | No | Reproducible evidence outputs, not application traffic |
| `cm_build*.py`, `cm_ir.py`, `bitset_backend.py` | Library/compiler implementation | No caller population by themselves | Must not receive ambient global telemetry |
| `cm_render.py` / `cm_lm.py` | Small algebra/rendering utility | No performance request stream found | Not an eligible workload source |
| Historical JSONL/circuit corpora | Frozen formula/circuit inputs | No | Benchmark/corpus evidence only |

`README.md` also describes the repository as a system that “benchmarks and
validates” Boolean-expression backends. No FastAPI, Flask, service, application
queue, policy engine, or other non-benchmark CM caller was found in the scoped
Python tree.

## Screen results on available traces

All input traces came from the synthetic three-boundary orchestration smoke and
were explicitly declared `synthetic`.

| Input | Events | Sessions | Sampling | Drops | Relevant observations | Decision |
|---|---:|---:|---:|---:|---|---|
| Single expression | 11 | 1 | 1/16 | 0 | 0 prepare requests; 0 eligible `k=13..15` calls | Collect named real metrics trace |
| Expression family | 30 | 1 | 1/16 | 0 | 3 family IDs; 21 candidate transitions | Collect named real metrics trace |
| Partial context | 30 | 1 | 1/16 | 0 | 3 streams; 21 transitions | Collect named real metrics trace |
| Combined | 71 | 3 | 1/16 | 0 | Same synthetic populations combined | Collect named real metrics trace |

None meets the accepted real-workload targets, and synthetic provenance alone
would block promotion even if raw counts were larger.

The screens also make capability boundaries explicit:

- sampled traces cannot drive exact cache replay;
- metrics V1 lacks parent-version/change-set and replayable expression data for
  incremental compilation;
- metrics V1 stores context digests/overlap, not assignments;
- the current trace lacks per-call current-versus-best counterfactual timings
  needed to calculate selector opportunity `O`;
- Numba/native break-even requires prototype import/JIT/copy timings and a
  measured `q*`.

## Correctness and reliability validation

| Check | Result |
|---|---|
| New Python 3.13 opportunity-screen unit tests | 5 passed in 0.024 s |
| Combined Python 3.13 tracing and opportunity tests | 17 passed in 1.241 s |
| Expanded focused pytest set | 64 passed in 42.23 s |
| Complete repository pytest suite | 385 passed plus 4 subtests in 93.66 s |
| JSON and JUnit artifact validation | pass |
| Accepted `cm_ir.py` SHA-256 | unchanged |

Focused tests cover logical-call deduplication, sampled-cache refusal, complete
cache-field acceptance, synthetic non-promotion, threshold validation, input
hashing, and refuse-overwrite behavior.

## Ranked next endeavors

1. **Named real workload capture.** Identify the actual application, operator,
   policy/version process, or context-query stream that CM is intended to
   serve. Capture default one-in-16 metrics at its caller boundary.
2. **Lane-specific capture upgrade.** Only after the screen shows adequate real
   volume, add the minimum fields needed for the selected lane: bounded full
   cache access order, replayable version deltas, approved context assignments,
   or counterfactual selector measurements.
3. **DP-R2 temporary-memory policy decision.** Independently valuable safety
   work, but changing defaults requires Brian's explicit API-policy decision.
   A decision memo can be prepared without changing behavior.
4. **DP-R3 audit-tool consolidation.** Safe local maintainability work if no
   real workload is available; it must preserve timing windows, corpus roles,
   refusal behavior, and source snapshots.
5. **New selector corpus.** Acquire/freeze VTR or another independent family
   only after real `k=13..15` traffic reaches the volume and opportunity gate.
6. **Numba/CUDD/SIMD.** Reopen only after workload evidence selects the lane and
   new dependency/cloud authorization is granted. RP-D0's source-only PLY 3.10
   blocker remains the current installation result.

## Decision

Continue in the current task for repository-local safety or tooling work. Move
to a new task when a genuine external application/workload is supplied if that
integration has its own repository or substantial domain context. The included
prompt makes that handoff self-contained.
