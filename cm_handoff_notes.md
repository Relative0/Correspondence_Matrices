# CM / Bitset / Parallel / Hybrid Handoff Notes

## Purpose of this document

This file is a comprehensive handoff for a new GPT/Codex/Cursor thread and also a stable project notebook for the repository. It summarizes:

- what was benchmarked
- what was implemented
- what was tested
- what results were obtained
- what conclusions seem justified
- what open issues remain
- what the highest-value next prompts are

---

## 1. Core project context

The project benchmarks **Correspondence Matrix (CM)** computation for propositional logic against other Boolean-computation methods.

The benchmarked backends discussed across the work include:

- **CM**
- **CM lazy**
- **CM parallel**
- **CM hybrid**
- **bitset**
- **Numba evaluator**
- **BDD / ROBDD / dd**
- **SymPy**
- **Espresso**
- **BDD->SOP baseline**

The benchmark task is fundamentally:

> Generate Boolean expressions, compute them using different backends, and compare timing and correctness against a reference truth-table evaluator.

The key reference evaluator throughout the work is:

- `eval_expr_tt(...)`

Correctness checks are intended to be performed **outside timed windows** for fairness.

---

## 2. Early benchmark interpretation

Initial benchmark interpretation from the HTML/CSV results:

- CM was **not universally fastest**
- BDD could be fastest at very small sizes
- CM often became relatively stronger as variable count grew
- BDD showed severe blow-up on random expressions
- SymPy often degraded with depth
- CM appeared comparatively stable

Important nuance reached early:

> The right claim was not “CM is fastest overall,” but rather that CM is unusually stable across increasing variable count and depth, especially on random/unstructured expressions.

This led to useful plots:
- line plot by variable count
- log-scale line plot
- grouped bar/log plot by depth
- heatmaps of log-times over `(n_vars, depth)`
- ratio plots such as `BDD / CM`

Those visualizations suggested:
- BDD is highly sensitive to variable count
- SymPy is highly sensitive to expression depth
- CM is relatively smooth/stable
- CM can “gain ground” relative to some methods as size/complexity grows

---

## 3. Important conceptual distinction that emerged

A major conceptual distinction was clarified:

### Bitset
- uses **hardware-efficient packed bit operations**
- best thought of as **data-level / hardware-level parallelism**
- evaluates many truth assignments at once with bitwise operations

### CM
- is fundamentally a **structured / algebraic / operator-based representation**
- supports decomposition, tensor composition, and reuse
- can exploit **structure-level parallelism**, not just hardware width

Key conclusion:

> Optimizing CM does **not** turn it into bitset, as long as CM retains its operator semantics, row/column partitioning, compositional DAG structure, and algebraic interpretation.

---

## 4. Bitset + Numba backends

A Codex implementation added two new backends.

### Bitset backend
Added in `bitset_backend.py`:

- `build_bitset_env(vars)`
- `eval_expr_bitset(expr, env)`
- `bitset_to_bool_array(bits, n_vars)`

Key design details:
- Python integer bitmasks were used
- full-mask semantics were required for complement-producing ops
- truth-table ordering had to match `eval_expr_tt(...)`
- pure bitwise execution was used (no loops over assignments)

### Numba backend
Added in `numba_backend.py`:

- flattened postorder / stack-program style evaluator
- `@njit` execution
- primitive arrays only
- separate compile time and execution time

### Benchmark integration
`cm_bench.py` was updated to add:
- `--no-bitset`
- `--no-numba`
- per-trial timing/correctness fields
- summary timing/correctness fields

### Initial expectation
- bitset would likely be a very strong baseline
- numba would be a useful control baseline
- bitset was expected to be the hardest backend for CM to beat

---

## 5. Bitset validation and comparison mode

A later plan specifically validated bitset correctness and integrated CM-vs-bitset comparison more carefully.

### Bitset improvements
- explicit mask semantics:
  - `full_mask = (1 << (1 << n_vars)) - 1`
- environment caching keyed by variable set
- cache stats helpers
- ordering checks against `eval_expr_tt(...)`

### CM parallel integration for comparison
Added:
- `compile_expr_to_cm_parallel(...)`
- process-based parallel execution
- benchmark fields and ratio columns:
  - `ratio_cm_parallel_over_cm`
  - `ratio_cm_parallel_over_bitset`

### Tests added
- bitset ordering equivalence
- mask clipping checks
- cache behavior checks
- CM parallel correctness
- determinism tests
- benchmark smoke tests

### Result
This phase showed:
- bitset was correct and fast
- CM parallel was modestly helpful at best
- bitset remained much faster than CM on raw execution

Important realization from this phase:

> Parallelizing CM execution alone was not enough. The main issue was not lack of parallelism, but too much total dense work.

---

## 6. CM optimization audit and major CM optimization pass

A major audit/optimization phase confirmed and improved several CM capabilities.

### Capabilities audited / improved
- lazy broadcasting / lazy materialization
- eager builder
- permutation / axis-reordering caches
- row/column normalization caches
- subtree memoization
- common subexpression elimination (CSE)
- fixed/modifier pruning
- deterministic combine ordering
- threshold-based parallel activation
- chunked tensor/block combine
- worker-pool reuse
- shared-memory use
- benchmark caching of reusable structures

### Optimizations added or strengthened
- eager/lazy subtree memoization
- compile-once reuse
- deterministic constant pruning
- cached lazy axis alignment plans
- cached normalization metadata
- worker-pool reuse
- optional shared-memory chunk combine
- diagnostics / debug stats
- explicit timing-policy fields

### Important fairness choices
- no global cross-expression cache in benchmark loops
- correctness kept outside timed windows
- explicit timing policy fields like:
  - `cm_tt_extract_time_s`
  - `cm_parallel_tt_extract_time_s`
  - `bitset_extract_time_s`

### Validation
- unit tests passed
- diagnostics were added
- benchmark integration remained intact

---

## 7. Parallel CM: what was learned

A process-based CM parallel layer was implemented and benchmarked.

### What worked
- process pool
- frontier splitting
- XOR flattening
- chunked combine
- deterministic ordering
- threshold-based activation

### What results showed
At one point:
- `cm_parallel / cm` was only around **0.95** at `n=16`
- bitset still beat CM by large factors

This led to an important conclusion:

> The problem was not just lack of parallelism; the bottleneck was total dense work and matrix/tensor materialization.

Later, an additional regression investigation found:

- CM baseline compare mode was **not** the source of regression
- the real issue was in `cm_parallel.py`
- the pool could start even when no meaningful parallel combine happened
- current chunking was along the **hypercube leading axis**, which was often tiny
- this caused overhead without real benefit

### Fix applied
- process pool creation made **lazy**
- new CLI threshold exposed:
  - `--cm-parallel-min-chunk-cells`

### Post-fix finding
- false overhead was removed
- forced parallelism still exploded runtime
- deeper issue remains:
  - current parallel work is still chunked at the wrong granularity

### Current parallel conclusion
> CM_parallel is not fundamentally broken, but the current chunking strategy is misaligned with the real expensive data layout.

### Suggested next direction
Parallelize:
- flattened buffers
- large contiguous matrix slices
- post-lift matrix blocks

rather than tiny hypercube-axis slices.

---

## 8. Balanced layout vs legacy square layout

A very important representational optimization was identified.

### Discovery
The benchmark’s canonical layout had been padding to the next power-of-two square shape.

Example:
- for `n=12`, padded square layout used a **16-variable ambient space**
- producing a `256 x 256` matrix instead of `64 x 64`

### Balanced layout idea
Use:
- row vars `R`
- column vars `C`
- matrix shape `2^|R| x 2^|C|`

for any split of variables into `R` and `C`.

### Key conceptual point
This does **not** stop the object from being a CM.

It simply chooses a better embedding / coordinate split.

### Example
For `n = 12`, all of these represent the same Boolean function:

- `6 / 6` split -> `64 x 64`
- `4 / 8` split -> `16 x 256`
- `0 / 12` split -> `1 x 4096`

Balanced split minimizes total matrix size.

### Benchmark finding
Balanced non-padded layouts produced speedups roughly around:
- ~1.2x to ~2.6x in representative cases
- about ~1.8x at `n=12`
- about ~1.3x at `n=16` in later summary reports

### Implementation
- `canonical_layout(..., mode="balanced")`
- old padded behavior retained as `legacy_square`
- benchmark flag added:
  - `--cm-layout`

### Important conceptual conclusion
> Balanced layout is still a true CM representation. It removes unnecessary ambient padding; it does not convert CM into bitset.

---

## 9. Symbolic CM DAG / IR redesign

This was one of the most important upgrades.

### Major change
A redesign introduced a shared symbolic CM DAG / IR:

- `cm_ir.py`

### What changed conceptually
Before:
- CM builders were still close to dense internal evaluation

After:
- expressions compile to canonicalized IR nodes
- repeated structure is interned by canonical subtree hash
- algebraic identities are folded early
- dense array work is delayed until `materialize_cm(...)`

Both:
- `cm_build.py`
- `cm_build_lazy.py`

were updated to use the same IR.

`cm_parallel.py` was also updated to use this IR.

### Diagnostics introduced
Per-trial diagnostics such as:
- `cm_subtree_cache_hits`
- `cm_canonical_rewrites`
- `cm_pruned_branches`
- `cm_materializations`
- `cm_live_vars_max`

### Important results
Balanced optimized runs showed:
- median `cm_materializations` around **7–11**
- `cm_live_vars_max` around **3–5**
  - even for `n = 12..16`

This was a major breakthrough.

### Interpretation
> CM was now acting as a **problem reducer / optimizer**, not just a dense evaluator.

Dense work was no longer happening for the full variable set.

---

## 10. What this taught us about CM

A very important conceptual conclusion emerged:

> CM’s biggest value is not raw evaluation speed by itself.

Instead, CM became:

- a **structured representation**
- a **compiler / optimizer**
- a **problem-reduction engine**

Bitset, by contrast, remained:
- a very strong flat execution backend

This led to a new architecture view:

- **CM = optimizer / IR / structured representation**
- **bitset = execution kernel**

---

## 11. Hybrid CM materialization with bitset fast path

This was the next major step after the symbolic DAG.

### Plan
Keep the symbolic CM DAG unchanged and improve only the execution layer.

### Implementation summary
In `cm_ir.py`:
- `materialize_ir(...)` accepts:
  - `materialize_mode="hybrid" | "numpy"`
  - `hybrid_threshold=7`

For each node:
- compute `k = len(live_vars)` after fixed-variable elimination
- if `k <= threshold`, evaluate that node through bitset
- otherwise use NumPy materialization

Bitset helpers added in `bitset_backend.py`:
- `bitset_to_bool_hypercube(...)`
- `eval_cm_node_bitset(...)`

Public CM entry points propagate execution controls through:
- `cm_build.py`
- `cm_build_lazy.py`
- `cm_parallel.py`

### Benchmark integration
Added:
- `--cm-hybrid-threshold`
- `--cm-compare-hybrid`

Normal CM now uses hybrid internally by default.

Compare mode runs:
- CM = legacy NumPy-only baseline
- CM_hybrid = hybrid execution
- bitset

### Tests
Expanded test coverage and passed:
- compileall passed
- unittest passed
- 20 tests all passing in one reported phase

---

## 12. Hybrid benchmark results

### Reported compare run
Settings included:
- `--sizes 4,8,12,16`
- `--trials 3`
- `--max-depth 4`
- `--cm-layout balanced`
- `--cm-compare-hybrid`
- `--cm-hybrid-threshold 7`
- `--cm-parallel`

### Reported improvements
CM_hybrid vs NumPy-only CM:
- `n=4`: 0.93x
- `n=8`: 0.73x
- `n=12`: 0.68x
- `n=16`: 0.72x

Interpretation:
- hybrid materially reduced CM work

### Reported comparison vs bitset
CM_hybrid vs bitset:
- `n=4`: ~31.3x slower
- `n=8`: ~20.4x slower
- `n=12`: ~14.8x slower
- `n=16`: ~8.2x slower

### Diagnostics
A particularly important result:
- CM_hybrid used median **1 bitset materialization**
- CM_hybrid used median **0 NumPy materializations**

Interpretation:
> The hybrid threshold often collapsed many whole reduced CM subproblems directly into a final bitset evaluation.

### Key conclusion from this phase
Correctness was preserved, and hybrid reduced CM work substantially, but:
- it still did not beat bitset in the tested regime
- the remaining gap was dominated by:
  - conversion overhead
  - CM boundary overhead
  - DAG/canonicalization/materialization overhead

---

## 13. Key realization after hybrid

This was one of the most important conceptual insights of the whole work:

> Once CM has reduced a problem to a very small live-variable subproblem, bitset is the optimal execution kernel.

This led to the architectural understanding that:

- CM is not primarily the best final evaluator
- CM is a **structure optimizer**
- bitset is a **small-subproblem executor**

This is an important positive result, not a negative one.

---

## 14. Practical meaning of CM-hybrid

A key question was asked:

> If CM_hybrid is only around bitset in speed, is there still benefit to using it?

The honest answer established was:

### If the only task is:
- one-shot flat evaluation of a Boolean function

then:
- bitset alone is likely the simplest and best choice

### But CM_hybrid remains valuable if you care about:
- structure
- decomposition
- reuse
- multiple related queries
- partial evaluation / conditioning
- sub-function extraction
- incremental updates
- compositional workflows
- interpretability of the operator representation

So the right framing became:

> CM_hybrid is valuable not because it trivially beats bitset at flat evaluation, but because it preserves structure while achieving much more competitive execution speed.

---

## 15. Recommended benchmark / CLI choices that were made

Throughout the work, the following design choices were recommended:

### Code surface
- **Root Only**

### Parallel execution model
- **ProcessPool**, not ThreadPool

### CM parallelization support
- **Both Lazy + Eager**

### CM layout mode
- **Balanced Default**
- keep legacy square available for compatibility / older results

### Hybrid appearance in benchmarks
- **Separate Backend**
- do not hide it as an invisible default-only benchmark result

### Hybrid threshold
- start with **7 live vars**
- keep tunable

### Benchmark comparison if hybrid is internal default
- **Add Compare Flag**
- so NumPy-only CM and hybrid CM can still be compared explicitly

These choices were made largely to preserve:
- scientific transparency
- apples-to-apples comparison
- paper-quality reporting

---

## 16. Current state of the project

As of this handoff, the project appears to have:

### Strongly implemented / validated
- bitset backend
- numba backend
- CM parallel layer (though not yet ideal)
- balanced layout support
- symbolic CM IR / DAG
- subtree memoization / CSE
- pruning
- caching / diagnostics
- hybrid materialization with bitset fast path
- benchmark compare modes and diagnostics
- passing tests across several implementation phases

### What seems stable
- correctness
- hybrid baseline behavior
- balanced-vs-legacy layout behavior
- bitset correctness and ordering

### What still seems imperfect
- CM_parallel chunking granularity
- overhead in CM_hybrid relative to pure bitset
- likely opportunity for more selective / partial hybridization
- benchmark threshold tuning for hybrid and parallel paths

---

## 17. Most important empirical results to remember

### A. Balanced layout matters
- reduced unnecessary work materially
- often around ~1.3x to ~1.8x improvement in cited examples

### B. Symbolic IR mattered a lot
- reduced live vars to around **3–5**
- limited materializations to around **7–11**
- made CM behave like a structure optimizer

### C. Hybrid materially improved CM execution
- around **0.68x–0.93x** of NumPy-only baseline in cited examples
- often collapsed to bitset execution on reduced subproblems

### D. Bitset still won in the tested flat benchmark
- but gap narrowed as problem size increased
- and hybrid showed the remaining gap is mostly overhead, not evaluation-core cost

### E. CM_parallel remains the least convincing layer so far
- current chunking is likely wrong
- pool startup overhead was one bug that has been fixed
- deeper granularity redesign still remains

---

## 18. Highest-value open technical problems

### 1. Fix CM_parallel granularity
Current issue:
- chunking hypercube axis 0 is often meaningless

Likely better direction:
- chunk flattened buffers
- chunk post-lift matrix slices
- chunk large contiguous blocks
- create process pool only when real parallel work is confirmed

### 2. Threshold sweep for hybrid
Recommended:
- sweep `--cm-hybrid-threshold` over perhaps `5..9`
- determine best crossover empirically

### 3. Mixed / partial hybrid policy
Current hybrid often collapses entire reduced subtrees into bitset.

Potential next step:
- preserve more CM structure during execution
- bitset-evaluate selected children or subnodes
- avoid full collapse where a more compositional mixed policy helps

### 4. Reduce conversion overhead around the CM/bitset boundary
This appears to be one of the main remaining sources of slowness relative to pure bitset.

### 5. Better cost model
Eventually replace simple thresholding with:
- cost-based materialization decisions
- backend selection based on live vars, shape, expected conversions, and reuse

---

## 19. Best prompts for future Codex/Cursor work

### A. Parallel granularity redesign
Use the prompt focused on:
- flattened buffers
- post-lift matrix blocks
- large contiguous work units
- avoiding tiny hypercube-axis chunking
- lazy pool creation
- data-layout-aligned parallelism

### B. Partial / mixed hybrid execution
Use a prompt that asks Codex to:
- preserve CM structure while selectively bitset-evaluating small children
- avoid collapsing entire large reduced subtrees into one bitset call
- compare:
  - NumPy-only CM
  - full-collapse hybrid
  - partial hybrid
  - bitset

### C. Full CM optimization audit
Use a prompt that asks for:
- PRESENT / PARTIAL / MISSING audit table
- memoization, pruning, normalization caches
- diagnostics
- benchmark fairness policy
- implementation of missing high-value optimizations

---

## 20. Best high-level interpretation to carry into the next thread

A good summary statement for a new GPT/Codex thread is:

> We began with CM as a benchmarked Boolean backend and found it stable but not universally fastest. We then added bitset and numba baselines, validated correctness, and discovered bitset is a very strong flat execution baseline. We optimized CM through balancing layout, symbolic IR/DAG compilation, memoization, pruning, and hybrid bitset materialization. This transformed CM from a dense evaluator into a structured optimizer / compiler that often reduces problems to small live-variable subproblems, then uses bitset to execute them. Hybrid materially improved CM, but pure bitset still wins on raw flat evaluation in the tested regime. The main remaining opportunities are better CM_parallel granularity, threshold tuning, and potentially partial hybridization to preserve more structure during execution.

---

## 21. Notes for a new GPT / agent thread

If starting a new GPT thread, the new agent should be told:

1. The repo already contains:
   - bitset backend
   - numba backend
   - symbolic CM IR
   - balanced layout mode
   - hybrid CM materialization
   - CM parallel layer
   - diagnostics and tests

2. Correctness has repeatedly been verified against:
   - `eval_expr_tt(...)`

3. The main known remaining issue is:
   - CM_parallel chunking the wrong granularity
   - not hybrid correctness
   - not baseline compare mode selection

4. The central conceptual result is:
   - CM is currently most promising as a **structure optimizer / IR**
   - bitset is the strongest flat execution kernel

5. Future work should focus on:
   - data-layout-aligned parallelism
   - mixed hybrid strategies
   - conversion-overhead reduction
   - threshold tuning

---

## 22. Honest bottom line

The work so far strongly suggests:

- **CM is not just “another evaluator.”**
- Its main strength is in:
  - structure
  - decomposition
  - problem reduction
  - preserving semantic/operator information
- **bitset remains the execution champion** for small dense subproblems
- The most compelling architecture so far is:

> **CM for structure + bitset for execution**

That is already a meaningful result.

---

## 23. Suggested next-step checklist

- [ ] run hybrid-threshold sweep `5..9`
- [ ] redesign CM_parallel chunking around flattened or post-lift buffers
- [ ] benchmark partial hybrid vs full-collapse hybrid
- [ ] reduce CM/bitset conversion overhead
- [ ] confirm latest merged code still preserves all tests and compare modes
- [ ] generate final paper-grade plots for:
  - CM
  - CM_hybrid
  - bitset
  - maybe CM_parallel once fixed

---

End of handoff notes.
