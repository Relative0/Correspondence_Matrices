# CRSE — active computation-first workstream

## Current learning implementation follow-up — 2026-08-29

[Milestones A/B report](docs/recognition/LEARNING_MILESTONES_AB_2026_08_29.md),
[Milestone C report](docs/recognition/LEARNING_MILESTONE_C_2026_08_29.md), and
[all 18 research tracks](docs/recognition/experiment_register.json).
The foundation now includes retained feature ablations, a query-count rule and
an exact CM/cofactor teacher. Two small NumPy MLPs were actually trained,
saved/reloaded and evaluated with independent replacement checks. They were
slower than exact controls; the negative results are retained. The approved
isolated PyTorch path now trains matrix, CNN, GNN, fused, and contrastive graph
models. Its synthetic representation signal passed, retrieval missed its target,
and EPFL transfer was poor; no model is promoted. Live LLM work remains pending.

The remainder records the earlier checkpoint and its original pilot evidence.

Updated 2026-08-29 following the owner's explicit request to focus on local
comparisons and results, bypass the Windows software work for now, and commit
this task's work.

## Decision

Windows launcher, native containment tests, VM provisioning, and
Orchestrator-controlled execution are **deferred**, not completed. Their earlier
approval packets remain historical and unchanged. The local research program
does not call those components or require their workspace.create/v1 gate.

No VM, Docker, Runpod resource, worker service, or external effect was used.
Existing CM algorithms, execution routes, research deliverables, and unrelated
worktree edits were left unchanged. No new dependency was installed.

## Working software

[Guide and measurement contract](docs/recognition/README.md)

[Experiment entry point](scripts/cm_recognition_experiment.py)

The first slice trains a bounded decision tree to choose direct, structural-CSE,
or CM-IR-based exact evaluation. It compares that learned choice with fixed,
heuristic, and frozen exact-cache controls. It does not yet learn new rewrite
rules or replace Boolean semantics with predicted answers.

To run another local experiment from the repository root, select a new output
directory:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_recognition_experiment.py --run --output docs/recognition/runs/pilot-002
```

Omit --run for a configuration preview. No additional approval is required just
to continue this requested bounded local implementation/testing work; paid cloud
resources, uploads, production integration, and Git writes remain separate.

## First pilot: completed, no speedup established

Local artifacts: docs/recognition/runs/pilot-20260828-001/ (Git-ignored).

- 84 generated expressions: 48 train, 16 validation, 16 test, four held-out mux.
- 6/8/10-variable complete truth vectors; 1/8/64 recomputed queries per session.
- 1,080 successful timing measurements and 23,445 checked query outputs.
- Zero semantic mismatches; zero held-out hits in the frozen training-answer cache.
- The model was frozen before validation/test measurements; execution-source
  fingerprints remained unchanged during the run.
- Training selected CSE as the constant baseline. On the 16 test formulas the
  learned selector's geometric-mean speedup was 0.613, i.e. about 1.63 times the
  baseline runtime. Feature extraction and inference are included. The four
  family-held-out formulas likewise showed a slowdown (0.586 speedup).
- Training amortization was not established. These are tiny, exploratory,
  single-machine measurements, not an accepted performance result or a claim
  about large expressions. The negative result is retained rather than hidden.

The detailed local report, raw rows, corpus, model, and artifact manifest are
retained in that run directory. All five recorded artifact hashes were checked
independently after writing.

## Verification

- Project Python 3.13 virtual environment: 37 focused unittest tests passed.
- Existing Python 3.10 pytest environment: 147 tests plus 146 subtests passed
  across the new suite and eight relevant existing CM/CSE/serialization suites.
- The project virtual environment lacks pytest, so the focused suite also works
  with standard-library unittest. Ruff is unavailable in the checked Python
  environment; no lint result or full-repository test result is claimed.

## Learning investigation and checkpoint scope

[Learning diagnosis and exploratory feature ablations](docs/recognition/LEARNING_INVESTIGATION_2026_08_29.md)

[CM neural-learning assessment and proposed benchmark](docs/recognition/CM_NEURAL_BENCHMARK_ASSESSMENT_2026_08_29.md)

The current learner is a decision tree, not a neural network or compiled LLM.
The follow-up feature ablations ran only in memory and were not integrated.
Their aggregate results are preserved with that provenance limitation; a
reproducible follow-up must retain raw rows and candidate models.

The owner authorized a local Git checkpoint of this task's CRSE software, tests,
research notes, and previously untracked historical CRSE controller packets.
The historical packets retain their original bytes and statuses; committing
them neither executes their instructions nor grants any new native authority.
Unrelated research edits and generated run artifacts are outside this checkpoint.
No push, neural implementation, new training run, or cloud execution is implied.

The next scientific work is to replicate the cheap-feature result against an
equally cheap deterministic rule, then test certified motif/rewrite selection
with task-matched exact baselines. The Windows work is not a prerequisite.
