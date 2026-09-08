# Prompt for the next independent non-neural CM workload

Recommended execution: paste the prompt below into a new Codex task. A separate task
keeps workload discovery and preregistration isolated from the stopped H2/H3/H6 panel.
Thread separation is not itself proof of workload independence; the new task must also
establish that the workload or trace existed for a real purpose before it was considered
for CM architecture testing.

## Copy-ready prompt

Continue the exact, non-neural CM architecture investigation in
`C:\Users\brian\Documents\CM_Computation`, using a fresh worktree based on the latest
reviewed source. If
`codex/cm-h2-h3-h6-gates-20260908` has not yet been merged, base the worktree on that
remote branch and record its exact commit; otherwise use current `origin/main`.

Treat these dispositions as binding:

- `docs/research/CM_HARDWARE_BEHAVIOR_CHANGE_CORPUS_RESULT_2026_09_04.md`;
- `docs/research/CM_ARCHITECTURE_AUDIT_DISPOSITION_AFTER_C38_2026_09_03.md`;
- `docs/research/CM_H2_H3_CURRENT_SOURCE_PROFILE_GATE_RESULT_2026_09_08.md`;
- `docs/research/CM_H6_FRESH_PROCESS_MEMORY_AND_ESTIMATOR_RESULT_2026_09_08.md`.

Begin with a discovery-and-admission phase for one genuinely independent active CM
workflow. Independence must come from provenance, not merely from using a new task:
the workload, trace, application need, or revision sequence must have existed for a
real purpose before its possible CM result was considered. Prefer an existing local,
maintained, user-originated workflow with a concrete caller-visible artifact and exact
task contract. Do not select a workload because it appears likely to favor CM, compact
keys, dense layout, a memory estimator, native execution, or incremental compilation.

Before opening decision-bearing timing or memory results:

1. Record the source checkpoint and preserve unrelated dirty files in the original
   checkout.
2. Inventory candidate real workflows using read-only metadata and source contracts.
   Establish creation/provenance, active use, inputs, outputs, caller-visible semantics,
   scale, repetition/reuse pattern, and why selection is independent of the stopped
   panels. Do not read secrets, private databases, credential stores, or unrelated user
   content.
3. Admit exactly one workflow by a declared provenance/task rule. If no workflow meets
   the rule, stop with `no_independent_active_workflow_identified`; do not substitute a
   public repository, generated benchmark, or another convenient workload post hoc.
4. Freeze the workload and all exclusions; exact independent oracle; arm definitions;
   cold and reused lifecycles; timing boundaries; retained and peak-memory accounting;
   ordering/hash requirements; repetitions; regression floors; low-sharing controls;
   source closure; failure handling; and continuation criteria.
5. Separate source discovery, instrumentation validation, profiling, and candidate
   evaluation. Do not change production behavior during discovery or profiling.

The initial experiment must be profile-first and hypothesis-neutral: attribute complete
caller-visible cost across construction, canonical keys/hashing/interning,
serialization, dense lifting/allocation/conversion/copies, restriction preparation,
evaluation, delivery, cache/reuse boundaries, and any native boundary that the admitted
workflow actually exercises. Use the fresh-spawn H6 protocol only as measurement
infrastructure; do not reuse its cases to choose the workload or refit its stopped
estimator.

Require exact independent-oracle agreement, stable output ordering and hashes,
exhaustive small-function tests where applicable, identity-sharing versus tree-expanded
metamorphics, low-sharing regression controls, cold/reused measurements, signed retained
and peak memory endpoints, and an independent standard-library summary replay. Retain
all failures, zeroes, refusals, and unfavorable rows.

Do not reopen H2, H3, H6 routing, or H9 from the old data. A component may continue only
if it passes a materiality and prevalence gate frozen for the newly admitted workflow.
If nothing passes, close the phase without an implementation candidate. If exactly one
component passes, freeze and test only one small reversible research candidate against
unchanged current source. Do not fit or enable a runtime selector.

H9 remains deferred unless the admitted workload itself is a real, independently
existing cross-revision workflow with exact historical provenance. Do not add replacement
repositories, run Yosys on the failed September 4 corpus, build further incremental-
hardware machinery, or reinterpret BlackParrot as held-out evidence.

Run the focused tests and `scripts/cm_research_check.py`. Do not commit, push, publish,
change defaults or website claims, or use RunPod without separate authorization. Work
autonomously through the frozen local gate, then report the go/no-go result. Prepare an
exact RunPod authorization request only if every local correctness, stability,
materiality, regression, and independent-replay condition passes.

In the result, distinguish clearly among: workload independence established or not;
measurement validity; component materiality; candidate eligibility; candidate result;
production status; and whether a RunPod request is permitted.
