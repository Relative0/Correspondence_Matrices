# CM use cases and benchmark opportunities

[Research library](../README.md) · Generated reading edition, 2026-08-28.

Derived from the authored explainer and its saved evidence. Charts and interactive controls remain in the downloaded HTML.

Latest follow-up: [verified Runpod memory smoke](RUNPOD-MEMORY-SMOKE.md). This does not establish general CM dominance or production estimator acceptance.

## Application hypotheses

Where Correspondence Matrices might create distinctive value

CM is most interesting when a Boolean function is not a disposable answer but a long-lived object: it must retain useful structure, survive across sessions or versions, accept transformations, and answer related questions repeatedly. The cases below are reasoned application hypotheses, not claims of deployed advantage.

### Evidence boundary

Hardware/formal-verification expressions and bounded real feature-model slices have been tested. Neither establishes deployed-workflow advantage, and the feature-model performance comparisons retain documented measurement gaps. Every other field below remains a candidate whose CM-specific benefit needs a real trace and a direct incumbent comparison.

### Advantages

#### Retain structure, not only an answer

A flat truth vector answers what the function does. A CM can also retain operator and subexpression organization, so a later tool can inspect, transform, compare, or attribute parts of the computation instead of reconstructing them from output alone.

#### Reuse a compiled identity

Expression keys, serialization, process-local compiled caching, and operator transforms are implemented. That creates a route to reuse across evaluations and related analyses, although durable production value has not yet been demonstrated.

#### Change the context without discarding the object

Restrictions and partial evaluation can keep the stable part of a model while inputs, policies, interventions, or versions change. Synthetic context tests improved over uncached CM but did not establish an advantage over incumbent engines.

#### Keep exactness and provenance together

Where complete explicit output is feasible, CM can couple an exact result with the structure that produced it. The output still grows exponentially with semantic support, so this is a bounded capability rather than an unlimited replacement for SAT or decision diagrams.

### Hardware verification and electronic design

#### Status

Measured adjacency

#### Problem

Engineers repeatedly prove that optimized circuits preserve behavior, inspect logic cones, and assess the effect of design revisions.

#### How CMs could help

A reusable expression identity plus retained operator structure could link equivalent outputs back to the subcircuits that produced them, support structural difference between revisions, and avoid rebuilding unchanged logic for every related check.

#### Information retained

The function, its semantic support, operator composition, reusable subexpressions, and version lineage can remain attached to one artifact rather than being reduced to a one-off answer vector.

#### Incumbents and alternatives

AIGs, ROBDD/CUDD, SAT/SMT, equivalence checkers, and synthesis tools already dominate this field. CM would need to complement them at an artifact or workflow boundary, not merely duplicate their core query.

#### Evidence still needed

Replay a real design history and show lower total workflow cost or clearer change attribution against the incumbent representation.

### Artificial intelligence with hard rules

#### Status

High-value hypothesis

#### Problem

Agents and neuro-symbolic systems may reuse the same safety rules, permissions, or consistency constraints across many proposed actions and rapidly changing contexts.

#### How CMs could help

CM could compile the hard-rule layer once, retain which predicates and operators produced a decision, restrict it under each new context, and compare rule-set versions without treating every check as a fresh expression.

#### Information retained

Rule identity, composition, support, transformations, and decision provenance can survive alongside exact Boolean behavior; the learned model itself is not represented by the CM.

#### Incumbents and alternatives

SAT/SMT, policy engines, Datalog, knowledge-graph reasoners, and ordinary compiled predicates may be better for existence queries or mature production integration.

#### Evidence still needed

Use a real guardrail or agent-policy trace to measure reuse, update frequency, explanation needs, and end-to-end cost against the deployed rules engine.

### Computational biology and Boolean regulatory networks

#### Status

Research hypothesis

#### Problem

Boolean gene and signaling networks are repeatedly evaluated under knockouts, interventions, initial conditions, and model revisions while researchers track stable states and causal structure.

#### How CMs could help

A structured, reusable artifact could preserve each update rule and its dependencies, reuse unchanged network regions, and apply restrictions for interventions without flattening away the regulatory composition.

#### Information retained

Update-function lineage, shared regulatory modules, intervention context, and exact bounded behavior can stay connected, which may help compare model versions and explain changed attractors.

#### Incumbents and alternatives

BDD-based attractor tools, SAT methods, graph algorithms, and specialized Boolean-network packages already exploit domain structure and may scale much further.

#### Evidence still needed

Benchmark real published networks on attractor or intervention workflows, including memory and repeated-query cost, against specialized BDD/SAT tools.

### Quantum-computing support logic

#### Status

Narrow research hypothesis

#### Problem

Quantum workflows contain classical Boolean subproblems: reversible-oracle logic, circuit-control conditions, syndrome predicates, and equivalence checks on compiled Boolean components.

#### How CMs could help

For those Boolean boundaries, CM could retain the construction of a predicate or reversible logic component, reuse compiled substructure across circuit revisions, and expose structural differences that a flat classical truth table loses.

#### Information retained

Classical predicate structure and provenance may be preserved. Quantum amplitudes, phase, entanglement, and general unitary evolution are outside the CM claim.

#### Incumbents and alternatives

Quantum decision diagrams, ZX-calculus tools, SAT/SMT, reversible-logic synthesis, and circuit-specific equivalence systems target the genuinely quantum or reversible parts directly.

#### Evidence still needed

Choose one Boolean boundary in a real quantum toolchain and compare correctness, artifact reuse, change analysis, and total cost with the native representation.

### Compilers and program analysis

#### Status

High-value hypothesis

#### Problem

Compilers revisit path conditions, guards, and optimization predicates as program context evolves across passes and source revisions.

#### How CMs could help

CM could retain predicate construction, share repeated subexpressions, partially evaluate under known facts, and carry stable identity through transformations or incremental builds.

#### Information retained

The relationship between a result, its source predicate, its support, and the transformations already applied need not be discarded after one evaluation.

#### Incumbents and alternatives

SSA-based dataflow, e-graphs, BDDs, SAT/SMT, abstract interpretation, and compiler-native memoization already solve overlapping pieces.

#### Evidence still needed

Instrument a real compiler or analyzer and test whether repeated predicates and context changes repay CM preparation against its native incremental machinery.

### Security policy and access control

#### Status

High-value hypothesis

#### Problem

Long-lived policies are evaluated repeatedly, revised frequently, and audited for accidental reachability, privilege escalation, and change impact.

#### How CMs could help

A CM artifact could keep policy clauses and composition attached to exact behavior, reuse unchanged structure, restrict under user or environment attributes, and compare versions structurally.

#### Information retained

Rule origin, logical composition, support, evaluation context, and version identity can remain available for audit rather than collapsing into a bare allow/deny result.

#### Incumbents and alternatives

Policy decision points, Datalog, BDDs, SMT, and dedicated reachability analyzers have mature semantics and integrations.

#### Evidence still needed

Replay a scrubbed policy history with realistic queries and demonstrate better auditability or total repeated-query cost without weakening policy semantics.

### Configuration systems and product families

#### Status

Bounded real-model evidence; performance provisional

#### Problem

Feature models and configuration rules persist across releases while teams test many related contexts and ask what a changed flag can affect.

#### How CMs could help

Persistent expression identity, serialization, structural difference, and partial evaluation align with a workload made of related rule versions and many incomplete assignments.

#### Information retained

Feature dependencies, shared constraints, known context, and version-to-version changes can be carried together instead of rebuilding a flat evaluator for every release.

#### Incumbents and alternatives

SAT, BDDs, constraint-programming systems, and feature-model analyzers are strong, specialized baselines.

#### Evidence still needed

Repair the documented measurement gaps, then require matched reuse, change-impact or total-workflow gains against the existing analyzer on representative histories and caller traces.

### Regulated rule and decision systems

#### Status

Auditability hypothesis

#### Problem

Eligibility, pricing, triage, and compliance systems need repeatable decisions, controlled rule changes, contradiction checks, and explanations tied to the exact rule version.

#### How CMs could help

CM could serve as a versioned structural artifact whose exact Boolean behavior, rule composition, transformations, and reuse history remain available to evaluation and audit tools.

#### Information retained

The decision function and how it was assembled can stay together, reducing the information loss that occurs when a rule set becomes only generated executable code or isolated outcomes.

#### Incumbents and alternatives

Decision tables, business-rule engines, DMN tooling, SAT/SMT, and conventional audit logs may already provide the required governance more simply.

#### Evidence still needed

Test a real governed rule lifecycle and compare traceability, change review, contradiction detection, and operating cost with the incumbent system.

### When to consider CMs

#### Good fit

The same Boolean structure is evaluated, restricted, transformed, or compared many times.

Operator or subexpression lineage matters after the first answer is produced.

Version differences and partial contexts are first-class workflow objects.

The semantic support is bounded enough for the required explicit artifact, or the CM is used as a structural layer rather than forced to enumerate everything.

#### Poor fit

The job is a one-off complete evaluation where BitSet's low setup cost dominates.

The only question is whether one satisfying assignment exists; SAT is built for that.

A canonical symbolic graph under a fixed variable order is the required artifact; ROBDD/CUDD already supplies it.

The workload needs general quantum-state, numeric, probabilistic, or continuous computation rather than a Boolean structural layer.

## Datasets and benchmark design

### Schema version

cm-use-case-benchmark-catalog/v1

### As of

2026-08-27

### Purpose

Audited, field-specific benchmark candidates for testing whether a reusable CM structural artifact creates value beyond a one-off Boolean answer.

### Interpretation rule

A result on a CM-shaped synthetic stress suite is a mechanism demonstration, not domain dominance. A domain claim requires a preregistered confirmatory result on the natural corpus with the best artifact-equivalent incumbent.

### Fairness protocol

Freeze dataset revisions, parsers, translations, exclusions, seeds, and resource limits before timing.

Run every eligible natural-corpus item; do not retain only formulas on which CM is fast.

Separate cold construction, warm evaluation, version update, partial-context update, serialization, and explanation or change-impact tasks.

Compare equivalent outputs and capabilities. SAT witness search, BDD graph construction, explicit truth-vector generation, and policy authorization are different artifacts.

Publish failures, refusals, timeouts, memory peaks, and never-break-even cases alongside successful timings.

Label synthetic stress results separately and sweep the property intended to help CM: reuse, edit locality, shared-subgraph fraction, context delta, and residual semantic support.

### Priority summary

#### Item 1

##### Tier

Tier A — test first

##### Fields

Configuration/product families; security-policy version audit; hardware design histories

##### Reason

These naturally combine long-lived Boolean structure, related versions or contexts, exactness, and change-impact questions.

#### Item 2

##### Tier

Tier A/B — bounded subset

##### Fields

Compiler and program-analysis predicates

##### Reason

The fit is strong for pure Boolean i1/path-condition families, but weak for general integer, memory, undefined-behavior, or interprocedural semantics.

#### Item 3

##### Tier

Tier B — conditional

##### Fields

AI-agent hard guardrails; biological update rules; regulated Boolean decision tables

##### Reason

There is a credible reusable-rule artifact, but mature domain engines already provide semantics CM must preserve exactly.

#### Item 4

##### Tier

Tier C — narrow research

##### Fields

Classical reversible and control logic in quantum toolchains

##### Reason

CM may help only at a Boolean boundary; it does not represent amplitudes, phase, entanglement, or general unitary evolution.

### Entries

#### Hardware verification and electronic design

##### Priority

Tier A — test first

##### Audit verdict

Sound and comparatively strong after narrowing the claim to repeated cone/version workflows. CM is not being proposed as a replacement for industrial equivalence checking or synthesis.

##### Pain point

Design teams repeatedly rebuild and compare related logic cones after synthesis and optimization passes, while needing exact equivalence, localized change impact, and traceability from output behavior back to changed structure.

##### Proposed CM role

Use CM as a versioned intermediate artifact for bounded cones: retain operator/subexpression structure, reuse unchanged compiled regions, restrict under partial inputs, and report structural and behavioral deltas between revisions.

##### Scope correction

Do not claim chip-level scalability, synthesis-quality dominance, or an advantage on one-off whole-netlist evaluation. Complete explicit output remains bounded by semantic support.

##### Real datasets

###### EPFL Combinational Benchmark Suite

###### Url

https://github.com/lsils/benchmarks

###### Use

Use original and best-result AIGER/BLIF/Verilog implementations as real circuit and related-implementation inputs; extract bounded output cones and retain circuit/fan-in metadata.

###### License note

Repository reports an MIT license; pin a commit and preserve circuit attribution.

###### EPFL suite description and methodology

###### Url

https://www.epfl.ch/labs/lsi/page-102566-en-html/benchmarks/

###### Use

Use the published circuit categories and ABC equivalence workflow to stratify arithmetic versus control cones and document how variants were produced.

###### License note

Methodology/source page; dataset license is governed by the repository.

##### Synthetic scenario

Start from each real AIG cone, apply seeded equivalence-preserving ABC rewrite/refactor/resubstitution sequences, then inject localized behavior-changing edits. Sweep shared-subgraph fraction, edit radius, query reuse, and fixed-input fraction while retaining every seed.

##### Baselines

ABC/AIG rewriting and equivalence

ROBDD/CUDD

SAT or SMT equivalence

packed BitSet or compiled evaluator

##### Tasks

cold cone construction

warm repeated exact evaluation

equivalent-rewrite detection

localized revision impact

partial-input restriction

serialize/reload and query

##### What would establish a useful advantage

Exact outputs and equivalence labels must match; on the natural version/cone trace, CM total workflow time must beat the fastest artifact-equivalent baseline with no memory/refusal regression, or provide a measured change-attribution capability the baseline lacks at acceptable cost.

#### AI-agent authorization and hard guardrails

##### Priority

Tier B — conditional

##### Audit verdict

The original AI wording was too broad. The defensible use case is the deterministic Boolean policy layer around an agent, not learned inference, planning, or natural-language reasoning itself.

##### Pain point

Agent systems repeatedly decide whether a principal, delegated agent, action, tool, resource, and context combination is allowed while policies, delegation depth, and tool inventories evolve. Operators also need a reviewable explanation of what changed.

##### Proposed CM role

Compile a bounded Boolean projection of the hard-guardrail layer, retain policy/subexpression identity across revisions, reuse it over request streams, and perform offline change-impact or counterfactual analysis. Keep the native policy engine as the semantic authority.

##### Scope correction

Do not represent model weights, prompts, probabilistic confidence, open-ended planning, or the full typed semantics of Cedar/Rego as Boolean variables without an explicit translation contract.

##### Real datasets

###### AWS sample agentic AI delegation authorization

###### Url

https://github.com/aws-samples/sample-cedar-agentic-ai-authorization

###### Use

Replay the documented permit/deny delegation scenarios and derive versioned tool-policy request traces, including user role, MFA, delegation depth, agent capability, and tool risk.

###### License note

Sample/reference implementation; pin the repository revision and inspect its license before redistribution.

###### AllenAI RuleTaker

###### Url

https://github.com/allenai/ruletaker

###### Use

Optional secondary corpus for repeated deterministic rule-theory queries after using the repository's logical forms rather than timing natural-language parsing.

###### License note

Apache-2.0 repository; retain dataset attribution.

##### Synthetic scenario

Generate seeded agent/tool/resource graphs with layered permit, forbid, delegation, tenant, time, and approval predicates. Produce request streams plus localized policy versions, preserving expected allow/deny outcomes and policy-clause provenance.

##### Baselines

native Cedar authorizer

OPA/Rego for a documented translatable subset

BDD or SAT policy analysis

ordinary compiled predicates with memoization

##### Tasks

request-stream authorization

warm policy reuse

policy-version impact

counterfactual context restriction

decision provenance

serialize/reload

##### What would establish a useful advantage

CM must exactly match the native policy authority on the translated subset and show a repeatable offline audit/versioning or total repeated-query advantage. A synthetic request-stream win alone does not establish production-agent value.

#### Computational biology and Boolean regulatory networks

##### Priority

Tier B — conditional

##### Audit verdict

Plausible for reusable update-rule and intervention families, but the earlier wording could be read as an attractor-analysis claim. Current CM evidence does not support replacing specialized Boolean-network dynamics tools.

##### Pain point

Researchers reuse related Boolean update rules across knockouts, over-expression, environmental inputs, parameterizations, and model revisions while trying to preserve regulatory provenance and understand why behavior changed.

##### Proposed CM role

Compile individual update functions or bounded synchronous-step slices, retain regulatory-rule structure, reuse unchanged modules, and restrict under interventions. Treat attractor and transition-system analysis as separate downstream tasks unless CM gains explicit dynamics semantics.

##### Scope correction

Do not claim whole-network attractor, asynchronous dynamics, or model-checking dominance. Preserve update semantics, input conventions, and multi-valued Booleanization metadata.

##### Real datasets

###### Biodivine Boolean Models benchmark collection

###### Url

https://github.com/sybila/biodivine-boolean-models

###### Use

Use the repository's validated BNET/AEON/SBML exports and metadata; stratify by variables, inputs, regulations, source repository, and model provenance.

###### License note

Model copyrights remain with original authors; follow each model's source and citation metadata before redistribution.

###### Cell Collective API and export tooling

###### Url

https://github.com/cellcollective/ccapi

###### Use

Obtain public Boolean rules, truth tables, and SBML-qual exports where permitted, then build intervention/version traces without discarding biological annotations.

###### License note

API client is MIT; model-specific rights and citations must be checked separately.

##### Synthetic scenario

From each real network, create seeded knockout, constitutive-expression, input-fixation, and localized rule-edit families. Keep regulatory modules unchanged across most versions and record which attractor-facing question is only proxied by update-rule evaluation.

##### Baselines

AEON/Biodivine BDD tooling

BoolNet or bioLQM/GINsim

SAT-based Boolean-network analysis

plain compiled update functions

##### Tasks

compile update-rule family

evaluate bounded synchronous step

intervention restriction

model-version diff

shared-module reuse

provenance recovery

##### What would establish a useful advantage

CM must match update semantics exactly and win on a real intervention/version workflow or provide demonstrably better rule-level provenance. Attractor speed cannot be claimed from update-function timing.

#### Classical reversible and control logic in quantum toolchains

##### Priority

Tier C — narrow research

##### Audit verdict

Correct only with a hard boundary around classical Boolean or reversible components. This is the weakest general-domain claim and should remain a targeted research experiment.

##### Pain point

Quantum compilation flows contain classical reversible or control subcircuits that are rewritten across versions and must retain exact computational-basis behavior, ancilla/garbage conventions, and construction provenance.

##### Proposed CM role

Represent bounded Boolean output functions of reversible components, reuse their shared classical structure across variants, and compare structural or truth-functional deltas. Use a quantum-native checker for genuinely quantum semantics.

##### Scope correction

CM does not represent amplitude, phase, interference, entanglement, noise, measurement probability, or general unitary equivalence. Multi-output reversible semantics and ancilla/garbage bits must be explicit.

##### Real datasets

###### RevLib reversible benchmark library

###### Url

https://www.revlib.org/

###### Use

Use machine-readable function specifications and REAL circuit realizations for classical reversible truth functions, including declared constants and garbage outputs.

###### License note

Cite individual contributors and confirm reuse terms for selected artifacts.

###### MQT Bench

###### Url

https://www.cda.cit.tum.de/mqtbench/index

###### Use

Use only circuits or extracted regions with a documented classical/reversible Boolean interpretation; the broader quantum suite is a negative-control boundary, not CM input.

###### License note

Follow the benchmark package/repository license and cite the MQT Bench publication.

##### Synthetic scenario

Generate reversible Toffoli/CNOT networks with explicit ancilla and garbage declarations, create equivalence-preserving gate rewrites and localized oracle edits, and export each output as a bounded Boolean root with a full mapping checksum.

##### Baselines

RevKit or reversible-logic simulator

MQT QCEC for quantum-aware equivalence

ROBDD/CUDD

SAT/SMT miter

packed truth-table evaluator

##### Tasks

multi-output truth-function extraction

equivalent circuit revision

localized oracle change

ancilla restriction

shared-subcircuit reuse

round-trip provenance

##### What would establish a useful advantage

CM must match every declared output under constants/garbage conventions and win a classical reversible version workflow. No result may be generalized to quantum-state simulation or unitary equivalence.

#### Compilers and program analysis

##### Priority

Tier A/B — bounded subset

##### Audit verdict

Strong for families of pure Boolean predicates and incremental path contexts; unsound as a general compiler-verification claim without modeling integers, memory, poison, undefined behavior, and interprocedural effects.

##### Pain point

Compilers repeatedly simplify, compare, and partially evaluate related branch and optimization predicates across passes, builds, and known program facts, often losing a stable cross-version identity for the logical slice.

##### Proposed CM role

Use CM for extracted pure-Boolean i1 predicate families: retain expression lineage, reuse shared subgraphs, restrict under known facts, and compare before/after predicates. Leave full IR refinement semantics to Alive2/SMT.

##### Scope correction

Exclude or explicitly encode integer widths, overflow, poison, undefined behavior, memory, loops, and calls. A Boolean projection is valid only under a documented extraction contract.

##### Real datasets

###### Alive2 and LLVM transformation tests

###### Url

https://github.com/AliveToolkit/alive2

###### Use

Select transformations whose source/target condition is a supported pure Boolean slice; use Alive2 as the semantic oracle and retain before/after IR provenance.

###### License note

Alive2 is MIT; LLVM inputs retain their own repository licensing and attribution.

###### LLVM test suite and regression corpus

###### Url

https://github.com/llvm/llvm-test-suite

###### Use

Extract repeated branch/path predicates from public programs and preserve program/test provenance; use reference outputs only for overall correctness, not as Boolean equivalence labels.

###### License note

Inspect the LLVM test-suite license and per-benchmark notices, especially external suites.

##### Synthetic scenario

Generate SSA-like Boolean DAGs with repeated guards, equivalent InstCombine-style rewrites, localized pass edits, and evolving fact sets. Include negative controls with integer/UB features that the importer must refuse rather than silently Booleanize.

##### Baselines

Alive2/Z3

LLVM InstCombine or SimplifyCFG

e-graph rewriting

ROBDD/CUDD

compiled predicates with memoization

##### Tasks

pure-Boolean extraction

before/after equivalence

known-fact restriction

incremental version update

subexpression lineage

refusal of unsupported semantics

##### What would establish a useful advantage

CM must agree with Alive2 on the accepted subset, refuse unsupported semantics, and beat the strongest Boolean baseline on a natural repeated-predicate trace or deliver measurable lineage/change-analysis value.

#### Security policy and access control

##### Priority

Tier A — test first

##### Audit verdict

One of the strongest fits for offline policy audit, related-version analysis, and repeated partial contexts. Native Cedar/OPA remains the online enforcement baseline and semantic authority.

##### Pain point

Authorization teams need to know not only whether a request is allowed, but which rule caused it, whether a policy revision expands reachability, which users/resources are affected, and whether unchanged policy structure can be reused safely.

##### Proposed CM role

Compile a documented Boolean subset into a versioned audit artifact, retain rule/subexpression provenance, restrict under principal/resource/context attributes, and calculate exact bounded change-impact sets across revisions.

##### Scope correction

Do not flatten typed entities, hierarchy, sets, strings, time, or deny-overrides semantics without a verified translation. Online request latency is unlikely to be CM's first dominance surface.

##### Real datasets

###### Cedar example use cases and performance artifacts

###### Url

https://github.com/cedar-policy/cedar-examples

###### Use

Use the application policies, schemas, entities, allow/deny requests, templated variants, and published benchmark folder as executable policy fixtures.

###### License note

Apache-2.0.

###### Cedar integration-test corpus

###### Url

https://github.com/cedar-policy/cedar-integration-tests

###### Use

Use handwritten and generated policy/entity/request cases as translation and differential-correctness tests before any timing claim.

###### License note

Follow the repository license and retain generated-corpus revision metadata.

###### OPA policy performance guidance

###### Url

https://www.openpolicyagent.org/docs/policy-performance

###### Use

Use OPA's benchmark methodology and metrics for any documented Cedar/Rego common subset; do not compare unlike policy semantics.

###### License note

Documentation and software are governed by the OPA project licenses.

##### Synthetic scenario

Generate RBAC/ABAC policy families with permit/deny precedence, entity hierarchy, tenant isolation, localized edits, and request traces. Emit both a rich native form and an explicitly limited Boolean projection with differential labels.

##### Baselines

native Cedar authorizer and symbolic compiler

OPA/Rego on a common subset

BDD or SAT policy analyzer

indexed decision tables

##### Tasks

differential authorization

policy-version reachability delta

counterfactual restriction

rule provenance

warm request trace

translation refusal/coverage

##### What would establish a useful advantage

Zero decision mismatches are mandatory. CM must beat the best audit-capable baseline on total version-analysis cost or produce exact change/provenance output not otherwise available; online latency alone is not sufficient.

#### Configuration systems and product families

##### Priority

Tier A — strongest first experiment

##### Audit verdict

The cleanest domain match: long-lived constraints, many partial assignments, related model versions, and exact change-impact questions directly exercise CM's proposed structural and context-reuse value.

##### Pain point

Feature models evolve while configurators repeatedly add and retract partial selections, test validity, explain conflicts, identify dead options, and assess which products or constraints changed between releases.

##### Proposed CM role

Retain feature-constraint structure and identity across sessions and versions, reuse unchanged subgraphs, restrict under partial selections, and expose exact bounded differences for sliced feature neighborhoods.

##### Scope correction

Whole-product enumeration is exponential and often inappropriate. Compare sliced/bounded explicit artifacts separately from SAT satisfiability, model counting, or BDD symbolic configuration.

##### Real datasets

###### FeatureIDE/FeatJAR models and analysis tooling

###### Url

https://github.com/FeatureIDE/FeatureIDE

###### Use

Use public example/fixture feature models and their analysis semantics; preserve hierarchical and cross-tree constraints when translating.

###### License note

FeatureIDE reports LGPL-3.0; verify model-specific notices.

###### torte reproducible feature-model experiments

###### Url

https://github.com/ekuiter/torte

###### Use

Use its curated feature-model benchmark, KConfig extraction, histories, transformation pipeline, and reproducibility metadata for real version families.

###### License note

Follow repository and constituent-model licenses.

###### Linux Kconfig history

###### Url

https://github.com/torvalds/linux

###### Use

Extract version-pinned Kconfig constraints and adjacent release histories through a published extractor; do not treat raw Kconfig syntax as a complete Boolean model without validation.

###### License note

Linux source is GPL-2.0-only; derived benchmark redistribution requires legal/license review.

##### Synthetic scenario

Generate hierarchical feature models with seeded mandatory/optional/alternative groups, cross-tree constraints, localized release edits, and interactive sessions that add/retract selections. Sweep slice size, shared constraints, edit locality, and residual support.

##### Baselines

FeatJAR SAT4J/Kissat/CaDiCaL analyses

ROBDD feature configurator

incremental SAT

plain compiled predicates

##### Tasks

interactive partial configuration

validity and conflict explanation

version delta on bounded slice

dead-feature query

session reuse

serialize/reload

##### What would establish a useful advantage

CM must preserve feature-model semantics and beat the fastest equivalent baseline on a real interaction/version trace for bounded slices, while reporting enumeration boundaries and all models that never amortize construction.

#### Regulated rule and decision systems

##### Priority

Tier B — Boolean decision-table subset

##### Audit verdict

Credible for audit and versioning of Boolean decision tables, but too broad if it implies that CM directly models numeric tax formulas, dates, aggregation, priorities, or the full DMN/OpenFisca language.

##### Pain point

Governed decision services need reproducible outcomes, explicit rule-version provenance, overlap/gap detection, controlled changes, and regression evidence across many related cases.

##### Proposed CM role

Compile the explicitly Boolean portion of a decision table or eligibility rule set into a versioned artifact, retain rule composition, compare revisions, and enumerate exact bounded coverage or conflict regions.

##### Scope correction

Numeric thresholds can become finite predicates only under a declared abstraction. Preserve DMN hit policy, rule priority, null/unknown handling, dates, and arithmetic in the native engine unless formally translated.

##### Real datasets

###### DMN Technology Compatibility Kit

###### Url

https://github.com/dmn-tck/tck

###### Use

Use reference DMN models with serialized inputs and expected outputs; select and declare the Boolean/decision-table subset, retaining hit-policy semantics and conformance identifiers.

###### License note

The project describes freely accessible test cases under a Creative Commons share-alike attribution model; verify repository license files for redistribution.

###### OpenFisca country packages

###### Url

https://openfisca.org/en/packages/

###### Use

Use package tests and version histories to identify bounded Boolean eligibility subgraphs; keep arithmetic microsimulation in OpenFisca as the oracle.

###### License note

OpenFisca core is AGPL; inspect each country package and input dataset license separately.

##### Synthetic scenario

Generate DMN-like Boolean decision tables with explicit hit policies, seeded overlaps, gaps, shadowed rules, localized version edits, and regression cases. Also generate unsupported numeric/date cases that the CM importer must refuse or abstract explicitly.

##### Baselines

DMN TCK-capable engine

OpenFisca for selected eligibility rules

decision-table index

BDD/SAT coverage analyzer

ordinary compiled predicates

##### Tasks

conformance replay

coverage/overlap/gap analysis

version regression

bounded eligibility enumeration

rule provenance

unsupported-semantics refusal

##### What would establish a useful advantage

CM must match the native engine on every accepted test, preserve hit-policy behavior, and show lower total audit/version cost or better exact bounded coverage output. Passing a Boolean projection does not establish general rules-as-code dominance.
