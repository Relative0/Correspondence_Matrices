# Correspondence Matrix use-case benchmark research

**Audit date:** 2026-08-27  
**Status:** benchmark design and source investigation; no third-party corpus has been downloaded or timed by this work.

## Bottom line

The eight use cases are credible only as bounded hypotheses. The strongest first tests are configuration/product-family histories, security-policy version audits, and hardware design histories. Pure-Boolean compiler predicates are a promising bounded subset. AI guardrails, biological update rules, and regulated decision tables are conditional opportunities because native engines own important semantics. Quantum use is narrowest: classical reversible or control logic only.

A benchmark should expose the workload property that could help CM—reuse, localized edits, shared subgraphs, repeated partial contexts, or bounded residual support—but it must not cherry-pick successful cases. Run the complete eligible natural corpus, publish exclusions and failures, and report the property-stratified synthetic suite separately. A synthetic win demonstrates a mechanism; it does not establish field-level dominance.

## Audited use-case claims

| Field | Priority | Defensible pain point and possible CM role | Necessary boundary |
|---|---|---|---|
| Hardware verification/design | Tier A | Repeated equivalence, cone inspection, and revision impact may benefit from a versioned Boolean artifact that preserves shared construction. | Complement AIG/SAT/equivalence workflows; do not claim chip-wide synthesis dominance. |
| AI with hard rules | Tier B | Agent authorization and deterministic guardrails reuse permissions across many actions and contexts; CM may help restriction, version comparison, and provenance. | This is not a learned-model, prompt, planning, or probabilistic-reasoning representation. |
| Boolean regulatory biology | Tier B | Update rules recur under interventions and revisions; CM may preserve dependency and rule lineage. | Test update/intervention workflows first, not general attractor or dynamical-systems dominance. |
| Quantum-support logic | Tier C | Classical reversible functions and classical control predicates may be reused across circuit variants. | No amplitudes, phase, entanglement, noise, or general unitary evolution. |
| Compiler/program analysis | Tier A/B | Repeated pure-Boolean guards and path predicates may benefit from shared identity and partial evaluation. | Exclude or explicitly refuse integer widths, memory, poison/undefined behavior, loops, and calls until modeled exactly. |
| Security/access policy | Tier A | Long-lived policies need version diff, reachability audit, and repeated contextual decisions; CM may help as an offline analysis artifact. | Preserve policy types, entity hierarchy, combining semantics, and errors; the native engine remains the online oracle. |
| Configuration/product families | Tier A, strongest | Versioned constraints and incomplete configurations naturally combine reuse, restriction, and explainable change impact. | Compare with incremental SAT, BDD, and feature-model analyzers on their own native semantics. |
| Regulated rules/decisions | Tier B | Versioned Boolean decision-table subsets need overlap, contradiction, and change review. | Preserve hit policies, null/unknown, arithmetic, dates, and governance; leave non-Boolean calculation in the native engine. |

The machine-readable version of this audit is in [CM-USE-CASE-BENCHMARK-CATALOG.json](CM-USE-CASE-BENCHMARK-CATALOG.json).

## Cross-domain benchmark contract

1. Pin source revision, parser, translation rules, exclusions, seeds, baseline versions, hardware, and resource limits before timing.
2. Differentially validate every translated item against the native oracle. A semantic mismatch invalidates performance results for that item.
3. Separate cold construction, warm repeated evaluation, adjacent-version update, partial-context update, serialize/reload, and explanation/change-impact tasks.
4. Compare artifact-equivalent outputs. SAT witness search, BDD construction, full truth-vector extraction, and authorization latency are different jobs.
5. Report wall time, CPU time, peak resident memory, artifact size, correctness, timeouts, refusals, and never-break-even cases. Do not average failures away.
6. Report the natural corpus independently from synthetic strata. On synthetic data, sweep reuse count, edit locality, shared-subgraph fraction, fixed-context fraction, and residual live-variable count.
7. Require a predeclared dominance gate: zero semantic mismatches; a win against the best equivalent baseline on the target workflow; confirmation on natural traces; and no unacceptable memory, refusal, or preparation regression.

## Real-world sources and proposed experiments

### 1. Hardware verification and electronic design

- Use the [EPFL combinational benchmark repository](https://github.com/lsils/benchmarks) and its [published suite methodology](https://www.epfl.ch/labs/lsi/page-102566-en-html/benchmarks/). Preserve AIGER/BLIF/Verilog provenance, circuit category, output-cone membership, and original versus optimized variants.
- Oracle: ABC combinational equivalence. Baselines: AIG/ABC, CUDD/ROBDD, SAT/SMT miter, and a packed compiled evaluator.
- Run exact cone evaluation, equivalence after an equivalence-preserving rewrite, changed-output localization after a small edit, warm family reuse, and serialize/reload.
- CM wins only if the whole revision workflow improves or change attribution becomes materially better at acceptable preparation and memory cost.

### 2. AI agents with hard rules

- Replay the [AWS Cedar agentic-authorization sample](https://github.com/aws-samples/sample-cedar-agentic-ai-authorization): roles, MFA, delegation depth, agent capability, tool risk, and permit/deny results form a realistic policy trace.
- [RuleTaker](https://github.com/allenai/ruletaker) is an optional secondary logical-rule corpus, but time its logical forms separately from natural-language parsing.
- Oracle: Cedar for the policy sample. Baselines: Cedar, OPA on a documented common subset, BDD/SAT, and compiled predicates.
- The benchmark concerns deterministic guardrails and authorization only. A result says nothing about model inference, hallucination, prompt attacks, or planning quality.

### 3. Computational biology

- Start with the [Biodivine Boolean Models collection](https://github.com/sybila/biodivine-boolean-models), preserving model metadata and BNET/AEON/SBML provenance. [Cell Collective API/export tooling](https://github.com/cellcollective/ccapi) is a second source when collection terms permit.
- Oracle and baselines: AEON/BDD or another specialist Boolean-network tool, SAT-based methods, compiled update functions, and network-native analysis.
- Test batches of update-rule evaluations under knockout, overexpression, and input fixation; adjacent model revisions; dependency explanation; and state carry-forward.
- Treat attractor enumeration and long-run dynamics as a separate artifact. CM should not be called dominant merely because it evaluates individual update rules well.

### 4. Quantum-computing support logic

- Use [RevLib](https://www.revlib.org/) function specifications and REAL circuits, including declared constant inputs and garbage outputs. Use [MQT Bench](https://www.cda.cit.tum.de/mqtbench/index) only for circuits or extracted regions with a documented classical/reversible interpretation.
- Oracles/baselines: reversible-logic tooling, MQT QCEC where applicable, BDD, SAT miter, and direct truth evaluation.
- Test function/circuit agreement, adjacent reversible-circuit edits, control-predicate restriction, and artifact reuse.
- General quantum circuits are a negative-control boundary and must be rejected rather than silently Booleanized.

### 5. Compilers and program analysis

- Select pure-Boolean slices from [Alive2](https://github.com/AliveToolkit/alive2) transformations and preserve source/target LLVM IR. Extract repeated branch/path predicates from the [LLVM test suite](https://github.com/llvm/llvm-test-suite) only with program provenance.
- Oracle: Alive2/Z3. Baselines: LLVM-native simplification, Z3, e-graphs where applicable, BDD, and compiled Boolean predicates.
- Test equivalence, simplification under known facts, reuse across similar functions or revisions, and explicit refusals for unsupported integer/memory/UB semantics.

### 6. Security policy and access control

- Use [Cedar example policies](https://github.com/cedar-policy/cedar-examples) for executable policy/schema/entity/request fixtures and the [Cedar integration tests](https://github.com/cedar-policy/cedar-integration-tests) for handwritten and generated differential tests. Follow [OPA's performance guidance](https://www.openpolicyagent.org/docs/policy-performance) for any declared Cedar/Rego common subset.
- Native Cedar/OPA results are semantic oracles. Also compare a BDD/SAT encoding and indexed/compiled policy evaluation for equivalent subset tasks.
- Test authorization replay, reachable-allow analysis, version change impact, partial attribute contexts, and explanation/provenance. Time online authorization separately from offline audit.

### 7. Configuration systems and product families

- Use [FeatureIDE/FeatJAR](https://github.com/FeatureIDE/FeatureIDE) public models and semantics, [torte](https://github.com/ekuiter/torte) for curated models, Kconfig extraction, and histories, and version-pinned [Linux Kconfig](https://github.com/torvalds/linux) inputs through a validated extractor.
- Baselines: FeatJAR/SAT, incremental SAT, BDD, and a compiled constraint evaluator.
- Test validity of partial configurations, completion/counting where artifact-equivalent, explanation of conflicts, adjacent-release update, affected-feature localization, and repeated interactive contexts.
- This is the best first domain because the native workload already contains the version families, partial assignments, and long-lived shared constraints that form the CM hypothesis.

### 8. Regulated rule and decision systems

- Use the [DMN Technology Compatibility Kit](https://github.com/dmn-tck/tck) serialized models, inputs, and expected outputs for a declared Boolean decision-table subset. Use [OpenFisca country packages](https://openfisca.org/en/packages/) to identify bounded Boolean eligibility subgraphs while keeping arithmetic microsimulation in OpenFisca.
- Oracles/baselines: conforming DMN engine, OpenFisca, indexed decision tables, BDD/SAT for the exact Boolean subset, and compiled predicates.
- Test conformance, overlaps, gaps, shadowed rules, local version changes, repeated cases, and audit explanations. Unsupported null/unknown, date, arithmetic, or hit-policy semantics must refuse or remain native.

## Reusable synthetic demonstration suite

Run `python cm_use_case_scenario_generator.py` from this directory. It creates deterministic JSONL suites under `synthetic/`, a manifest, and SHA-256 checksums. Each case contains:

- a base Boolean DAG;
- an equivalent double-negation rewrite for equivalence and structural-change tests;
- a localized behavior-changing revision;
- all-free and progressively fixed contexts;
- one or more roots, workflow metadata, and exact packed truth bits for every version/context/root.

The files exercise the same reproducible mechanism across all eight fields while keeping field-specific workflow labels and root counts. They are demonstrations, not substitutes for natural corpora. The generator records its seed and truth-bit convention, can be rerun without network access, and validates equivalent/changed expectations before writing.

Use [BENCHMARK-RUN-MANIFEST-TEMPLATE.json](BENCHMARK-RUN-MANIFEST-TEMPLATE.json) to record a real run. A publishable result should bundle the filled manifest, source/license notes, translation audit, raw timings, correctness outcomes, failures/refusals, environment capture, and output checksums.

## Recommended execution order

1. Configuration history pilot, because it best matches the stated reuse-and-context hypothesis.
2. Cedar policy version/audit pilot, with strict differential semantics.
3. EPFL hardware revision/cone pilot, extending the project's existing adjacency evidence into an actual workflow.
4. Pure-Boolean compiler slice.
5. AI guardrail, biology update-rule, and regulated decision-table pilots after their translators pass native-oracle conformance.
6. Quantum classical-boundary pilot only if a specific reversible/control workflow owner exists.

The result sought is not “a dataset where CM wins.” It is a reproducible map of where CM wins, loses, refuses, or never repays construction—connected to measurable workload properties and checked against the best method that produces the same artifact.
