# Prompt for a separate CM learning and neural evidence website task

Work in:

`C:\Users\brian\Documents\CM_Computation`

This is a shared, dirty working tree with work from multiple tasks. Preserve every
existing tracked modification and untracked file. Do not revert, clean, reset,
overwrite frozen experiment artifacts, commit, push, publish, deploy, run paid/cloud
work, train a model, or consume prospective data unless I explicitly ask. Stage
nothing outside your own website files. Before editing, inspect `git status --short`
and treat all pre-existing changes as belonging to other tasks.

## Objective

Create a new, exceptionally comprehensive, evidence-bound page about the CM learning
and neural research, integrated into the existing GitHub Pages site published at:

`https://relative0.github.io/Correspondence_Matrices/`

The new page should do for learning/neural work what the current CM Benchmark site
does for exact computation: make the complete research program understandable,
auditable, and reproducible. It must include successful results, negative results,
failed gates, superseded hypotheses, and approaches that were tried but should not
be repeated. It is not a marketing page and must not imply that a model was promoted
or that learning currently beats the exact production path.

Build a dedicated route, preferably `learning-neural-evidence.html`, titled and
navigated as “Learning & neural” (or a similarly clear label). Do not replace or
collapse the existing benchmark, expert, use-case, or feature-model pages.

## Read these current decision documents first

Read each completely before designing the page:

1. `docs/research/CM_NEURAL_ARCHITECTURE_REASSESSMENT_2026_09_02.md`
2. `docs/research/CM_POST_BENCHMARK_NEURAL_ELIGIBILITY_2026_09_03.md`
3. `docs/research/CM_VERSION_HISTORY_LEARNING_PROTOCOL_2026_09_04.md`
4. `docs/research/CM_LEARNING_BENCHMARK_HANDOFF_CONTRACT_2026_09_04.md`
5. `docs/research/CM_QUERY_LADDER_DEVELOPMENT_LEARNING_EVALUATION_2026_09_04.md`
6. `docs/CM_COMPUTATION_DEEP_TECHNICAL_DOSSIER.md`
7. `docs/recognition/LEARNING_ROADMAP.md`
8. `docs/recognition/CM_NEURAL_BENCHMARK_ASSESSMENT_2026_08_29.md`

Then inventory, read, and reconcile every applicable learning milestone report and
its adjacent machine-readable result, including—not limited to—AB; C, C2 through
C36 (including C5, C21, C28, and C36); the D/D2–D10 rule/cache/profitability line;
and E1/E2. Use `rg --files docs/recognition` to ensure later or oddly named reports
are not skipped. Read the source JSON used by any number shown. Do not blindly copy
an older conclusion when a later reassessment supersedes it.

Also read the current exact-architecture evidence that changed the learning decision,
especially the native portfolio closure, query-ladder cross-machine analysis, and
C38/native portability adjudication. Locate these through the paths already bound by
the current research documents and `tests/test_cm_master_website.py`.

## Required scientific content

Organize the page with progressive disclosure so a non-specialist can understand the
headline while a researcher can inspect the full evidence. Include at least:

### 1. Current status and decision

- No further neural training is currently justified.
- No current selector or neural route is promoted.
- No prospective corpus has been consumed by the current gate.
- Advice remains disabled and the unchanged exact fallback remains authoritative.
- State precisely what future evidence could reopen development, without presenting
  that as expected success.

### 2. Task taxonomy

Explain the distinct learning tasks A–F from the reassessment:

- exact answer/relation prediction;
- decomposition/cut proposal;
- partition ranking;
- exact-backend selection;
- runtime/cost prediction; and
- representation learning.

Make clear that classification accuracy, a valid proposal, and an exact globally
best computation are different contracts. A learned proposal is not an exact answer
engine, and exact checking/fallback costs must be charged.

### 3. Complete experiment timeline

Provide an explorable timeline or evidence table for the major AB, C, D, and E
milestones. For each entry show:

- research question;
- dataset/cohort and split;
- representation/model or analytical policy;
- baselines;
- measured result;
- exact verification/fallback behavior;
- disposition: retained, negative, superseded, blocked, or development-only;
- why continuing that path is or is not useful; and
- links to the report and machine-readable artifact.

Negative paths are first-class results. In particular, surface C5's retained
equivariance but poor accepted-positive recall and 6.3–9.2x slowdown versus exact
ANF; C21's global-best completion barrier; failed GF(2), dispatcher, sentinel,
prepared-policy, profitability, cross-machine, and variance gates; and stale C36
assumptions replaced by repaired post-R2/current exact evidence. Do not flatten a
complex negative result into “neural networks do not work.”

### 4. Representations and model inventory

Visually distinguish:

- mathematical CM/truth matrices;
- dense matrix tensors;
- canonical source-DAG graph inputs;
- fused matrix/graph models;
- CM IR compiler/execution structures;
- packed ANF exact teacher/control;
- CSE-flat, direct BitSet, R2, native slots, ROBDD/CUDD, SAT/CNF, and other non-CM
  exact controls.

Show verified parameter counts and input/output contracts for the matrix MLP, matrix
CNN, graph GNN, fused models, retrieval model, multiscale/variable models, structural
linear controls, natural GNN, direct-cut/rank GNN, and C5 variable-cut models. Do not
call CM IR a mathematical CM or ANF a learned embedding.

### 5. Learning quality—not “coin toss” rhetoric

Build a precise results table by learning task and CM representation. Where labels
are balanced binary labels, show balanced accuracy plus sensitivity/specificity or
accepted-positive recall where available. Where a split has no positives, label the
reported number as specificity—not balanced accuracy. Show majority and class-chance
controls where they can be correctly reconstructed. Do not describe ordinary
accuracy on a skewed dataset as better than chance.

Report cross-seed and cross-split behavior, not only the best seed. Include the
frozen signal criteria and whether each experiment actually met them. Clearly mark
retrospective/inspected “confirmatory” data as non-prospective. Explain why the later
source-blind q64 protocol requires both validation and audit, explicit majority and
analytical controls, at least 0.65 balanced accuracy, margins above chance/majority/
control, at least 0.80 coverage, and three independently passing neural seeds.

### 6. CM-family exact matrices versus non-CM foundational methods

Provide an evidence-bound comparison section answering how the best CM-family
representations perform against foundational non-CM controls. Separate tasks:

- complete relation materialization;
- restriction/query ladders;
- multi-root/repeated outputs;
- resident version history;
- decomposition/global-best search; and
- any configuration/BDD/SAT task included by the current site.

For every comparison identify the task, cohort, aggregate statistic, host, and
whether the result is exact, provisional, one-host, or cross-machine. Keep CM-family
members separate from comparison controls. Never synthesize absolute cross-host
timings, and never mix geometric-mean regret with sum-based selector economics.

### 7. Perfect-predictor and charged economics

Show the decisive headroom results and their boundaries, including:

- repaired post-R2 word-only q64 headroom `1.000415621x`;
- task-identical bigint closure at exactly `1.000000000x` with 18/18
  `cse_bigint` labels;
- resident version-history gross headroom `1.137580420x` on only three exposed
  cases and the approximately 3,560.5 ns/case ceiling preserving `1.10x`;
- the later 54-case q64 sum-based gross results `1.105866083x` (GCC) and
  `1.114578775x` (Clang), while fully charged eligibility remains absent; and
- why feature extraction, inference, exact verification, fallback dispatch, wrong
  route regret, and abstention regret must all be included.

Explicitly show that perfect classification can still be slower than the best fixed
exact arm. The newer candidate economics evaluator also requires a learned route to
retain at least `1.10x` fully charged speedup and beat the frozen analytical control
on every physical host.

### 8. Provenance, split isolation, and fail-closed behavior

Explain source-DAG/circuit/source-group split isolation, semantic and alpha-renaming
duplicate checks, pair retention, source manifests, hashes, independent verification,
refused rows, stale source detection, and why cross-run label synthesis is rejected.

Show the new unlabeled 72-case q64 freeze: 40/16/16 source-group splits, zero prior
alpha-structural overlap, 13 identity-free structural features, joint cross-host
label rule, abstention thresholds, and zero timings/labels/models/prospective/cloud
execution at freeze time. Link its report, manifest, and verification artifacts if
they are intended for publication; otherwise link the repository directory.

### 9. C5 certificate/early-termination boundary

Explain why variable-renaming equivariance and exact proposal reconstruction do not
prove global optimality. Present the full independent-certificate requirements,
including coverage of unexplored partitions, sound objective bound, independent
checker, exact reconstruction, termination without completion search, metamorphic
tests, charged verification cost, unchanged fallback, and at least 25% measured
global-best work avoided as the current development engineering floor.

### 10. Reproducibility and next admissible work

Provide source links, artifact hashes/statuses, exact test environments, test counts,
and commands that only replay/read existing evidence. Separate “can be done now”
from “requires a new authorized Benchmark task” and “prohibited until a gate
passes.” Include a concise list of experiments that should not be repeated under
the current evidence.

## Website implementation requirements

Use the existing static-site architecture under:

`deliverables_n22_24/master_explainer_2026_08_03`

Read these before editing:

- `cm_master_build_2026_08_03.py`
- `cm_master_shared.css`
- `cm_master_shared.js`
- all `cm_*_template.html` files
- `cm_master_data_2026_08_03.json`
- `cm_master_content_2026_08_03.json`
- `tests/test_cm_master_website.py`
- `tests/test_cm_feature_model_website.py`
- `tests/test_cm_website_navigation.py`
- `.github/workflows/publish-results-site.yml`

Follow the existing evidence architecture. Prefer a dedicated evidence loader such
as `cm_learning_neural_evidence.py` that reads pinned machine-readable artifacts,
validates expected statuses/hashes/keys, and returns structured page evidence plus
number tokens. Every quantitative claim rendered in prose should come through the
site's `_numbers`/token mechanism or an equivalently tested evidence binding. Do not
hand-copy numbers into HTML without a machine-source assertion.

Add a dedicated template such as `cm_learning_neural_template.html`, generate the
final `learning-neural-evidence.html`, and integrate it into:

- the build page list;
- shared navigation on every generated page;
- any relevant home/expert cross-links;
- `.github/workflows/publish-results-site.yml` so GitHub Pages actually copies it;
- the navigation page tuple and exact-template expansion tests; and
- a new focused evidence test, preferably `tests/test_cm_learning_neural_website.py`.

Keep the site self-contained: no CDN dependency, telemetry, remote script, or runtime
fetch required. Reuse the established visual language, but make this page unusually
good at navigating a large evidence corpus. Appropriate interactions include task,
representation, evidence-status, and outcome filters; a milestone timeline; compact
comparison charts; expandable “why this stopped” panels; definitions/tooltips; and
direct source/artifact links. All important content must remain usable without
hover, work with keyboard navigation, respect reduced motion, have adequate contrast,
and render well on narrow/mobile and wide screens. Images require meaningful alt
text. Do not sacrifice auditability for animation.

Every scope boundary must be visible near the associated result, not hidden in a
single disclaimer. Repository evidence links must use the site's existing
GitHub-Pages-to-repository routing behavior. Generated files must contain no template
markers, unresolved number tokens, or absolute local machine paths.

## Anti-overclaim rules

- Do not say that a neural model computes an exact CM answer unless the evidence
  actually establishes that contract; it currently does not.
- Do not say learning is production-ready, prospectively confirmed, or promoted.
- Do not imply C5 beats exact ANF; its safe path was materially slower.
- Do not reuse the historical confirmation split as new prospective evidence.
- Do not merge timings from different runs into a fabricated current label table.
- Do not compare absolute timings between different physical hosts.
- Do not conceal refusals, missing native dependencies, drift, incomplete charges,
  small samples, one-host status, label imbalance, or lack of positives.
- Do not turn a gross oracle-headroom diagnostic into a fully charged learned result.
- Do not claim “better than a coin toss” from accuracy alone. State the class chance,
  majority control, balanced metric, split, seed, and coverage.
- Clearly distinguish exact CM-family implementations from non-CM controls.

## Build and verification

Regenerate the entire site using the repository builder; do not manually patch only
the generated HTML. Run, at minimum, the exact-template, evidence-binding, navigation,
HTML/link, and JavaScript syntax tests covering every site page. The likely focused
command is:

```powershell
.\.venv\Scripts\python.exe -B deliverables_n22_24\master_explainer_2026_08_03\cm_master_build_2026_08_03.py
.\.venv\Scripts\python.exe -m pytest -q `
  tests\test_cm_master_website.py `
  tests\test_cm_feature_model_website.py `
  tests\test_cm_website_navigation.py `
  tests\test_cm_research_publication.py `
  tests\test_cm_learning_neural_website.py
```

Adapt only if repository inspection shows a more current command. Also open the
generated site locally and perform visual/browser QA at mobile and desktop widths,
checking every interaction and local link. This visual QA does not replace static
tests.

Do not run neural training, exact benchmarks, RunPod, or prospective-data commands
for this website task. It is a read-only evidence publication task plus static-site
implementation and tests.

## Handoff

When finished, report:

- the exact pages/build/data/navigation/workflow/tests changed;
- which reports and machine artifacts bind every major section;
- the build and test results;
- visual QA performed and any remaining layout limitations;
- any evidence conflict discovered and how it was represented rather than hidden;
- `git status --short` and a clear separation of your files from pre-existing dirty
  files; and
- any claim or section intentionally omitted because evidence was insufficient.

Do not commit or push unless I separately ask after reviewing the result.
