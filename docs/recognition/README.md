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
Orchestrator-controlled execution, automated worker launching, cloud execution,
packaging/deployment, and production promotion. Docker and a VM are not needed.

## What is implemented

Research follow-ups:

- [Learning diagnosis and feature-cost ablations](LEARNING_INVESTIGATION_2026_08_29.md).
- [CM neural-learning assessment and proposed benchmark](CM_NEURAL_BENCHMARK_ASSESSMENT_2026_08_29.md).

These distinguish the implemented decision-tree pilot from exploratory
in-memory diagnostics and neural experiments that are only recommendations.

This first research slice learns **which exact computation strategy to use**.
It does not yet discover new Boolean identities or learn to output truth values.

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

On Linux, use the same script with the project's Python interpreter. No code in
this research package calls Docker, Runpod, a shell, a launcher, or the network.
NumPy is the only non-standard dependency; it is already used by this repository.

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
