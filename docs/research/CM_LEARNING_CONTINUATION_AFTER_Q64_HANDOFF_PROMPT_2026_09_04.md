# Prompt for CM learning continuation after the frozen q64 Benchmark handoff

Work in:

`C:\Users\brian\Documents\CM_Computation`

This repository has a dirty shared working tree containing work from multiple tasks.
Preserve every existing tracked change and untracked file. Do not revert, clean,
reset, overwrite frozen artifacts, or stage unrelated work. Do not commit or push
unless separately requested after review. Do not run a paid/cloud job, create a
RunPod resource, consume prospective data, or change production routing without
explicit authorization for that exact action.

## Objective

Continue the CM learning investigation only if the Benchmark task has produced a
new, independently verified, two-physical-machine exact handoff for the already
frozen 72-case q64 source-blind cohort. Do not reproduce the Benchmark execution in
this task. Authenticate and consume its finished artifacts read-only.

The authoritative freeze is:

`docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001/FREEZE.json`

Its file SHA-256 is:

`3cf5c2672e01aae6130282f2ea1a65de32746597a59689605a2d913a675a0692`

Its independent status is `verified_source_blind_freeze_no_labels`. It contains 72
new cases, 40/16/16 source-group fit/validation/audit splits, zero prior
alpha-structural overlap, 13 identity-free model features, and no timings, labels,
models, prospective data, or cloud execution. Do not edit the freeze, its manifest,
verification, report, or any file in its source closure.

## Read first

Read these documents and their referenced machine artifacts completely:

1. `docs/research/CM_NEURAL_ARCHITECTURE_REASSESSMENT_2026_09_02.md`
2. `docs/research/CM_POST_BENCHMARK_NEURAL_ELIGIBILITY_2026_09_03.md`
3. `docs/research/CM_VERSION_HISTORY_LEARNING_PROTOCOL_2026_09_04.md`
4. `docs/research/CM_LEARNING_BENCHMARK_HANDOFF_CONTRACT_2026_09_04.md`
5. `docs/research/CM_QUERY_LADDER_DEVELOPMENT_LEARNING_EVALUATION_2026_09_04.md`
6. the Benchmark task's new report, freeze binding, raw evidence, manifests,
   independent verifications, cleanup evidence, and normalized handoff.

Inspect the current implementations and tests:

- `cmbench/recognition/learning_benchmark_handoff.py`
- `cmbench/recognition/query_ladder_learning_evidence.py`
- `cmbench/recognition/query_ladder_learning_freeze.py`
- `cmbench/recognition/query_ladder_development_experiment.py`
- `scripts/cm_learning_benchmark_handoff.py`
- `scripts/cm_query_ladder_development_experiment.py`
- `tests/test_learning_benchmark_handoff.py`
- `tests/test_query_ladder_learning_evidence.py`
- `tests/test_query_ladder_learning_freeze.py`
- `tests/test_query_ladder_development_experiment.py`

## Mandatory first gate

Locate the new Benchmark handoff without guessing which run is current. Verify its
manifest and independent-verification chain and then run the existing freeze-bound
readiness assessment. The handoff must establish all of the following:

- exact surface `architecture_query_ladder_q64`;
- exact freeze-file, task-contract, source-checkpoint, source-tree, case-set, and
  label-table bindings;
- exactly the frozen 72 source groups and 40/16/16 split counts;
- protocol frozen before labels, zero cross-split source overlap, and zero
  prospective cases consumed;
- all eight frozen exact arms, including unfavorable/refused rows;
- task-identical exact outputs and sum-based per-case median economics;
- at least two independently verified replications on distinct physical machines;
- the same cases and joint label table on both machines;
- zero schedule, semantic, source, artifact, or verification mismatches;
- same-host p95 feature/control, bounded inference, exact verification, fallback
  dispatch, and abstention-regret charges;
- at least two non-abstaining labels with at least eight source groups each; and
- gross and fully charged oracle headroom of at least `1.10x` on every host.

Use:

```powershell
.\.venv\Scripts\python.exe scripts\cm_learning_benchmark_handoff.py `
  --handoff <new-verified-handoff.json> `
  --freeze docs\recognition\runs\query-ladder-source-blind-learning-freeze-20260904-001\FREEZE.json
```

If the result abstains, stop the learning execution. Report the exact blockers and
what evidence would resolve them. Do not fit a selector, train a neural model,
consume a substitute cohort, weaken a threshold, impute a missing cost, relabel the
already inspected 54-case cohort, or synthesize a label table from different runs.

## If and only if the exact gate passes

### 1. Materialize the authenticated development label table

Build the `crse-query-ladder-labeled-development-dataset/v1` document strictly from
the verified Benchmark label table and frozen cohort. It must contain each frozen
case exactly once with only:

- `case_id` for evaluator binding, never as a model feature;
- frozen source-group SHA-256 for split auditing, never as a model feature;
- the frozen split;
- the byte-identical 13-value `model_features`; and
- the joint cross-host exact-arm label or `__abstain__`.

Bind its case set, label-table hash, records digest, and freeze file hash. Retain all
abstentions for economics and exclude them from fit. Run the existing dataset
validator before any fitting callback can execute.

### 2. Run deterministic controls before neural work

Evaluate, in this order:

1. the pre-frozen ultra-cheap analytical control;
2. the best fixed exact arm;
3. a deterministic majority-label diagnostic, clearly marked non-routing;
4. a bounded-depth/size cost tree using only the 13 features; and
5. a small regularized linear or multinomial model using only the 13 features.

Fit only `development_fit`. Use `development_validation` only for predeclared
hyperparameter selection and threshold calibration. Lock the candidate and all
thresholds before reading `development_audit` labels. Never expose validation or
audit labels to the fitter. Preserve model/version/seed/configuration hashes and
record every attempted configuration so a failed path is not silently discarded.

### 3. Apply the precommitted signal criteria

On validation and audit independently require:

- every non-abstaining development label is represented;
- balanced accuracy at least `max(0.65, class-balanced chance + 0.15)`;
- ordinary accuracy at least `0.10` above the split's majority-class accuracy;
- balanced accuracy at least `0.03` above the frozen analytical control; and
- non-abstain prediction coverage at least `0.80`.

Candidate abstention counts as an incorrect classification and reduces coverage.
Report per-class recall, confusion matrices, class support, majority accuracy,
balanced chance, analytical-control accuracy, and analytical-control balanced
accuracy. Do not use “better than a coin toss” without this complete context.

Use `cmbench.recognition.query_ladder_development_experiment` to recompute the
assessment. A passing classification result is development evidence only, not an
economic or production result.

### 4. Neural work is last and remains bounded

Only consider a tiny neural candidate if:

- the exact fully charged handoff passed;
- at least one deterministic learned control established a real signal;
- the remaining measured inference budget can still preserve `1.10x`; and
- a neural model has a concrete task advantage that the bounded controls cannot
  express.

Keep inputs to the same 13 frozen features unless a new pre-label freeze explicitly
authorizes another representation. Do not reopen C5 or train on mathematical CM/
truth matrices merely because Torch is available; those are different tasks and C5
remains a frozen negative artifact. Predeclare architecture, parameter cap, optimizer,
epochs, seeds, and stopping rule. Require at least three distinct seeds. Every seed
must independently pass every validation and audit signal criterion. One failing
seed rejects the replicated neural signal; do not report only the best seed.

### 5. Recompute actual routed economics

For every surviving candidate, independently verify a
`crse-query-ladder-development-routing-evidence/v1` document containing all 72 by 8
per-case exact-arm medians and same-host candidate-inference/fallback timing for both
physical-machine replications. Bind it to the freeze, label table, prediction rows,
machine identities, and both independent verifications.

Use:

```powershell
.\.venv\Scripts\python.exe scripts\cm_query_ladder_development_experiment.py `
  --freeze docs\recognition\runs\query-ladder-source-blind-learning-freeze-20260904-001\FREEZE.json `
  --handoff <new-verified-handoff.json> `
  --dataset <verified-development-labels.json> `
  --predictions <locked-candidate-predictions.json> `
  --routing-evidence <verified-candidate-routing-evidence.json> `
  --output <candidate-development-assessment.json>
```

The evaluator must replay the handoff's best-fixed and oracle sums from the exact
median table. It charges selected-arm runtime, wrong-arm regret, feature/control,
actual candidate inference, exact verification, fallback dispatch, and abstention
regret. Cross-host-unstable labels must abstain. Require on every host:

- candidate fully charged speedup at least `1.10x`; and
- candidate fully charged total strictly better than the frozen analytical control.

Perfect classification with excessive inference cost must fail. Do not replace
candidate runtime with oracle runtime or reuse timing costs between hosts.

### 6. Preserve the claim boundary

Even a complete pass permits only a development conclusion. Do not consume a new
prospective corpus, enable advice, change the exact fallback, promote a model, alter
production routing, or claim external confirmation. Those require a separately
frozen prospective protocol and explicit authorization.

## Artifacts and independent verification

Create a new run directory; never overwrite an existing run. Bind inputs, source
state, environment, models, predictions, timing samples, assessment, report, and
manifest. Add a separate verifier that replays hashes, split isolation, feature
closure, prediction metrics, exact sums, and charged economics without relying on
the producer's derived conclusions. Verification must fail on a changed label,
feature, split, seed, prediction, timing, cost, machine identity, or claim boundary.

Record explicitly:

- models attempted and trained;
- prospective cases consumed;
- exact benchmark executions performed by this learning task (expected zero);
- cloud resources created (expected zero unless separately authorized);
- advice/routing/fallback status; and
- whether each result is retrospective, source-blind development, or prospective.

## Tests

Add focused tests for any new implementation and rerun the existing learning/gate
suite. At minimum cover:

- missing/tampered/mismatched Benchmark evidence;
- freeze, case, label-table, and source-tree mismatch;
- feature/identity/timing leakage;
- source-group split overlap;
- validation or audit labels reaching fit;
- abstentions excluded from fitting but retained in economics;
- majority/constant predictors rejected;
- analytical-control margin and coverage failures;
- duplicate or unstable neural seeds;
- actual candidate inference erasing perfect-predictor headroom;
- cross-host cost reuse;
- exact median/economics tampering;
- callback non-invocation when any gate fails; and
- unchanged exact fallback and production prohibition.

Use `.venv` for non-Torch tests and `.venv-crse-neural` only if an authorized neural
experiment actually occurs. Report missing tools rather than installing or hiding
them.

## Final handoff

Lead with one of three outcomes:

1. `abstained before fit`, with exact blockers;
2. `deterministic development signal only`, with validation/audit and charged
   economics; or
3. `replicated neural development signal only`, with every seed and every host.

State exactly what was read, generated, trained, timed, and verified; what was not
done; every negative result; the unchanged production boundary; tests and counts;
artifact paths and SHA-256 values; and a clean separation between this task's files
and unrelated dirty worktree content.
