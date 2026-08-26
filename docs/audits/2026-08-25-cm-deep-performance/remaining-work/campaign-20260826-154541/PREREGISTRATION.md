# CM Workload Trace Foundation Preregistration

Campaign: `campaign-20260826-154541`  
Registered: 2026-08-26, before implementation or overhead measurement  
Branch / HEAD: `main` / `0f833bc389778f7f915deb7acd4499d207e0ec21`

## Objective

Implement only Phase 1 of
`CM-REMAINING-WORK-DEPENDENCIES-TESTING-INTEGRATION-PLAN-2026-08-26.md`:
a dependency-free, opt-in, metrics-only workload trace schema, bounded safe
JSONL sink, validator, deterministic logical replay skeleton, benchmark-boundary
integration, and mechanics/overhead validation.

This campaign will not select a cache policy, fit a backend selector, claim
family/context dominance, change production dispatch, install dependencies, or
raise output budgets. Synthetic events test mechanics only.

## Preservation

The worktree already contains the accepted website/audit rerun work and
unrelated untracked `.claude/`, `external/`, `tmp/`, and `The Broken Silence.*`
files. Preserve all of it exactly. Do not stage, commit, push, or inspect
`.env*`/credentials. `cm_ir.py` must remain at its retained SHA-256
`ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`
unless a separately measured trace integration genuinely requires a change;
Phase 1 is expected not to require one.

## Frozen design decisions

- Schema version: `cm-workload-trace/v1`.
- Default content mode: `metrics`; replayable expressions/assignments are out
  of scope.
- Trace path is explicit and refuses overwrite.
- Disabled tracing uses a null sink and creates no file.
- Event payload keys are allow-listed; arbitrary `repr`, expression text,
  variable names, source paths, environment values, and exception text are
  forbidden.
- Sink failures disable/drop tracing and never fail CM computation.
- Output is bounded by bytes and file count; rotation paths also refuse
  overwrite; final-cap drops are explicitly counted and marked where space
  permits.
- Replay preserves session/sequence order and does not simulate performance or
  execute expressions in this phase.
- All new tooling refuses overwrite and records input SHA-256.

## Tests

Required focused coverage:

1. schema/event round trip and invalid version/type/key/value refusal;
2. metrics privacy allow-list and no raw content;
3. null sink no-file behavior;
4. base and rotation overwrite refusal;
5. byte/file bound and dropped-event accounting;
6. simulated writer failure cannot escape into the caller;
7. truncated/corrupt JSONL is reported and not silently accepted;
8. validator and replay refuse overwrite and record hashes;
9. multi-session merge/order validation;
10. explicit benchmark boundary events do not change results.

Run the focused tests, the existing audit/backend/cache/context tests, and the
full suite after implementation. No test asserts hardware speed.

## Overhead protocol and gate

- Use a frozen deterministic set of representative expressions and supports.
- Prebuild expressions and keep truth/reference construction outside timing.
- Compare identical compile/evaluate operations with the null sink and metrics
  JSONL sink in paired round-robin order.
- Use at least 101 paired rounds per case after warmup and report per-case and
  aggregate medians, dispersion, event counts, bytes, and exact output matches.
- Charge event construction, JSON encoding, writes, flushing, and close to the
  enabled arm; report close separately as well.
- Disabled/null tracing must show no material whole-call regression. Enabled
  metrics tracing targets under 2% whole-call overhead and under 5 microseconds
  per emitted event. If enabled capture fails this target, retain the safe
  tooling only if useful, reduce event frequency to session/call boundaries,
  and do not recommend continuous production capture.
- Treat effects near noise as inconclusive. This is a tooling gate, not a CM
  performance claim.

## Runpod authorization and cap

Brian explicitly requested Runpod for compute-heavy work. After the local trace
foundation passes, one fail-closed dependency feasibility campaign may run with
a self-imposed total cap of `$0.25` (RP-D0): verify pinned CPython 3.13 Numba,
llvmlite, and `dd.cudd` wheels, licenses/identities, CPU flags, and tiny exact
smokes. It must install only inside the disposable pod/container, record
resolved versions/hashes, terminate in `finally`, and save a zero-pod
postflight inventory. No representative native benchmark is authorized by this
preregistration.

## Decisions

- Keep: exact, bounded, scrubbed, fail-contained tooling that passes correctness
  and has acceptable disabled-path overhead.
- Revise: excessive enabled overhead by reducing trace frequency without
  changing measured CM semantics.
- Reject/revert: semantic changes, unbounded retention, leaked raw content,
  overwrite, escaped trace I/O failures, or material disabled-path regression.
