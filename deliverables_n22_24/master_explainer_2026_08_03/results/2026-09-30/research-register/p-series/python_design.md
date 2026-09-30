# Python hot-path and exact-dispatch audit

This is an audit contribution, including **post-hoc exploratory diagnostics**, not a new preregistered P14 result. All supplied evidence was left unchanged. Paths below are relative to `primary/ASTRA_P1_P13_AUDIT_PACKAGE` unless explicitly identified as new diagnostics. Line numbers refer to the supplied source.

## Findings that change the next experiment

1. There is still a useful pure-Python implementation experiment to run. An exact decision prototype improves on P13 in the local exploratory measurements, but it does not beat a stronger direct baseline. Moving immediately to C is premature if the intended conclusion is algorithmic end-to-end superiority.
2. The frozen policy is representation-dependent in a particularly sharp way: its five-shell predicate depends on retaining swapped operands as different nodes. Simple canonical commutative CSE makes the five-shell predicate impossible in the current primitive-only source recipes, while the actual folding mechanism still saves substantial ANF work.
3. The source-inclusive endpoint includes Boolean output verification and digest/report conversion after the inner compiler timer stops. It also rebuilds an already-built ordinary DAG for the direct arm. Both require correction or explicit alternative endpoint reporting before native-backend comparisons.
4. The post-hoc build profiles include the cost of regenerating an ordinary reference DAG for the recipe stream. P11/P12 profile only construction, while P13 profiles construction plus dispatch. These profile totals do not establish an isolated telemetry cost.

## What P08–P13 actually maintain

The ordinary node is already a `__slots__` class, not an unslotted dataclass (`03_N1_BASELINE/n1_gatep_harness.py:32`). The source factory interns `(op, ordered_child_ids, value)` and returns the existing node on a hit (`:43–51`). P-series telemetry is updated only when a **new interned node** is created. A cache hit is not a new pair occurrence. This distinction is essential to any proposed interning-based trigger.

| Stage | Per-created-node work | Dispatch |
|---|---|---|
| P08, `n2_p8_harness.py:67–122` | Depth, child use counts, reuse events, nonlinear count, pair multiplicities, pair token masks, several maxima | Full tree and floating features |
| P09, `n2_p9_harness.py:67–138` | Calls ordinary `_make`, checks node-list growth, tracks only tree-used primitives, byte depths/use flags, packed pair counts | Full reduced-feature tree |
| P10, `n2_p10_harness.py:63–160` | Fuses P09 into one `_make`; still depth/use/pair work | Same tree |
| P11, `n2_p11_harness.py:78–165` | Drops depth; saturates shell knowledge, tracks reuse and pair repeats | Only conjunction leading to leaf 10 |
| P12, `n2_p12_harness.py:62–165` | Pair dictionary counts saturated at 5, edge/binary counts; repeat derived as B-D | Shell, repeat threshold, then lazy reuse scan |
| P13, `n2_p13_harness.py:60–193` | Edge/binary counts and packed pair-key list; no construction-time pair dictionary | Set for distinct pairs; possibly count dictionary; possibly reuse scan |

P13 avoids one Python dictionary update loop but still performs, per binary node, a binary attribute increment, operand comparison, optional swap, integer shift/OR allocation, and list append (`:93–99`). It also still creates an operand-ID tuple for structural interning. A `set` and then `_count_elements` both hash the same stored keys when exact multiplicities are needed (`:146`, `:162–163`). The right comparison is the entire source/dispatch path, not a claim that counting is now free because its loop is in C.

The frozen condition is exactly, for this frozen gate:

- S >= 5, where S is the largest number of distinct created binary nodes sharing an unordered child-ID pair;
- Q/E <= 0.44374121725559235, where Q counts repeated child uses and E counts all created-node edges;
- R/B <= 0.16333333402872086, where B is the number of binary nodes and R=B-D for D distinct unordered pairs.

Only leaf 10 is below the 0.80 cutoff. P11 checks this leaf fact (`n2_p11_harness.py:168–184`), and the supplied tree was inspected. Predicate reordering preserves the selected backend, though bypass reasons and predicted leaf ratios can change. P12 explicitly permits this distinction in its preregistration. A new optimized dispatcher should preserve backend decisions and returned ANF, not require identical diagnostic scan traces.

The feature population is all factory-created nodes, including nodes no longer reachable from the selected final root. The backend clone/annotation sees only the reachable root DAG. Consequently, equivalent final roots with different dead construction histories can receive different policy decisions. This is a second representation/history dependence, separate from operand order. A production parser with dead-node elimination must validate its policy on the resulting feature population rather than assume the supplied thresholds transfer.

## Two exact bounds missed by P13

### Binary count bound

A five-shell contributes at least four repeat-excess events. Therefore annotation implies R>=4 and 4/B<=t_repeat. For the exact binary floating threshold stored in the gate, this implies:

`B >= ceil(4/t_repeat) = 25`.

P13 currently only checks `B<5` before allocating the set (`n2_p13_harness.py:141`). A check for `B<25` is equally exact and stronger. Compute the integer bound once from `threshold.as_integer_ratio()`; do not substitute a rounded decimal.

### Reuse lower bound from node and edge totals

For a nonempty valid factory DAG with edges to earlier nodes, at least the newest node has no incoming source edge. Let U be the number of distinct child IDs appearing among E edges and N the total number of created nodes. Then U<=N-1 and:

`Q = E-U >= max(0,E-N+1)`.

The dispatcher can bypass before pair-set construction whenever this lower bound exceeds `floor(E*t_reuse)`. This is valid even if the factory retains dead nodes; those make the bound looser. It does not assert every created node is reachable from the final root. The shortcut assumes normal same-factory dense IDs and acyclic construction, which the existing lowering already assumes.

| Corpus | Cases | B<25 bypass | Reuse-bound bypass | Union |
|---|---:|---:|---:|---:|
| P8 training | 188 | 79 | 15 | 92 |
| P8 validation | 98 | 41 | 11 | 51 |
| Gate-P | 36 | 15 | 5 | 19 |
| Natural controls | 10 | 1 | 6 | 7 |

These are exact checks on reconstructed source factories, not fitted thresholds. `python_diagnostics/dispatch_diagnostics.json` preserves per-case records. The reuse statistic is not generally `E-N+1`: among the 36 Gate-P factories, only 13 have exactly one unreferenced created node; the others have 2–5. Replacing the inequality by equality would be an error.

### Cheaper exact reuse scan

P13 multiplies the partial reuse count by a large rational denominator at every repeated edge (`:184`). With final E already known, precompute `allowed = E*tnum//tden` and compare `reuse>allowed`. For nonnegative integer reuse these are equivalent. This removes repeated large-integer multiplication and repeated threshold conversion in wrapper calls.

These bounds are safe at final dispatch. **They are not monotone rejection rules during open-ended construction.** Additional distinct pairs can dilute repeat density, and additional disjoint subgraphs can dilute reuse density. Permanent rejection during construction requires a proven upper bound on remaining binary nodes/edges. Conversely, a small recent-pair cache cannot prove absence of a distant fifth occurrence.

## Frozen exploratory prototype and evidence

`python_diagnostics/dispatch_diagnostics.py` implements `TupleBoundFactory`. Its changes were frozen before its timing run and not tuned afterward:

1. Reuse the already-allocated operand-ID tuple as pair key when ordered; create `(b,a)` only when reversed. The source structural key and node order remain unchanged.
2. Derive B from `len(pairs)` instead of incrementing a separate Python integer attribute on every binary node.
3. Apply the two exact bounds above.
4. Count multiplicities once using `_count_elements`, derive R from dictionary length, then test maximum multiplicity. This trades the original selective set+count plan for one counting pass after the bounds; it is a candidate implementation, not a universal performance theorem.
5. Use precomputed exact rational constants and an integer allowed-reuse count.
6. Return the selected-backend boolean. Full diagnostic counters, labels, and leaf `exp()` are reconstructed separately, outside timing.

Correctness evidence:

- Identical decisions and complete ordered structural-cache keys for all 332 supplied training/validation/evaluation recipes.
- 2,000 further generated DAGs with fixed seed, including TF nodes, n-ary edges, orientation differences, CSE hits, and unused created nodes. These were all bypass cases; they alone would be weak positive-path coverage.
- A separate 4,040 targeted suite, including 273 annotate decisions and 404 cases with 26 distinct ordered/opcode TF/primitive shells. It checks the same exact reference decision, CSE-hit exclusion, and cache identities.
- 14,708 abstract integer-boundary checks for the bound and threshold transformations.
- The timing experiment compares exact polynomial sets outside each measured batch; 2,268 such timed/warmup equality checks pass.

Artifacts: `dispatch_diagnostics.py/json`, `targeted_dispatch_checks.py/json`, `time_frozen_dispatch.py`, `timing_worker_0.json` through `timing_worker_2.json`, and `timing_summary.json`. The scripts/results preserve hashes, seeds, platform, interpreter, GC settings, and raw observations. No original file was changed.

The timing run used three fresh sequential subprocesses on local Windows CPython 3.13.5, five randomized blocks per case, ten operations per block, and two warmups per arm. It had no controlled CPU affinity or power mode. Recipe generation was outside measurement. It is a short diagnostic on repeatedly seen cases, not a publishable performance estimate or untouched holdout.

| Comparison | Case geomean | Sum of case medians | Cases faster |
|---|---:|---:|---:|
| Prototype/P13, Gate-P build+dispatch | 0.9150 | 0.9135 | 36/36 |
| Prototype/P13, Gate-P clean full pipeline | 0.9491 | 0.9519 | 33/36 |
| Prototype/direct, Gate-P clean full pipeline | 1.1220 | 1.0343 | 3/36 |
| P13/direct, Gate-P clean full pipeline | 1.1822 | 1.0865 | 2/36 |
| Prototype/P13, natural build+dispatch | 0.9519 | 0.9619 | 9/10 |
| Prototype/direct, natural build+dispatch | 1.0751 | 1.0844 | 2/10 |

The clean full endpoint uses the matched statistics-free lowering supplied by the mechanism audit; bypass/direct compile the existing source DAG without cloning it, and annotation builds P6 metadata using the unchanged P6 backend. Verification/digests are outside timing. Natural cases were timed for construction/dispatch only; this table makes no natural full-pipeline claim.

The prototype's comparison with P13 deliberately includes all six changes. The gain cannot be assigned to tuple keys, the bounds, or removal of logging individually. In particular, P13 emits a diagnostic dictionary and a predicted leaf ratio, whereas the prototype returns a boolean. A follow-on experiment should split “P13 boolean-only” from “new pair/bound implementation” to isolate the source of improvement. These results justify testing another Python implementation, but they do **not** demonstrate a crossover against an efficient direct baseline.

## Structural interning and the frozen policy

`Factory.bin` intentionally preserves operand order (`03_N1_BASELINE/n1_gatep_harness.py:59–73`). Gate-P constructs `B,A` shells at selected levels (`04_EXPERIMENTS/P08/n2_p8_harness.py:139`). Telemetry then discards orientation before counting pair shells.

For a fixed unordered pair of distinct children and only AND/OR/XOR, the current interner permits six nodes: three opcodes times two orders. If commutative operand order is canonicalized, it permits at most three nodes. Thus the five-shell predicate cannot become true for any entirely primitive AND/OR/XOR source built this way. This is an algebraic fact, not merely a correlation in the selected cases.

An untimed reconstruction canonicalized all 36 Gate-P recipes, preserving local Boolean identities and using the same source randomness. Exact polynomial sets and exhaustive eight-variable oracle values agree. Results:

- Frozen dispatch annotate count falls from 5 to 0; maximum pair-shell count is at most 3.
- Created source nodes: 996 original, 933 canonical.
- Direct evaluated ANF nodes: 932 original, 869 canonical.
- Direct multiplications: 522 original, 478 canonical.
- Direct pair terms: 17,670 original, 17,087 canonical.
- Always-P6 on the canonical source still consumes folds on 27 cases and uses only 758 pair terms and 197 multiplications.

Canonical CSE removes only about 3.3% of total direct pair products here; propagated folding retains a very large work reduction on the canonical DAG. Therefore ordinary commutativity does not explain away the folding mechanism. It does show that the learned predicate identifies one encoding of profitable structure rather than the structure itself.

Canonicalization is a separate, semantics-preserving source-IR transformation, **not** exact preservation of P13 factory counters or frozen policy decisions. Do not silently add it to an “equivalent telemetry implementation” arm or retune the tree on these cases. Test direct and always-folded compilers on the same canonical IR, then train/freeze any new policy using separate discovery/training cases. A canonical-factory Python subclass may add call overhead; operation reductions are not runtime claims, and the prototype is not asserted to be the fastest canonical implementation.

## Timing and profiling issues found in this slice

### Verification inside source-inclusive timing

`n2_p13_harness.py:311–333` starts before source construction and stops after `compile_once` returns. That calls `P06/n2_p6_harness.py:440–459`: its inner `pipeline_ns` stops at line 453, then computes `anf_to_bitset`, the digest, degree statistics, and `dataclasses.asdict`. The outer source-inclusive timer includes those operations. `source_pipeline_ns - source_build_ns - compiler_ns` is therefore a verification/reporting tail plus call overhead, not a missing compiler stage.

Equivalent outputs make much of the tail common work. A large common tail pulls ratios toward one and changes both summed-time case weights and apparent source/compile fractions. It can attenuate losses as well as wins. This should be fixed by returning the polynomial before verification or exposing an explicit computation-end timestamp; correctness can still be checked after every timed batch. Memory scope has the same issue: outer source `tracemalloc` includes the tail even though the inner compiler-only memory pass stops earlier.

### Direct rebuild

P13 source construction produces a complete ordinary DAG. P06 direct compiler then clones and re-interns it (`P06/n2_p6_harness.py:444`), while the folded compiler builds its in-node metadata (`:447`). Both arms are charged for these passes in the recorded endpoint, so this is not an uncharged optimized pass. But direct lowering accepts the original DAG and does not need its clone. At the current small workload sizes this is a material baseline weakness. Report source+direct-lower and source+annotate+fold-lower as an additional fair practical comparison.

### Diagnostic allocation inside dispatch

P13 `dispatch` resets eight diagnostic fields, snapshots `counters()`, and computes a leaf `math.exp()` on several paths (`:129–193`). `source_arm_once` immediately calls `f.counters()` again (`:320`). The second dictionary duplicates a result already returned by dispatch. Reporting work should be separated from the production decision path, and equivalent reporting burden kept outside all timed arms.

### Polluted profiles

P11/P12/P13 profile scripts call `gatep_eval_recipes()` inside every profiled round. That function constructs all 36 original reference DAGs to advance a shared RNG stream (`P08/n2_p8_harness.py:193–200`), then returns builders that construct the target DAG again.

The P13 profile has 13,450 ordinary `_make` calls plus 13,450 target `_make` calls. Its direct profile has 26,900 ordinary calls. About 0.059 of 0.134 profiled seconds in the P13 arm is recipe enumeration, rather than target build/dispatch. Moreover, `profile_p11_build.py` and `profile_p12_build.py` never call dispatch; `profile_p13_build.py` does. Profile totals cannot be compared as equivalent endpoints. Precompute the recipe list once before enabling cProfile, use the same endpoint for each arm, and treat profile allocation/call attribution separately from unbiased elapsed timings.

### Free-telemetry sensitivity model

`P13_POSTHOC_FREE_TELEMETRY.json` reports 0.958020 case geomean and 0.872678 summed-time ratio. It replaces measured source-build+dispatch cost with direct-build cost. This is a post-hoc model, not a measurement or a hard upper/lower bound on a future compiler. Even that modeled case-geomean does not reach the preregistered 0.95 effect-size criterion. Correcting clone and verification/statistics endpoints changes the counterfactual further. “Telemetry is the sole remaining obstacle” is consequently too strong.

## Ranked code changes

Every performance alteration below belongs in a separately frozen experiment; none should rewrite the supplied P1–P13 result files. “Exact” below means backend/output equivalence on the same source representation; source canonicalization preserves Boolean meaning but changes graph/counter values.

| Priority | File/function | Current behavior and proposed change | Expected effect / semantics / registration |
|---|---|---|---|
| 1 | P13 `source_arm_once:311`; P06 `run_pipeline_once:440` | Move verification, digest, degree, report conversion outside source endpoint; retain explicit phase boundaries | Correct measurement meaning; semantics unchanged; new endpoint preregistration mandatory |
| 2 | P06 `run_pipeline_once:444` | Direct lowering consumes existing source DAG; keep clone control arm for continuity | Remove avoidable direct work; output unchanged; benchmark new baseline, no historical relabeling |
| 3 | N1 `update_peak:433`, `lower_anf:437`; P06 `lower_p6` | Use matched statistics-free kernels and gather stats separately | Remove per-result degree scans/counters that can favor work-eliding algorithms; same polynomial; new matched-arm trial |
| 4 | P13 `dispatch:129`, `source_arm_once:320` | Boolean-only production decision; diagnostics outside timing, remove duplicate counters snapshot | Low-risk fixed overhead removal, especially small sources; exact selection; freeze separate arm |
| 5 | P13 `dispatch:141–146` | B<25 and E-N+1 reuse lower bound before pair exactification | Avoid pair/set work for proven negatives; exact; no policy retune, but new implementation preregistration |
| 6 | P13 `_make:93–99`, `dispatch:146–164` | Tuple reuse, derive binary count from list length, count once after bounds | Reduces allocation/increments/duplicate hashing on survivors; exact for ordinary IDs; combined exploratory result above; isolate changes |
| 7 | P13 `dispatch:175–184`; P11 `_ratio_le_int:70` | Cache gate rationals once; integer allowed reuse count | Reduce repeated conversion/wrapper/big-int work; exact threshold; separate ablation |
| 8 | N1 `Factory._make:46`; P13 `_make:78` | Specialize zero/one/two-argument ID creation using indexed tuples rather than a generator; share with all arms | Likely modest construction benefit; preserves keys/IDs; test CSE hit and miss mixes; matched factory prerequisite |
| 9 | N1 `Factory.bin:59`; P08 source recipes | Canonicalize commutative child order in an efficiently shared factory | Stronger baseline; changes source DAG/policy behavior, so new factorial experiment and policy validation mandatory |
| 10 | N1 `lower_anf:438–481`; P06 lower memo | Test dense list memo indexed by nid on supplied dense IDs, preserving demand-driven evaluation | Avoid repeated dict membership/lookups; allocate O(N) refs, may hurt sparse reachable subgraphs; same output, measure separately |
| 11 | Profile scripts; P08 `gatep_eval_recipes:193` | Cache recipes before profiling; identical build vs build+dispatch scopes | Correct profile attribution; no semantics change; corrected exploratory profile sufficient, not a performance claim |
| 12 | P08 `natural_eval_recipes:277` | Replace eager `cache.setdefault(key, parse_blif(path))` with explicit miss check | Avoid duplicate BLIF parsing in recipe setup; outside current timed region, so do not claim compiler speedup |

Dense memoization and tuple-key construction are concrete candidates, not promised wins. Do not replace `dict.get`+assignment by `setdefault` that eagerly constructs a Node on cache hits. Do not remove source fanout checks merely because demand-driven lowering bypasses descendants: sharing profitability remains a separate question.

## Designs considered and why they are not yet the next frozen implementation

- **Recent-pair caches, small lists, staged dictionaries:** can provide positive witnesses, but eviction/limited windows cannot prove shell absence. Exact fallback/replay and its cost are required. A small-list threshold can be selected on a separate microbenchmark discovery set, not the 36 repeatedly seen Gate-P cases.
- **Only count repeats:** still requires exact membership knowledge for first occurrences or a later exact pass. P12 already derives repeats from B-D. A Bloom filter may be a conservative trigger but must not make final negative decisions without an exact guarantee.
- **Piggyback on interning:** current structural keys distinguish opcode, truth token, and orientation. A hit represents an existing node and must not increment shell counts. Grouping a two-level interner by unordered pair could expose multiplicity while serving CSE, but changes allocation/hashing for all arms. Both direct and folded paths must use the same grouped factory and preserve orientation/token distinctions inside each bucket.
- **Uninstrumented build, cache scan at dispatch:** possible exactly because the cache already contains child-ID tuples. Compare a scan of cache keys plus C-backed counting with P13, but do not assume “zero source telemetry” is zero total cost. P7B's full-DAG feature scan failure does not prove a much smaller exact cache-key scan must lose; it is a useful alternative, not yet measured here.
- **Delaying activation:** one cannot know a repeat occurred from an ordinary cache miss without checking the pair under another opcode/orientation. A late trigger needs a replay to recover prior pair membership and counts. It saves work only if the trigger is cheaper than observation and sufficiently uncommon.
- **Cantor pairing / triangular arrays / hand-written Python open addressing:** extra arithmetic, O(N²) address space, or Python probe loops may exceed the cost of C-backed dictionaries. No evidence here justifies replacing P13 with these approaches.
- **Packing `(a<<32)|b`:** exact only with a defined ID range. The harness never checks `<2**32`. The pairs `(0,4294967298)` and `(1,2)` collide under this encoding. This is not an issue for the tiny supplied sources, but a production path needs a bound check/fallback. Tuple keys avoid this latent bound.
- **Start lowering and switch policy later:** Boolean correctness is feasible with careful memo/result reuse, but discovering the frozen global density predicate from only demanded nodes is not equivalent. Some nodes may be pruned or dead; old ANF work is sunk. This should be a different adaptive compiler experiment with explicit transition/accounting rules.

## Preregistration-ready immediate experiment

Run a **matched Python baseline and exact-dispatch factorial experiment** before telemetry-only C. Hypotheses: (H1) a minimal boolean dispatcher with exact bounds reduces construction+dispatch cost relative to P13; (H2) propagated folding remains worthwhile against a statistics-free, no-clone direct implementation; (H3) its advantage depends on source representation and workload structure.

Freeze source recipes and compiler operations. Preserve P8 gate values/thresholds and P6 profitability unchanged in the legacy-source dispatch arms. Freeze the tested prototype without timing-driven edits. Separate these arms:

1. Efficient direct: ordinary shared factory, no unnecessary direct clone, statistics-free ANF lowering.
2. Always-P6: same ordinary source factory, metadata construction and statistics-free folded lowering.
3. P13 decision implementation with boolean-only return and common untimed diagnostics; source representation unchanged.
4. Exact-bounds/tuple/count-once candidate with the same boolean-only interface.

This removes the reporting-overhead confound present in the exploratory candidate/P13 comparison. A separate two-by-two source-canonicalization × direct/always-folded stratum measures generic CSE fairness. Do not force the old five-shell policy onto the canonical source and describe the resulting abstention as failed algebraic opportunity; its representation dependence is already proven.

Primary timing: source recipe execution through returned final sparse ANF; exclude equality/oracle/digest/reporting and trace-memory passes. Include every source observation, threshold decision, metadata build, and lowerer call. Report construction, dispatch, metadata and lowering individually, plus total. Common source RNG recipe generation is included only if it is part of the declared source-input model; also report instruction-trace replay where a parser-equivalent workload is desired. Do not regenerate fixture lists inside timing.

Mandatory correctness gates: all 332 old recipes as regression data; all original fuzz; positive shell/TF, high-sharing, n-ary, dead-node, reversed-order, CSE-hit, threshold-boundary and ID-limit cases. Require byte-for-byte same structural keys for exact-dispatch arms, identical selected backend, exact polynomial sets, and independent bitset equivalence where tractable. Report complete test counts, not only `passed:true`.

Corpora: old 36 Gate-P and ten natural cones are regression strata. Freeze a new synthetic factor grid and independent seeds before timing, covering support size, ANF density, fanout, pair multiplicity, orientation and profitable/unprofitable propagated folds. Separate benchmark discovery from untouched circuit-family test selection. Natural controls must remain a negative-opportunity stratum; add newly frozen natural positive cases discovered without test timing.

Timing design: sequential fresh workers with randomized **complete paired blocks**, adequate warmups, batched operations long enough to dominate timer noise, fixed interpreter/build, documented CPU affinity/power/GC conditions, raw timestamps and trial order. Use at least enough independently scheduled workers to estimate between-process variation; determine the repetition budget in a pilot excluded from inference. Prespecify GC-on primary if that reflects deployment, optional GC-off sensitivity. Do not call nonpaired schedule indices matched repetitions.

Success criteria: zero correctness/decision mismatches; candidate/P13-boolean build+dispatch geomean <=0.95 and total <=0.99 with process-aware 95% upper bound <1; folded candidate/direct case-balanced total <=0.95 with 95% upper bound <1 for an algorithmic crossover claim. Retain natural negative-stratum overhead guardrail <=1.05 and report per-case tails. Failure of the strong crossover criterion is not erased by a secondary summed-time win. Analyze per-case log ratios using paired blocks and a hierarchical process/case bootstrap; stratify depths/families, report geometric mean, median, summed case medians, and contributions. The old cases are fixed regression tests, so any population confidence statement must identify its sampling unit and limitations.

Preserve frozen hashes, code diffs, original and canonical source IDs, fixture instructions/seeds, decisions, root ANF digests, untimed operation counts, all raw timing rows, environment, affinity/power/GC settings, and complete failures/timeouts. Preregister resource/time caps and treat noncompletion as data rather than selectively dropping hard cases.

## When compiled work becomes informative

Ranking by information value for the current evidence:

1. Matched clean Python direct/always-folded/exact-dispatch trial above: isolates whether the remaining gap is telemetry, baseline work, or source policy.
2. Shared compiled factory with a telemetry switch: both arms use identical allocation, interning, canonicalization, node layout and native/Python transition boundaries. Direct pays only genuinely common factory costs. Report incremental telemetry on/off and selected lowering separately.
3. Matched compiled sparse-ANF kernels for direct and folded algorithms: tests whether work reductions survive removal of Python overhead. This is a stronger long-term engineering direction but a larger experiment.
4. Telemetry-only native helper with unchanged Python source factory: useful as a narrow incremental-overhead test, especially batched, but Python per-node packing/list observation remains. A native call per node can cost more than it saves. Do not extrapolate its win to a native Boolean compiler.
5. Alternate runtimes: a PyPy comparison can be informative after correctness; mypyc/Cython require a deliberately typed subset; generic Python set/object recursion is not automatically a suitable Numba kernel. Runtime maturity/availability was not independently benchmarked in this audit, so no performance ranking among those tools is asserted.

If C is chosen, hold source representation, CSE, operand ordering, Node allocation, factory API crossings, direct/folded ANF data structures, memoization, instrumentation, validation placement, and randomization identical wherever not constituting the preregistered incremental difference. Include matched native-direct and native-folded controls when the shared factory/kernel changes. A faster native observed operation is engineering evidence, not evidence that CM is unique or that the original direct baseline was optimal.

## Inspected evidence in this contribution

Read the primary P08, P09, P10, P11, P12 and P13 harnesses, the frozen P8 tree, P12/P13 preregistrations and raw combined JSON schemas, P13 independent verification source and saved fuzz/invariance outputs, P11/P12/P13 profile text and profile-generation scripts, P12/P13 free-telemetry models, the N1 source factory and ANF lowerer, P6 source/clone/lowering entry points, and the P8 recipe/BLIF-construction code. Reconstructed all 332 policy cases using relocated byte-identical runtime sources. Other audit agents cover the rest of the full requested artifact checklist.

The independent verifier checks saved invariance/fuzz flags, row counts, hashes, symbolic digest consistency, and aggregate summaries; reading that script is not itself a fresh semantic rerun. Our diagnostic reruns above and the root auditor's original P13 replay are distinct additional evidence.
