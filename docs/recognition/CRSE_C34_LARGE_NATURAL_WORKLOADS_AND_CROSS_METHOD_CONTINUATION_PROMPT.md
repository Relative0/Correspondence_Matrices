# CRSE continuation implementation brief: C34 natural workloads and exact cross-method headroom

Use this document as an implementation brief. Continue the work in the existing
`C:\Users\brian\Documents\CM_Computation` repository; do not merely propose a plan.
Work locally and safely, preserve the research register, implement the strongest
well-supported next milestone, test it, and report negative results as plainly as
positive ones.

## Mission

The immediate milestone is **C34: larger natural, task-matched workloads and exact
CM/GF(2) headroom adjudication against appropriate alternative methods**.

C30-C33 established a prepared exact policy lifecycle and a bounded asynchronous shadow
boundary. C33 reduced full observational overhead from about 2.040x synchronously to
about 1.038x asynchronously on the existing 48-case natural Yosys corpus. That makes the
engineering boundary credible locally, but it does not establish that a learned router is
profitable or that CM/GF(2) wins broadly. C34 must first measure where a fixed exact
CM/GF(2) path has enough task-matched advantage to pay for recognition, verification, and
dispatch. Do not train or promote another router until the exact-method measurements show
that headroom.

Prefer a small number of scientifically clean task tables over a large Cartesian sweep.
Each table must compare methods that return the same requested result and must charge all
work required by that contract.

## First actions and repository discipline

1. Read this brief and the project brief at
   `CRSE_LEARNING_RESEARCH_NEW_THREAD_PROMPT.md`.
2. Inspect `git status --short`, the current branch, and recent commits before editing.
   Do not reset, restore, clean, or overwrite work already present.
3. At the time this handoff was written, the last committed milestone was C32 at
   `88d21a6` (`Implement C32 baseline-serving shadow boundary`). C33 was implemented and
   locally verified but not yet committed. The repository state may have advanced, so
   determine the actual state rather than assuming this remains true.
4. Review the C31, C32, and C33 reports and results before starting C34:
   - `docs/recognition/LEARNING_MILESTONE_C31_PROSPECTIVE_CROSS_MACHINE_REPLICATION_2026_08_31.md`
   - `docs/recognition/LEARNING_MILESTONE_C32_BASELINE_SERVING_SHADOW_2026_09_01.md`
   - `docs/recognition/LEARNING_MILESTONE_C33_BOUNDED_ASYNC_SHADOW_2026_09_01.md`
   - `docs/recognition/learning_milestone_c31_linux_results.json`
   - `docs/recognition/learning_milestone_c32_shadow_results.json`
   - `docs/recognition/learning_milestone_c33_async_shadow_results.json`
5. Read `docs/recognition/LEARNING_ROADMAP.md` and
   `docs/recognition/experiment_register.json`. Preserve all 18 research tracks and all
   eight application registrations exactly; update them through the existing registration
   pattern rather than rebuilding the register manually.
6. Match the style and testing structure of the surrounding C21-C33 implementation.
   Prefer bounded, reviewable changes.

There may be unrelated dirty files from video production and P7/W4 timing work. At the time
of this handoff these included `docs/video_factory/**`,
`tests/test_cm_runpod_p7_w4_timing.py`, and P7 timing audit scripts/records under
`docs/audits/2026-08-25-cm-deep-performance/**`. Do not edit, stage, remove, or attribute
those files unless the user separately assigns that work. Never stage with `git add .`.

Do not add videos, rendered media, archives, remote packages, dependency caches, or raw
RunPod retrievals to Git. Raw local experiment runs under `docs/recognition/runs/` are
intentionally ignored; do not force-add them. Commit only curated specifications, compact
results, source code, tests, reports, manifests, independent verification summaries, and
registration changes when the user asks for a commit.

## Fixed scientific scope

Preserve these 18 research tracks:

1. **R01** Task-aware routing and cost prediction
2. **R02** Computational-subclass recognition
3. **R03** Verified motifs and semantic macros
4. **R04** Rewrite profitability and scheduling
5. **R05** Generalized rule discovery
6. **R06** CM decomposition and layout
7. **R07** Order and compilation selection
8. **R08** Functional similarity and retrieval
9. **R09** Partial contexts, sessions, and versions
10. **R10** SAT/equivalence/counting guidance
11. **R11** CMs as exact training teachers
12. **R12** Neural representation comparisons
13. **R13** Learning-method comparisons
14. **R14** Adaptive/sequential learning
15. **R15** LLM-assisted learning and discovery
16. **R16** Inference and training efficiency
17. **R17** Confidence, novelty, and abstention
18. **R18** Negative controls and hard limits

Preserve these eight applications:

1. Configuration and product families
2. Hardware verification and design
3. Security and access-control policy audit
4. Compiler and program-analysis predicates
5. AI-agent hard guardrails
6. Boolean biological networks
7. Regulated rules and decision tables
8. Classical reversible and control logic

C34 may concentrate its measurements on the hardware/Boolean-circuit application, but its
registration must not delete, merge, rename, or imply empirical coverage of the other
seven applications.

## Evidence established so far

Use the checked-in reports and result JSON as the authority. This summary is orientation,
not a substitute for reading them.

- Early exact CM/CSE experiments established that timing claims depend on the task
  contract, representation, setup charge, and corpus. The website figures comparing CM to
  plain and flattened CSE answer different questions from later recognition and shadow
  experiments; do not combine their ratios as though they were one benchmark.
- Matrix MLP, matrix CNN, graph, fused, contrastive, and related neural classifiers were
  trained and evaluated. Their transfer/generalization was weak on the held-out natural
  regimes studied. Exact algebraic/ANF features and controls frequently led. These are
  valid negative learning results, not a reason to erase the learning tracks.
- The D-series proved motif rules over metavariables and compiled structural matchers.
  Warm rule reuse beat repeated per-instance CM proof, but ordinary no-rewrite CSE was
  still faster on the small synthetic motifs. Rule correctness and reuse were established;
  production profitability was not.
- The E-series and R10 work added exact BDD/SAT/equivalence/counting-related contracts and
  controls. Exact engines were useful, while the tested learned timing/routing surfaces did
  not justify promotion.
- C15-C16 froze exact CM/GF(2) artifacts and screened paths with independent replay and
  cross-machine timing discipline.
- C18-C23 expanded independent natural cones, LogiKBench/Yosys material, exact method
  contracts, decomposition tables, persistence, and fresh held-out data. C21/C23 found
  narrow wins for packed/screened exact paths and little learnable router headroom.
- C24-C29 localized overhead and variance. Recognition, dispatch, measurement noise, and
  machine effects often consumed the narrow nominal advantage. These negative findings
  are part of the result.
- C30 created a frozen prepared-policy context and passed the local lifecycle gate.
- C31 replicated the frozen C30 policy on a second Linux machine with the prospective
  protocol and retained the exactness/refusal boundary.
- C32 proved baseline-serving shadow observation but synchronous full observation cost
  about 2.045x the shadow-disabled total.
- C33 implemented a bounded asynchronous boundary with explicit delivery acknowledgement.
  On the local 48-case C27 natural corpus it served 2,048 exact baseline responses and
  produced 512 full plus 128 quarter-sampled asynchronous observations, with zero candidate
  starts before acknowledgement, zero mismatches/divergences, zero candidate results
  served, and zero writes/promotions. Full asynchronous total ratio was about 1.038x versus
  the exact shadow-disabled baseline; quarter sampling was about 0.996x. This is local
  engineering evidence, not production or broad profitability evidence.

## Existing natural sources and split hygiene

Inventory these sources before creating anything new:

- `docs/recognition/c18_independent_cone_dataset.json`
- `docs/recognition/c18_independent_corpus_verification.json`
- `docs/recognition/c19_logikbench_small_cone_dataset.json`
- `docs/recognition/c19_logikbench_small_cone_verification.json`
- `docs/recognition/c21_decomposition_table_dataset.json`
- `docs/recognition/c21_decomposition_table_verification.json`
- `docs/recognition/c23_yosys_fresh_gf2_dataset_v2.json`
- `docs/recognition/c23_yosys_fresh_gf2_dataset_v2_verification.json`
- `docs/recognition/c27_yosys_fresh_gf2_dataset.json`
- `docs/recognition/c27_yosys_fresh_gf2_dataset_verification.json`
- the held-out ABC i10 material under
  `deliverables_n22_24/heldout_abc_i10_2026_08_26/`

The exact filenames of a companion verification record may differ slightly; discover them
with repository search rather than inventing replacements.

Do not silently reuse fitting, policy-selection, threshold-setting, or prior evaluation
data as fresh test data. Record source provenance, circuit/module/output identities,
deduplication keys, semantic hashes, transformations, and overlap with every earlier
split. If a useful source is reused, label the measurement as repeat/extension evidence
and keep a truly held-out component where the claim requires it.

Prefer deterministic extraction from checked-in, redistributable sources. If an external
corpus must be downloaded, verify its license/provenance and freeze only bounded source
material with hashes. Do not browse or download merely to make the corpus look larger.

## Existing infrastructure to reuse

Do not build a parallel benchmark framework until the existing one has been inspected.
Relevant components include:

- `cmbench/comparative/contracts.py`
- `cmbench/comparative/tasks.py`
- `cmbench/comparative/arms.py`
- `cmbench/comparative/corpus_freeze.py`
- `cmbench/comparative/readiness.py`
- `cmbench/comparative/schedule.py`
- `cmbench/comparative/fresh_persistence.py`
- `scripts/cm_comparative_native_scout.py`
- `scripts/cm_native_contracts.py`
- the exact GF(2), screened-policy, prepared-context, and shadow modules under
  `cmbench/recognition/` and `cmbench/comparative/`
- C21-C33 runners, independent verifiers, tests, and registration scripts

For C33 specifically, inspect:

- `cmbench/recognition/gf2_async_shadow_boundary.py`
- `cmbench/comparative/gf2_async_shadow_experiment.py`
- `scripts/cm_comparative_c33_async_shadow.py`
- `scripts/crse_gf2_async_shadow_verify.py`
- `tests/test_gf2_async_shadow_boundary.py`
- `tests/test_cm_comparative_gf2_async_shadow_experiment.py`

## C34 implementation sequence

### 1. Freeze the claims and task contracts

Before measuring, define a small set of exact questions. At minimum, consider separate
tables for:

1. complete truth-vector or functional-representation construction;
2. exact best GF(2)/ANF decomposition under the already defined objective;
3. equivalence or miter status;
4. satisfiability and, where requested, a verified witness;
5. restriction, counting, or repeated-query workloads; and
6. persistence/reload or resident-query workloads when persistence is part of the claimed
   use case.

Do not place a method in a table merely because it accepts the same input. It must return
the same requested output under the same semantic definition. For example, a SAT solver
answering existence is not a substitute for a full truth vector, and a CSE kernel that
only evaluates supplied assignments is not equivalent to a method charged with compiling
or enumerating all assignments.

Write the contract before collecting timings. Include input, output, exactness condition,
allowed preprocessing, setup lifecycle, amortization unit, verification work, and failure
or abstention semantics.

### 2. Build a bounded larger natural corpus

Extend the natural evidence enough to expose width, structure, density, sharing, output
count, and repeated-query differences without creating an unreviewable sweep. Target
support for roughly 7-12 live variables where each exact task remains feasible, while
retaining smaller controls. Bound case counts, repetitions, wall time, and artifact size.

Stratify by meaningful circuit properties rather than only variable count. Retain circuit
family and source-group separation so one design with many related cones cannot dominate
both selection and evaluation. Store a compact manifest plus an independently checked
semantic/provenance verification record.

If the existing checked-in sources cannot support a clean larger held-out set, implement
the extraction and verification machinery first and state the evidence limit. Do not pad
the dataset with trivial renamings or synthetically correlated variants.

### 3. Implement task-matched exact arms

Use only methods appropriate to each table, selected from:

- exhaustive, screened, source-packed, or prepared exact CM/GF(2);
- direct, plain, flattened, bigint, or word-packed CSE/evaluation;
- ABC/AIG-based exact operations;
- CUDD/BDD with fixed ordering, reordering, and resident modes kept distinct;
- CaDiCaL or another existing SAT backend for SAT/miter tasks.

Do not claim a library backend was measured unless the actual backend ran. Keep unavailable
methods as explicit readiness results rather than substituting a Python illustration.
Reuse native adapters and readiness probes already in the repository.

### 4. Charge the full lifecycle

Record and, where appropriate, separately report:

- parsing and normalization;
- representation construction;
- feature extraction;
- compile/build/setup;
- policy preparation or source screening;
- query/evaluation;
- exact result verification;
- serialization and persistence;
- reload and resident reuse;
- recognition and dispatch;
- failure, timeout, or refusal handling.

Separate cold, warm, and resident claims. Define the amortization denominator. Never hide
setup in one arm while charging it to another, and never mix a resident compiled object
with a cold one-shot competitor without labeling that difference.

Use counterbalanced schedules, deterministic seeds, warmup rules, per-block raw records,
robust summaries, and width/source strata. Retain absolute times alongside ratios; very
large ratios on microsecond tasks can still have too little absolute headroom for a router.

### 5. Establish exactness independently

Every measured result must be checked independently of the producer. Where feasible,
recompute semantic results from frozen source/input artifacts rather than trusting copied
expected fields. Verify witnesses, truth bits, best-artifact objective/tie breaks, source
and context hashes, manifests, schedules, summary aggregation, and refusal controls.

Add fail-closed mutation tests for at least source drift, manifest drift, task mismatch,
output-bound mismatch, changed ordering/normalization, and result tampering. Evidence must
not certify itself by calling the same top-level implementation as the producer.

### 6. Run a no-training headroom adjudicator

The first C34 decision must use fixed exact paths and frozen task definitions. For every
candidate surface, compute both relative and absolute headroom against the best eligible
exact alternative. Then charge a conservative recognition, verification, and dispatch
budget derived from measured C30-C33 overhead rather than assuming free routing.

Suggested decision rule:

- **No headroom:** the best CM/GF(2) path is not reliably faster, or its lower confidence
  bound/robust margin does not cover recognition plus verification. Record the negative
  result and do not train a router for that surface.
- **Narrow headroom:** the exact path wins but the remaining absolute margin is small or
  unstable. Continue fixed-policy engineering or larger confirmation; do not promote a
  learned path.
- **Actionable headroom:** a task/source/width region has stable, held-out, task-matched
  advantage comfortably larger than measured recognition and verification costs. Only
  then define a leakage-safe C35 learning or routing experiment.

Freeze numerical gates before the adjudication run. Do not tune gates on the final test
records. Report confidence/dispersion and source-family consistency, not only a global
median.

## Scientific invariants

- Exact semantics are mandatory. Learning may propose, rank, or abstain; it may not certify
  correctness.
- Every speed comparison must be task matched.
- Preserve output bounds and witness/full-vector distinctions.
- Preserve source provenance, data splits, and overlap disclosures.
- Use an independent verifier and hash-bound evidence manifests.
- No candidate serving, production writes, training writes, deployment, or promotion.
- Do not infer broad superiority from one narrow task/width/corpus.
- Do not erase negative controls or failed hypotheses.
- Do not convert timing noise into labels for a classifier.
- A statistically visible difference may still be economically useless; include absolute
  headroom.
- Continue to distinguish generated/synthetic evidence, repeated natural evidence, fresh
  held-out evidence, and cross-machine evidence.

## Expected C34 deliverables

Produce the following, adapting names to the established naming convention:

1. exact task-contract and arm implementation changes;
2. bounded natural-corpus extraction/freeze code if needed;
3. a compact dataset manifest and independent corpus-verification JSON;
4. a frozen experiment specification with predeclared gates;
5. a deterministic counterbalanced local runner;
6. unit and integration tests covering exactness and failure controls;
7. raw ignored local run evidence;
8. a compact curated results JSON;
9. an independent verification script and verification JSON;
10. a human-readable C34 milestone report;
11. a machine-readable C34 summary suitable for a future unchanged second-machine run;
12. roadmap and experiment-register updates preserving 18 tracks and eight applications;
13. a clear next decision: stop the surface, replicate a real win, improve a fixed exact
    path, or proceed to a leakage-safe learning experiment.

Do not create a RunPod package merely because previous milestones used RunPod. Local-first
work is sufficient until there is a frozen, meaningful C34 result worth replicating.

## Testing and environment notes

- Prefer the project virtual environment interpreter when available.
- `.venv` has the main test environment but may not contain PyTorch.
- `.venv-crse-neural` has the PyTorch CPU environment (previously PyTorch 2.10) but may not
  contain pytest.
- If a broad local test requires neural imports, the established approach is to use the
  main `.venv` interpreter with the neural environment's site-packages added explicitly,
  without installing or modifying dependencies unless necessary.
- Run the focused tests for every changed surface first. Then run the relevant comparative,
  register, and independent-verification tests. Run the broad suite when feasible.
- A prior broad C32-era run passed 1,174 tests plus 1,142 subtests and retained two known
  pre-existing failures: a stale generated website Git revision and an old historical
  one-pass manifest whose recorded `cm_exprlib.py` size no longer matched. Re-evaluate
  current failures; do not blindly whitelist them if their cause has changed.
- Before claiming completion, run whitespace/diff checks, inspect `git diff --stat`, and
  inspect `git status --short`. State exactly what was tested and what was skipped.

## RunPod and external-operation boundary

Do not make a paid or external call based only on historical authorization. If a later
unchanged second-machine replication is scientifically justified, first freeze a minimal
package and manifest, write a bounded protocol, state the exact upload contents and byte
count, and obtain current explicit authorization for that package/protocol. Never read,
print, copy, or commit API keys or credential values. Use only the existing non-secret
credential reference/mechanism.

Any replication protocol should retain the established controls: one owned Secure CPU pod,
no replacement unless separately authorized, pinned image, resource/rate/total-cost caps,
bounded retrieval, cleanup and reconciliation deadlines, no persistent/network volume, and
no training or production writes. Confirm deletion/reconciliation before reporting the run
complete.

## Likely C35 decision after C34

Choose C35 from evidence, not momentum:

- If C34 finds an actionable exact CM/GF(2) surface, freeze it and either perform an
  unchanged second-machine confirmation or build a leakage-safe, abstaining router whose
  complete charged cost fits inside the measured headroom.
- If C34 finds only narrow/no headroom, do not train another timing classifier. Improve the
  fixed packed/screened implementation, study resident/repeated-query regimes, or move to a
  different research track such as natural motif reuse, exact decomposition/layout, or
  partial-context versioning.
- Expand to the other seven applications only with task-native corpora and contracts. Do
  not reuse circuit timing claims as application evidence.
- Revisit neural models only where a measurable decision exists, leakage-safe data is
  sufficient, an exact abstaining fallback remains authoritative, and the inference cost
  is demonstrably affordable.

## Completion standard

C34 is complete only when the implemented task tables, corpus, exact results, timings,
controls, hashes, independent replay, tests, curated report, and register updates agree.
Do not report completion from a successful intermediate command or producer-only output.
If the result is negative, finish and register it anyway; a clean no-headroom finding is a
valid milestone and should direct the next implementation choice.
