# CM Workload-Intake Opportunity Screen Preregistration

Registered: 2026-08-26T17:23:05Z  
Local date: 2026-08-27

## Repository preservation

- Root: `C:\Users\brian\Documents\CM_Computation`
- Branch / HEAD: `main` / `0f833bc389778f7f915deb7acd4499d207e0ec21`
- Accepted `cm_ir.py` SHA-256:
  `ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`
- Preserve the dirty worktree, website work, audit outputs, `.claude/`,
  `external/`, `tmp/`, and `The Broken Silence.*` exactly.
- Do not read `.env*`, credentials, tokens, or private configuration.
- No commit, push, dependency installation, cloud resource, or external write
  is authorized by this campaign.

## Starting finding

A repository-wide Python call-site scan found no active non-benchmark
application or service consuming CM. Current entry points are the benchmark
CLI, audit/diagnostic scripts, rendering/deployment utilities, and the isolated
remote worker. Existing corpora are benchmark inputs, not ordered real request,
version, or context streams.

`cmbench.tracing.replay` validates events and produces deterministic logical
ordering and basic counts. It does not apply the documented collection-volume
or capability gates for cache, family, context, selector, or native work.

## Hypothesis

A small, dependency-free, read-only opportunity screen can prevent invalid
downstream campaigns by reporting:

- declared evidence class (`real`, `synthetic`, or `unknown`);
- sampling, drops, sessions/process lifetimes, and phase evidence;
- preparation, family-version, context-transition, and eligible-support volume;
- which exact-replay capabilities are absent from metrics-only V1 events;
- conservative follow-up decisions tied to the accepted minimum targets.

## Scope

- Add one pure analysis module under `cmbench/tracing/`.
- Add one refuse-overwrite CLI under `scripts/`.
- Add focused unit tests.
- Run it on the three synthetic trace-mechanics artifacts from
  `orchestration-20260826-213058`.
- Record a consumer/workload map and future workload-intake instructions.

## Non-goals

- No trace schema change.
- No public wrapper, compiler, cache, selector, backend, or output change.
- No cache-policy simulation, expression replay, or performance claim.
- Declaring evidence `real` is provenance supplied by the trace owner; the tool
  cannot prove production origin from anonymous metrics.
- Synthetic volume never authorizes workload-dependent implementation.

## Acceptance gates

1. Input traces are validated using the existing strict loader.
2. Input hashes and threshold values are recorded.
3. Backend duplicates from the same logical call do not inflate selector call
   counts.
4. Sampled or dropped traces are rejected for exact cache replay.
5. Family/context/selector/native follow-up remains false unless provenance and
   required volume/capabilities are present.
6. Output refuses overwrite.
7. Focused tests pass on Python 3.13 and the established system pytest runtime.
8. Existing trace and full-suite correctness remain clean.

