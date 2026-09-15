# Evaluation protocol v3: typed CM pair compilation

Protocol date: 2026-09-15  
Paper: **Operator-Level Boolean Computation with Correspondence Matrices**  
Prospective sole author: **Brian Theory**  
Status: **analysis plan complete; corpus, environment, and run manifest remain
unfrozen; no confirmatory measurement is authorized under this file alone**

This protocol supersedes v2 because it changes the compiler arms, primary
decision rule, workload factors, and instrumentation. Exploratory pilot results
cannot be presented as confirmatory evidence. Any later material change to the
primary cell, endpoints, thresholds, corpus, baselines, exclusions, or analysis
requires a numbered successor protocol.

## Questions and evidence boundary

1. Does every pure structural, hybrid, and whole-root-retabulation result agree
   with the source expression on the declared frame?
2. How much work does pure structural token fusion avoid relative to four-pass
   retabulation?
3. Does that mechanism reduce user-visible cost against a direct packed-AST
   evaluator in one prespecified useful-region cell?
4. How do outcomes change with signed operands, failed recognition, sharing,
   fixed substitutions, reuse, natural circuits, and explicit output?

The paper makes no speed, memory, prevalence, or break-even claim until the
frozen campaign is complete. Constant-time four-bit fusion is a kernel fact, not
an end-to-end result.

## Compiler outcomes and arms

All arms receive the same immutable expression object, variable order, fixed
mapping, and requested output.

| Arm or outcome | Contract |
|---|---|
| Pure structural pair | `strategy="pure_structural"`; signed primitive, token negation, and same-frame fusion only; local retabulations must equal zero |
| Hybrid pair | `strategy="hybrid"`; admits local exact retabulation and may consume such a child in later negation or fusion; root outcome must be `hybrid_pair` |
| Whole-root retabulation | `strategy="retabulate"`, or an otherwise unwrapped exact root retabulation; four full source evaluations; root outcome `full_retabulation` |
| Ordinary fallback | No pair returned; ordinary CM IR evaluates the unchanged expression; root outcome `ordinary_fallback` |
| Direct packed AST | One identity-memoized source-DAG traversal over assignment masks using `eval_expr_bitset`; no CM frame rules or scalar four-pass evaluation |
| Prepared packed program | Structural lowering once, then the same bound flat/word program for declared reuse |
| ROBDD | Repository backend with frozen variable order; build and query costs separate |
| ABC-compatible AIG | Mandatory for the frozen translatable natural-circuit subset; import, construction, optimization, and query/simulation reported separately |
| Common token query | Every four-bit producer calls `cm_token_value`; indexing and call overhead are identical and credited to none |

The legacy spelling `strategy="structural"` is a compatibility alias for
`hybrid` and is forbidden in the confirmatory harness.

For two live variables `(R,C)`, packed assignment positions from least to most
significant are `(00,01,10,11)`, so the masks are `R=1100_2` and `C=1010_2`.
The resulting four-bit word, read most significant first, is the CM token order
`(11,10,01,00)`. Fixed false and true variables use all-zero and all-one masks.

## Workload strata

| Stratum | Construction | Expected pair outcome |
|---|---|---|
| A. Exact frame | Recursive formulas over one positive `(R,C)` pair | Pure structural |
| B. Signed/permuted frame | A with independently sampled input negations and operand swaps | Pure structural after alignment |
| C. Mixed child | One structural child and one two-variable child requiring exact local retabulation | Hybrid pair |
| D. Root retabulation | Two live variables but no admitted structural root | Full retabulation |
| E. Multiple pairs | Different row/column pairs in one expression | Ordinary fallback |
| F. Compound/out-of-domain | Opaque compound operands or unsupported pair layouts | Hybrid, full retabulation, or fallback according to total support; never relabeled pure |
| G. Natural formulas/circuits | Untouched externally sourced structures selected before pair compilation | Empirical prevalence and boundary |

Generated cells use:

- balanced AST occurrence counts `15, 63, 255, 1023, 4095`;
- skewed counts `15, 63, 255` only, with measured AST height at most `128`;
- AND, OR, XOR, implication, and equivalence at outer nodes;
- reuse counts `1, 10, 100, 1000`;
- compact token, scalar query, packed batch, and budget-permitted dense output;
- identity-shared DAG nodes, structurally equal but separately allocated
  subtrees, and no sharing; and
- separate correctness/secondary-timing cases with fixed substitutions.

Every case records AST occurrences `N`, unique object nodes `U`, height, live
support, fixed variables, sharing class, seed, and content hash. Balanced and
skewed cells are not silently pooled. A generated case outside the height limit
is never admitted to the corpus; a recursion failure inside the admitted corpus
is retained as an observation.

## Natural corpus and AIG gate

Before any pair compiler is run on a natural case, the freeze records:

- source repository or archive, immutable revision, license, and acquisition
  date;
- extraction, translation, inclusion, and exclusion rules;
- original identifier, circuit/formula size, support distribution, and output;
- identity sharing and equal-but-distinct subtree statistics;
- original bytes and translated-AST hashes; and
- semantic-duplicate grouping without deleting distinct source structures.

The ABC-compatible executable version, libraries, exact commands, supported
file types, timeout, and translatable subset must be frozen. If this environment
is unavailable, protocol v3 cannot produce a confirmatory circuit result; the
study must wait or adopt a disclosed successor protocol with a narrower claim.

## Preparation, query, cache, and output boundaries

- Cold one-shot direct-packed measurements start in a fresh process, clear the
  bitset-environment cache, and include environment-mask construction.
- Prepared packed measurements construct the environment exactly once; report
  construction, lowering/binding, and execution separately and in the declared
  compile-plus-K total.
- CM token production includes support discovery, alignment, fusion, and any
  admitted local retabulation.
- Whole-root retabulation includes support discovery and four complete scalar
  source-expression evaluations.
- The common token query begins only after a producer returns an equal four-bit
  word; it is never a CM-specific advantage.
- Every dense result includes conversion, allocation, broadcast/lift, copying,
  and output bytes. Token-only results are never reported as materialized CMs.
- Backend-native preparation is permitted only when it is exposed and timed.

## Instrumentation

Required per-case fields include:

- requested strategy and root outcome;
- AST occurrences, unique object nodes, and height;
- compiler calls and negation nodes scanned;
- primitive tokens, signed alignments, token negations, token fusions, local
  retabulations, pair attempts, and pair collapses;
- identity-sharing class and `N/U` ratio;
- environment-cache state before and after the arm;
- preparation, execution, query, conversion, and materialization times;
- representation bytes, explicit output bytes, and peak process memory; and
- disagreement, exception, timeout, budget rejection, and disposition.

The legacy `nodes_total` and `pairable_ratio` fields may be retained for old
readers but are not compared across strategies. A ratio computed from different
traversal contracts is not a scientific endpoint.

## Correctness gate

Before performance results are unblinded or summarized:

1. Every completed arm agrees with an independent truth-table oracle whenever
   exhaustive evaluation fits the output budget.
2. Larger cases agree on a frozen assignment sample and by an independent
   equivalence check where available.
3. Pure structural strata have zero local retabulations; mixed-child cases
   report `hybrid_pair`; whole-root cases report `full_retabulation`.
4. Structural, hybrid, retabulated, direct-packed, prepared-packed, ROBDD, and
   AIG outputs agree wherever the corresponding arm completes.
5. Fixed substitutions are checked through both CM and direct-packed APIs.
6. Inputs, layouts, and fixed mappings remain unchanged.
7. No failing or unsupported case is silently discarded.

An arm with a disagreement is quarantined from performance interpretation until
diagnosed. Raw records retain the case, seed, arm, error, and disposition.

## Sampling and process policy

- Use isolated processes on one frozen machine and power mode; record CPU,
  logical cores, RAM, OS, Python, NumPy, compiler/tool versions, and thread
  settings.
- Do not increase the language recursion limit during measurement. The corpus
  height cap is the declared policy.
- Perform correctness and one untimed warm-up before timing.
- Randomize arm order within case/repetition using a recorded schedule seed.
- Collect at least 30 valid repetitions per generated cell and at least 15 per
  natural case unless the 60-second arm/case timeout intervenes.
- Calibrate legitimate repeated inner loops to at least 100 ms.
- Measure peak memory in a fresh process without subtracting undeclared caches.
- Never run competing benchmark processes concurrently.
- Retain append-only per-repetition observations, not summaries alone.

The non-confirmatory pilot must demonstrate median absolute deviation divided by
median of at most 5% in the primary cell. If it cannot, revise measurement
controls and issue protocol v4; do not weaken the primary threshold after
seeing confirmatory data.

## Sole primary utility test

The one primary cell is:

- Stratum B signed/permuted frames;
- balanced formulas with `N=1023` and `U=N`;
- no fixed variables and no object-identity sharing;
- compact-token output and reuse count `1`;
- CM cases whose root outcome is `pure_structural`; and
- direct packed AST as the comparator.

Stratum B is generated from the pure structural grammar. Root outcome is a
validation condition, not a post-measurement filter: any non-pure outcome is a
correctness-gate failure and remains in the primary-cell record.

The ratio is competitor time divided by CM time. Primary success requires:

1. zero correctness disagreements;
2. median ratio at least `1.20`;
3. a 95% hierarchical bootstrap interval entirely above `1.00`; and
4. no more than a 10% median peak-memory increase for CM.

The 20% timing threshold is the minimum effect judged practically worthwhile
and is four times the target 5% repeatability bound. The 10% memory tolerance
allows ordinary allocator granularity but rejects a material space-for-time
trade. Report absolute time and bytes so these relative thresholds cannot hide
trivial differences.

All structural-versus-retabulation comparisons, prepared-reuse cells, other
sizes, output forms, sharing classes, fixed cases, ROBDD/AIG comparisons, and
natural cases are secondary. Correct their intervals or tests within each
endpoint family using Benjamini-Hochberg at `q=0.05`. No favorable secondary
cell can replace a failed primary cell.

## Freeze manifest

Before the first confirmatory measurement, create an immutable run directory
containing:

- this protocol and its SHA-256 hash;
- Git commit plus hashes of every dirty diff and untracked source used;
- content-addressed source snapshots for every arm;
- generated and natural corpus records, provenance, licenses, hashes, seeds,
  and splits;
- exact primary-cell selector and analysis script;
- machine-readable arm configuration, cache policy, output budget, timeout,
  repetition counts, and randomized schedule;
- hardware/software/environment capture and ABC/AIG configuration;
- exact test commands and complete outputs; and
- empty append-only result files whose schemas and checksums are registered
  before measurement.

A non-confirmatory harness pilot may occur before this freeze. After the pilot,
fix defects, issue new source hashes and a new run identifier, and do not inspect
confirmatory outcomes until all gates above are immutable.

## Interpretation

- **Applied empirical paper:** the sole primary cell passes, correctness and
  reproducibility gates pass, and secondary results map the boundary honestly.
- **Narrow technical paper:** formal/compiler correctness holds but the primary
  utility cell fails; foreground the typed transformation and report the
  negative or neutral systems boundary.
- **Stop performance claims:** any unresolved correctness disagreement or
  irreproducible timing invalidates the performance-centered submission.

Formula-valued LM valuation and logical pairing are formal contributions, not
performance endpoints. The implementation does not compile formula-valued LMs.
