# CRSE learning research — new-task implementation prompt

Copy this document into a new coding task, or explicitly ask that task to read
this file and use it as its implementation brief. It preserves the research
agenda; it is not an instruction to restart the historical Windows launcher.

---

## Outcome

Extend the existing Certified Recognition and Strategy Engine (CRSE) into a
local-first research system for learning to make exact Correspondence Matrix
(CM) and propositional-logic computations cheaper. Implement working software,
train actual models, and run reproducible, task-matched experiments. Do not stop
at another proposal, a collection of model stubs, or an architecture diagram.

I want eventually to investigate every research path listed below, including
deep neural networks and appropriate LLM-assisted approaches. Preserve all paths
in a living experiment register. Implement them in coherent, tested increments;
do not attempt a giant uncontrolled Cartesian product of models and tasks.
A negative result is a valid research outcome, not a reason to hide an experiment.

The central architecture is learned recognition/proposal/ranking plus exact
execution and verification. Explore CMs both as model inputs and as exact
training teachers for models that operate on expression graphs. The objective
is useful generalization to unseen functions, structures, contexts, and versions,
not merely replaying cached answers or fitting the benchmark generator.

## 1. Start from the software and evidence already present

Repository: `C:/Users/brian/Documents/CM_Computation`.
Known checkpoint: `db952fb6772231ff8193811511afa49ab499d729`,
`Checkpoint CRSE research and CM neural-learning assessment`.

Read applicable AGENTS.md guidance and inspect the assigned checkout before
editing. Verify the checkpoint is available; inspect subsequent changes rather
than resetting to it. Other tasks share this project. At handoff, unrelated dirty
work includes `docs/research/README.md`, `scripts/cm_measurement_verify.py`, and
`tests/test_cm_measurement_verify.py`, plus other untracked research files.
Recheck current status; do not assume that list is exhaustive or still current.

Read these existing sources, relative to the repository root:

1. `CRSE_COMPUTATION_FIRST_STATUS.md`.
2. `docs/recognition/README.md`.
3. `docs/recognition/LEARNING_INVESTIGATION_2026_08_29.md` and
   `docs/recognition/learning_diagnostics_2026_08_29.json`.
4. `docs/recognition/CM_NEURAL_BENCHMARK_ASSESSMENT_2026_08_29.md`.
5. All six modules in `cmbench/recognition/`,
   `scripts/cm_recognition_experiment.py`, and `tests/test_recognition_research.py`.
6. Relevant existing AST, DAG serialization, CM, and exact-backend interfaces:
   `cm_exprlib.py`, `cm_expr_serde.py`, `cm_ir.py`, `bitset_backend.py`,
   `cmbench/expr/`, `cmbench/backends/`, `cmbench/results/`,
   `cmbench/output_budget.py`, and `cmbench/tracing/`.
7. `deliverables_n22_24/master_explainer_2026_08_03/index.html`, especially the
   embedded `_content.use_case_benchmark_catalog` and `e20_feature_model_audit`.
   The embedded DATA is on a very long line: parse its JSON and inspect selected
   sections instead of dumping that line into the conversation.
8. The scientific capability, transformation, and benchmark lists in
   `CERTIFIED_RECOGNITION_STRATEGY_ENGINE_ORCHESTRATOR_PROMPT.md`, especially
   sections 3–12 and the scientific workstream descriptions. Treat its historical
   approval/effect instructions as background, not the active workflow here.

The paper is available at
`C:/Users/brian/Downloads/CorrespondenceMatrices (2).pdf`.
Read relevant definitions and inspect matrix layouts using the PDF skill if
available. Its prior-reviewed SHA-256 is
`7a9958a2ec34e61318855a3e8054d668c7d9654de3316c4fe546f7db7a2503a9`.
If unavailable, use the checked-in assessment and executable exact semantics,
mark the source limitation, and request the PDF only if it becomes essential.

The original Matrix Model Factory and WCP/controller packets concern another
workstream. Windows launcher development, native containment, VM/Docker setup,
Orchestrator workspace creation, and deployment remain deferred, not completed.
Do not restart those tasks or require their old effect gates for ordinary local
research. Do not edit the Orchestrator repository or alter its approval system.

### Current implementation and what the evidence does not show

- `CostTree`, `fit_cost_tree`, and `load_model` implement a bounded cost-sensitive
  decision tree, not a neural network or LLM. The retained pilot model has seven
  nodes, four leaves, depth three, and 1,684 JSON bytes.
- `portfolio.prepare` supplies `direct`, sharing-aware `cse`, and `cm` backends.
  CSE and CM use the same bigint executor. `cm` means CM-IR simplification here,
  not construction of a dense pixel matrix. Keep that distinction in reports.
- `portfolio.reference_bits` is a separate NumPy Boolean interpreter.
  `corpus.make_corpus`, `experiment.run_experiment`, and `write_artifacts` already
  provide generation, measurements, validation, and artifact records. Extend
  these mechanisms without replacing their scientific contracts silently.
- The original pilot used 48 training formulas and returned 0.613 geometric-mean
  speedup versus fixed CSE on its 16 test formulas: it was slower. Feature and
  inference costs matter. The zero-overhead oracle is not an achieved speedup.
- A later in-memory feature ablation measured about 1.230 speedup on 32 fresh
  known-family formulas and 1.719 on eight mux formulas for a query-only tree.
  Its raw rows and complete candidate artifacts were not retained. The saved
  summaries are exploratory, not reproducible confirmatory evidence. An equally
  cheap query-count rule was not yet beaten. Reimplement and replicate this
  experiment with complete artifacts; do not treat it as an integrated feature.
- `docs/recognition/runs/pilot-20260828-001/` contains ignored local pilot
  artifacts if still present. Do not overwrite them or silently depend on them
  being available in every checkout. Missing artifacts require a clearly new run.
- No neural or LLM benchmark result exists yet. The website's feature-model
  performance remains provisional because of documented measurement gaps.

## 2. Scope, autonomy, and resource boundaries

This is an implementation task when I assign this brief. Proceed with relevant
local inspection, code/documentation edits, generated fixtures, non-destructive
tests, bounded training using available dependencies, and local evaluation.
Continue to the next safe implementation step without asking me to say
"continue" after every milestone. State assumptions and summarize outcomes.

Do not commit, push, deploy, publish, upload local formulas/netlists, start cloud
resources, call paid APIs, access credentials, accept licenses, install system
components, or perform destructive cleanup without the required explicit
authorization. Do not read `.env*`, key files, token caches, or credential stores.
Do not turn this task into a service, an unattended background job, or an
automatically retraining production system.

If new dependencies, datasets, model downloads, or larger compute are needed,
prepare one grouped request naming exact packages/models/sources, versions or
revisions, licenses, local paths, download size, intended effects, and finite
compute/cost limits. Continue independent local work while that decision is
pending. An approval covers its stated scope; do not repeatedly request approval
for each normal test or training step within it. Unavailable optional tools
should not block the rest of the program.

Use the project's `.venv/Scripts/python.exe` where compatible. Keep neural and
LLM dependencies optional and lazy-imported so the existing NumPy-only pilot and
its tests still work. Prefer an established framework when available; a genuinely
trained NumPy MLP may serve as a small neural baseline, but does not complete
the CNN/GNN/LLM tracks. Do not build a new general-purpose deep-learning framework.

Start with CPU-only smoke experiments, the existing input-admission bounds, and
small local blocks (initially at most eight variables). Preserve the current
16-variable/4,096-node/depth-96/full-reference guards in the original pilot.
Use an explicit finite experiment manifest before execution: seeds, corpus size,
training steps/epochs, batch size, threads, wall time, memory estimate, and output
directory. Default smoke wall budget: 120 seconds per run, at most three training
seeds and two CPU threads; do not multiply bounded runs into an unbounded sweep.
Stage larger local campaigns as one explicit, budgeted batch for review.

Admission checks must precede large allocations. Label cooperative time checks
honestly; they are not a hard OS sandbox. Do not launch unbounded native solver
calls and assume a Python timer can stop them. Use verified existing bounded
adapters where suitable, or defer those runs with a precise limitation.

## 3. Scientific invariants

Define the requested computation before selecting a method. Keep separate tasks
for complete output, one assignment, SAT/witness, validity, equivalence,
implication, exact count, partial restriction, simplification under a stated cost,
compact representation, CM composition/quotient, semantic change impact,
functional-block recognition, and repeated context/version workflows.

Exactness is mandatory for accepted computational results. A learned model may
propose a backend, motif, rewrite, partition, order, search hint, refusal, or
abstention. It cannot certify its own output. Use independent exact evaluation
at bounded support, checked rule side conditions, GF(2) algebra for a verified
fragment, BDD checks with explicit manager/order semantics, or independently
checked SAT/UNSAT certificates as appropriate. A SAT witness does not prove
UNSAT or an exact count. Random tests and approximate signatures are not proofs.

Invalid, uncertain, unsupported, or timed-out proposals are rejected and the
exact fallback remains available within the same total budget. Record rejection
costs. Preserve the original input until acceptance, and test a single switch
that disables all learned advice without changing the exact result contract.

Distinguish a reusable rule proved over metavariables from one instance verified
on one formula. Check side conditions on every use. New rules/macros need
admission evidence, bounded matching, redundancy/cycle handling, and provenance.
Only this proof-and-compile path can legitimately turn a learned discovery into
a cheap deterministic rule; it is not the same thing as caching an answer.

An explicit single-output CM/truth vector still needs `2^k` bits for k independent
variables. Do not give a model the already-computed answer for free when timing
construction from an expression. Graph inputs, local blocks, and compact exact
outputs can avoid full materialization; they do not erase that output bound.

CMs require explicit variable order/partition, assignment labels, bit order,
shape, and valid-bit masks. Binary input values do not imply binary neural
weights. Matrix rotation, transposition, input negation, output negation, and
variable permutation need correctly transformed labels, not image-style
augmentation that silently changes semantics. When comparing CM to other
representations, align the variable universe and distinguish structural identity
from semantic identity. For factorization use the intended algebra, especially
AND/XOR over GF(2), not approximate real-valued low rank.

Generate labels from exact executable semantics. The paper's page-12 example
`(X implies Y) XOR (X OR Y)` simplifies to `NOT Y`, not the printed `NOT X`;
the assessment records the four-assignment check. Do not copy unchecked worked
examples into training labels. Turn relevant identities into executable tests.

## 4. Preserve every capability in an experiment register

Create a machine-readable register plus a readable roadmap under
`docs/recognition/`. Retain these stable IDs. Each entry records its hypothesis,
input/output contract, representation, model/deterministic controls, exact
checker, source data, dependencies, next experiment, results, resource needs,
and status: planned, implemented, smoke-tested, measured, replicated,
negative-result, or blocked-with-reason. Interfaces/stubs do not mean measured.
Do not silently delete a path because another path is easier or performs better.

| ID | Capability to investigate | Minimum scope retained |
| --- | --- | --- |
| R01 | Task-aware routing and cost prediction | Direct/CSE/CM, bigint/words, later task-eligible BDD/SAT/counting; cheap features, query-count rules, learned feature acquisition, feasibility and tail-risk prediction |
| R02 | Computational-subclass recognition | Hidden affine/XOR, Horn, dual-Horn, 2-CNF, low-width/separator structure, independent components, cardinality/threshold constraints, mux/ITE, arithmetic blocks and adders |
| R03 | Verified motifs and semantic macros | Obscured/redundantly written XOR, mux, comparators, half/full adders, repeated cones, and generalized functions; verified boundary and replacement |
| R04 | Rewrite profitability and scheduling | Region/rule/direction selection, sequences, stopping, cost-aware factoring versus expansion, and preservation of sharing |
| R05 | Generalized rule discovery | Infer identities over metavariables, synthesize macros, prove before admission, compile cheap matchers, prevent rewrite cycles |
| R06 | CM decomposition and layout | Cofactors, repeated/complementary blocks, disjoint supports, variable partitions, recursive blocks, GF(2) rank/factors, tensor/Kronecker-style exact decompositions |
| R07 | Order and compilation selection | BDD variable order including native reordering controls, AIG cuts/balancing/refactoring/resubstitution, compact representations, low-width decomposition, and query-appropriate targets |
| R08 | Functional similarity and retrieval | Rank equivalent/complementary/related functions, semantic embeddings, nearest-candidate lookup, and exact follow-up verification; compare hashing and deterministic signatures |
| R09 | Partial contexts, sessions, and versions | Choose specialization, incremental updates, reusable compiled regions, cache policies, and change-impact strategy; correct invalidation, context identity, provenance, serialize/reload |
| R10 | SAT/equivalence/counting guidance | Bounded initial variable/polarity hints, portfolio choice and component/order advice; maintain exact solver completeness and independent checking |
| R11 | CMs as exact training teachers | Supervise graph models from local truth functions, cofactor relations, functional distances, and verified transformation costs; no full CM required at inference |
| R12 | Neural representation comparisons | Dense CM/block MLP or CNN; recursive/shared-block model; source AST/AIG/CM-IR GNN; hierarchical/transformer and fused graph+CM variants |
| R13 | Learning-method comparisons | Cost-sensitive regression/ranking, linear models, trees/rule lists, forests/boosting/quantile models; supervised, contrastive/self-supervised, multitask, imitation, transfer, and curriculum learning |
| R14 | Adaptive/sequential learning | Active learning, hard negatives, counterexample-guided refinement, replayed contextual bandits, bounded reinforcement learning, phase changes and drift; no automatic production adaptation |
| R15 | LLM-assisted learning and discovery | Offline DSL rule/macro proposals and bounded symbolic program synthesis, strategy/cost ranking, proof candidates, explanatory reports, few-shot/retrieval controls, optional approved adapter fine-tuning and teacher-to-small-model distillation |
| R16 | Inference and training efficiency | Feature budgets, batching, incremental embeddings, early exits, distillation, quantization/binarization, model compilation, CPU/GPU crossover, and caching with explicit accounting |
| R17 | Confidence, novelty, and abstention | Calibration, out-of-distribution behavior, feasibility, uncertainty-triggered fallback, negative transfer, adversarial near-matches, and hardware transfer |
| R18 | Negative controls and hard limits | Predicting raw AND/OR/XOR/equality/popcount versus exact packed operations; random/dense incompressible tables, no-sharing/anti-reduction cases, low oracle headroom, and overhead-dominated workloads |

Carry this complete transformation inventory into the R02–R07 implementations:
constant propagation; irrelevant-variable elimination; idempotence; complement;
double negation; absorption; consensus; associative/commutative flattening and
operand ordering; De Morgan/NNF; implication/equivalence elimination or useful
introduction; XOR cancellation and affine extraction; distributive factoring
and bounded expansion; mux/ITE introduction; Shannon expansion; cofactoring and
restriction; independent-component decomposition; common-subexpression/repeated
cone recognition; symmetry; small-function classification; CM transpose,
negation, aligned composition and directional quotient/set difference; and AIG
balancing/rewrite/refactor/resubstitution. Keep semantic XOR difference distinct
from directional quotient and repository-specific structural operator artifacts.

### Neural and LLM implementation expectations

Provide an actual train/save/reload/infer/evaluate path for neural models, not
random embeddings or an untrained network called a learned baseline. Start with
small MLP/CNN and GNN experiments, roughly 50,000–250,000 parameters where sensible;
report actual parameters, layers, activations, graph memory, and latency. Include
larger/deeper/hierarchical models in controlled scaling experiments, not as an
assumed improvement. Do not require one network to solve every task.

Compare matrix versus graph versus fused inputs with matched task/data/training
budgets, and distinguish representation gains from changes in parameter count or
optimization. Preserve edge roles, negations, variable identities, and DAG sharing.
Test functional-equivalence augmentation, hard near-matches, and generalization
across formula size/support; handle padding/masks and unseen sizes explicitly.

LLMs are optional research participants, not the logical authority or an automatic
runtime dependency. Separate frozen pretrained inference, in-context examples,
retrieval, actual parameter training, and compiled/distilled discoveries in all
reports. Prefer offline proposals in a small declarative Boolean DSL. Parse and
bound outputs; never execute model-generated Python, shell commands, imports,
or verifier changes as a shortcut. Verify candidate proofs using an independent
checker; natural-language confidence is not evidence. Do not train a foundation
model from scratch. Local models, API calls, fine-tuning, and associated data
transfer require the applicable resource/dependency approvals above.

Implement the provider boundary and deterministic fake-output tests even when a
live LLM is unavailable, but leave the actual LLM experiment visibly pending.
When authorized, pin model identity/revision where possible, prompt and retrieval
hashes, sampling settings, token/call/retry limits, cost, latency, and licensing.
Compare LLM proposals against grammar enumeration, deterministic rules, random
candidate order, search/imitation baselines, and non-LLM proposers. Include all
rejected proposals and candidate-generation cost, not just the successful ones.

## 5. Reuse the harness; make extensions modular and measurable

Use versioned, typed contracts for task, input/representation, feature bundle,
candidate proposal, deterministic applicability check, exact acceptance check,
learner, trained artifact, backend adapter, budget, and experiment result.
Keep training, inference, checking, and measurement separable. Add only the
abstraction needed by a working vertical slice; do not refactor unrelated code.

Every proposal should carry its source-region identity, rule/model version,
substitution, side conditions, predicted cost/uncertainty, candidate budget,
pre/post structural metrics, check result/evidence, rejection reason, and actual
end-to-end cost. Distinguish handwritten, synthesized, and learned proposals.
Use decision traces and auditable model cards. Feature schemas and fallback
policies must be bound to the model artifact, not changed silently at evaluation.

Use inert bounded serialization: JSON for metadata; strictly checked numeric
arrays or a vetted non-executable tensor format for weights. Check hashes,
dimensions, dtype, finiteness, allocation limits, schema/version, and architecture
before loading. Do not load untrusted pickle/joblib or arbitrary executable
checkpoints. Malformed, stale, or mismatched models must fail closed. Persist
partial/interrupted runs as incomplete, never as accepted or promoted artifacts.

Preserve the existing preview-by-default, explicit-run, and no-overwrite behavior.
Add clear CLI/config entry points for dataset generation, training, evaluation,
and experiment selection without silently running training on import. Keep
large datasets/checkpoints/raw outputs in ignored unique run directories and
commit-sized summaries/specifications separate. Every completed run needs raw
rows, frozen split/model/config, data/source hashes, environment and dependency
versions, seeds, timing boundaries, correctness results, and a readable report.
Re-running an experiment must not depend on hidden conversation state.
Extend source fingerprinting to cover new nested model/adapter modules; the
current pilot's top-level recognition-module glob is not sufficient for those.

## 6. Task-matched baselines and representative applications

Retain strong exact and non-neural controls: raw packed evaluation; flat bigint;
NumPy words; sharing-aware CSE-flat; CM IR/flat/word/no-reinflate variants where
eligible; exact result cache and compiled-artifact reuse; in-repository ROBDD and
optional dd.autoref/CUDD with exact engine labels; BDD restriction; SAT through
correct Tseitin/miter contracts; GF(2)/ANF for admitted fragments; SymPy for its
symbolic task; Espresso/PyEDA for minimization; ABC/AIG transformations; bounded
equality saturation; and exact #SAT/knowledge compilation on separate contracts.
Inspect what exists before adding an adapter. An unavailable backend is reported,
not silently omitted or mislabeled as a different implementation.

Native SIMD, JIT/model compilation, GPU/batched packed computation, and cache
engineering remain possible non-neural efficiency controls. Do not require them
for a first experiment or conflate an engineering win with a learning win.

Preserve all eight application families from the master explainer:

| Priority | Application | Meaningful experiment and boundary |
| --- | --- | --- |
| First | Configuration/product families | Partial selections, dead-feature/validity queries, version deltas and reuse; compare incremental SAT/BDD/exact CM, not whole-product enumeration against a yes/no solver |
| First | Hardware verification/design | Bounded EPFL-style cones, repeated revisions, hidden motifs, restriction, equivalent rewrites and localized changes; compare ABC/AIG/CUDD/SAT/exact packed paths |
| Next | Security/access-control policy audit | Exact bounded change-impact and context restriction; native Cedar/OPA semantics remain authoritative for a verified Boolean subset |
| Next | Compiler/program-analysis predicates | Pure Boolean i1/guard families and known-fact rewrites; do not silently model integer overflow, memory, poison, or undefined behavior as ordinary Booleans |
| Later | AI-agent hard guardrails | Deterministic authorization logic, delegation/tool-policy versions and provenance; not open-ended reasoning or neural confidence as permission |
| Later | Boolean biological networks | Update-rule/intervention families with preserved update semantics; update speed is not an attractor-analysis result |
| Later | Regulated rules/decision tables | Boolean eligibility, coverage, overlaps and version regressions; preserve priority/hit-policy and refuse unsupported numeric/date/null semantics |
| Narrow | Classical reversible/control logic | Boolean output functions with explicit constants, ancilla and garbage conventions; no claims about quantum amplitudes, phase, entanglement or unitary simulation |

Use existing local provenance-reviewed data first. Record local license/attribution
and immutable source revision. Separate natural traces from generated or mutated
mechanism demonstrations. Keep all other domains on the register even if the
first runnable end-to-end domain is configuration or hardware.

## 7. Training and evaluation discipline

Create training, validation, exploratory-test, and sealed confirmatory partitions
by source circuit/model history and generating template, not by timing row,
matrix pixel, adjacent version, or renamed expression. Group semantic equivalents
when tractable; otherwise report exactly which leakage checks are implemented.
Remove known structural/alpha-renaming/commutative duplicates and transformed-copy
leakage. Fit normalization, embeddings, retrieval indexes, thresholds, and fallback
choices only with allowed training/validation data. A later tuning decision after
test inspection requires a fresh confirmatory set.

Include random, XOR/implication-heavy, balanced-all-variable, redundant/shared,
low-reuse, anti-reduction, BDD-friendly/hard/order-sensitive, hidden-motif, and
independently sourced families. Sweep live support separately from ambient count;
query reuse, depth, sharing, context overlap/phase changes, edit radius, density,
and hardware. Keep malformed/deep/cyclic inputs, near-equivalent one-bit changes,
unsupported semantics, refusals, proof disagreement, timeout and memory cases.
Do not discard unsuccessful runs to manufacture a feasible-looking dataset.

Train cost-sensitive/ranking models on measured comparable costs, not just
winner labels; label post-execution information oracle-only unless a timed probe
is explicitly part of inference. Use a virtual-best ceiling to diagnose headroom.
All research tracks may receive a bounded feasibility experiment even with a low
ceiling, but do not scale training on a task with no plausible overhead-adjusted
opportunity. Compare equal search/candidate budgets, not a neural best-of-many
result against a single deterministic attempt without charging that search.

For bandit/sequential experiments, distinguish full-information cost tables from
feedback available only for the chosen action. Do not expose future labels or
unchosen costs to an online policy. If evaluating logged off-policy behavior,
retain action-selection probabilities and state the estimator's assumptions.
Local bounded learning on a generated stream is a research experiment, not
permission for automatic production retraining or model replacement.

Measure preparation, feature extraction, inference, candidate generation/search,
backend build, kernel, conversion/materialization, and required acceptance proof
separately and in the end-to-end total. A common independent after-the-fact audit
can be outside all arms' primary timers; checks needed to accept a learned
proposal belong inside its timed path. Include model load and CPU/GPU transfer
in cold cells; distinguish warm batching throughput from single-request latency.

Separate fresh expressions, identical-answer caching, precompiled sessions,
related expressions, partial-context changes, version updates, and reload/first
query. Do not call recomputation Q times on one expression an interactive session
trace. Charge specialization/inference once only if genuinely reusable. Give
the strongest baseline equivalent cache and preprocessing opportunities.

Use paired counterbalanced timings, per-instance summaries, multiple training
seeds, source/family-clustered confidence intervals, and explicit timer-noise
controls. Repeated rounds are not independent samples. Report wall time, peak
memory, output/certificate correctness, regret, p95/p99/max slowdown, >=2x choices,
timeout/OOM/refusal rates, coverage, abstention, calibration, precision/recall,
query-count break-even, and data-generation/training/inference cost. Record model
loading and retraining economics separately from steady-state query savings.

No accepted semantic mismatches or unverified applied transformations are allowed.
Accuracy alone is inadequate: the site's k=16 feature-model sample has only
86 valid queries out of 20,480, so always predicting invalid gets about 99.58%
accuracy while failing every valid query. Similarly, near-zero truth-table
distance does not make an authorization change or equivalence error acceptable.

Predeclare practical materiality and tail-risk criteria per task before the
confirmatory run. A promising exploratory win is not production promotion.
Seek a second source family and eventually a second machine; if unavailable,
leave replication pending instead of relabeling more local rounds independent.

## 8. Implementation sequence and completion bars

Keep a short working plan and the full register. The following sequence is a
default, not a requirement to request approval at every boundary.

**Milestone A — trustworthy reusable foundation.** Re-run the relevant existing
tests; preserve baseline behavior; persist the reduced-feature ablation properly;
add the equally cheap query-count rule; implement the task/proposal/check/model
contracts needed for the first neural slice. Include a small exact CM/cofactor
teacher and explicit input layout tests. Do not stop at this milestone if a
safe next step is available.

**Milestone B — first actual neural comparison.** Train at least one small neural
motif/profitability model on generated exact-labeled small functions. Use hidden
XOR/affine or mux motifs as the first slice. Save/reload the trained model, verify
every accepted replacement, and benchmark against an exact motif detector,
deterministic rewrite policy, tiny tree, and no-learning exact computation.
Retain a fresh held-out result even if slower. Random/untrained models are
controls, never substitutes for this milestone. If a framework approval is
missing, report the precise dependency rather than claiming completion.

**Milestone C — graph learning with CM supervision.** Implement and train a GNN
using local exact CM/cofactor supervision, compare against the matrix model,
and test new structure/support and at least one real local circuit/configuration
source when eligible. Add contrastive functional retrieval with exact checks and
the graph-versus-CM-versus-fused representation ablation. A small smoke run proves
plumbing, not scientific generalization.

**Milestone D — transform, decompose, and reuse.** Extend the first exact proposal
pipeline to rewrite scheduling and proved macro discovery; CM partitions/block
and GF(2) decompositions; BDD orders/AIG choices; and partial-context/version
specialization. Each gets a finite experiment and its own matched output contract,
not just a registry entry or imported backend.

**Milestone E — remaining model and application paths.** Exercise LLM proposals
and distillation when authorized; learning-method and efficiency ablations;
replayed bandits/sequential policies; SAT/#SAT guidance through exact adapters;
remaining subclasses, negative controls, and application families. Keep an honest
pending/blocked status where data, semantics, tooling, or authority is missing.

For each milestone deliver code, relevant tests, runnable commands/configs, model
and dataset manifests where applicable, raw measurements, a concise result report,
and an updated register. A track is measured only after its actual experiment
runs, including negative outcomes; scaffolding and fake-provider tests count only
as implementation tests. Completing one milestone is not completion of the whole
program. The eventual all-paths outcome requires an actual bounded evaluation for
each path, or my explicit acceptance of a documented infeasibility disposition.
While any path is merely planned, stubbed, unmeasured, or blocked, report that
remaining work plainly; a populated register alone does not complete the program.

Stay focused on working vertical slices. Keep progressing while useful authorized
work remains, but do not manufacture benchmark wins, run indefinitely, or claim
unexecuted paths are done. If an external dependency truly blocks the next work,
ask one grouped concrete question with the prepared package/budget details.

## 9. Verification and reporting

Existing focused command, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_recognition_research.py -v
```

The prior checkpoint passed 37 focused tests. Its relevant regression selection
passed 147 tests and 146 subtests using the available Python 3.10 pytest runtime;
pytest was absent from the project Python 3.13 virtual environment. These are
historical results, not current verification. Inspect interpreter/dependency
availability, then run the relevant selection without installing tools silently:

```powershell
python -B -m pytest -q -p no:cacheprovider tests/test_recognition_research.py tests/test_bitset_cse.py tests/test_share_aware_flatten.py tests/test_build_memo.py tests/test_expr_serde_v2.py tests/test_bitset_backend.py tests/test_prepared_flat_evaluation.py tests/test_bitset_engine_policy.py tests/test_expr_eval_module.py
```

Add tests for every new boundary: bit/variable alignment; transformed labels;
split leakage; train-only preprocessing; actual parameter updates; deterministic
seed replay within documented limits; save/load prediction agreement; malformed
weights and dimension limits; unavailable optional backends; verifier rejection
and timeout; rewrite cycles; stale/context-invalid reuse; LLM malformed/unsafe DSL
responses; no-network defaults; no-overwrite runs; interrupted training; learned
bypass; and all required accounting fields. Use speed measurements in reports,
not brittle unit-test assertions that one algorithm must always be faster.

At each handoff, report: implemented versus merely proposed capabilities;
verification commands/results; model sizes and actual learning performed;
dataset/split identities; overhead-inclusive wins and losses; unresolved evidence
limits; next runnable work; and the smallest grouped approval needed, if any.
Review git status/diff so unrelated changes are not attributed to this task.
Do not claim that tests on the research path certify Windows containment or
validate every historical benchmark on the website.

## 10. Research pointers and how to use this brief

Use the checked-in assessments first; verify primary papers and official package
documentation before adopting their methods or dependencies. Useful starting
points, not proofs of a CM speedup:

- DeepGate2, truth-function supervision for graph learning:
  https://arxiv.org/abs/2305.16373
- DeepGate3, hierarchical circuit representation:
  https://arxiv.org/abs/2407.11095
- NeuRewriter, learned local rewrite selection:
  https://arxiv.org/abs/1810.00337
- egg, exact equality-saturation infrastructure with admitted rules:
  https://arxiv.org/abs/2004.03082
- Feature-Budgeted Random Forest, feature acquisition cost:
  https://proceedings.mlr.press/v37/nan15.html
- SATzilla, algorithm portfolios:
  https://www.cs.ubc.ca/labs/algorithms/Projects/SATzilla/
- NeuroSAT, neural SAT representation/guidance precedent:
  https://arxiv.org/abs/1802.03685
- Ansor, learned cost modeling for compiler search:
  https://www.usenix.org/conference/osdi20/presentation/zheng
- Tensor Language Model, learned program generation for tensor optimization:
  https://www.usenix.org/conference/osdi24/presentation/zhai

Do not assume these packages are installed, safe to execute, appropriately
licensed for reuse, or the best current method. Inspect those facts separately.
The research menu is intentionally broader than any one paper or model family.

Begin by inspecting the current implementation and creating the complete track
register, then implement and verify the first missing vertical slice. Keep the
long-term neural/LLM agenda intact while producing concrete local results now.

---

Handoff drafting note: the outcome-first structure, explicit local-work authority,
single approval-boundary section, and evidence-based completion bars follow the
[official prompting guidance](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices).
This does not select a particular coding-agent model or LLM provider.
