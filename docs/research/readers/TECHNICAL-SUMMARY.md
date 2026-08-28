# Correspondence Matrices — technical summary

[Research library](../README.md) · Generated reading edition, 2026-08-28.

Derived from the authored explainer and its saved evidence. Charts and interactive controls remain in the downloaded HTML.

Latest follow-up: [verified Runpod memory smoke](RUNPOD-MEMORY-SMOKE.md). This does not establish general CM dominance or production estimator acceptance.

## Representation

A Correspondence Matrix represents a Boolean operator as an ordered binary matrix. The point is not that it computes a different answer — it computes exactly the same answer — but that it makes a different set of operations expressible.

### Truth table

#### Plain-language explanation

A truth table answers *what are the outputs?* You list every combination of inputs and write down what comes out. It is complete, and for a fixed variable ordering it pins the function down exactly.

A Correspondence Matrix answers a different question: *what operator produced those outputs, and what is its structure?* Same function, same answers — but now the operator is an object you can hold, compare, decompose, and store.

#### Technical detail

A complete truth function, a normalised CM, and a reduced ordered BDD can each identify a Boolean function under their respective conventions. Their organisation and their supported operations differ. Uniqueness of a CM is relative to an ordered variable basis; matrix equality requires the same normalised ordered basis on both sides.

This is the same distinction as between a list of a function's values and a closed-form expression for it. Both determine the function; only one supports algebraic manipulation.

#### Example

##### Caption

The AND operator, both ways

##### Rows

['0', '0', '0']

['0', '1', '0']

['1', '0', '0']

['1', '1', '1']

##### Matrix

['0', '0']

['0', '1']

### Live k

#### Plain-language explanation

Here is the single most important idea for reading any chart on this site. Suppose a system has 32 variables available, and you write the expression `x2 AND x17`.

Two variables matter. The other thirty do not appear and cannot change the answer. The meaningful output is four rows — every combination of two variables. The *ambient* truth table over all 32 variables has 4,294,967,296 rows, but 4,294,967,292 of them are copies of those same four answers.

So the honest measure of how big a job is is not how many variables exist. It is how many variables *actually change the answer*. This project calls that number `live_k`, and it is the horizontal axis of essentially every chart here.

#### Technical detail

Nominal *n* is the size of the variable namespace. Syntactically used variables are those appearing in the expression. Semantic support, `live_k`, counts variables with a genuine functional effect — a variable can appear syntactically and still be semantically dead, as in `x AND (y OR NOT y)`.

Explicit output size is 2<sup>live_k</sup>, not 2<sup>n</sup>. Plotting against nominal *n* without qualifying semantic support silently compares shallow sparse formulas against dense all-live ones and produces curves that mean nothing.

This is not a modelling assumption; it was measured. Holding `live_k` fixed and varying the ambient namespace across 16, 20, 24 moves the measured ratio by 0.040.

#### Table

['Nominal n', '32', 'variables available in the namespace']

['Syntactically used', '2', 'variables appearing in the expression']

['Semantic support (live_k)', '2', 'variables that can change the answer']

['Reduced output', '4 bits', '2 to the power of live_k']

['Ambient truth table', '4,294,967,296 entries', '2 to the power of n — almost entirely repetition']

### Operator calculus

Representing an operator as a matrix makes a family of operations expressible that a truth table does not naturally support. It is important to be exact about which of those are implemented, which exist in the formalism but have never been demonstrated on a workload, and which are neither.

#### Plain-language explanation

Once the operator is an object rather than a list of answers, you can ask things like: what is the difference between these two rules? Can this rule be factored into simpler ones? What does it reduce to if I fix one input?

The formalism supports those questions. That is a genuine and separate claim from “we have implemented them and shown they pay off,” and this project has been careful not to blur the two.

#### Columns

##### Item 1

###### Heading

Implemented and measured

Structural intermediate representation over a shared graph

Semantic-support analysis (computing live_k before evaluating)

Engine selection by support profile and required output

Prepared and cached execution keyed on expression identity

Reduced packed output without materialising a dense matrix

Failure-aware paired reporting and immutable corpus provenance

Explicit-output guard above live_k = 16

##### Item 2

###### Heading

In the formalism, not workload-validated

Matrix transformations on operators

Structural decomposition and quotienting

Logical measurement and reconstruction via ordered bra/ket vectors

Basis-normalised matrix comparison

Projection and conditioning

##### Item 3

###### Heading

Future work

Canonical CM equivalence checking

Automatic multi-backend routing with a cost model

Cross-expression structural reuse

Real-domain workload validation

#### Caveat

The current CM path establishes **output equality** — two expressions produce identical packed bits. That is a necessary condition for canonical structural equivalence, not a sufficient one. A canonical CM equivalence layer has not been implemented or demonstrated, and nothing on this site should be read as claiming it has.

### Pipeline

The compilation path from expression to answer, with each stage labelled by what is actually built today.

#### Stages

##### Expression input

###### N

01

###### Status

implemented

###### What

A Boolean expression arrives; the variable namespace and ordered basis are established.

##### Semantic support analysis

###### N

02

###### Status

implemented

###### What

live_k is computed — which variables genuinely affect the output. This governs workload size and every downstream decision.

##### Engine selection

###### N

03

###### Status

implemented manually; automatic routing is future work

###### What

Route to a packed CM kernel, a BitSet path, or a symbolic backend based on the support profile and the artifact requested.

##### Compiled, reusable representation

###### N

04

###### Status

scoped caching implemented; cross-expression reuse is future work

###### What

The structural IR is built and cached under a key derived from expression identity, so an identical expression reuses the compiled program.

##### Packed Boolean operations

###### N

05

###### Status

implemented

###### What

Reduced packed output is produced without ever materialising a dense CM matrix, unless the matrix itself is what was asked for.

##### Output

###### N

06

###### Status

implemented

###### What

A packed truth vector by default; the dense CM matrix artifact only on explicit request.

## Comparison contracts

Grouped by role: **execution kernels** produce an explicit output vector over the semantic support (BitSet, the CM packed path, compiled evaluators). **Symbolic engines** produce a graph or normal form that supports post-construction queries (ROBDD/CUDD, SAT, SymPy). **Minimisers** produce a smaller equivalent expression (Espresso).

A comparison is only meaningful within a role, and only when both sides produced the same artifact — which is why every timed comparison in this project is gated on bit-for-bit output equality first, and why construction and evaluation costs are never merged into one ranking.

## Current frontier

The B1/E3 CM-versus-CSE-flat residual remains below its pre-registered materiality bar and is not an optimisation target. V3's separate B2/B4 bare-program result is accepted as workload-specific, not universal. Preparation remains the leading raw optimisation surface; cache, family, context, selector, and native economics require a real workload and the strongest applicable incumbent.

Several items below are marked *partially answered*. That means a preliminary experiment exists and produced a result — often a negative or CM-versus-CM one — that does not meet the success criterion the project wrote for it. Those are reported as they stand rather than upgraded by optimism.

## Measurement discipline

Each of these exists because breaking it produced a wrong published number at some point in this project's history.

### Rules

#### Item 1

##### Rule

Nothing is timed until both sides agree, bit for bit

##### Lay explanation

Before the stopwatch starts, every method being compared has to produce exactly the same answer — every bit identical. If two methods disagree, that is a bug to fix, not a data point to quietly drop. Otherwise you can measure something fast that is simply computing the wrong thing.

##### Technical explanation

Packed-equality gating across every arm and the wrapper, on every formula, before any timing is recorded. For the decision-diagram comparison this was strengthened from sampled checks to *full extraction equality* on all 192 rows, so the timed comparison is provably of the same answer produced two ways. Compile-scaling cases likewise verified packed equality across all arms on every case.

##### What goes wrong without it

A faster implementation that is subtly wrong looks like a win. Worse, an arm that fails on hard inputs and succeeds on easy ones gets timed only on the easy ones, which is survivorship bias dressed as a speedup.

##### Sources

deliverables_n22_24/CM_GAP_EPFL_VALIDATION_2026-08-03.md §2

deliverables_n22_24/b5_cudd_2026_08_03_run5/

deliverables_n22_24/b3_scaling_2026_08_03/

#### Item 2

##### Rule

The pass mark for the decisive experiment was written down before the data existed

##### Lay explanation

The most important measurement in the project had its success threshold fixed in advance, in a document, before anyone had a single external number. Then the experiment ran — and failed to meet the threshold. The project reported that and changed its claim, rather than looking for another way to slice the data.

##### Technical explanation

The external protocol pre-registered the corpus source, cone-selection rules, arms, schedules, clustering basis and a three-condition materiality rule: the external CM ÷ CSE-flat geometric mean had to be at or below 0.95, *and* its circuit-clustered interval had to exclude parity, *and* the median break-even had to be at or below 1000. The measured result was 0.9998 [0.9747, 1.0249] — the first two conditions failed. That failure makes parity the final posture for the EPFL AND/INV workload. The later B2/B4 V3 result is reported separately and rules out silently generalising that posture to every workload.

##### What goes wrong without it

Without a threshold fixed in advance, any result can be narrated as a success. Pre-registration is what makes a negative result informative instead of merely disappointing.

##### Sources

deliverables_n22_24/CM_GAP_EPFL_PROTOCOL_2026-08-03.md

deliverables_n22_24/CM_GAP_EPFL_VALIDATION_2026-08-03.md §3

#### Item 3

##### Rule

Confidence intervals are clustered on the right unit

##### Lay explanation

If you time the same expression seven times, you have not measured seven expressions — you have measured one, seven times. Treating those as seven independent facts makes your error bars look far tighter than they are. Every interval on this site is built by resampling the thing that is actually independent.

##### Technical explanation

The inferential unit is the formula, the cell, the source circuit, or the machine — never the timing round. The synthetic corpus uses a stratified-by-cell bootstrap; the external corpus uses a circuit-clustered bootstrap, because 129 cones come from only 19 circuits and cones from one circuit share structure; machines are reported individually and never pooled. Circuit clustering makes the external interval wider than a cone-level interval would be, and that width is the honest one.

##### What goes wrong without it

Pseudo-replication. Repeated rounds inflate the effective sample size, intervals shrink toward zero width, and a difference that is well within run-to-run noise acquires the appearance of statistical significance.

##### Sources

deliverables_n22_24/CM_GAP_EPFL_PROTOCOL_2026-08-03.md

deliverables_n22_24/epfl_run_2026_08_03/

deliverables_n22_24/b6_pod_replication_2026_08_03/

#### Item 4

##### Rule

The two measurement orders are reported separately and never averaged

##### Lay explanation

You can time one method fully and then the other, or you can alternate between them. Those two orders leave the computer's fast temporary memory in different states, so they are genuinely two different measurements. Reporting only their average hides which one you did — so both are always shown.

##### Technical explanation

Blocked and round-robin schedules are reported as separate columns wherever both are measured, and are never pooled into a single figure. The campaigns that measure both are the corrected kernel experiment, its replay, the cross-machine replication and the external validation. The wrapper-boundary, guard, engine-crossover and order-sensitivity runs are blocked-only and say so on their reports.

##### What goes wrong without it

An earlier pass in this project attributed a schedule effect to a real performance difference. Once the two orders were separated the effect was visible as what it was. Pooling would have hidden it permanently.

##### Sources

deliverables_n22_24/b1_e3_replay_2026_08_03/

deliverables_n22_24/b6_pod_replication_2026_08_03/

deliverables_n22_24/b2_wrapper_2026_08_03/

#### Item 5

##### Rule

Every summary number is recomputed from the raw rows by someone other than the code that produced it

##### Lay explanation

The program that runs a benchmark also prints a summary. That summary is not trusted. A separate program re-reads the individual measurements and recomputes every headline figure from scratch, and the two have to match before anything is published.

##### Technical explanation

Independent reaggregation from the raw per-formula rows precedes citation of any statistic. The corrected kernel experiment was reaggregated by a third-party pass in which every summary row reproduced to within floating-point tolerance, break-even reproduced exactly on all formulas, and all stratified intervals agreed. This page does the same thing again: every figure here is recomputed by the build script from the raw evidence files, never copied from a report's prose.

##### What goes wrong without it

A bug in the summarising code becomes a published result. Two separate passes in this project's history found exactly that.

##### Sources

deliverables_n22_24/CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md

deliverables_n22_24/epfl_run_2026_08_03/

#### Item 6

##### Rule

Corpora are frozen and fingerprinted

##### Lay explanation

The set of test expressions is fixed and given a short fingerprint derived from its exact contents. Every machine that runs the benchmark re-checks that fingerprint first. If one character changed, the run stops. So when five machines report different timings, you know it is the machines that differ and not the questions they were asked.

##### Technical explanation

Corpora carry SHA-256 digests recorded in the campaign manifest and verified at each point of use. The cross-machine replication verified the corpus digest on every machine and additionally required the identity fields of every row to match exactly. The external corpus's upstream source is pinned to a specific commit with per-file digests and a licence digest recorded.

##### What goes wrong without it

Silent corpus drift. Two runs disagree and there is no way to tell whether the workload or the machine changed.

##### Sources

deliverables_n22_24/cm_benchmark_refresh_manifest_2026_08_03.json

deliverables_n22_24/cm_gap_epfl_provenance_2026_08_03.json

deliverables_n22_24/b6_pod_replication_2026_08_03/

#### Item 7

##### Rule

Every timing is labelled with what it actually includes

##### Lay explanation

“How long did it take?” is ambiguous. Did that include building the compiled program, or not? Did it include getting the answer back out? Every number here says which, because comparing a figure that includes setup against one that does not is the easiest way to publish a wrong ratio.

##### Technical explanation

Timings are typed: preparation, kernel, end-to-end call, extraction, and — for decision diagrams — build, sampled evaluation and full extraction, each reported separately. The build window convention is stated explicitly wherever two runs use different ones: the matched comparison's build includes creating a fresh manager and declaring variables, while the order-sensitivity run's build is expression-to-diagram conversion only. Those two are never plotted on the same axis.

##### What goes wrong without it

A superseded wrapper-overhead figure in this project's history was carried forward from a different corpus and timing protocol without re-measurement, and understated the real cost by a large factor.

##### Sources

deliverables_n22_24/b5_cudd_2026_08_03_run5/

deliverables_n22_24/bx2_cudd_orders_2026_08_03/

deliverables_n22_24/b2_wrapper_2026_08_03/

#### Item 8

##### Rule

Only matched pairs are aggregated, and every refusal is recorded

##### Lay explanation

If one method manages a hard case and the other gives up, that pair cannot be averaged into a speed comparison — you would be crediting one method for the cases where its competitor was absent. Only cases where both methods answered are counted, and every case where one declined is reported separately.

##### Technical explanation

Failure-aware paired reporting: unmatched observations are excluded from ratio aggregation, and skips, guard trips and runtime refusals are counted and published rather than dropped. The external campaign reported 129 of 129 rows successful with zero runtime-guard skips; the guard sweep reports the decline rate for every cell alongside the timings.

##### What goes wrong without it

Survivorship bias. The arm that fails more often on hard inputs is measured only on easy ones and appears faster than it is.

##### Sources

deliverables_n22_24/CM_GAP_EPFL_VALIDATION_2026-08-03.md §2

deliverables_n22_24/b4_sweep_2026_08_03/

#### Item 9

##### Rule

Building a thing and using a thing are never merged into one ranking

##### Lay explanation

Some tools spend effort up front to make later questions cheap; others do no setup and pay on every question. Adding those two costs into a single “speed” number produces a ranking that is meaningless for both. They are always shown as separate panels.

##### Technical explanation

Construction cost and evaluation or extraction cost are measured, reported and plotted as distinct quantities. There is no three-way winner anywhere on this site, and there is deliberately no blended ranking across tools that produce different primary artifacts.

##### What goes wrong without it

A canonical-form engine looks terrible at a job it was never designed for, or an evaluator looks free because its setup was charged to a different column.

##### Sources

deliverables_n22_24/b5_cudd_2026_08_03_run5/

deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md row 13

#### Item 10

##### Rule

The workload axis is live_k, not how many variables exist

##### Lay explanation

How big a job is depends on how many things actually matter, not on how many things are lying around. Charts plotted against the total number of variables silently mix easy sparse problems with hard dense ones and produce curves that mean nothing.

##### Technical explanation

Semantic support is measured, not assumed, and is the horizontal axis of every chart here with one stated exception: the guard chart, whose question — how often is a randomly drawn expression from a namespace of this size declined — is genuinely about the namespace. The axis choice was itself verified: holding semantic support fixed while varying the ambient namespace across 16, 20, 24 moves the ratio by 0.040, and on that chart nominal n appears as the series rather than the axis.

##### What goes wrong without it

Shallow sparse formulas and all-live formulas get compared as if they were the same size of problem, and any resulting scaling curve is an artifact of the mix.

##### Sources

deliverables_n22_24/b4_sweep_2026_08_03/

deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md row 6

#### Item 11

##### Rule

Withdrawn numbers are named, not deleted

##### Lay explanation

When a published figure turns out to be wrong, it is listed in a standing correction table alongside the reason it was wrong and what replaced it — rather than quietly disappearing. Anyone who read the old material can find out exactly what changed.

##### Technical explanation

A standing erratum and claim map name every superseded figure with its status — confirmed, revised, or superseded — and its replacement. On this site those figures appear in exactly one place, the corrections ledger, struck through, and are never plotted. Where the summary prose and the raw evidence still disagree, that disagreement is published too rather than resolved silently in favour of the nicer number.

##### What goes wrong without it

Superseded figures leak back into later material because nobody recorded that they were withdrawn. This has happened in the project's history and is what the ledger exists to prevent.

##### Sources

deliverables_n22_24/CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md

deliverables_n22_24/CM_GAP_FILE_INDEX_AND_SUPERSESSION_2026-08-02.md

deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md

#### Item 12

##### Rule

Reproduce a reported finding before fixing it — and be willing to refute it

##### Lay explanation

When an outside reviewer reports a problem, the first step is to reproduce it independently, not to fix it. Several reported problems turned out to be real; at least one turned out to be wrong, and was recorded as refuted rather than fixed to be agreeable.

##### Technical explanation

Externally reported findings are independently reproduced before any change is made, and are refuted where the evidence does not support them. In the consolidated corrective pass, six of seven external findings were confirmed and addressed and one was refuted on the evidence. A separate formal argument about decision-diagram size was refuted as stated while its practical conclusion was upheld — the exact bound in the argument was wrong, and node counts do not imply byte size or runtime, but the practical conclusion it supported survived.

##### What goes wrong without it

Agreeableness masquerading as rigour. Fixing a non-problem adds risk and hides the fact that the reviewer's model was wrong.

##### Sources

deliverables_n22_24/CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md

deliverables_n22_24/CM_GAP_DEEP_FOLLOWUP_2026-08-02.md

## Current evidence update

What the 2026-08-26/27 evidence added

These results close stale ‘never studied’ language without promoting synthetic diagnostics into production claims. They leave the accepted kernel, wrapper, guard, artifact, and corpus boundaries intact.

### Lay lede

Several missing checks have now been run. They tell us more about where CM does and does not help, but they still do not substitute for traffic from a real application.

### Cache, family, and context reuse: measured synthetically

#### Summary

The flag called persistent cache was measured as a process-local, synthetic all-hit cache. Cached whole-call CM still took 3.13×–12.84× BitSet time. With 50 cached evaluations, execution-only CM still took 2.80× at k=16, 3.87× at k=12, 8.91× at k=8, and 11.18× at k=4.

#### Detail

Related-family high-reuse cells remained 5.25×–26.45× slower than BitSet. Across the synthetic partial-context grid, cached CM was 4.85×–7.37× faster than uncached CM. The n=16, 500-context cells were hypothesis-generating near-parity points: 1.108, 0.952, and 0.997 CM/BitSet at fixed fractions 0.25/0.50/0.75. They used only 3 trials and no native CUDD restriction comparator. No byte-LRU, durable cache, production working set, hit distribution, RSS plateau, or production cache policy is validated.

#### Audiences

master

expert

investor

layperson

### Metrics tracing: bounded diagnostic only

#### Summary

Full-rate V1 and V2 capture were rejected at median whole-call ratios 1.3037 and 1.1173. Deterministic one-in-16 V3 sampling was retained opt-in at 1.0052, with 0 exact mismatches, 0 drops, and 0 I/O errors.

#### Detail

The per-emitted-event gate failed. Sampling loses exact access order, and the anonymous metrics schema contains neither replayable expressions nor raw contexts. Synthetic single, family, and context traces passed mechanics, schema, privacy, exactness, and logical replay-summary checks; no real workload was found.

#### Audiences

master

expert

investor

### Workload intake: valid template, deliberately not ready

#### Summary

The strict owner-declared manifest validates structurally but reports not ready, with 13 explicit blockers. It is a template, not a captured workload.

#### Detail

Real cache, edit/version, partial-context, selector, and native economics remain blocked on a named application and caller, artifact and output-order contract, budgets, lifecycle, capture duration, and separate metrics, expression, context, and upload approvals.

#### Audiences

master

expert

investor

layperson

### Native dependency feasibility: resolution stopped before algorithms

#### Summary

Three authorized disposable CPU attempts cost $0.0019 cumulatively and ended with 0 pods. The final attempt built the pinned pure-Python astutils wheel, then failed closed because dd 0.6.0 requires source-only PLY 3.10 and that source build was not authorized.

#### Detail

Numba, dd.cudd, CUDD restriction, and native performance were never reached. They are untested, not failed. No dependency was integrated and no native or SIMD performance claim exists.

#### Audiences

master

expert

investor

### Temporary memory: refusal works; the estimator is not conservative

#### Summary

Direct output, benchmark, and remote surfaces have different output guards and no default temporary limit. In 4 bounded dense cases, the current estimate sat below median tracemalloc peak by 3.51×–38.73×; typed refusal still occurred before materialisation in 4/4 cases.

#### Detail

tracemalloc is not an RSS or native-memory upper bound, so these cases do not calibrate a universal multiplier. No default changed. Proposed 16 MiB benchmark/remote and 64 MiB direct profiles remain a future approval decision after estimator and compatibility work; they are not current settings.

#### Audiences

master

expert

investor

layperson

### Audit reliability and current validation

#### Summary

DP-R3 consolidated 3 duplicate exact-file SHA-256 helpers into 1 streaming helper with compatibility and source-snapshot coverage. Its tiny exact smoke passed integration but failed timing gates at 1.0402; this is maintainability work, not a performance improvement.

#### Detail

The newest repository validation is 84 focused tests and 391 tests plus 4 subtests in the full suite. Test counts describe validation state, never benchmark evidence.

#### Audiences

master

expert

investor

## Named-number provenance

Values below retain the source field and any qualification used by the website.

- `b4.ambient_ns` = 16, 20, 24. Source: `deliverables_n22_24/b4_sweep_2026_08_03/CM_b4_headline_summary_2026_08_03.csv :: distinct ambient_n`.
- `b4.k16.spread` = 0.040. Source: `deliverables_n22_24/b4_sweep_2026_08_03/CM_b4_headline_summary_2026_08_03.csv :: max-min of paired_ratio_geomean at live_k=16 across ambient n`.
- `cache.evals` = 50. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/cache_reuse50_summary.csv :: cm_eval_repeat_median`.
- `cache.exec.k12` = 3.87×. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/cache_reuse50_summary.csv :: n_vars=12 ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached`.
- `cache.exec.k16` = 2.80×. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/cache_reuse50_summary.csv :: n_vars=16 ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached`.
- `cache.exec.k4` = 11.18×. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/cache_reuse50_summary.csv :: n_vars=4 ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached`.
- `cache.exec.k8` = 8.91×. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/cache_reuse50_summary.csv :: n_vars=8 ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached`.
- `cache.whole.max` = 12.84×. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/cache_process_local_summary.csv :: max(cm_persistent_cache_no_reinflate_time_s_median / bitset_time_s_median)`.
- `cache.whole.min` = 3.13×. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/cache_process_local_summary.csv :: min(cm_persistent_cache_no_reinflate_time_s_median / bitset_time_s_median)`.
- `context.f25.ratio` = 1.108. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/partial_f0p25_c500_summary.csv :: n_vars=16,c=500 cm_cache_total / bitset_full_recompute_total`.
- `context.f5.ratio` = 0.952. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/partial_f0p5_c500_summary.csv :: n_vars=16,c=500 cm_cache_total / bitset_full_recompute_total`.
- `context.f75.ratio` = 0.997. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/partial_f0p75_c500_summary.csv :: n_vars=16,c=500 cm_cache_total / bitset_full_recompute_total`.
- `context.speedup.max` = 7.37×. Source: `partial context summary CSVs :: max(speedup_cm_cache_vs_cm_no_cache_median)`.
- `context.speedup.min` = 4.85×. Source: `partial context summary CSVs :: min(speedup_cm_cache_vs_cm_no_cache_median)`.
- `context.trials` = 3. Source: `selected n=16,c=500 partial context rows :: trials`.
- `cudd.rows` = 192. Source: `deliverables_n22_24/b5_cudd_2026_08_03_run5/cm_b5_cudd_matched_results_2026_08_03.json :: len(rows)`.
- `dependency.cost` = $0.0019. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/runpod_dependency_feasibility_run3/dependency_runpod_audit_run3_2026_08_26.json :: total_cost_usd`.
- `dependency.postflight_pods` = 0. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/runpod_run3_postflight_inventory.json :: pod_count`.
- `dpr3.helpers.after` = 1. Source: `deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-08-27/ACCEPTED-LATE-EVIDENCE.json :: provenance_consolidation.streaming_helpers_after`.
- `dpr3.helpers.before` = 3. Source: `deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-08-27/ACCEPTED-LATE-EVIDENCE.json :: provenance_consolidation.duplicate_helpers_before`.
- `dpr3.smoke.ratio` = 1.0402. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/dpr3_trace_overhead_smoke_summary.json :: ratio_median`.
- `epfl.n_circuits` = 19. Source: `deliverables_n22_24/epfl_run_2026_08_03/cm_gap_epfl_analysis_2026_08_03.json :: n_circuits`.
- `epfl.n_cones` = 129. Source: `deliverables_n22_24/epfl_run_2026_08_03/cm_gap_epfl_analysis_2026_08_03.json :: n_ok`.
- `family.bitset.max` = 26.45×. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/family_high_reuse_summary.csv :: max(ratio_cm_cache_over_bitset_median)`.
- `family.bitset.min` = 5.25×. Source: `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/family_high_reuse_summary.csv :: min(ratio_cm_cache_over_bitset_median)`.
- `flat.epfl` = 0.9998. Source: `deliverables_n22_24/epfl_run_2026_08_03/cm_gap_epfl_analysis_2026_08_03.json :: primary_blocked_cm_cse_flat.geomean`.
- `flat.epfl.hi` = 1.0249. Source: `deliverables_n22_24/epfl_run_2026_08_03/cm_gap_epfl_analysis_2026_08_03.json :: primary_blocked_cm_cse_flat.ci95_hi`.
- `flat.epfl.lo` = 0.9747. Source: `deliverables_n22_24/epfl_run_2026_08_03/cm_gap_epfl_analysis_2026_08_03.json :: primary_blocked_cm_cse_flat.ci95_lo`.
- `guard.k` = 16. Source: `deliverables_n22_24/cm_b4_guard_family_sweep_2026_08_03.py :: max_full_output_vars (the explicit-output guard; the same driver's wrong-guard predicate is `live_k <= 16`)`.
- `memory.cases` = 4. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/DP-R2-OUTPUT-BUDGET-PROBE.json :: len(cases)`.
- `memory.multiple.max` = 38.73×. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/DP-R2-OUTPUT-BUDGET-PROBE.json :: max(cases[].peak_over_estimated_temporary_median)`.
- `memory.multiple.min` = 3.51×. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/DP-R2-OUTPUT-BUDGET-PROBE.json :: min(cases[].peak_over_estimated_temporary_median)`.
- `memory.proposed.benchmark_mib` = 16. Source: `deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-08-27/ACCEPTED-LATE-EVIDENCE.json :: temporary_memory_policy.proposed_benchmark_remote_mib`.
- `memory.proposed.direct_mib` = 64. Source: `deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-08-27/ACCEPTED-LATE-EVIDENCE.json :: temporary_memory_policy.proposed_direct_mib`.
- `memory.refusals` = 4. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/DP-R2-OUTPUT-BUDGET-PROBE.json :: count(cases[].refusal_before_materialization)`.
- `tests.focused` = 84. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/focused_pytest.xml :: count(testcase)`.
- `tests.full` = 391. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/full_pytest.xml :: count(testcase)`.
- `tests.full.subtests` = 4. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/full_pytest.xml :: testsuite.tests - count(testcase)`.
- `trace.drops` = 0. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/trace_overhead_v3_sample16_summary.json :: trace_dropped_events`.
- `trace.io_errors` = 0. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/trace_overhead_v3_sample16_summary.json :: trace_io_errors`.
- `trace.mismatches` = 0. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/trace_overhead_v3_sample16_summary.json :: exact_mismatches`.
- `trace.sample_every` = 16. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/trace_overhead_v3_sample16_summary.json :: sample_every`.
- `trace.v1.ratio` = 1.3037. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/trace_overhead_summary.json :: ratio_median`.
- `trace.v2.ratio` = 1.1173. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/trace_overhead_v2_summary.json :: ratio_median`.
- `trace.v3.ratio` = 1.0052. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/trace_overhead_v3_sample16_summary.json :: ratio_median`.
- `workload.blockers` = 13. Source: `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/WORKLOAD-MANIFEST-TEMPLATE-VALIDATION.json :: len(blockers)`.
