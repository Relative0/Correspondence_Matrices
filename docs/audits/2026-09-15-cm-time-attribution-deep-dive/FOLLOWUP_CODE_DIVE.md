# CM-family code-dive candidates

This note answers the follow-up question after the diagnostic audit was sealed.
It recommends investigation and cleanup boundaries, not routing changes or
performance claims. Every candidate preserves the existing mathematical and
public output contracts until evidence supports a separate change.

## Priority 1 — persistent family compilation and cache eligibility

**Why:** This is the clearest CM-family-specific cleanup target. Persistent
compilation performs a structural-sharing prepass, canonical digest work,
eligibility selection, cache lookup/update, and sometimes foreign-node adoption.
Shared associative classes switch the implementation from subtree reuse to
root-only reuse. Those responsibilities are coupled in
`compile_expr_to_cm_ir_persistent` (`cm_ir.py:285–391`).

**Measured signal:** repeated identical roots realized seven root hits and
reduced core family time from 2.844 to 2.120 ms. The shared family produced
52 hits but no root hit and slowed from 3.462 to 3.862 ms. The zero-hit
composition family slowed from 2.880 to 3.380 ms. Mutation-rate treatments also
show that a hit count is not a useful proxy for time saved.

**Code-dive boundary:** separate and account for sharing/eligibility discovery,
digest construction, lookup, miss construction, local adoption, insertion,
eviction, and retained bytes. Check whether the structural UID work is repeated
when the same information already exists, and document the root-only invariant
that protects canonical shape. A cleanup should first make these lifecycle
states explicit and testable; it should not weaken cache-key or shape soundness.

**Evidence needed:** exclusive low-perturbation spans, hit type and reused-node
weight, eviction pressure, retained graph bytes, and exact shape/output checks
on the existing sharing and foreign-node tests. This belongs in this thread
because it directly reuses the audit's cases, definitions, and cache findings.

## Priority 2 — public wrapper and diagnostic-path convergence

**Why:** `materialize_hybrid_no_reinflate` has a diagnostics-free flat fast path
and a generic instrumented path. Supplying a diagnostics dictionary changes the
executed control path. `_cm_family_workload` always supplies diagnostics, and it
passes `words_eval` explicitly while flat selection can rely on module-scoped
defaults (`cm_bench.py:946`; `cm_ir.py:2033–2276`). This makes observation,
configuration, and execution lifecycle harder to reason about.

**Measured signal:** the public-minus-bare resident increment is 19.6–30.5 µs
across disclosed cases, or 30.3–88.5% of the public median. For the k16 example,
the increment is about 24.5 µs, 39.3% of public time. These are incremental
whole-call differences, not an exclusive wrapper timer.

**Code-dive boundary:** map budget node counting, output-basis construction,
engine selection, flat-program lookup, binding, result wrapping, and diagnostics
recording into a common control flow. Verify that enabling diagnostics observes
the same semantic and engine path rather than selecting a materially different
one. Treat correctness guards and result metadata as public-contract work.

**Evidence needed:** branch-equivalence tests with diagnostics on/off, explicit
evaluation configuration, exclusive wrapper phases, and output-budget failure
cases. This should follow the cache lifecycle dive or run beside it in a new
thread only if implementation work is split between owners.

## Priority 3 — family benchmark timing and validation contracts

**Why:** The benchmark code currently makes correct interpretation difficult.
Family reference construction occurs outside backend totals; per-variant
compile/eval spans stop before conversion and comparison; the family total
includes those operations; direct environment preparation has another boundary.
The Y02–Y05 worker similarly includes exhaustive validation and delivery work
inside task totals but outside named stages. This is primarily evidence-quality
cleanup, though it also exposes repeated work.

**Measured signal:** Y05 CM diagnostic time is 68.9% exhaustive semantic guard
and 28.4% shared SymPy minimization. Historical CM task timers are only
0.038–0.491% of several fresh-process caller totals. The historical CM-SAT
unnamed residual is 88.2% of task time, but its exact internal causal share is
unresolved. Calling any of these values a kernel time is misleading.

**Code-dive boundary:** define one nested timing schema with caller, ingress,
preparation, execution, required delivery, optional benchmark oracle, and
lifecycle spans. Ensure child spans are exclusive or explicitly marked
inclusive. Keep reference construction and scientific correctness checks, but
state whether they are inside the user-facing contract or harness-only.

**Evidence needed:** arithmetic conservation tests, a diagnostics-disabled
whole-call run kept separate from profiling, and fixture-based assertions that
every delivered output is consumed. This cleanup has high value even if it
does not make CM faster.

## Priority 4 — CMIRBuilder responsibility and retained metadata

**Why:** Cold common-executor CM was slower than CSE-flat in all 13 disclosed
cases, while resident execution was within 10% in 11. The difference lies mainly
before the common packed executor: structural UID preparation, recursive build,
canonical rewrites, support propagation, key construction, sorting, and
interning. `CMNode` also retains public structural keys and support tuples.

**Measured signal:** CSE and CM prepared execution often reached parity, but CM
traced retention exceeded CSE in 12 of 13 cases. This is a bounded development
signal, not a production memory ranking. CM sometimes lowered fewer primitives,
showing that rewrite work can be useful rather than merely overhead.

**Code-dive boundary:** clarify ownership of structural identity, canonical
ordering, rewrite decisions, support summaries, public keys, and builder-local
UIDs. Inspect repeated traversals and Python object retention without removing
information required by CM consumers. Preserve canonicalization, separately
allocated-equal-subtree, deep-tree, and foreign-node guarantees.

**Evidence needed:** one-pass counters and retained-object graphs, plus factorial
ablations that preserve output and separately retain/remove each metadata class.
Because this is correctness-sensitive and broader than instrumentation cleanup,
it should be a new task after the first three boundaries are understood.

## Priority 5 — binding, liveness, and packed result conversion

**Why:** This is a narrower implementation cleanup. Flat binding combines fixed
key construction, lookup, validation, mask construction and template creation.
Word execution combines environment lookup, scratch management, kernel calls,
and ndarray-to-integer conversion. Bigint execution combines logical operations
with allocation/refcount release. Existing phase data cannot divide them.

**Measured signal:** once prepared, CM-flat and CSE-flat are usually close.
The fixed-structure k4–k18 ladder shows growth from output width while CM node
and instruction counts stay fixed. That points to mask/output width rather than
CM representation as the main scaling variable in these cells.

**Code-dive boundary:** document cache ownership and lifetime, separate binding
state from execution state, and make conversion/liveness accounting observable.
Do not treat a lower-level rewrite as a CM-specific scientific gain unless the
same packed primitives and output contract are held constant.

**Evidence needed:** allocation/native-call observation, cache hit/miss spans,
and fixed-width/value factorials. This is lower priority because no large
CM-specific kernel defect was isolated.

## Recommended sequence

1. Persistent family cache lifecycle and eligibility.
2. Public wrapper/diagnostic path convergence.
3. Family benchmark timing and validation schema.
4. CMIRBuilder retained metadata and traversal ownership.
5. Binding/liveness/conversion internals only if the earlier dives leave a
   material unexplained remainder.

The first three can be investigated together in this thread because they share
the audit harness, cases, and terminology. The CMIRBuilder cleanup is large and
correctness-sensitive enough for a new task with a compact handoff from this
audit. No change should consume held-out confirmation inputs or alter routing,
defaults, or scientific dispositions during the cleanup phase.
