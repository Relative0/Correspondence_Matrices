# CM Computation — Next Optimization and Implementation Program

**Purpose:** Codex-ready implementation and research brief for:

`C:\Users\brian\Documents\CM_Computation\`

**Primary source dossier:** `docs\CM_COMPUTATION_DEEP_TECHNICAL_DOSSIER.md`

This document translates the latest architectural/performance analysis into an implementation program. All project-specific current-state claims should be checked against the dossier and live repository before changing production code.

---

# 1. Executive conclusion

The project is best understood as an **exact Boolean-computation portfolio** with:

- a shared source DAG;
- several representations and evaluators;
- repeated-restriction workloads;
- exact decomposition and certification;
- lifecycle-sensitive backend crossovers;
- and prospective routing between exact methods.

The most important immediate recommendation is:

> **Do not run the originally conceived C37 unchanged. First repair and remeasure the restricted direct evaluator.**

The proposed `U/N` router currently detects, at least partly, an implementation asymmetry:

- complete-truth direct evaluation is now DAG-memoized;
- compiled projection benefits from that memoized complete evaluation;
- C36 `_eval_ast_restricted` still recursively follows occurrences independently for every query.

Therefore the current routing boundary may partly route around a correctable implementation defect rather than identify a fundamental backend crossover.

This does **not** mean routing should be abandoned. It means routing should be studied only after the primitive exact backends are brought to comparable implementation quality.

---

# 2. Current architecture

```text
serialized Boolean DAG v2
        │
        ├── direct complete-truth evaluation
        │       └── now identity-memoized
        │
        ├── direct restricted evaluation
        │       └── still occurrence-recursive, repeated per query
        │
        ├── structural-CSE FlatProgram
        │       ├── Python big-int execution
        │       └── NumPy uint64 execution
        │
        ├── CM IR
        │       ├── interning and Boolean rewrites
        │       ├── lowering to FlatProgram
        │       └── dense / packed materialization
        │
        ├── packed source ANF
        │       └── exact GF(2) algebra with bounded product cache
        │
        ├── compiled full-truth projection
        │       └── full truth + per-query gather indexes
        │
        └── exact decomposition
                ├── XOR components
                ├── GF(2) rank
                ├── cofactor blocks
                └── Kronecker form
```

CM IR should not be treated as either the mathematical Correspondence Matrix itself or the presumed universal fastest evaluator. It is an interned/canonicalizing Boolean compiler DAG.

The current performance frontier is lifecycle dependent:

- one-shot, support 3–10: direct packed AST;
- repeated small-width restrictions: flattened CSE;
- wide q1–q16 restrictions: flattened CSE;
- wide q64 fixed backend: compiled projection;
- bounded exact decomposition: C16 screen-then-materialize;
- favorable sparse source algebra: packed ANF.

This favors a **small exact portfolio** driven by measurable structure/lifecycle rather than one universal representation.

---

# 3. FIRST PRIORITY — repair restricted direct evaluation

## 3.1 Why this comes before formal C37

Current C36 memoized-rerun totals are approximately:

| Q | Direct restriction | CSE | CM IR | Projection |
|---:|---:|---:|---:|---:|
| 1 | 15.388 ms | **10.373 ms** | 24.237 ms | 83.446 ms |
| 4 | 49.368 ms | **16.552 ms** | 30.839 ms | 85.577 ms |
| 16 | 191.371 ms | **38.808 ms** | 54.445 ms | 92.861 ms |
| 64 | 750.243 ms | 122.812 ms | 142.082 ms | **119.956 ms** |

Yet direct restriction is reportedly the per-case winner for 14 of 18 C36 development cases. A small number of high-sharing multiply cases catastrophically damage the aggregate because the current direct restriction helper unfolds shared DAG structure repeatedly.

That means fixing the helper could alter:

- the best fixed backend;
- oracle headroom;
- the `U/N` boundary;
- the need for routing;
- and the correct formal C37 design.

## 3.2 Implement three exact restricted-evaluation versions

### R0 — Current occurrence-recursive restriction

Preserve unchanged as historical/control implementation.

### R1 — Per-query identity-memoized restriction

Within one fixed query assignment:

```python
memo: dict[int, int] = {}

def eval_restricted(node):
    key = id(node)
    if key in memo:
        return memo[key]

    result = evaluate_node_under_current_fixed_assignment(node)
    memo[key] = result
    return result
```

The memo should be scoped to one query unless restriction state becomes part of the key.

### R2 — Topological restricted evaluator with liveness

Compile serialized DAG v2 into a slot arena such as:

```text
opcode[]
left_child[]
right_child[]
variable_id[]
remaining_use_count[]
```

Evaluate in topological order and release packed results after final use.

This can remove:

- Python recursive calls;
- repeated lookup per recursive edge;
- retention of every node bigint until return;
- repeated structural hashing.

The conceptual sharing improvement is from:

`O(U B)` to `O(N B)`

where:

- `U` = unfolded occurrence visits;
- `N` = unique reachable DAG nodes;
- `B` = packed-bit operation cost.

## 3.3 Required measurements

Measure separately:

- `T_decode`
- `T_restriction_setup`
- `T_evaluation`
- `T_delivery`
- `T_total`

Also record:

- unique nodes visited;
- child-edge visits;
- primitive gate evaluations;
- maximum live packed values;
- peak RSS;
- Python allocations where practical;
- q1, q4, q16, q64;
- high- and low-`U/N` groups separately.

## 3.4 Decision rule

If direct becomes competitive on the multiply cases, discard the old `U/N > 10` selector as a production candidate and rebuild the backend landscape.

If projection still wins high-`U/N` cases, retain `U/N` as a structural feature because it will then predict a genuine crossover between optimized exact algorithms.

If R2 materially beats R1 with acceptable memory, use R2 as the new direct backend.

---

# 4. SECOND MAJOR DIRECTION — multi-query care-set evaluation

The current system effectively chooses between:

1. independent restriction per query;
2. full projection over every one of the `2^k` complete assignments.

There is a third exact option:

> **Evaluate the union of complete assignments actually required by the whole query set once.**

For query `q`, let `A_q` be the complete assignments consistent with that query and:

`R_q = |A_q| = 2^(k-f_q)`

where `f_q` is the number of fixed variables.

Define:

`L = sum_q |A_q|`

and:

`C = | union_q A_q |`

and:

`S = 2^k`.

Then:

`C <= min(L,S)`.

---

# 5. Three exact batching modes

## 5.1 Mode A — concatenated query lanes

Construct one packed lane vector containing all residual assignment lanes for q1, q2, ..., qQ.

For each source variable, build its bit pattern over these lanes and evaluate the DAG once.

Approximate cost:

`T_concat ≈ T_environment + I * B(L)`

where `I` is compiled instruction count.

Advantages:

- all queries share one DAG traversal;
- per-query output segments are already contiguous;
- little/no post-evaluation gather.

Disadvantage:

- the same complete assignment can appear in more than one query segment.

## 5.2 Mode B — union care-set evaluation

Deduplicate all complete assignments requested by the trace.

Approximate cost:

`T_care ≈ T_union/map + I * B(C) + T_gather`

Advantages:

- never evaluates more assignment lanes than full projection;
- shares assignment overlap across restrictions;
- can be much smaller than full truth.

Disadvantages:

- query-to-union mapping is needed;
- variable patterns become arbitrary rather than regular full-truth patterns.

## 5.3 Mode C — existing full projection

Approximate cost:

`T_full ≈ T_truth(S) + T_index + T_gather`

This remains attractive when union coverage `C/S` is high or full-truth extraction is highly optimized.

---

# 6. Why arbitrary packed lanes are exact

Packed Boolean evaluation does not require its lanes to enumerate a complete Cartesian truth table.

Each bit lane may represent an arbitrary assignment:

```text
lane:       0 1 2 3 4 5
x0 value:   0 1 1 0 0 1
x1 value:   1 0 1 1 0 0
```

Bitwise Boolean operators remain exact lane-by-lane.

Codex should determine whether the current evaluator already supports arbitrary packed variable environments or whether a small environment-builder generalization is needed.

---

# 7. Stronger variant — trace-specialized restriction compilation

Instead of batching only assignment lanes:

1. Symbolically restrict the source DAG for every query.
2. Cache restriction results by:
   `(node ID, fixed variables relevant to node, their values)`.
3. Intern all resulting reduced subgraphs across the trace.
4. Compile the combined set as one multi-root FlatProgram.
5. Evaluate roots in groups with matching residual-variable order.

A node whose live variables do not intersect a changed fixed assignment can be reused unchanged.

This creates a trace-specific exact partial decision structure without paying for a fully general fresh BDD.

---

# 8. Multi-query experiment design

Compare:

1. memoized/topological direct per query;
2. structural CSE per query;
3. concatenated-lane evaluation;
4. union care-set evaluation;
5. trace-specialized multi-root restricted DAG;
6. full projection.

Record:

- `L`
- `C`
- `C/S`
- number of distinct fixed-variable masks;
- query-overlap ratio;
- distinct restriction signatures per node;
- residual widths;
- support `k`;
- unique nodes `N`;
- instruction count `I`.

Development continuation gate:

- zero semantic mismatch;
- at least ~1.10x improvement over the best repaired fixed backend;
- no unacceptable memory tail.

Prospective continuation gate:

- at least 1.05x on a frozen independent/transfer corpus;
- zero exactness failure.

---

# 9. DIRECT SERIALIZED-DAG-v2 TO EXECUTION ARENA

Serialized DAG v2 already preserves structural sharing. Several downstream paths reconstruct Python objects, traverse them, and rediscover CSE.

Investigate direct v2-to-arena compilation.

Example:

```text
opcodes:        uint8[]
child_a:        uint32[]
child_b:        uint32[]
variable_ids:   uint16[]
support_masks:  integer/packed-mask[]
last_use:       uint32[]
root_ids:       uint32[]
```

During the same pass compute:

- `N`: unique reachable nodes;
- `U`: unfolded occurrence visits;
- operation histogram;
- reference counts;
- last-use positions;
- live/support masks;
- instruction count;
- peak-live-slot estimate;
- routing features.

This could fuse/remove duplicated:

- router traversal;
- support discovery;
- structural CSE discovery;
- liveness analysis;
- FlatProgram preparation.

The arena should drive:

- Python bigint execution;
- word execution;
- arbitrary care-set environments;
- multi-root evaluation;
- restriction/cofactor evaluation.

Kill criterion:

- if decode+preparation does not improve by ~20%, and
- total q1/q4 does not improve by at least ~5%,

retain only if it materially simplifies another winning backend.

---

# 10. RE-TEST BIGINT VS NUMPY WORD EXECUTION

The automatic engine selector reportedly chooses word arrays conservatively around support `k >= 16`, while C36 used word execution across support 11–16.

Measure:

```text
CSE bigint
CSE words
CM IR bigint
CM IR words
```

at every C36 width and q1/q4/q16/q64.

Python bigints may outperform NumPy words at lower widths because the entire bit operation occurs in optimized C with low Python-visible dispatch, while NumPy can incur per-gate ufunc overhead.

Do not assume the crossover.

---

# 11. OPTIMIZE COMPILED PROJECTION INTERNALLY

Current projection reportedly performs approximately:

1. packed full truth in Python integer;
2. int-to-bytes/vector conversion;
3. NumPy `uint8` full-truth vector;
4. 64 `uint32` gather-index arrays;
5. gather;
6. pack;
7. convert to integer;
8. canonical delivery construction.

First stage-profile:

`T_projection = T_truth + T_int_to_bytes + T_vector + T_indices + T_gather + T_pack + T_int + T_delivery`

## 11.1 Retain packed bytes internally

If delivery ultimately needs canonical bytes, digest, count, SAT, and witness, avoid round-tripping through Python int when not required.

Derive from packed bytes:

- SHA-256;
- SAT;
- popcount/model count;
- least witness.

## 11.2 Minimum-width indexes

For `k <= 16`, indexes fit in `uint16`.

Test:

- `uint8` where valid;
- `uint16` through 16-bit domains;
- `uint32` only above that.

Measure actual NumPy behavior.

## 11.3 Replace 64 independent index arrays

Evaluate:

- one contiguous index buffer plus offsets;
- a padded 2-D matrix;
- fixed-variable mask/value descriptors;
- stride/block extraction descriptors.

## 11.4 Variable-order-aware extraction

Explore an internal truth order that makes frequent restrictions slices/strides/blocks, then permute outputs back to canonical residual-variable order.

## 11.5 Native broadword extraction

Only if profiling says gather/pack is material.

A C/Rust/Cython kernel could combine:

- packed extraction;
- canonical output bytes;
- popcount;
- SAT;
- least witness.

---

# 12. ROUTING AFTER BACKEND REPAIR

After the primitive backends are frozen, route by predicted runtime/cost.

Candidate features:

- `k`
- `N`
- `U`
- `I`
- `Q`
- `L`
- `C`
- operator counts;
- residual support distribution;
- fixed-variable frequency;
- query overlap;
- distinct restriction masks;
- peak-live estimate;
- cheap ANF-density estimate if available.

Possible cost forms:

`T_direct_hat = a0 + a1 * sum_q N_q * B(R_q)`

`T_CSE_hat = b0 + b1*I + b2*sum_q I_q*B(R_q)`

`T_care_hat = c0 + c1*I*B(C) + c2*L`

`T_projection_hat = d0 + d1*N*B(2^k) + d2*sum_q R_q`

Safe routing rule:

`T_default_hat - T_candidate_hat > T_selector + delta`

Otherwise use the robust default.

Priority:

1. analytical cost model;
2. shallow tree/boosted regression;
3. neural router only if simpler methods leave substantial oracle headroom.

---

# 13. ONLINE BREAK-EVEN POLICY WHEN Q IS UNKNOWN

If eventual query count is unknown:

1. start with the low-setup exact method;
2. observe accumulated queries;
3. estimate future reuse;
4. compile a heavier backend only when expected future savings exceed its setup cost;
5. switch exact backends without changing output semantics.

This is a deterministic rent-versus-buy policy and may be more robust than predicting eventual `Q` from circuit structure.

---

# 14. CROSS-QUERY COFACTOR CACHE

For node `v`, let `L(v)` be its live-variable set.

Under query `q`, the node depends only on the restriction of `q` to `L(v)`.

Possible cache key:

`(v, F_q ∩ L(v), assignment restricted to F_q ∩ L(v))`

Store results in a canonical local residual-variable order.

Potential benefits:

- reuse between queries differing only on variables irrelevant to a subgraph;
- reuse across related restrictions;
- reuse across sibling cones;
- bounded resident cache without full truth.

CM IR already carries live-variable metadata and may be a useful experimentation surface.

---

# 15. MULTI-ROOT / CROSS-CONE COMPILATION

If real workloads compute multiple outputs from a shared parent circuit:

1. retain the parent circuit DAG;
2. collect requested roots;
3. mark union of reachable nodes;
4. compile one multi-root program;
5. share intermediates;
6. emit multiple exact results.

Compare:

`T_separate = sum_r T(r)`

with:

`T_multi_root = T({r1,...,rm})`

Record:

- sum of per-root node counts;
- union node count;
- sharing ratio;
- preparation;
- execution;
- peak memory;
- exact result hashes.

Only prioritize if real workloads have enough sibling-root reuse.

---

# 16. MAJOR MATHEMATICAL EXPERIMENT — GF(2) RANK IN THE ANF BASIS

The repository already has:

- packed ANF;
- exact partitioned truth-matrix rank;
- C16 screen-before-materialize decomposition.

For a partition into row variables `R` and column variables `C`, reshape ANF coefficients into:

`A[alpha,beta]`

where `alpha` indexes a subset of row variables and `beta` a subset of column variables.

Truth evaluation applies subset-zeta transforms on both axes:

`T = Z_R A Z_C^T (mod 2)`

Since subset-zeta matrices are invertible over GF(2):

`rank_GF2(T) = rank_GF2(A)`

If:

`A = U V`

then:

`T = (Z_R U)(V Z_C^T)`.

This suggests rank and rank factorization could potentially be computed in ANF coefficient space, with truth-basis factor conversion only for finalists.

## Why this might help

For ANF-sparse functions:

- the coefficient matrix may contain far fewer nonzeros;
- dense truth-matrix layout may be avoidable during screening;
- only a winning candidate may require canonical truth-basis factors.

This could connect the successful C6 packed-ANF work with C16 rank screening.

## Validation

Exhaust all 65,536 Boolean functions of four variables.

For every nontrivial partition:

- compute truth matrix;
- compute ANF coefficient matrix;
- prove rank equality;
- factor;
- transform factors;
- reconstruct exact truth.

Then test all C16 cases and compare timing by ANF density.

Potential external/native GF(2) control: M4RI.

Kill if:

`T_ANF_construction + T_ANF_rank + T_factor_conversion`

does not beat current rank screening on the intended sparse cohort.

---

# 17. GLOBAL-BEST DECOMPOSITION BRANCH-AND-BOUND

C21 showed that ranking does not save work if the exact same complete descriptor universe is still evaluated.

The missing mechanism is a **sound lower bound** allowing early termination.

## 17.1 Rank lower bound

During incremental Gaussian elimination:

`r_partial <= r_final`.

If artifact cost is:

`C_rank = r*(n_rows+n_cols) + C0`

then:

`LB_rank = r_partial*(n_rows+n_cols) + C0`

is a sound lower bound.

If `LB_rank` exceeds the incumbent primary cost, abort the candidate.

Tie rules must be respected; equality cannot be pruned unless deterministic tie order is also bounded.

## 17.2 Cofactor-block lower bound

As blocks are scanned:

- discovered pattern classes cannot disappear;
- already-required references cannot shrink.

Maintain a monotone lower bound on final artifact cost and abort once it cannot beat the incumbent.

## 17.3 Kronecker early rejection

Stream blocks and reject immediately on the first block inconsistent with the exact zero-or-common-factor condition.

## 17.4 XOR-component early termination

As ANF monomials add interaction edges, connected components can merge but cannot split.

Once the graph becomes connected, a nontrivial XOR-component artifact is impossible for that candidate.

## 17.5 Ordering after bounds

Once sound bounds exist, order partitions using deterministic lower bounds so a strong incumbent is found early.

Only after this should learned ranking be reconsidered.

## 17.6 Proof record

For every pruned candidate retain:

```text
candidate identity
lower-bound type
bound value
incumbent value
minimal evidence required to replay the bound
```

Required success:

- byte-identical global-best artifact;
- replayable proof for all pruned candidates;
- >=30% reduction in expensive descriptor work;
- >=1.10x complete-task speedup.

---

# 18. IMPROVE ALL-PARTITION PROCESSING

Potential exact improvements:

## Gray-code partition traversal

Order row subsets so consecutive partitions differ by one moved variable.

Reuse:

- permutation plans;
- reshape metadata;
- elimination workspaces;
- compatible rank/cofactor state where mathematically valid.

## Group by matrix shape

Process equal `(abs(R),abs(C))` shapes together and reuse buffers.

## Singleton-cut fast paths

Implement specialized packed tests for rank/cofactor/Kronecker when one side has only one variable.

## Hash prefilter

Use cheap fingerprints only to reject obvious inequality; exact comparison remains mandatory on fingerprint matches.

## Certified descriptor-payload reuse

Let descriptors retain exact intermediate work:

- rank pivots/echelon state;
- cofactor classes;
- complement flags;
- common Kronecker factor;
- serialization ingredients.

Finalist materialization then reuses screening work.

---

# 19. ANF REPRESENTATION PORTFOLIO

Compare exact ANF representations:

### Sparse monomial set

Best when `M << 2^k`.

### Current packed coefficient bitset

Best at moderate/high density and zeta-transform-heavy work.

### ZDD-backed monomial family

Potentially useful when monomial sets exhibit repeated combinatorial structure.

Use strict node/time budgets and exact fallback.

Potential external reference: PolyBoRi.

Candidate representation features:

- monomial count `M`;
- density `M/2^k`;
- max degree;
- operand monomial overlap;
- product-cache hit rate;
- decision-diagram node count/growth.

---

# 20. NATIVE FULL-TRUTH FROM ANF

When ANF is already available, benchmark exact native full evaluation directly from ANF.

Possible external/reference approaches:

- Gray-code/Fast Exhaustive Search;
- space-efficient Möbius transform;
- BeanPolE-style Boolean-polynomial evaluation.

Match lifecycle and output contracts exactly.

---

# 21. FUSED NATIVE FLATPROGRAM EXECUTOR

At support 11–16, a per-gate NumPy call may be expensive relative to the small word vector.

Implement in increasing complexity:

1. native scalar slot interpreter;
2. native word-array interpreter;
3. compiler-vectorized implementation;
4. explicit SIMD only if needed.

Conceptual loop:

```text
for instruction in program:
    for word in active_words:
        dst[word] = op(src1[word], src2[word])
```

Include:

- contiguous slots;
- liveness-based reuse;
- multi-root output;
- arbitrary care-set patterns;
- optional fused count/SAT/witness extraction.

Compare complete-task performance across:

```text
Python bigint
NumPy words
native scalar words
native compiler-vectorized words
explicit SIMD if justified
```

Continue only if the complete task improves materially, e.g. >=1.10x in the target regime.

---

# 22. ARITHMETIC-STRUCTURE PRESERVATION / RECOVERY

The high-expansion C36 projection winners are multiply-low-cone cases.

Bit-blasting may have destroyed compact arithmetic semantics.

Consider a mixed exact IR containing:

```text
word-level add
word-level multiply
bit extract
comparison
mux
Boolean primitive
```

Then evaluate these over assignment batches using native operations.

For bit-blasted inputs, investigate selective exact arithmetic recovery.

Potential external controls/references:

- Berkeley ABC;
- arithmetic-aware AIG rewriting/refactoring;
- targeted exact structure-recovery approaches such as BoolE-style methods.

Do not make unrestricted equality saturation or broad rewriting universal preprocessing.

Target prepared, repeated, arithmetic-heavy workloads only.

---

# 23. CONTRACT SPECIALIZATION

Current C36 delivery includes explicit reduced relation plus digest/count/SAT/witness.

If future consumers sometimes need less, define separate exact contracts:

```text
RELATION_EXPLICIT
RELATION_DIGEST
MODEL_COUNT
SAT_ONLY
CANONICAL_WITNESS
COMPRESSED_EXACT_ARTIFACT
```

Then optimize each honestly.

For repeated conditioning without explicit relation output, revisit:

- decision-DNNF;
- resident BDD/ZDD;
- incremental SAT;
- certified knowledge compilation.

Do not compare these summary-only contracts against C36's explicit relation task as if they were identical.

---

# 24. TESTING PROGRAM

## 24.1 Sharing metamorphic tests

Create semantically identical forms with radically different sharing:

```text
shared DAG
duplicated DAG
v1 nested tree
v2 shared serialization
associatively regrouped equivalent form
```

Require identical exact outputs.

Also assert work invariants:

```text
memoized node evaluations <= reachable unique nodes
slot execution count == compiled instruction count
raw occurrence baseline count == unfolded visits
```

Avoid wall-clock thresholds in unit tests.

## 24.2 Exhaustive four-variable universe

For all 65,536 Boolean functions:

- all restrictions;
- all nontrivial partitions;
- truth/ANF consistency;
- ANF-basis rank equality;
- factor reconstruction;
- cofactor artifacts;
- Kronecker artifacts;
- independent vs batched queries;
- care-set vs full projection;
- trace-specialized vs fresh restriction.

## 24.3 Query metamorphic properties

Verify compatible restriction composition:

`restrict(restrict(f,a),b) = restrict(f,a union b)`

Also verify:

- batching equals independent queries;
- query ordering changes no canonical result;
- duplicate query dedup preserves duplicate outputs;
- trace-specialized reduction equals fresh restriction;
- online backend switching preserves exact delivery.

## 24.4 Controlled structural generator

Independently vary:

- support `k`;
- unique nodes `N`;
- unfolded visits `U`;
- `U/N`;
- instruction count `I`;
- operator mix;
- roots;
- query count `Q`;
- residual widths;
- care-set coverage `C/S`;
- query overlap;
- ANF density;
- cross-root sharing.

Use only for mechanistic profiling, not prospective confirmation.

## 24.5 Memory tests

Use both:

- `tracemalloc`;
- process RSS/native allocation measurement.

Track:

- live bigint payload;
- FlatProgram slots;
- NumPy buffers;
- projection index memory;
- care-set maps;
- cofactor caches;
- BDD/ZDD nodes;
- multi-root state.

## 24.6 Performance regression counters

Assert complexity-related counters rather than milliseconds:

- each shared DAG node evaluated once;
- topological restricted evaluator executes each reachable restricted node once;
- care-set evaluator processes exactly `C` lanes;
- liveness caps active slots;
- minimum safe index dtype;
- branch-and-bound prunes a constructed candidate;
- direct v2 compiler performs one topological compilation pass.

---

# 25. REPRODUCIBILITY AND MANIFEST CLOSURE

The current memoized C36 run is internally verified but omitted the changed performance-critical backend source from its manifest.

Fix experiment provenance.

At experiment completion:

1. inspect `sys.modules`;
2. resolve all local imported modules;
3. hash their exact bytes;
4. include native `.pyd/.dll/.so` dependencies where relevant;
5. record/hash interpreter executable if practical;
6. record dependency versions / lockfile;
7. hash dataset;
8. hash protocol;
9. hash schedule;
10. hash verifier;
11. hash results.

Add a tamper test:

> changing `bitset_backend.py` must alter the experiment manifest.

For formal experiments use a clean Git worktree, source archive, or otherwise hash-closed state.

---

# 26. RECOMMENDED EXPERIMENT ORDER

| Order | Experiment | Main question | Continue when |
|---:|---|---|---|
| 1 | Restricted evaluator R0/R1/R2 | Does DAG-aware restriction eliminate the router boundary? | Exact and faster/no harmful tail |
| 2 | C36 stage + RSS profile | Where does runtime/memory go? | Material stages identified |
| 3 | Bigint vs words matrix | Are compiled arms using the right engine at widths 11–15? | Measurable crossover |
| 4 | Concatenated/care-set batch backend | Can 64 restrictions be evaluated as one exact assignment batch? | >=1.10x development gain |
| 5 | Direct v2 DAG-to-slot arena | Can routing/CSE/support/liveness passes be fused? | >=20% prep or >=5% total |
| 6 | Projection conversion/index cleanup | Can projection become materially cheaper? | >=5–10% projection gain |
| 7 | Trace-specialized cofactor DAG | Can query-local structure be reused without full truth? | Wins a real regime |
| 8 | ANF-basis rank experiment | Can C16 rank screening avoid dense truth layout? | Exhaustively exact + speedup |
| 9 | Global-best lower-bound pruning | Can C21 completion be reduced soundly? | >=1.10x total + proof |
| 10 | Native fused slot executor | Is Python/NumPy dispatch limiting? | >=1.10x relevant complete task |
| 11 | Multi-root/cross-cone evaluation | Is parent-circuit sharing enough? | Strong grouped-workload gain |
| 12 | Formal routing confirmation | Is meaningful headroom left after repair? | Prospective >=1.05x charged |
| 13 | Contract-specific BDD/d-DNNF | Are summary-only repeated queries important? | Real task contract supports it |
| 14 | Learned guidance | Is there an exact early-termination decision with headroom? | Simpler methods leave room |

---

# 27. WHAT NOT TO PRIORITIZE

## Deeper neural answer prediction

Do not spend another major cycle on GNN depth/activation/width/dropout unless a new task exists where prediction truly removes exact work.

## Formalizing old `U/N > 10` unchanged

Do not formalize before repairing `_eval_ast_restricted`.

## Universal CM IR promotion

CM IR remains valuable but current evidence does not establish it as universal fastest execution.

## Fresh BDD per short task

Already unfavorable under the tested lifecycle.

## Unrestricted equality saturation

Previous broad rewrite/caching evidence is often narrow or negative. Restrict any future use to bounded, targeted, arithmetic-heavy subgraphs.

---

# 28. TARGET FUTURE ARCHITECTURE

```text
                    serialized DAG v2
                           │
              one-pass metadata/slot compiler
       ┌───────────────────┼────────────────────┐
       │                   │                    │
   graph data          trace data           ANF data
 N,U,I,live sets     Q,L,C,overlap       degree,density
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │
                 deterministic cost planner
                           │
       ┌───────────────────┼───────────────────────┐
       │                   │                       │
 memoized/topological   query-set batch      full projection
 direct restriction     or cofactor DAG      packed extraction
       │                   │                       │
       ├───────────────────┼───────────────────────┤
       │              optional CSE/CM IR           │
       │              or native execution          │
       └───────────────────┼───────────────────────┘
                           │
                  canonical exact delivery
                           │
                  independent verification
```

CM IR remains a normalization/compiler option rather than a mandatory universal execution layer.

ANF becomes both an exact evaluation path and a possible algebraic screening basis.

Routing becomes a thin decision layer after exact algorithms are optimized.

---

# 29. IMMEDIATE IMPLEMENTATION INSTRUCTION

The first implementation task should be:

> **Create a development-only exact experiment comparing the existing `_eval_ast_restricted` with an identity-memoized version and a topological/liveness version, preserving the old implementation as a frozen control.**

Do **not** consume prospective C37 confirmation data.

Use only development/exposed corpora.

Required artifact layout:

```text
docs/recognition/runs/<new-development-id>/
    protocol.md
    results.json
    raw_measurements.jsonl
    environment.json
    manifest.json
    independent_verification.json
    report.md
```

The manifest must include all transitive performance-critical sources.

Required correctness:

- zero relation mismatch;
- zero count mismatch;
- zero SAT mismatch;
- zero witness mismatch;
- exact canonical delivery equality.

Required profiling:

- decode;
- restriction setup;
- evaluation;
- delivery;
- total;
- peak RSS;
- node/gate execution counts.

Required subgrouping:

- support width;
- `N`;
- `U`;
- `U/N`;
- family;
- query count.

After this experiment, recompute the backend oracle from scratch.

Only then decide whether:

1. structural routing retains meaningful headroom;
2. projection remains necessary;
3. CSE becomes dominant;
4. multi-query care-set evaluation should become the primary follow-up.

---

# 30. DECISION TREE AFTER THE FIRST IMPLEMENTATION

```text
memoized/topological restriction tested
             │
             ├── high-U/N direct becomes fast
             │       │
             │       ├── routing headroom collapses
             │       │       → abandon old router
             │       │       → focus batch/care-set/CSE
             │       │
             │       └── routing headroom remains
             │               → rebuild features on optimized backends
             │
             └── high-U/N direct still slow
                     │
                     ├── projection wins because full-truth amortization is real
                     │       → continue structural/lifecycle routing
                     │
                     └── CSE wins
                             → investigate CSE/batch/native path
```

---

# 31. EXTERNAL TECHNICAL REFERENCES FOR FOLLOW-UP

These are external references, not project evidence.

## M4RI

GF(2) dense matrix arithmetic / word-parallel Gaussian elimination.

`https://arxiv.org/abs/0811.1714`

## PolyBoRi

Boolean polynomial / ZDD-based algebra.

`https://www.sciencedirect.com/science/article/pii/S0747717109000273`

## Berkeley ABC

AIG rewriting, refactoring, structural hashing, exact-equivalence-oriented circuit optimization.

`https://people.eecs.berkeley.edu/~alanmi/abc/abc.htm`

## BoolE-style arithmetic structure recovery

`https://arxiv.org/abs/2504.05577`

## Knowledge compilation / decision-DNNF

Potential relevance for summary-only repeated conditioning.

`https://drops.dagstuhl.de/entities/volume/LIPIcs-volume-377`

These should only be tested under task-matched exact lifecycle contracts.

---

# 32. SCIENTIFIC RULES FOR THE IMPLEMENTING AGENT

For every optimization:

1. Keep the previous exact backend as a control.
2. Do not silently change the task contract.
3. Charge setup/transformation costs.
4. Preserve independent verification.
5. Save raw timing rows.
6. Hash all transitive performance-critical sources.
7. Report memory as well as time.
8. Separate development from prospective confirmation.
9. Do not tune thresholds on confirmation data.
10. Label conclusions as measured, derived, inferred, or speculative.

A speedup that depends on:

- removing verification;
- excluding setup;
- warm caches unavailable in deployment;
- changing output requirements;
- or comparing only to a known-defective baseline

must not be presented as a general project improvement.

---

# 33. FINAL PRIORITY STATEMENT

The three strongest directions are:

## Priority 1 — Repair restricted exact evaluation

Highest-information, lowest-risk immediate task.

## Priority 2 — Multi-query care-set / trace-specialized evaluation

Directly attacks repeated exact work and may create a new backend between independent restriction and full projection.

## Priority 3 — ANF-basis GF(2) rank + exact lower-bound pruning

Strongest mathematical path toward extending the successful C6 and C16 exact advances.

Only after these are adjudicated should the project return to a formal routing study or learned guidance.

The guiding principle should remain:

> **Optimize exact computation first. Route only between genuinely optimized exact alternatives. Introduce learning only when it can avoid exact work rather than add itself before the same exact work.**
