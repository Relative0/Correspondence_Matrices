# Evaluation protocol v2: operand-aligned CM compilation

Protocol date: 2026-09-15  
Paper: **Operator-Level Boolean Computation with Correspondence Matrices**  
Prospective sole author: **Brian Theory**  
Status: **revised analysis plan; corpus and run-manifest freeze still required before confirmatory measurements**

Any material change to the questions, primary endpoints, workload strata,
baselines, thresholds, or exclusion rules creates a numbered successor protocol.
Exploratory measurements may guide implementation but cannot be presented as
confirmatory evidence under this version. Version 2 adds the direct packed-AST
and four-bit-LUT boundaries, distinguishes them from a prepared flat program,
and scopes the NPN/AIG comparison; no v1 measurements are carried forward.

## Research questions

1. **Correctness.** Does signed-operand alignment and recursive token fusion
   preserve Boolean semantics for every admitted input?
2. **Compiler mechanism.** On expressions built repeatedly over one canonical
   row/column operand pair, how much work is avoided by structural token fusion
   compared with four-assignment retabulation and ordinary CM compilation?
3. **User-visible cost.** After discovery, compilation, conversion, allocation,
   and output are counted, when—if ever—does the pair path reduce elapsed time or
   peak memory?
4. **Boundary.** How do benefits change with signed/swapped operands, expression
   size, reuse count, failed pair recognition, multiple operand pairs, compound
   operands, and explicit-output size?

The primary empirical claim is deliberately conditional: the method may help a
repeated-same-operands stratum and lose elsewhere. Constant-time four-bit fusion
is not treated as an end-to-end speed result.

## Implementations and ablations

All arms consume the same immutable expression AST and declared variable order.

| Arm | Purpose | Required implementation state |
|---|---|---|
| Structural pair token | Signed-literal alignment, token negation, and recursive lookup-table fusion through `compile_expr_to_cm_pair_token` | Implemented; freeze exact source hash |
| Retabulation-only pair | Disable structural assembly and derive the final token by four Boolean evaluations | Implemented as the explicit non-default `strategy="retabulate"` / `pair_strategy="retabulate"` ablation |
| Ordinary CM IR | Existing `compile_expr_to_cm` path with the same materialization policy and output budget | Implemented; freeze configuration and source hash |
| Direct packed AST | Evaluate the source DAG once over assignment bitmasks, memoized by node identity | Implemented as `eval_expr_bitset`; for `(R,C)`, masks are `1100₂` and `1010₂` and the four-bit result is the token truth word |
| Prepared packed program | Lower a shared DAG once, then execute its flat bit-vector program for repeated workloads | Existing flat/word evaluators must be wrapped behind the same workload and endpoint contract; lowering is preparation time |
| Four-bit LUT query | Query the same completed four-bit truth word with a shift and mask | Report only after the CM and direct-packed arms have separately paid their preparation cost; the query kernel is common, not a CM advantage |
| ROBDD | Repository ROBDD backend with declared variable order; report build and query costs separately | Include for workload sizes it supports; failures and timeouts remain observations |
| External AIG flow | Import translatable natural circuits, build/optimize the AIG, and report synthesis plus simulation/query boundaries | Required for the circuit subset when a frozen ABC-compatible environment is available; do not substitute hand-translated formulas |

The structural-versus-retabulation contrast is the mechanism test. The ordinary
IR, direct packed AST, prepared packed program, ROBDD, and circuit AIG arms test
whether the mechanism is useful beyond its own representation. NPN
canonicalization is recorded only if the external synthesis flow actually
invokes it: NPN is an input/output-phase and permutation classification method,
not an evaluator baseline. No arm may receive a hand-tuned expression
unavailable to the others. Backend-native preprocessing is allowed but timed
and reported.

For two variables, `build_bitset_env((R,C))` assigns bit positions from least
to most significant to `(00,01,10,11)`. Thus the printed masks are
`R=1100₂`, `C=1010₂`; bitwise evaluation returns a word whose most-significant-
first reading is `(11,10,01,00)`, exactly the CM token order. The direct packed
arm traverses each unique AST/DAG node once per evaluation and does not use CM
frame recognition, four separate scalar passes, or dense materialization.

## Workload strata

The confirmatory corpus contains independently generated and externally sourced
cases, assigned identifiers before timing. Each generated cell uses fixed seeds
recorded in the manifest and contains the same number of cases.

| Stratum | Construction | Expected compact-path behavior |
|---|---|---|
| A. Exact frame | Recursive formulas over the same positive `(R,C)` variables | Structural fusion without alignment |
| B. Signed/permuted frame | As A, with independently sampled input negations and operand swaps | Alignment followed by structural fusion |
| C. Two-variable fallback | Same two live variables, but structures outside the signed-primitive assembly rules | Four-assignment retabulation |
| D. Multiple pairs | Formulas containing different row/column pairs | No whole-expression pair token; ordinary fallback |
| E. Compound operands | Binary operators whose logical operands are compound formulas rather than signed variables | Outside the structural alignment claim; retabulate only when total live support remains one row and one column |
| F. Natural formulas | Untouched formulas/circuits selected without reference to pair-compiler outcomes | Measures prevalence, failures, and external validity rather than guaranteeing opportunities |

Generated strata A-E cross these factors:

- AST node count: `15, 63, 255, 1023, 4095` where generation succeeds;
- tree shape: balanced and skewed;
- outer connective: AND, OR, XOR, implication, and equivalence;
- reuse count of one prepared artifact: `1, 10, 100, 1000` evaluations;
- requested result: compact token, scalar evaluations, packed batch, and explicit
  dense CM where the output budget permits it.

Natural stratum F is frozen before running the pair compiler. Duplicate semantic
functions are retained only when they arise from distinct source structures and
are labeled as such. Cases used in the 2018 paper, later optimization, feature
selection, or protocol development are exploratory and cannot supply the sole
confirmatory evidence.

## Endpoints

### Primary endpoints

1. **Prepared repeated-evaluation time** for reuse counts `10, 100, 1000`,
   including compilation once and all requested evaluations.
2. **One-shot end-to-end time** for reuse count `1`, from an already parsed common
   AST through the requested result.
3. **Peak process memory above the pre-run baseline** for the same task.

Each primary result is reported by workload stratum and requested-result type;
they are not pooled into one universal ratio.

### Required timing boundaries

- structural support discovery, alignment, fusion, and completed-token return;
- retabulation support discovery plus all four scalar source-AST traversals;
- direct packed-AST environment construction and one memoized packed traversal;
- flat/word-program lowering, binding, and execution, with preparation separate;
- completed-token/LUT query, which is identical after either producer has
  returned the same four bits;
- ROBDD construction and query separately;
- AIG import/construction, rewriting or mapping, and simulation/query separately;
  and
- conversion, allocation, and materialization for every explicit array output.

Compile-plus-`K` query totals are derived from these observed components and
also measured end to end. A prepared-query win cannot erase a higher preparation
cost unless the declared reuse count amortizes it. No token producer receives
credit for the common LUT query itself.

### Mechanism and diagnostic endpoints

- token-only compilation time;
- support-discovery time if it can be isolated without changing semantics;
- explicit conversion/allocation/materialization time;
- counts of primitive tokens, signed alignments, token negations, token fusions,
  direct retabulations, visited nodes, attempts, collapses, and fallbacks;
- compiled representation size and explicit output bytes;
- correctness disagreements, exceptions, timeouts, and budget rejections; and
- empirical break-even reuse count, computed from measured preparation and
  per-evaluation costs rather than extrapolated from kernel timing alone.

`pairable_ratio` is diagnostic only. Kernel timings and operation counts are not
substitutes for either primary elapsed-time endpoint.

## Correctness gate

Before performance data are unblinded or summarized:

1. every completed arm must agree with an independent truth-table oracle on all
   cases for which exhaustive evaluation fits the output budget;
2. larger cases must agree on the frozen random assignment set and, where
   available, by an independent equivalence check;
3. all 16 tokens and all signed/permuted primitive frames must pass exhaustively;
4. input ASTs, `R`, `C`, and `fixed` must be unchanged after every arm; and
5. any disagreement quarantines the affected arm and stratum until diagnosed.

No failing case is silently discarded. The case identifier, seed, arm, exception
or disagreement, and disposition are retained in the raw results.

## Timing and memory procedure

- Run each measurement in an isolated process pinned to the same machine and
  software environment. Record CPU, logical-core count, RAM, OS, Python, NumPy,
  backend versions, power mode, and relevant thread-count settings.
- Complete correctness and one untimed warm-up before sampling. Warm and cold
  scenarios are labeled separately; neither substitutes for the other.
- Randomize arm order within case and repetition using a recorded schedule seed.
- Collect at least 30 valid repetitions per generated cell and at least 15 per
  natural case unless the preregistered timeout makes this infeasible. Report the
  actual count.
- Use a monotonic high-resolution clock. Calibrate inner loops so a timed sample
  is at least 100 ms when repeated evaluation is semantically legitimate.
- Measure peak memory in a fresh process. Do not subtract backend caches created
  outside the declared preparation boundary.
- Set a 60-second per-arm/case timeout and enforce the existing explicit-output
  budget. Timeouts and budget rejections are reported, not converted to timings.
- Do not run competing benchmark processes concurrently. Retain raw per-repeat
  observations; summaries alone are insufficient.

## Analysis rules

For each paired comparison, report the median time ratio, median absolute time,
median memory difference, a distribution plot, and a 95% hierarchical bootstrap
interval resampling cases and repetitions. Ratios use competitor time divided by
CM time, so values above one favor the CM arm. Also report unaggregated case-level
results to reveal heavy tails and failures.

The primary practical-success rule is:

- zero correctness disagreements;
- at least a 20% median improvement (`ratio >= 1.20`) with the 95% interval
  entirely above `1.00` for structural pair compilation versus retabulation in
  strata A-B; and
- at least a 20% median one-shot or prepared end-to-end improvement, with the
  95% interval entirely above `1.00`, against at least one sharing-aware external
  baseline in a predeclared stratum/result/reuse cell, without more than a 10%
  median peak-memory increase in that cell.

This rule establishes a publishable useful region, not general superiority.
Results below it remain reportable and narrow the claim. A kernel-only win, a win
selected after seeing all cells, or a result obtained only by omitting conversion
or output cost does not clear the utility gate. All other comparisons are
secondary and corrected for multiplicity by the Benjamini-Hochberg procedure at
`q=0.05` within each endpoint family.

## Freeze manifest required before the first confirmatory run

The run directory must contain:

- protocol version and SHA-256 hash;
- Git commit plus hashes of every dirty tracked diff and untracked source used;
- source snapshot or content-addressed archive for every implementation arm;
- corpus records, source licenses/provenance, generator version, seeds, and split;
- machine-readable arm configuration, output budget, timeout, repetitions, and
  randomized execution schedule;
- environment and hardware capture;
- the exact test command and full pass/fail output; and
- an append-only raw-result file with checksums.

The manifest is written before measurement and copied into the results directory.
Changing implementation, corpus, exclusions, thresholds, or analysis after that
point requires a new run identifier and disclosure; a substantive protocol
change requires a numbered successor.

## Interpretation decision

- **Go, empirical methods paper:** the practical-success rule passes in a clearly
  described repeated-same-operands region and all correctness/reproducibility
  gates pass.
- **Go, narrower technical paper:** structural compilation is correct and its
  mechanism advantage passes, but external end-to-end utility is small; foreground
  the verified operator transformation and state the negative systems boundary.
- **No-go for a performance-centered paper:** correctness fails, or neither the
  mechanism nor an external end-to-end comparison clears its threshold. Preserve
  the formal result and evidence, but do not market computational speed.

LM valuation, logical relational pairing, and representation-conversion theorems
are formal contributions and are not performance endpoints in this protocol.
