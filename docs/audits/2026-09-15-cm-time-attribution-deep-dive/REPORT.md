# CM time attribution: structure, execution, and caller costs

## Finding and scope

CM execution does not have one bottleneck. The evidence distinguishes three
different questions: the size of the requested answer, the cost of constructing
and retaining a CM representation, and the surrounding work charged to a caller.
An explicit relation imposes exponential output work. That alone does not explain
CM's extra construction cost over a sharing-aware flat program, recurring public
wrapper work, family cache management, or a benchmark's exhaustive validation.

This is a diagnostic study at commit
`e334de594262059cc18cf37eaab56b0f79e94843`, in a separate detached worktree.
The original root and consolidation worktree were not edited. There are no
production changes: instrumentation, scripts, tests, and reports are contained
in this new audit directory. All new measurements use disclosed development
inputs and are **diagnostic measurements, not confirmation benchmarks**.

Some requested predecessor artifacts are absent at that commit. The original
root supplied read-only, individually hashed copies of the performance report,
SymPy worker and development-gate evidence. The task harness explicitly loads
one hash-bound historical helper while resolving CM/BitSet imports from the
pinned worktree. Its provenance is separate from baseline production code.
No held-out input was loaded, generated, or run; already measured historical
records were recomputed without executing their inputs.

Labels used throughout:

- **Measured:** a result from the declared diagnostic passes or arithmetic on
  frozen measured records, with its actual timer boundary preserved.
- **Code-supported inference:** a mechanism established by source inspection,
  without claiming an independently timed contribution.
- **Hypothesis:** a plausible finer explanation that the available observations
  do not distinguish.
- **Unknown:** missing, inseparable, or insufficiently resolved evidence.

## 1. What does “full information” require?

An expression over a requested basis of k Boolean variables has 2^k rows in its
complete relation. A packed one-output relation occupies ceil(2^k/8) bytes;
the dense Boolean/uint8 interfaces in this implementation use 2^k bytes for the
same logical values. All competitors delivering the same full packed relation
owe those output bits. CM's mathematical expressiveness does not establish an
additional per-row disadvantage over another packed evaluator.

The current `CMNode` is a symbolic DAG, not a stored matrix of all assignments.
Its kind, operator, children, public structural key, and variable-support tuple
describe the expression. Exponential expansion begins when a path constructs
truth masks, evaluates full-width intermediates, or materializes complete
output. Calling all IR-construction cost “full information” conflates retained
symbolic metadata with actual relation materialization.

| Requested task | Unavoidable requested output | What full-relation CM adds |
|---|---|---|
| Complete packed relation | 2^k bits and full delivery | No larger logical answer than direct packed controls; different graph/preparation costs remain. |
| Supplied B assignments | B answers, plus supplied assignment input | Enumerating 2^k rows would solve a larger task. The measured CM batch helper evaluates only the supplied rows. |
| Cofactor relation | 2^(number of remaining variables) bits per context | Full original-basis reinflation can be unnecessary if the requested result is reduced. Comparisons must fix this contract. |
| Exact count | One integer up to 2^k, at most k+1 bits | Enumeration creates information the output does not require; structured counters may avoid it. |
| SAT status / equivalence status | A Boolean, plus any required witness | Full relation or both full truth vectors are an algorithm choice. SAT solving a formula/miter need not enumerate all rows. |
| Simplified expression | A complete equivalent expression under an agreed form/quality contract | A truth-table-to-minimizer pipeline may enumerate minterms the symbolic task did not require. Expression size can itself be large; that does not universally require a full truth table. |

These are **code-supported contract distinctions**, not a proof that SAT, BDD,
or symbolic methods always run faster. Those methods have their own preparation,
search/representation costs, and difficult instances. The frozen counts and
ROBDD controls are useful precisely when their task and delivery are named.

## 2. Where the execution paths differ

The complete [execution map](EXECUTION_MAP.md) identifies all requested phases
and explicitly marks absent analogues. The principal paths are:

| Path | Preparation retained | Work repeated per evaluation |
|---|---|---|
| Raw recursive AST ablation | Expression and supplied environment | Repeated source occurrences, recursive dispatch and bigint arithmetic. |
| Current direct/memo AST | Expression; environment cache | Identity memo creation, unique-object traversal and bigint results retained through the call. |
| Structural CSE-flat | Structural UID/fanout preparation, flat loads/ops and release schedule; bound masks | Slot-template copy, flat dispatch and packed arithmetic. |
| CM through common flat primitives | Source UID prepass; canonical CM DAG with keys/support; then flat program and bound masks | Exactly the same prepared flat executor as the CSE arm. |
| Bare production CM-flat | CMNode and root-attached flat program | Program lookup, fixed-context key construction/validation, bound lookup, flat execution. |
| Public no-reinflate CM | Same CMNode | Budget estimation including node counting, output-basis decisions, engine selection, bare evaluator and result object. |
| CM-family | Per-variant CM preparation, optionally digest-keyed persistent nodes | Sharing prepass/digest/cache management, required new compilation, output computation and wrapper/verification work. |

**Code-supported inference:** structural CSE can preserve useful sharing while
retaining a smaller execution representation. It has no CMNode public deep keys
or support tuple per node. CM can compensate by simplifying logic before
lowering, so its flat program can be shorter. When the two lowered programs are
similar, preparation rather than packed arithmetic is the main difference in
the disclosed tiny cases.

The existing direct API already memoizes by object identity. The diagnostic
uncached recursive arm must not be described as today's production BitSet.
Conversely, engine labels `raw_ast_flat` and `raw_ast_words` currently select
occurrence-expanding raw lowering; the strongest structural CSE control is
explicitly invoked separately. Beating the occurrence-flat ablation does not
establish an advantage over sharing-aware CSE.

## 3. What the controlled measurements establish

The primary ladder has 137 exact-output cells; the task/family suite has 70.
Every declared cell completed and passed its complete output/semantic checks.
All medians, absolute process CPU readings, phase-pass percentages, helper
counts, memory observations, structural metrics and output sizes are available
in [PROFILE_RESULTS.json](PROFILE_RESULTS.json) and [TIME_LEDGER.md](TIME_LEDGER.md).
The detailed numerical findings are in [LADDER_FINDINGS.md](LADDER_FINDINGS.md)
and [TASK_FINDINGS.md](TASK_FINDINGS.md).

### Matched packed execution

For the disclosed `random-existing-k16` case, the corrected uninstrumented
resident per-output medians are approximately 36.3 microseconds for CSE-flat,
36.2 microseconds for CM through the common flat executor, and 62.3 microseconds
for public CM. Cold library-session medians are approximately 337.8, 500.7 and
613.0 microseconds respectively. These are **measured** local diagnostics;
resident calls include byte delivery and the common audit guard, not just
arithmetic. Preparation is included in the cold boundary and excluded from the
resident boundary by design.

This library boundary starts at `Session.run`: constructing the session's
variable-name tuple, clearing caches, physical file loading and session teardown
are outside it. Resident q64 recomputes the identical output 64 times, with no
whole-result memoization in any arm. It tests retained execution state, not an
application's useful query mix or modeled amortized savings. The common equality
guard is audit work; required public output-budget guards remain inside public
calls. [METHOD_LIMITS.md](METHOD_LIMITS.md) gives the complete boundary.

The difference changes with the case. CM rewrites reduce some flat programs,
including the disclosed small mixed-expression fixtures, so a prepared CM
kernel can be faster. Shared-subtree and XOR-chain examples can give CSE and CM
the same number of flat operations and closely similar prepared cost. These
results answer the kernel question: **some CM kernels are competitive once
preparation and wrapper differences are isolated**. They do not establish a
complete caller or corpus advantage.

### Public wrapper regression

The public/bare comparisons hold the source, CM graph shape, variable order,
packed primitives and delivered bytes constant. The ledger reports the
incremental public-minus-bare resident difference and its fraction of public
time for every case. This is a controlled incremental comparison, not an
additive division of independently measured phase medians.

For `random-existing-k16`, the resident public-minus-bare median difference is
24.5 microseconds per output, 39.3% of the public median. Across the 13 cases,
this incremental fraction ranges from 30.3% to 88.5%. These are **measured
differences of whole-call medians**, not exclusive wrapper phase fractions:
cache behavior, timing variation and path interactions remain in the difference.

**Code-supported inference:** public calls repeatedly traverse nodes for output
budget accounting, estimate full/reduced output, decide the output basis,
select the engine and allocate a result wrapper. These obligations are absent
from a bound kernel. A diagnostics dictionary selects the generic wrapper;
`diagnostics=None` permits the flat fast path. The explicit `public_cm_diag`
arm therefore measures an implementation-path interaction, not merely the
cost of reading a clock. Family calls always provide a diagnostics dictionary.

The trace preserves these branch choices. An initial trace missed imported
evaluator aliases and could mislabel kernel work as wrapper self time; its
records remain preserved and are excluded. The corrected trace and tests
cover the aliases. Even corrected fine-grained probes significantly dilate
tiny calls, so their percentages use their own measured caller denominator.

### Assignment, restriction, scalar and expression tasks

The same NumPy batch helper consumes raw-adapter, structural-sharing-adapter,
or CM nodes and delivers every one of 4,096 supplied-row answers. This isolates
CM preparation from a change of evaluator more closely than the predecessor
CM-versus-lambdify comparison. Deterministic assignment-row generation, packing
and list conversion are significant shared costs in this diagnostic boundary.
The generation phase must not be called necessary CM work or a property of an
already supplied batch.

Restriction q1/q64 uses the same prepared packed primitives and reduced output
order for direct CSE and CM ingress. The q64 treatment cycles four distinct
two-variable contexts: it measures repeated binding reuse, not 64 independent
contexts. It compiles once per session and still delivers every cofactor.

Exact count, SAT and equivalence use CSE and CM ingress to the same packed
executor before the same bit-count/status operation. SymPy task controls are
reported as algorithm comparisons. The simplification ablation gives direct
and CM ingress the same minterm/SOPform backend; separate SymPy simplify arms
use a different pipeline. This prevents assigning a minimizer or evaluator
advantage to CM representation.

## 4. Raw CM and family CM are not slow for identical reasons

They share source traversal, canonicalization, retained support/key structure,
lowering, execution and delivery mechanisms. Family CM adds the work needed to
decide whether retained representations remain reusable across variants.

**Code-supported inference:** the persistent compiler runs a structural-sharing
prepass even on hits and computes canonical digests. Without shared associative
classes, it can reuse subtree entries. With context-dependent shared associative
classes, it restricts reuse to the whole root to preserve canonical shape. A
small change can therefore destroy a root hit even while much syntax is shared.
Foreign-node adoption can rebuild local interning information. This is
reuse-management cost, not full-relation output cost.

Measured high/partial/mutation treatments report actual hits, misses and retained
entries, rather than assuming mutation rate equals lost reuse. Root-only versus
subtree eligibility is essential to interpreting those counters. Zero counters
recorded as placeholders when diagnostics were off are normalized to unknown
in the synthesis; phase-pass counters and genuine public counters are used.

The public family function also performs conversion/verification outside its
per-variant compile/eval spans. Its outer wrapper constructs reference truth
tables and family structural diagnostics. The new public-family diagnostic
reproduces that preparation plus the actual `_cm_family_workload`; it is an
instrumented decomposition of the CM family portion, not a new timing claim
for running every backend in `time_expression_family_workload`.

The public family function returns benchmark statistics and validates internal
relation results. Its audit hash is constructed from reference values; it is
not a newly returned CM relation artifact. The custom CSE/CM family arms return
complete packed variant outputs. Public-family versus custom-family totals
therefore compare these different benchmark/output boundaries, while cache
on/off comparisons within each boundary retain the same contract.

Repeated identical variants can amortize representation preparation. Packed
evaluation, requested output delivery and per-call wrapper work still recur.
The persistent cache stores representations, not a guarantee that a full result
is free. The table of amortizable mechanisms is in the execution map; actual
reuse depends on object lifetime, cache keys, capacity, context and mutation.

## 5. Reinterpreting the frozen comparative evidence

[FROZEN_EVIDENCE.md](FROZEN_EVIDENCE.md) recomputes the ledgers and verifies their
bindings. All nine SymPy development-gate ratios reproduce exactly. That gate
remains **no-go**: the predecessor changed representation and evaluator together
and did not isolate a CM contribution.

Several boundary findings materially change how those numbers can be explained:

- In the frozen Y02–Y05 CM arms, the task timer is only about 0.038% of caller
  time for complete relation, 0.491% for assignment batch, 0.315% for SAT and
  0.058% for equivalence (aggregate same-arm sums). Most observed caller wall
  time lies outside the task timer. Imports, transport and shutdown cannot be
  individually allocated from those records.
- The worker's task timer includes correctness/delivery work that its named
  stages omit, despite its docstring. CM SAT's unnamed residual is about 88.2%
  of task time. Code shows exhaustive scalar validation in that span; the
  residual is **measured**, and validation's presence is a **code-supported
  inference**. Its individual share is **unknown**; assigning the entire
  residual to validation would be an unsupported hypothesis.
- Architecture `compilation_ns` is hardcoded zero; preparation includes
  compilation. Some binding occurs inside `evaluation_ns`. Lane D evaluation
  contains a whole nested task. Those fields cannot be presented as pure kernels.
- Retry A cleanup contributes roughly 87–96% of accounted totals by arm and
  calls `gc.collect()` while local roots/results are still referenced. This is
  measured collection work, not measured complete object disposal.
- Retry-002 Lane B rows are q64. Prefix correctness hashes for q1/q4/q16 are
  not independent timings. The cross-machine query ladder does measure distinct
  query counts, and its isolated-process lifecycle is separate from accounted
  task total.
- Some older performance timings ran under tracemalloc. They remain valid as
  allocation-instrumented observations; no multiplier turns them into
  uninstrumented timing estimates.

Direct BitSet, portable ROBDD, native SAT, CNF counting, factorized counts and stream controls
must therefore be interpreted at their own task/preparation/delivery boundary.
A symbolic BDD or scalar count is a smaller requested artifact than an explicit
relation; an explicitly materialized BDD truth relation must pay extraction too.
Task-matched frozen direct-versus-CM ingress controls are stronger attribution
evidence than comparisons that change both algorithm and output contract.

## 6. Scaling: output growth versus representation work

The fixed-expression ladder keeps a seven-node CM and three-instruction flat
program while changing the requested output basis from four to eighteen
variables. Output grows from two bytes to 32,768 bytes although semantic support
stays at four variables. The measured increase in masks, packed operations,
conversion and traced retained memory is therefore not caused by increasing
CM-node count. Complete output over unused requested axes still has to repeat
the values. This separates output growth from source/IR growth.

The structural examples separately show object sharing, structural sharing and
single-consumer chain flattening. `flat_instructions` is not a primitive-operation
count: an n-ary instruction can execute many bigint/word operations. The metrics
include both counts and peak word-buffer liveness. CM rewrites can reduce one
without proportionally reducing another; primitive cost also depends on operand
width and values.

Derived flat-program metrics are computed after the memory snapshot. In recursive
CM and dense arms, that structural accounting can create a flat program that was
absent during execution and the retained-memory observation. Those derived
instruction/cache fields cannot be used to assign bytes at the earlier snapshot.

Support tuples and deep public keys are retained CM structure. However the
current interning map uses compact child UIDs; it would be incorrect to revive
the historical claim that every intern lookup hashes a deep CM key. Key
construction, operand sorting, support union, repeated Python calls and foreign
adoption remain plausible/measured helper costs at their recorded resolution.
The same pure-Python helper includes more than one mechanism, so its full time
cannot be split among hashing, comparison, allocation and reference counting
without further evidence.

These small cases do not independently vary all axes. They support bounded
mechanism observations and a fixed-structure output-growth comparison, not
independent fitted exponents in source size, support width, sharing and mutation.
The ledger includes a representation-by-residency incremental decomposition;
it does not force those interacting effects into additive percentage shares.

## 7. What remains unknown

Every measured caller span has an explicit arithmetic remainder, but not every
slowdown has a uniquely identified cause. Corrected ladder phase-pass remainder
shares range approximately 2.4–66.1%; the high end occurs for tiny kernels where
harness/probe work is large. This remainder cannot be redistributed to make
the attribution look complete.

The evidence does not determine:

1. Unbiased nanosecond-level helper shares from heavily instrumented Python
   calls; distinguishing them requires lower-perturbation observation with the
   same code path and caller contract.
2. Separate bigint arithmetic versus allocator/refcount cost, word scratch
   management versus conversion, or cache validation versus key/lookup work
   inside joint helpers. Allocation/native-call-level observations would be
   needed; existing wall spans do not resolve them.
3. Reliable tiny-phase process CPU shares on this Windows clock. Zero readings
   are quantization, not evidence that a phase consumes no CPU.
4. Complete native RSS, cumulative allocated bytes, allocator fragmentation or
   process-lifetime retention from tracemalloc's net/peak traced bytes.
5. Exact import/startup/transport/shutdown splits for historical caller totals,
   or full object-teardown time for the new in-process ladder.
6. SAT/counting/BDD kernel shares where only frozen aggregate or nested spans
   exist, and the performance of unavailable native counting/BDD implementations.
   No unavailable dependency or held-out input was used to fill those gaps.
7. Universal crossover points, a new routing rule, cross-machine performance,
   or a scientific development/confirmation gain. The cases and repetitions
   were selected for attribution, not confirmation or population inference.

## 8. Direct answers and disposition

**Is full-information CM responsible?** For explicitly delivered relation size,
yes, and every comparator owing the same complete relation pays that output
requirement. For CM metadata construction, public-wrapper regression and
scalar-task algorithm mismatch, it is an incomplete or wrong explanation.

**Does CSE-flat preserve sharing while shedding CM structure?** Yes by code;
the common-executor diagnostic shows that its preparation advantage can coexist
with CM kernel parity. CM simplification can also produce a smaller program.

**How much regression is outside the evaluator?** It is case-dependent and
reported as public-minus-bare increments and own-denominator phase shares.
For tiny resident outputs, wrapper work can exceed kernel work; cold caller
cost also includes representation preparation. Historical fresh-process totals
are often dominated by lifecycle work outside either evaluator.

**Are raw and family CM slow for the same reasons?** They share IR/execution
costs; family adds digest/sharing eligibility, cache management, adoption and
family wrapper/reference work. High hit counts do not imply zero reuse cost.

**Which costs are inherent?** Delivering the requested full output and performing
the requested task. Python object layouts, repeated support/key construction,
particular cache rules, wrapper traversals and conversions are properties of
this implementation/API. The detailed classifications are in
[ROOT_CAUSE_MATRIX.md](ROOT_CAUSE_MATRIX.md).

**Can CM kernels compete?** Yes on some matched prepared packed cases. That is
not an end-to-end gain after their other required costs are charged.

**Why can CM be the wrong representation for scalar or assignment queries?**
An explicit relation retains/evaluates answers the caller did not request,
while suitable query algorithms can work on the supplied rows or symbolic
constraints. CM-based nonenumerative family methods must be assessed separately
from raw explicit CM rather than inheriting either its cost or its credit.

**What cannot be concluded?** No universal dominance, causal split of unresolved
joint spans, production improvement, routing change or new scientific gain.

Verification and exact artifact/source hashes are recorded in
[VERIFICATION.md](VERIFICATION.md) and [AUDIT_MANIFEST.json](AUDIT_MANIFEST.json).
The audit was sealed before version-control mutation; the user subsequently
authorized committing this additive audit directory. It remains unpushed.
**No scientific disposition changed.** The diagnostic scope is complete.
