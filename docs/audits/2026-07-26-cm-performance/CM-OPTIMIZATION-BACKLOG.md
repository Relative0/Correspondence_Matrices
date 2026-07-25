# CM Optimization Backlog

Date: 2026-07-26

Implemented items are recorded in `CM-PERFORMANCE-AUDIT.md`. This file retains
the completed output-budget prerequisite for traceability, followed by
remaining work ordered by expected real-world value and prerequisites.

## 1. Central explicit-output budget (completed continuation)

- **Priority:** P1
- **Relevant code:** `cm_bench.cm_equivalence_check`,
  `cm_ir.materialize_cm`, `cm_ir.materialize_hybrid_no_reinflate`, partial/family
  runners, remote protocol.
- **Evidence:** complete output remains \(2^k\); some direct equivalence paths
  call no-reinflate without a maximum-output guard. Guards differ by workflow.
- **Root cause:** feasibility policy is expressed in caller-specific flags
  instead of one artifact budget.
- **Recommendation:** define a typed budget covering maximum output bits/bytes,
  temporary bytes, and allowed reduced output. Every entry point must return a
  typed `ok`, `reduced`, `refused`, `timeout`, `oom`, or `unvalidated` status.
- **Expected impact:** prevents accidental exponential allocation and survivor
  bias; makes practical limits observable.
- **Risk/scope:** medium; public status semantics and remote protocol need a
  compatibility plan.
- **Dependencies:** agreed output contract and status schema.
- **Validation:** exact boundary tests at 15/16/17/18/20/24/32 live variables,
  refusal tests, reduced-output tests, remote round trips, schema regression.
- **Disposition:** implemented. See `OUTPUT-BUDGET-CONTINUATION.md`.

## 2. Byte-budgeted cache policy and telemetry

- **Priority:** P1
- **Relevant code:** bigint/words environment caches and bound programs in
  `bitset_backend.py`; IR and alignment caches in `cm_ir.py`; truth-table caches
  in `cmbench/context.py`; pool cache in `cm_parallel.py`.
- **Evidence:** caches are bounded by entries. One high-support words environment
  or bigint mask can retain far more memory than many small entries. Thread-safe
  scratch now scales per active thread.
- **Root cause:** cache APIs expose counts/hits, not retained bytes or a process
  budget.
- **Recommendation:** measure retained byte estimates, set per-cache and global
  byte limits, use explicit eviction, expose hits/misses/bytes/evictions, and
  document thread lifetime.
- **Expected impact:** predictable long-running and remote-worker memory.
- **Risk/scope:** medium; size estimation for Python integers/object graphs is
  approximate.
- **Dependencies:** output budget and worker concurrency policy.
- **Validation:** cold/warm memory curves, mixed-width eviction, concurrent
  requests, cache invalidation, repeated process RSS plateau.
- **Disposition:** implement next together with item 9 worker admission.

## 3. Frozen distinct-expression regression corpus

- **Priority:** P1
- **Relevant code:** `cmbench/corpus.py`, `run_bench`, V4 corpus artifacts.
- **Evidence:** the 49-record V4 corpus contains repeated expression hashes;
  controlled support 8/12/16 each uses one expression across seven ambient
  bindings. Seeded generation may drift across NumPy versions.
- **Root cause:** the corpus was designed partly for ambient-binding analysis,
  not independent formula inference or a committed correctness gate.
- **Recommendation:** commit SHA-addressed formulas with expected truth digests,
  support, operator counts, source/license, and workload cluster. Include
  distinct formulas per stratum.
- **Expected impact:** reproducible differential testing and statistically valid
  paired comparisons.
- **Risk/scope:** low to medium; data provenance and repository size.
- **Dependencies:** corpus licensing and frozen serialization version.
- **Validation:** clean-checkout replay under multiple Python/NumPy versions and
  `PYTHONHASHSEED` values.
- **Disposition:** implement before another publication benchmark.

## 4. Corpus replay for every workflow

- **Priority:** P2
- **Relevant code:** equivalence, partial-context, expression-family, and
  operator-difference runners in `cm_bench.py`.
- **Evidence:** JSONL replay is integrated only into the normal single-expression
  runner; other workflows regenerate inputs.
- **Root cause:** transitional monolithic runners own their generation logic.
- **Recommendation:** separate workload definition from execution and let every
  runner consume immutable IDs/hashes.
- **Expected impact:** repeatable comparisons and easier regression isolation.
- **Risk/scope:** medium; schema preservation.
- **Dependencies:** item 3 and workflow-specific serialized metadata.
- **Validation:** old schema tests, deterministic replay, hash propagation to raw
  and summary output.
- **Disposition:** implement after item 3.

## 5. Lazy CLI/workflow imports

- **Priority:** P2
- **Relevant code:** top-level imports in `cm_bench.py`,
  `cmbench.availability.detect_backends`, optional backends.
- **Evidence:** cold profile spent 3.712/4.860 s in imports and 1.501 s in
  backend discovery; `run_bench` itself accumulated 1.210 s.
- **Root cause:** the CLI imports most backends and workflows before parsing
  flags, then availability detection imports optional modules.
- **Recommendation:** keep parser/config imports light, load only selected
  workflows/backends, and cache one availability result.
- **Expected impact:** materially faster `--help`, smoke tests, and short
  developer iterations; no core kernel change.
- **Risk/scope:** medium; module globals and compatibility aliases are widely
  used.
- **Dependencies:** stable config/context boundary.
- **Validation:** cold-start A/B in fresh processes, all CLI/schema tests,
  optional-backend present/absent matrix.
- **Disposition:** implement as a separate reviewable change.

## 6. Integrate prepared evaluation with an explicit break-even policy

- **Priority:** P2
- **Relevant code:** `PreparedFlatEvaluation` in `bitset_backend.py`; repeated
  execution in `cm_bench.time_backends_on_expr`.
- **Evidence:** V4 prepared evaluation improves small-support repeated bindings
  but is neutral or slower around support 12–16. The normal repeat loop still
  calls the generic wrapper.
- **Root cause:** preparation exists as an API/experiment but not as a dispatcher
  choice with accounted setup cost.
- **Recommendation:** measure preparation plus 1/10/100/1000 queries across
  support and expression shape; opt in only beyond a tested break-even point.
- **Expected impact:** lower repeated-query latency at small support without
  regressing larger cases.
- **Risk/scope:** medium; stale bindings, fixed-map cache keys, and concurrency.
- **Dependencies:** frozen corpus and byte-budgeted cache.
- **Validation:** paired exact output, preparation included/excluded tables,
  invalidation tests, concurrent binding tests.
- **Disposition:** defer pending break-even surface.

## 7. Fast/full test tiers and CI matrix

- **Priority:** P2
- **Relevant code:** `tests/`, new `requirements-dev.txt`.
- **Evidence:** full tests take about 68 seconds, mostly subprocess integration
  tests; the project venv previously lacked pytest; no CI configuration exists.
- **Root cause:** no declared developer environment or test tiers.
- **Recommendation:** define a core correctness tier, a CLI/integration tier,
  and opt-in remote/CUDD/performance tiers. Run Windows and Ubuntu with supported
  Python and minimum/current dependencies.
- **Expected impact:** faster safe iteration and cross-platform confidence.
- **Risk/scope:** low; avoid duplicating test selection in many places.
- **Dependencies:** CI provider decision.
- **Validation:** tier union equals full collection; clean-environment install.
- **Disposition:** `requirements-dev.txt` done; tiers/CI remain.

## 8. Define the zero-variable contract

- **Priority:** P2 correctness
- **Relevant code:** `BenchmarkConfig.validate`, AST/generators, constant handling
  in the IR.
- **Evidence:** configuration accepts size zero, but random generators require at
  least one variable and the public AST has no constant node.
- **Root cause:** empty-input semantics were never specified.
- **Recommendation:** either reject `n=0` at validation or expose a constant
  expression contract consistently across all backends.
- **Expected impact:** removes a malformed-input ambiguity.
- **Risk/scope:** low if rejected; medium if constants become public AST nodes.
- **Dependencies:** mathematical/API decision.
- **Validation:** CLI/config/backend tests for the chosen behavior.
- **Disposition:** stop and decide; do not guess.

## 9. Threaded worker concurrency and memory limits

- **Priority:** P2
- **Relevant code:** `cm_remote_worker.ThreadingHTTPServer`, thread-local words
  scratch, remote request limits.
- **Evidence:** thread-local scratch fixes corruption and preserves concurrency,
  but scratch memory is now proportional to active same-program evaluations.
  `ThreadingHTTPServer` does not impose a worker bound.
- **Root cause:** concurrency was implicit and had no memory admission policy.
- **Recommendation:** add a configurable bounded executor or semaphore, reject
  requests whose estimated concurrent memory exceeds budget, and expose queue,
  active-worker, and rejection telemetry.
- **Expected impact:** predictable service memory and latency under load.
- **Risk/scope:** medium; queueing/backpressure behavior becomes public.
- **Dependencies:** items 1 and 2.
- **Validation:** mixed-size load test, identical/different requests, bounded RSS,
  cancellation/error handling.
- **Disposition:** implement with cache budgeting.

## 10. Tiled/streaming exact execution

- **Priority:** P3
- **Relevant code:** words evaluator and `CM_TILED_WORDS_EVALUATOR_DESIGN_2026-07-23.md`.
- **Evidence:** final words output and environment are monolithic; complete
  output remains exponential. The design is not implemented.
- **Root cause:** existing APIs return one integer/vector, which requires the
  complete artifact in memory.
- **Recommendation:** create a separate iterator/chunk API for consumers that
  accept streaming output, hashes, counts, or bounded queries. Never replace the
  complete-output API silently.
- **Expected impact:** lower peak memory and larger feasible support for
  streaming-compatible tasks.
- **Risk/scope:** high; new artifact semantics, ordering, cancellation, and cache
  design.
- **Dependencies:** a real downstream task and output budget.
- **Validation:** exact concatenated output, chunk-boundary fuzzing, peak RSS,
  throughput, early cancellation, cross-platform ordering.
- **Disposition:** research prototype only.

## 11. Real workload and task-matched backend campaign

- **Priority:** P3 research
- **Relevant code:** all benchmark workflows and external dataset adapters.
- **Evidence:** no validated real-domain dataset; current comparisons are
  synthetic and sometimes compare unlike artifacts.
- **Root cause:** benchmark development preceded workload acquisition.
- **Recommendation:** use public EDA/circuit, policy/configuration, and
  compiler-analysis workloads. Measure parsing, construction, preparation,
  query, memory, correctness, and amortization against task-matched CUDD/AIG/SAT/
  packed baselines.
- **Expected impact:** determines whether CM has end-to-end practical value.
- **Risk/scope:** high; external data, new adapters, and statistical design.
- **Dependencies:** item 3, same-environment backends, workload licenses.
- **Validation:** pre-registered outcomes, formula-cluster bootstrap, at least
  two materially different machines, complete artifact comparability.
- **Disposition:** highest-value research, not an immediate code optimization.

## Parked or rejected

- **Universal multiprocessing default:** parked. Existing activation and speedup
  evidence is negative; do not hard-code workers.
- **GPU/distributed implementation:** parked until a real workload amortizes
  transfer and setup.
- **Sparse truth-table default:** rejected because it changes the output artifact
  and query costs.
- **Approximate or mixed-precision execution:** rejected for the exact default;
  Boolean output already has exact one-bit precision.
- **Dense CM reinflation as a benchmark shortcut:** rejected; no-reinflate is the
  semantically equivalent lower-copy path when a matrix is not required.
- **Performance assertions in ordinary pytest:** rejected; hardware variation
  makes them unstable. Keep measurement in opt-in tooling.
