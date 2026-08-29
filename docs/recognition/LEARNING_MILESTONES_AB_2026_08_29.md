# CRSE learning: Milestones A/B, 2026-08-29

## Result

Implemented the missing foundation and a first actual neural comparison using
the existing CRSE software. **No learning speedup over the strongest relevant
deterministic controls was established.** All 18 tracks and eight application
families remain in the [experiment register](experiment_register.json).
The broader program is not complete.

The original 37 tests passed before changes. The expanded suite passed **63
tests** in the project Python 3.13 environment. The available Python 3.10 pytest
selection passed **173 tests and 146 subtests**. No dependency was installed.

## Implemented

- Feature-schema-bound query-only and query/depth trees, retaining the original
  full-feature tree, direct/CSE/CM backends and frozen training cache. An equally
  cheap fixed rule selects direct for Q <= 2 and CSE otherwise.
- Typed bounded task, proposal, scorer and exact-check contracts. Proposals
  retain source identity, provenance, side conditions, probability, node counts,
  rejection reason, evidence and timings. One switch bypasses learned advice.
- Exact CM/cofactor teacher with explicit partitions, assignment/bit order,
  valid masks, padding, transpose and input/output negation tests.
- Actual NumPy MLP training, train-only preprocessing, bounded hashed float32
  serialization, save/reload agreement, inference and exact evaluation.
- One independently verified affine replacement per request. Invalid, stale,
  cyclic/nonreducing, incorrect and timed-out proposals are rejected. Half the
  cooperative request budget is reserved for fallback; the total deadline can
  refuse a result. No hard OS deadline is claimed.
- Preview/dataset/train/evaluate/run CLI phases, raw rows, source/data/model
  hashes, pre-run manifests, incomplete records and an independent artifact audit.
- Bounded inert Boolean DSL and deterministic fake-provider tests. These are
  interface tests only; **no actual LLM experiment occurred**.

The existing engines, AST, DAG serialization, original admission guards and
production routes were not replaced. The teacher constructs dense local truth
input; the `cm` portfolio arm remains CM-IR simplification plus bigint execution.

## A: retained routing ablation

Run: [routing-ablation-20260829-002](runs/routing-ablation-20260829-002/report.md).
104 formulas: 48 train, 16 validation, 32 exploratory test and eight held-out mux;
4/6/8 ambient variables; Q=1/8/64; three paired rounds. CSE was the fixed baseline
selected from training measurements. There were 1,944 raw measurements, 44,910
checked query outputs and zero mismatches.

| Method | Test speedup vs CSE | p95 slowdown vs CSE |
| --- | ---: | ---: |
| Full-feature learned tree | 0.614 | 2.46 |
| Query-only learned tree | 1.162 | 1.27 |
| Query/depth learned tree | 0.795 | 1.88 |
| Fixed query-count rule | **1.564** | **1.09** |

The query-only tree is faster than CSE here but slower than the equally cheap
rule. This does not establish an advantage from learning. The ablation retains
the original structural/alpha split contract; semantic, commutative and
generating-template grouping are **not** claimed for this corpus. It is not a
confirmatory replication of the historical in-memory diagnostic.

Dataset canonical SHA-256:
`2d07dc6ddc2a16f5a1e5b9b9cf6866a3da6343e2532d53a09d9cb79f3251ccce`.
All fitted models and their feature projections/ranges are retained.

## B: trained neural motif comparison

Run: [affine-mlp-20260829-002](runs/affine-mlp-20260829-002/report.md).
208 formulas: 128 train, 32 validation, 32 exploratory test and 16 sealed
mechanism-confirmation cases. Every parent affine function has a one-bit
near-match. Source templates and variable-permutation/output-complement support
groups do not cross splits. Ambient count is eight; positive affine live-support
sizes are 1/2/3/5 for training, 4 for validation, 6 for test and 7 for confirmation.
Near-matches use all eight variables.

Dataset canonical SHA-256:
`c021ee0655add4a3765c943392ed45d05f27f734e225a031ec9d16bea2a9da0f`.

Two models were trained with seeds 20260829 and 20260830. Each has **65,793
parameters**, layers **512 -> 128 ReLU -> 1 sigmoid**, float32 weights, **40
epochs, batch size 32 and 160 SGD updates**. Input is 256 truth positions plus
256 validity-mask positions. Each saved JSON model is **360,371 bytes**; numeric
parameters occupy 263,172 bytes, excluding normalization/metadata. This is an
MLP, not a CNN/GNN.

Training cross-entropy changed from 0.7171 to 0.6772 and from 0.7300 to 0.6770.
Fit times were approximately 61.9 ms and 48.1 ms. Dataset generation/checks took
2.069 s; exact training-cost measurements/tree fitting took 0.392 s; the full
run took 7.212 s. No training amortization over exact controls is shown.
Models were frozen before validation/test/confirmation, with no test-dependent
tuning. Saved/reloaded predictions agreed. Scores are uncalibrated motif
probabilities, not authoritative truth values, proof, or profitability estimates.

| Method | Test speedup vs CSE, seed 20260829 | Seed 20260830 |
| --- | ---: | ---: |
| Direct exact execution | 1.409 | 1.405 |
| CSE exact execution | 1.000 | 1.000 |
| Deterministic CM-IR rewrite policy | 0.395 | 0.398 |
| Exact answer reuse within request | **1.656** | **1.658** |
| Exact affine detector plus checked replacement | 0.185 | 0.182 |
| Tiny measured-cost tree | 0.609 | 0.605 |
| Warm MLP plus checked replacement | **0.167** | **0.202** |
| MLP including model load | 0.030 | 0.033 |

Warm MLP test latency was about 6.0x and 4.9x CSE latency; p95 slowdowns were
12.74x and 12.30x. It failed the declared materiality/tail criteria. Building a
full CM already computes the answer, so direct/cache controls are essential.
No larger sweep was used to search for a favorable outcome.

All 3,840 evaluation rows succeeded: 85,152 checked query outputs, zero
mismatches. Across repeated rounds, both seeds, and warm/cold cells there were
468 accepted replacements (including the exact detector) and 228 semantic
rejections. An independent audit reconstructed and rechecked all these
candidates, and replayed 160 unique saved-model scores. These are not counts of
independent formulas.

## Evidence and timing limits

CM construction, tensor conversion, inference, candidate generation, required
acceptance proof, backend build and queries are inside primary totals. Cold
cells additionally load the model from a locally warm filesystem, not cold OS
startup. Common admission and after-the-fact output audits are outside all arms
equally. Memory has a separate tracemalloc allocation probe, not a process-RSS
or hard memory-bound claim. Q identical recomputations are not a natural session;
the exact-cache arm gets the same reuse opportunity. Full output still has 2^k
bits. Accepted equivalence proves one instance, not a rule over metavariables.

Only one held-out generating template/support cluster exists per neural split;
clustered intervals are unavailable for that stated reason. Two training seeds,
syntactic variants and timing rounds do not establish independent-source or
cross-machine replication. No natural application-family result is claimed.

The source PDF matched its supplied SHA-256. Pages 7/8/12 were text-inspected;
pages 7/8 were rendered and inspected. Teacher labels explicitly distinguish
ascending repository assignment order from the paper's displayed order. The
page-12 `(X implies Y) XOR (X OR Y) = NOT Y` correction is an executable test.

The [finite plan](learning_smoke_plan.json) records one artifact-only amendment
to include the routing pre-run spec in its hash manifest. Both `-001` runs remain
unchanged. Both `-002` runs used the same datasets, hyperparameters and policies,
new directories and 60-second limits. They are repeated measurements, **not
independent replication** or a selected best result. Both pairs had the same
negative learning conclusion.

[Machine summary](learning_milestones_ab_results.json) and
[independent audit](verification/learning-20260829-002.json) are small retained
records. Full raw data/models remain in ignored run directories. The audit
verified seven routing and ten neural artifact hashes, plus 51 execution-source
fingerprints for each run.
Raw output vectors are not stored; it rechecks functions, model predictions and
replacements, not historical nanosecond timings.

## Run and verify

Preview without writing/training:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_recognition_learning.py
.\.venv\Scripts\python.exe -B scripts/cm_recognition_experiment.py --feature-ablation --sizes 4,6,8
```

For a fresh run, use the finite plan's arguments with a new output directory.
Separate neural phases use `--phase dataset`, then `--phase train --input
<dataset-directory>`, then `--phase evaluate --input <trained-directory>`, each
with `--run` and a new `--output`. Imported datasets are bounded/revalidated;
trained model and evaluation dataset identities must match.

Verification performed:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_recognition_research.py -v
python -B -m pytest -q -p no:cacheprovider tests/test_recognition_research.py tests/test_bitset_cse.py tests/test_share_aware_flatten.py tests/test_build_memo.py tests/test_expr_serde_v2.py tests/test_bitset_backend.py tests/test_prepared_flat_evaluation.py tests/test_bitset_engine_policy.py tests/test_expr_eval_module.py
.\.venv\Scripts\python.exe -B scripts/crse_learning_verify.py docs/recognition/runs/routing-ablation-20260829-002 docs/recognition/runs/affine-mlp-20260829-002
```

Pytest is absent from the project virtual environment; the available Python 3.10
installation supplied it. No full-repository, Windows containment or historical
website-benchmark validation is claimed.

## Next work and authorization

Next is Milestone C's graph-learning comparison, then remaining transformation,
reuse, model and application paths. CNN/GNN/fused inputs, generalized rules,
adaptive learning, live LLMs and natural-source experiments are **not completed**.
PyTorch is absent from the project, pytest and bundled document runtimes. One
[optional dependency request](NEURAL_DEPENDENCY_REQUEST.md) specifies an isolated
environment, pinned CPU packages, licenses, download cap and finite next batch.
No installation has started. Existing NumPy work needs no additional approval.

Unrelated dirty research files were left untouched. No commit, push, deployment,
publication, upload, credential access, system installation or cleanup occurred.
