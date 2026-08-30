# CM fast-variant and comparative benchmark plan

Date: 2026-08-29  
Revision: 2, completeness-audited against the current backlog and E1–E10 gap analysis  
Status: implementation and measurement plan only  
Cloud authorization: none. The preceding corpus/oracle/RSS pod was deleted
and its single-create authorization is consumed.

Audit receipt:
`CM-FAST-VARIANTS-COMPARATIVE-BENCHMARK-PLAN-AUDIT-20260829.md`.

## 1. What the latest study did and did not test

The latest 35-case, 630-call Runpod study tested three representations of the
same compiled CM computation:

- `dense`: full dense CM materialization through `materialize_cm`;
- `bigint`: packed integer evaluation through `eval_cm_node_flat`;
- `words`: packed word-array evaluation through `eval_cm_node_words`.

That study established exact agreement with an independent scalar oracle and
measured temporary-allocation and whole-child memory behavior. It was not a
performance ranking. In particular, it did not exercise every higher-level CM
optimization or compare a complete optimized CM pipeline with other
algorithms.

The current code uses the more specific terms **full reinflation** and
**no-reinflation**. `materialize_hybrid_no_reinflate` can return a packed
bitset or reduced one-dimensional truth table without reconstructing the full
dense two-dimensional CM. The code also contains compile/reuse, persistent
caches, fixed-support projection, canonicalization, subtree reuse, flat
evaluation, word evaluation, and related fast paths.

It does make sense to test the faster CM variants. The comparison needs both
individual ablations and a frozen combined pipeline. Otherwise a result could
show that “fast CM” changed without revealing which optimization helped, which
cost was omitted, or whether a cache benefited from prior observations.

## 2. Research objective

Build an auditable benchmark system that answers four separate questions:

1. Which CM implementation choices reduce total time or memory for a fixed
   output contract?
2. When do compilation, no-reinflation, fixed-support evaluation, and reuse
   amortize their setup costs?
3. On which matched tasks is a prespecified fast CM pipeline competitive with
   the strongest available non-CM implementation?
4. Where is CM slower, larger, or unable to provide the requested artifact?

The target is a task-by-task performance map, not a universal-winner claim.

## 3. Evidence already available

The new program should reuse rather than repeat the following work:

- Dense, bigint, and word results agree with a separate scalar DAG evaluator
  on 35 BX1/B2/EPFL cases and 630 Runpod calls.
- The structural study covered five generated families, `k=6,8,12,16`, and
  360 calls. Both studies found no candidate temporary-memory underestimate.
- No-reinflation, cached execution, persistent-cache, partial-context, CSE,
  ROBDD, and BitSet benchmark paths already exist in `cm_bench.py` and the core
  modules.
- CSE-flat is the strongest generic incumbent found so far. In the accepted
  symmetric V3 kernel study, bare CM/CSE-flat was about `0.891`, while the
  end-to-end wrapper ratio was about `3.094`. Runpod replicated the bare ratio
  at roughly `0.903` to `0.913`. This is workload-specific evidence, not a
  general CM advantage.
- Historical no-reinflation slices improved CM by about `1.1x` to `2.7x`, but
  remained roughly `1.7x` to `15x` slower than a pure bitset implementation in
  those slices.
- Existing related-family and partial-context experiments show real CM cache
  benefits over uncached CM, while BitSet and ROBDD still won several small
  absolute-time comparisons.
- Matched session/version contract code has checked CM, CSE, direct CNF, and
  native CaDiCaL semantics, lifecycle counters, fresh/reused engines, and
  artifact replay. Its fixed-order diagnostic clocks are explicitly not a
  ranking.
- Native CaDiCaL has executed correctly through PySAT. Current local
  `dd.autoref` is available, but compiled `dd.cudd` is absent and must not be
  silently replaced by autoref.
- A candidate d4 Linux ELF binary exists at
  `external/d4v2/scripts/d4ScriptsCompetition/bin/d4`, is 5,054,920 bytes, and
  has SHA-256
  `29cb30f351ed92b02343e5e7a98b082e949d9838245f37c0bcdecf68a57ffd39`.
  Its presence is not execution evidence; build provenance, dependencies,
  version behavior, and tiny known-count cases still need verification.

The 35-case corpus and the previously called “heldout” half have now been
observed. They remain useful regression data, but cannot serve as a clean new
holdout for fitting a selector or choosing favorable variants.

## 4. Completeness audit against the remaining research program

This revision cross-checks the plan against the current optimization backlog,
the earlier E1–E10 benchmark gap analysis, the accepted symmetric/CSE studies,
and the new structural and corpus memory evidence. “Included” means the plan
contains an executable phase and gate. “Conditional” means the work is useful
only after its stated workload or profiling precondition. “Retired” means the
existing evidence gives a specific reason not to spend compute on it.

| Area | Audit disposition | Where it is covered |
| --- | --- | --- |
| IR compile cost versus DAG size and unfolded-tree size | Included; do not repeat already accepted cells blindly | IR stage counters, high-sharing families, current one-memo confirmation, Phases 3, 7, and 9 |
| Structural sharing versus ordinary CSE | Included with the strongest `CSE-Flat` incumbent | CM arm matrix, structural ladder, clustered formula analysis |
| Full materialization versus no-reinflation | Included as a primary ablation with both reduced-output and restored-output contracts | CM arms, output parity rules, Phase 7 |
| Compile/evaluate amortization | Included across a query-count ladder and unknown-version arrival | Task matrix, Phases 6, 7, and 10 |
| Cache/schedule sensitivity | Included for blocked, round-robin, sliding-window, and Zipf/locality schedules | Phases 6, 7, and 10 |
| Formula-cluster replication and operator balance | Included; formula/circuit/history is the statistical unit | Corpus freeze and analysis rules |
| Variable ordering and residual CM transposes/permutations | Included alongside fixed-order and reordered native CUDD | Phase 7 ordering subcampaign and Phase 8 |
| Feasibility and above-guard behavior | Included as refusal/frontier evidence, separate from artifact-parity speed claims | Phase 7 frontier and task-matched external study |
| CUDD timing repair, extraction, and reordering accounting | Included; native execution remains a prerequisite | Phases 4 and 8 |
| Current one-memo preparation change | Included as cross-machine confirmation, not a new selector result | CM arms and Phase 7 |
| Compact canonical rank/key prototype | Included with byte, compile, structural-signature, and foreign-adoption gates | Contingent CM prototypes and Phase 7 |
| Temporary-memory estimator and real RSS | Included as a separate policy/compatibility study; no automatic default change | Phases 3, 7, and 9 |
| Byte/cost-aware artifact cache | Included only with real or captured access traces | Phase 10 |
| Incremental compilation across edits | Included only with true edit histories and unknown-version arrivals | Phase 10 |
| Independent-block decomposition | Conditional on a proved disjoint-support workload | Phase 11 |
| Native/JIT word fusion | Conditional on profiling that shows packed-word execution dominates total cost | Phase 11 |
| Streamed/tiling output | Conditional on a caller contract that accepts chunks | Phase 11 |
| Backend selector | Conditional on meaningful workload volume and a new untouched corpus | Phase 12 |
| Native CaDiCaL, CUDD/ZDD, and d4 | Included with native identity and task-matching gates | Phases 4 and 8 |
| Platform and fresh-allocation variability | Included with multiple fresh Runpod allocations and host-stratified analysis | Phase 9 |
| CI and independent reproduction | Included after the implementation and evidence freeze | Phase 13 |

The audit also preserves existing negative results. It does not propose:

- Espresso as a complete-vector competitor; it produces a minimized cover and
  changes the task.
- SymPy as a timed competitor; it remains an independent correctness oracle.
- extra ambient-variable replicas in place of distinct formulas.
- more repetitions of the already observed corpus as a substitute for more
  independent formulas/circuits.
- a universal support threshold chosen from existing timing data.
- a GPU, multiprocessing, or distributed default before a streamed,
  kernel-dominant workload demonstrates that startup, copying, and aggregate
  memory can amortize.
- a sparse numerical-matrix arm without proved exact block sparsity.
- a semantic XOR interpretation of the directional CM quotient.

These exclusions are part of the comprehensive plan: compute is reserved for
questions capable of changing a scientific or engineering conclusion.

## 5. Non-negotiable comparison rules

### 5.1 Match the requested artifact

Methods are comparable only when they answer the same question and return the
same required artifact. Examples:

- A packed complete truth vector may be compared directly with another packed
  complete truth vector.
- A BDD build time alone cannot be compared with a complete-vector result. If
  the task requires the vector, BDD extraction time and output bytes count.
- A model counter may be compared with a CM popcount for an exact count task.
  It is not required to enumerate and return a vector when the task asks only
  for a count.
- A SAT solver is the primary competitor for satisfiability or witness tasks.
  Exhaustively building a CM vector may remain a bounded diagnostic arm, but
  should not be presented as the natural large-instance SAT strategy.

### 5.2 Charge the whole lifecycle

Every row must identify and, where applicable, time:

1. process and interpreter startup;
2. input parsing and normalization;
3. translation to the backend's accepted form;
4. construction or compilation;
5. first query;
6. repeated queries or restrictions;
7. extraction/materialization of the requested artifact;
8. serialization and reload;
9. cleanup.

Kernel-only and end-to-end results may both be reported, but never merged or
substituted for one another.

### 5.3 Freeze choices before timing

Variable order, CSE mode, representation, cache policy, native options,
timeouts, query order, and any automatic route must be fixed in the plan.
Choosing the fastest method per case after seeing the measurements creates a
descriptive “virtual best,” not a deployable algorithm.

### 5.4 Treat failures as results

Timeouts, memory refusals, unsupported artifacts, invalid native identities,
parser failures, output-limit failures, semantic mismatches, and cleanup
failures stay in the denominator. A failed arm is not dropped from the paired
cohort.

## 6. CM arm matrix

The first timed study should include these named arms where their output
contract applies:

| Arm | Purpose | Setup charged | Output charged |
| --- | --- | --- | --- |
| `CM-IR-Current` | Current sharing-aware canonical IR and one-memo preparation | Parse + structural UID/digest + canonicalize/intern + lower | Declared downstream artifact |
| `CM-IR-TwoMemo-Control` | Historical preparation control for cross-machine confirmation | Same staged preparation | Same artifact as current IR |
| `CM-Dense` | Plain full materialization baseline | Parse + CM compile | Full dense CM |
| `CM-Flat-Bigint` | Packed integer evaluator | Parse + flat compile | Packed vector/hash |
| `CM-Flat-Words` | Packed word evaluator | Parse + word program | Word vector/hash |
| `CM-Hybrid-NoReinflate` | Avoid full dense reconstruction | IR compile | Packed or declared reduced output |
| `CM-Compiled-Reuse` | Compile once, evaluate/query repeatedly | First compile separated and included | Requested per-query result |
| `CM-Persistent-Family` | Reuse across a prespecified related family/version history | Cache creation, lookup, misses, eviction | Requested per-version/query result |
| `CM-Fixed-Support` | Project fixed or dead axes | Projection and support discovery | Explicitly declared reduced or restored result |
| `CM-Fast-Frozen` | Combined production candidate | Every enabled stage | Task-required artifact |

Add two internal controls:

- `CSE-Flat`, using the current structural-CSE flat evaluator, is the strongest
  current same-language generic baseline.
- A raw non-CSE flat/BitSet path is an ablation that shows the value of shared
  structure and avoids comparing only heavily optimized arms.

The IR preparation ledger must separately record expression-DAG nodes,
unfolded occurrences where bounded, structural UID/digest time,
canonicalization/interning time, CM IR nodes, lowering time, flat instructions,
primitive operations, transpose/permutation events, memo hits/misses, and peak
temporary/retained bytes. This distinguishes a faster IR from a faster packed
executor.

The following arms are contingent prototypes rather than required members of
the first comparison:

- `CM-IR-Compact-Key`, evaluated only after it preserves exact ordered IR,
  public keys, structural signatures, persistent cache identities, and foreign
  adoption behavior.
- `CM-Incremental-Edit`, evaluated only on real edit histories and always
  against both cold-current CM and sharing-aware CSE-flat.
- `CM-Independent-Blocks`, evaluated only when disjoint support is proved and
  the exact final layout is declared.
- `CM-Native-Words`, evaluated only when profiling shows the packed word kernel
  dominates task-total cost; it uses fixed-width word arrays, never arbitrary
  Python bigints reinterpreted as fixed-width native integers.
- `CM-Streamed-Tiles`, evaluated only for a consumer contract that accepts
  ordered chunks and separately reports latency to first chunk, total latency,
  output bytes, and peak memory.

`CM-Fast-Frozen` must be a checked-in configuration assembled from components
that independently passed correctness and ablation tests. It must not select
among variants from the timing result being scored. A later learned selector
requires separate training data and a new untouched evaluation corpus.

## 7. Task-matched external comparisons

| Task | Required result | CM arms | Primary non-CM arms |
| --- | --- | --- | --- |
| IR preparation/lowering mechanism | Exact ordered IR and/or identical packed program | Current IR, two-memo control, compact-key prototype | CSE-flat and raw-flat preparation controls; not an end-user speed claim |
| Complete relation | Exact vector in declared variable order | Dense, packed, no-reinflate, fast-frozen | CSE-flat/BitSet; native CUDD only with full extraction charged |
| Exact model count | Integer count | Packed popcount, no-reinflate count path | d4; native CUDD count |
| SAT/UNSAT | Status | Bounded CM/CSE checks | CaDiCaL primary |
| Witness | Status plus validated assignment | Bounded CM/CSE witness extraction | CaDiCaL primary; CUDD path if implemented |
| Equivalence/delta | Boolean equivalence and/or exact delta count | CM/CSE XOR vector/count | SAT miter; CUDD XOR/count |
| Repeated partial contexts | Answer/count/restricted artifact for a fixed context sequence | Compiled, persistent, fixed-support | CaDiCaL assumptions; CUDD restrict/query |
| Version history | Answers over frozen edit sequence | Fresh and resident CM family pools | Fresh/resident SAT; fresh/resident CUDD where meaningful |
| Persistence/reload | Same declared artifact after reload | CM structural export/reload | CUDD graph export/reload; d4 only if an appropriate compiled artifact contract is available |
| Streamed complete relation | Ordered exact chunks plus final digest | Tiled/streamed CM only after contract gate | Tiled packed baseline; parallel/native arms only after amortization proof |
| Feasibility frontier | Success, typed refusal, timeout, or memory outcome | All applicable CM arms | CSE/BitSet, CUDD/ZDD, d4, CaDiCaL; speed ratios only within task-matched subsets |

For complete vectors, the unavoidable explicit-output work grows with
`2^k`; symbolic backends should not receive credit for omitting extraction.
For count, SAT, or witness tasks, forcing every backend to create a vector
would instead bias the comparison against the algorithms designed to answer
the smaller query directly.

## 8. Implementation program

### Phase 0 — semantic and artifact contract

1. For every benchmark task, define variable ordering, unused-variable
   treatment, constants, output schema, count convention, and whether reduced
   support is permitted.
2. Decide whether a reduced result must be reinflated before delivery. If the
   consumer needs the full artifact, reinflation time and memory are charged.
3. Record which comparisons are kernel, library API, and end-to-end process
   measurements.
4. Define exact parity among dense, packed bigint, packed words,
   no-reinflation, reduced-support, restored-output, count, and streamed
   artifacts before timing any of them.

**Gate P0:** no timed arm may use an ambiguous algorithm or output name.

### Phase 1 — freeze provenance and environments

1. Record the Git commit plus the exact dirty-file manifest without modifying
   unrelated work.
2. Freeze source hashes for CM, CSE, contract, adapter, supervisor, analysis,
   and bootstrap code.
3. Freeze Python, package, wheel, OS, CPU-affinity, container-image, and native
   binary identities.
4. Preserve existing Runpod evidence and prior controller versions unchanged.
5. Create a fresh benchmark corpus manifest and immutable case IDs.
6. Mark current BX1/B2/EPFL records as observed regression cases.

**Gate P1:** every executable and input has a verifiable identity; secrets are
excluded from source manifests and evidence.

### Phase 2 — modular benchmark harness

Extend the current small contract tools instead of adding another large mode
to `cm_bench.py`:

- reuse `scripts/cm_measurement_verify.py` for frozen-source isolated cells;
- reuse `scripts/cm_session_contracts.py` for fresh/reused sessions and
  version histories;
- reuse `scripts/cm_native_contracts.py` for binary identity and adapter
  contracts;
- reuse `scripts/cm_process_supervisor.py`, adding a Linux implementation;
- add a thin comparative schedule/controller and analysis layer;
- keep each backend behind the same typed task/result interface.

Required record fields include case, corpus cluster, task, backend, arm,
configuration hash, lifecycle, block/order position, repetition, input and
output hashes, timings by stage, output bytes, process-tree peak RSS, status,
reason, native identity, worker identity, and cleanup status.

Also retain CPU affinity, cgroup CPU/memory controls, CPU model, microcode when
available, kernel, Python build, GC mode, NumPy configuration, native CPU
features, scheduler, wall-clock start, load observations, page faults,
`tracemalloc` call-window peak, whole-worker RSS/HWM, cgroup peak/current
memory when available, and controller overhead. CPU time and Linux `perf`
counters may be recorded as mechanism diagnostics when provider permissions
allow them; they are never a condition for accepting a primary wall-time row.

Use separate modes for latency and throughput. Primary single-operation
latency runs use one benchmark worker pinned to the declared affinity and do
not overlap arms. A later throughput run may use `1, 2, 4, ...` independent
workers up to the allocation, but reports aggregate throughput, per-worker
RSS, tail latency, and interference separately. It cannot replace the serial
latency result.

The harness must use append-safe or atomic evidence publication, bounded
stdin/stdout/stderr, at-most-once cell identities, exact planned-versus-
observed reconciliation, and source rehashing before and after execution.

**Gate P2:** synthetic/fake adapters can reproduce success, refusal, timeout,
malformed output, semantic mismatch, and cleanup failure without turning any
of them into a success.

### Phase 3 — correctness and accounting tests

Add focused tests to natural existing files. Cover at least:

- all 16 binary Boolean operators;
- `k=0`, constants, contradiction, tautology, unused and dead variables;
- variable-order permutations and the 63/64/65-bit word boundary;
- sharing-aware DAGs with repeated object identities, structurally equal
  distinct nodes, deep sharing, foreign-node adoption, and bounded unfolded
  occurrence controls;
- exact ordered IR, structural signature, persistent digest, flat program,
  primitive-op counts, and public-key compatibility for every IR prototype;
- dense, bigint, words, no-reinflate, reduced-support, and restored full
  outputs against a scalar oracle;
- cold/warm calls, compile hits/misses, cache eviction, unknown-version
  arrival, and fresh/reused engine counts;
- context clearing, contradictory assumptions, witnesses, non-minimal cores,
  exact count, equivalence, and version delta;
- d4 and CUDD parser fixtures including duplicate, fractional, missing,
  out-of-universe, and truncated results;
- clock injection and lifecycle totals so tests never assert wall-clock speed;
- process descendants, timeouts, memory/output caps, partial files, controller
  interruption, cleanup, and unrelated-process protection;
- analysis rejection of missing/duplicate cells, hashes, order fields,
  unsupported substitutions, and accidental cherry-picking.
- measurement-overhead controls for clocks, RSS sampling, tracing, hashing,
  validation, and optional `perf` collection, with validation outside the
  timed span unless validation is part of the declared consumer task.
- deterministic shard/resume tests proving that a resumed campaign runs only
  previously unattempted cell identities and never overwrites prior evidence.

**Gate P3:** zero semantic mismatches; all negative controls must be detected;
no benchmark timing claim comes from unit tests.

### Phase 4 — native and Linux readiness

1. Implement process-tree ownership, deadline enforcement, bounded streams,
   cleanup verification, and external peak-RSS/HWM observation on Linux.
2. Validate that affinity and cgroup metadata describe the allocation; never
   report the host logical-CPU count as allocated CPUs.
3. Recheck CaDiCaL on the bounded known-answer suite and preserve wrapper plus
   compiled-extension identities.
4. Build or install a reviewed native CUDD binding in the frozen Linux image.
   Verify fixed ordering, disabled/enabled reordering as declared, restrict,
   count, vector extraction, graph export, reload, and root-manager identity.
5. Verify the hash-pinned d4 ELF on Linux: architecture, dynamic dependencies,
   version/help behavior, exit codes, timeouts, and tiny CNFs with known counts
   including zero variables, UNSAT, unused declared variables, and all models.
6. Keep `dd.autoref` as a diagnostic implementation, never as an unannounced
   substitute for native CUDD.
7. Verify native ZDD only for an exact set-family/count task where its artifact
   is meaningful; never add it merely to increase the number of competitors.
8. Calibrate RSS sampling and cgroup/process counters with paired allocation
   controls. Retain discrepancies instead of selecting whichever counter
   makes an arm look smaller.
9. If `perf` is permitted, run a tiny counter-stability probe before collecting
   cycles, instructions, branches, and cache-miss diagnostics. Refusal remains
   a valid outcome.

**Gate P4:** every native arm either has actual successful native execution
with frozen identity or is labeled unavailable and omitted without a proxy.

### Phase 5 — trivial local smoke

Run only bounded local correctness cells, normally `k <= 8`, with one or two
cases per task and no performance conclusions. Validate schemas, extraction,
oracles, lifecycle counters, schedules, evidence checksums, and cleanup.

This phase is local because it is trivial computation. Any substantive timing
pilot or corpus sweep belongs on Runpod per the user's instruction.

**Gate P5:** the full planned ledger is produced, every smoke cell reconciles,
and rerunning the verifier does not mutate frozen evidence.

### Phase 6 — corpus and schedule freeze

Use three disjoint roles:

1. **Regression corpus:** current synthetic, BX1, B2, EPFL, and previously
   observed feature-model cases. Used to catch correctness regressions.
2. **Development/scout corpus:** cases used to tune timeouts, repetitions, and
   implementation defects. Never used as untouched confirmation.
3. **Confirmation corpus:** newly acquired and frozen before comparative
   results are inspected. No selector fitting or arm choice may use it.

Stratify independent formula/circuit/history units by live `k`, syntactic and
live support, DAG nodes, shared-subexpression ratio, depth, operator mix,
truth density, fixed axes, number of contexts, version edit size, and queries
per build. Include natural and adversarial cases, but report them separately.

The synthetic matrix should include chains, balanced trees, low- and
high-sharing random DAGs, adders, multipliers, comparators, multiplexers,
parity, popcount/carry structures, independent-support blocks, dead/fixed-axis
cases, and operator-balanced AND/OR/XOR/IMP/EQV/mixed families. Real data
should include distinct outputs from the existing EPFL checkout, independently
sourced circuits with recorded licenses and hashes, feature-model or policy
revision histories, and unweighted CNF/model-count instances appropriate for
the native adapters. Multiple outputs or revisions from one source remain one
cluster where dependence is plausible.

Use task-specific size ladders rather than one global `k` grid:

- complete explicit output: dense and packed ladders from `k=0` through the
  tested production guard, then adaptive `k=17..22` frontier cells only where
  output, time, and memory limits allow;
- ordering: at least 20 base functions across size levels with up to 100
  frozen relabellings per function, treating relabellings as repeated measures;
- context/reuse: query counts
  `q=1,2,4,8,16,32,64,256,1024,4096`, fixed-support fractions, overlap, and
  blocked/sliding-window/Zipf/round-robin locality regimes;
- version histories: short and long sequences with controlled edit sizes,
  phase changes, reversion, cache pressure, and previously unseen versions;
- count/SAT/BDD feasibility: extend by structural nodes/clauses and variables
  beyond the explicit-output range until each backend reaches a prespecified
  timeout, memory refusal, or corpus limit. These rows describe the frontier;
  they do not create speed ratios against a CM arm that returned no artifact.

Recommended scout minima, subject to availability:

- 24 to 48 independent formula/circuit units across at least four structural
  strata for complete-vector ablations;
- at least 12 independent context/version histories spanning
  `q = 1, 2, 4, 8, 16, 32, 64, 256` where feasible;
- at least 12 independent count/equivalence units that extend beyond the
  complete-vector-friendly range;
- at least seven balanced timed blocks per retained case/arm, increasing only
  from a prespecified noise rule and never counting repetitions as new cases.

For any principal confirmatory claim, target at least 30 independent cluster
units if a suitable corpus exists. If not, report the study as a pilot.

If the scout passes and Brian authorizes extended Runpod computation, target:

- 200–500 independent complete-vector formula/circuit units spanning support,
  sharing, operator, depth, and output-density strata;
- at least 50 independent context histories and 50 independent version/edit
  histories, with query counts sampled across the full ladder;
- at least 100 independent count/equivalence/CNF units, including cases beyond
  complete-vector feasibility;
- 7–15 balanced timed blocks per case/arm, increased only by a frozen noise
  rule and capped so additional compute is spent on independent units first;
- five or more fresh Runpod allocations for the final primary subset when
  between-allocation variability is material.

These are targets, not permission to download data or allocate pods. A power
and variance analysis after the scout may increase or reduce them before the
confirmation manifest is frozen.

Use a balanced Latin-square or deterministic counterbalanced arm order within
each case/block. Random seeds and the realized order ledger are frozen before
timing. Thermal/setup probes are recorded and excluded only by the predeclared
rule.

**Gate P6:** corpus roles, exclusions, repetitions, order, and primary metrics
are frozen before paid measurements.

### Phase 7 — CM internal ablation and scaling campaign on Runpod

Run the CM campaign in independently verifiable shards. Each shard repeats a
small anchor set so drift can be detected, but case-level measurements are
never averaged across changed source/configuration hashes.

#### P7A — IR preparation and structural ladder

Measure current sharing-aware IR, the explicit historical two-memo control,
CSE-flat, raw flat, and the compact-key prototype if it passed P3. Cross:

- DAG nodes and bounded unfolded occurrences;
- sharing factor and repeated-object versus structurally-equal sharing;
- depth and balanced versus left/right-associated shape;
- AND/OR/XOR/IMP/EQV/mixed operator classes;
- current and permuted variable order;
- parse, structural UID/digest, canonicalize/intern, build, lower, and bind
  stages.

This completes the still-useful portions of the old E1/E2 work without
discarding the accepted high-sharing and CSE-flat results. The one-memo arm is
a second-machine confirmation, not a new untouched optimization choice.

#### P7B — representation and output ladder

Measure:

- dense versus packed bigint versus packed words;
- full materialization versus hybrid no-reinflation;
- reduced-support output versus restored full output;
- full support versus fixed/dead-axis projection;
- scalar popcount/count-only versus complete output where both contracts are
  intentionally requested;
- each individual speedup versus the prespecified `CM-Fast-Frozen` stack.

No-reinflation receives two result columns when relevant: the time/memory to
produce its native packed/reduced artifact and the total including restoration
to the consumer's full artifact. The first cannot stand in for the second.

#### P7C — lifecycle, amortization, and schedule

Cross compile-every-time, compile-once, persistent/family reuse, fresh process,
resident process, previously known version, and previously unseen version over
the full `q` ladder. Run blocked, round-robin, sliding-window, and Zipf/locality
schedules with cache counters and cache budgets recorded. Measure cold-start,
first-use, steady-state, eviction, phase-change, serialize, reload, and cleanup.

Report a per-case amortization curve and crossover interval, not one global
query count. Repetition order is counterbalanced and the formula/circuit,
rather than an individual repeated call, remains the inferential unit.

#### P7D — ordering, feasibility, memory, and guard behavior

- Run frozen variable relabellings on order-sensitive adders/multipliers and
  other base functions. Record CM transpose/permutation work and compare
  dispersion with fixed-order and reordered CUDD later in P8.
- Sweep the explicit-output size ladder and record success, typed refusal,
  timeout, output bytes, call-window temporary allocation, whole-worker RSS,
  cgroup peak, and cleanup.
- Re-evaluate the candidate temporary-memory estimate by representation and
  stage. Fit/calibrate only on the declared calibration cohort; freeze the
  rule before confirmation. A benchmark result does not change a production
  default without a separate API-policy decision.
- Preserve existing `k=17..20` and memory rows; add new frontier cells only
  where they fill a declared stratum or validate a changed implementation.

Primary metrics are task-total wall time and process-tree peak RSS. Secondary
metrics are construction and lowering time, per-query time, extraction and
restoration time, output size, page faults, cache hits/misses/evictions,
instruction/live-buffer counts, live support, and crossover query count.

**Gate P7:** the combined fast arm is exact, its lifecycle is fully charged,
and its behavior is consistent with the individual ablations. Every shard is
complete or has explicit retained failures; memory and estimator conclusions
remain scoped to the observed counters. If the combined arm is slower or
unstable, fix it and refreeze or retain that negative result before P8.

### Phase 8 — task-matched external campaign on Runpod

After separate exact authorization, run the pinned Linux native comparison in
pilot shards and then, only if clean, the larger development corpus:

- complete vector: `CM-Fast-Frozen`, CM baselines, CSE-flat/BitSet, and native
  CUDD with full extraction and output validation charged;
- count: CM/CSE popcount, native CUDD/ZDD where the declared set artifact
  applies, and native d4;
- SAT/witness: native CaDiCaL plus bounded CM/CSE diagnostic arms;
- equivalence/delta: CM/CSE, CaDiCaL miter, and native CUDD XOR/count;
- contexts and histories: fresh and resident CM/CSE, CaDiCaL assumptions, and
  CUDD restriction on the exact same frozen sequences;
- persistence/reload: exact CM artifact replay and native CUDD graph replay;
  d4 compiled-artifact replay only if its verified mode supports the declared
  contract.

Native CUDD timing must exclude out-of-task validation and split order
generation, manager/variable setup, build, dynamic reorder, restriction/query,
extraction, validation, serialization, and reload. Compare fixed order,
predeclared candidate orders, and CUDD's declared reordering method; retain the
actual final order and manager/root identities. d4 count includes CNF
translation and process startup in end-to-end totals. CaDiCaL records clause
translation, solver construction, assumptions, solves, and witness/core
validation separately.

The exact proposal must state manifests, locked dependencies, native hashes,
container and volume sizes, resource classes, fresh-allocation count, maximum
pod-hours, dollar caps, per-cell and campaign deadlines, watchdogs, owned
cleanup, evidence bounds, retry policy, and whether an interrupted shard may
resume only its never-attempted cells. The known zero-volume CPU transport is
an option, not standing authorization.

**Gate P8:** zero semantic mismatches, complete planned-cell reconciliation,
no unexplained backend substitutions/skips, owned cleanup confirmed, and
runtime/cost within the authorized boundaries. A native refusal is retained
and cannot be filled with a pure-Python proxy.

### Phase 9 — untouched confirmation and platform replication

Only if P8 succeeds:

1. Freeze all fixes, arms, primary metrics, exclusions, selectors if any,
   source/native identities, and the untouched confirmation manifest.
2. Run the confirmation corpus without tuning or dropping unfavorable cells.
3. Replicate the primary subset on at least five fresh allocations if the
   scout shows material between-allocation variance.
4. Keep host/CPU-model-stratified results, affinities, cgroup limits, image
   identities, and allocation metadata.
5. If runtime portability matters, run a secondary pinned Python/NumPy matrix
   after the primary configuration. It is a portability study, not additional
   independent formula evidence.
6. Run a separate throughput/concurrency study only if a real concurrent
   service workload exists; do not mix it with single-worker latency.

No scale-up is justified merely because one pilot ratio is favorable. Bugs
found in confirmation invalidate the affected frozen claim: fix, create a new
versioned confirmation cohort, and preserve the failed evidence.

**Gate P9:** the frozen confirmation ledger is complete, no tuning used its
results, host effects are retained rather than pooled away, and the primary
conclusion survives the predeclared cluster/host analysis or is reported as
inconclusive.

### Phase 10 — real cache, context, and incremental-edit economics

Collect or freeze real access and revision traces before optimizing policy.
Compare no cache, current entry-LRU, byte-LRU, and size/cost-aware admission.
Record compiler/schema/options and structural keys, artifact/retained/disk
bytes, build and serialization costs, hits/misses/evictions, invalidation,
phase changes, process boundaries, family/version/context identity, subsequent
query count, and corrupt/stale artifact controls.

For incremental compilation compare cold CM, current structural subtree/root
reuse, a minimal tracked-query red/green prototype if implemented, and
sharing-aware CSE-flat. Include digest/validation cost, changed/affected
regions, retained dependency state, adversarial wrong-hit cases, reversion,
and queries after each edit. Independently regenerated families do not count
as real edit histories.

**Gate P10:** adoption requires lower total workload cost and acceptable peak
and retained memory on untouched traces. Cache hit rate alone is insufficient.

### Phase 11 — conditional optimization frontier

These studies are authorized scientifically only when profiling or workload
evidence triggers them; each still needs operational approval:

- **Native/JIT word fusion:** factor program choice from executor choice using
  `{CM flat, CSE-flat/raw flat} × {current words, native/JIT words}`. Charge
  JIT compilation, dispatch, binding, copying, and conversion. Test AVX2,
  optional AVX-512/ternary fusion when available, scalar fallback, CPU feature
  dispatch, per-thread behavior, and peak memory.
- **Independent-block decomposition:** prove disjoint support, then compare
  explicit combination with implicit broadcast/Kronecker and lazy permutation
  plans. Charge final full materialization when required.
- **Streamed/tiling output:** compare bounded single-process tiling first. Add
  multiple processes or other hardware only if compute dominates transport and
  aggregate memory stays bounded. Report time to first chunk and total time.
- **Large-output frontier:** extend until prespecified timeout/memory/output
  stops. Never describe reduced peak memory as removing exponential output
  work.

**Gate P11:** exact reference equality, cold and warm accounting, a new
held-out batch, CPU-feature provenance, and a task-total benefit. Failure to
meet the workload precondition closes the branch without a run.

### Phase 12 — prespecified backend selector

Build a selector only if real volume exists in a region where arms cross.
Train on a frozen tuning corpus using only features available before executing
the selected backend: support, DAG/instruction/primitive-op counts if their
measurement cost is charged, operator mix, sharing, live buffers, output kind,
cache state, expected query count, budget, and platform class.

Compare the frozen selector with simple prespecified rules and each individual
backend on a new untouched circuit-held-out corpus. Report selector overhead,
geometric mean and maximum regret, `>=2x` misroute rate, failure/memory
behavior, schedule stability, and cross-machine transfer. Report an oracle
virtual-best only as an unreachable descriptive bound.

**Gate P12:** no in-sample production integration; adoption requires bounded
regret, no correctness/refusal regression, and a net task-total benefit after
feature and routing overhead.

### Phase 13 — CI, independent reproduction, and release evidence

Run focused and full relevant regression under the pinned environments, then
hosted CI. Produce a clean external reproduction bundle that rebuilds or
verifies native dependencies, replays a representative subset from manifests,
and independently recomputes results from raw rows. Require a separate person
or machine to reproduce source hashes, planned-cell reconciliation,
correctness, cleanup, and principal summaries before publication or a new
downloadable release.

**Gate P13:** no stronger public claim until the exact frozen bundle is
reproduced outside the authoring session and all known limitations accompany
the result.

### Runpod compute envelope and sharding

The earlier 20-minute smoke limit is historical, not a scientific requirement
for this plan. A reasonable extended program, after local/native readiness,
is approximately:

| Stage | Illustrative CPU pod-hours | Purpose |
| --- | ---: | --- |
| Native/readiness and measurement scout | 2–4 | Verify Linux controls, native adapters, noise, and cell costs |
| CM internal ablation and scaling | 8–20 | P7A–P7D on development data |
| Task-matched external development campaign | 8–20 | P8 pilot and larger development cohort |
| Untouched multi-allocation confirmation | 10–30 | P9 confirmation and host variance |
| Conditional cache/JIT/streaming/selector work | 10–40 each triggered branch | P10–P12 only after their gates |

Pod-hours are planning magnitudes, not authorization or a cost promise. Every
proposal must refresh current quotes and name a hard dollar cap. Prefer
one-to-six-hour immutable shards with an independent watchdog, atomic evidence,
and owned deletion, rather than one extremely long fragile process. A shard
can stop early on convergence or failure; unused planned compute is not a
reason to add unreviewed work. Run independent shards sequentially unless a
separately approved throughput or platform-replication design requires
concurrency.

## 9. Analysis and claim rules

The independent formula, circuit, or version history is the statistical unit;
timed repetitions are repeated observations. Use paired log time/RSS ratios,
cluster-aware intervals, medians and tail quantiles, and host-stratified
summaries. Retain absolute measurements alongside ratios.

Predeclare one primary comparison and metric per task family. Treat operator,
support, sharing, depth, schedule, lifecycle, platform, and output contract as
crossed factors rather than pooling them into one ratio. Use hierarchical or
cluster bootstrap intervals over independent source units; never resample
timed repetitions as if they were new formulas. Report raw paired scatter,
distributions, and per-case outcomes so aggregates can be audited.

Timeout/refusal frontiers use completion rates and interval-censored times,
not medians computed only from survivors. Missing cells, resource mismatches,
and semantic/cleanup failures are separate categories. Apply a declared
family-wise or false-discovery procedure to secondary hypothesis families;
exploratory findings remain labeled exploratory and require a new cohort.

Primary performance claims should use task-total time. A practical provisional
gate for saying one frozen arm is faster is:

- zero semantic errors in both arms;
- at least a 5% median paired task-total improvement;
- a cluster-aware 95% interval for the time ratio entirely below `1.0`;
- no unexplained material regression in peak RSS, failure rate, or required
  artifact completeness.

If those conditions are not met, report “inconclusive at this scale.” Kernel
results may explain the outcome but cannot override the end-to-end result.
Crossovers should be reported as intervals over `q`, not as an exact universal
threshold unless the observations support that precision.

A `CM-Fast-Frozen` production adoption additionally requires:

- exactness on all regression and confirmation cases;
- explicit fallback/refusal behavior;
- no hidden cache priming or answer caching;
- bounded memory under the production guard;
- a task-total gain on its intended workload class;
- preservation of the consumer's required output contract.

## 10. Deliverables

Each executed stage should produce:

- signed-off protocol and authorization boundary;
- source/input/dependency/native-binary manifests;
- complete planned-cell ledger and realized order ledger;
- independent scalar or task-specific oracle records;
- append-only raw measurement rows;
- process/RSS and cleanup evidence;
- exact mismatch/refusal/failure ledger;
- machine-readable summary and independent reanalysis script;
- checksum manifest and frozen source snapshot;
- short result note separating findings, limitations, and unsupported claims.

The final report should contain these distinct views:

1. IR preparation, structural compression, and lowering;
2. CM internal representation/no-reinflation ablations;
3. cold one-shot task totals;
4. warm/reused amortization, cache, context, and edit curves;
5. task-matched comparisons with other methods;
6. feasibility/refusal and memory frontiers;
7. variable-order and platform dispersion;
8. failures, negative results, and claim boundaries.

## 11. Immediate implementation order

1. Freeze the exact semantic and artifact contracts for IR, dense, bigint,
   words, no-reinflation, reduced support, restoration, count, and streaming.
2. Extract common task/result schemas from the existing measurement, session,
   and native-contract scripts.
3. Implement and test Linux process-tree/RSS supervision.
4. Add IR-stage counters and exact signature/program compatibility records.
5. Implement deterministic balanced schedules, immutable shards, resume-only-
   unattempted behavior, and strict ledger reconciliation.
6. Add CM arm-specific correctness, lifecycle, memory, and analysis tests.
7. Hash-pin and run bounded native d4 known-count probes.
8. Obtain and verify current native CUDD, and ZDD only for its matched task, in
   the pinned Linux image.
9. Implement backend adapters for the task matrix, including translation,
   extraction/restoration, startup, and cleanup cost.
10. Run the trivial local smoke and freeze a review package.
11. Run a short authorized Runpod native/measurement scout; estimate noise,
    cell cost, memory, and safe shard sizes without making performance claims.
12. Inventory and freeze development plus new confirmation corpora without
    inspecting confirmation timing results.
13. Write an exact multi-shard Runpod P7 proposal with refreshed quotes and
    hard pod-hour/dollar limits.
14. Complete the CM internal ablation before interpreting external rankings.
15. Run P8 task-matched external comparisons after native readiness and a new
    exact authorization.
16. Freeze and run P9 confirmation across fresh allocations.
17. Trigger P10–P12 only when the real-workload/profile gates are satisfied.
18. Complete P13 CI and independent reproduction before stronger publication.

## 12. Stop conditions

Stop before paid timing if any arm has a semantic mismatch, ambiguous output
contract, unverified native identity, unowned descendant, unbounded output,
or incomplete cleanup. Stop a paid run on its declared deadline, cost bound,
evidence-size bound, resource mismatch, watchdog loss, or first unreconciled
correctness failure according to the frozen protocol.

Do not claim:

- that the recent 630-call memory study ranked speed;
- that dense/bigint/words cover all CM algorithms or speedups;
- that a host CPU count is the pod allocation;
- that call-window `tracemalloc` is process RSS;
- that a cache-hit result represents unknown-version construction;
- that symbolic build time equals explicit-vector completion;
- that a favorable selected subset establishes general superiority;
- that retries, repeated calls, relabellings, outputs from one circuit, or
  multiple pods increase the number of independent formulas;
- that a virtual-best or post-hoc fastest arm is an implementable selector;
- that successful frontier rows justify excluding refusals/timeouts.

## 13. Decision point after this plan

The next useful work is implementation and local validation through P5; it
does not require another pod. Once P0–P5 pass, prepare an exact Runpod
readiness scout and then the multi-shard P7 campaign. The program is designed
to use substantial compute when it increases independent coverage, measures a
frontier, or replicates platform effects. Comparative native timing follows
only after d4/CUDD readiness and the CM ablation are clean, and each paid stage
requires its own explicit resource and budget authorization.
