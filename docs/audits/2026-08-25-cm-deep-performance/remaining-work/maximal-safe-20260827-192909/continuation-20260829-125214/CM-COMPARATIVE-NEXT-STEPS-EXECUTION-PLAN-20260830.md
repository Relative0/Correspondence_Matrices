# CM comparative program: next-steps execution plan

Date: 2026-08-30
Status: implementation plan; no Runpod create, upload, purchase, or publication authorized
Supersedes: the “immediate implementation order” for already-completed P0–P6 work in
`CM-FAST-VARIANTS-COMPARATIVE-BENCHMARK-PLAN-20260829.md`
Does not supersede: that document's task contracts, fairness rules, analysis rules,
or P7–P13 scientific scope

## 1. Objective

Move from the verified V4 corpus and offline P7 gate to defensible CM internal
measurements, then to task-matched comparisons with CSE-flat, native CUDD, d4,
and CaDiCaL, and finally to untouched confirmation and fresh-host replication.

The work must preserve four boundaries:

1. Development measurements may diagnose, size shards, and select a later
   configuration; they cannot serve as untouched confirmation.
2. Every timed comparison must deliver the same declared task artifact.
3. Validation, corpus selection, and failure handling cannot be chosen after a
   favorable timing result is seen.
4. Every cloud write requires a new exact authorization. This plan itself
   authorizes none.

## 2. Starting point

### Complete and authoritative

- P6 V4 freeze:
  `docs/research/verification/comparative-p6-candidate-v4-2026-08-30`.
- Logical freeze SHA-256:
  `54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd`.
- 104 independent case/cluster IDs: 32 regression, 42 development, and 30
  confirmation.
- Ten EPFL cases identify exact bounded primary-output cones; ten circuits with
  no eligible output are frozen exclusions.
- Six schedule policies and 9,672 maximum-block order rows.
- P7 offline gate:
  `docs/research/verification/comparative-p7-offline-gate-v1-2026-08-30`.
- All 58 P7-eligible inputs prepare: 24 regression and 34 development.
- Four concrete IR controls and five concrete complete-relation arms are bound.
- Two `k=8` functional cases pass all nine arms against the independent scalar
  oracle; no durations are retained.
- Native Linux functional readiness is technically established by V20 for
  CaDiCaL, CUDD dump/reload, and five d4 known-count cases. `perf` was absent.

### Not yet complete

- No isolated P7 timed-cell worker or campaign runner exists.
- No frozen full-corpus oracle file exists for the ten EPFL output cones.
- No Linux correctness/oracle scout has run against V4.
- No P7 timing proposal is frozen or authorized.
- `CM-Fast-Frozen` is not yet a distinct checked-in configuration.
- The current 30-case confirmation corpus covers CNF count/SAT/witness/frontier
  tasks, not principal IR or complete-relation claims.
- Real context/version histories and their access traces are not frozen.
- No P7, P8, or P9 performance result exists.

## 3. Program map

| Work package | Purpose | Compute class | Cloud authorization |
| --- | --- | --- | --- |
| W1 | Isolated Linux cell runner and negative controls | Trivial/local fake tests | None |
| W2 | Immutable runner/source package | Trivial/local verification | None |
| W3 | Full V4 correctness and oracle scout | Nontrivial Runpod | Separate exact authorization |
| W4 | Small P7 timing and RSS scout | Nontrivial Runpod | Separate exact authorization |
| W5 | Full P7A/P7B development ablation | Multi-shard Runpod | Exact shard/count authorization |
| W6 | Freeze/test a distinct fast configuration, if justified | Local tests then Runpod development | Separate authorization for timing |
| W7 | P7C/P7D lifecycle, order, memory, and frontier | Multi-shard Runpod | Separate authorization |
| W8 | Formula/circuit confirmation acquisition and freeze | Static/local or Runpod conversion | Upload/compute authorization as applicable |
| W9 | P8 task-matched external development comparisons | Multi-shard Runpod | Separate authorization by task family |
| W10 | P9 untouched confirmation and host replication | Multi-allocation Runpod | Exact multi-create authorization |
| W11 | Real histories/cache/edit economics | Runpod after trace freeze | Separate authorization |
| W12 | Conditional JIT/block/stream/selector work | Runpod only if triggered | Separate branch authorization |
| W13 | Independent reproduction and release evidence | Fresh task/machine | Separate operational approval |

W1, W2, W3, W8, W4, and W5 are the immediate critical path in that order. W8
must freeze the new formula/circuit confirmation cohort before W4 exposes any
comparative timing. W6, W7, and W9 through W13 are gated by evidence rather
than assumed to succeed.

### Planning compute envelope

| Stage | Initial planning range | Scaling trigger |
| --- | ---: | --- |
| W3 correctness/oracle | 0.5–2 CPU pod-hours | Oracle or functional cell cost exceeds the bounded proposal |
| W4 timing/RSS scout | 1–3 CPU pod-hours | Fewer cases if one complete cycle cannot fit safely |
| W5 full P7A/P7B development | 8–20 CPU pod-hours | Frozen noise extension and W4 cell-cost evidence |
| W7 lifecycle/order/frontier | 4–12 CPU pod-hours | Only frozen missing strata and workload-relevant ladders |
| W9 external development | 8–20 CPU pod-hours | Separate task-family pilots pass |
| W10 untouched confirmation | 10–30 CPU pod-hours | Fresh-allocation replication only if host variance warrants it |

These are capacity estimates, not quotes or authorization. Each proposal must
refresh the actual offer price and set hard pod-hour and dollar caps. Longer
programs should use multiple sequential immutable shards instead of one fragile
long-lived controller.

## 4. W1 — isolated Linux cell runner

### 4.1 Planned implementation surface

Prefer a small layer over the existing comparative modules:

- `cmbench/comparative/p7_runner.py`: cell schemas, frozen-ledger expansion,
  worker-result validation, and controller-side oracle validation.
- `scripts/cm_comparative_p7_worker.py`: one reviewed stdin request to one JSON
  result; no network, no arbitrary import/path, and no campaign decisions.
- `scripts/cm_comparative_p7_campaign.py`: shard execution, append-only ledger,
  resume, reconciliation, environment/source records, and final summary.
- `scripts/cm_comparative_p7_analyze.py`: read-only development summaries and
  frozen noise-extension decisions.
- `tests/test_cm_comparative_p7_runner.py`: schemas, measured-span accounting,
  oracle separation, malformed output, and failure retention.
- `tests/test_cm_comparative_p7_campaign.py`: plan expansion, resume,
  reconciliation, conditional extension, source mutation, and cleanup gates.

Do not add a large mode to `cm_bench.py` and do not change production defaults.

### 4.2 Cell identity

Every cell identity must include:

- V4 freeze SHA-256;
- policy ID and task;
- case and cluster IDs;
- source and member SHA-256;
- arm and concrete configuration SHA-256;
- block, case position, arm position, and frozen order-row SHA-256;
- lifecycle, output contract, affinity class, and resource-limit profile;
- worker/source manifest SHA-256.

The cell ID is the SHA-256 of canonical finite JSON over those fields. A cell
cannot be rewritten, and a resumed shard can run only cell IDs with no prior
terminal record.

### 4.3 Worker contract

The worker must:

1. accept one bounded canonical request from stdin;
2. resolve only the case and arm already present in the verified freeze;
3. refuse extra fields, unknown arms, source mismatches, path escapes, secret
   paths, and unsupported task/artifact combinations before measurement;
4. create no child process unless that arm's declared adapter requires one;
5. execute one cell and write one bounded canonical JSON result;
6. emit diagnostics only to bounded stderr;
7. never access the Runpod credential or controller state; and
8. retain no answer cache between fresh-process cells.

### 4.4 Measured spans

For P7A IR preparation, task-total starts before source parse/translation and
ends after the declared ordered IR or flat-program artifact is complete. The
semantic evaluation used to validate that artifact is outside the timed span.

For P7B complete relation, task-total starts before source parse/translation
and includes compile, lower/bind, execute, extraction, and delivery of the full
declared vector/hash. Oracle generation and comparison remain outside.

Each result separately retains worker process wall time, controller-observed
process wall time, and stage times. Process startup is reported, never silently
mixed into or removed from the library-task result.

### 4.5 Supervision and resources

Use `cmbench/comparative/linux_supervisor.py` for a fresh owned process group
per cell. Require:

- absolute executable/argument vector;
- bounded stdin, stdout, and stderr;
- per-cell deadline;
- process-count bound;
- sampled simultaneous process-tree RSS and per-process HWM where readable;
- container/cgroup memory fields recorded separately;
- forced group termination after success or failure;
- verified empty owned group and closed streams before terminal success; and
- typed retention of timeout, memory stop, output stop, malformed output,
  worker error, semantic mismatch, and cleanup failure.

A sampled RSS stop is not described as a kernel memory limit. Host logical CPU
count is not described as allocated CPU count; affinity is authoritative.

### 4.6 Oracle separation

The runner accepts only a precomputed, source-bound oracle record:

- synthetic E3 cases use the JSONL member's frozen `truth_sha256`, independently
  rechecked once from the expression;
- EPFL cases use `BlifNetlist.packed_value(root)` and the exact frozen support
  order; this path shares neither CM IR nor the CM/flat evaluator;
- every oracle row binds case ID, source/member hash, root/support, width,
  encoding, result hash, generator source hash, and oracle-package hash.

The worker returns its result digest. The controller compares it with the
oracle only after the measured worker exits. A mismatch is terminal and stops
the affected shard before further performance cells.

### 4.7 Required local/fake tests

Before any cloud proposal, test at least:

- success with injected deterministic clocks;
- worker refusal before execution;
- timeout, memory, output, process-count, and cleanup failures;
- malformed/truncated/duplicate-key/nonfinite worker JSON;
- correct result with wrong cell/case/arm/configuration identity;
- semantic mismatch after an otherwise successful worker;
- validation accidentally invoked inside the measured span;
- source changed before a shard and between cells;
- duplicate running/terminal ledger entries;
- resume after partial success and after retained failure;
- unplanned cell, duplicate cell, missing cell, and reordered arm attempts;
- noise-extension decisions that add only the next complete counterbalance
  cycle and never discard minimum-block rows;
- unrelated-process protection; and
- verifier rerun that performs no mutation.

**Gate W1:** all fake negative controls are detected, all bounded functional
cells match independent oracles, and no performance conclusion comes from unit
tests.

## 5. W2 — immutable runner package

Build a non-overwriting package containing:

- V4 freeze and P7 offline-gate identities;
- exact source manifest and dependency lock;
- worker/campaign/analyzer files and focused tests;
- cell/result/oracle/ledger schemas;
- source-before and expected source-after manifests;
- fake test/JUnit evidence;
- package checksums and a read-only verifier; and
- explicit `performance_measurement=false` for the package build.

Run it from an isolated temporary source tree to prove the manifest is
dependency-closed. Secret-like files, `.env*`, controller credentials, local
databases, and unrelated source must be absent.

**Gate W2:** isolated tests pass, all local imports close, every package byte
rehashes, the verifier is nonmutating, and the exact upload size is bounded.

## 6. W3 — Runpod Linux correctness and oracle scout

This is the first next cloud run and it is deliberately not a performance
campaign.

### 6.1 Workload

- Verify the exact W2 package and V4 source identities.
- Run focused tests under the pinned Linux runtime.
- Validate affinity/cgroup/process supervision on the actual allocation.
- Generate one independent oracle record for each of the 58 P7 cases.
- Execute each applicable P7 arm once per case outside a ranking design:
  58 cases × four IR controls and five relation arms where applicable, bounded
  by the task/case registry.
- Require exact result-oracle equality, identical one-memo/two-memo ordered IR,
  typed failures, and verified cleanup.
- Record coarse total runtime and maximum observed resources only to size the
  later proposal. Do not publish arm ratios, ranks, or per-arm comparative
  timings from this run.

### 6.2 Operational proposal

Freeze a new proposal only after W2. It must state:

- exact file count, bytes, and hashes;
- one pinned Secure CPU resource request;
- 12-GB container storage, zero pod volume, and no network volume unless a
  reviewed workload change proves otherwise;
- current offer/price preflight and hard phase/campaign caps;
- exact pod-create count, normally one, with no replacement;
- maximum lifetime and earlier cleanup deadline;
- 256-KiB resumable upload chunks with exact full-payload identity;
- authenticated role-specific bootstrap routes, bounded retry of setup-time
  404s, and no credential in evidence;
- watchdog acknowledgement before create;
- ownership-only deletion and final empty-inventory/detail checks; and
- bounded result ZIP, oracle package, logs, JUnit, and cleanup receipts.

The proposal and authorization must name each other by path and SHA-256. No
earlier consumed authorization or external `$10` record may be reused.

**Gate W3:** all planned functional cells reconcile, zero mismatches occur,
the oracle package verifies locally after retrieval, supervision/cleanup is
complete, and no performance ranking is made.

## 7. W4 — small P7 timing/RSS scout

### 7.1 Static scout selection

Create a new immutable scout manifest before timing. Select approximately 12
independent units from V4 using only frozen static strata:

- synthetic cases spanning `k=8,12,16`, operator families, tree/shared shapes,
  depth, and sharing; and
- EPFL cases spanning low/mid/high support and small/medium/larger source cones.

Selection must be deterministic from case metadata and cannot inspect W3
per-arm timings. W3 failures can exclude a case only under the already-frozen
typed execution rule, with the failure retained.

### 7.2 Scout ledger

Run one complete counterbalance cycle:

- P7 IR: 12 cases × 8 blocks × 4 arms = 384 planned cells;
- P7 relation: 12 cases × 10 blocks × 5 arms = 600 planned cells;
- total target: 984 primary cells, plus separately labeled nonprimary anchors
  and Linux control probes.

Adjust the exact case count downward before freeze if W3 cell-cost evidence
shows the authorized lifetime cannot safely include all 984 cells. Never cut a
counterbalance cycle after timing begins.

### 7.3 Scout questions

The scout answers only:

- per-task/case cell-cost and RSS distributions;
- whether deadlines and stream/evidence bounds are safe;
- measurement overhead relative to cell duration;
- whether minimum blocks are sufficient under the frozen MAD/median rule;
- between-cell drift within one allocation;
- whether any arm is systematically refused or near the memory/output guard;
  and
- safe case counts per immutable shard.

It is not the principal P7 result.

**Gate W4:** complete ledger or retained typed failures, zero semantic mismatch,
acceptable measurement overhead, safe bounds for a full shard, retrieved
evidence verification, owned deletion, and reconciled cost.

## 8. W5 — full P7A/P7B development ablation

### 8.1 Minimum campaign size

At V4 minimum blocks:

- P7 IR: 58 cases × 8 blocks × 4 arms = 1,856 cells;
- P7 relation: 58 cases × 10 blocks × 5 arms = 2,900 cells;
- total minimum: 4,756 cells.

Conditional extension to V4 maximum blocks can raise this to 9,512 cells only
through the frozen noise rule. Added independent cases have priority over added
repetitions if a new development version is needed.

### 8.2 Sharding

- Split by complete case/block units; never split an arm order within a block.
- Use W4 resource evidence to target immutable shards of roughly 30–90 minutes
  or another explicitly authorized duration.
- Run shards sequentially under one exclusive launch owner unless a separate
  throughput study authorizes concurrency.
- Include a small frozen diagnostic anchor set in every allocation. Anchor
  rows are labeled diagnostic and are not counted as independent formulas.
- A resumable campaign may execute only never-attempted cell IDs. A new pod for
  an interrupted shard requires the retry/replacement behavior stated in that
  shard's authorization.

### 8.3 Primary development comparisons

- IR: current one-memo versus historical two-memo within the ordered-IR
  artifact family; CSE-flat versus raw-flat within the flat-program control
  family. Do not rank ordered IR against a flat program as if they were the
  same delivered artifact.
- Relation: dense versus packed bigint, packed words, no-reinflation, and
  CSE-flat under the same full-output contract.
- Preserve stage accounting for parse, structural identity, canonicalization,
  IR build, lower/bind, execute, extraction/delivery, and task total.
- Report absolute task-total time and process-tree peak RSS with paired ratios;
  do not substitute kernel-only results.

### 8.4 Development analysis

- The inferential unit is the independent formula/circuit cluster.
- Use paired log ratios and cluster bootstrap intervals.
- Report medians, p10/p90 or p95 tails, per-case scatter, completion rates, and
  absolute time/RSS.
- Keep synthetic and natural results separate before any pooled summary.
- Retain timeouts/refusals in completion/frontier summaries; do not compute a
  survivor-only headline.
- Apply the predeclared extension rule from minimum to maximum blocks without
  changing cases, arms, metrics, or exclusions.

**Gate W5:** every planned cell is terminal and reconciled, no semantic or
identity mismatch exists, source hashes are unchanged, all shard cleanups and
costs reconcile, and conclusions remain explicitly developmental.

## 9. W6 — distinct `CM-Fast-Frozen` decision

Do not create a second label for an existing arm.

After W5, one of three outcomes is recorded:

1. **No combined arm:** retain the strongest applicable existing named CM arm
   and omit `CM-Fast-Frozen`.
2. **Distinct combined candidate:** implement a checked-in configuration whose
   components independently passed exactness/accounting gates and whose code
   path/configuration hash differs from every W5 arm.
3. **Inconclusive:** run a newly frozen development ablation; do not choose from
   confirmation data.

A combined candidate must have:

- an immutable configuration document listing every enabled component,
  threshold, cache/lifecycle setting, fallback, and output contract;
- exact tests for all 16 binary operators, constants, unused/dead axes,
  variable orders, sharing identities, word boundaries, reduced/restored
  output, and memory/output refusal;
- a direct ablation of the combined stack versus each contributing component;
- no learned per-case routing unless P12 is separately triggered; and
- no hidden warm cache or answer cache.

If development results choose among configurations, the chosen configuration
is frozen before any untouched formula/circuit confirmation is executed.

**Gate W6:** the arm is exact, distinct, fully charged, and either advances as
a frozen candidate or is explicitly omitted with the negative result retained.

## 10. W7 — P7C/P7D lifecycle, ordering, memory, and frontier

V4 is sufficient for the initial IR/relation ablation, but not for all P7C/P7D
claims. Create a versioned development freeze for:

- compile-every-time versus compile-once;
- resident and fresh processes;
- query counts `q=1,2,4,8,16,32,64,256,1024,4096` where feasible;
- blocked, round-robin, sliding-window, and Zipf locality;
- fixed/dead-axis reduced output and restored-full output;
- frozen variable relabellings on order-sensitive units;
- explicit-output `k` and memory/frontier strata that fill gaps beyond the
  preserved `k=17..20` evidence; and
- estimator calibration and confirmation cohorts that remain disjoint.

Real access/version histories are deferred to W11; generated traces remain
controls and cannot support natural-workload claims.

**Gate W7:** lifecycle and restoration costs are complete, cache counters are
honest, frontier failures remain in the denominator, and any estimator rule is
frozen before its confirmation cohort.

## 11. W8 — untouched formula/circuit confirmation freeze

The present CNF confirmation set cannot confirm IR or complete-relation claims.
Complete this package after the non-performance W3 correctness scout but before
the comparative W4 timing scout. No development arm timing may be inspected
before the selection rule, source list, output roots, or exclusions are frozen.

Before principal P9 claims:

1. acquire at least 30 independently licensed formula/circuit units if a
   suitable corpus exists;
2. record repository URL, commit, license identity, source path/hash, and any
   conversion toolchain identity;
3. if using HDL, freeze a deterministic HDL-to-BLIF/AIG preparation contract
   and verify semantic equivalence on fixtures;
4. select one primary-output cone per independent circuit through a static,
   bounded, bytewise rule;
5. reject unsupported sequential logic, ambiguous licenses, semantic comments,
   duplicates, malformed sources, and over-bound cones before timing;
6. freeze roots, support/order, structural strata, oracle hashes, schedules,
   exclusions, and primary metrics; and
7. prohibit all comparative timing inspection until the final candidate and
   analysis plan are frozen.

The existing Yosys benchmark checkout is a possible licensed source only after
the conversion contract is implemented and audited. The VTR checkout remains
excluded unless per-benchmark redistribution terms are established.

**Gate W8:** at least 30 independent eligible clusters, complete source/license/
conversion/oracle identities, task-specific confirmation coverage, and no
timing inspection.

## 12. W9 — P8 task-matched external development comparisons

Run separate task families rather than one mixed ranking.

### Complete relation

- Frozen primary CM candidate or named CM arms;
- CSE-flat/BitSet;
- native CUDD only when full extraction in the declared variable order is
  charged;
- fixed and declared CUDD ordering/reordering modes, with actual final order
  retained.

### Exact count

- CM/CSE exact popcount path;
- native CUDD count where the represented set semantics match;
- hash-pinned native d4 with CNF translation and process startup charged.

### SAT and witness

- bounded CM/CSE diagnostics;
- native CaDiCaL status, assumptions, witness validation, and miter modes;
- no complete-vector requirement imposed on SAT-only tools.

### Contexts, histories, and reload

- fresh and resident CM/CSE;
- CaDiCaL assumptions;
- CUDD restrict/query;
- exact CM structural export/reload and CUDD graph dump/reload;
- d4 reload only if a verified compiled-artifact contract exists.

Each task family gets its own manifest, primary comparison, artifact contract,
deadline/memory bounds, and authorization. V20 capability evidence is rechecked
under the new package; no pure-Python proxy may replace unavailable native code.

**Gate W9:** zero mismatches, complete task-specific ledgers, no backend
substitution, startup/extraction/restoration correctly charged, and owned
cleanup/cost reconciliation for every shard.

## 13. W10 — P9 untouched confirmation and fresh-host replication

Only the frozen W6 candidate and W9 task configurations advance.

- Execute the W8 formula/circuit confirmation without tuning or dropping
  unfavorable cells.
- Execute the existing CNF confirmation for the count/SAT task families.
- Preserve all failures, resource refusals, and host metadata.
- If W4/W5/W9 show material between-allocation variance, run the primary subset
  on at least five fresh allocations. Each allocation identity remains a
  stratum; do not pool host effects away.
- Freeze a portability matrix only after the primary Python/NumPy/native image
  result; do not count runtime variants as independent formulas.
- Do not add a throughput study unless a real concurrent workload requires it.

**Gate W10:** untouched ledgers reconcile, no confirmation-driven tuning
occurred, the cluster/host-aware primary analysis completes, and the outcome is
reported as supported, negative, or inconclusive under the predeclared rule.

## 14. W11–W12 — later workload and optimization branches

### Real histories, cache, context, and edits

Freeze observed access/revision traces before optimization. Compare no cache,
entry LRU, byte LRU, and size/cost-aware admission by total workload cost,
retained memory, invalidation, and phase behavior. For incremental compilation,
use true edits and compare cold CM, current structural reuse, any new prototype,
and CSE-flat. Cache hit rate alone is not a success criterion.

### Conditional branches

Run only when prior profiling/workload evidence triggers them:

- native/JIT word fusion through a program × executor factorial design;
- exact independent-support block decomposition;
- bounded streamed/tiled relation output;
- larger output/frontier cells; and
- a prespecified backend selector trained only on development data and tested
  on a new circuit-held-out corpus.

Every branch has a new plan, source freeze, correctness gate, Runpod proposal,
and untouched evaluation cohort. Unused compute is not a reason to trigger one.

## 15. Analysis and decision rules

### Primary metrics

- task-total wall time;
- process-tree peak RSS.

### Secondary mechanism metrics

Stage time, controller/process wall time, output bytes, page faults, operation
and instruction counts, transposes/permutations, cache hits/misses/evictions,
live buffers/support, cgroup observations, and crossover query count.

### Statistical rules

- independent formula/circuit/history cluster is the unit;
- timed blocks are repeated observations, not new samples;
- paired log time/RSS ratios and cluster bootstrap intervals;
- absolute distributions and per-case scatter alongside ratios;
- host-stratified summaries for multi-allocation work;
- completion and censored-frontier analysis for failures;
- declared multiplicity control for secondary hypothesis families; and
- no ratio between arms that delivered different artifacts.

A provisional “faster” statement requires zero semantic errors, at least a 5%
median paired task-total improvement, a cluster-aware 95% ratio interval below
1.0, and no unexplained material regression in RSS, failures, or artifact
completeness. Otherwise report “inconclusive at this scale.”

Production adoption additionally requires regression plus untouched
confirmation exactness, explicit fallback/refusal behavior, bounded memory
under the production guard, and workload-relevant total benefit. Benchmark
evidence does not silently change a public default.

## 16. Runpod operating protocol for every authorized stage

1. One named launch owner; other tasks review but do not create.
2. Fresh immutable local run identity and output directory.
3. Read-only preflight: authorization hash, proposal hash, source/package hash,
   current inventories, account/offer, current quote, aggregate attributable
   cost, host AC/awake state, and no active conflicting guard.
4. Atomic state publication and exact watchdog acknowledgement before POST.
5. Exact resource validation: Secure CPU class, affinity, memory, image,
   container disk, integer zero pod/network volume where specified, ports, and
   actual versus quoted price.
6. Token-gated, role-specific HTTP routes; resumable bounded chunks; full
   payload hash before worker start.
7. At-most-once workload token and bounded polling/log/evidence transfer.
8. Campaign and per-cell deadlines, evidence/output bounds, and early abort on
   mismatch, source mutation, cleanup failure, or budget violation.
9. Ownership-only DELETE in controller and watchdog paths.
10. Final v1/v2 inventories empty, owned pod details absent, guards/watchdogs
    exited, evidence hashes verified, and delayed billing conservatively
    reconciled.

Each authorization states exact create count, replacement/retry behavior,
maximum lifetime/pod-hours, phase and aggregate dollar caps, and whether resume
may execute never-attempted cells. Authorization for one shard does not imply
authorization for the next.

## 17. Evidence layout

Each executed package should contain:

```text
proposal-and-authorization/
source-manifest.json
dependency-lock.json
native-identities.json
freeze-and-shard.json
environment.json
source-before.json
oracle/
ledger.jsonl
raw-results/
failures.jsonl
cleanup/
source-after.json
summary.json
analysis.json
checksums.json
verification.json
```

Results remain append-only until final atomic publication. Summary files are
recomputable from the raw ledger and cannot be the sole evidence.

## 18. Stop and refreeze conditions

Stop the affected stage without filling cells when any occurs:

- semantic or ordered-artifact mismatch;
- source, dependency, native binary, image, or configuration hash mismatch;
- unplanned/duplicate cell or changed order ledger;
- worker/controller result schema ambiguity;
- unmeasured or uncleaned owned process tree;
- provider resource mismatch;
- current or projected authorized cost/lifetime breach;
- missing/partial evidence beyond the bounded recovery rule; or
- loss of exclusive launch ownership.

A code or contract fix creates a new versioned package and proposal. Preserve
the failed package/output. Confirmation bugs invalidate the affected frozen
claim; they do not become development data for the same confirmation version.

## 19. Immediate work queue

1. Implement W1 schemas, worker, controller, and measured-span separation.
2. Add the W1 fake negative-control and resume/reconciliation tests.
3. Build and independently verify W2 from an isolated source tree.
4. Freeze a deterministic W3 source/oracle workload and exact Runpod proposal.
5. Obtain explicit W3 authorization; run once; retrieve, clean up, and audit.
6. Complete W8's static source/license/conversion/output-root freeze before any
   comparative timing is exposed.
7. Use W3 only to freeze W4 case count, deadlines, RSS/evidence bounds, and
   current hard cost caps.
8. Freeze and seek authorization for W4; run the one-cycle timing/RSS scout.
9. Use W4 to freeze W5 shard sizes without changing V4 cases/arms/metrics.
10. Run W5 sequentially under exact shard authorizations.
11. Decide W6 without inventing a duplicate combined arm.
12. Proceed to task-separated W7/W9 development and W10 confirmation only
    after their gates.

## 20. Definition of program completion

The comparative program is complete when:

- all executed shards and retained failures reconcile to immutable ledgers;
- CM internal ablations cover IR, representation/no-reinflation, lifecycle,
  ordering, memory, and relevant frontiers;
- CUDD, d4, and CaDiCaL comparisons are task-matched and native-identified;
- principal CM claims survive or fail an untouched task-specific confirmation
  under a predeclared cluster/host analysis;
- real-history/cache/edit claims use frozen natural traces;
- conditional branches are either gated in with evidence or explicitly closed;
- cleanup, source identities, billing, and claim limitations are independently
  verified; and
- a clean external reproduction bundle reproduces the principal summaries on
  another task or machine.

Negative and inconclusive outcomes satisfy completion when the frozen study is
correct, complete, and honestly reported.
