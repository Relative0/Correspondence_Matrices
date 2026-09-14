# A comprehensive, fair CM benchmark research plan

Research date: 13 September 2026. Status: research and execution preparation, not new performance evidence or authorization to rent compute.

## Executive assessment

There are many credible workloads worth testing. A production deployment is **not** a prerequisite for demonstrating a useful algorithmic improvement. Public engineering models, faithfully translated application inputs, and carefully controlled synthetic experiments can establish real, reproducible gains within their stated tasks. Establishing **production savings**, however, additionally requires an operator's actual request mix, reuse, invalidation, integration costs and operational constraints.

This package recommends **80 test families in nine areas**, supported by **42 primary sources**. These are not 80 independent datasets, downloaded corpora, implemented adapters or completed experiments. Several families deliberately reuse one corpus to ask different questions. The [full catalog](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/CATALOG.md) specifies sources, tasks, sizes, priorities and admission conditions for every family. Its [JSON counterpart](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/CATALOG.json) supports a future runner.

The most valuable first campaign combines hardware logic, product configuration, biological update functions, exact counting, affine systems and synthetic controls. It should test CM against strong native methods as well as CSE-flat and optimized BitSet. SymPy belongs in several explicitly matched task lanes; its historical timing advantage is worth investigating, but not importing into a modern scoreboard without qualification.

The proposed RunPod envelope is **up to 16 total pod-hours and $50, whichever limit is reached first**, with one active pod at a time. These are planning caps, not a price quote or approved spending. A 2,400-base-case target is a coverage goal to calibrate, not a promise that every method, size and repetition fits those limits. The [execution prompt](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/RUNPOD_MEGA_PROMPT.md) requires local correctness gates, an input freeze, a live quote and explicit cloud approval before launch.

## 1. What the existing evidence does and does not establish

### The attached 0.89 / 1.00 / 3.09 comparison

The supplied image reports a bare CM evaluator taking 0.89 times the CSE-flat control time, while the CM wrapper/whole call takes 3.09 times the control time. That is evidence of a narrower evaluator improvement and a whole-call regression on the depicted synthetic case. It does not by itself establish an amortized win.

If the extra wrapper cost is paid for **every** call, more repetitions retain the regression. If some of that cost can be moved into a reusable preparation object, an implemented prepared API may cross over. That requires new full-lifetime measurements; it cannot be inferred by simply dividing the chart's overhead by its evaluator saving. The display also does not identify an actual deployment or its request history.

The earlier phrase “no deployed workload has demonstrated enough reuse” should therefore be read more carefully: **the evidence reviewed here does not establish a deployment with measured, wrapper-inclusive production savings**. It does not establish that deployments were attempted and all failed to reuse the preparation. Neither a negative production result nor the absence of all deployments has been proven by this research.

### The historical SymPy numbers are present

Reaggregation of one local archive produced the following. The ratio is the median of individual recorded SymPy-time / CM-time pairs, not a ratio of aggregate medians.

| Nominal variables | Paired rows | Median recorded ratio | Range |
| ---: | ---: | ---: | ---: |
| 4 | 5 | 5.453 | 2.900–6.437 |
| 8 | 5 | 76.047 | 21.118–195.344 |
| 12 | 5 | 1.638 | 1.516–1.861 |
| 16 | 5 | 1.384 | 0.869–1.665 |

All 20 rows record both correctness flags as true. This supports the user's recollection that substantial differences were measured. It is not a complete audit of every historical archive. Exact inputs, hashes, arithmetic and limitations are retained in the [historical audit](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/HISTORICAL_AUDIT.md).

The inspected [SymPy adapter](C:/Users/brian/Documents/CM_Computation/expr_simplify.py:39) asks for a simplified DNF. The [benchmark timer](C:/Users/brian/Documents/CM_Computation/cm_bench.py:2239) ends before subsequent callable creation and assignment-grid evaluation. CM construction and symbolic simplification are different outputs. Current SymPy documentation also describes an eight-variable default restriction on exhaustive simplification unless `force=True`; larger calls can do less simplification. The abrupt change between 8 and 12 variables is consistent with this mechanism, but the exact historical source/environment binding has not been independently recovered. [SymPy logic documentation](https://docs.sympy.org/latest/modules/logic.html#sympy.logic.boolalg.simplify_logic).

The appropriate conclusion is “historical unlike-task timer differences, requiring matched-task replication,” not “the observations were fabricated,” nor “CM is 76× faster than SymPy generally.” A prior [gap audit](C:/Users/brian/Documents/CM_Computation/CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md:639) criticized the comparator design; that is evidence about past interpretation, not an instruction to exclude SymPy now. SymPy's possible production use is irrelevant to whether a particular API comparison is fair.

Recommended SymPy reruns are fully consumed truth-table generation, `lambdify` assignment evaluation with CSE enabled and disabled, SAT/witness queries, equivalence through an XOR satisfiability miter, and a **separate** expression-simplification study. Keep exhaustive simplification small and bounded. CM alone is not a substitute for a minimizer: a CM-assisted simplification pipeline must return the same kind of expression and report both runtime and expression quality.

## 2. First decide what answer the caller wants

A single “best Boolean algorithm” ranking would be misleading. Separate the following output contracts, including subtypes within a row.

| Task | Required result | Essential comparators |
| --- | --- | --- |
| Complete relation | Every output bit in a declared variable/assignment order | CM full wrapper; optimized BitSet; sharing-aware CSE-flat; packed/tiled native evaluator; CUDD including extraction |
| Concrete evaluations | Answers for supplied assignments or data rows | Compiled direct evaluator; CSE-flat batch; NumPy/SymPy callable; CM lookup/batch; native application engine |
| SAT and witness | Status, or a checked witness when requested | Native CaDiCaL/PySAT; Kissat one-shot; CryptoMiniSat for XOR; admitted CM plan |
| Exact count | Exact integer over the declared universe | Native d4/Ganak exact mode; exact CUDD traversal; CM counting plans; direct enumeration at small sizes |
| Projected count | Number of distinct visible solutions, ignoring hidden-variable multiplicity | Projection-capable exact counter and validated CM projection path |
| Equivalence and semantic difference | Status, counterexample or exact difference count, separately | SAT/ABC miter for status; packed XOR/popcount or exact counter for count |
| Repeated queries/history | Ordered answers under a specified lifetime | Every eligible method with preparation, caches and invalidation enabled fairly |
| Streaming | Complete declared byte stream, or explicit cancelled prefix | Producers plus real consumer cost; no generator-construction-only timing |
| GF(2) algebra | Rank, consistency, count, basis or decomposition, separately | Packed Gaussian elimination; native M4RI; CM-associated affine paths |
| Simplification/synthesis | Equivalent expression/netlist under stated quality objective | SymPy; Espresso/ABC where suitable; CM-assisted pipeline only |
| Weighted inference | Probability/weighted count with stated precision | Native weighted counter/BDD or domain engine; validated CM extension |
| Row-ID set queries | Set/bitmap over actual records | CRoaring; dense words/BitSet; sorted-list control; admitted CM adapter |

For example, proving satisfiability cannot fairly be billed as “faster than generating all assignments.” Conversely, a SAT solver that returns one witness has not completed a caller's full-table request. A BDD must include expansion when the output is explicitly a table, but should not be forced to expand for a count query.

Native competitors matter. [PySAT](https://pysathq.github.io/docs/html/api/solvers.html) exposes incremental assumptions; [CryptoMiniSat](https://github.com/msoos/cryptominisat) supports XOR-aware solving; [M4RI](https://github.com/malb/m4ri) supplies dense binary linear algebra; [CUDD](https://github.com/cuddorg/cudd) and [Sylvan](https://github.com/trolando/sylvan) provide native decision-diagram implementations. Pin and capability-test actual builds, not just package names.

For exact counting, verify precision and modes: the consulted [Ganak repository](https://github.com/meelgroup/ganak) distinguishes its default probabilistic setting from `--prob 0`; approximation fallback must also be disabled for an exact lane. [d4v2](https://github.com/crillab/d4v2) is not interchangeable with every historical d4 executable or command line. A floating-point BDD counting API is not a general arbitrary-precision integer oracle; test large non-power-of-two counts and use an exact traversal where necessary.

## 3. Where the workloads come from

These recommendations distinguish public application-derived inputs, historical engineering benchmarks, application fixtures, reference models, synthetic mechanisms and production traces. None of those labels can be upgraded to production traffic merely because a repository is public or an application domain is industrial.

### Hardware and logic design — 10 families

Start with arithmetic and control functions from the [EPFL combinational suite](https://github.com/lsils/benchmarks), then add independently held-out designs from [Yosys benchmarks](https://github.com/YosysHQ/yosys-bench). The latter explicitly distinguishes mostly synthetic small benchmarks from larger real-design benchmarks. Extensions include ISCAS85 combinational circuits, ISCAS89 next-state logic, [IWLS2005](https://iwls.org/iwls2005/benchmarks.html), and [VTR](https://docs.verilogtorouting.org/en/latest/vtr/benchmarks/) designs. Koios/LogikBench repackaging needs upstream ancestry deduplication, not credit as independent coverage. [Koios provenance](https://github.com/zeroasiccorp/logikbench/blob/main/logikbench/benchmarks/koios/README.md).

Concrete tests: complete output cones; groups of 1/4/16/64 shared outputs; current-state-to-next-state functions; original versus synthesized equivalence; and controlled, verified inequivalent mutations. Sampling should span depth, reconvergence, operator mix and structural size, not just variable count. Preserve sharing in CSE-flat as well as CM.

Whole designs should remain available at native size for symbolic tasks. A bounded cone cut is a useful derived experiment, but treating its cut signals as independent changes the input domain. Either preserve upstream constraints or label it an abstraction. A one-step sequential function is not a reachability or full sequential-equivalence result.

### Configuration and feature models — 10 families

The [SoftVarE Feature-Model Benchmark](https://github.com/SoftVarE-Group/feature-model-benchmark) describes 2,518 models from 41 systems. [UVLHub](https://www.uvlhub.io/) offers additional discoverable collections, including SPLOT and product-domain datasets. These counts identify a useful acquisition pool, not 2,518 independent real-world systems. Releases and repositories can overlap.

Concrete tests: Linux, BusyBox, uClibc/Fiasco and eCos configurations; automotive/finance models; small complete SPLOT/UVL models; smartwatch evolution; dead/core/optional-feature analysis; interactive partial configurations; ordinary and projected counts; and semantic differences across releases.

These are especially attractive for amortization because a model may be loaded once and queried many times. However, generated configuration sessions remain modeled reuse until an operator supplies interactions. Preserve histories in order and split by system/history rather than treating every revision as an independent held-out example.

Product counts require special care. A CNF count over auxiliary encoding variables is not automatically the number of distinct feature configurations. Preserve original-feature mappings and the translation's semantics. Full definitional encodings may have unique auxiliary extensions; mere equisatisfiability is not enough. The catalog includes projected tests, including empty projection, unused visible features and multiple auxiliary extensions.

### SAT, counting and verification — 8 families

Use application SAT/UNSAT cases from [SAT Competition 2025](https://satcompetition.github.io/2025/benchmarks.html), planning and graph-coloring cases from [SATLIB](https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html), and exact-counting instances from [Model Counting Competition public releases](https://mccompetition.org/past_iterations.html). Prefer stable published releases over links labeled draft. Competition collections are valuable stress tests, but their deliberate hard-instance selection does not estimate typical application latency. [Competition design](https://mccompetition.org/2025/mc_description.html).

Retain full-size instances, even when CM refuses expansion. A native solver's success alongside a bounded CM refusal is informative. Keep ordinary, projected and weighted counting separate. Further extensions are package-dependency feasibility through [aspcud](https://github.com/potassco/aspcud) and checked bit-blasting of [SMT-LIB QF_BV](https://smt-lib.org/benchmarks.shtml) inputs against [Z3](https://github.com/Z3Prover/z3). Optimization preferences, word arithmetic and signedness cannot silently disappear in translation.

### Biology, reliability and probability — 8 families

The [Biodivine repository](https://github.com/sybila/biodivine-boolean-models) and a [stable 212-model release](https://zenodo.org/records/8020309) supply published Boolean-network models. Start with local regulatory update functions, then synchronous simulation, fixed points and perturbation contexts. Compare symbolic network tasks against [AEON.py](https://github.com/sybila/biodivine-aeon-py) or native SAT as appropriate. A 100-node network can have small local update support; report both sizes. Free inputs and Booleanized multivalued models require their documented interpretation.

[OpenPRA](https://docs-dev.openpra.org/guides/benchmarking.html) and [SCRAM](https://github.com/rakhimov/scram) provide an entry into static fault-tree work. Repeated basic events must remain the same variable. Test Boolean top-event functions first; exact probability is a separate weighted extension, distinct from rare-event approximations or truncated cut sets.

For Bayesian inference, start with ASIA, CANCER and EARTHQUAKE from the [bnlearn repository](https://www.bnlearn.com/bnrepository/), then consider CHILD, ALARM, INSURANCE and WATER. These are reference models, not CM-ready truth tables. Conditional probability tables, categorical encodings and evidence normalization must be preserved. Do not admit this lane until a weighted adapter is independently checked.

### Policies and data filtering — 6 families

[Cedar integration fixtures](https://github.com/cedar-policy/cedar-integration-tests) include expected decisions, reasons and errors. They can support a bounded propositional policy study against the [native Cedar engine](https://github.com/cedar-policy/cedar). OPA supplies a useful [prepared-policy performance reference](https://www.openpolicyagent.org/docs/policy-performance). Neither source makes arbitrary policy predicates independent Boolean inputs: types, missing attributes, errors, entity relationships and correlations must survive the adapter.

[ClassBench-ng](https://github.com/classbench-ng/classbench-ng) supports synthetic packet-rule models. [Real Roaring datasets](https://github.com/RoaringBitmap/real-roaring-datasets) support row-ID intersection/union/difference workloads against [CRoaring](https://github.com/RoaringBitmap/CRoaring). Record count is not assignment count: one million rows with 32 predicates is not a complete 32-variable truth table. Report native-query and Boolean-kernel lanes separately so parsing and predicate-extraction costs are visible.

### Affine logic and coding — 6 families

Use attributed LDPC matrices from [AFF3CT configuration files](https://github.com/aff3ct/configuration_files), with file-level license and matrix-role verification. Add explicitly synthetic parity, checksum/CRC-like, repeated-right-hand-side, mixed CNF/XOR and decomposition tests. Compare against native M4RI and XOR-aware SAT, not only Python-level CM and BitSet paths.

Affine scalar tasks can grow well beyond 32 columns without constructing all assignments. Independently vary rows, columns, rank, density and right-hand sides. Report a fast generic GF(2) algorithm as such unless a controlled raw-ingress versus CM-ingress comparison isolates a CM-specific contribution.

### Synthetic mechanisms, lifetimes and API controls — 32 families

The remaining catalog entries are 16 synthetic mechanisms, eight lifetime/delivery experiments and eight SymPy/representation controls. They are not filler: they explain where a performance difference comes from and prevent an application sample from hiding a boundary.

Vary independent factors: sharing/no sharing, depth, operator mix, constants/tautologies, satisfiable density, variable order, locality, factor width, projection multiplicity, affine rank and memory pressure. Include equal functions under different syntax, misleading ambient widths, BDD-friendly and BDD-hostile structures, and cheap short-circuit cases where an incumbent should win.

Lifetime tests cover no reuse, repeated identical results, distinct contexts on one model, cache eviction, version churn, serialization/reload and streaming/cancellation. Existing materialized truth tables, such as the [IWLS2026 contest inputs](https://github.com/alanminko/iwls2026-ls-contest/), are suitable for load/query or synthesis tasks, not evidence about AST-to-table construction.

## 4. A reasonable size plan, including 24–32 variables

For explicit relation tasks, use 4/8/12/16/20/24/28/32 variables when feasible, with optional 18/22/26/30 bridge points near a crossover or memory boundary. Do not synthesize missing real-world sizes by silently deleting constraints or padding with irrelevant variables. Keep natural-size source panels and controlled synthetic size sweeps distinct.

For one Boolean output, the packed result occupies `ceil(2^k / 8)` bytes. The following are arithmetic lower bounds, not measured resident memory.

| Output variables k | Packed output | One byte per assignment | k packed input-variable masks |
| ---: | ---: | ---: | ---: |
| 8 | 32 B | 256 B | 256 B |
| 12 | 512 B | 4 KiB | 6 KiB |
| 16 | 8 KiB | 64 KiB | 128 KiB |
| 20 | 128 KiB | 1 MiB | 2.5 MiB |
| 24 | 2 MiB | 16 MiB | 48 MiB |
| 28 | 32 MiB | 256 MiB | 896 MiB |
| 30 | 128 MiB | 1 GiB | 3.75 GiB |
| 32 | 512 MiB | 4 GiB | 16 GiB |

Python bigint overhead, allocation transients, cached intermediates, multiple outputs and consumers can add substantially to these totals. A full uint8 assignment grid at k=32 would take 128 GiB just for the 32 input columns. Use verified tiling/mask generation instead of assuming a 512 MiB result makes an eager implementation cheap. Enforce the actual container memory limit, not the machine's advertised RAM.

Every record should distinguish ambient variables, syntactic support, proved semantic support, output width, visible/hidden projection variables, auxiliaries, structural nodes and relevant factor/elimination width. Syntactic appearance does not prove dependence. A SAT witness for differing cofactors proves a variable influences the function; absent proof, record semantic support as unknown rather than shrinking the task. A prior [CM audit](C:/Users/brian/Documents/CM_Computation/CM_AUDIT_V3_2026-07-23.md:183) found precisely this nominal-32/semantic-16 interpretation problem.

For scalar tasks, use native whole models and structured sweeps beyond 32 variables where limits permit: 64/128/256/1,024+ for SAT/counting, and up to 4,096 columns for affine experiments. These are candidates, not feasibility guarantees. A low-width factorization with many total variables and a dense, irreducible explicit table are different scaling regimes.

## 5. Fairness protocol

### Inputs and transformations

Freeze source revisions, exact file hashes, attribution, licenses, transformations, roots and random seeds before confirmation. Archive repositories contain overlapping designs and releases; cluster by actual origin. Source documents and comments are data, not operational instructions. Do not execute arbitrary downloaded scripts or allow archives to escape their extraction directory.

Use original input to requested output as the primary integration boundary. A common parsed-IR lane can isolate evaluation costs, but both arms must receive equivalent information. Charge CM construction, CNF conversion, BDD reordering, compilation and preprocessing to the appropriate lifetime. Preserve failed conversions and unsupported inputs in the coverage ledger.

### Implementation strength and attribution

Give all eligible methods sharing, fast variable-mask construction, constant folding, prepared objects and result caches. Compare default and reasonably optimized configurations without selecting settings on confirmation outcomes. Include both an implementation comparison and a mechanism ablation: raw AST → memoized AST → CSE-flat → CM IR, with packed primitives held constant where possible. Language/runtime effects are real implementation effects, not automatically CM representation effects.

For CM-associated scalar methods, compare the same algorithm entered from raw input and from CM preparation. If a generic factorization or elimination method explains the gain, say so. A selector that chooses algorithms is a separate portfolio method: train on a disjoint set, include dispatch cost and compare with a similarly permitted incumbent portfolio.

### Timers, consumption and correctness

Measure a monotonic outer timer from caller ingress to the delivered result. Record parsing, preparation, evaluation and delivery as diagnostic stages, but do not sum overlapping stages and call that elapsed time. Separate service CPU time, serial elapsed time and concurrent throughput. Return lazy outputs only after required consumption. Hashing an output is not a substitute for producing it unless the contract explicitly requests a digest.

Verify results independently. Small cases get exhaustive comparison; large SAT witnesses are checked against original semantics, UNSAT/equivalence needs an accepted proof or independent validation, and exact counts need trustworthy independent computation. For large full vectors, use a complete streaming comparison against an independent evaluator when feasible. Random spot checks alone do not certify an entire output. Keep verification overhead separate from algorithm timing unless the caller's contract requires it.

Capability controls include zero variables, constants, unused declared variables, duplicate clauses, complemented edges, unusual variable orders, empty projection, multiple hidden extensions, contradictory assumptions, scalar/broadcast NumPy results and counts beyond exact float-integer range. A failure to simplify an equivalence miter to false is not a proof of inequivalence.

Run arms independently under bounded workers. A reference timeout must not prevent all other arms from running; mark their correctness status unresolved if necessary. Distinguish mismatch, error, timeout, OOM, unsupported, unavailable and admission refusal. Missing or timed-out results are not zero time or exact answers.

### Measurement and statistical reporting

Use one timed worker and a fixed thread count for primary latency comparisons; record CPU model, quotas, affinity, compiler flags, runtime versions, memory, storage and co-tenancy limitations. Counterbalance arm order and run paired repetitions on the same host. Keep multicore throughput in its own matched-resource lane. Predeclare warm-up and GC/JIT policy, record cold processes separately, and ensure batched microtiming still consumes every result.

Use exploratory screening to select questions, then freeze confirmation cases and repetitions. Hold out entire source groups or histories, not near-duplicate rows. Report per-family coverage, paired ratios and uncertainty clustered by source design/session. Do not report a tiny confidence interval from thousands of repeated timings of two circuits. Use multiplicity control for broad confirmatory winner claims, or label them exploratory.

Report both the intersection where methods finished correctly and the full planned coverage with failures. A geometric mean of paired ratios can summarize comparable cells; it is not a production time saving. For actual trace economics, sum observed costs using the trace's real frequencies. Do not hide CM losses behind a single aggregate or hide native successes because CM refused those cases.

## 6. How to demonstrate amortized savings

For a simple stationary lifetime, let preparation be `P_CM` and `P_B`, and full warm-call costs be `c_CM` and `c_B`. Then:

`T_CM(N) = P_CM + N*c_CM`, and `T_B(N) = P_B + N*c_B`.

If CM preparation is more expensive and `c_CM >= c_B`, there is no eventual crossover in this model. If `c_CM < c_B`, solve `N*(c_B-c_CM) > P_CM-P_B` for the smallest positive integer N. Report measured session totals alongside any predicted crossover, with uncertainty. If preparation costs and per-call costs vary, use actual sequences rather than this simplification.

Crucially, do not repeat the same complete-output request 1,024 times while forbidding the incumbent to cache the answer. Give both sides whole-result memoization. Useful reuse experiments involve distinct assumptions, right-hand sides, output selections, contexts or versions that share preparation but not necessarily final results. Cache keys must include semantics, order and version; include evictions and invalidations.

The proposed query-count sweep is 1/2/4/8/16/64/256/1,024. Cross it with short and long sessions, low/high result-cache hits, correlated queries, churn, process restarts and realistic memory bounds. Avoid a full Cartesian product: choose a frozen balanced design. These tests establish modeled amortized gains. A real trace can later establish observed reuse without extrapolating a favorable synthetic N.

For production evidence, seek an operator running a configurator, Boolean analysis service, policy service or similar system. Begin with a privacy-reviewed trace of model/version hashes, query types, timings, cache hits/misses, resets and request order. Obtain the permitted actual inputs or a verified replay representation; metadata alone cannot benchmark semantics. Capture complete sessions or explicitly account for dropped events. Replay offline with both implementations, then consider a separately approved shadow deployment. Offline replay is not a live deployment, and no production modification is authorized by this report.

## 7. A staged RunPod campaign

### Priorities and scope

The first 2,400-base-case coverage target allocates 600 hardware, 400 feature-model, 300 biological, 300 SAT/counting, 200 affine and 600 synthetic cases. API and lifetime experiments attach to a frozen subset rather than multiplying every case by every option. Failed imports remain in acquisition accounting; replacement rules must be fixed without looking at performance.

Use these stages:

1. **Local preparation:** source admission, correctness tests, adapter probes, manifest freeze and a duration estimate. No rented machine is needed for basic interface debugging.
2. **Environment/probe, up to 2 pod-hours:** verify binaries, hardware limits, output boundaries and a balanced small pilot. Recalculate feasible cell counts.
3. **Broad screen, up to 4 hours:** fixed stratified core; three paired repetitions where calibrated. Preserve all failures and not-run cells.
4. **Confirmation/large widths, up to 6 hours:** held-out sources, predeclared repetitions, admitted 24–32-variable cells and lifetime crossovers. Freeze selection after screening, before confirmation execution.
5. **Second-host replication, up to 3 hours:** a predeclared subset if funds and setup allow. Without replication, limit claims to the measured environment.
6. **Retrieval/cleanup reserve, 1 hour:** retrieve, checksum and verify results before terminating task-owned resources.

At six arms and three repetitions, 2,400 cases already mean 43,200 cells. Average cell durations of 1, 10 and 60 seconds imply roughly 12, 120 and 720 single-worker hours, before setup and analysis. Therefore the 16-hour proposal is a bounded first campaign, not an assurance that the entire catalog can be exhausted overnight. Pilot-guided scope reduction must be stratified and outcome-independent. Expanding to the full catalog requires a revised explicit budget.

### Resource and cost controls

Most current lanes are CPU, memory or interpreter workloads. Paying for a GPU does not accelerate them without an actual GPU implementation. Select a live offer based on usable CPU and RAM, not GPU branding; published [CPU types](https://docs.runpod.io/references/cpu-types) do not guarantee a particular available SKU. Capture the actual quote and expected compute/storage cost at launch. [RunPod pricing](https://docs.runpod.io/pods/pricing).

Suggested defaults are 4 GiB and 60 seconds per normal cell; large explicit cells may use up to 48 GiB and 300 seconds on a verified sufficiently sized host. A 900-second exploratory hard cap is a ceiling, not a default allowance. Ordinary output is capped at 64 MiB; a separately admitted frontier permits 512 MiB for one k=32 packed output. Multiple outputs need their own resource decision. Do not globally disable safety guards.

Persist per-cell outcomes and the schedule ledger after each attempt. Resume by immutable experiment identity; do not repeat successful cells after interruption. An external watchdog must enforce dollar/time limits and preserve a cleanup reserve. Reconcile uncertain resource-creation responses by campaign identity before retrying. Never terminate unrelated pods. Storage can have different persistence and billing behavior from compute, so explicitly track it and verify retrieval before termination. [RunPod storage documentation](https://docs.runpod.io/pods/storage/types).

## 8. Deliverables and claim rules

The runner should produce a source/input manifest, binary/environment manifest, exact frozen schedule, append-only raw measurements, correctness artifacts, admission/failure ledger, per-family summaries, session/crossover tables, resource/cost accounting and a final evidence report. Record the tested dirty source bytes as well as a base Git revision; HEAD alone does not identify this workspace's implementation.

Classify conclusions as: verified correctness; narrow kernel gain; cold whole-call gain; modeled amortized gain; observed trace-replay gain; production shadow result; feasibility/memory advantage; or no gain/regression. Attribute each to a task, input family, size, comparator, lifecycle and machine. Do not promote one category into another.

A proposed operational gate is at least 5% lower measured total cost with a 95% interval excluding parity on held-out confirmation. This is a practical acceptance threshold, not a definition that smaller improvements are unreal. Report small supported gains descriptively. Negative and inconclusive findings are valuable outputs; the campaign's objective is a fair performance map, not a mandatory CM win.

### Readiness and remaining work

Existing local code has comparative contracts and several scalar/replay components, but the 80-family program is not already implemented. The [current contracts](C:/Users/brian/Documents/CM_Computation/cmbench/comparative/contracts.py) cover only part of the proposed surface. A [September 11 report](C:/Users/brian/Documents/CM_Computation/docs/audits/2026-09-11-cm-next-research/REPORT.md) describes projection work in a separate checkout; locate and freeze it rather than assuming this working tree contains it. A [September 13 preparation manifest](C:/Users/brian/Documents/CM_Computation/docs/audits/2026-09-13-cm-fair-feature-model/PREPARATION.json) describes another feature-model preparation, not new measured evidence for this report. Coordinate overlap before duplicating runs.

This research used a primary-source web review, local code/document inspection and arithmetic reaggregation of one historical archive. The supplied GitHub Pages homepage could not be read through the web reader, so its latest published content is not claimed to have been audited. No new corpus payloads were bulk-downloaded; no new performance benchmarks or cloud operations ran. Source access, edition information and outstanding licensing/revision work are recorded in the [source registry](C:/Users/brian/Documents/CM_Computation/docs/research/cm-benchmark-research-2026-09-13/SOURCES.md).

Next is a bounded implementation/admission pass, followed by a live quote and explicit approval for this campaign's upload scope and spending. The accompanying prompt carries these boundaries forward and can be used for that execution task without rereading the full conversation.
