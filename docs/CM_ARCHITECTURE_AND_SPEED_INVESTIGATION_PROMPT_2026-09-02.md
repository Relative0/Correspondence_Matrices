# Copy-paste prompt — comprehensive CM architecture and speed investigation

**Date:** 2026-09-02  
**Project root:** `C:\Users\brian\Documents\CM_Computation`  
**Purpose:** Audit, profile, improve, and validate the speed of the project's Correspondence Matrix implementations and related execution architectures.  
**Status:** Investigation and execution prompt. This prompt is not, by itself, authorization to upload private files, create cloud resources, publish, commit, or push.

---

## Prompt begins

Work in the project at:

`C:\Users\brian\Documents\CM_Computation`

Conduct a comprehensive, evidence-led investigation of the architectures used to construct, represent, compile, materialize, and evaluate Correspondence Matrices (CMs). The investigation must cover basic dense CMs, ordered CM IR, packed representations, flat compiled programs, no-reinflation paths, persistent and prepared execution, and any other implementation that is relevant to CM speed or memory use.

Do not stop after writing a plan. Inspect the current code and saved evidence, run the appropriate local checks, build missing measurement or correctness tools when justified, profile the real implementation, implement low-risk improvements that survive the gates below, and produce a decision-ready report. Use Runpod for substantive computation after the applicable authorization and frozen-input gates have been satisfied. Keep local work small, bounded, and useful for preflight, correctness, and debugging.

The central question is:

> What changes can make the CM family materially faster on the workloads for which its semantic structure, reusable compiled state, restriction behavior, or output representation is actually useful, while preserving exact correctness and accounting honestly for construction, conversion, memory, and lifecycle costs?

Answer this separately for:

1. basic dense CMs and their construction/materialization path;
2. ordered CM IR construction, canonicalization, interning, reuse, and evaluation;
3. packed CM execution using Python integers and `uint64` words;
4. flat raw and structural-CSE programs used as implementation controls;
5. no-reinflation and reduced-output paths;
6. repeated evaluation, fixed-context, related-version, and incremental workloads;
7. end-to-end application workloads, including parsing, lowering, execution, extraction, and serialization;
8. memory-bound and output-bound regimes;
9. contingent native, JIT, parallel, or streamed implementations;
10. comparisons with task-matched non-CM methods, after the CM implementations and benchmark contracts are verified.

Do **not** spend time remapping historical “Inflation/Deflation” terminology. Use exact current implementation and symbol names. Refer to “no-reinflation” only when discussing the existing no-reinflation implementation or its directly derived variants.

---

## 1. Operating rules

### 1.1 Preserve provenance and unrelated work

Before editing anything:

- Read every applicable `AGENTS.md`.
- Record `git rev-parse HEAD`, `git status --short`, Python and dependency versions, OS, CPU affinity, logical host CPU count, and relevant memory-limit evidence.
- Treat the working tree as live and possibly dirty. Do not reset, clean, revert, reformat, stage, or overwrite unrelated changes.
- Do not assume that a report dated before the current working tree describes the current code. Link every measured result to exact source hashes and, when possible, the Git commit plus a manifest of uncommitted transitive dependencies.
- Never read, print, copy into evidence, edit, or commit `.env` files or credentials.
- Do not commit or push unless the user explicitly requests it.

### 1.2 Separate kinds of evidence

For every claim, label its basis as one of:

- current source inspection;
- current local test;
- current local measurement;
- frozen Runpod result;
- historical report;
- prototype or projection;
- hypothesis;
- theoretical limitation.

Never silently promote a projection, session-only observation, stale report, or synthetic microbenchmark into a current result. Preserve negative and null results.

### 1.3 Cloud execution and cost safety

The user prefers Runpod for any computation beyond trivial local checks. Before any new Runpod create or private upload:

- locate and read the current Runpod handoff, proposals, authorization records, controller, cleanup rules, and attributable billing evidence;
- determine whether an existing authorization precisely covers the new bundle, wrapper, workload, resource, storage, time, replacement policy, and cost cap;
- do not infer that an earlier authorization for a different manifest or workload transfers to this one;
- if exact authorization is absent, prepare a frozen proposal and manifest, report the hashes and limits, and ask for approval;
- reconcile the remaining campaign budget rather than assuming the historical `$5` ceiling is unused;
- use the already proven secure HTTP controller route unless current evidence gives a concrete reason to change it;
- use one owner, at-most-once workload execution, a hard watchdog, atomic state publication, identity-bound cleanup, final inventory checks, bounded transport, and attributable billing reconciliation;
- preserve failed preflight and attempt directories; never hide failed or partial runs;
- do not allocate replacements beyond the exact authorization.

Do not treat the host's reported logical CPU count as allocated vCPU count. Record CPU affinity, cgroup limits when present, actual process configuration, and the provider resource response separately.

---

## 2. Read-first source and evidence set

Start with these files, then follow their links and imports. Verify all paths against the current tree.

### 2.1 Current synthesis and decision records

- `docs/CM_COMPUTATION_DEEP_TECHNICAL_DOSSIER.md`
- `docs/audits/2026-08-25-cm-deep-performance/CM-OPTIMIZATION-BACKLOG.md`
- `docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/continuation-20260829-125214/CM-FAST-VARIANTS-COMPARATIVE-BENCHMARK-PLAN-20260829.md`
- `docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/continuation-20260829-125214/CM-FAST-VARIANTS-COMPARATIVE-BENCHMARK-PLAN-AUDIT-20260829.md`
- `docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/continuation-20260829-125214/CM-COMPARATIVE-NEXT-STEPS-EXECUTION-PLAN-20260830.md`
- `docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/continuation-20260829-125214/RUNPOD-P7-W4-TIMING-FINAL-RESULT-AUDIT-20260901.md`
- `docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/continuation-20260829-125214/RUNPOD-P7-W5-INTERIM-STATUS-20260901.md`

Do not repeat W4 or W5 blindly. Establish what completed, what remains partial, what has been superseded, and whether current source differs from their frozen bundles.

### 2.2 Core architecture

- `cm_exprlib.py`
- `cm_expr_serde.py`
- `cm_lm.py`
- `cm_operator_difference.py`
- `cm_build.py`
- `cm_build_lazy.py`
- `cm_build_pair.py`
- `cm_normalize.py`
- `cm_ir.py`
- `bitset_backend.py`
- `cm_parallel.py`
- `cmbench/backends/bitset_engine.py`
- `cmbench/output_budget.py`
- `cmbench/comparative/arms.py`
- `cmbench/comparative/p7.py`

Find all callers, tests, wrappers, benchmarks, caches, environment switches, and serializers associated with these files. Use `rg` and Python AST inspection rather than relying only on filenames.

### 2.3 Historical optimization and negative-result reports

Locate and read the current copies of at least:

- `CM_ARCHITECTURE_AND_AUDIT.md`
- `CM_speedup_investigation_phase1.md`
- `CM_speedup_phase2_report.md`
- `CM_no_reinflation_report.md`
- `CM_ir_cost_report.md`
- `CM_persistent_cache_report.md`
- `CM_partial_hybrid_report.md`
- `CM_flat_liveness_speedup_report.md`
- `FABLE_CM_SPEEDUP_AGENDA.md`
- `CM_tierC_rescope_report.md`
- `CM_parallel_validation_report.md`
- `CM_parallel_stress_test_report.md`

For each, identify the code version, workload, baseline, timing boundary, result, limitation, and whether later evidence supersedes it. Do not reopen a rejected idea without a new workload, new mechanism, or clear measurement showing that its prior limiting condition has changed.

---

## 3. Known evidence anchors to reconcile, not assume

Use these as audit leads. Confirm them from primary saved artifacts and current source before repeating or extending them:

- The historical environment-building cliff above small supports was addressed with vectorized NumPy packing, with large measured improvements and bit-identical outputs on its bounded cohorts.
- Cached CM-node hashing, identity-keyed evaluation memoization, and shared structural-digest memoization have already been investigated or implemented. Locate their exact current forms before proposing another generic memo layer.
- No-reinflation historically reduced work relative to hybrid reinflation on some slices, but often remained slower than pure packed evaluation. This makes boundary and contract profiling more valuable than assuming reinflation itself is the remaining bottleneck.
- Flat last-use freeing reduced live scratch in some cases but was generally neutral or negative for elapsed time. Reopen it only when a current memory-bound workload makes the trade worthwhile.
- Partial-hybrid structure preservation frequently lost to full packed collapse because of boundary conversions.
- Multiprocessing did not activate profitably on the normal grids and showed only limited or intermittent benefit under forced stress. Parallelism needs a real coarse-grained workload, not another small-expression microbenchmark.
- W4's frozen timing scout found the current one-memo and historical two-memo ordered-IR arms effectively tied, while raw-flat and CSE-flat controls remained close. Verify exact ratios and uncertainty in the final audit.
- W4 relation results showed different winners by contract; structural-CSE flat was strong, packed words were competitive, and no-reinflation did not dominate dense across the full relation grid. Recover the complete table rather than quoting selected cells.
- C34 one-shot natural complete-output cases favored direct packed AST evaluation on their bounded support range.
- C35 repeated restrictions made sharing-aware CSE-flat the strongest fixed method on that cohort; CM improved relative to direct AST but did not win the fixed-method comparison.
- C36 suggested that current shared-DAG memoization could change results at wider supports, but the earlier freeze omitted transitive performance dependencies. Treat any current-versus-frozen comparison as a projection until a clean causal A/B is run.
- A bounded screen/materialize study reported a material improvement over exhaustive execution, while a separate cheap-proposal study could not avoid full completion under the frozen global-best contract. These answer different questions.
- The W5 campaign was recorded as partial in its interim status. Determine whether later artifacts completed it before scheduling new work.
- Current session-only routing or selector observations are not durable benchmark evidence and must not control production behavior.

For each anchor, decide one of: **confirmed current**, **confirmed historical**, **superseded**, **not reproducible from saved evidence**, or **requires a clean follow-up**.

---

## 4. Define the objects being compared

Create a precise architecture inventory. At minimum, distinguish:

| Object or path | Meaning to establish | Typical cost boundary to measure |
|---|---|---|
| Mathematical CM | Boolean relation over ordered row and column bases | semantic contract only |
| Basic dense CM | Explicit NumPy Boolean matrix, generally shaped by powers of two | build, lift, align, combine, transpose/copy, memory, output |
| Ordered CM IR | Interned/canonicalized Boolean-operation DAG with ordering and materialization semantics | parse/adopt, digest, canonicalize, intern, liveness, lower, materialize |
| Direct AST bitset | Direct evaluation of the expression with packed truth vectors | environment build, DAG traversal, primitive operations, output |
| Raw flat program | Slot-based lowering without structural CSE | compile, bind, evaluate, extract |
| Structural-CSE flat program | Flat program with shared structural nodes | digest/CSE compile, schedule, scratch, evaluate |
| Packed bigint CM | Truth-vector or CM data packed into Python integers | environment, integer operations, conversion, extraction |
| Packed-word CM | Explicit `uint64` word arrays and scratch plan | allocation, fill, kernel, masking, copies, output |
| No-reinflation path | Final or hybrid result that avoids rebuilding a dense 2-D CM | reduced evaluation, metadata, extraction, any reinflation avoided |
| Prepared/reused execution | Compiled object, bound environment, persistent cache, or session reused across calls | setup once, per-call, invalidation, lookup, memory retention |
| Lazy/pair/special path | Specialized construction or alignment implementation | eligibility, semantic equivalence, activation, fallback |
| Parallel/native/streamed path | Conditional execution strategy | startup, transfer, scheduling, useful work, teardown |

Do not rank unlike artifacts without explaining the contract difference. In particular:

- an ordered CM IR artifact and a flat Boolean program are not interchangeable compiler products;
- full dense relation materialization and a packed truth vector have different output contracts;
- reduced restrictions and full-output completion have different output volumes;
- compile-once results cannot be compared with one-shot results unless setup is reported separately and an honest reuse count is stated;
- an independent scalar oracle establishes correctness but is not automatically a meaningful performance competitor.

Produce a Mermaid diagram of the current dataflow from input parsing through all compilation, lowering, execution, materialization, extraction, and serialization paths. Annotate cache boundaries, canonicalization points, conversion boundaries, dense allocations, packed allocations, wrapper calls, and possible repeated work.

---

## 5. Architecture audit questions

Answer each question with source references, call paths, tests, and measurements where appropriate.

### 5.1 Basic dense CM construction and evaluation

1. Where are row and column bases chosen, ordered, normalized, and canonicalized?
2. Which operations allocate new dense arrays? Which use views, broadcasts, cached permutations, or cached lifts? Which force a copy because of layout, dtype, transpose, or contiguity?
3. How much time and memory are spent in variable discovery, layout calculation, row/column permutation, lift, alignment, pointwise combine, final transpose, and serialization?
4. Are the cached permutation and lift keys compact, stable, and cheap relative to the work they save?
5. Is a dense matrix constructed when the caller ultimately needs only a truth vector, a restriction, a scalar, a hash, or a stream?
6. Which parts are inherently proportional to explicit output size, and which overheads can be reduced without changing the output contract?
7. Do dtype, shape, memory order, temporary allocation, or NumPy dispatch dominate at any supported sizes?
8. Are there safe opportunities for preallocation, destination-aware operations, view reuse, fused normalization, or eliminating redundant layout conversions?
9. Are `cm_build.py`, `cm_build_lazy.py`, `cm_build_pair.py`, and IR materialization semantically aligned on constants, dead axes, variable order, and all supported operators?

### 5.2 CM IR construction

1. Map `CMIRBuilder`, `CMNode`, structural digests, keys, canonicalization, interning, foreign-node adoption, persistent caches, liveness analysis, and output-budget checks.
2. Measure cold and warm costs for structural digesting, canonical sorting, key construction, hash lookup, object allocation, liveness rebuilding, and lowering.
3. Identify repeated tree or DAG traversals. Determine whether each traversal uses identity, equality, structural digest, or canonical keys and whether it recomputes data already known.
4. Verify the current state of the one-memo versus historical two-memo design. Do not infer a causal speedup from results that lack a clean before/after source freeze.
5. Test the ready compact canonical-key hypothesis from the optimization backlog, if it remains unimplemented and current profiling still identifies key/canonicalization cost as material.
6. Examine object layout and metadata size. Estimate retained bytes per unique node and per compiled artifact with both analytical accounting and measured memory.
7. Identify which ordering and metadata guarantees downstream callers actually consume. Do not remove guarantees merely to win a flat-program benchmark.
8. Determine when persistent caching saves work, when it merely converts a cold benchmark into an all-hit benchmark, and how invalidation, eviction, and memory retention behave.
9. Measure benefits against DAG uniqueness and sharing metrics such as unfolded occurrences `U`, unique identity nodes `N`, `U/N`, structural duplicate rate, depth, arity, and operator mix.

### 5.3 Packed and flat executors

1. Audit direct AST evaluation, raw flat, structural-CSE flat, CM-node bigint evaluation, word-array evaluation, last-use schedules, prepared execution, and environment construction.
2. Verify whether shared DAGs are traversed once per identity or repeatedly. Include the current `eval_expr_bitset` memoization state and the restricted-evaluation helpers in the audit.
3. Separate compilation, environment creation, binding, scratch allocation/clearing, kernel execution, extraction, conversion, and wrapper overhead.
4. Explain the observed size crossover between Python bigint and `uint64` words. Measure it on relevant shapes rather than installing a single global threshold from synthetic data.
5. Check word-edge correctness at widths and supports around 0, 1, 63, 64, 65, 127, 128, and 129 bits/variables where the relevant guard permits the case. Verify tail masking and signed/unsigned conversions.
6. Determine whether last-use freeing reduces peak memory enough to justify its allocator and dispatch costs. Preserve the negative timing result if it still holds.
7. Consider native or JIT word fusion only if profiles show a repeated, batchable word kernel dominates setup, copy, and output costs. Use explicit `uint64` semantics; do not reinterpret Python bigint internals.

### 5.4 No-reinflation, restrictions, and partial outputs

1. Map the exact contracts and callers of `materialize_hybrid_no_reinflate`, `FinalNoReinflateResult`, and related restriction paths.
2. Quantify work avoided: dense allocation, layout expansion, reinflation, conversion, and output serialization.
3. Quantify remaining boundary overhead: metadata construction, slicing, fixed-map handling, packed-to-dense or dense-to-packed conversions, and wrapper layers.
4. Compare only equivalent results: full output with full output, reduced result with the same reduced result, and restored/full result with the same restored/full result.
5. Test realistic repeated partial contexts and changing fixed assignments. Include compile once plus a query-count ladder, not only a single call.
6. Verify the known limitation that a frozen global-best contract may still require full completion. Do not claim that a cheap proposal avoids the oracle work unless the contract or proof changes.

### 5.5 Reuse, incremental compilation, and related versions

1. Distinguish parse reuse, digest reuse, node interning, compiled-artifact reuse, bound-environment reuse, scratch reuse, and result reuse.
2. Build or locate a real structured workload with related expressions, edits, restrictions, or repeated queries. Avoid an artificial all-hit cache trace as the principal evidence.
3. Measure cold first use and amortized per-call cost for query counts such as `q = 1, 2, 4, 8, 16, 32, 64` where feasible.
4. Report cache hit rate, bytes retained, invalidation correctness, lookup time, eviction behavior, and break-even query count.
5. Compare cold CM IR, current persistent cache, any incremental prototype, raw flat, structural-CSE flat, and direct AST on the same semantic job.
6. Do not add a learned selector unless current natural traffic demonstrates a material decision problem and the selector can be evaluated out of sample with abstention and deterministic fallback.

### 5.6 End-to-end and operational architecture

1. Profile parsing, Verilog/Yosys conversion if used, expression normalization, compilation, evaluation, output checking, JSON/ZIP work, HTTP transport, and supervisor overhead separately.
2. Make output lifecycle explicit: produced, serialized, transported, verified, retained, and cleaned up.
3. Detect artifact-path mismatches, stale outputs, partial JSON publication, duplicate execution, and misleading success markers.
4. Report both kernel timing and caller-visible end-to-end timing. A kernel win that disappears at the wrapper boundary is not an application win.

---

## 6. Test and evidence audit

Build a machine-readable test/evidence ledger with one row per test group or result artifact. Include:

- subsystem and exact symbols covered;
- semantic contract and failure mode;
- unit, property, differential, integration, performance, operational, or cloud classification;
- current test path and command;
- fixture source and whether it is synthetic, natural, converted, or real corpus data;
- supported operators and shapes;
- support-size range and boundary values;
- representations compared;
- independent oracle used;
- code/manifests/result hashes;
- last verified status;
- reproducibility status;
- known blind spots;
- superseding evidence, if any.

Run the smallest relevant existing suites first. Then run the broader non-neural suite if the environment and time allow. Reuse existing fixtures and extend current test files when coverage naturally belongs there. Add tests only to close meaningful gaps.

At minimum, verify:

- all 16 supported binary Boolean operators and every supported unary/constant form;
- constants, unused variables, dead axes, empty and one-variable cases;
- ordered row/column bases and nontrivial variable permutations;
- fixed values, reduced output, restored output, and contradictory assignments;
- shared identity DAGs, structurally equal nonidentical DAGs, foreign-node adoption, and deep or wide expressions;
- associative and commutative canonicalization without changing noncommutative operations;
- serialization and deserialization round trips;
- dense, packed-bigint, packed-word, no-reinflation, CM IR, raw-flat, CSE-flat, and direct-AST output equality where contracts match;
- output-budget and memory-estimator values immediately below, at, and above limits;
- cache invalidation, fallback, and eviction behavior;
- at-most-once remote execution, bounded upload/download, source freezing, resource validation, watchdog acknowledgment, ownership-only cleanup, final inventory, and billing reconciliation.

Use an independent scalar evaluator or independently generated truth table for correctness. Never use one optimized implementation as the only oracle for another. Record complete-output hashes as well as sampled comparisons when the full output is within the approved bound.

Treat test counts carefully: distinguish collected tests, passing test cases, parameterized subtests, benchmark cells, jobs, calls, and rows. A high count does not compensate for a missing operator, boundary, natural family, or independent oracle.

---

## 7. Measurement design

### 7.1 Workload axes

Construct a balanced matrix across the dimensions that affect architecture choice:

- support size and output size;
- row/column split and relation shape;
- expression size, depth, operator mix, and constant frequency;
- identity sharing, structural duplication, and canonical-equivalence opportunities;
- one-shot versus compile-once/repeated execution;
- full materialization, reduced restriction, restored output, and scalar/query output;
- fixed-support repeated assignments;
- related-version edits;
- natural converted cases, real project corpus cases, and controlled synthetic stress cases;
- cold process, warm process, cold cache, warm cache, and alternating schedule.

Use existing frozen P7/W4/W5 contracts where they answer the question. Add new cases only for a documented coverage gap. Keep a small calibration cohort, a development cohort, and a final untouched confirmation cohort.

### 7.2 Required timing boundaries

Record, where applicable:

1. parse/deserialization;
2. variable discovery and ordering;
3. digest/key/canonicalization/interning;
4. IR or flat-program construction;
5. liveness and scratch planning;
6. environment construction;
7. bind/fixed-map preparation;
8. dense lift/align/permute/combine;
9. packed kernel execution;
10. materialization or restriction;
11. extraction and conversion;
12. output hashing/serialization;
13. wrapper and subprocess overhead;
14. total caller-visible time.

Record counts and structural metrics next to time so a speed difference can be explained rather than merely observed.

### 7.3 Memory boundaries

Record:

- predicted output bytes and predicted temporary bytes by representation;
- `tracemalloc` peak where it covers Python/NumPy allocations adequately;
- process RSS high-water evidence where available;
- retained cache/artifact bytes after each lifecycle stage;
- dense array, packed integer, word scratch, node, instruction, and serialized-output sizes;
- allocation counts or representative allocation sites when profiling supports them.

Harden representation-specific memory estimates before changing any default guard. Historical evidence indicates that a generic `2 * output_bytes` estimate can materially understate dense peak memory; confirm the current behavior on bounded cases.

### 7.4 Statistical protocol

- Calibrate timer and profiler overhead before using fine-grained spans.
- Use randomized or balanced interleaving to control drift and first-run effects.
- Warm only the layers the workload contract says are reusable.
- Use enough repetitions for stable medians and uncertainty intervals, but do not multiply large explicit outputs needlessly.
- Report medians, robust spread or bootstrap intervals, sample count, failures, and censoring.
- Retain raw rows. Do not report only aggregate ratios.
- Predeclare primary metrics, tie/noise bands, fallback rules, and exclusion rules.
- Separate exploratory scout results from frozen confirmation results.
- Compare end-to-end ratios and kernel-only ratios side by side.

---

## 8. Required baselines and fairness rules

For implementation studies, include the smallest fair set from:

- direct AST packed evaluation;
- raw flat compilation/evaluation;
- structural-CSE flat compilation/evaluation;
- current ordered CM IR;
- historical/control CM IR only when its source can be reproduced exactly;
- basic dense CM;
- packed bigint CM;
- packed-word CM;
- no-reinflation CM;
- prepared or persistent CM variants.

For later method comparisons, select task-matched external baselines based on the actual problem:

- truth-table or Boolean expression evaluation;
- repeated restrictions or cofactoring;
- Boolean equivalence or canonical comparison;
- symbolic manipulation;
- SAT/SMT queries;
- BDD/ZDD operations;
- ANF/GF(2) algebra;
- circuit simulation or synthesis;
- enumeration or materialized relation production.

Do not claim a general CM victory from a workload built around a CM-specific artifact. Conversely, do not penalize CM for producing a richer artifact without reporting the value and cost of that artifact. Compare equivalent answers first; present richer-artifact costs separately.

External comparisons are a later gate. First establish that the CM variants are correct, their timing boundaries are honest, and their current fastest configurations are frozen. Use maintained native tools only when installation, versioning, invocation, correctness checking, and license terms are documented. Include conversion and startup cost unless the workload contract justifies amortization.

---

## 9. Prioritized hypotheses and experiments

Treat this list as a starting order, not as assumed conclusions. Reprioritize only with evidence.

### H0 — Establish the current source truth

The working tree and current dossier may be ahead of the last committed/frozen benchmark source. Produce a transitive dependency manifest and reconcile current code against W4, W5, C34, C35, C36, and older reports before interpreting speed differences.

**Gate:** no causal performance claim without exact source and dependency hashes.

### H1 — Shared-DAG memoization removes redundant direct-evaluator traversal

Audit current per-call identity memoization in `eval_expr_bitset` and every related restriction evaluator. Build a clean causal A/B using frozen source copies or a controlled switch, not a comparison between non-equivalent trees or outputs. Stratify by `U/N`, depth, and support.

**Gate:** identical outputs, no regression on low-sharing cases outside the predeclared noise band, and a replicated benefit on high-sharing natural or corpus cases.

### H2 — Compact canonical keys can reduce ordered CM IR cold compile cost

If current profiles still place meaningful time or memory in `_canonicalize_commutative_args`, `CMNode.key`, structural sorting, or foreign adoption, prototype the ready compact-key design from the backlog.

**Gate:** exact ordered-IR and packed-output hashes; no regression in interning, digest, variable order, path identity, or serialization; cold compile and peak memory improve on high-sharing cases; neutral results remain neutral.

### H3 — Basic dense CM has avoidable layout, lift, and temporary-copy costs

Instrument `cm_build.py`, `cm_normalize.py`, and dense IR materialization to locate redundant permutation, lift, transpose, broadcast, or copy work. Prototype only source-supported changes such as cached layouts, destination-aware operations, safe views, preallocation, or fused adjacent transformations.

**Gate:** same dense matrix, bases, dtype, and ordering; representation-specific peak-memory checks; benefit survives caller-visible measurement rather than only a single NumPy primitive.

### H4 — No-reinflation can be improved at its conversion and wrapper boundaries

Historical no-reinflation results avoided dense rebuilding but often remained slower than pure packed evaluation. Profile metadata, conversion, extraction, fixed-map, and wrapper costs before changing the kernel.

**Gate:** equivalent reduced/restored contract, independent oracle, improvement across realistic repeated restrictions, and no misleading comparison with full dense output.

### H5 — Prepared execution and lifecycle reuse have a measurable break-even point

Measure compiled artifact, bound environment, scratch, and cache reuse separately. Determine break-even query counts and memory retention on real related expressions or repeated restrictions.

**Gate:** include cold setup, invalidation, lookup, retention, and end-to-end time; do not adopt from an all-hit synthetic trace alone.

### H6 — Representation-specific memory estimates can prevent unsafe or needlessly conservative choices

Calibrate dense, bigint, word, IR-node, flat-instruction, and serialized-output estimates against bounded measured peaks.

**Gate:** conservative on the validation matrix, explicit safety margin, boundary tests, and no default-routing change until confirmed on a separate cohort or machine.

### H7 — A native or fused word kernel is useful only in a repeated batch regime

Proceed only if H1–H6 show that word-kernel operations dominate after setup and copies. Prototype a narrow explicit-`uint64` kernel with a pure-Python reference and bounded output.

**Gate:** installation and build are reproducible, all word boundaries pass, transfer/setup are charged, repeated natural workload wins, and fallback remains exact.

### H8 — Parallel or streamed CM construction is workload-specific

Historical multiprocessing results were mostly overhead-bound, with only small or intermittent forced-stress benefits. Revisit only for a real live-tensor or streamed-output workload whose chunks contain enough useful work.

**Gate:** single-process bounded baseline, activation evidence, memory and first-chunk latency, process startup/IPC charged, deterministic assembly, and safe cleanup.

### H9 — Incremental compilation across real edits can exploit CM IR structure

Use naturally related versions or a realistic edit generator. Compare current cold compilation, current caches, an incremental prototype, raw flat, and CSE-flat.

**Gate:** exact invalidation, realistic hit pattern, retained-memory accounting, and a break-even result on untouched confirmation sequences.

### H10 — Task-matched external methods define where CM is competitive

After the fastest honest CM configurations are frozen, benchmark them on equivalent application tasks against suitable direct, CSE, BDD/SAT/ANF/circuit, or other methods.

**Gate:** same inputs and outputs, independent correctness, conversion/setup charged, fixed versions and seeds, adequate coverage, and claims restricted to the measured task family.

Do not spend compute on claims that contradict explicit-output lower bounds, universal tensor shortcuts without a proved workload structure, semantic XOR as a general quotient, or global semantic canonicality from current structural keys.

---

## 10. Phased execution plan

### Phase A — Snapshot and provenance

1. Record source, environment, dirty-state, and evidence hashes.
2. Identify transitive dependencies for every planned executable.
3. Reconcile frozen bundles against current source.

**Exit:** a reproducible source/evidence ledger with no ambiguous current-versus-frozen claims.

### Phase B — Architecture map

1. Trace public entry points to internal construction/evaluation paths.
2. Build the architecture table and Mermaid dataflow.
3. Mark semantic, cache, allocation, conversion, and output boundaries.

**Exit:** every benchmark arm names an exact artifact and contract.

### Phase C — Test and result audit

1. Inventory existing tests and saved runs.
2. Map each result to source, workload, oracle, and limitation.
3. Close important correctness gaps before timing changes.

**Exit:** baseline correctness passes and unresolved gaps are explicit.

### Phase D — Measurement harness and calibration

1. Reuse current comparative harnesses where possible.
2. Add stage timings, structural counters, memory boundaries, and raw-row output without changing semantics.
3. Calibrate instrumentation overhead and validate schedules.

**Exit:** a small frozen local scout produces reproducible, internally consistent evidence.

### Phase E — Current-baseline profiling

1. Profile basic dense CM, CM IR, direct AST, raw flat, CSE flat, bigint, words, and no-reinflation on equivalent contracts.
2. Include one-shot, compile-once, repeated restriction, and related-version regimes.
3. Identify the top three time and memory costs per regime.

**Exit:** hypotheses are ordered by measured addressable cost, not intuition.

### Phase F — Causal low-risk experiments

Run clean A/B experiments for H1–H6 one at a time. Do not combine optimizations until each component's correctness and effect are known. Keep reversible prototypes isolated and reviewable.

**Exit:** each experiment is accepted, rejected, or deferred with raw evidence and a stated reason.

### Phase G — Real structured workloads

Finish or reconcile the W5 campaign before creating a redundant workload. Then add only the real repeated-query, related-version, partial-context, operator-calculus, or corpus cases needed to cover remaining gaps.

**Exit:** at least one natural or corpus-backed workload exercises each claimed benefit.

### Phase H — Conditional larger implementations

Only after profiles justify them, evaluate compact IR storage, incremental compilation, native/fused words, block decomposition, streamed output, or parallel execution.

**Exit:** every larger prototype has an activation condition, fallback, correctness proof/test, and end-to-end break-even analysis.

### Phase I — Frozen Runpod confirmation

1. Freeze exact sources, tests, wheels, datasets, wrapper, command, seeds, bounds, and result schema.
2. Verify manifest closure locally without reading secrets.
3. Obtain or cite exact authorization.
4. Run one owned bounded campaign under the approved cost/time/resource limits.
5. Retrieve, hash, independently reconcile, clean up, inventory, and reconcile billing.

**Exit:** result evidence is complete, attributable, and reproducible; partial runs are reported as partial.

### Phase J — Comparative methods

Freeze the best CM variants by task before external comparisons. Run task-matched comparisons with honest conversion and lifecycle costs. Do not tune on the final confirmation corpus.

**Exit:** conclusions name the task, regime, artifact, hardware, output contract, uncertainty, and limits.

### Phase K — Integration and synthesis

1. Land only improvements that pass correctness, memory, and performance gates.
2. Update tests and architecture documentation.
3. Retire, defer, or narrow unsuccessful ideas.
4. Produce a ranked next-work backlog based on measured value and risk.

**Exit:** another developer can reproduce the accepted results and understand why each rejected path was rejected.

---

## 11. Required deliverables

Create a dated investigation directory under the existing audit tree and produce:

1. **Source and evidence ledger** — commit, dirty files, transitive hashes, environment, frozen-bundle relationships.
2. **CM architecture map** — symbols, artifacts, contracts, dataflow, caches, allocations, conversions, callers.
3. **Test coverage matrix** — subsystem × operator × boundary × representation × oracle × status.
4. **Historical result reconciliation** — confirmed, superseded, negative, incomplete, projected, or irreproducible.
5. **Baseline profile report** — stage timing, structural counters, memory, kernel and end-to-end results.
6. **Hypothesis register** — mechanism, expected benefit, workload, experiment, gate, status, evidence.
7. **Raw machine-readable results** — no aggregate-only evidence.
8. **Optimization patches or isolated prototypes** — small, reviewable, tested, and linked to causal results.
9. **Runpod proposal and frozen manifest** for any newly needed substantive campaign.
10. **Runpod execution/audit artifacts** when authorized — controller state, logs, hashes, raw results, inventory, cleanup, and billing reconciliation.
11. **Comparative benchmark report** after the CM gate passes — task-matched methods, fairness boundaries, uncertainty, failure accounting, and limits.
12. **Final decision memo** — what is fastest for each regime, what changed, what did not work, what remains unknown, and what should be done next.

The final decision table must have rows for at least:

- one-shot full output;
- compile-once full output;
- repeated fixed-support evaluation;
- repeated partial restrictions;
- related-version/incremental compilation;
- dense relation required;
- packed truth vector sufficient;
- memory-constrained explicit output;
- small support;
- medium support within guard;
- natural/corpus workload;
- application end-to-end workload.

For each row, state the best verified implementation, runner-up, setup cost, per-call cost, memory, break-even point if relevant, confidence, and disqualifying limitations.

---

## 12. Reporting language and claim discipline

Use precise conclusions such as:

- “On this frozen repeated-restriction cohort, prepared CM IR reduced median per-query execution by X after Y setup, breaking even at q=Z.”
- “Dense construction remained output-bound; the patch reduced temporary peak memory but did not improve caller-visible time.”
- “The packed-word kernel won at these sizes, but setup erased the gain for one-shot calls.”
- “No-reinflation avoided dense reconstruction but remained slower than direct packed evaluation under this output contract.”

Do not write:

- “CM is faster” without naming workload, output, lifecycle, and baseline;
- “128-vCPU pod” based only on the host logical CPU count;
- “memory limited” without quota or measured evidence;
- “all tests pass” when only a focused subset ran;
- “independent” when both outputs share the same implementation or transformation;
- “production ready” based on a scout, projection, or synthetic-only result;
- “asymptotically better” from bounded timing data.

Report null, negative, noisy, timed-out, excluded, and failed cases. Preserve enough evidence to distinguish a method failure from transport, dependency, wrapper, or resource failure.

---

## 13. Required final response

When the work reaches the current safe stopping point, report:

1. the exact source state investigated;
2. the CM architectures and execution paths found;
3. the tests and historical runs audited;
4. correctness gaps found and closed;
5. the dominant measured bottlenecks by regime;
6. optimizations implemented and their causal results;
7. ideas rejected or deferred and why;
8. Runpod runs performed, exact cost/resource/cleanup outcome, and any failed attempts;
9. comparisons with other methods, if the readiness gate was passed;
10. remaining uncertainties and the highest-value next steps;
11. all files changed and all verification commands/results;
12. `git status --short` and `git diff --stat`, without attributing unrelated dirty files to this work.

If blocked on exact cloud authorization, do all safe local architecture, source, evidence, test, manifest, and preflight work first. Then provide one exact authorization request covering the manifest hash, private-file count, wrapper hash, command, resource, storage, time, cost, cleanup, and replacement policy.

## Prompt ends
