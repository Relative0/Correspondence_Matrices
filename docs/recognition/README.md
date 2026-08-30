# CRSE: computation-first local research

## Scope decision — 2026-08-28

The owner explicitly asked to defer the Windows software/VM work and build
software that runs computational comparisons, like the Correspondence Matrix
experiments in this repository. This is the active scope for this research path.

The earlier Orchestrator product-pilot packets and WCP native-launcher work are
historical, separate workstreams. They are not prerequisites for this manually
invoked local experiment. We are not executing or weakening their gates, claiming
their native tests passed, or calling workspace.create/v1. No historical prompt,
approval hash, controller source, or production route is changed.

Deferred: Windows launcher, process containment/fault injection, VM provisioning,
Orchestrator-controlled execution, automated worker launching, general cloud
execution, packaging/deployment, and production promotion. D8 is one explicitly
authorized bounded Linux confirmation, not a cloud product path. Docker and a VM
are not needed.

## What is implemented

Current implementation: [Milestones A/B and measured results](LEARNING_MILESTONES_AB_2026_08_29.md),
[Milestone C graph-learning results](LEARNING_MILESTONE_C_2026_08_29.md), and
[Milestone C2 variable-size decomposition results](LEARNING_MILESTONE_C2_2026_08_29.md),
[Milestone C3 natural arbitrary-partition decomposition](LEARNING_MILESTONE_C3_NATURAL_DECOMPOSITION_2026_08_29.md),
[Milestone C4 direct-cut and pair-ranking results](LEARNING_MILESTONE_C4_DIRECT_CUT_RANKING_2026_08_29.md),
[Milestone C5 variable-conditioned equivariant cuts](LEARNING_MILESTONE_C5_VARIABLE_CONDITIONED_CUT_2026_08_29.md), and
[Milestone C6 packed exact source ANF](LEARNING_MILESTONE_C6_PACKED_SOURCE_ANF_2026_08_30.md), plus
[Milestone D task-computation results](LEARNING_MILESTONE_D_2026_08_29.md) and
[Milestone D2 proved-rule reuse](PROVED_RULE_MILESTONE_D2_2026_08_29.md), followed
by [Milestone D3 versioned rule caching](VERSIONED_RULE_CACHE_MILESTONE_D3_2026_08_29.md),
[Milestone D4 profitability gating](RULE_PROFITABILITY_MILESTONE_D4_2026_08_29.md),
[Milestone D5 natural EPFL evaluation](NATURAL_RULE_PROFITABILITY_MILESTONE_D5_2026_08_29.md),
[Milestone D6 actual configuration revisions](NATURAL_REVISION_CACHE_MILESTONE_D6_2026_08_29.md),
[Milestone D7 bounded multi-pass normalization](NATURAL_NORMALIZATION_MILESTONE_D7_2026_08_29.md),
[Milestone D8 frozen Linux confirmation](LINUX_ONE_PASS_CONFIRMATION_MILESTONE_D8_2026_08_29.md),
[Milestone D9 frozen calibrated profitability policy](NATURAL_PROFITABILITY_POLICY_MILESTONE_D9_2026_08_29.md),
[Milestone E1 bounded BDD order selection](LEARNING_MILESTONE_E1_BDD_ORDER_SELECTION_2026_08_30.md),
and [Milestone E2 exact SAT/equivalence guidance](LEARNING_MILESTONE_E2_SAT_EQUIVALENCE_GUIDANCE_2026_08_30.md).
The [complete register](experiment_register.json) preserves all 18 research tracks;
the [roadmap](LEARNING_ROADMAP.md) distinguishes measured slices from pending work.
There is a trained NumPy MLP path with independent exact acceptance, retained
feature ablations and a query-count rule. The optional isolated PyTorch path now
trains and reloads matrix MLP, CNN, graph GNN, fused, and graph-retrieval models.
Its generated-data representation signal passed, retrieval missed its threshold,
and transfer to a real all-negative EPFL slice was poor. No model is promoted;
broader graph/hierarchical work and live-LLM experiments remain pending.
Milestone C2 adds an exact balanced-cofactor XOR-decomposition teacher, mixed
n=4/6/8 training, held-out n=10 confirmation, validation-only calibration, a
shared multiscale CM control, and canonical factor witnesses. Its independent
verifier recomputed 192 scalar truth tables and 768 model decisions without
error. The learned representation and size-transfer criteria both failed,
while the exact CM detector remained perfect; the EPFL slice again contained
no target positives.
Milestone C3 scouts the full local EPFL BLIF suite and finds 894 exact positives
and 8,166 negatives for arbitrary XOR decomposition over discovered variable
partitions. It freezes 188 balanced, circuit-disjoint natural cones across 4-10
variables, trains graph and multitask models with exact ANF interaction targets,
adds a validation-only minimum-cut decoder, and repeats with 94 same-circuit
structure-matched pairs. All three independent verifiers passed with zero
semantic mismatches. Learned classification, exact-partition recall, and the
structure-matched criteria failed, so exact ANF remains the accepted control.
Milestone C4 replaces independent edge decoding with direct supervision of the
complete canonical variable cut and adds same-circuit pair ranking. Two graph
arms and a structural ranker trained under two new seeds. Pair ordering was
strong on the confirmatory circuits but did not transfer to the held-out square
circuit; accepted graph-positive recall stayed at 0.000-0.222. Charged graph
proposal plus exact acceptance was 4.6-6.0x slower than exact ANF. Independent
replay passed with zero semantic mismatches, and no learned arm is promoted.
Milestone C5 adds bidirectional messages and a shared per-variable cut head with
exact non-anchor permutation equivariance. The no-ranking arm improved
confirmatory BA to 0.750-0.778 and accepted recall to 0.222-0.333, but held-out
square results remained weak and the learned path was 6.3-9.2x slower than exact
ANF. A new exact symbolic source-DAG ANF control achieved perfect recognition
and 1.22-1.58x median gains, but a 63.7 ms confirmatory p95 tail blocked its cost
criterion. The next work is a cached, bitset, budgeted symbolic hybrid.
Milestone C6 packs the complete bounded ANF coefficient vector into one Python
integer and evaluates exact Boolean polynomial products with GF(2) subset
transforms. On the frozen EPFL splits, the packed and cached cores achieved
1.28-1.64x median and 1.80-2.18x p95 speedups over truth-vector ANF. The
validation-frozen fallback gate preserved 11 exact fallbacks and zero semantic
mismatches, but missed confirmatory p95 by 1.4%. The packed core advances; the
gate and production path do not.
Milestone D now measures complete-vector, point, restriction and repeated-vector
requests through direct, CSE, CM-IR and explicit dense-CM paths. Its fitted
task/query router helped restrictions and repeated work but slowed complete
vectors; exact caching was the strongest reuse control, while dense-CM
construction and per-instance rewrite proof were negative results.
Milestone D2 proves one AIG-XOR identity over metavariables, compiles a bounded
sharing-preserving matcher, and compares repeated reuse against explicit CM
proof at every site. It was exact and faster than repeated CM proof, but slower
than the no-rewrite CSE control, so no rewrite is promoted.
Milestone D3 adds a proved De Morgan OR rule, deterministic overlap priority,
and exact per-cone cache invalidation across three generated DAG versions. The
cache was about 2.1x faster than fresh rematching on sparse changed versions,
but the no-rewrite CSE control remained faster.
Milestone D4 adds a proved common-factor rule, a task/reuse/size gate, serialized
cache provenance, additions/removals/reverts, and adversarial collision, pack,
and capacity checks. The gate was 1.366x faster than fresh matching but only
0.891x versus no rewrite on generated eight-variable cones; the cached oracle
had just 1.7% headroom.
Milestone D5 freezes that gate on 32 nonoverlapping natural EPFL cones at support
9-12. Across three repeated sessions it achieved 1.030x versus no rewrite and
1.517x versus fresh matching. Cold use lost while warm sessions gained
1.156-1.168x. This small one-machine result is not promoted.
Milestone D6 uses 120 bounded relations from 20 actual adjacent feature-model
transitions. Exact identity produced 41 safe hits and 79 invalidations, but the
cached CM path was only 1.015x over fresh CM and about 10.94x slower than direct
conditioned-CNF evaluation.
Milestone D7 adds strict multi-pass termination, exact cycle checks and overlap
refusal. It exposed 18 factoring applications after lowering, but fixpoint lost
to both one pass and no rewrite. One pass achieved 1.050x at 128 executions on
the reused D5 slice. D8 reran that frozen one-pass contract on Linux. Exactness
and rule incidence reproduced, but profitability did not: one pass achieved only
0.929x versus no rewrite. Unconditional one-pass rewriting is not promoted.
Milestone D9 trains a bounded cost policy only on circuit-disjoint depth/control
BLIF and freezes it before loading the size/evaluation split. It preserved zero
mismatches and correctly abstained on all 33 evaluation workloads. Exact factoring
reduced CSE operations, but unconditional one pass measured 0.429x and the charged
all-abstain gate measured 0.982x versus no rewrite. The mechanism passed; rewrite
profitability and production promotion did not.
Milestone E1 adds exact reloadable BDD artifacts, restriction and equivalence
queries, four deterministic/search order controls, and a bounded cost tree. The
first-occurrence order led; charged search and learned selection were negative.
Milestone E2 adds an exact expression-to-CNF adapter, trusted CaDiCaL SAT/UNSAT
sessions, verified witnesses and cores, safe version invalidation, deterministic
phase/order controls, and a bounded fresh-versus-resident policy. All 2,080
measurement and task-comparison rows were exact, but the learned arm was 1.0420x
the sealed best fixed action. The local second-machine gate failed, so no cloud
resource was used and no solver policy was promoted.

The guide below describes the original routing pilot, which remains available
unchanged by default. Use `--feature-ablation` for the optional routing arms.
The NumPy neural entry point is `scripts/cm_recognition_learning.py`, also
preview-only unless `--run` and a new `--output` are supplied. The explicitly
optional PyTorch entry point is `scripts/cm_recognition_neural.py` and must be run
with `.venv-crse-neural/Scripts/python.exe` and a new output directory.
The default-environment Milestone D entry point is
`scripts/cm_recognition_computation.py`; it immediately runs the finite
task-computation benchmark and refuses an existing output directory.
The D2 entry point is `scripts/cm_recognition_rules.py`; it runs the fixed
proved-rule comparison and likewise refuses an existing output directory.
The D3 entry point is `scripts/cm_recognition_versioned_rules.py`; it runs the
three-version rule-pack cache comparison.
The D4 entry point is `scripts/cm_recognition_rule_profitability.py`; it runs the
generated gate and cache-hardening comparison. The D5 entry point is
`scripts/cm_recognition_natural_rules.py`; it runs the sealed natural EPFL
repeated-session comparison. D6 uses `scripts/cm_recognition_natural_revisions.py`
for the audited configuration-history cache comparison. D7 uses
`scripts/cm_recognition_normalization.py` for the bounded fixpoint comparison.
The immutable D8 protocol, upload manifest, retained Linux evidence and final
Runpod reconciliation are under `docs/recognition/linux_confirmation`.
The D9 entry point is `scripts/cm_recognition_natural_profitability_policy.py`;
its independent verifier is `scripts/crse_natural_profitability_policy_verify.py`.
The E1 entry point is `scripts/cm_recognition_bdd_order.py`. The E2 entry point
is `scripts/cm_recognition_sat_guidance.py`; pass `--verify` with a retained run
directory to replay its artifact hashes, decisions, and trusted solver contract.
The C2 entry point is `scripts/cm_recognition_variable_decomposition.py`; it
uses `.venv-crse-neural/Scripts/python.exe` and a fresh output directory. Its
independent verifier is `scripts/crse_variable_decomposition_verify.py`.
The C3 natural and structure-matched entry points are
`scripts/cm_recognition_natural_decomposition.py` and
`scripts/cm_recognition_natural_decomposition_matched.py`; the frozen decoder
follow-up is `scripts/cm_recognition_natural_decomposition_decoder.py`.
The C4 entry point is `scripts/cm_recognition_natural_cut_ranking.py`; its
independent verifier is `scripts/crse_natural_cut_ranking_verify.py`.
The C5 entry point is `scripts/cm_recognition_natural_variable_cut.py`; its
independent verifier is `scripts/crse_natural_variable_cut_verify.py`.
The C6 entry point is `scripts/cm_recognition_natural_source_anf.py`; its
independent verifier is `scripts/crse_natural_source_anf_verify.py`.

Research follow-ups:

- [Learning diagnosis and feature-cost ablations](LEARNING_INVESTIGATION_2026_08_29.md).
- [CM neural-learning assessment and proposed benchmark](CM_NEURAL_BENCHMARK_ASSESSMENT_2026_08_29.md).

These historical notes distinguish the original decision-tree pilot from its
then-exploratory diagnostics and proposed neural work; the implemented follow-up
and current limitations are in the Milestones A/B report above.

This first research slice learns **which exact computation strategy to use**.
The later D2 slice admits one manually specified proved identity; it does not
yet discover rules or learn to output truth values.

The program generates Boolean expressions, measures three exact implementations,
fits a small cost-sensitive decision tree, freezes it, and evaluates it on unseen
expressions. A separate family is completely withheld from training/validation.

The three algorithms all return the same complete packed truth vector:

| Algorithm | Work performed |
| --- | --- |
| direct | Raw expression evaluation over packed integer variable columns |
| cse | Structural common-subexpression elimination plus sharing-aware flattening, then the bigint executor |
| cm | CM canonicalization/simplification, then the same bigint executor |

CSE is the existing strong structural-reuse baseline, not the known weak
no-CSE ablation. The CM arm measures CM IR simplification, not construction of a
dense correspondence matrix. These results do not cover every CM/BDD/solver path.

Additional evaluation controls are a predeclared structural heuristic, the best
constant algorithm selected using training data only, and an exact-answer cache
containing training formulas only. The cache is frozen during evaluation.

The learner uses variable count, query count, node count/depth, sharing,
operator proportions, identical children, and complementary children. It stores
only thresholds and mean relative costs. The model contains neither training
expressions nor answers; it can choose a strategy for feature vectors never seen
in training. Out-of-range inputs and insufficient predicted gain use the
training-selected constant fallback. Range checks are not calibrated confidence
or a guarantee of good choices on novel distributions.

## Run locally

From the repository root, preview the bounded configuration (no experiment or
result writes):

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_recognition_experiment.py
```

Run the initial generated-corpus experiment, choosing a **new** output directory:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_recognition_experiment.py --run --output docs/recognition/runs/pilot-001
```

Run another approved optional PyTorch representation experiment only with the
isolated environment and another new output directory:

```powershell
.\.venv-crse-neural\Scripts\python.exe -B scripts/cm_recognition_neural.py --output docs/recognition/runs/neural-new-id
```

Run and verify a fresh variable-size exact-decomposition experiment:

```powershell
.\.venv-crse-neural\Scripts\python.exe -B scripts/cm_recognition_variable_decomposition.py --output docs/recognition/runs/variable-decomposition-new-id
.\.venv-crse-neural\Scripts\python.exe -B scripts/crse_variable_decomposition_verify.py docs/recognition/runs/variable-decomposition-new-id --output docs/recognition/verification/variable-decomposition-new-id.json
```

Run and verify fresh natural arbitrary-partition, decoder, and structure-matched
experiments using new output paths:

```powershell
.\.venv-crse-neural\Scripts\python.exe -B scripts/cm_recognition_natural_decomposition.py --output docs/recognition/runs/natural-decomposition-new-id
.\.venv-crse-neural\Scripts\python.exe -B scripts/crse_natural_decomposition_verify.py docs/recognition/runs/natural-decomposition-new-id --output docs/recognition/verification/natural-decomposition-new-id.json
.\.venv-crse-neural\Scripts\python.exe -B scripts/cm_recognition_natural_decomposition_decoder.py --base docs/recognition/runs/natural-decomposition-new-id --output docs/recognition/runs/natural-decomposition-decoder-new-id
.\.venv-crse-neural\Scripts\python.exe -B scripts/crse_natural_decomposition_decoder_verify.py docs/recognition/runs/natural-decomposition-decoder-new-id --output docs/recognition/verification/natural-decomposition-decoder-new-id.json
.\.venv-crse-neural\Scripts\python.exe -B scripts/cm_recognition_natural_decomposition_matched.py --output docs/recognition/runs/natural-decomposition-matched-new-id
.\.venv-crse-neural\Scripts\python.exe -B scripts/crse_natural_decomposition_matched_verify.py docs/recognition/runs/natural-decomposition-matched-new-id --output docs/recognition/verification/natural-decomposition-matched-new-id.json
```

Run and verify a fresh direct-cut and same-pair ranking experiment:

```powershell
.\.venv-crse-neural\Scripts\python.exe -B scripts/cm_recognition_natural_cut_ranking.py --output docs/recognition/runs/natural-cut-ranking-new-id
.\.venv-crse-neural\Scripts\python.exe -B scripts/crse_natural_cut_ranking_verify.py docs/recognition/runs/natural-cut-ranking-new-id --output docs/recognition/verification/natural-cut-ranking-new-id.json
```

Run and verify a fresh variable-conditioned cut and source-symbolic comparison:

```powershell
.\.venv-crse-neural\Scripts\python.exe -B scripts/cm_recognition_natural_variable_cut.py --output docs/recognition/runs/natural-variable-cut-new-id
.\.venv-crse-neural\Scripts\python.exe -B scripts/crse_natural_variable_cut_verify.py docs/recognition/runs/natural-variable-cut-new-id --output docs/recognition/verification/natural-variable-cut-new-id.json
```

Run and verify a fresh packed exact source-ANF comparison:

```powershell
.\.venv-crse-neural\Scripts\python.exe -B scripts/cm_recognition_natural_source_anf.py --output docs/recognition/runs/natural-source-anf-hybrid-new-id
.\.venv-crse-neural\Scripts\python.exe -B scripts/crse_natural_source_anf_verify.py --run docs/recognition/runs/natural-source-anf-hybrid-new-id --output docs/recognition/verification/natural-source-anf-hybrid-new-id.json
```

Run a fresh bounded Milestone D task-computation experiment with the default
project environment and a new output directory:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_recognition_computation.py --output docs/recognition/runs/computation-new-id
```

Verify its retained hashes, exact workload outputs, fitted policy, rewrite
decisions, and learned bypass independently:

```powershell
.\.venv\Scripts\python.exe -B scripts/crse_computation_verify.py docs/recognition/runs/computation-new-id --output docs/recognition/verification/computation-new-id.json
```

Run and verify a fresh bounded proved-rule comparison:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_recognition_rules.py --output docs/recognition/runs/rule-new-id
.\.venv\Scripts\python.exe -B scripts/crse_rule_verify.py docs/recognition/runs/rule-new-id --output docs/recognition/verification/rule-new-id.json
```

Run and verify a fresh versioned rule-pack cache comparison:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_recognition_versioned_rules.py --output docs/recognition/runs/versioned-rule-new-id
.\.venv\Scripts\python.exe -B scripts/crse_versioned_rule_verify.py docs/recognition/runs/versioned-rule-new-id --output docs/recognition/verification/versioned-rule-new-id.json
```

Run and verify fresh generated and sealed-natural profitability comparisons:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_recognition_rule_profitability.py --output docs/recognition/runs/rule-profitability-new-id
.\.venv\Scripts\python.exe -B scripts/crse_rule_profitability_verify.py docs/recognition/runs/rule-profitability-new-id --output docs/recognition/verification/rule-profitability-new-id.json
.\.venv\Scripts\python.exe -B scripts/cm_recognition_natural_rules.py --output docs/recognition/runs/natural-rule-new-id
.\.venv\Scripts\python.exe -B scripts/crse_natural_rule_verify.py docs/recognition/runs/natural-rule-new-id --output docs/recognition/verification/natural-rule-new-id.json
.\.venv\Scripts\python.exe -B scripts/cm_recognition_natural_revisions.py --output docs/recognition/runs/natural-revision-new-id
.\.venv\Scripts\python.exe -B scripts/crse_natural_revision_verify.py docs/recognition/runs/natural-revision-new-id --output docs/recognition/verification/natural-revision-new-id.json
.\.venv\Scripts\python.exe -B scripts/cm_recognition_normalization.py --output docs/recognition/runs/natural-normalization-new-id
.\.venv\Scripts\python.exe -B scripts/crse_normalization_verify.py docs/recognition/runs/natural-normalization-new-id --output docs/recognition/verification/natural-normalization-new-id.json
```

The optional PyTorch command performs actual bounded training immediately; it
has no preview mode. The retained `neural-20260829-001` run already consumed one of
the three
approved manual experiment slots. Verify a completed run separately with
`scripts/crse_neural_verify.py`. Do not tune on the retained EPFL evaluation
slice and relabel the result as confirmation.

On Linux, use the same scripts with compatible isolated interpreters. No research
entry point calls Docker, Runpod, a launcher, or the network. The default path
uses the repository's existing NumPy dependency. The optional path lazy-imports
the pinned PyTorch CPU environment recorded in the dependency manifest; it does
not alter default imports or install packages at runtime.

Useful parameters: --sizes 6,8,10, --query-counts 1,8,64, --rounds 3,
--train-per-family 12, --validation-per-family 4, --test-per-family 4,
--held-out-family mux, --seed 20260828, --max-seconds 120.

The default has 48 training, 16 validation, 16 in-distribution test, and four
family-held-out expressions. Hyperparameters and the heuristic are predeclared;
validation/test timings never enter fitting. Validation is diagnostic in this
first slice, not a tuning search. Re-running with modified settings after seeing
results is exploratory, not a fresh independent replication.

Outputs:

- report.md: readable comparison, including slowdowns.
- raw.csv: every measurement, randomized execution order, selected backend,
  feature/inference time, status, and exact-check outcome.
- corpus.json: generated formulas in the existing v2 DAG format, split/group IDs,
  declared output universes, and query counts.
- model.json: bounded, non-executable JSON decision tree.
- summary.json: environment, settings, source fingerprints, timing contract,
  case-level reference checks, training cost, model/corpus hashes, and summaries.
- manifest.json: raw hashes of all output artifacts.

Outputs in docs/recognition/runs are locally retained and Git-ignored. Nothing
deletes, replaces, uploads, or promotes them. An existing output directory is
refused. A stopped/failed pilot must not be described as a successful experiment.

## Measurement contract

One measured session is: start with an admitted AST, select an algorithm if
needed, compile/bind a fresh program, and execute it Q times. Outputs are
recomputed each time; a repeated query is not an answer-cache lookup. There is no
persistent program/result cache in the exact algorithm arms. All arms share a
warm cache of input variable masks. This is **not** cold process startup or a
persistently precompiled multi-session benchmark.

The learner and heuristic pay for feature extraction and selection inside their
timed window. The exact-cache control pays for its lookup hash and any fallback
computation. The constant baseline is the measured cost of its fixed algorithm;
it needs neither inference nor a feature walk. Common input admission, corpus
generation, module import, reference construction, and correctness audits are
outside all algorithm windows. Common mask setup and reference/audit costs are
recorded separately. A later learned rewrite would also have to pay for its
required semantic verification **inside** its end-to-end cost; this selector
does not make learned semantic proposals.

Each output of each query must match the independent NumPy AST interpreter.
Operator semantics are additionally tested against the existing truth-table
implementation. Any disagreement or backend failure invalidates the pilot;
the failing rows are retained and no production output is consumed.

Formula groups, not timing rows, are split. Exact and variable-renamed structural
duplicates are removed across all splits (even across variable universes and
query counts). This is not full semantic deduplication, commutative canonical
grouping, or a guarantee that no mathematical motif appears in both partitions.
The mux family is withheld by default as an additional distribution-shift test.

Rounds are randomized per formula, then summarized by per-formula medians.
Reported speedup is fixed-training-baseline time divided by method time; values
below one mean a slowdown. p95/max slowdown, >=2x choices, and regret versus the
optimistic virtual-best portfolio are also reported, by split and family.
More rounds are not more independent formulas. This small generated pilot has
no publication-grade confidence intervals or cross-machine evidence.

Dataset construction/measurement and model-fit costs are not hidden: training
wall time and fit time are separate, with an observed amortization estimate only
when the held-out aggregate saves time. That estimate is not a deployment claim.

## Bounds and remaining work

The experiment admits at most 16 output variables, 4,096 identity nodes, depth
96, 50,000 unfolded nodes, 8,388,608 reference cells, and 256 repeated queries.
Counts and rounds are bounded. A configured corpus that exceeds these limits is
refused, not silently filtered. Time checks are cooperative between bounded
calls, **not** a hard wall-time/memory sandbox. This is intentionally ordinary
local scientific software, not an untrusted-code execution service.

A complete truth vector still has 2^n bits. This pilot is not evidence of fast
complete enumeration for hundreds of variables. Large-expression work will need
task-specific compact outputs: evaluation under assignments, equivalence checks,
counting under explicit limits, or certified reduced representations.

Next scientific extensions, based on observed opportunity:

1. Measure larger/independently sourced workloads with fixed task/output contracts.
2. Add certified motif proposals (XOR/affine, mux, decomposition) with exact
   acceptance checks, comparing against deterministic motif detectors.
3. Learn rewrite profitability or generalized rules with proof admission; do not
   substitute an approximate model answer for a Boolean proof.
4. Add task-matched BDD/SAT/counting and word-vector backends, then query-count
   break-even and cross-machine replication.

No speedup is assumed. A small oracle opportunity or a slower learned selector
is a useful negative result and a reason to keep the deterministic algorithm.

## Tests

The focused suite uses standard-library unittest, so it works in the existing
project virtual environment even when pytest is absent:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_recognition_research.py -v
```

It is also pytest-compatible. Existing CM/CSE regression tests remain separate
and unchanged. No commit, push, cloud resource, dependency installation, or
Windows-native effect is implied by running this experiment.
