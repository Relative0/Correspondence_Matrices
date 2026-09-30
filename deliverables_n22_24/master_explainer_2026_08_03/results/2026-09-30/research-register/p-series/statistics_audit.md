# Independent timing, statistics, and benchmark-selection audit

The supplied P11–P13 arithmetic is reproducible, but the reported source-inclusive timer includes substantial correctness/reporting work outside the stated compiler endpoint. This makes the apparent approach to parity misleading. Reconstructing source build + dispatch + compiler from the existing raw components still does not establish a case-balanced win: P13/direct becomes **1.052094**, rather than **1.016459**. A corrected prospective rerun is required before treating either number as an unbiased measurement of the specified production pipeline.

Paths below are relative to `primary/ASTRA_P1_P13_AUDIT_PACKAGE/` unless an audit-output filename is given. No original artifact was edited. This subaudit ran data analysis and structural selection reconstruction, not benchmark timing loops.

## Evidence read and independently checked

| Artifact family | Inspection/check |
|---|---|
| P11/P12/P13 preregistrations | Read timing, primary endpoints, invariance/correctness gates, thresholds and guardrails. |
| P11/P12/P13 harnesses and delegated compiler chain | Traced endpoint boundaries, trial schedules, bootstrap, summary comparisons and source generation. |
| P11/P12/P13 `gatep.json` | Parsed all 2,880 timing rows per phase, symbolic and memory payloads. |
| All ten `natural/*.json` files in each of P11/P12/P13 | Parsed all 600 timing rows per phase; no missing cases. |
| P11/P12/P13 `N2_P*_SUMMARY.json` | Independently recomputed 90 comparisons, including all 95% intervals; maximum numerical discrepancy 2.23e-16. |
| P11/P12/P13 per-case CSVs, results and interpretation material | Used to cross-check claims; independent CSV output comes from raw rows rather than trusting supplied medians. |
| P11/P12/P13 fuzz, invariance and independent-verifier JSON | Read pass counts/branch coverage; these stored records are evidence of prior runs, not fresh execution. |
| P11/P12/P13 free-telemetry JSON and build profiles | Inspected counterfactual construction and profile scope. |
| P08 calibration/harness/preregistration and P8 frozen selections | Inspected train/validation/evaluation separation, objective, source builders and model selection. |
| P07B correction note, fixed harness, saved buggy harness and results | Confirmed explicit correction from outer wrapper to probe + backend pipeline time. |
| Six pinned BLIF files, source manifest, P1/P8 selections | Independently parsed every file, verified SHA-256 and Git blob hashes, reconstructed all P1/P8 choices exactly. |

Reproduce with `.venv/Scripts/python.exe audit_p1_p13_20260918/statistics_recompute.py` from the workspace. Outputs are `statistics_recomputed.json`, `statistics_case_medians.csv`, and `statistics_case_contributions.csv`. The script uses only the standard library, imports no experiment harness, and performs no timing reruns. It reads **10,440 timing rows** across these three phases. All 138 per-case schedules match their exact frozen shuffled order, have contiguous unique schedule positions, the stipulated 20 Gate-P / 15 natural repeats per arm, and stored `ok=true`.

## Timing boundary defect and its consequence

P13's outer timer begins before source construction and ends after `compile_once` returns (`P13/n2_p13_harness.py:311–346`). Delegation reaches `P06/n2_p6_harness.py:439–460`. There the inner `pipeline_ns` timer stops at line 453, **before** `anf_to_bitset`, correctness comparison, polynomial digest, final-degree computation, statistics conversion, function return, and compiler object cleanup. All of that work lies inside P13's outer timer. P11 lines 258–285 and P12 lines 269–303 have the same issue; it originates in P08 lines 396–421. The preregistered P13 endpoint, line 143, ends with sparse-ANF lowering. P11 line 119 and P12 line 146 say the same.

This is not an unfair endpoint applied only to CM in P11–P13: all simultaneous source arms include the extra wrapper work. Nevertheless it is a materially different workload from the stated endpoint, and an additive mostly-common cost dilutes both speedups and slowdowns. The mismatch also means the P08 training/validation objective (source medians + **inner** compiler medians, lines 318–339 and 369–382) differs from the later measured outer source-inclusive endpoint.

The package already identified exactly this type of error in `P07B/P7B_TIMING_CORRECTION.md:3–7`. Its fix is visible in `P07B/n2_p7b_harness.py:101–118`: `pipeline_ns=probe_ns+r['pipeline_ns']`, with a separate `dispatch_wall_ns`. In P7B the original defect had also unfairly affected only the dispatch arm; in P8 onward it is symmetric but still contradicts endpoint interpretation.

For diagnosis, define **reconstructed** time per raw row as `source_build_ns + compiler_ns`; dispatch is already inside `source_build_ns`. Then form medians within case/arm. This avoids the incorrect identity `median(build)+median(compiler)=median(build+compiler)`. It excludes all residual wrapper time rather than pretending every excluded nanosecond is oracle cost; some call/destruction overhead is legitimate production cost. A future timer should bracket the actual complete production operation, with verification after its end, and specify whether freeing returned/intermediate objects is charged.

| Gate-P phase | Supplied outer geomean [95% CI] | Reconstructed geomean [95% case-bootstrap CI] | Outer summed-median ratio | Reconstructed summed-median ratio |
|---|---|---|---:|---:|
| P11 | 1.043490 [0.974046, 1.093383] | 1.102008 [1.002711, 1.175773] | 1.004381 | 1.000389 |
| P12 | 1.019888 [0.950964, 1.066939] | 1.072517 [0.981217, 1.143754] | 0.982339 | 0.974558 |
| P13 | 1.016459 [0.950719, 1.063606] | 1.052094 [0.962738, 1.121505] | 0.980269 | 0.958750 |

The residual's sum of case medians is **42.92%, 42.08%, 41.91%** of the corresponding direct outer sums in P11/P12/P13. In P13 it is roughly 101–121 microseconds per direct Gate-P case. These quantities explain why correcting the endpoint moves the case-balanced estimate away from parity while strengthening the weighted gain from the two largest real fold wins. Both endpoint definitions continue to fail the required geomean <=0.95 and upper CI <1 criteria.

| Phase/depth | Depth 6 outer / reconstructed | Depth 8 outer / reconstructed | Depth 10 outer / reconstructed |
|---|---:|---:|---:|
| P11 | 1.066840 / 1.150244 | 0.999977 / 1.049692 | 1.065063 / 1.108415 |
| P12 | 1.045928 / 1.105851 | 0.983426 / 1.029168 | 1.031368 / 1.084001 |
| P13 | 1.032307 / 1.070316 | 0.979704 / 1.018475 | 1.038404 / 1.068318 |

In particular the P13 depth-8 point-estimate crossover disappears under the reconstructed compiler endpoint.

## Aggregation, concentration and statistical scope

The bootstrap itself is implemented correctly for its declared statistic: `P11/n2_p11_harness.py:47–69`, P13 comparison at lines 463–471. Cases are paired before division; 5,000 resamples draw those paired case ratios, not unrelated numerator and denominator cases. Summaries compute geometric means of case-median ratios, not pooled repetition medians. There is no arithmetic or denominator-switching error in the 90 checked summaries.

The phrase “paired randomized repetitions” should not imply matched temporal blocks. The actual schedule shuffles the entire arm list (P13 lines 409–425), and `rep` is an ordinal execution position. Pairing is by case for the final statistic. Case-bootstrap intervals quantify sensitivity to the observed case mixture and condition on estimated medians. They do not propagate uncertainty within repetitions, account for depth-stratified sampling, establish independence of structurally related circuits, or constitute independent confirmation after many design iterations. A nested, blocked analysis in a fresh run would address these issues; statistical reinterpretation of this old corpus cannot restore an untouched holdout.

| Phase | Outer median case ratio | Wins | Direct sum / candidate sum, milliseconds |
|---|---:|---:|---:|
| P11 | 1.087077 | 2/36 | 9.194216 / 9.234492 |
| P12 | 1.047238 | 3/36 | 9.498159 / 9.330412 |
| P13 | 1.051102 | 3/36 | 9.393968 / 9.208616 |

In P13, `8:11` saves **501.765 microseconds**, while `10:2` saves **172.755 microseconds**; together their savings exceed the net corpus saving of **185.352 microseconds**, because most cases lose. `8:11` alone contributes 271% of the net saving and represents 9.12% of direct outer workload. Omitting only `8:11` changes the outer summed ratio to **1.037061** and the reconstructed summed ratio to **1.062288**. Omitting it changes P11/P12 outer summed ratios to **1.063806 / 1.040272**. This supports a concentrated useful-mechanism result, not robust typical-case acceleration.

The other P13 outer “win,” `6:1`, is a **bypass** case. Its compiler medians are effectively identical (42.464 vs 42.454 microseconds) while the telemetry build median is larger (51.147 vs 39.099 microseconds). Its total-row median happens to favor P13; medians of parts are nonadditive, and this isolated win is not evidence of folding. Raw per-repetition data, not just the total win count, is essential here.

P11 genuinely improves over simultaneous P10 on the supplied endpoint: 0.969953 [0.963118, 0.977106], and the stored specialized-engineering gate passes. P12/P11 is 0.978766 [0.969244, 0.988333] but its stricter combined engineering criterion fails. P13/P12 is 0.996897 [0.990522, 1.003201], failing its engineering criterion. These are within-run comparisons; chaining ratios from different machine runs is not a valid controlled estimate of total P8-to-P13 progress.

## Natural controls and source selection

| Phase | Outer natural geomean | Outer weighted | Reconstructed geomean [95% CI] | Reconstructed weighted |
|---|---:|---:|---|---:|
| P11 | 1.005777 | 0.996435 | 1.017987 [0.999660, 1.043982] | 0.996604 |
| P12 | 1.015126 | 0.994350 | 1.030012 [0.997849, 1.071741] | 0.993311 |
| P13 | 1.000918 | 1.011995 | 1.013031 [0.998588, 1.032541] | 1.013516 |

All ten natural cases bypass and consume zero folds in all three phases. Consequently no natural folding-acceleration claim follows. `cavlc:35` contributes approximately 72.5–72.9% of direct natural summed time; in P13 its 10.166 millisecond loss accounts for 103% of the net natural loss. The residual wrapper fraction is only about 2.4% of the natural summed endpoint, but for some small cases is most of the time: P13 `priority:new_n130` 81.7%, `router:92` 68.3%. Calling natural behavior simply “negligible overhead” hides this heterogeneous regime and the absence of any positive folding examples.

All supplied source hashes and selections are consistent. Independent properties are:

| Source | Inputs / outputs | `.names` nodes | Cubes | P1 admitted roots | P1 selected roots |
|---|---:|---:|---:|---:|---|
| adder_size_2022 | 256 / 129 | 132 | 2059 | 2 | f[4], f[5] |
| bar_size_2015 | 135 / 128 | 512 | 1792 | 0 | none |
| cavlc_size_2024 | 10 / 11 | 49 | 1328 | 23 | 17, 35 |
| int2float_size_2025 | 11 / 7 | 24 | 233 | 19 | e4, y6 |
| priority_size_2024 | 128 / 8 | 102 | 578 | 4 | new_n130, new_n174 |
| router_size_2024 | 60 / 30 | 45 | 384 | 2 | 105, 92 |

Every source has maximum `.names` fan-in six. These are already size-optimized mapped BLIF networks, and the evaluator expands cubes into AND/OR/NOT source DAGs. “Source nodes” in the frozen selection mean `.names` cone nodes, not the number of constructed binary Boolean nodes or ANF terms. The admitted set restricts support to 9–12 and cone nodes <=128, then chooses structural extremes; it is not a random sample of natural applications, whole circuits, or unmapped optimization opportunities (`P01/n2_p1_harness.py:220–298`).

The P8 selection reconstruction exactly matches eight training and eight validation roots. The sets are root-disjoint from the ten evaluation roots, as intended (`P08/n2_p8_harness.py:228–260`). They are neither circuit-disjoint nor cone-disjoint: training/validation selected cone unions share **2 adder, 11 cavlc, 6 int2float, 3 priority, 2 router** internal `.names` nodes with evaluation-cone unions. Thus root exclusion is an auditable literal safeguard against identical-root labels, not evidence of independent natural generalization. The P8 preregistration itself acknowledges this limitation.

## Memory boundary and measurement limits

P13 starts `tracemalloc` before source construction and stops it only after `compile_once` has performed correctness conversion/reporting (harness lines 312–336). P11/P12 do the same. Thus the source-inclusive allocation peak includes verifier/transient reporting allocations, whereas the compiler-only peak in P6 stops before `anf_to_bitset` (P6 lines 453–460). Unlike time, a production-only allocation peak cannot be recovered by subtracting reported peaks. A clean memory rerun must retain the intended outputs and stop tracing before verification while documenting the object-lifetime boundary. `tracemalloc` is Python-tracked peak allocation, not process RSS, all native memory, or asymptotic space.

The stored whole-pipeline Gate-P memory geomeans relative to direct are P11 **0.993015**, P12 **1.011858**, P13 **0.993050**. Their **median** case ratios are **1.060421**, **1.074123**, **1.062963**: the typical case has a modest peak increase despite near-unity/below-unity geomeans. Natural memory geomeans are **1.019191**, **1.021513**, **1.012959**. P13/P12 Gate-P peak ratio **0.978928** is an engineering observation for this traced wrapper, not a demonstrated reduction in total production memory. A single untimed memory pass per case/arm also supplies no run-to-run uncertainty estimate.

## Profile and counterfactual cautions

P11–P13 build profile scripts recreate all recipe closures inside each profiling round. `P08/n2_p8_harness.py:193–203` advances the frozen RNG by **building ordinary Gate-P cases** before returning build closures. These extra constructions are included in the cProfile totals but outside the actual timed `source_arm_once` build. For example P13's direct profile spends 0.063 of 0.127 seconds in `gatep_eval_recipes` and records 26,900 ordinary `_make` calls, while P13's candidate profile records 13,450 candidate plus 13,450 ordinary calls. These profiles can locate functions but their total-time proportions do not partition the benchmark timer. Materialize recipes once outside the profiled region in a future diagnostic.

The “free telemetry” estimates, 0.962603 / 0.963002 / 0.958020 for P11/P12/P13, are counterfactuals based on ordinary-build medians plus candidate **inner** compiler medians (`P13/make_p13_artifacts.py:52–58`). They also omit the outer residual and sum medians rather than medians of row sums. They should not be presented as directly comparable to the outer endpoint, measured implementation wins, or proof that compiled telemetry will cross the <=0.95 threshold. Even the supplied P13 zero-cost-telemetry point estimate remains above that threshold.

P11 random fuzz selected zero annotations; P12 selected zero annotations and ran no lazy reuse scans; P13 selected one annotation, 22 multiplicity exactifications, and two reuse scans. These outcomes limit positive-path coverage from the random fuzz despite the 1,000-case totals. The 332-case invariance set and targeted boundary/branch tests matter more for the newly specialized branches. The supplied “independent verifier” reads records and recomputes selected summaries; it is not an independently implemented semantic compiler or a fresh timing run.

## Recommended next evidence

First repair and prospectively freeze the measurement boundary; benchmark a small diagnostic subset with outputs verified outside timing, preserve the existing outer value as a separately labeled metric, and ensure profile recipes are constructed outside profiling. Do not retune the policy while diagnosing the timer. Then run one frozen implementation comparison with balanced randomized arm blocks, multiple fresh processes and raw timestamps/system metadata. Record source construction, telemetry, dispatch, cloning/lowering, release policy, and production total separately.

For a policy or generalization claim, create a genuinely new test corpus after freezing every policy/implementation choice: hold out entire natural circuits or design families, include untouched synthetic seeds plus differently constructed families, structurally deduplicate related cones, and declare sampling and size/support limits before timings. Train on full production cost including telemetry, select once on disjoint validation, and open the final holdout once. Evaluate all methods with the same source representation and downstream compiler. Use positive natural fold incidence as a separate prerequisite for a natural folding claim; abstention controls cannot supply it. Predeclare a case-balanced primary endpoint, depth/circuit strata, practical weights, minimum effect, and one decision rule; retain arithmetic/weighted results as explicitly separate estimands.

No additional timing work was performed by this subaudit. The current data substantiate implementation improvements and a small number of substantial synthetic wins; they do not substantiate broad practical or typical-case end-to-end speedup.
