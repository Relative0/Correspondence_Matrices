# CM Remaining-Work Dependencies, Testing, and Integration Plan

Date: 2026-08-26  
Research checked: 2026-08-26  
Status: implementation plan; no dependency installation or cloud run is
authorized by this document

## Executive decision

The next work should not begin with CUDD, Numba, or handwritten SIMD. The first
deliverable should be a small, opt-in, dependency-free workload trace and replay
layer. It will establish whether production-like traffic contains enough cache
reuse, real expression revisions, repeated partial contexts, `k=13..15`
selector opportunity, or repeated word-kernel work to justify the corresponding
implementation cost.

The recommended order is:

1. implement trace capture, validation, scrubbing, and deterministic replay;
2. collect real cache, version/family, and context streams without changing
   execution decisions;
3. evaluate cache, incremental, and context policies offline;
4. pursue another frozen selector corpus only if real traffic shows material
   routing opportunity;
5. prototype Numba packed-word evaluation only if repeated word-kernel time is
   material;
6. test native CUDD on context/query workloads, not as a generic exhaustive
   output replacement;
7. consider a compiled SIMD extension only if Numba proves that native packed
   fusion is useful but leaves a measured kernel bottleneck.

Every new path remains optional and fail-closed until it passes exactness,
memory, cold/warm, held-out, cross-host, and operational rollback gates. The
accepted `WORDS_AUTO_MIN_VARS=16` rule remains the default. Berkeley ABC i10 is
consumed held-out evidence and must not be used to tune its replacement.

## Authoritative starting state

- Current repository interpreter: CPython 3.13.5 on Windows x86-64.
- Current environment: NumPy 2.3.2 and `dd` 0.6.0.
- `dd.autoref` is available; `dd.cudd` is not available on this Windows venv.
- Numba, llvmlite, pytest, and psutil are not installed in this venv. Pytest is
  declared in `requirements-dev.txt`; the accepted regression suite does not
  depend on installing it for this plan.
- Existing surfaces already include process-local compiled-IR caches,
  persistent-digest cache experiments, expression-family and partial-context
  benchmark paths, ROBDD timing, backend availability detection, output
  budgets, and an old row-oriented `numba_backend.py` experiment.
- The existing `numba_backend.py` produces byte-per-assignment output. It is not
  the packed-word candidate proposed below and must not be used as equivalent
  evidence for complete packed CM output.
- Latest gates: 368 tests and 4 subtests passed; the three-host preparation
  replication was exact; the existing k16 selector transferred to i10 with
  zero catastrophes; the preregistered feature selector failed and was rejected.

Relevant current integration points:

- `cm_ir.py`: `compile_expr_to_cm_ir_persistent`,
  `compile_expr_to_cm_ir_cached`, and cache diagnostics;
- `bitset_backend.py`: `FlatProgram`, prepared flat evaluation, word planning,
  scratch reuse, and `eval_cm_node_words`;
- `cmbench/config.py`, `cmbench/context.py`, `cmbench/availability.py`, and
  `cmbench/cli.py`: optional feature configuration and availability reporting;
- `cm_bench.py`: `_robdd_partial_context_workload`,
  `time_partial_context_workload`, `run_partial_context_bench`,
  `time_expression_family_workload`, and `run_expression_family_bench`;
- `cmbench/results/`: timing semantics and stable raw/summary schemas;
- `cm_expr_serde.py`: approved expression serialization boundary;
- `cmbench/output_budget.py`: fail-before-allocation output and temporary-memory
  limits.

## Non-negotiable experimental rules

- Preserve exact Boolean semantics, variable order, packed-bit order, output
  type, refusal behavior, and the `Omega(2^k / w)` explicit-output lower bound.
- Keep preparation, lookup, binding, kernel, output conversion, serialization,
  restriction, symbolic query, and exhaustive extraction windows separate.
- Never store raw caller names, source text, paths, secrets, or environment
  values in a default trace. Do not inspect `.env*` to construct metadata.
- Trace capture is off by default. Disabled tracing must not allocate an event
  or acquire a global lock on the normal path.
- A metrics trace and a replayable trace are different artifacts. Metrics-only
  capture is the default; serialized expressions/contexts require a deliberate
  replayable mode and user-controlled storage.
- Preserve every failed, refused, skipped, timed-out, and over-budget row. Do
  not tune or report only survivors.
- Pre-register splits, eligible backends, features, model class, metrics, stop
  rules, seeds, and budgets before opening held-out outcomes.
- No ordinary unit test may assert a hardware-dependent speedup.
- Dependency experiments use isolated venvs or immutable container images. Do
  not add optional packages to the core runtime requirements until a candidate
  clears production integration gates.
- Every Runpod job gets a cost cap, timeout, refuse-overwrite output path,
  explicit termination, and postflight zero-resource inventory. Previous cloud
  approval does not authorize a new campaign.

## Phase 0 — Reproducibility and experimental environment contract

### Deliverables

Create a uniquely dated directory such as:

`docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-YYYYMMDD-HHMMSS/`

Each campaign must contain:

- `PREREGISTRATION.md` written before outcome inspection;
- `ENVIRONMENT.json` with repository commit, dirty-file manifest, interpreter,
  dependencies, OS, CPU flags, affinity, clocks, seeds, commands, and limits;
- source/corpus manifests with URLs, licenses, commit or release pins, sizes,
  and SHA-256 hashes;
- raw JSONL/CSV rows and a schema version;
- paired summaries and cluster-aware intervals;
- failures/refusals/timeouts/skips;
- `RESULTS.md`, `DECISIONS.md`, and `NEXT-AGENT-HANDOFF.md`;
- hashes of every executable script and frozen input;
- a postflight cloud inventory whenever cloud resources were used.

### Environment lanes

1. **Core/local lane:** the unchanged repository venv; no new dependency.
2. **Trace-analysis lane:** initially standard library plus current NumPy and
   pandas. Use `tracemalloc` for Python allocations. Add psutil only if RSS
   sampling cannot be obtained reliably from the host and installation is
   separately approved.
3. **Numba lane:** isolated venv/container pinned to a mutually supported
   Numba/llvmlite pair and the repository's Python/NumPy versions.
4. **CUDD lane:** Linux x86-64 container using a verified `dd.cudd` wheel when
   available; source compilation is a separately recorded fallback, never an
   invisible setup step.
5. **Native SIMD lane:** isolated build image with compiler identity and flags
   recorded. Built artifacts are tied to their ABI and CPU baseline.

### Phase gate

Proceed only when the baseline quick suite, focused backend/cache/context suite,
and full suite are green and the source hashes match the campaign manifest.

## Phase 1 — Dependency-free workload trace foundation

### Proposed code surface

- `cmbench/tracing/schema.py`: typed/versioned event definitions;
- `cmbench/tracing/sink.py`: null sink, bounded JSONL sink, rotation, flushing,
  and failure containment;
- `cmbench/tracing/replay.py`: schema validation and logical-order replay;
- `scripts/cm_validate_workload_trace.py`: scrub/validate/hash/report;
- `scripts/cm_replay_workload_trace.py`: offline replay with refuse-overwrite;
- focused tests under `tests/test_cm_workload_trace_*.py`.

Prefer an explicit optional `TraceSink` passed through `BenchmarkContext` and
public wrapper calls. Do not introduce ambient global telemetry into
`CMIRBuilder`. Internal cache events can flow through existing diagnostics and
be converted to trace events at the call boundary.

### Event classes

- `session_start` / `session_end`;
- `prepare_request` / `prepare_result`;
- `evaluation_request` / `evaluation_result`;
- `cache_lookup`, `cache_insert`, `cache_evict`, and `cache_reject`;
- `family_version` with prior-version relation;
- `context_transition` and `context_query`;
- `process_restart` or session boundary;
- `failure`, `refusal`, `timeout`, and `trace_drop`.

### Required common fields

- `schema_version`, event ID, session ID, process-local sequence, UTC time, and
  monotonic offset;
- anonymous workload/family/context IDs;
- compiler/schema/options identity and structural digest;
- `s`, estimated or measured `t`, `k`, `m`, primitive operation mix, sharing
  factor, output kind, and output/temporary budget;
- cold/warm/cache state, expected and observed `q` where known;
- preparation, lookup, kernel, conversion, serialization, and total times;
- artifact logical bytes, serialized bytes, retained-node counts, measured
  allocation delta where available, and RSS sample source;
- status and typed failure/refusal reason.

Metrics-only traces store digests, counts, timings, and anonymous IDs. A
replayable trace may additionally store versioned `cm_expr_serde` payloads and
contexts as variable indices plus Boolean values. It must carry a content flag,
remain local unless separately approved, and never silently fall back to raw
`repr(expr)`.

### Trace quality and safety tests

- schema round-trip and forward-version refusal;
- deterministic IDs for identical approved structural inputs;
- truncation/corruption recovery without accepting a partial final event;
- bounded file size, rotation, and explicit dropped-event counts;
- simulated write failure cannot fail the CM computation;
- no raw expression text or variable names in metrics-only mode;
- thread/process IDs cannot collide within a merged trace;
- disabled mode produces no file and no observable semantic change;
- enabled metrics mode median overhead target: under 2% of whole-call time and
  under 5 microseconds per event-bearing call on the representative local
  slice. If that is not met, sample at session/call boundaries rather than
  weakening the gate.

### Collection adequacy targets

These are minimum targets for an informative trace, not claims of statistical
representativeness:

- cache: at least 10,000 prepare requests or one complete smaller production
  workload, at least two process lifetimes, and at least one working-set phase
  change;
- family/edit: at least 200 real version transitions across at least 20 family
  IDs, or every available revision if the real population is smaller;
- partial contexts: at least 500 transitions across at least five natural
  streams, preserving their actual order and phase boundaries;
- selector/kernel: at least 50 independent formulas and 500 eligible calls in
  `k=13..16`, if that traffic exists.

If real use cannot produce these events, report that absence; do not manufacture
a production justification from synthetic traffic.

## Phase 2 — Offline cache economics and safe cache integration

### Replay policies

Evaluate, in identical logical request order:

1. no cache;
2. current entry-count LRU behavior;
3. byte-budgeted LRU;
4. byte-LRU plus minimum-build-cost admission;
5. a size/cost policy based on expected saved preparation time per retained
   byte;
6. an offline future-aware oracle only as an upper bound, never as a deployable
   comparator.

Do not start with TinyLFU. Add frequency sketching only if the real trace shows
recency alone loses material opportunity and the sketch's bytes and update time
are charged.

### Accounting

Report hit, byte-hit, saved-prepare-time, and net-saved-time curves against cache
budget. Charge digesting, lookup, validation, insertion, eviction,
serialization, deserialization, and output conversion. Distinguish serialized
bytes from retained in-memory bytes; shared DAG nodes must not be double-counted.
Validate estimates with `tracemalloc` and RSS plateaus at representative budget
points.

### Correctness and reliability gates

- cache key includes compiler/schema version, normalization/lowering options,
  flattening mode, output/layout contract, and relevant interpreter/native ABI;
- structural digest hits receive an exact O(`s`) validation signature when
  loading a durable artifact; a digest is not promoted to a mathematical
  semantic-equivalence theorem;
- corrupt, truncated, wrong-version, wrong-option, wrong-endianness, and
  deliberately collision-simulated artifacts fail closed and recompile;
- atomic write-then-rename, file locking or single-writer ownership, checksums,
  size caps, and stale temporary cleanup are tested before cross-process reuse;
- eviction never invalidates a live caller-owned artifact;
- cache telemetry cannot recurse into cache operations;
- concurrency tests define whether caches are process-local, thread-safe, or
  explicitly unsupported.

### Integration ladder

1. offline simulator only;
2. experimental cache object behind an explicit benchmark flag;
3. shadow admission decisions while serving the current path;
4. opt-in byte budget for a named workload;
5. production default only after a predeclared task-total win, bounded RSS,
   stable P95 latency, and a clean rollback run.

Default acceptance target to preregister before replay: at least 5% task-total
net time saved on the target trace with the clustered interval below parity,
no more than 2% P95 regression, RSS within the declared budget, and zero stale
or wrong hits. If the trace owner has a different materiality threshold, record
it before viewing policy results.

## Phase 3 — Real expression families and incremental compilation

### Required trace content

For each version transition record the anonymous family/version IDs, parent
version, structural root digest, changed subtree digests or a replayable
serialized version, changed support, `s`, `m`, `q` after the edit, and process
boundary. Independently regenerated random variants do not count as an edit
trace.

### Comparators

1. cold CM compilation;
2. current process-local root/subtree caching;
3. persistent-digest path including validation cost;
4. sharing-aware CSE-flat;
5. a minimal dependency-tracked incremental prototype only after the first
   four are measured;
6. task-matched BDD manager reuse for workloads whose requested query is
   symbolic or context-heavy.

The first incremental prototype should retain immutable nodes and track the
dependency cone from changed subtrees to root analyses/lowering results. Do not
introduce an e-graph unless the trace demonstrates repeated rewrite work large
enough to repay maintenance, extraction, and memory.

### Tests and stop rules

- exact canonical DAG signature, flat program, support, output ordering, and
  packed result for every version;
- adversarial edits that preserve a digest prefix, alter options, commute
  children, change only dead variables, change support, and revert to an older
  version;
- cold restart and replay in a new process;
- retained dependency state and RSS plateau across long version chains;
- cluster results by family, not by individual version;
- reject if change-impact bookkeeping plus validation consumes the saved work,
  if RSS is unbounded, or if the strongest applicable incumbent wins total
  task time.

## Phase 4 — Real partial-context streams and CUDD frontier

### Trace and break-even variables

Capture original and remaining support, number/fraction fixed, transition
Hamming distance, fixed-variable-set Jaccard overlap, reuse distance, contexts
per phase, queries per context, output kind, cache budget, process/manager
lifetime, and whether the caller wants a symbolic answer, one assignment, or a
complete remaining-variable truth vector.

Prioritize real streams near the observed synthetic frontier (`n=16`, roughly
500 contexts, high overlap, and 50%--75% fixed), but retain all other streams so
the analysis does not condition on likely wins.

### Equivalent-artifact comparisons

- complete remaining truth vector: BitSet fixed/restricted, CM compile-once and
  context reuse, ROBDD build-once + restriction + exhaustive extraction;
- single assignment or symbolic query: compare only equivalent single/symbolic
  query artifacts, without charging either side for an unrequested truth table;
- full-variable output: preserve the current exact lift/order contract and
  charge its materialization.

For BDDs, time build, optional reorder, restriction, symbolic query, and
exhaustive extraction separately. Record manager/order lifetime, node counts,
computed-cache/reorder statistics, garbage collection, and peak memory.

### CUDD dependency lane

Use Linux first. PyPI publishes a CPython 3.13 manylinux `dd==0.6.0` wheel, and
the `dd` project documents that compatible Linux wheels include compiled CUDD.
Verify `import dd.cudd`, backend identity, embedded CUDD version, license files,
and a tiny exact cofactor before running a benchmark. If the wheel is
unavailable for the chosen image, stop and request separate approval for a
source build; do not silently fetch/build CUDD inside the timing campaign.

Run fixed, expression-first-occurrence, and preregistered deterministic orders.
Dynamic reordering is a separate arm with reorder time charged. A CUDD win on
restriction alone does not imply a win on exhaustive extraction.

### Context integration gate

Integrate only for a named query/output mode and workload region where held-out
streams show lower task-total cost, bounded nodes/RSS, and no catastrophic
tail. Start behind `backend_preference="cudd"`; keep `auto` unchanged until
shadow routing succeeds on a second host.

## Phase 5 — Another independently frozen selector study

### Traffic gate

Before acquiring a new corpus, compute the opportunity on real traces:

`O = sum(max(0, T_current - T_best_eligible)) / sum(T_current)`.

Proceed only if `k=13..15` contains at least 50 independent formulas and 500
eligible calls and `O >= 0.03` for the target timing boundary, or if a documented
latency/memory SLO makes a smaller volume material. Otherwise retain k16 and
stop.

### Corpus governance

- i10 remains locked historical test evidence and is excluded from all fitting,
  feature selection, threshold selection, and debugging decisions.
- Freeze the next source commit/release, licenses, complete file list, hashes,
  extraction algorithm, seeds, eligibility rules, and formula/circuit clusters
  before timing outcomes.
- Preferred new source: a license-reviewed, commit-pinned combinational subset
  from the official VTR benchmark collection. VTR contains benchmark designs
  and is generally MIT-licensed, with component exceptions documented in its
  license. If conversion from Verilog is required, pin and hash the exact
  synthesis toolchain and command; source parsing/synthesis belongs outside the
  backend timing window.
- Reserve whole design families for final transfer. Outputs/cones from one
  circuit cannot be split across tuning and held-out roles.
- If a second independent licensed combinational source cannot be frozen, do
  not claim broad selector transfer.

### Model development

Use BX1 and explicitly labeled reused-development corpora only. Start with the
current k16 policy, a shallow deterministic decision tree or small rule list,
and a regularized linear model. Candidate features are `k`, `s`, `m`, primitive
operator counts, sharing factor, peak live word buffers, output kind, cache
state, expected `q`, and budget. Do not use measured candidate/backend outcomes
as runtime features.

Cross-validation is grouped by circuit/family. Reject a model before held-out
timing if any development fold has a `>=2x` catastrophic route, if selector
arithmetic is not negligible relative to the saved work, or if a simpler model
has comparable regret.

### Final gates and integration

- raw and CM arms report geomean, median, P95, maximum regret, `>=2x` rate,
  selector overhead, refusal rate, and memory behavior;
- blocked and round-robin schedules remain separate;
- fit on one host and confirm the frozen model on materially different hosts;
- do not refit after opening the new final held-out outcomes;
- first integration is shadow mode that records current and candidate decisions
  while executing only the current path;
- production eligibility requires zero catastrophic held-out routes, clustered
  regret interval no worse than the current policy, material task-total benefit,
  and a fail-closed fallback to k16 when features are missing or over budget.

## Phase 6 — Numba packed-word prototype

### Dependency contract

As of the research date, official Numba 0.67.0 supports Python 3.10--3.14 and
ships CPython 3.13 wheels; it supports NumPy 2.5, so the current NumPy 2.3.2 is
inside the published range. Use the matching llvmlite 0.49.x/LLVM 22 line in an
isolated environment and freeze the resolved wheel hashes. Re-check upstream
support immediately before installation because these versions are temporal.

Do not modify `requirements.txt` initially. Add an experimental lock/manifest
under the campaign directory. A later optional extra such as `cm[numba]` is
appropriate only after acceptance.

### Candidate representation

- consume the existing `FlatProgram`/word plan rather than recursively walking
  Python objects;
- dense contiguous opcode, operand, release, and load arrays;
- `np.uint64` input/output and preallocated scratch buffers;
- one exact mask for the last partial word;
- no Python bigint passed through a fixed-width compiled signature;
- no byte-per-assignment materialization;
- begin with unfused exact operations, then test only measured binary/ternary
  fusions;
- one compilation per stable signature, with compile-cache identity recorded.

The prototype belongs in an experimental backend module. `detect_backends()`
may expose availability, but normal dispatch remains unchanged.

### Timing windows and workload gate

Record dependency import, first JIT, subsequent-process cached compilation,
plan conversion, binding, copies, scratch allocation/reuse, kernel, final mask,
conversion, and total call separately. Test `q` over a logarithmic grid and
derive the measured break-even:

`q* = ceil((T_import + T_jit + T_convert) / (T_reference_kernel - T_jit_kernel))`.

Only continue if a real trace contains enough calls beyond `q*` and word-kernel
time is a material share of the task. Batched synthetic repetition alone is not
a production workload.

### Correctness, memory, and concurrency gates

- differential equality against recursive bigint, flat bigint, current words,
  and direct assignment references on deterministic random, BX1/B2/EPFL, high
  sharing, every operator, constants, fixed bindings, and boundary `k` values;
- odd/non-multiple-of-64 output lengths and exact tail masking;
- input aliasing, non-contiguous arrays, zero-sized or refused allocations,
  and malformed programs fail safely;
- scratch reuse cannot leak bits between evaluations;
- concurrent calls use thread-local or caller-owned scratch and have a defined
  threading layer;
- peak temporary and retained memory are no worse than the declared budget;
- cold/warm and cross-process results are reported separately.

Default continuation threshold: at least 10% task-total improvement on the
trace-defined repeated target region, clustered interval below parity, no
material P95 regression, and no memory growth. Otherwise retain the negative
result and do not integrate.

## Phase 7 — Compiled SIMD only after Numba

A native extension is a second optimization tier, not a parallel first attempt.
Enter this phase only if the Numba packed prototype establishes an end-to-end
win and profiling still attributes material time to word operations or missed
fusion/vectorization.

### Prototype design

- scalar portable reference kernel;
- runtime-dispatched x86-64 AVX2 arm;
- optional AVX-512 arm only on hosts that report the exact required features;
- ternary logic such as `VPTERNLOG` only for patterns proven equivalent to the
  source op sequence;
- contiguous aligned buffers with unaligned-safe fallback;
- deterministic tail handling and no reads beyond allocated buffers;
- GIL release only around code that owns or safely borrows immutable buffers;
- compiler, standard library, flags, ABI, baseline, dispatch table, and binary
  hash recorded.

NumPy's official SIMD documentation describes compile-time baseline/dispatched
kernels and runtime CPU probing. Follow that model: never ship an AVX2/AVX-512
binary as a universal baseline, and test the scalar fallback by explicitly
disabling dispatched features.

### Hardware matrix

- local Windows x86-64 for ABI and fallback correctness;
- at least two Runpod Linux CPU types with recorded flags;
- one AVX2-only or AVX-512-disabled run;
- one AVX-512-capable run only if the provider exposes and records it;
- optional ARM64 is a portability experiment, not required for an x86-only
  candidate unless ARM support is a product requirement.

GPU and multiprocessing remain out of scope unless a real streamed-output API
and kernel-dominant workload first demonstrate that transfer/startup can be
amortized.

## Dependency and approval matrix

| Item | Current state | Planned use | Where | Approval before action |
|---|---|---|---|---|
| Standard library JSONL/tracemalloc | Available | Trace and allocation foundation | Current venv | No new dependency approval |
| NumPy 2.3.2 | Installed | Packed arrays and existing benchmarks | Current/experimental | No |
| pandas | Required by repo | Offline summaries | Current venv | No |
| `dd.autoref` 0.6.0 | Installed | Local correctness/reference BDD | Current venv | No |
| `dd.cudd` 0.6.0 | Missing locally; Linux wheel published | Native BDD contexts | Isolated Runpod Linux image | Yes: new dependency/cloud campaign |
| Numba 0.67.0 | Missing | JIT packed-word prototype | Isolated venv/container | Yes: install |
| llvmlite 0.49.x | Missing | Numba's LLVM binding | Isolated venv/container | Yes: install |
| psutil | Missing | Optional cross-platform RSS samples | Trace-analysis env | Yes: install, only if needed |
| Native compiler/build system | Not selected | AVX2/AVX-512 extension | Isolated build image | Yes: build dependency |
| VTR benchmark sources/toolchain | Not frozen | New selector family | Source staging area | Yes: download; build only if conversion requires it |
| Runpod | Prior campaign finished; zero pods | Linux/CUDD/cross-host studies | Paid external compute | Yes: exact new cost cap |

No package should be installed into the shared repository venv until its lane
has an approved reason. Prefer disposable named venvs or immutable images so a
negative experiment leaves the accepted environment unchanged.

## Unified validation matrix

### Unit and property-style tests without new test dependencies

- deterministic expression generator across every supported operator;
- trace schema, scrubbing, rotation, corruption, and replay;
- cache policy accounting and byte-budget invariants;
- cache key/invalidation matrix;
- exact family transitions and historical-version reappearance;
- context overlap, all-fixed, none-fixed, duplicate and adversarial streams;
- selector missing-feature and budget fallbacks;
- packed-word tail masks, scratch reuse, and buffer ownership;
- availability detection when each optional module is absent or broken.

### Differential correctness

For every experimental evaluator or reuse path, compare the same expression,
support, fixed context, output variable order, and artifact against the trusted
direct assignment reference plus the strongest current applicable engine.
Require zero mismatches; sampling is acceptable only above the safe exhaustive
reference limit and must use frozen seeds and explicit coverage.

### Failure and reliability

- output and temporary-memory refusal before allocation;
- malformed/corrupt/truncated traces and cache artifacts;
- dependency import error, native-library load error, unsupported CPU, JIT
  failure, and CUDD build/reorder failure;
- timeouts preserve typed rows and terminate workers;
- disk full/read-only output simulation;
- interrupted writer leaves no accepted partial artifact;
- all experimental dispatch paths fall back to the current exact path or return
  a typed refusal—never a partial result.

### Performance protocol

- paired per-expression/context/version rows;
- multiple repetitions, medians, dispersion, and clustered intervals;
- one tuning slice and genuinely held-out slices;
- blocked and round-robin schedules reported separately;
- cold process, warm process, and warm artifact cache separated;
- wall clock, CPU time where useful, allocation peak, RSS plateau, retained
  bytes, and output bytes;
- no cross-machine pooling without a host-aware model;
- selector/cache policy decision overhead charged;
- failures and budget refusals retained in denominators where applicable.

### Release integration ladder

1. experimental script/module, not imported by the default path;
2. unit/differential tests and representative local benchmark;
3. frozen held-out and second-host validation;
4. optional explicit configuration;
5. shadow decision/telemetry in the target workload;
6. named canary workload with rollback switch;
7. default only after stable trace economics and documented operational limits.

Each rung gets its own commit-sized coherent change and can be reverted without
altering accepted artifacts or unrelated website work.

## Runpod campaign design and provisional budgets

These are planning caps, not authorization:

| Campaign | Purpose | Provisional cap | Stop condition |
|---|---|---:|---|
| RP-D0 | Verify pinned Numba and `dd.cudd` wheels/imports, CPU flags, licenses, tiny exact smoke | $0.25 | Any dependency/identity/hash failure |
| RP-C1 | CUDD fixed/reorder context smoke on a frozen trace subset | $0.50 | Any mismatch, blended timing, node/RSS limit |
| RP-C2 | Representative CUDD context frontier on two CPU types | $2.00 | No smoke win or budget frontier crossed |
| RP-N1 | Numba packed-word cold/warm smoke and exactness | $0.50 | Any mismatch or no kernel-level signal |
| RP-N2 | Trace-defined repeated batch, two CPU types | $2.00 | No task-total win beyond preregistered gate |
| RP-S1 | Frozen-selector cross-host confirmation | $1.00 | Development gate failed or any catastrophic held-out route |
| RP-X1 | Native SIMD only after Numba acceptance | $3.00 | No added benefit over Numba or portability failure |

Run only the next eligible row, not the entire table. Every pod must terminate
in `finally`, and the campaign must save a postflight inventory showing zero
remaining pods. Large opt-in repetitions require a new cap after the smoke
result is reviewed.

## Go/no-go summary

| Workstream | Start when | Integrate when | Stop/defer when |
|---|---|---|---|
| Trace foundation | Immediately; no new dependency | Safe, bounded, scrubbed, <2% overhead | Overhead/content risk cannot be bounded |
| Cache policy | Real access trace exists | >=5% task-total net win, bounded RSS, zero stale hits | Synthetic-only or incumbent wins |
| Incremental family | Real edit/version replay exists | Total family work wins with bounded retained state | Bookkeeping repays no work |
| Partial contexts | Natural ordered streams exist | Named output/query region wins held-out | Only restriction micro-window wins |
| Feature selector | Real `k=13..15` opportunity >=3% | Zero catastrophic held-out routes and cross-host transfer | Insufficient traffic or any gate failure |
| Numba words | Real repeated kernel-dominant batch exists | >=10% target task-total win, exact and bounded | JIT/copy/prep dominates |
| CUDD | Symbolic/context workload exists | Equivalent task-total artifact wins | Exhaustive extraction erases benefit |
| Native SIMD | Numba wins but kernel remains hot | Material added task-total win on dispatch matrix | Complexity exceeds incremental benefit |

## Recommended implementation batches

### Batch 1 — Safe local foundation

Estimated effort: 2--4 engineering days.

- implement metrics-only trace schema/null sink/bounded JSONL sink;
- instrument public benchmark and compile/evaluate boundaries;
- add validator, scrubber, manifest, replay skeleton, and unit tests;
- measure disabled/enabled overhead;
- add a synthetic smoke only to test mechanics, not policy conclusions.

This batch requires no new dependency, cloud compute, corpus download, API
default change, or production routing change.

### Batch 2 — Real trace replay

Elapsed collection time depends on the real workload; analysis effort is about
2--4 engineering days after capture.

- collect metrics traces first;
- request replayable expressions/contexts only where necessary and approved;
- run cache-policy simulation and opportunity screens for family, context,
  selector, and native lanes;
- preregister which downstream lane, if any, clears its entry gate.

### Batch 3 — Workload-backed prototypes

Estimated effort per accepted lane:

- byte-LRU/cost admission: 2--4 days;
- minimal incremental compiler: 4--8 days;
- context/CUDD frontier: 2--4 days plus approved compute;
- new selector corpus/model: 3--6 days plus source review and compute;
- Numba packed words: 3--6 days plus dependency approval;
- compiled SIMD: 5--10 days and only after Numba acceptance.

Do not schedule every lane. Batch 2 selects the lanes that have real economic
support.

## Immediate first-agent checklist

1. Preserve branch, HEAD, status, dependency versions, and source hashes; do
   not touch unrelated website or untracked files.
2. Re-read the current backlog update and external-run results.
3. Create the uniquely dated remaining-work campaign directory and preregister
   trace overhead/content gates.
4. Implement only Phase 1 metrics tracing and its tests.
5. Run quick, focused, and full correctness gates.
6. Produce a trace mechanics smoke and overhead result; make no cache or reuse
   performance claim from it.
7. Stop before replayable production capture, dependency installation, source
   download, Runpod creation, API default change, commit, or push unless the
   exact action is approved.

## Current primary-source dependency notes

- Numba 0.67.0 release notes, 2026-08-11:
  https://numba.readthedocs.io/en/stable/release/0.67.0-notes.html
- Numba installation/version support:
  https://numba.readthedocs.io/en/stable/user/installing.html
- Numba 0.67.0 CPython 3.13 wheels and release metadata:
  https://pypi.org/project/numba/0.67.0/
- llvmlite release/compatibility metadata:
  https://pypi.org/project/llvmlite/
- `dd` CUDD backend and build/wheel documentation:
  https://github.com/tulip-control/dd/blob/main/doc.md
- `dd` 0.6.0 CPython 3.13 manylinux wheel metadata:
  https://pypi.org/project/dd/
- NumPy CPU/SIMD dispatch documentation:
  https://numpy.org/doc/stable/reference/simd/index.html
- VTR official benchmark repository and licensing:
  https://github.com/verilog-to-routing/vtr-verilog-to-routing
  and
  https://github.com/verilog-to-routing/vtr-verilog-to-routing/blob/master/LICENSE.md
- Runpod pod lifecycle documentation:
  https://docs.runpod.io/pods/manage-pods

The version statements above are evidence as of 2026-08-26 and must be checked
again immediately before installing or building dependencies.
