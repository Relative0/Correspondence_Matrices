# Copy-paste prompt — CM maximal safe remaining-work campaign

Project root:

`C:\Users\brian\Documents\CM_Computation`

## Mission

Carry the remaining CM performance, memory-safety, real-workload-intake, and
optional-backend readiness work as far as can reasonably be taken in one
coherent campaign without inventing workload evidence, changing public
defaults without approval, or drifting into already rejected experiments.

Work autonomously through every safe repository-local phase. Do not stop just
because the repository still lacks a real application trace: record that gate,
then complete the independent temporary-memory estimator, refusal-path,
compatibility-replay, and optional-lane readiness work. Ask Brian only when a
genuine approval boundary is reached, and consolidate approval questions into
one precise request wherever possible.

This campaign covers all of the following:

1. detect and validate any newly supplied real-workload manifest or trace;
2. harden and validate dense, bigint, and word-packed temporary-memory
   estimates without changing defaults;
3. test refusal-before-allocation and exact-result behavior across public
   materialization and conversion boundaries;
4. evaluate the proposed memory-policy profiles against accepted benchmark
   corpora and held-out structural stress cases, clearly distinguishing this
   from real-workload compatibility;
5. implement only behavior-neutral, backward-compatible policy/provenance
   plumbing that is justified by the estimator results and tests;
6. select at most one cache, family, partial-context, selector, or native lane
   if and only if genuine workload evidence clears its entry gate;
7. update the readiness assessment and exact approval packages for another
   selector corpus, Numba/SIMD, CUDD, or Runpod without performing an
   unauthorized download, build, installation, or cloud launch;
8. preserve negative findings and produce a self-contained handoff.

Do not perform the separate website-results audit in this campaign. Another
agent is handling it.

## 1. Preserve and reconcile the repository first

Before changing anything:

1. Read every applicable `AGENTS.md` completely.
2. Record the actual branch, HEAD, remotes, `git status --short`, tracked
   modifications, staged files, and untracked paths.
3. Record available Python interpreters and relevant dependency versions.
   Prefer `.venv\Scripts\python.exe`; the established system Python may be
   needed for pytest if the virtual environment still lacks it.
4. At prompt creation, the known base was `main` at
   `4dbfffc1db749e85401d533c5a07cb529a41eb37`, but do not assume it is still
   current. Website work may have been committed or may still be in progress.
5. Expect concurrent or newly completed website work, including
   `deliverables_n22_24\master_explainer_2026_08_03\website_audit_2026-08-27\`
   and possible edits under the master-explainer directory. Do not modify,
   stage, revert, overwrite, delete, reconcile, or attribute those files to
   this campaign.
6. Also preserve local-only `.claude/`, `external/`, `tmp/`, generated
   `.pytest*` scratch directories, and `The Broken Silence.*`. Never read or
   expose `.env*`, credentials, tokens, private configuration, or credential
   caches.
7. Do not use broad staging commands. Do not commit or push unless Brian
   explicitly authorizes the final reviewed file set. Do not deploy or
   publish anything.
8. Do not install dependencies, download corpora/source archives, clone
   repositories, create Runpod resources, upload files, or perform other
   external writes without a new exact authorization.
9. Web research against official/primary sources is authorized. Record the
   search date and direct URLs. Do not rely on remembered current versions.
10. Recheck status before every substantive edit and again before handoff so
    concurrent website changes stay isolated.

Create a unique campaign directory without overwriting accepted artifacts,
for example:

`docs\audits\2026-08-25-cm-deep-performance\remaining-work\maximal-safe-YYYYMMDD-HHMMSS\`

Use refuse-overwrite outputs throughout.

## 2. Read the authoritative evidence before acting

Read these in order:

1. `README.md`
2. `deliverables_n22_24\CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md`
3. `deliverables_n22_24\CM_BENCHMARK_REFRESH_CLAIM_MAP_ADDENDUM_2026-08-03.md`
4. `docs\audits\2026-08-25-cm-deep-performance\CM-DEEP-PERFORMANCE-AUDIT.md`
5. `docs\audits\2026-08-25-cm-deep-performance\CM-BENCHMARK-RESULTS.md`
6. `docs\audits\2026-08-25-cm-deep-performance\CM-RESEARCH-LEDGER.md`
7. `docs\audits\2026-08-25-cm-deep-performance\CM-OPTIMIZATION-BACKLOG.md`
8. `docs\audits\2026-08-25-cm-deep-performance\reruns\campaign-20260826-132038\OPTIMIZATION-BACKLOG-UPDATE.md`
9. `docs\audits\2026-08-25-cm-deep-performance\remaining-work\campaign-20260826-154541\NEXT-AGENT-HANDOFF.md`
10. `docs\audits\2026-08-25-cm-deep-performance\remaining-work\workload-intake-20260827-002305\RESULTS.md`
11. `docs\audits\2026-08-25-cm-deep-performance\remaining-work\workload-intake-20260827-002305\CM-REAL-WORKLOAD-INTAKE.md`
12. `docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\RESULTS.md`
13. `docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\DP-R2-TEMPORARY-MEMORY-POLICY-DECISION.md`
14. `docs\audits\2026-08-25-cm-deep-performance\remaining-work\three-lane-20260827-011536\REAL-WORKLOAD-INTAKE.md`
15. `docs\audits\2026-08-25-cm-deep-performance\CM-REMAINING-WORK-DEPENDENCIES-TESTING-INTEGRATION-PLAN-2026-08-26.md`

Follow the current claim map and latest accepted artifacts whenever older
reports conflict. Use older reports only for history.

Inspect the current implementations and tests relevant to the work, especially:

- `cmbench/output_budget.py`
- `cm_ir.py`
- `cm_build.py`, `cm_build_pair.py`, and lazy/parallel builders
- `cmbench/config.py`
- `cm_bench.py`
- `cm_runpod_protocol.py`
- `cm_remote_executor.py`
- `cm_remote_worker.py`
- `bitset_backend.py`
- `cmbench/backends/`
- `cmbench/tracing/`
- `scripts/cm_output_budget_policy_probe.py`
- `scripts/cm_validate_workload_manifest.py`
- `scripts/cm_validate_workload_trace.py`
- `scripts/cm_screen_workload_trace.py`
- `tests/test_output_budget.py`
- the current benchmark and audit drivers

Use commit history only when it clarifies why a current boundary exists.

## 3. Conclusions that remain settled

Do not spend time trying to revive or optimize any of these:

- CM and sharing-aware CSE-flat are kernel-equivalent on accepted evidence;
  the tiny residual is not an optimization opportunity.
- CM preparation is the larger credible constant-factor surface, but current
  scaling is with structural DAG size, not an unfolded-tree catastrophe.
- BitSet led accepted whole-call comparisons through `live_k=16`.
- Flat bigint remained fastest through `live_k=12`; the word-packed engine won
  at `live_k=16`. Do not restore a universal support-only threshold below 16.
- The BX1-trained feature selector failed untouched i10 transfer with
  catastrophic routes. Do not tune a replacement on i10.
- Complete packed output has unavoidable time and storage proportional to
  `2^k / w` for the same artifact.
- Synthetic cache, family, and context experiments do not establish production
  economics. Sampled metrics are not exact access-order replay.
- BDD construction, restriction, symbolic query, and exhaustive extraction are
  different artifacts and timing windows.
- A quotient or structural operator result is not semantic XOR timing.
- Engineering cache keys are not a proof of formal global CM canonicality.
- Raising an output guard is not an optimization.
- The prior three RP-D0 authorizations are consumed. The final standard
  install attempt stopped at source-only PLY 3.10; it did not test Numba or
  CUDD correctness/performance.

## 4. Preregister the campaign and rank hypotheses

Before implementation, create `PREREGISTRATION.md` with:

- exact repository state and preserved concurrent files;
- timing, artifact, output-order, and memory measurement definitions;
- calibration versus held-out structural slices;
- cold subprocess versus warm-process schedules;
- repetitions, deterministic seeds, timeouts, output limits, and stop rules;
- planned raw schemas and unique output paths;
- acceptance/rejection gates below;
- a ranked hypothesis table including mechanism, evidence, affected files,
  expected benefit, correctness risk, memory risk, maintenance cost,
  dependencies, validation, and decision.

Priority order:

1. correctness, refusal, overflow, cache-insertion, or protocol defects;
2. temporary-memory estimator accuracy and reliability;
3. behavior-neutral compatibility/provenance plumbing;
4. genuine real-workload intake and opportunity screening;
5. one workload-selected prototype, if any;
6. optional dependency/corpus/cloud readiness only.

Do not tune gates after seeing held-out results.

## 5. Lane A — real-workload detection and intake

First search the current repository for any new owner-declared workload
manifest or genuine non-benchmark caller/ordered trace added since the latest
audit. Frozen formulas, circuit corpora, audit scripts, benchmark invocations,
generated variants, and remote benchmark workers are not real workloads.

If no genuine workload exists:

1. Validate the retained manifest template and record that it is structurally
   valid but not metrics-ready.
2. Produce `REAL-WORKLOAD-STATUS.md` listing the exact missing owner inputs:
   application/repository, caller boundary, requested artifact and ordering,
   process lifecycle, repetitions, budgets, capture duration, and separate
   metrics/replay/external-upload approvals.
3. Do not pause the campaign. Continue through all independent memory and
   readiness phases.
4. At handoff, give Brian one concise copy-paste intake block, not a sequence
   of small questions.

If a genuine manifest exists:

1. Validate it with the strict existing validator and preserve its input hash.
2. Proceed only if `validation_status=pass` and
   `ready_for_metrics_capture=true`.
3. Add the existing opt-in, fail-contained `JsonlTraceSink` at the named caller
   boundary, not as ambient compiler telemetry.
4. Prove tracing-off and sampled-tracing-on results and output ordering are
   byte-identical.
5. Capture within the declared one-in-16, byte, file, duration, and content
   limits. Keep data local unless exact external upload was separately
   approved.
6. Validate, logically summarize, and screen the trace as `evidence-class
   real`.
7. Select at most one downstream lane only if it clears the accepted gate:
   cache: 10,000 prepares or a declared complete smaller workload plus two
   process lifetimes and a phase change; family: 200 transitions across 20
   families or a declared complete smaller population; context: 500 natural
   transitions across five streams; selector/native: 50 independent formulas
   and 500 calls at `k=13..16`, with selector opportunity at `k=13..15` at
   least 3%.
8. Request replayable expressions, deltas, or contexts only for the one lane
   selected, with a separate content approval.

Do not manufacture volume or convert synthetic traces into real evidence.

## 6. Lane B — audit the current memory model and materializers

Create a concise map that distinguishes:

- explicit output bytes;
- estimator-declared temporary bytes;
- Python allocations visible to `tracemalloc`;
- NumPy/native allocation and process RSS/high-water behavior;
- retained caches/memos versus temporary buffers;
- cold import/allocator effects versus warm steady state;
- dense Boolean/uint8, Python bigint, and word-packed representations;
- preparation, kernel, materialization, conversion, serialization, pair,
  partial/reduced, equivalence, and remote-wrapper boundaries.

Trace structural DAG nodes `s`, live support `k`, compiled operations `m`,
operator mix, maximum simultaneously live full-width buffers, context-fixed
support, output representation, and output size. Determine exactly where the
current estimate is computed, checked, recorded, and ignored.

Explicitly audit integer overflow, negative inputs, enormous shifts, malformed
budgets, and estimation work that could itself allocate or take exponential
time. Estimation must be bounded and fail closed.

## 7. Lane C — build a reproducible estimator study

Extend the existing probe or create one focused reusable driver under
`scripts/`. It must:

- use only already available dependencies;
- run cold cases in isolated subprocesses and warm cases in-process;
- support dense, bigint, and word-packed paths where those paths actually
  exist;
- separate preparation, evaluation, materialization, and conversion windows;
- record `s`, `k`, `m`, operator mix, liveness/buffer information, output
  bytes, current estimate, candidate estimate, `tracemalloc` peak, and process
  RSS/high-water information when available;
- label RSS methodology and platform limitations precisely;
- never call `psutil` unless it is already installed and recorded; prefer
  standard-library/OS facilities or a child-process high-water measurement;
- save every repetition, cold/warm state, failures, refusals, and timeouts;
- use deterministic seeds, typed outcomes, and refuse-overwrite output;
- cap local support/output/memory so it fails closed instead of stressing
  Brian's computer;
- emit JSON or JSONL raw data plus a CSV summary and environment metadata.

Build structurally diverse cases rather than only scaling one formula:

- sharing-heavy and sharing-light DAGs;
- shallow/wide and deep/narrow shapes;
- AND/XOR/NOT mixtures and representative accepted-corpus formulas;
- fixed-context support reductions;
- pair and conversion cases where applicable;
- calibration and genuinely held-out structural families.

Use enough repetitions to distinguish allocator noise, but keep the initial
local campaign bounded. Provide larger runs as explicit opt-in commands; do
not launch Runpod merely to increase repetitions.

## 8. Lane D — derive and validate candidate estimators

Do not fit a single empirical multiplier to the earlier four dense points.
Derive representation-specific models from actual allocation/liveness
mechanisms. Account for fixed overhead, final copies, full-width live buffers,
array/object headers where relevant, tail storage, and structural operation or
liveness terms.

Split calibration and held-out cases before fitting. Report:

- underestimate count and maximum underestimate;
- overestimate distribution and worst overestimate;
- monotonicity in output size and relevant structural/liveness terms;
- cold and warm results separately;
- `tracemalloc` and RSS/native evidence separately;
- false admission and false refusal counts under each candidate profile;
- cost of computing the estimate itself.

A production estimator change may be retained only if all of the following
hold:

1. it follows from the implementation's allocation/liveness structure rather
   than a post-hoc universal multiplier;
2. it is deterministic, cheap, overflow-safe, and monotone where required;
3. it does not underestimate any calibration or held-out measured case under
   the preregistered measurement definition;
4. it includes an explicitly documented safety margin and does not claim to be
   an OS-enforced RSS guarantee;
5. focused exactness, refusal, and full regression tests pass;
6. it changes no caller default, output guard, artifact, ordering, or routing.

If no honest estimator clears those gates, retain the improved diagnostic
tool, model comparison, and negative result. Do not force an implementation.

Record an estimator version in diagnostics and machine-readable artifacts if
an estimator is changed. Keep legacy behavior distinguishable.

## 9. Lane E — refusal, exactness, and state-safety validation

Whether or not a new estimator is retained, expand focused tests and bounded
diagnostics for:

- dense, packed bigint, and word-packed paths;
- direct public materializers;
- pair construction and internal fallback checks;
- partial/reduced outputs and all-fixed/none-fixed contexts;
- equivalence/comparison paths;
- parallel entry points where active;
- output conversion and serialization;
- local and mock-remote request handling;
- cache/memo behavior on refusal.

For every relevant path prove:

- identical exact output and ordering when admitted;
- typed refusal before the material allocation being guarded;
- no partial artifact, stale cache entry, retained failed memo, or partial
  serialized result;
- deterministic boundary behavior at limit-1, limit, and limit+1;
- legacy `None`/missing-field semantics remain unchanged;
- malformed limits fail predictably.

Treat any real exactness, stale-cache, partial-output, or protocol defect as
P0. Fix it with regression tests before making performance claims.

## 10. Lane F — candidate policy compatibility replay

Without changing defaults, evaluate at least:

- current legacy behavior;
- the memo's candidate `production-balanced-v1` resolved values:
  benchmark/new remote: 64 KiB output, 16 MiB estimated temporary, `k<=16`;
  direct public materializers: 256 KiB output, 64 MiB estimated temporary;
- at least one stricter and one more permissive diagnostic profile if useful
  for locating the frontier.

Replay accepted corpora plus the preregistered held-out structural-stress
slice. Record admitted/refused counts, reason, representation, estimate,
observed memory, exactness, and false-admission/false-refusal diagnostics.

Call this benchmark-corpus compatibility only. It cannot estimate real caller
compatibility in the absence of a real workload.

Do not activate `production-balanced-v1`. Brian must explicitly approve both
the numeric profiles and the possibility that formerly admitted calls become
typed refusals.

## 11. Lane G — behavior-neutral protocol preparation

Only after the estimator work clarifies the required fields, decide whether a
small additive protocol change is justified now. A retained change must be
strictly backward-compatible and behavior-neutral:

- optional policy/estimator version identifier;
- echo of resolved numeric limits in diagnostics/results;
- missing or `null` legacy requests retain their current meaning;
- local, mock-remote, and worker paths agree on `ok`, `reduced`, and
  `refused`;
- old serialized fixtures still load unchanged;
- no default or numeric value is silently injected into a legacy request.

If this cannot be accomplished as one small attributable change, produce a
tested prototype or protocol specification and defer production integration.
Do not create a remote pod to test serialization; use local/mock fixtures.

## 12. Lane H — workload-selected implementation, if eligible

Implement at most one of the following only when a real trace clears its gate
and the requested artifact/timing boundary matches:

- byte/cost-aware process-local cache with exact invalidation and RSS plateau;
- minimal incremental/family compilation over real ordered versions;
- partial-context routing/restriction over natural context streams;
- feature-selector development using a newly frozen corpus, never i10 for
  tuning;
- Numba word kernel for a measured repeated kernel-dominant batch;
- CUDD restriction/query work for a genuinely symbolic/context artifact.

Preregister the one selected prototype separately. Compare against the
strongest applicable incumbent on identical artifacts and full task-total
boundaries. Charge lookup, bookkeeping, JIT/import, copying, extraction,
serialization, and selector overhead. Use paired rows and a held-out slice.

Minimum integration gates:

- cache/incremental/context: at least 5% task-total net improvement, bounded
  retained memory/RSS, zero stale or exactness failures;
- selector: zero catastrophic held-out routes, low regret, and transfer beyond
  the tuning family;
- Numba/native: at least 10% target task-total improvement after import/JIT/
  copy/output costs and a real observed repetition count;
- CUDD: equivalent requested task artifact wins; construction or restriction
  alone cannot stand in for exhaustive output.

If no real workload clears a gate, do not implement any of these. Record the
evidence gate as functioning correctly.

## 13. Lane I — optional corpus, dependencies, SIMD, CUDD, and Runpod

Use current primary sources to refresh only the readiness facts that may have
changed: official Python/NumPy/Numba/llvmlite/dd package metadata and release
notes, official CUDD/dd documentation, official NumPy SIMD/CPU dispatch docs,
official candidate circuit-corpus repositories/licenses, and official Runpod
lifecycle documentation.

Produce `OPTIONAL-LANES-READINESS.md` containing:

- current versions, dates, supported Python/platform wheels, and direct URLs;
- the exact PLY 3.10 source-only blocker and the distinction between standard
  dependency resolution and `--no-deps` exceptions;
- artifact/timing equivalence requirements for CUDD;
- CPU feature and cold/warm JIT/copy requirements for Numba/SIMD;
- licensing/provenance requirements for another independently frozen circuit
  family;
- why i10 is consumed held-out evidence and cannot tune a replacement model;
- the workload signal required before each lane becomes worthwhile;
- a go/no-go verdict for every lane.

If a lane is genuinely eligible, prepare one consolidated, exact authorization
request covering image, files uploaded, dependency names/versions/hashes,
whether source building is allowed, corpus/source download, maximum pod price,
maximum lifetime, total campaign cap, timeouts, teardown in `finally`, and a
zero-pod postflight. Do not launch it. The previous three Runpod approvals do
not carry forward.

Do not prepare or run a broad matrix of pods. Authorize only the next eligible
smoke, with larger work contingent on its result.

## 14. Benchmark and statistical integrity

All performance and memory comparisons must:

- use identical expressions, semantic support, contexts, and output ordering;
- compare equivalent artifacts;
- separate preparation, kernel, wrapper, materialization, conversion,
  serialization, cache, and estimator windows;
- retain paired per-formula/per-context rows;
- distinguish blocked, round-robin, cold-process, and warm-process schedules;
- report medians, dispersion, failures, refusals, timeouts, and skips;
- use cluster-aware intervals where formulas share a circuit/family;
- preserve failures in denominators and avoid survivor bias;
- record hardware, OS, Python, dependencies, affinity if controlled, seeds,
  commands, source hashes, and output hashes;
- avoid claims above the current safe guard without a fail-closed protocol;
- treat changes near noise as inconclusive.

No hardware-sensitive timing assertion belongs in the ordinary unit-test
suite.

## 15. Implementation discipline

For each candidate change:

1. save the pre-change result;
2. make one coherent attributable edit;
3. run focused correctness tests;
4. run paired measurements on the same inputs;
5. check cold/warm allocation and retained memory;
6. test at least one held-out structural family;
7. retain only reproducible useful gains or real reliability fixes;
8. if rejected, revert only that campaign's experimental edit and preserve the
   negative result;
9. never weaken validation, guards, exactness, or output ordering to improve a
   number.

Use `apply_patch` for source edits. Match surrounding style. Do not reformat
unrelated code. Preserve accepted raw artifacts byte-for-byte.

## 16. Validation ladder

Run, in proportion to the retained changes:

1. syntax/compile checks with the repository virtual environment;
2. direct dependency-free unit tests for new helpers;
3. focused pytest for output budgets, tracing/workload, remote protocol,
   materialization, backends, and every modified path;
4. quick estimator/refusal smoke;
5. representative calibration and held-out estimator study;
6. accepted-corpus compatibility replay;
7. complete repository pytest;
8. JSON/JSONL/CSV schema and parse validation;
9. source-manifest/hash validation;
10. `git diff --check` on implementation files;
11. final `git status --short` and diff review excluding concurrent website
    work.

Do not delete pre-existing pytest scratch directories. Put this campaign's
temporary test data under its unique directory or an ignored temporary path,
and do not stage it.

## 17. Required deliverables

Under the unique campaign directory create:

- `PREREGISTRATION.md`
- `RESULTS.md`
- `REAL-WORKLOAD-STATUS.md`
- `MEMORY-PATH-MAP.md`
- `MEMORY-ESTIMATOR-MODEL.md`
- `POLICY-COMPATIBILITY-REPLAY.md`
- `OPTIONAL-LANES-READINESS.md`
- `OPTIMIZATION-BACKLOG-UPDATE.md`
- `NEXT-AGENT-HANDOFF.md`
- `RUN-COMMANDS.md`
- environment and source-manifest JSON
- raw per-repetition memory data in JSON/JSONL or CSV
- machine-readable estimator/profile summaries
- focused/full JUnit where pytest is run

`RESULTS.md` must lead with what was implemented, what was rejected, whether
any default changed, whether a real workload existed, and the exact next
approval/input needed. Keep benchmark-corpus compatibility distinct from real
workload compatibility.

The backlog must separate:

- ready to implement;
- implemented and retained;
- needs a real workload;
- needs policy approval;
- needs corpus/dependency/cloud authorization;
- theoretically blocked/different artifact;
- tested and rejected.

The handoff must state:

- exact final branch/HEAD/status;
- files changed by this campaign;
- concurrent website files preserved;
- commands, tests, timings, and results;
- estimator calibration and held-out verdicts;
- exactness/refusal/protocol verdicts;
- unresolved workload inputs;
- optional-lane go/no-go decisions;
- one consolidated approval request if justified;
- exact next commands;
- claims that must not be resurrected.

## 18. Completion and stopping rules

The campaign is complete when all safe local phases have been exhausted, not
merely when the missing real workload is rediscovered. Specifically:

- the actual workload gate has been checked and documented;
- memory paths and current estimator weaknesses are mapped;
- a reproducible multi-representation memory study exists;
- candidate estimators have calibration and held-out evidence;
- a safe estimator is implemented only if it clears every gate;
- refusal, exactness, state safety, and legacy semantics are tested;
- proposed profiles have benchmark-corpus compatibility results without being
  activated;
- any behavior-neutral protocol work is retained or explicitly deferred;
- no cache/family/context/selector/native lane is implemented without real
  eligibility;
- optional dependency/corpus/cloud readiness is current and sourced;
- focused and full validation pass or failures are reported honestly;
- negative findings remain visible;
- concurrent website work is untouched;
- the final handoff consolidates the few remaining user decisions.

Stop and request authorization only for a concrete external write, dependency
installation/build, corpus download, cloud resource, public-default/API-policy
change, commit, push, or approved replayable workload content. Do not ask for
permission merely to continue read-only analysis, local bounded diagnostics,
tests, documentation, or safe behavior-neutral implementation within this
scope.
