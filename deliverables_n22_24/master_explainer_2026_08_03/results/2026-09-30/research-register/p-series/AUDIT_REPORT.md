# CM folding P1–P13: independent technical audit

Audit date: 18 September 2026. The user explicitly invoked the pasted audit prompt. Other document instructions were treated as historical protocols or evidence, not authority to publish, spend money, change the project, or run an unrestricted campaign. All new experiments are exploratory. Ratios are numerator runtime / denominator runtime, so values below one indicate improvement.

## A. Executive verdict

The standalone [executive verdict](EXECUTIVE_VERDICT.md) gives the decision in approximately two pages. The immediate recommendation is **a controlled Python measurement and baseline experiment before telemetry-only C/Cython**. Correct contraction is supported; general practical superiority is unestablished. There are material endpoint, baseline, representation, and generalization issues that native code alone cannot resolve.

## B. Technical audit

### 1. Evidence and verification boundaries

The primary archive was safely extracted into `primary/ASTRA_P1_P13_AUDIT_PACKAGE`; the supplied Gate-A archive into `gatea/Computation_and_Benchmarks`. SHA-256 identities are recorded in `archive_inventory.json`. All 1,004 entries in the package's own `MANIFEST_SHA256.txt` matched. Original files were not patched. Separate `runtime/` copies recreate the directory names expected by imports. These packaged imports otherwise refer to historical `cm_n2_p*_run` directories that do not match the archive's P01–P13 layout.

The public repository snapshot at `1145537c9e2274ae7622dad5b68a7d612b27bb7e` was downloaded; all 13 requested repository paths were recovered with individual hashes in `pinned_repository_manifest.json`. This snapshot is separate from the user's existing checkout at another commit. The authoritative experimental implementations remain the archived harnesses.

The original operator-level paper PDF and original N1 ZIP were not supplied or found in the retrieved snapshot. Their included text/harness/results were sufficient for this performance audit; no claim depends on checking the operator paper's original typography. The supplied phase-calculus PDF has 33 pages; its full text was extracted and the scope and Boolean-to-ANF pages visually checked. Its lifted quantum arithmetic is background, not evidence for these timings. We did not recertify that paper's entire mathematics.

Primary-file inspections and details are documented in [mechanism_baselines.md](mechanism_baselines.md), [statistics_audit.md](statistics_audit.md), and [python_design.md](python_design.md). These are complementary technical appendices, not substitutes for checking source. Required-file inspection status is listed below.

### 2. What the experiment actually computes

**Source representation and interning.** N1 `Node` is a four-slot Python object: integer `nid`, string `op`, argument tuple, and optional value. `Factory._make` interns `(op, ordered child-ID tuple, value)`. IDs are dense within a factory, not globally interchangeable. `Factory.bin` applies elementary constant and identical-object identities, but deliberately preserves operand order otherwise. It therefore shares literally identical ordered expressions, not all commutatively equivalent expressions. Source recipes build Boolean DAGs from Gate-P generators or BLIF sum-of-products expansion. Gate-P source generation itself includes random-number and recipe execution costs.

**Fanout.** Edge-use counts refer to structural references from interned nodes, not repeated evaluations of a node, not truth-table support, and not the number of cache lookup hits. Telemetry counts created source nodes, including nodes made unreachable by later identities; the annotated compiler clone follows the selected root's reachable DAG. A single-root compiler could exploit stronger reuse identities only after proving every stored node is reachable. That invariant does not hold generally in these factories.

**Sparse ANF.** A polynomial is a Python set of integer monomial masks. Bit `i` denotes variable `i`; mask 0 denotes the constant monomial. Symmetric difference implements XOR. Multiplication loops over both sets, ORs masks, and toggles the product in an output set, implementing `x_i^2=x_i` in the Boolean quotient ring over GF(2). The empty set is zero and `{0}` is one. Direct lowering recursively memoizes by node ID. It does not expand repeated visits to the same node again, but it can repeat a product across distinct AND/OR/TF nodes involving the same operands.

**Four-bit signatures.** Token bit `2*x+y` stores the Boolean value at `(x,y)` in order 00,01,10,11. A propagated signature states that a node is exactly a Boolean function of up to two specific source expressions. These bases may each depend on many primary variables. A two-expression signature is not a claim that total primary-variable support is two. Common-frame truth-token composition is exact, including operand swaps and supported polarity alignments such as `NOT(base)`. The frozen recognizer does not propagate signatures through arbitrary standalone NOT nodes; doing so is an additional algorithmic change.

For truth token `(v00,v01,v10,v11)`, the ANF is

`v00 XOR (v10 XOR v00)*a XOR (v01 XOR v00)*b XOR (v11 XOR v10 XOR v01 XOR v00)*a*b`.

No independence between `a` and `b` is required: an identity valid for all four pairs remains valid after substituting arbitrary Boolean expressions. The operator manuscript's narrow structural rule excludes compound operands treated as opaque; P-series use of compound bases is a valid substitution-based extension, which should be stated explicitly rather than described as the identical admitted path of the manuscript.

**Profitability and demand.** P4 propagates semantic information without requiring each intermediate rewrite to be profitable. P5/P6 retain capped term/work estimates, shell information, and use counts in compact metadata; these are heuristic cost estimates, not exact ANF sizes. At demand time the selector compares estimated keep/fold work, penalizes sharing, requires positive benefit and minimum absolute/fractional savings, and either recursively lowers the two signature bases or follows ordinary children. Accepted folds bypass shell descendants before ANF expansion. P2's unused fold plans and P3's shallow recognition explain why propagation plus demand was a meaningful change. Exact formulas and locations are in the mechanism appendix.

**Dispatch.** With the frozen P8 gate and 0.80 cutoff, the sole annotation leaf requires all three predicates:

* maximum unordered-pair shell multiplicity at least 5;
* reuse events / structural edges at most `0.44374121725559235`;
* `(binary nodes - distinct unordered pairs) / binary nodes` at most `0.16333333402872086`.

P11 specializes this conjunction. P12 delays edge-reuse exactification. P13 collects `(min_id << 32) | max_id` per new binary node, uses `set` for cardinality, conditionally counts multiplicities, and scans reuse only for survivors. Pair observation at build time is still incremental work. P13 is not a full-DAG scan-free pipeline: its eligible reuse scan occurs at dispatch, and the compiler subsequently clones the DAG.

### 3. The timing boundary does not match its stated name

P13 `source_arm_once`, lines 311–343, starts an outer timer before source construction and stops it after `compile_once` returns. The `source_build_ns` segment includes dispatch and diagnostic construction. Through P12/P8, `compile_once` reaches P6 `run_pipeline_once`, lines 440–459. That inner function stops `pipeline_ns` after clone/metadata construction and lowering, then performs `anf_to_bitset`, digesting, final-degree scans, dictionary construction, and dataclass serialization. Its return is inside P13's outer timer.

Thus the recorded source endpoint contains output verification/reporting, not just source generation through ANF production. This is a code-confirmed endpoint mismatch with the preregistration, not an allegation of deliberate bias. Final polynomial verification is approximately common work because outputs agree, but common overhead compresses ratios toward one; it cannot simply be ignored near a crossover. Object cleanup and wrappers also contribute to the residual.

We reconstructed **each individual row** as `source_build_ns + compiler_ns`, before taking medians. Dispatch is already in the first field. This estimates the declared compiler-focused segments but does not recover every desirable lifecycle cost. It is a sensitivity analysis; a future run needs a single explicit boundary returning the polynomial before verification.

| Gate-P phase | Published outer geomean | Reconstructed geomean | Reconstructed case-bootstrap 95% interval | Reconstructed summed-median ratio |
|---|---:|---:|---:|---:|
| P11 | 1.043490 | 1.102008 | [1.002711, 1.175773] | 1.000389 |
| P12 | 1.019888 | 1.072517 | [0.981217, 1.143754] | 0.974558 |
| P13 | 1.016459 | 1.052094 | [0.962738, 1.121505] | 0.958750 |

Do not compare different phases as controlled sequential improvements: each row has its own concurrent direct arm and host session. The P13 residual accounts for roughly 42% of summed direct Gate-P source timings. The reported results are arithmetically reproducible, but the headline source endpoint was mislabeled relative to its declared scope.

The documented P7B correction discarded contaminated evaluation timing and switched to adding inner compiler time to probe/dispatch time. That corrected time should be authoritative for P7B. It does not immunize the later P8 source wrapper. P7B also retains a memory-boundary mismatch: dispatch's tracing wraps backend verification, whereas the direct/backend trace stops before it.

### 4. Baseline fairness: four distinct questions

**Does optimized code receive uncharged metadata?** Lower-only P4+ comparisons intentionally start with annotated nodes; they establish a conditional lowering result and cannot establish a source-inclusive win. The later source wrappers charge telemetry, selected annotation/clone, and lowering. No evidence was found that P13 secretly gets signature construction for free in that endpoint. However endpoint exclusions and the extra verification work still need correction.

**Does direct perform avoidable inherited work?** Yes. P6's direct pipeline clones/reinterns the already freshly built source into another ordinary factory. Direct `lower_anf` needs no extra node representation to consume that source. Both direct and P6 retain ANF counters and repeated peak-degree scans. A flag named `collect_stats=False` does not turn those off. These are not ordinary requirements for producing ANF.

**Could a better direct implementation narrow the win?** Yes, experimentally. We generated separate AST-transformed functions removing ANF statistics, disabled selector-reporting blocks, and reporting-only traversal; algebra and acceptance predicates stayed fixed. Original code was retained and diffs were saved. Three sequential fresh Windows CPython 3.13.5 processes, 36 known cases, randomized blocks, 8 blocks × 12 inner repeats, produced 6,912 raw batch observations and 864 initial arm/case equality checks; every measured batch's final output also matched.

| Exploratory comparison | Case geomean | Summed medians |
|---|---:|---:|
| Original algebra/diagnostics, P13 / direct; verification excluded | 1.0652 | 0.9836 |
| Statistics removed, P13 / direct; original cloning retained | 1.0910 | 1.0075 |
| Statistics-free direct / original direct | 0.7870 | 0.7809 |
| Statistics-free direct without clone / with clone | 0.7019 | 0.7298 |
| Statistics-free P13 with bypass clone removed / equally improved direct | 1.1891 | 1.0869 |

These are local exploratory diagnostics, not replications of the original machine or confidence intervals for the project. No affinity/power control was imposed; fresh processes and longer batches reduce some noise but do not establish host stability. They are sufficient to reject the assumption that pair telemetry is the only meaningful untested cost.

**Are we charging optimized code for normal compiler data?** Dense IDs, opcode, ordered operand IDs, and an interning key are normal in this specific baseline. Reading them is cheap, but additional tuple/int construction, a second pair lookup, appends, counters, and scans are incremental. Fanout is common in some compilers but absent here; show both a native-fanout scenario and the actual incremental cost rather than declare it universally free. Exact support size and profitability metadata are not automatically available. Pair multiplicities and the frozen policy's features are especially not normal compiler givens.

### 5. Mechanism classification and stronger comparators

The transformation combines exact two-expression truth-function propagation, frame normalization, Boolean algebraic strength reduction, and demand-driven DAG contraction. It is stronger than literal CSE, because it recognizes semantic equivalence across different operator shells. It is not an independent source of Boolean information beyond a four-entry truth function. It is neither a general superoptimizer nor a general two-cut enumerator. Calling it **propagated two-support truth-function contraction** is both accurate and compatible with the CM motivation.

N1's generic implementation already includes common-pair token composition and adds a primary-support retabulation path; it is not an independent implementation of the same algorithm. The supplied Gate-A S1/S2 raw data contain 10,500 rows, of which 10,389 satisfy admission, with no CM/generic mismatch in digests or reported multiplication/pair/peak metrics. That equivalence is useful evidence about semantics and scope, but not a matched replacement for P13's propagated, demand-driven ANF implementation.

The pinned repository's `cut_fusion.py` is an appropriate source for a bounded-cut comparator: it enumerates real small cuts, uses truth functions/templates, guards fanout, and checks whole-program benefit. Its output/execution contract is packed truth-vector computation, so port the recognition strategy to the same ANF endpoint or measure all conversion costs; do not compare its old timings directly against P13. Existing CSE, expression rewrites, and dispatchers likewise need matched contracts. [Mockturtle's cut-enumeration documentation](https://mockturtle.readthedocs.io/en/latest/algorithms/cut_enumeration.html) supplies a standard generic framing for cut-based recognition.

Comparator priority: (1) improved direct sparse ANF; (2) the same propagated signatures and selector described and independently checked as generic truth-function contraction; (3) commutative CSE; (4) bounded-cut/LUT contraction with the same ANF output; then BDD, AIG rewriting, Espresso, or broader supergate methods where their conversion and preprocessing costs fit the workload. External tools are not free preprocessing. Product memoization and coefficient-directed lowering are especially relevant shared-kernel baselines.

### 6. Representation dependence does not erase the algebraic benefit

Telemetry observes unique interned nodes, not every request to construct a node. On AND/OR/XOR-only sources with ordered interning, an unordered pair can produce six distinct shells: three operators in two orders. With commutative operand canonicalization it can produce at most three. Consequently the frozen `>=5` gate is impossible on those canonicalized sources.

An independent diagnostic canonicalized all 36 Gate-P source DAGs and checked exact polynomial and exhaustive eight-variable Boolean outputs. Annotation changed from 5 cases to 0. Total stored source nodes fell 996→933, evaluated direct nodes 932→869, multiplications 522→478, and pair products 17,670→17,087. Always-P6 on canonical sources still accepted folds in 27/36 cases and performed only 758 pair products. The small direct work reduction cannot explain away the much larger contraction reduction. Nevertheless the **policy** is sensitive to irrelevant representation choices and will need separately trained/calibrated treatment before transfer to another factory.

The subclass-based Python canonicalizer was about 1.069× the cleaned ordered direct path by geomean in our run. Extra method/branch cost exceeded its work savings. That result neither excuses omitting CSE as a comparator nor proves a production canonical factory would be slower.

### 7. Exact Python opportunities that P13 had not exhausted

Let `B` be counted binary nodes, `D` distinct unordered pairs, `R=B-D`, `E` total structural edges, `N` stored nodes, and `q` the number of nodes used as children at least once. Reuse events are `U=E-q`.

* A five-shell requires `R>=4`. Combining it with `R/B<=0.16333333402872086` gives **B>=25**. P13's initial `B<5` check is much weaker.
* A nonempty acyclic factory has at least one node never used as a child, so `q<=N-1`, hence **U>=max(0,E-N+1)**. If that lower bound already exceeds the frozen reuse allowance, bypass before exact pair counting. Do not replace it with equality unless reachability/single-sink invariants are proved; these factories can retain discarded nodes.
* Convert `U/E<=t` into `U<=floor(E*tnum/tden)` once, using `t.as_integer_ratio()`, rather than multiply two large integers at every reuse event. Preserve the exact frozen binary-float threshold.
* Reuse the existing child-ID tuple when its order is canonical; allocate a reversed tuple only when necessary. This can remove packed Python-integer shifts and ORs. Whether tuples beat integers is workload-dependent.
* Count once in the C-backed counting loop rather than creating a set then sometimes counting again. This changes the cost tradeoff for cases that previously exited after a cheap set; it must be measured, not assumed.
* Keep decision-only dispatch separate from diagnostic dictionaries, exponentiation of leaf predictions, and reason reporting. Reconstruct diagnostics outside the measured interval.

The prototype combines these ideas; its source, exactness checks, hashes, and raw timings are under `python_diagnostics/`. It preserves construction cache structure and Boolean decisions, not identical historical diagnostic reason codes or scan traces. On 332 archived recipes and 2,000 additional DAGs there were no mismatches. Separately, 4,040 targeted dispatch cases passed, including 273 annotation decisions and 404 saturated-TF cases; 14,708 integer-boundary checks also passed. These counts describe different checks, not thousands of independent full ANF compilations. Bounds alone can rule out pair work on 19 Gate-P and seven natural cases.

Three fresh sequential process runs showed candidate/P13 ratios of approximately 0.915 for Gate-P build+dispatch and 0.949 for the statistics-free selected pipeline with bypass cloning removed. Candidate/improved-direct remained 1.122 case-balanced and 1.034 by summed medians. Natural **build-only** candidate/P13 was about 0.952; that is not natural folding performance. These observations show remaining Python headroom; they do not isolate which combined change caused it.

Other suggestions require care. Tiny recent-pair caches are exact only as positive witnesses or with a fallback; a miss cannot establish absence. Delayed activation needs retained history or a proof that earlier nodes cannot affect a final predicate. Build-prefix density is not monotone when future denominators can grow, so permanently shutting telemetry off without a final-size bound is unsound. Piggybacking on structural-cache hits alone misses different operators and swapped operands on the same pair. Small-list hybrids, staged dictionaries, open addressing in Python, triangular IDs, and adaptive direct-then-fold lowering may be explored on development inputs, but none presently has better evidence than the exact bounds and shared tuple strategy. Switching after direct work has already expanded descendants incurs sunk cost and may sacrifice the chief benefit of demand-driven contraction.

### 8. Timing, statistics, memory, and inference

The historical harness uses `perf_counter_ns`, deterministic shuffled arm schedules, case medians, and a seeded bootstrap of case ratios. P11–P13 scheduling and sample counts match their frozen code. Ninety supplied summary estimates/intervals were independently recomputed to floating-point precision. This rules out a simple summarization arithmetic mistake.

It does not establish precision for a 1–5% machine effect. The schedules shuffle all arm repetitions within a case; the integer `rep` is a schedule position, not an arm-paired experimental block. Case-level pairing is valid; treating equal `rep` numbers as simultaneous paired observations would not be. The bootstrap treats measured case-median ratios as fixed and resamples cases, capturing empirical workload heterogeneity rather than full uncertainty across processes, sessions, machines, or human benchmark selection. Excluding parity (one) from such a ratio interval is not immunity from timer bias.

Warm state includes prior symbolic/correctness calls, allocator reuse, and repeated recipes. There is no adequately documented CPU affinity, stable frequency/power control, GC policy, or cross-session design to resolve close rankings robustly. GC is not automatically bad; its treatment must be consistent and declared. A disabled-GC sensitivity run can accompany a realistic GC-enabled primary run. Use independent worker processes with matched randomized blocks, fixed warmup rules, and sufficiently long batches. Record the CPU/runtime/OS/hash seed/power/affinity metadata and raw block order. [pyperf documents calibrated batches and multiple worker processes](https://pyperf.readthedocs.io/en/latest/run_benchmark.html); [its system guidance](https://pyperf.readthedocs.io/en/latest/system.html) discusses affinity and frequency stability. Do not alter the user's machine settings merely to execute this audit.

For a future inference, resample workload families/cases and paired process blocks in a hierarchical analysis; separately report a fixed-suite machine-repeat interval. A paired log-ratio analysis or blockwise sign-flip/permutation sensitivity is useful when its exchangeability assumptions are stated. More repetitions cannot repair a contaminated endpoint or a weak population definition.

Memory endpoints are not whole-process RSS. `tracemalloc` measures traced Python allocations only while enabled; lower-only runs exclude pre-existing DAG storage, and source wrappers can include verification temporaries. P13's reported Gate-P peak-memory geomean is 0.993050 but its median case ratio is 1.062963. Production-only peaks cannot be reconstructed by subtracting reported peaks. P7's packed arrays can save memory without winning Python construction time. P7 also differs from P6 in some statistics accounting, so its timing is not a perfectly isolated storage experiment. Future reports need process RSS plus traced Python peak and an explicit retained-input/output lifetime convention.

P11/P12/P13 build profiles include `gatep_eval_recipes()` rebuilding ordinary reference DAGs to advance RNG state. In P13, roughly half the profiled `_make` calls are common recipe generation rather than the target build. P11/P12 profiling excludes dispatch; P13 includes it. Whole-profile totals are therefore not interchangeable incremental telemetry measurements. The actual timed cases pre-enumerate recipes, so this is a profile interpretation issue rather than an additional measured-case contamination.

### 9. Geometric means, aggregate time, and break-even

For per-case median times `O_i,D_i`, `exp(mean(log(O_i/D_i)))` answers the multiplicative relative performance for an equally weighted case drawn from this empirical suite. It does not give total wall time. `sum(O_i)/sum(D_i)` estimates the ratio for one occurrence of every case at its typical measured time; equivalently it weights relative ratios by direct time. Both are legitimate. Neither identifies production frequencies without an independently specified workload distribution.

P13's original case median ratio is 1.05110, geomean 1.01646, and summed medians 9.208616 ms / 9.393968 ms = 0.980269. Reconstructed values are median 1.10854, geomean 1.05209, and 5.118794 ms / 5.339028 ms = 0.958750. Only three cases win in either accounting. Tables for all cases and contributions are saved as CSVs.

| Gate-P depth | Original geomean | Reconstructed geomean | Reconstructed median case ratio | Reconstructed sum ratio |
|---|---:|---:|---:|---:|
| 6 | 1.032307 | 1.070316 | 1.074211 | 1.062179 |
| 8 | 0.979704 | 1.018475 | 1.112231 | 0.831483 |
| 10 | 1.038404 | 1.068318 | 1.108545 | 1.015926 |

Nominal generator depth is not realized ANF difficulty: identities and sharing can collapse a generated shell. Depth eight's sum benefit is concentrated in case `8:11`. On the original endpoint this case saves 501.765 microseconds, 271% of the total net saving; `10:2` contributes another 172.755 microseconds, 93%. Other cases offset those gains. Omitting `8:11` raises the aggregate ratio to 1.037061. Report this sensitivity rather than discarding the case after seeing it.

A useful break-even model is `incremental build + dispatch + annotation + selected lowering - direct lowering < 0`, with every common stage identical or canceled under an explicit contract. Plot total difference against direct time, pair products, actual ANF density, and sharing; stratify by representation and family. A single direct-workload-size threshold is not established by 36 confounded points. The per-case CSV provides the observed coordinates; [P14's synthetic design](P14_PREREGISTRATION_DRAFT.md) specifies how to identify a causal break-even surface rather than fit a favorable curve post hoc.

### 10. Benchmark selection, leakage, and natural opportunity

All six embedded BLIF sources were readable and their SHA-256 and Git blob IDs matched. P1's ten selected cones and P8's train/validation selections were independently reconstructed. The evaluation deliberately selects constrained support and node sizes from already size-optimized LUT circuits, expands them to AND/OR source recipes, and samples only a few roots. It does not represent all EPFL outputs, raw RTL, AIG structure, or a random production corpus. Zero accepted folds in ten selected cones is useful overhead-control evidence, not an estimate that natural circuits never fold.

P8 evaluation roots are distinct from train/validation roots, but the underlying circuits and some internal nodes overlap. Shared internal-node counts include adder 2, cavlc 11, int2float 6, priority 3, router 2. Root disjointness is a weaker boundary than circuit-family disjointness. Reusing the same Gate-P evaluation family through thirteen architecture revisions permits human adaptation even if each pass freezes its own implementation. Preregistration hashes establish artifact identity, not independent proof of preregistration time; the package lacks a separate trusted chronology sufficient to certify that.

For natural discovery, scan a **development-only** collection for coverage and structural motifs before looking at runtime outcomes. Include original and synthesized forms of arithmetic, mux/select, decoders, control circuits, and cryptographic Boolean circuits. Use per-circuit sampling across outputs and cone sizes, preserving both naturally occurring opportunities and zero-opportunity cases. The [EPFL repository](https://github.com/lsils/benchmarks) provides arithmetic and random/control categories and multiple circuit formats. Discovering candidates is legitimate, but report the fraction of scanned circuits/cones that qualify and the preprocessing search cost if it belongs to deployment.

Reserve entirely different circuit families/provenances as a sealed test manifest. Freeze sampling, support/resource limits, representations, and feature computation before inspecting folds or times on that set. Split at design/family level, including all outputs and synthesis variants of one design in one split. Report unconditional corpus performance and a separately declared mechanism-positive stratum; do not publish only circuits discovered to win. Where exhaustive truth vectors are infeasible, use exact ANF equality on tractable cases and a suitable independent equivalence checker with explicit timeout handling.

### 11. Better policy targets

The current gate predicts a fixed backend's runtime ratio through structural proxies and admits only one leaf. Preserving it is valuable for implementation experiments, not evidence that it is the best long-term policy. A future policy should estimate **net time saved**, accounting for saved pair-product expansion, node/term sizes, shared descendants, annotation cost, and telemetry itself. Report false positives and false negatives against always-P6 using clean endpoints; do not retune on the repeatedly examined 36 cases.

An analytic model such as estimated saved kernel work minus representation-specific incremental costs may transfer better than shell multiplicity, especially across operand canonicalization. Calibrate constants only on development machines/workloads. Compare an analytic model, a learned model, and a no-dispatch/always-direct policy on sealed test families. Prediction targets must include the baseline improvements; a tree trained against the slower inherited baseline need not remain calibrated.

## C. Ranked code-level cleanup list

Exact line evidence and fuller implementation notes are in the appendices. Every future timed comparison must freeze/hash the changed code; 'same Boolean semantics' does not make a post-hoc change preregistered.

| Priority | File/function | Current behavior → proposed change | Expected effect and semantic boundary | Registration |
|---|---|---|---|---|
| 1 | P08–P13 `source_arm_once`; P06 `run_pipeline_once` | Outer timer includes verification → return polynomial at declared boundary; validate afterward | Repairs endpoint; can move ratios away from one; no Boolean change | Explicit correction, new clean run |
| 2 | N1 `lower_anf`, `mul_poly`, `update_peak`; P06 `lower_p6`; P03 `apply_tf_poly` | Statistics and monomial scans in timing → separate instrumented analysis and lean shared kernel | Large measured diagnostic overhead; no Boolean/selector change | New matched implementation experiment |
| 3 | P06 `run_pipeline_once` direct; P08–P13 bypass | Clone fresh ordinary source again → lower existing source | Removes allocation/hash/traversal work; same ANF, node IDs remain factory-local | New baseline and matched bypass |
| 4 | P13 `dispatch`, `_make` | Weak B<5 test, packed keys, set then counts → B>=25/reuse bounds, cached tuples, one count pass | Preserves Boolean decision; combined prototype improved P13 locally | New exact-equivalence experiment |
| 5 | P11–P13 dispatch return/reporting | Diagnostic dictionaries and leaf exponentiation timed → Boolean-only decision, untimed report | Removes bookkeeping; does change diagnostic API/trace | Freeze interface and equality scope |
| 6 | N1 `Factory.bin`, interning | Ordered commutative nodes → canonical AND/OR/XOR keys | Same Boolean result; changes DAG and frozen-policy decisions; speed uncertain | Separate representation factorial; no disguised policy equivalence |
| 7 | P03 `apply_tf_poly`, P06 accepted fold path | Eagerly lower both bases → inspect ANF coefficients first | Avoids irrelevant bases for constants/projections; same polynomial, changed work/counts | New algorithmic experiment; all16 tokens |
| 8 | N1/shared `mul_poly` | General product always → zero/one shortcuts and optional Boolean idempotence | Same polynomial; equality-check cost may outweigh benefit | Matched direct/folded kernel ablation |
| 9 | N1/shared lowerer | Memoize node result only → cache partial products across AND/OR/TF shells | Same polynomial; extra memory/key overhead; avoid unsafe mutable-set aliasing | Shared-kernel experiment |
| 10 | N1/P06 recursive memo | Dictionary and recursive calls → dense list memo/sentinel, specialized arity keys; iterative option | Same semantics for dense local IDs; recursion/scaling benefit uncertain | Implementation experiment with DAG tests |
| 11 | P11–P13 `profile_*_build.py` | Recipe regeneration included, dispatch boundaries differ → prebuild recipes and profile identical scopes | Better diagnosis, not a measured compiler speedup | Label corrected profiles |
| 12 | P05–P07 metadata/pair encodings | Fixed-width assumptions/caps → explicit ID/estimate bounds and overflow guards in native ports | Avoids porting truncation/overflow into correctness bugs | Mandatory correctness specification |

Smaller loop binding, `__slots__`, and tuple reductions should follow profiles from the cleaned pipeline, not precede it. `Node` already has slots; replacing a nonexistent node dataclass is not an optimization. Do not replace all set/dict operations with bespoke Python arrays merely because storage is compact: P5–P7 already demonstrate that extra Python indexing and integer packing can overwhelm memory gains.

## D. Experimental gaps before publication

**Mandatory:** clean timing/memory boundaries; lean direct and folded kernels; no redundant direct clone; independent generic propagated comparator; representation stress and canonical CSE; positive-path targeted correctness; fresh-process repeated-session timing; circuit-family holdout with opportunity prevalence; separate case-balanced and deployment-weighted estimands; code/data/environment and exclusion manifests. A natural-folding speedup claim additionally requires natural cases where folds actually fire and improve total time under a frozen test protocol.

**High value:** shared product caching and coefficient-directed lowering; calibrated analytic cost policy; family-level break-even surfaces; cross-runtime/cross-machine replication; peak RSS and lifecycle accounting; larger-support tests using independent equivalence checks; include timeouts and ANF blowups as outcomes rather than silently dropping them.

**Optional:** broad BDD/AIG/Espresso comparisons when output contracts can be matched; GPU/Numba or full Rust core rewrites; quantum-calculus extensions. These are not prerequisites for demonstrating the narrow symbolic-contraction result and should not postpone fixing the current measurement.

## E. Concrete P14 recommendation

[P14_PREREGISTRATION_DRAFT.md](P14_PREREGISTRATION_DRAFT.md) contains a freeze-ready specification. It is explicitly a **draft**, because this audit has already seen development results and an untouched test manifest/environment still must be sealed. It defines exact hypotheses, implementation deltas, arms, endpoint/lifetime contracts, correctness gates, held-out designs, thresholds, statistics, and artifacts. The next experiment is called **P14-PY0: repaired measurement and exact Python dispatch against a lean direct baseline**.

## F. Alternatives and compiled fairness

Ranked by scientific information first:

1. **Stay in CPython for P14-PY0.** Highest immediate value, low effort relative to a port. The audit supplies a verified candidate and shows baseline costs materially change the conclusion.
2. **Matched compiled sparse-ANF core.** After the cleaned Python result, this best tests whether algebraic savings survive a faster shared arithmetic kernel. Both direct and folded arms use it; broad effort and output/memory conventions must be controlled.
3. **Compiled common source factory with optional telemetry.** Best test of compiler integration if construction dominates. Share allocation, interning, IDs, canonicalization, and FFI batching. Direct telemetry-off is essential; a forced-bypass telemetry-on arm measures the tax.
4. **Telemetry-only C/Cython.** A focused engineering option after P14-PY0; less informative about algorithmic merit. P13 already uses C-backed set/count operations, so speeding the residual requires attention to crossing/boxing costs, not just compiling a Python loop. Do not call it a matched language-level algorithm comparison.
5. **Alternate runtimes.** An inexpensive PyPy pilot of both complete paths can test runtime sensitivity, but requires JIT warmup and startup/steady-state separation. mypyc needs useful type information; Cython's benefit depends on typed native operations. Numba is a better fit for a redesigned typed numeric kernel than this dynamic Python DAG. Rust is a reasonable larger typed-core engineering choice, not the cheapest causal experiment. These are suitability judgments, not measured speed forecasts. See [PyPy](https://pypy.org/performance.html), [mypyc](https://mypyc.readthedocs.io/en/latest/introduction.html), [Cython](https://docs.cython.org/en/latest/src/userguide/numpy_tutorial.html), and [Numba](https://numba.readthedocs.io/en/stable/user/performance-tips.html).

Three strong alternative P14s are therefore: a matched lean-kernel/product-cache factorial; a generic propagated-signature versus bounded-cut algorithm comparison; and an untouched natural-opportunity census followed by sealed test timing. Each answers a more fundamental open question than reducing one observed CPython counter cost.

A compiled observer is incremental functionality that direct does not need. It is not intrinsically unfair to implement only that functionality in native code while keeping common operations identical. The error is attributing all resulting improvement to a new algorithm, or compiling common work only on the optimized path. A fair native factorial uses shared source allocation/interning and kernel, comparing telemetry off/direct, telemetry on/forced direct, telemetry on/selected folding, and generic folding. Preserve a best direct arm without forced extra metadata. Report cold startup, steady compile, lower-only, and end-to-end separately, including FFI and ownership conversion.

## G. Red-team account

The strongest skeptical explanation is that Gate-P is tailored to repeat a narrow pair structure; an order-sensitive factory creates avoidable duplicates; a diagnostic-heavy ANF kernel rewards skipping instrumented nodes; the baseline rebuilds work; common verification compresses headline ratios; two large winners carry the weighted result; and thirteen iterations adapt the architecture to a reused benchmark. A generic truth-function implementation can reproduce the same algebra. These explanations **survive** as material qualifications on runtime magnitude, representation robustness, novelty, and generalization.

They do not fully explain away the optimization. Exact polynomial equality, exhaustive small-domain checks, replayed decision invariance, and large pair-product reductions after commutative canonicalization remain. Common verification adds work to both paths; it can distort relative ratios but cannot manufacture the observed algebraic identity or explain the surviving operation reduction. Removing statistics does not make contraction mathematically disappear. The defensible negative conclusion is narrower: **the useful mechanism has not yet earned the broad performance interpretation assigned to it, and the current selected pipeline is weak against a better direct baseline.**

## H. Positive case and publication language

The technically strongest case is that semantic information can remain valuable through locally unattractive intermediates. Propagating a tiny exact function of two expression bases and waiting until demand exposes a profitable ancestor can avoid large intermediate polynomial products. This is a credible compiler technique for formula-to-ANF workloads with suitable repeated structure. The usefulness need not depend on CM uniqueness, and a modest total-time benefit in an honestly specified workload distribution could still matter.

**Supported now:** exact common-frame Boolean contraction on the tested domain; substantial reductions in symbolic pair-product work on Gate-P; ancestor propagation recovering opportunities shallow recognition misses; equality of selected outputs; declining implementation overhead across some simultaneous comparisons; natural abstention on this small selected corpus.

**Suggestive only:** meaningful speedups against a lean implementation in a useful deployment population; generic applicability to natural circuits; transfer to canonicalized IR; the fitted dispatch model's generalization; native implementation crossover.

**Unsupported:** universal or natural-corpus CM acceleration; a new Boolean-information capability beyond generic truth functions; a statistically established P13 case-balanced direct crossover; an inherent C/Cython solution to the remaining gap; quantum computational advantage from these experiments.

The reconciled judgment is to preserve the mechanism and narrow the claim. The project should now test whether its algebraic savings repay their true incremental cost against a credible implementation and on fresh opportunity-bearing workloads.

## Required artifact inspection checklist

All files below were successfully inspected by the audit team, including primary code rather than summaries alone. This is inspection status, not a claim to have rerun every historical experiment.

| Requested artifact | Status |
|---|---|
| `03_N1_BASELINE/n1_gatep_harness.py`; `SHARING_GUARD_DIAGNOSTIC.md` | Inspected; direct/selector/kernel and sharing analysis |
| `P01/n2_p1_harness.py`; `P02/n2_p2_harness.py`; `P03/n2_p3_harness.py` | Inspected with preregistrations and raw evidence |
| `P04/n2_p4_harness.py`; `P05/n2_p5_harness.py`; `P06/n2_p6_harness.py`; `P07/n2_p7_harness.py` | Inspected; propagated metadata, selectors, kernels, timing/storage |
| `P07B/n2_p7b_harness.py`; `P7B_TIMING_CORRECTION.md` | Inspected; corrected time authoritative, memory caveat identified |
| `P08/n2_p8_harness.py`; `P8_FROZEN_GATE.json` | Inspected; policy, training, selection and source wrappers |
| `P09/n2_p9_harness.py`; `P10/n2_p10_harness.py`; `P11/n2_p11_harness.py` | Inspected; counter and factory specialization |
| `P12/n2_p12_harness.py`; `P13/n2_p13_harness.py` | Inspected; exactness, lazy scans, raw schedules and replay |
| P12/P13 raw result JSONs and component case files | Inspected and recomputed; row/summary/schedule checks |
| P11/P12/P13 post-hoc build profiles and scripts | Inspected; mismatched profile scope identified |
| Six pinned BLIF inputs | All parsed; SHA-256/Git blobs and selection replay matched |
| `P1_NATURAL_SELECTION_FROZEN.json`; `P8_EPFL_TRAINVAL_SELECTION.json` | Inspected and independently reconstructed |
| `02_BACKGROUND/operator-level-boolean-computation-with-correspondence-matrices.txt` | Inspected; token/frame/theorem scope checked |
| Added S1/S2 Gate-A archive | Primary comparator code and raw equality/admission checks inspected |
| Original `CM_Phase_Calculus_Verified.pdf` | Full text extracted; relevant scope and ANF pages visually checked; contextual use only |
| Broader repository at requested commit | Snapshot retrieved; requested 13 source paths recovered and relevant competitors inspected |

## Final answer to the prompt's research decision

**Yes, one more pure-Python experiment is warranted.** Run P14-PY0 before native telemetry. Its value is identifying whether there is a practically important advantage left after fixing measurement and baseline overhead, while testing a demonstrably unexhausted exact Python implementation. Proceed to a native factorial only after that result and a sealed holdout establish which cost actually warrants compilation. No publication, commit, push, native port, paid compute, or new full benchmark campaign was performed as part of this audit.
