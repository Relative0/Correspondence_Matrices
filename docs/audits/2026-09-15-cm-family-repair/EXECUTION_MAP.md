# Repaired execution and observation boundaries

Implementation base: e334de594262059cc18cf37eaab56b0f79e94843. The repair branch
starts at 4d9b869fb7b22eb6263ef613b5a9d41fcbbb78dd, which adds the predecessor audit.

## Public no-reinflate API

`evaluate_compiled` forwards explicit flat and words choices to
`materialize_hybrid_no_reinflate`.

1. Resolve explicit settings or existing module defaults. Preserve the early
   invalid-threshold exception on the historical fast treatment.
2. Prepare fixed map and requested, live and output bases.
3. Read cached CM node count; estimate full and reduced outputs; decide and
   enforce byte, variable and temporary limits. Admission occurs once.
4. Select the packed engine using the actual delivered width, or enter the
   existing NumPy fallback. The automatic words threshold remains 16.
5. Execute and deliver the same result/status/budget objects. The diagnostics-off
   fast return skips diagnostic delivery; generic mode retains accumulation.

The words path includes binding, words allocation/execution and integer conversion.
The flat evaluator includes cached lowering, binding, template copying and the
inline opcode loop. Its exclusive traced span is **not** pure logical arithmetic.
The NumPy fallback additionally aligns and expands the output tensor and produces
the uint8 truth vector. None of these paths now performs a preliminary budget
plan followed by a second plan on fallback.

## Persistent compilation

`compile_expr_to_cm_ir(persistent_cache=True)` enters the persistent compiler:

- Initialize diagnostics/builder and prepare the structural sharing eligibility
  plan. This remains outside legacy `ir_compile_time_s`.
- Shared associative classes select the existing root-only regime. Compute the
  digest/options key, look up and update recency. A miss consumes the **same
  call's** UID/sharing plan through public builder dispatch; a hit returns the
  retained root.
- The other regime traverses subtree keys and builds missing parents, including
  foreign-node adoption when necessary. A root hit is possible in this regime
  too: hit position and reuse regime are separate axes.
- Insert/evict using the existing capacity and policy; report entry count.

The private prepared plan pins the exact immutable source root. It lives only
through one synchronous build, restores previous state on failure/reentry, and
is ignored when a subclass substitutes another root or disables sharing-aware
flattening. It is not a persistent source cache. Digest collision assumptions,
canonical keys, shared-class boundaries, foreign adoption and cache capacity are
unchanged.

## Family caller

`time_expression_family_workload` prepares configuration and observer, then:

1. Copy variant handles, construct reference truth vectors when eligible, and
   compute family structural diagnostics.
2. Prepare/select the direct evaluator and any environment. Consume each
   result, convert it for the oracle, and check it.
3. Run CM without persistent reuse, then with reuse if requested. Each backend
   resets the persistent cache once; variants within a cached family share it.
4. For each CM variant: compile, evaluate, collect actual engine/output metadata,
   convert/check the result, and count completed/checked/correct variants.
5. Aggregate legacy fields and provenance, and perform any enabled ROBDD
   algorithm comparison. The delivered artifact is the statistics row.
6. Outside the nested capture, attach contract/schema fields and serialize its
   trace. The separate outer observer measures this remainder as well.

Reduced outputs are expanded **only for comparison with an already constructed
small full oracle**. This validates omitted variables; it does not change the
public result or charge oracle expansion to the kernel.

## Timing schema

`--family-profile-timing` / `BenchmarkConfig.family_profile_timing` defaults off.
Supplying a `PhaseRecorder` explicitly also opts in and retains failure records.
Each record has schema, boundary, parent, status, inclusive wall/process CPU and
exclusive wall/process CPU. Exceptions retain their phase/type and propagate.

Only exclusive records inside **one capture** form a partition. The parent's
exclusive remainder includes unnamed harness work, residual control and observer
overhead. Adding inclusive parents to children, summing legacy timers with these
records, or transferring their shares onto a clean timing run is invalid.

The legacy family total still includes oracle conversion/comparison and excludes
initial reset/basis setup and some returned-row aggregation. Legacy per-variant
time still stops after public evaluation. The old fields retain those meanings;
their elapsed values can change because the workload now also collects metadata.

Summary grouping includes schema, requested and actual engines (including mixed
counts), output widths/statuses and the serialized execution contract. Skipped
cache paths remain visible as `not_run`, with zero consumed/checked variants.

Process creation, command-line parsing, imports, input generation/DAG decoding and
CLI file delivery are outside this function. `measure.py` records imports from
Python entry, not OS startup. `diagnose.py` observes entry-to-return and explicitly
reports the gap outside its nested capture; it does not invent startup shares.

## Unchanged controls and frozen Y02–Y05

Direct `eval_expr_bitset` is identity-memoized recursive AST evaluation. Structural
CSE-flat retains sharing without CM support/key/rewriting structures. Bare CM-flat
shares packed primitives with that bigint control. Their prepared calls have no
CM public admission/result-wrapper phase. Raw nonmemoized AST, SAT/count/BDD,
assignment-query and simplified-expression findings remain in the sealed audit;
these repairs do not change those algorithms.

Y02–Y05 workers are absent from the implementation base. Their frozen records and
code audit are authoritative for their historical boundaries, not a place to
retrofit new percentages. As already recomputed in the predecessor:

| Worker | Work inside task total but outside some named stages |
|---|---|
| Y02 relation | List expansion/packing and digest delivery |
| Y03 assignment batch | Supplied-assignment generation, answer conversion/packing |
| Y04 SAT | Exhaustive scalar validation and witness checking |
| Y04 equivalence | Right-expression parsing and comparison delivery |
| Y05 simplified expression | Semantic vector validation, packing, `srepr`, expression-quality work |

The caller/task gap is measured; its startup/import/transport/shutdown allocation
remains unknown. CM assignment and SAT residual shares (86.937% and 88.209%) are
historical differences, not newly measured oracle phase shares. No worker,
historical field, report, route or scientific disposition was rewritten.
