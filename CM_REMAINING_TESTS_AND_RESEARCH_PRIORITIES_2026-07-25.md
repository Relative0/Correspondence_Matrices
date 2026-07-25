# Correspondence Matrices: Tested, Still Untested, and Highest-Value Next Tests

Date: 2026-07-25  
Source reviewed: `Correspondence-Matrices-A-Structural-Layer-for-Boolean-Computation (13).pdf` (57 pages, created 2026-07-25)  
Project reviewed: current working tree in `CM_Computation`

## Executive conclusion

The paper's central implementation and explicit-output correctness claims have substantial project evidence. The current test suite passes (`194 passed in 60.52s` on 2026-07-25), and the project contains local and remote CM/BitSet campaigns with zero reported output mismatches, prepared same-expression tests, live-support/engine-policy tests, native-CUDD construction evidence, and provenance/timing audits.

The structural-layer thesis itself is **not yet decisively validated**. The true remaining research questions are:

1. Does CM provide an end-to-end advantage on real, independently sourced, structured workloads?
2. Can CM-native transformations produce useful results more efficiently than strong task-matched baselines?
3. Can a canonical CM representation/equivalence procedure be precisely defined, implemented, and independently verified?
4. Can cross-expression and partial-context reuse beat strong incremental baselines under fair total-cost accounting?
5. Can an automatic router make reliable choices across CM, packed BitSet, CUDD/ROBDD, SAT, Espresso, and symbolic systems?
6. How does CM behave on controlled BDD-friendly, BDD-hard, order-sensitive, high-live-support, and low-reuse families?
7. Do the reported effects replicate with formula-clustered statistics, frozen artifacts, and fully recorded environments?

Three items presented in the PDF as high-priority CM-value experiments have already received meaningful preliminary testing:

- related-expression family reuse;
- repeated partial contexts;
- operator difference/quotient and other native transformations.

They should **not** be restarted as if no evidence exists. Their current results are mixed: CM reuse improves CM's own uncached path in selected regimes, but does not beat BitSet or ROBDD/CUDD on the tested synthetic workloads; quotienting is implemented and correct as a distinct feature artifact, but is not a demonstrated semantic-delta speed win. The next version of each test should use representative real workloads, stronger incremental competitors, and end-to-end cost accounting.

## How this assessment was made

Evidence was classified into four levels:

1. **Automated software validation** - unit/integration tests of behavior and schema.
2. **Empirical benchmark evidence** - raw/summary artifacts and reports for a defined synthetic workload.
3. **Partial research evidence** - an implementation or smoke/small campaign exists, but generality, baseline strength, environment matching, or statistical power remains inadequate.
4. **Unvalidated research claim** - no project evidence establishes practical value or the claimed property.

This distinction matters. For example, tests can establish that a quotient function implements its definition; they cannot establish that quotienting is useful in hardware verification. Likewise, output equality is not evidence of canonical CM structural equivalence.

The PDF was checked both by text extraction and by rendering and visually inspecting its final experiment/provenance pages. Key paper locations are pages 4-6, 10-12, 22-31, 36-57, especially the priority list on page 55 and the three CM-value experiments on page 56.

## What has already been tested

| Area | Status | Evidence and result | Retest guidance |
|---|---|---|---|
| Core software correctness | **Tested** | Current run: `python -m pytest -q` -> **194 passed**. Coverage includes expression evaluation, golden cases, backends, conversion, caches, engine policy, no-reinflation, partial/family modes, equivalence schemas, timing/provenance, CUDD selection, CLI, and reporting. | Keep as a regression gate. Do not mistake it for research validation. |
| CM vs packed BitSet output correctness | **Tested within stated support/corpora** | Audit V4 reports 294 executed remote pairs plus seven intentional guard skips and zero mismatches; local paired campaigns also report zero mismatches. | Do not rerun identical formulas merely to accumulate counts. Add property-based/adversarial generators, independent oracles, and new workload classes. |
| Reduced-live large ambient `n` | **Tested for reduced support** | Multi-seed and remote campaigns cover ambient sizes through 32 when semantic/output support remains bounded; sampled assignment checks report zero mismatches. | Do not describe this as arbitrary 32-live-variable scalability. Future testing should stratify by actual semantic support and memory use. |
| Live-support analysis and engine policy | **Tested as implemented policy** | Dedicated policy, defaults-scope, partial/family symmetry, provenance, and guard tests exist. V4 audited flat/words/recursive selection. | Retain regression coverage. The unresolved item is learned/automatic multi-backend routing, not the current threshold policy. |
| Prepared same-expression evaluation | **Tested** | V4 reports 378 local paired observations over 42 formulas, zero mismatches, and about 1.31-1.82x improvement at small support versus legacy binding. At support 12-16 the advantage is around parity. | Do not repeat the same small-support campaign. Extend to realistic query streams and include preparation, cache memory, invalidation, and cold/warm costs. |
| Related-expression family reuse | **Partially tested** | `CM_experiment_A_related_families_report.md` implements cross-expression subtree-cache reuse. Shared-block cases improved cached CM by about 1.18-1.30x, with a best reported 1.39x against uncached CM. Composition-mix results were mixed. BitSet remained roughly 11.7-46.3x faster in the strongest cited exact-output cases. | Do not rerun only the existing synthetic family sweep. Test real edit/version/query families; compare with hash-consed DAGs, e-graphs, incremental BDD managers, and compiler memoization. |
| Repeated partial contexts | **Partially tested** | `CM_experiment_B_partial_contexts_report.md` reports cached-CM speedups of about 2.05-4.39x over uncached CM and up to 6.24x in one fixed-fraction sweep. BitSet and ROBDD restriction remained faster at `n <= 16`. | Preserve this as preliminary evidence. Next test must use real context traces and compare against CUDD restrict/cofactor, incremental SAT/assumptions, and task-specific incremental evaluators. |
| CM quotient/difference and transformations | **Functionality tested; practical value unproven** | `CM_experiment_C_operator_difference_quotient_report.md` validates directional quotienting, transpose, complement, rotations, operand swap, expression negation, and operand-negation transforms. At `n=16`, BitSet was faster for semantic delta; CM quotient computes a different artifact and is not a semantic-XOR speed win. | Do not benchmark unlike artifacts as a speed contest. First define a domain task whose required output is the CM feature artifact, then compare complete workflows. |
| Output equivalence | **Tested** | CM and BitSet compare complete packed outputs in bounded-support campaigns; `ROBDD_CM_equivalence_report.md` tests ROBDD canonical equality after construction. | Continue as an oracle/regression check. Do not label CM output comparison as canonical structural equivalence. |
| Native CUDD construction | **Tested for small/easy synthetic formulas** | V4 reports native `dd.cudd` identity on 49/49 formulas and retained best-of-10 build components. Older matched runs also measured build plus truth-table extraction at `n=16`. | Keep the data, but do not generalize it to hard BDD families or a complete downstream comparison. |
| CUDD packed extraction | **Previously tested, but final V4 same-corpus campaign incomplete** | Earlier Docker/RunPod reports measured build+truth-table extraction, including about 0.364 s at `n=16`. The PDF correctly says final-pod query/extraction was incomplete, so the older number is not a final same-environment V4 result. | Do not erase the older evidence. Run one frozen same-environment campaign with build, order search, query, cofactor, equivalence, model count, and extraction reported separately. |
| Formula/corpus and timing provenance | **Substantially implemented and tested** | V4 added immutable corpus hashes, typed timing boundaries, paired aggregation checks, CUDD identity checks, and generated chart-data drift tests. | Complete publication metadata and archive a frozen revision; continue machine-validating every public figure. |
| Parallel evaluator | **Tested in a limited stress grid** | The parallel stress report found intermittent activation and no consistent speedup; overhead usually dominated. | Low priority unless a new kernel, larger live-support regime, or non-Python parallel backend changes the cost model. |

## What still truly needs to be tested

### Priority 1 - Real, independently sourced workloads

**Status: untested.** The PDF states that there are zero validated real-domain datasets. No repository evidence found changes that conclusion.

At least three domains should be selected before making a general structural-layer claim:

- hardware verification/EDA: equivalence, cofactors, cone-of-influence updates, engineering changes, and repeated property checks on circuit/netlist-derived formulas;
- configuration and policy systems: repeated access-control, feature-model, or policy queries under changing assignments and rules;
- compiler/program analysis: path conditions, dataflow predicates, or symbolic execution states with repeated restriction and related-expression evolution.

For each workload, measure the actual requested result, not merely a common intermediate. Include parsing, normalization, construction/preparation, query execution, memory, cache growth, and amortization break-even. Use public datasets and publish workload identifiers and transformation scripts.

### Priority 2 - Canonical CM representation and equivalence

**Status: unimplemented and untested.** Current CM equivalence is output equality. Structural hashes are syntactic diagnostics, not semantic canonical identifiers.

A valid test program requires:

1. a precise normalization convention for ordered variable basis, dimensions, reductions, and permitted transformations;
2. a canonicalization algorithm or a proof that a proposed normal form is canonical under those conventions;
3. exhaustive validation for small Boolean functions;
4. property-based tests over equivalent rewrites, basis permutations, near misses, and adversarial structures;
5. independent comparison with complete truth tables and same-manager ROBDD equality;
6. collision and determinism tests for any serialized canonical identifier;
7. complexity, memory, and comparison-time measurements including canonicalization cost.

This is conceptually high value, but it must first answer whether the canonical artifact offers anything not already supplied by ROBDDs, AIG normalization, Boolean-network rewriting, or canonical truth representations.

### Priority 3 - CM-native transformation value on a real task

**Status: operators implemented; end-to-end utility untested.**

The right experiment is not “CM quotient versus XOR,” because those outputs have different meanings. Choose a task in which difference, quotient, decomposition, projection, conditioning, reconstruction, or measurement is itself required. Specify:

- the formal output and correctness oracle;
- why that output solves a real downstream problem;
- comparable algorithms over BDDs/AIGs/truth tables/SAT or domain-native structures;
- total time and peak/resident memory;
- whether the CM result improves a downstream decision, proof, optimization, or diagnosis.

This directly tests the paper's distinctive formal contribution.

### Priority 4 - Cross-expression reuse against strong incremental systems

**Status: preliminary synthetic evidence exists; comparative thesis remains unproven.**

The next campaign should use families derived from real edits, shared modules, compiler passes, circuit revisions, or policy versions. Compare:

- current CM structural-hash compiled-IR cache;
- uncached CM;
- packed recomputation;
- CUDD shared-manager/restrict workflows;
- AIG structural hashing and rewriting;
- e-graph or hash-consed DAG reuse where appropriate;
- incremental SAT when the task is feasibility rather than full output.

Report cache hit quality, lookup overhead, memory retention, eviction behavior, invalidation correctness, preparation cost, and the number of queries required to break even.

### Priority 5 - Repeated partial contexts with task-matched baselines

**Status: preliminary synthetic evidence exists; CM lost to BitSet and ROBDD restriction at tested sizes.**

Use recorded or generated traces reflecting a domain's actual context overlap and change distribution. Test sliding, random, locality-heavy, adversarial low-overlap, and phase-changing traces. The key result should be a break-even surface over:

- original support;
- remaining live support;
- number of contexts;
- context overlap;
- output type;
- cache budget;
- cold versus steady state.

Include CUDD cofactor/restrict, incremental SAT assumptions, and any domain-native incremental method.

### Priority 6 - BDD-friendly, BDD-hard, and order-sensitive families

**Status: not completed.** The paper explicitly warns that the 49-formula CUDD corpus is not adversarial or BDD-hard and that ten seeded orders are not exhaustive.

Use standard parameterized families with known behavior, including easy/reducible, parity-like, multiplexer, arithmetic/circuit-derived, and order-sensitive cases. For CUDD report:

- fixed natural/domain order;
- explicitly stated alternative orders;
- best-of-`k` result and full search cost;
- dynamic-reordering method and total cost;
- node count, peak memory, build time, and each downstream query separately.

For CM and BitSet, stratify by true semantic support and required artifact. This test maps representation boundaries; it should not force unlike artifacts into one leaderboard.

### Priority 7 - Automatic multi-backend routing and cost model

**Status: proposed only.** Current engine selection is an implemented CM/BitSet policy, not automatic routing across the broader ecosystem.

Build and test the router only after collecting workload data for distinct deliverables. The router should predict both feasibility and total cost for packed evaluation, canonical equivalence, cofactor/restriction, minimization, satisfiability, and symbolic manipulation. Evaluate with held-out workloads using:

- regret versus the best feasible backend;
- catastrophic-choice rate, including out-of-memory/timeouts;
- routing overhead;
- calibration and confidence;
- robustness under platform shift;
- ablation against simple threshold policies.

SAT, Espresso, and SymPy should only enter tasks they are designed to solve.

### Priority 8 - Same-environment CUDD downstream campaign

**Status: partly tested historically; incomplete in the final V4 environment.**

Use the frozen V4 corpus plus BDD-hard extensions in one environment. Separate:

- parse/translation;
- manager setup and variable declaration;
- fixed-order construction;
- ordering/reordering search;
- equivalence;
- cofactor/restrict;
- satisfiability/model counting if relevant;
- packed extraction;
- cleanup and peak memory.

This closes a comparability gap. It is important for publication integrity, but by itself it is less likely to establish novel CM value than real workloads or CM-native transformation tests.

### Priority 9 - Formula-clustered uncertainty, replication, and generalization

**Status: limited audit/bootstrap work exists; definitive replication is still needed.**

Rounds from one formula are repeated measurements, not independent formulas. Future inference should use formula as the sampling unit, paired per-formula effects, hierarchical or cluster bootstrap intervals, and enough formulas per stratum to estimate heterogeneity. Pre-register primary outcomes and success/failure thresholds. Replicate on at least two materially different machines and report platform interaction rather than pooling raw timings.

### Priority 10 - Explicit high-live-support scaling and resource limits

**Status: bounded tests exist through support 16 and selected beyond-guard cases; general scaling above 16 remains unproven.**

Run controlled live-support sweeps independently of ambient `n`, with memory telemetry and fail-closed limits. Include low-reuse and anti-reduction expressions. The objective is to locate time/memory feasibility surfaces, not to imply polynomial scaling for explicit `2^k` outputs.

### Priority 11 - Robustness and independent verification

**Status: project-internal checks are strong; independent reproduction is absent.**

Add:

- property-based and exhaustive-small-function tests for all CM transforms;
- mutation testing of correctness-critical paths;
- differential testing with at least two independent oracles;
- serialized-corpus replay from a clean checkout/container;
- independent implementation or external replication of the most important result;
- fuzzing of parser, basis order, constants, degenerate support, and cache invalidation.

## Highest-value tests for the broader world of computation

These are ranked by potential contribution, not by ease.

### 1. Incremental hardware-change verification benchmark

Use public sequential versions of circuits or netlists. Ask whether CM can reuse structure across engineering changes to accelerate equivalence, cone-local cofactors, failure localization, or changed-output characterization. Compare against CUDD, AIG-based flows, SAT sweeping/incremental SAT, and packed simulation.

**Why it matters:** incremental verification is expensive, structure-rich, and already has strong baselines. A reproducible win or a clearly useful new diagnostic artifact would be meaningful beyond this project.

### 2. Canonical-CM theorem plus exhaustive small-function validation

Define a canonical CM normal form, prove its invariants, exhaustively enumerate small Boolean functions/bases, and compare canonicalization cost and artifact size with ROBDDs and other canonical forms.

**Why it matters:** this could turn CM from an implementation architecture into a precisely comparable representation. A negative result would also be valuable by locating where uniqueness depends on arbitrary basis/order choices.

### 3. Real incremental policy/configuration workload

Benchmark thousands of related policy versions and assignment contexts, including explanation/difference queries rather than only Boolean outputs. Compare CM reuse with BDD restriction, incremental SAT, and direct compiled evaluation.

**Why it matters:** it combines the two best preliminary CM signals - related-expression reuse and partial contexts - in a domain with natural shared structure and repeated queries.

### 4. Operator-calculus task benchmark

Choose a real problem where CM quotient/decomposition/measurement produces an actionable artifact, such as change localization, operator-family classification, decomposition selection, or explanation generation. Validate the result with a domain oracle and compare complete workflows.

**Why it matters:** this is the cleanest test of what may be unique about CM. Raw packed-output speed is already well served by BitSet, and canonical graph equivalence is already well served by BDDs.

### 5. Representation-boundary atlas

Publish a large, reproducible study crossing semantic support, structural sharing, formula family, BDD order sensitivity, query type, output artifact, cache budget, and machine. Measure CM, BitSet, CUDD/ROBDD, AIG, SAT, and task-specific methods only on appropriate tasks.

**Why it matters:** even without a universal CM win, an honest map of representation and workload boundaries would be a useful contribution to compiler and Boolean-tool selection.

## Tests that should not simply be repeated

- The 194-test suite should remain a regression gate; raising the count without new failure modes adds little research evidence.
- Existing synthetic CM/BitSet equality campaigns should not be rerun unchanged merely to accumulate more zero-mismatch pairs.
- The small synthetic related-family and partial-context campaigns should not be repeated without new real traces or stronger baselines.
- CM quotient should not again be compared directly to semantic XOR as if the artifacts were equivalent.
- CUDD symbolic build time should not be mixed with CM/BitSet packed-output time.
- Ambient-`n` sweeps with reduced live support should not be used as evidence for arbitrary high-live-support scalability.
- More random timing rounds on the same small formula set should not be treated as more independent samples.
- Native Windows `dd.autoref` should not be labeled or used as a performance proxy for native CUDD.

## Publication-readiness work that is not itself a scientific test

The PDF's provenance checklist remains important:

- image/container digest;
- CPU model, quota, and isolation;
- RAM/cgroup limit;
- OS/kernel;
- Python and dependency versions;
- thread/affinity settings;
- exact repository revision or archived source bundle;
- exact benchmark command/configuration;
- frozen result-artifact identifier and hashes.

The project has improved corpus and timing provenance substantially, but the current working tree is dirty and contains uncommitted/untracked V4 code and artifacts. A publication snapshot should be made from an intentionally frozen, clean, archived revision. This report did not commit, push, deploy, or alter existing project files.

## Recommended execution order

1. Freeze and archive the current evidence, commands, environments, and raw artifacts.
2. Select one real domain and define its required outputs and strongest task-matched baselines.
3. Run the real related-family/partial-context workload with total-cost and memory accounting.
4. Run a CM-native transformation/decomposition task on the same or a second domain.
5. In parallel with research design, formalize canonical CM equivalence before implementing a benchmark for it.
6. Add controlled BDD-hard/order-sensitive and high-live-support boundary suites.
7. Complete the same-environment CUDD downstream campaign.
8. Collect enough diverse workloads to train and test an automatic backend router.
9. Seek an independent reproduction of the strongest positive and strongest negative result.

## Bottom line

The project has already done enough testing to support a conservative claim: CM is a functioning structural IR/evaluation layer with correct bounded explicit-output paths, live-support-aware execution, scoped preparation/caching, and preliminary structural-reuse and transformation capabilities.

It has **not** yet shown that CM changes the cost or capability frontier on representative real computation. The highest-value next work is therefore not another generic CM-versus-BitSet microbenchmark. It is a real structured incremental workload, paired with strong task-matched baselines, followed by a precise canonical-equivalence program and a real use case for CM-native operator calculus.

## Project evidence consulted

- `CM_AUDIT_V4_2026-07-24.md`
- `CM_AUDIT_V4_FIX_IMPLEMENTATION_AND_RUNPOD_2026-07-24.md`
- `CM_SESSION_2026-07-24_AUDIT_V4_STATE_AND_FINDINGS.md`
- `CM_experiment_A_related_families_report.md`
- `CM_experiment_B_partial_contexts_report.md`
- `CM_experiment_C_operator_difference_quotient_report.md`
- `ROBDD_CM_equivalence_report.md`
- `CUDD_ROBDD_extraction_report.md`
- `CM_final_robustness_report.md`
- `CM_n20_feasibility_report.md`
- `CM_parallel_stress_test_report.md`
- `deliverables_n22_24/CM_FABLE_BENCHMARKS_2026-07-21.md`
- current `tests/`, implementation modules, benchmark artifacts, and repository status
