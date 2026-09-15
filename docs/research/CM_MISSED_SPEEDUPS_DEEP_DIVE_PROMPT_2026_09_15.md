# Successor CM deep dive: missed speedups, residual costs and audit blind spots

Paste the request below into a new Codex task, or ask it to read and execute this
file. Recommended initial setting: GPT-6 Astra, high reasoning. The companion
`CM_FAMILY_REPAIR_COMMIT_HANDOFF_2026_09_15.md` explains the recommendation and
commit-aware evidence verification. This file prepares a task; it does not record
execution of that task.

---

## Request and purpose

At exact commit `4f979d141d8a73591a83d48f7273f516b7205823` in
`C:/Users/brian/Documents/CM_Computation`, perform an independent, deep code and
measurement audit of the remaining CM and CM-family performance costs. Find out
whether useful speedups, correctness repairs, lifecycle simplifications or
measurement defects were missed by the prior attribution and repair work.

Treat earlier conclusions as evidence to evaluate. Do not assume an optimization
exists, assume a hot helper is wasteful, or assume the repairs necessarily improve
all callers. Look for counterexamples, hidden state and measurement confounding
as carefully as opportunities. A supported conclusion that no additional change
is currently justified is an acceptable outcome.

The goal is an evidence-backed opportunity and implementation-decision report.
This request authorizes the bounded local audit, read-only investigation,
diagnostic scripts, default-off instrumentation and isolated experimental
prototypes. It does **not** authorize shipping further production optimizations.

## Isolation, permissions and evidence preservation

1. Begin with read-only Git/status/source inspection. Read applicable AGENTS.md.
   The target is the exact repair commit above, not moving `main` or the current
   branch tip. Its parent is `4d9b869fb7b22eb6263ef613b5a9d41fcbbb78dd`; the original
   implementation baseline is `e334de594262059cc18cf37eaab56b0f79e94843`.
2. Create a separate clean worktree from the repair commit, using an unused
   `codex/` branch. Suggested names are `codex/cm-missed-speedups-audit-20260915`
   and `C:/Users/brian/Documents/CM_Computation/tmp/cm-missed-speedups-20260915`.
   Check both names first. Do not overwrite or repurpose an existing worktree.
3. Protect the dirty repository root and all existing worktrees, especially
   `tmp/cm-consolidation-20260914`, `tmp/cm-time-attribution-20260915`, and
   `tmp/cm-family-repair-20260915`. Record their tracked status and hashes of dirty
   files; record status and hashes for task-relevant untracked evidence. Do not
   read secret files, unrelated untracked data or credential stores.
4. Read the existing project `.venv/Scripts/python.exe`; do not alter the shared
   environment. Put temporary files, pytest outputs and diagnostic artifacts in
   the new worktree. Use Python `-B`, disable pytest's cache provider and select a
   fresh worktree-local basetemp. Do not install optional dependencies.
5. Use existing exposed development fixtures and already measured evidence.
   Do not load, generate or execute held-out confirmation cases. Do not launch
   cloud resources, spend externally, change public claims or scientific
   dispositions, or rewrite/regenerate historical evidence.
6. Keep prototypes in the new audit directory or separate temporary copies of
   relevant code there. Any instrumentation of production files must be explicitly
   default-off and reviewed/tested. Do not change public defaults, routing,
   crossover thresholds, cache policy, output contracts or correctness guards.
   Do not remove oracle checking and report the difference as a CM speedup.
7. Leave the new audit uncommitted and unpushed. Do not merge, deploy, publish,
   create another task, or start scheduled monitoring. Approval for this audit
   does not carry the preceding task's commit/push request into new work.

## Read these sources and predecessor records first

Use the following repository-relative paths against their bound source versions.
Resolve them to absolute paths in the report. Read ledgers and timing code as well
as narrative conclusions; do not rely on this handoff's summaries alone.

### Current repair baseline

- `docs/audits/2026-09-15-cm-family-repair/PLAN.md`, `REPORT.md`, `CHECKS.md`,
  `EXECUTION_MAP.md`, `ROOT_CAUSE_MATRIX.md`, and `OPPORTUNITIES.md`.
- Current records are `PROFILE_RESULTS-v2.json`, `TIME_LEDGER-v2.md`,
  `final-fresh-a-v2.json`, `final-fresh-b-v2.json`,
  `final-resident-a-v2.json`, `final-resident-b-v2.json`, and
  `MECHANISMS-final-v3.json`. Earlier versions and failed candidates are preserved
  for provenance; do not pool them with the final source.
- Inspect `measure.py`, `paired_resident.py`, `diagnose.py`, `summarize.py`,
  `AUDIT_MANIFEST.json`, `AUDIT_MANIFEST.sha256`, `SOURCE_IDENTITY_DIAGNOSTIC.json`,
  `PRESERVATION.json`, and `GIT_REVIEW.json` in that directory.
- Read `docs/research/CM_FAMILY_REPAIR_COMMIT_HANDOFF_2026_09_15.md`,
  `CM_FAMILY_REPAIR_PUBLICATION_2026_09_15.json`, and
  `verify_cm_family_repair_publication.py` from the original repair worktree.
  These handoff files are in a later documentation commit, so a worktree at the
  exact repair implementation commit will not contain them. Use the absolute
  path under `C:/Users/brian/Documents/CM_Computation/tmp/cm-family-repair-20260915/`.

### Prior attribution and lifecycle studies

- `docs/audits/2026-09-15-cm-time-attribution-deep-dive/`: read `REPORT.md`,
  `EXECUTION_MAP.md`, `CODE_AUDIT.md`, `FROZEN_EVIDENCE.md`, `TIME_LEDGER.md`,
  `ROOT_CAUSE_MATRIX.md`, `PROFILE_RESULTS.json`, `FOLLOWUP_CODE_DIVE.md` and manifest.
- The follow-on `docs/audits/2026-09-15-cm-family-lifecycle-code-dive/` is still
  local untracked evidence in
  `C:/Users/brian/Documents/CM_Computation/tmp/cm-time-attribution-20260915`.
  Read its `REPORT.md`, `TIMING_CONTRACT.md`, `TIMING_CONTRACT_RESULTS.json`,
  `WRAPPER_BRANCH_ANALYSIS.md`, `WRAPPER_BRANCH_RESULTS.json`,
  `CACHE_LIFECYCLE.md`, `CACHE_LIFECYCLE.json`, `VERIFICATION.md`, and manifest.
  Its historical tests assert some now-fixed behavior; run them only against
  their bound baseline. Do not change fixed production code to satisfy them.
- Read the local plan
  `C:/Users/brian/Documents/CM_Computation/tmp/cm-time-attribution-20260915/docs/research/CM_FAMILY_REPAIR_AND_SPEEDUP_PLAN_2026_09_15.md`.
  Do not assume either this plan or the untracked follow-on audit arrived through Git.

### Governing task-comparison evidence

- `docs/audits/2026-09-11-cm-performance/REPORT.md`.
- `docs/audits/2026-09-11-cm-continuation/REPORT.md`.
- `docs/audits/2026-09-15-cm-sympy-development-gate/NO_GO.md` and `REVIEW.json`.
- `docs/research/cm-benchmark-research-2026-09-13/REPORT.md`.
- `docs/recognition/architecture_comparison_execution_retry_20260903/VERIFIED_INTERPRETATION.md`.
- `docs/recognition/architecture_query_ladder_cross_machine_execution_20260904/VERIFIED_CROSS_MACHINE_INTERPRETATION.md`.

### Relevant implementation

- `cm_ir.py`: CMNode, CMIRBuilder, structural UID generation, canonicalization,
  rewrites, keys/interner, support/live sets, build memo, normal and persistent
  compilation, scoped sharing plans, foreign adoption, lowering caches, wrapper
  admission, materialization and default-off observer hook.
- `bitset_backend.py`: recursive/memo AST, CSE-flat, CM-flat, positional masks,
  bound-program/context caches, words execution, allocation/release and conversion.
- `cm_bench.py`: family, partial-context and equivalence paths, reference creation,
  explicit engine settings, output provenance, timers, row construction and summaries.
- `cmbench/backends/bitset_engine.py`, `cmbench/output_budget.py`,
  `cmbench/phase_timing.py`, config/result modules, expression DAG serialization,
  and the applicable family generators and tests.
- `cmbench/comparative/sympy_cm_claim_cleanup.py` and the Y02–Y05 workers; follow
  their actual imports into already eligible SAT/counting/BDD evaluators.
- `tests/test_cm_family_repairs.py` and the affected test list in repair `CHECKS.md`.

## Stage 1 — audit the audit before adding measurements

Verify content hashes against the exact commits and local evidence paths. The
old repair `seal.py --verify` asserts its historical pre-commit HEAD and diff;
that assertion failing after commit is not evidence corruption. Use the additive
publication verifier for current committed bytes and source normalization, and
separate historical checkpoint claims from current Git preservation checks.
Verify predecessor content in its original evidence worktree. If a required local
record is missing, mark the dependency unavailable; do not reconstruct it from
memory or silently substitute a different version.

Audit these known weaknesses and any others the code reveals:

- Whether resident baseline/candidate module aliases actually isolate imported
  globals, selectors, source-attached programs, environment caches and persistent
  state. Check each function's defining module/source, not just its displayed
  name. Shared mutable input roots can contaminate compile or binding comparisons.
- Whether "cold" resets all relevant state or just the persistent root map.
  Separate fresh process, imports, fresh source objects, first compile, first bind,
  warm evaluator, warm cache and long-lived resident family. Do not call a block
  of one miss followed by many hits an all-miss measurement.
- Whether actual engines, packed primitives, variable order, output basis, output
  type, validation and delivery match. The prior public words16 versus bare bigint
  comparison is not an isolated wrapper comparison.
- Whether argument construction belongs to the timed caller. The older wrapper
  helper built names and OutputBudget inside its span. Family diagnostic metadata
  reconstructed from a first variant is not the original generated family object.
- Whether a family total covers compile/evaluate only, the backend loop with
  oracles, or complete statistics-row delivery. New provenance is real caller work;
  distinguish its cost from a slower kernel without dropping required reporting.
- Whether detailed tracing is off by default, whether its inactive wrappers still
  add work, and whether activation changes the algorithm or merely observation.
  Check nested, exception and restoration behavior, including standalone imports.
- Whether timers overlap, CPU resolution is adequate, and residuals have a measured
  explanation. cProfile's default elapsed-time measurements are not process CPU.
  Do not add cumulative helper times or inclusive nested spans.
- Correct output-byte accounting: the old fallback8 metadata recorded 32 packed-
  equivalent bytes, while its delivered uint8 truth table is 256 bytes. Retain and
  explain the old record; never rewrite it. Distinguish result payload, Python
  object overhead, temporary arrays, serialized rows and shared retained graphs.
- Distinguish line-ending identity failures from changed source semantics. The
  chart-data failure and two historical source-hash failures reproduce on the
  baseline. Do not regenerate old evidence to make those checks pass.
- Check that controls truly share unchanged code; if a dependency changed, identify
  the binding and invalidate affected comparisons instead of repairing the story.

Write an evidence-validity table: reusable as-is, recomputable from frozen records,
requires new matched observation, invalid for this inference, or unavailable.
For each entry give the exact reason and what conclusion it can support.

## Stage 2 — freeze the hypothesis queue and bounded plan

Before executing new performance measurements, create `PLAN.md` with exact fixture
identities/seeds, source/config hashes, phase boundaries, cache treatments,
comparison pairs, repetition/order plan, limits and stop conditions. Record any
later amendment before running it; preserve all earlier raw outputs.

Start from these mechanisms, while actively looking for unlisted ones:

1. **Identity and repeated traversal.** Remaining warm-call eligibility/structural
   UID/digest work, key hashing/sorting, multiple traversals of the same source,
   recursive Python dispatch, memo lifetime and equality/collision assumptions.
   The duplicate root-only miss prepass was repaired; verify it remains repaired.
   Determine what recurring work is required for sound identity and what can only
   amortize if callers retain an immutable prepared object.
2. **CM representation and retained information.** Node/key/support/live-set
   construction and propagation, tuple/dictionary/set allocation, interning,
   rewrites, metadata retained after lowering, source edges versus unique nodes,
   flat instruction count and live width. Test whether CSE-flat preserves sharing
   with less structure under identical execution primitives and output contracts.
3. **Family cache work.** Root versus subtree position, root-only versus subtree
   policy, same-call versus prior-call origin, digest lookup, LRU work, insertion,
   eviction/reinsertion, foreign integration and builder-local identity. Weight
   hits by saved/repeated work; high hit count alone proves little. Separate warm
   identical roots, partial overlap and no-reuse mutation. Check retained reachable
   graphs after releasing tracer references, not only cache entry count.
4. **Public wrapper and reporting.** Repeated basis/fixed-map normalization,
   budget estimates, operation/node count, diagnostics dictionaries, optional
   observer dispatch, kwargs/result objects, provenance JSON, summary grouping and
   reference/conversion work. A node-count cache already exists. Reopen a rejected
   proposal only with new evidence showing a distinct missed cost or invalid assumption.
5. **Program/environment/context binding.** Lowering, variable-index mapping,
   complete environment versus positional masks, fixed signatures, binding cache
   keys/lifetimes, q1 versus q64, changed variable orders and widths. Separate an
   evaluator-ready API opportunity from one that merely moves preparation to callers.
6. **Kernel, allocations and conversion.** Bigint/words paths under matched
   widths and result types, instruction dispatch, allocation peaks, liveness and
   release, result copies, reinflation, bigint/array conversions and serialization.
   Determine what scales with unavoidable output bytes, source size, program
   length, support width or Python object count. Do not infer a words bottleneck
   from a comparison whose control used bigint.
7. **Task-specific ingress and lifecycle.** Direct AST versus CM ingress into the
   same eligible assignment/SAT/count/equivalence/simplification evaluator; shared
   structure and simplifications retained or lost along the way; repeated parsing,
   decoding, imports, validation or transport. Distinguish a faster implementation
   of the same task from choosing a smaller task or a different algorithm.
8. **Correctness and cleanup risks introduced by repairs.** Explicit flag forwarding
   at adjacent callers, default restoration, source-plan exact-root/options binding,
   reentry/failure, cache collision assumptions and GC/id reuse, observer retention,
   skipped outputs, reduced-output oracles, stale diagnostics and package import
   closure. Keep a functional defect separate from a performance opportunity.

For each hypothesis record: novelty relative to earlier audits, affected callers,
code locations, expected causal mechanism, falsifying observation, independent
control, required invariant, plausible saving ceiling, memory/lifetime tradeoff,
and a keep/defer/reject/unresolved decision. Investigate the most material and
testable items first. Do not spend the budget merely because it is available.

## Stage 3 — controlled attribution ladder and representative coverage

Use the smallest subset that distinguishes the hypotheses. Inventory all these
task shapes; use frozen evidence for an already answered shape, and explicitly
mark unsupported/unmeasured cells. Do not run the full 80-family catalog.

- Complete packed relation; supplied assignment batch; restriction/cofactor q1
  and q64; exact count; SAT and equivalence status; simplified-expression delivery.
- Low/high source sharing; family variants with high, partial and negligible reuse.
- Existing repair fixtures include implication of conjunction/disjunction k4/k16,
  random_expr seed2026 k8 fallback, Or(x0,x19) reduced/refused k20, and the shared
  XOR DAG from persistent-path tests. Reuse the exact construction/metadata.
- Existing families: shared_block_mix seed2 size8, composition_mix seed3 size5,
  and eight repeats of the existing simple root. Retain base_expr/shared blocks.
- Select any additional points only from already exposed development fixtures.
  First establish development provenance; never sample the held-out partition.

The matched ladder should distinguish raw recursive AST, memoized AST,
sharing-aware CSE-flat, CM IR lowered through those same packed primitives,
bare CM-flat, public CM, CM-family persistent off/on, and direct-versus-CM ingress
into the same eligible evaluator. Keep input, order, fixed context, engine,
cache state, output, correctness and delivery constant where possible. Record
"no analogous phase" where appropriate. If they cannot match, label the comparison
as a task/algorithm/contract comparison; do not call its whole gap CM overhead.
Include direct BitSet, SymPy, SAT/counting and ROBDD controls only for the tasks
they actually deliver, using existing installed evaluators and exposed development
inputs. Reuse frozen comparator evidence when a dependency is unavailable; label
the unrun cell explicitly. Do not silently substitute a cheaper result contract.

Use an execution map from process launch through caller-visible completion:
startup/imports; input loading/parsing/DAG decoding; source/UID preparation;
canonicalization/rewrites; keys/hashing/sorting/interning; support/live propagation;
cache validation/lookup/hit/miss/insertion/eviction; lowering; variable/basis mapping;
masks/environment; restriction binding; kernel; intermediate allocation/release;
reinflation/materialization; conversion; required API guards; serialization,
delivery and cleanup. Define exclusive boundaries or explicitly report a combined
span where separation would distort execution. Show unresolved residuals.

### Measurement rules and limits

- At most **two hours of local performance execution**, plus necessary focused
  correctness checks. At most **three isolated prototype candidates total**.
  No external spending. Review the queue after the initial observations and stop
  early if no material, testable opportunity remains.
- Routine widths at most16, at most8 family variants, at most64 KiB of explicit
  output per result; k20 only for the existing reduced/refusal cases. Predeclare
  source/program sizes and refuse accidental expansion. Restrict workers to
  ten seconds per individual diagnostic call and a total worker budget. Stop a
  worker on observed memory above 1 GiB; report the available monitoring mechanism
  and its limitations rather than claiming a hard OS cap without one.
- Two warmup blocks, at most 21 measured blocks, at most 64 calls per small API block
  or 4 family calls per block. Use two independently launched paired runs for
  shortlisted effects. Balance baseline/candidate order and record its seed/order.
  Count every timed invocation against the budget; do not repeat until a desired
  result appears. Preserve disagreement and negative results.
- Use genuinely isolated baseline/candidate state. Separate fresh-worker controls
  from alternating resident comparisons. Verify import/cache isolation before
  trusting resident comparisons. Record Python/dependency versions, source and
  config bindings, native-thread environment values, GC treatment and available
  host/load metadata. Do not globally reconfigure the user's machine.
- Keep uninstrumented wall/process-CPU timings separate from phase tracing,
  cProfile, helper counts, allocation/tracemalloc and object-retention passes.
  Preserve zero CPU-resolution samples; use null for unavailable measurements.
  Profiler percentages cannot be transferred mechanically to uninstrumented time.
- For every measured cell record raw block totals and normalized call times,
  caller boundary, phase wall/CPU and shares within that capture, hot-helper call
  counts/mean costs, source DAG nodes/edges, CM nodes, flat instructions, support
  widths/live width, sharing, materializations/output bytes, and practical peak/
  retained allocation data. Record cache axes, lookup/validation/adoption work,
  entries and graph retention separately. Unknown is preferable to guessed data.
- Include exact independent output checks, variant completion/check counts,
  compile/program identities and refusal/exception behavior. Construct references
  outside kernel timing while retaining their cost in complete harness accounting.
  Exhaustively check these small fixtures where practical; keep q64/permuted/all-
  fixed and reduced-output sentinels. Sampling is not exact verification.
- Use incremental or factorial treatments when observer, provenance, wrapper,
  cache and engine changes interact. Show interactions instead of allocating
  overlapping percentage shares. If estimating a maximum possible saving from a
  phase, state assumptions and use a denominator from the same matched capture.
- Retain the prior review margins as diagnostic flags: an effect exceeding both
  5% and 2 microseconds per API call, or 5% and 0.05 ms per family, in both independent
  runs. They are screening thresholds, not significance tests, pytest assertions,
  promises of general improvement or excuses to hide smaller consistent effects.
- Stop an affected experiment on wrong output, broken invariant, output/resource
  breach, unexplained retained growth or evidence/protected-file change. Keep its
  failed record. Continue only safe independent analysis until the cause is clear.
  Ask before exceeding a bound; do not discard unrelated completed work.

## Stage 4 — conclusions and implementation decisions

Label claims consistently as **measured**, **code-supported inference**,
**hypothesis** or **unknown**. Classify material costs as inherent explicit-output
cost, task/algorithm mismatch, CM representation, CM-family reuse management,
current Python/runtime implementation, wrapper/lifecycle, output conversion/
delivery, comparator preparation, or unresolved. Multiple interacting mechanisms
may share a measured span; do not manufacture exact independent shares.

Directly answer:

1. Which remaining costs dominate actual callers after the repairs, and which
   material gaps are still unassigned? Did any measurement blind spot change the
   interpretation of an earlier result?
2. Which new opportunities are supported, which earlier deferred/rejected ideas
   should stay closed, and what new evidence would justify reopening them?
3. Does CSE-flat's smaller representation still explain its advantage after
   matching sharing, primitives, basis, cache state and delivery?
4. How much public/family overhead is necessary contract work, optional observation,
   benchmark reporting, repeated preparation or implementation-specific structure?
5. Are warm digest preparation, subtree adoption or family mutation costs large
   enough to justify follow-up? What work is actually avoided by each cache hit?
6. Are binding/mask or words allocation/conversion costs now material when isolated?
   Which existing caches already cover proposed reuse?
7. Which kernels are competitive on truly matched tasks, and which apparent wins
   only move preparation, consume less output, change validation or change algorithms?
8. What scales with live variables, source edges, sharing, support width, program
   length, mutation and output size? What can amortize, under what ownership and
   lifetime assumptions, and with what retained-memory or correctness cost?
9. Did any repair introduce a repeatable regression or a correctness/lifecycle
   defect? Separate a diagnostic-row tradeoff from unchanged-core performance.
10. Which changes merit a small implementation task now, which require broader
    representation/API decisions, and which should be skipped? What remains
    impossible to conclude without new evidence or confirmation authorization?

Rank only supported opportunities. For each give the exact mechanism/code surface,
matched measured effect and uncertainty, task applicability, plausible saving
ceiling, memory/complexity risks, invariants and tests, dependencies and smallest
reviewable implementation scope. A prototype effect is not an accepted production
change. Treat readability-only cleanup as such, with no invented speed claim.
Do not recommend a broad rewrite merely because the kernel is small.

## Deliverables and completion

Create a new, unused directory:
`docs/audits/2026-09-15-cm-missed-speedups-deep-dive/`.

Deliver at least:

- `PLAN.md`: frozen scope, hypotheses/cases, exact bounds and amendments.
- `EVIDENCE_REVIEW.md`: validity decisions, timer/contract/import/cache issues,
  exact predecessor references and known baseline failures.
- `EXECUTION_MAP.md`: current caller paths, exclusive/combined boundaries and
  absent phases; distinguish changes from the prior maps.
- `HYPOTHESIS_LEDGER.md`: novel/reopened/already-closed ideas, falsifiers, tests,
  findings and keep/defer/reject/unresolved status, including negative results.
- `PROFILE_RESULTS.json` plus immutable raw records: sources/inputs/configs,
  timing/count/memory/scaling/cache/correctness data with treatment labels.
- `TIME_LEDGER.md` and `ROOT_CAUSE_MATRIX.md`: absolute caller/phase costs, valid
  shares, interactions, comparisons and unresolved material residuals.
- `OPPORTUNITIES.md`: ranked evidence-backed opportunities and excluded shortcuts.
- `FOLLOW_UP_IMPLEMENTATION_PLAN.md`: concrete small repair/optimization steps,
  acceptance tests and decisions needed, without shipping them during this audit.
- `REPORT.md`: a rigorous explanation for a reader who understands the mathematics
  but has not read every implementation file; directly answer the ten questions.
- `AUDIT_MANIFEST.json` and a verification entry point: exact artifact/source/input/
  predecessor hashes, environment and run accounting, known limitations, and
  commit-aware content verification separate from historical Git checkpoints.

Finish with meaningful instrumentation/prototype correctness tests and applicable
project checks. Report pre-existing failures without rewriting their evidence.
Reverify predecessor contents and protected worktrees. Review Git status and diff;
account for every changed/new file, leave work uncommitted/unpushed, and state
explicitly that no scientific disposition changed. Give a concise recommendation
on whether further implementation is justified and what evidence/approval it needs.
