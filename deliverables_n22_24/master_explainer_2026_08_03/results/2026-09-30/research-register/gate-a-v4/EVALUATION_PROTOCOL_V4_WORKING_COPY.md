# Evaluation protocol v4: CM pair-root compiler

Date: 2026-09-23. Author: Brian Theory. **Prospective working copy; NOT FROZEN. Gate A: NO-GO.** No performance observations informed this revision. V3 is preserved unchanged, SHA-256 `54039d0c2ce26a8e9f81dbd6eb60cba6fa093335d1d049afbf6f8269182cdc1f`. This document supersedes v3 only when adopted and bound to a complete, validated freeze manifest. It is not permission to execute Gate B.

## 1. Scientific question and exact algorithm

Does pure structural pair-root compilation deliver an equivalent four-bit function faster than identity-memoized direct packed AST evaluation in the single primary cell below? Secondary questions concern provenance, syntactic sharing, fixed substitutions, ambient dense output, prepared representations, and untouched natural structures. Negative, tied, low-pairability, and generic-equivalence results are valid.

The candidate source is repository `Relative0/Correspondence_Matrices`, commit `0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b`. The audit source manifest identifies exact files and hashes. A later source must have a new manifest and rerun correctness gates. No implementation change is silently folded into this identity.

This is architecture A: **pair-root compilation**. Signed primitive recognition, frame normalization, NOT, and same-frame fusion assemble a root token. Hybrid can tabulate an unsuccessful subtree over four assignments. If the requested root fails, successful child tokens are discarded. The token API returns None and signals fallback; the dense wrapper compiles the original expression through ordinary CM IR. No persistent local-rewrite arm is claimed.

The source grammar is finite, acyclic `Var(int)`, `Not`, `And`, `Or`, `Xor`, `Imp`, `Eqv`. Variable names are `x<index>`. Names in each ordered layout must be distinct; row and column layouts are disjoint. Every occurring variable must have an axis or a fixed binding. Fixed bindings are Boolean values; no custom Var subclasses, malformed nodes, cyclic graphs, or implicit missing-value defaults enter the experimental corpus. Invalid requests are recorded separately from valid NoPair requests.

Define `FV_F(e)=FV(e) - dom(F)` syntactically. No essential-support minimization, constant propagation before pair compilation, or change to identity sharing is allowed. A returned canonical pair uses one row variable and one column variable absent from F. Semantics apply F first, then assign those live pair variables.

Root provenance is S (structural), T (root directly tabulated), or H (structural construction above tabulation). NOT maps S→S, T→H, H→H. Fusion maps (S,S)→S and all other eight ordered combinations→H. The combination is `mu`, not a lattice join. Provenance is mapped to `pure_structural`, `full_retabulation`, `hybrid_pair`. NoPair maps to `ordinary_fallback` plus a separate fallback-executed flag. `requested_strategy` is recorded independently. Historical `structural` is forbidden in this harness.

## 2. Arms and equivalent delivered artifacts

Each case has one immutable canonical identity-DAG serialization preserving both object sharing and equal-but-distinct nodes. Each worker reconstructs the same serialization; arm-private copies prevent cache pollution. Serialization/deserialization and corpus generation are common input staging outside the timer. Preparation unique to an arm is inside its timer.

| Arm ID | Exact preparation and output contract |
|---|---|
| cm_pure | `compile_expr_to_cm_pair_token(...,strategy='pure_structural')`; token plus frame and built-in metrics; timed scalar endpoint extracts the integer token. NoPair is a retained disposition, not an ordinary evaluation. Primary arm. |
| cm_hybrid | Same API, strategy hybrid; any of S/T/H/NoPair is legitimate outside validation-specific strata. |
| cm_tabulate | Same API, strategy retabulate; includes both statistics/discovery passes and four scalar source evaluations; T or NoPair. |
| direct_packed | `build_bitset_env` plus `eval_expr_bitset` on the source identity DAG. Environment construction is charged. Primary comparator. |
| prepared_cse | `compile_expr_cse(flatten=False)` plus binding and execution with the shared packed backend; initial setup charged once. Equal-but-distinct structural interning is explicitly allowed. |
| ordinary_cm | Ordinary IR compile plus the requested token extraction or ambient materialization. IR preparation, all conversions, and output ownership charged. No use of pair speculative artifacts. |
| generic_local | Independent local truth-function optimizer with exactly the same syntactic two-variable information and frame assignments; recognition, tabulation, structural CSE if used, and extraction charged and declared. Implementation must be source-qualified before freezing. |
| robdd | Frozen repository BDD backend and variable order equal to case order; no dynamic variable reordering; build plus assignment query/extraction charged. Manager/version and terminal convention recorded. |
| abc_aig | Mandatory descriptive control on the prospectively frozen translatable natural subset. The delivered artifact is a one-output combinational binary AIG, with current latch values treated as independent inputs. Exact executable/hash, libraries, command script, supported input dialect, conversion/optimization boundary, and ABC CEC check are frozen. This structural endpoint is not pooled with token or dense timing estimands. |

Four-bit producers deliver the identical integer in [0,15], with bit `2*r+c` representing assignment (r,c): MSB-first display `(11,10,01,00)`. Metadata records the canonical frame. Report payload information (4 bits), Python object size, and total prepared-representation size separately. Never equate four information bits with four allocated bytes.

Dense output is **Contract A**: shape `(2**len(rows),2**len(cols))`, false-first lexicographic axes in declared list order, owned writable NumPy bool array, one payload byte per entry. All declared axes remain, even if fixed or absent from the expression. `n_out=len(rows)+len(cols)`; bytes=`2**n_out`. Example rows `[x0,x2]`, cols `[x1]`, F(x2)=1, x0 AND x1 gives `[[0,0],[0,0],[0,1],[0,1]]`, shape (4,2), eight bytes.

Direct dense adapter builds ambient masks then overrides masks for fixed axis names with all-zero/all-one masks, preserving ambient width. Non-axis fixed names are supplied through the fixed map. The audit's `direct_ambient` reference adapter establishes this behavior. The raw direct API gives env precedence on overlap and cannot be called naïvely with conflicting ambient/fixed maps. Every other arm must produce the same fixed-first result. An alternative residual calculation is allowed only with full ambient broadcasting and copying charged.

Dense output admission uses a common `OutputBudget(max_output_bytes=65536, max_temporary_bytes=None, max_output_vars=16, allow_reduced_output=False)` before any arm executes. Packed secondary output uses the same axes, little-endian bit positions, exact `(2**n_out+7)//8` payload bytes, and a separately named endpoint. Budget refusal is not NoPair. The estimator's temporary estimate is a heuristic, not a proven RSS bound. Process memory limits/timeouts remain separate.

All arms record expression identity, variable order, fixed mapping, representation, order, shape, bytes, independent correctness digest, preparation inclusion, sharing, cache policy, and permitted result reuse. A metadata-rich public CM call is compared as that actual call; do not remove its built-in statistics overhead to improve performance. External diagnostic passes run separately from timing.

## 3. Generated corpus

### Sole primary cell

100 distinct serialized formulas; balanced signed/permuted pure grammar; exactly N=1023 and U=N; no fixed variables; canonical frame `(x0,x1)`; token output; reuse K=1; cm_pure versus direct_packed. Primary root outcome S is a correctness requirement, never an attrition filter.

Reproducible generator specification: PCG64 via the frozen NumPy version, seed 2026092301. For each case create 240 binary primitive occurrences over fresh Var(0)/Var(1) objects; primitive operations independently uniform among the five operations. Select exactly 120 primitive positions for operand swap, without replacement. Select exactly 64 of the 480 literal positions for one NOT each, without replacement. Combine the ordered 240 primitive expressions using recursive midpoint splitting; choose each joining operation uniformly except force the final root operation to the case's assigned outer operation. Cases 0–19 use AND at root, 20–39 OR, 40–59 XOR, 60–79 IMP, 80–99 EQV. Every syntactic occurrence has its own object. This gives 959 occurrences before signs and 1023 after 64 NOT nodes. Record actual height (at most 11), do not infer N from a generator parameter.

Reject only an exact duplicate canonical syntax serialization, continuing the same random stream and recording the collision. Do not reject semantic duplicates: only 16 functions exist on this frame. No pairability, latency, memory, or token-value feedback affects generation. Validate all cases before freeze; any failure of the intended pure grammar is a generator/correctness failure, not an excluded case.

### Secondary cells

Preserve v3 strata A–G: exact positive frame, signed/permuted frame, mixed tabulated child, root tabulation, multiple pairs, compound/non-pair boundary, natural. Generated sizes 15,63,255,1023,4095 (balanced) and 15,63,255 (skewed, H<=128); K=1,10,100,1000; token, scalar query, packed, and budget-admitted dense. Identity-shared, equal-but-distinct, and unshared inputs are distinct cells. Fixed false/true, fixed-only, fixed canonical axes, syntactic cancellation, and multi-pair cases are included.

Each secondary cell has 30 distinct syntactic cases and 30 timing repetitions per arm/case, with 15 independent memory repetitions. Exact generators, layout sizes, deterministic sharing transformations, and a finite cell list are enumerated in `SECONDARY_CELLS_V4.json`; its 30 cells specify 900 cases. Full counterbalanced secondary schedules are serialized separately for time and memory. Unsupported endpoint/case combinations are assigned `not_applicable` before execution, not after timings. No opportunistic expansion of secondary cells is allowed after freeze.

## 4. Natural corpus and contamination barrier

Natural results cannot be frozen until a manifest names source project/archive, immutable revision, license, original file/output identifier, acquisition date, extraction tool/version/command, translation rules, inclusion/exclusion rules, original structural support, translated FV_F count, N/U/H, object sharing, equal-but-distinct counts, original content hashes and translated DAG hashes. License compatibility is recorded before distribution.

`NATURAL_CORPUS_PROVENANCE_V4.json` prospectively selected every declared output bit of two MIT-licensed CAM top modules at exact Yosys-bench and upstream commits, recorded all original hashes and staging rules, and fixed translation commands before any pairability pass. Yosys 0.33 and ABC 1.01 are package- and executable-hash bound. All 142 outputs translated, and all 142 one-output native AIG artifacts passed untimed ABC CEC. The pair compiler has not been run on this population; pairability and performance remain unobserved. Do not reuse a favorable selected subset from S1/S2, P14, or later performance campaigns. A previously measured corpus is exposed, not fresh; label it and freeze a new untouched selection or explicitly narrow the intended claim in another successor.

Selection and translation must be finalized before running the pair compiler. Include every selected output, retaining untranslatable/oversized/out-of-grammar cases in the intake ledger with prospectively defined reasons. Do not simplify away hard cases to increase pairability. Then run untimed correctness and report S/T/H/NoPair counts over the full selected denominator; errors/refusals are separate categories. Low pairability is a result and does not trigger corpus replacement. The ABC-translatable subset is defined by parser/dialect constraints alone, before pairability or timing.

## 5. Cache and preparation policy

“Cold” means **fresh process after imports, cold workload-dependent caches**. It does not mean cold operating-system page caches or empty import-time tables. All arms import the same declared common module set before the clock; five CM 16x16 LUTs are import-resident, excluded consistently, and their memory remains in process peak memory. Report this as a post-import API comparison, not process-startup latency.

| State | Cold call | Prepared K reuse |
|---|---|---|
| cm_token composition LRU | `cm_compose.cache_clear()`; 0 entries; LUT arrays remain | Persist within cell only; construction during setup charged |
| normalize row/col permutation and lift LRUs | `clear_cm_normalize_caches()` | Persist within cell |
| bitset env LRU (256) | `clear_bitset_env_cache()` | Build once, setup charged |
| words env LRU (4) and constant LRU (8) | `clear_words_env_cache()` | Persist within cell; no cross-cell reuse |
| IR root cache (4096), persistent cache (16384), alignment LRU | Call all three clear routines; pair fallback reuse flags remain false | Only arm-declared reuse; construction charged |
| AST/IR-attached flat/CSE programs, per-program bound FIFO (64), word plans/scratch and node counts | Fresh deserialized input and new IR/FlatProgram objects; no cached attributes copied | Retain only this case's prepared objects; setup/binding/planning/scratch charged |
| IR builder interning and evaluator identity memo | New per call | Native per-call lifetime unless explicitly the prepared object |
| harness contexts, masks, grids, layouts, truth tables | Fresh contexts; no oracle tables accessible in timed process | Only declared input preparation retained |
| BDD/AIG/generic native state | New manager/process and empty task-specific state; executable exact policy in manifest | Retain declared compiled object only |

Cache reset calls happen outside the timer and counters are captured immediately before and after. Reset failure is a validation failure. Warm-up and correctness run in disposable processes that exit; no untimed call may repopulate a subsequently “cold” worker. Every primary observation uses its own new process and exactly one timed API operation. No inner-loop averaging of warm operations is reported as a cold sample. This deliberately replaces v3's ambiguous ≥100 ms calibrated inner-loop instruction. Each arm's timer starts immediately before its arm-specific preparation and ends after the required artifact exists and required conversion is complete. JSON logging, independent correctness verification, and hashes are outside the timer.

The source's built-in pair counters stay on in timing. Additional work profiling (support passes, visited identities, scalar evaluations, discarded pairs, phase splits) runs untimed on identical cases with separately hashed wrappers; those instrumentation times are not subtracted from measured total. Dense fallback elapsed total includes failed pair attempt, original-root compilation, and materialization.

Prepared endpoints use `T_m(K)=C_m+sum(query_j)`: charge setup once, then K queries from a manifest schedule generated without results. Shared token producers both call `cm_token_value`; they have the same logical query cost, so repeated identical queries cannot reverse setup ordering. Do not claim CM-specific amortization from this comparison. Different prepared representations may have distinct q and meaningful break-even.

## 6. Scheduling, repetitions, memory, failures

Freeze machine CPU, RAM, OS, Python/NumPy, tool versions, thread counts, affinity/power policy, recursion limit, and timer resolution. Do not raise recursion limit. No competing experiment runs concurrently. Scheduling seed 2026092302, PCG64: for each repetition, permute case order; for each case, use 15 CM-first and 15 direct-first repetitions in a seeded random permutation. Secondary arm orders use balanced cyclic orders plus seeded permutation, written in full before execution. Memory schedule seed 2026092303 is separate.

Worker environment fixes `PYTHONHASHSEED=20260923`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and `OPENBLAS_NUM_THREADS=1`. Python garbage collection remains enabled for every arm; run `gc.collect()` once after imports/input staging/cache reset and before measurement, outside the timer, with no collection suppression inside the call. Freeze exact affinity CPU IDs and power mode in the environment manifest; do not silently treat an unset affinity or changed power policy as equivalent. Import order and source dependency closure are identical across primary arms.

Primary: exactly 30 time repetitions for each of 100 cases per arm and 15 memory repetitions per case/arm. Natural: 30 time and 15 memory repetitions per admitted case/arm. Timeout 60 seconds per arm call, process kill recorded; no rerun of a failed row. Infrastructure launch failures before an arm starts may be retried once under the same logical row ID, retaining both attempts. Otherwise a missing/failed primary observation means primary success cannot be declared. No outlier deletion, winsorization, trimming, or post hoc ratio-of-sums alternative.

Peak-memory statistic is absolute peak resident working-set bytes of a dedicated fresh worker, including common imports and staging; no baseline subtraction. On Windows use GetProcessMemoryInfo PeakWorkingSetSize. On Linux use `getrusage(RUSAGE_SELF).ru_maxrss`, converting reported KiB to bytes. Sample inside the worker immediately after artifact production and before oracle verification or serialization; parent captures abnormal termination. Memory runs are separate from time runs and use K=1 in the primary cell. The freeze manifest binds the one applicable platform metric, and the analyzer rejects any other metric. OOM, timeout, budget refusal, exception, semantic disagreement, NoPair, and infrastructure failure have distinct dispositions.

Before final freeze, a separately identified exploratory harness pilot must meet v3's retained repeatability target: for each primary case, median absolute deviation / median <=0.05 for both arms under the selected single-call policy. Freeze the pilot corpus and do not use its performance to select favorable primary formulas. Require measured timer-call overhead <=1% of median measured call duration. If either control fails, revise measurement controls prospectively and requalify; do not relax effect thresholds. Gate A retained four completed non-confirmatory pilots: the mounted-filesystem baseline and three prospective environment-control variants. Timer overhead passed in every completed pilot, but every pilot failed the all-case repeatability rule, including CPU 0 and CPU 11 affinity at nice -20. **STOP: no confirmatory execution is authorized under this v4 timing policy or candidate environment.**

## 7. Sole primary analysis

For case i=1..100 and repetition j=1..30, let D_ij and C_ij be positive integer elapsed nanoseconds from direct_packed and cm_pure. Let

`r_i = median_j(D_ij) / median_j(C_ij)` and `R = median_i(r_i)`.

Median for an even count is the arithmetic mean of the two middle order statistics. Paired hierarchical bootstrap: NumPy PCG64 seed 2026092304; B=20,000 draws. In each draw sample 100 case indices with replacement. For each selected occurrence independently sample 30 repetition indices with replacement, applying the same indices to both arms. Compute each resampled ratio of medians then their median. The percentile CI is the 0.025 and 0.975 quantiles of 20,000 R values, NumPy `method='linear'`. Use float64 for arithmetic after validating integer input. Do not bootstrap timing iterations as independent formulas.

For separate memory observations M_C,ik and M_D,ik (k=1..15), set `m_i=median_k(M_C,ik)/median_k(M_D,ik)` and `M=median_i(m_i)`.

Primary success iff: all required correctness and completion checks pass; all 100 cases have every specified time/memory row; R>=1.20; CI lower bound>1.00; M<=1.10. Equality at the lower CI threshold fails. Any invalid/missing result yields `not_evaluable`, never success; an otherwise complete campaign that misses thresholds yields `utility_not_established`. No secondary result substitutes for primary success.

A ratio 1.20 means C/D=0.8333, approximately 16.7% less elapsed time. The threshold is a prespecified practical decision threshold, not a claim of “20% less time.” Report absolute nanoseconds/bytes and all r_i and m_i.

## 8. Secondary inference and P14 boundary

V3's “correct intervals or tests using BH” is withdrawn. V4 reports secondary effect estimates, counts, all failures, and pointwise descriptive 95% intervals labelled **not simultaneous; no confirmatory secondary significance claims**. There are no secondary null-hypothesis decisions, no BH p-value family, and no claim that BH adjusts confidence intervals. A future inferential family requires a numbered prospective amendment specifying hypotheses, p-values, family members, and coverage before results are seen. This policy avoids an undefined multiplicity procedure while preserving the sole primary claim.

P14 is a different owned-ANF endpoint. Retain only the already printed case-balanced geometric means and stated simultaneous intervals; do not rerun it or read raw performance records in this gate. Synthetic E/D=1.0508 with interval [0.9683,1.1075] is slower by point estimate, not an established slowdown. No P14 or later result fills the pair-compiler evidence gap.

## 9. Freeze gates and immutable artifacts

Require: adopted v4/manuscript agreement; source-qualified regression suite; all adapters source-closed and oracle-equal; natural and generated manifests complete; ABC/BDD environment complete; cold reset assertions; primary analysis code tested on synthetic fixtures; workload scheduling/counterbalance verified; pilot controls met; immutable source/corpus/analysis/environment hashes; empty append-only row files registered by hash. Gate A must be rerun against that exact package before Gate B. Use the attached schema and manifest template; null placeholders are disallowed in a real freeze.

No confirmations, exploratory performance results, or historical timing files were read for this revision. Changes after freeze to scope, arms, endpoints, cache policy, corpus, exclusions, analysis, or thresholds invalidate that freeze and require a numbered successor. Administrative environment corrections also receive a new manifest/run ID with disclosed rationale.

## 10. Change ledger from v3

1. Explicit pair-root boundary, discarded speculative children, and token-versus-dense fallback dispositions.
2. FV_F replaces ambiguous support; S/T/H maps and requested/outcome fields made total.
3. Ambient axes and fixed-first packed adapter frozen; byte units corrected.
4. Cold post-import policy covers every relevant cache; warm-up process separated; single-call observations replace cold/warm-mixing inner loops.
5. 100 cases, 30 time/15 memory repetitions, exact generator and scheduling specified; no change to sole primary frame/N/U/endpoint or 1.20/1.10 thresholds.
6. Ratio-of-per-case-medians, cross-case median, paired hierarchical bootstrap and absolute memory definition made executable.
7. Undefined BH interval language replaced by descriptive-only secondary reporting.
8. Failure/attrition and malformed-input policies made explicit; no result-driven exclusions.
9. The 30-cell/900-case secondary expansion and completed v4 harness are instantiated and hash-bound. Native CUDD and all 142 Yosys/ABC translations are untimed-qualified. The final environment identity remains unfrozen because the repeatability gate failed; that failure is not a waiver.
