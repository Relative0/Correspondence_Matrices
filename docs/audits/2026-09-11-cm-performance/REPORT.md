# CM performance investigation

**A small shared-backend change materially reduces cold packed evaluation cost.**
Truth-variable masks now come directly from periodic packed bytes instead of
expanding assignment indices and repacking NumPy arrays. On six new synthetic
confirmation cases, the public packed-CM path improved **2.492× at q1** and
**1.195× at q64**, including decode, compilation, binding, execution, guards and
packed delivery. Direct BitSet and structural CSE-flat also improve. This is a
general engineering gain, not evidence of CM superiority.

The code change is local and tested. No native-batch work, website, earlier
frozen evidence, routing policy or resource default was changed. Nothing was
committed, pushed, published or deployed, and no paid infrastructure was used.

**Current state and corrected priorities.** The source baseline is
`72041c23ceebc257afc977c9e744b762bccaf21c`, with pre-existing website and
native-batch changes recorded by worktree inspection. No additional project
`AGENTS.md` was found; the supplied global instructions apply. README, research
library, July/August audit material, the technical dossier, optimization
backlogs, August corrections and September implementation/results were checked
against executable code. The published overview could not be fetched by the
web reader; local source and research records establish implementation state.

The August compact-key recommendation is superseded by the
[September 8 profile gate](../../research/CM_H2_H3_CURRENT_SOURCE_PROFILE_GATE_RESULT_2026_09_08.md):
key preparation was 7.878% of aggregate exclusive time and dense alignment
3.886%, below their frozen continuation thresholds. This audit does not reopen
H2/H3. The new experiment addresses **packed input-mask construction at a cold
cache boundary**, identified separately on new synthetic inputs.
The [H6 calibration](../../research/CM_H6_FRESH_PROCESS_MEMORY_AND_ESTIMATOR_RESULT_2026_09_08.md)
obtained valid fresh-process memory signals, but its single estimator ordered
0/3 materially separated holdout pairs correctly; memory routing remains
unjustified. The [September implementation note](../../research/CM_RECOMMENDED_INTEGRATIONS_IMPLEMENTATION_AND_TESTING_2026_09_02.md)
also supersedes recommendations to repair occurrence-recursive restricted
evaluation: R2, native slots and multi-root union already exist.

**Execution map.** Public mathematical-CM operations, the CM compiler IR and
complete packed truth vectors are distinct representations and contracts.

| Boundary / source | Executed work and reuse | Status and principal cost |
| --- | --- | --- |
| `cm_bench.py:1433,2718`; `cmbench/context.py` | Benchmark setup, availability, corpus preparation, timing and reference orchestration. The standard single-expression sweep prebuilds BitSet environments. | Implemented. A warm benchmark can hide the cold setup cost measured here; diagnostics/oracles are outside this audit's timing. |
| `cm_expr_serde.py:87,152` | DAG-v2 serialization, backward-reference validation, decoding and structural deduplication. | Implemented, O(DAG size) representation. Tree-v1 export can expand sharing; disk reload and fresh process are separate lifecycle costs. |
| `cm_ir.py:531,1204` | Structural UID pass, safe associative flattening, interning, exact rewrites, support union and compilation. `CMNode.vars` retains canonical support. | Implemented. Compact interning already exists; public deep keys remain. Normalized structural identity is not universal semantic canonicality. |
| `cm_ir.py:285,1292`; `bitset_backend.py:374,697` | Compile reuse, persistent-named IR cache, lowering, binding templates and prepared execution. | Implemented. “Persistent” IR is process-local: 16,384 entries today, not the 10,000 in older prose. Identity compile cache: 4,096; bound templates: 64/program. Disk persistence is a separate research API. |
| `bitset_backend.py:17,57` | Build MSB-first variable columns; immutable mapping cached by the ordered variable-name tuple. | **Changed here above k=10.** Cold construction uses packed periodic bytes; cache semantics and the small-width path are unchanged. |
| `bitset_backend.py:115,329,423,873`; `cmbench/backends/bitset_engine.py` | Memoized bigint DAG evaluation; flat structural CSE/CM programs; NumPy word execution with `out=` and per-thread scratch. | Implemented. Auto words threshold remains 16 when requested. Warm operation cost, liveness and conversions still determine crossovers. |
| `cm_ir.py:1899,2006`; `cm_normalize.py`; `cm_build*.py` | Output admission, fixed assignments, broadcasting/alignment, dense CM or full/reduced packed/table delivery. | Implemented. Eager/lazy/hybrid share the IR; pair-aware 2×2 collapse is experimental and conditional. Reduced output must retain its different declared basis. |
| `gf2_restricted_evaluators.py:223`; `gf2_native_slots.py:273`; `backends/native_restriction.py` | R2 topological arena, validated native bindings, scratch allocation, exact fallback; sibling roots can share one union arena. | Implemented; native activation is guarded and off by default. Native batch successor is pre-existing untracked functional work, not a result of this audit. |
| `cmbench/comparative/{persistence,fresh_persistence,incremental_revision}.py`; `cm_parallel.py` | Structural artifacts/reload, revision reuse, process-pool/shared-memory evaluation; remote wrappers add serialization and infrastructure lifecycle. | Research/optional paths. Fresh persistence has correctness evidence; revision promotion failed. Process, transfer and memory costs must be charged. |

For k live variables, complete explicit output still contains `2^k` bits. Packing
reduces constants; it cannot eliminate output work. The new constructor produces
the same n packed variable columns, with work proportional to their packed
payload rather than traversing unpacked assignment arrays. CPython byte
repetition and little-endian integer conversion implement the construction;
[Python's sequence/integer specification](https://docs.python.org/3/library/stdtypes.html)
and [NumPy's packing convention](https://numpy.org/doc/stable/reference/generated/numpy.packbits.html)
define the ordering boundary verified by tests.

**Measured bottleneck and validation.** The host is Windows 10, AMD family 25
model 80, 12 logical CPUs, Python 3.13.5 and NumPy 2.3.2 in the project `.venv`.
`freeze.json` records revision, source hashes and environment; `fixtures.json`
contains exact DAGs, seeds and development/confirmation roles. Nine adjacent
AB/BA pairs were run per cell, with cell order shuffled by a fixed seed. Timing
passes are uninstrumented; profiling and allocation passes are separate.

At n=16 on the shared development fixture, a diagnostic public-CM session spent
0.180 ms decoding, 0.895 ms compiling and 1.881 ms in binding/guard/execution.
The candidate reduced that last stage to 0.425 ms. The direct control's mask
binding was 1.946 ms versus 0.174 ms. These single staged observations localize
cost; the repeated complete-task results below support performance claims.

| Cold mask construction | Baseline median | Candidate median | Ratio of medians |
| --- | ---: | ---: | ---: |
| 11 variables | 0.146 ms | 0.0225 ms | 6.48× |
| 16 variables | 1.763 ms | 0.114 ms | 15.46× |
| 18 variables | 12.823 ms | 0.483 ms | 26.55× |
| 22 variables | 348.381 ms | 12.927 ms | 26.95× |

The width-11/13/16/18/20/22 cold-mask geomean is 15.830×. Cache hits remain
approximately 0.12–0.13 microseconds at n16/n22; no hit-path improvement is claimed.

| Confirmation public packed-CM q1 case | Baseline median | Candidate median | 95% interval for paired geometric speedup |
| --- | ---: | ---: | ---: |
| n11, low sharing | 0.466 ms | 0.375 ms | 1.194–1.359× |
| n11, high sharing | 1.034 ms | 0.918 ms | 1.056–1.214× |
| n13, low sharing | 0.724 ms | 0.433 ms | 1.555–1.973× |
| n13, high sharing | 1.198 ms | 0.989 ms | 1.158–1.248× |
| n18, low sharing | 14.034 ms | 1.325 ms | 10.335–11.223× |
| n18, high sharing | 14.747 ms | 2.048 ms | 7.103–7.961× |

| Whole-session arm, same ordered packed output | q1 speedup | q64 speedup | 16 changing restrictions |
| --- | ---: | ---: | ---: |
| Public CM | 2.492× | 1.195× | 1.676× |
| Bare CM-flat | 2.490× | 1.248× | 1.746× |
| CM NumPy words | 2.273× | 1.322× | 1.617× |
| Structural CSE-flat, `flatten=True` | 3.225× | 1.256× | 1.800× |
| Direct BitSet / raw-flat restriction control | 3.827× | 1.213× | 1.405× |
| Dense NumPy control, then packed delivery | 1.034× | 0.999× | 1.029× |

These are geometric means of paired ratios, equally weighting six cases, not
ratios of aggregate elapsed time. The per-cell intervals bootstrap the nine
pairs with 2,000 fixed-seed draws. Bootstrapping the six case speedups gives broad
public-CM intervals of 1.248–5.181× at q1 and 1.046–1.398× at q64; neither is a
population-level application estimate. Fixed-work throughput has the reciprocal
time relationship; absolute session latency is retained in the raw files.

**Regressions and limits are material.** The worst ratio of medians over all
54 cold CM cells was **0.972×**, in a small residual-width restriction session.
Warm kernels are unchanged. Across the panel their aggregate ratios were near
parity, but a CSE-flat restriction cell had a 0.882× paired geometric ratio
(interval 0.768–0.990×), and public CM had a 0.884× warm cell (0.728–1.048×).
Every cell's maximum time and minimum paired ratio is saved; nine repeats do
not establish stable production p99 latency. Low-width restrictions often miss
the changed branch, so they principally measure noise/control behavior.

Two fresh-process passes are retained. `fresh_process.json` includes a second,
tracemalloc-instrumented build and must not be used as one-shot latency.
`fresh_process_timing.json` uses exactly one build with checksum delivery,
imports and process cleanup: n16 medians were **338.9 ms baseline / 466.6 ms
candidate**, an observed regression amid varying startup/import time; n22 was
**662.1 / 333.8 ms**. Paired geometric intervals are respectively 0.744–1.021×
and 1.949–2.119×. This is the audit subprocess lifecycle, including its harness
imports, not an optimized service launch benchmark.

| Setup memory, separate traced pass | Baseline peak | Candidate peak | Retained candidate |
| --- | ---: | ---: | ---: |
| n16 | 993,400 B | 149,396 B | 141,216 B |
| n18 | 4,037,080 B | 663,388 B | 630,632 B |
| n22 | 66,796,648 B | 12,829,860 B | 12,305,256 B |

Retained storage differs from baseline by only 312 bytes in these measurements.
The saved fresh children include OS working-set endpoints and process-lifetime
peaks; these are not a calibrated task-peak RSS estimator. Traced allocation and
OS memory must not be conflated. Cache eviction, release, immutable access,
ordered-name identity and concurrent readers have regression coverage.

**Task-matched comparisons.** The faster environment helps the incumbents too:
public CM was not the fastest q1 packed arm on any of the six confirmation
fixtures. Independent count-only diagnostics used the four exposed development
fixtures, with complete build/query cost and a fixed-order `dd.autoref` control.
Direct BitSet won all four q1 count cases; CSE-flat won all four q64 cases.
For n16/high-sharing/q64, medians were 6.645 ms CSE-flat, 8.410 ms public CM,
15.086 ms direct, and 20.650 ms `dd.autoref`. Counts were exact in all 288 timing
rows. This small panel does not establish a general symbolic ranking.
Native CUDD and Numba were unavailable in the project interpreter; no usable
native binary was found in the current build directory, so no new native timing
claim is made. The existing guarded native and two-host comparison results
remain historical, separately scoped evidence.

**Workload coverage and useful next opportunities.** Expected benefit below is
an engineering judgment unless explicitly marked measured. H/M/L denotes
confidence, not a fitted score.

| Priority, source and mechanism | Affected task / expected benefit | Tradeoff, effort and cheapest useful experiment |
| --- | --- | --- |
| **1. Retain periodic-mask construction**, `bitset_backend.py:17`. Exact byte-pattern generation avoids expanded arrays; [Python](https://docs.python.org/3/library/stdtypes.html), [NumPy](https://numpy.org/doc/stable/reference/generated/numpy.packbits.html). | Cold single expressions, new basis/context cache misses, fresh processes; **measured**, high confidence for these inputs. | Low effort/risk; implemented. Next: prospective application traffic and another existing host, with startup and cache state recorded. Warm hits and retained storage do not improve. |
| **2. Bound retained cache bytes and share positional masks**, `bitset_backend.py:17,374,818`; `cm_ir.py:78,88`. Values depend on width/position, while maps depend on names; separate those identities. Compare byte-LRU before cost/frequency admission; [TinyLFU](https://arxiv.org/abs/1512.00727). | Long sessions, renamed/context bases, mixed sizes, revisions; potentially large memory benefit, M confidence, unknown trace-level speed benefit. | Medium effort; accounting must include bound templates and per-thread scratch. A 256-entry cache at k22 can retain 2.75 GiB of packed column payload alone. First run bounded name/width churn and a real access trace; retain canonical keys and test eviction/invalidation. No policy/default change here. |
| **3. Finish existing native batch successor**, `cmbench/comparative/gf2_native_slot_batch.py`, `native/cm_fused_slots_batch/`. One FFI call per residual width and reusable native workspace; transfer mechanism analogous to [DuckDB vector execution](https://duckdb.org/docs/current/internals/vector). | Repeated restrictions and sibling roots; pre-existing functional evidence, M confidence of end-to-end gain. | Existing work is preserved. Use its independently frozen prospective workload, scalar native/R2/CSE-flat controls, q1–q64, mixed widths, binding/copy/output cost and a new binary identity. Arbitrary-lane batching previously lost; this successor avoids that expanded lane representation. |
| **4. Keep compact results through smaller queries**, `cmbench/comparative/tasks.py`, `gf2_projection_optimized.py`, `recognition/gf2_decomposition.py`. Use count/SAT/witness/cofactor operations without mandatory full-vector delivery; [knowledge-compilation map](https://arxiv.org/abs/1106.1819), [dd implementation](https://github.com/tulip-control/dd). | Repeated configuration checks, equivalence, counting and hypothetical policy services; potentially changes scaling, H confidence in contract distinction, workload-dependent performance. | Medium/high effort. Run build+restriction+query ladders with native CUDD/SAT/d-DNNF where available. Count over disjoint factors needs a proof of independence and declared dead-variable multiplicity. Full-vector expansion is still charged when requested. |
| **5. Amortize ingress and preparation**, `cm_expr_serde.py:87`, `CompiledExpr`, `PreparedFlatEvaluation`, `comparative/fresh_persistence.py`. Retain validated DAG/program/session state and compact serialized artifacts; [DuckDB format separation](https://duckdb.org/docs/current/internals/vector). | Fresh processes, repeated roots and persistent sessions; high potential when import/decode dominates, M confidence in deployment benefit. | Medium effort; bounded lifetimes, schema/options identity and corruption checks required. Measure fresh build, fresh reload and resident q1/q64, including I/O, decode and cleanup. Do not replace safe DAG serialization with arbitrary executable deserialization. |
| **6. Restrict exact GF(2) acceleration to an activated algebraic task**, `recognition/gf2_anf_rank.py`, `gf2_decomposition.py`; packed elimination/M4RI, [implementation](https://github.com/malb/m4ri). | Rank-only queries and demonstrably compressible ANF/block decomposition; M confidence, potentially large kernel gains. | High integration effort; GF(2) algebra is applicable, floating-point low rank is not an exact substitute. Charge basis conversion and artifact construction. Prior ANF rank-only gain did not improve the complete screen; reproduce that task boundary before native integration. |
| **7. Revisit incremental compilation only on active independent edits**, `comparative/incremental_revision.py`, `cm_ir.py:285`. Dependency validation with unchanged-result propagation; [Rust red-green algorithm](https://rustc-dev-guide.rust-lang.org/queries/incremental-compilation-in-detail.html). | Version differences, edit sessions and policy revisions; unknown benefit, L/M confidence. | High effort, wrong-hit risk and retained graph costs. Existing radix prototype lost to persistent CM/CSE and hardware history admission stopped. A new active trace must precede development; compare cold/current-cache/red-green/CSE, charging hashing and validation. |
| **8. Stream/tile before adding hardware parallelism**, `bitset_backend.py:873`, `cm_parallel.py`, native executor. Bounded chunks, fused kernels and output streaming; [CUDA guidance](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html), [Sylvan](https://github.com/trolando/sylvan). | Large complete output or large symbolic state traversal; potential lower peak memory/earlier first chunk, L confidence of latency gain on current tasks. | High effort and a different streaming contract. First single-process tile sweep; only then thread/process/GPU trials with startup, transfers, synchronization, oversubscription and aggregate RSS. Native SIMD/ternary fusion must retain portable exact fallbacks. |
| **9. Research hierarchical symbolic sharing**, `recognition/variable_decomposition_experiment.py`, comparative symbolic arms; [CFLOBDD bounds](https://arxiv.org/abs/2406.01525), [2026 symbolic decomposition](https://arxiv.org/abs/2601.08354), [ZDD synthesis](https://arxiv.org/abs/2512.07018). | Hypothesized repeated hierarchical circuits, sparse set-family synthesis or bounded-width decomposition; L practical confidence, possibly substantial succinctness benefit. | High effort. Screen structural width and repeated subfunctions before conversion; benchmark compact compose/restrict/equivalence contracts. Theorems depend on ordering/structural parameters and give no general CM latency guarantee. |

Composition means exact Boolean operations over aligned variables; equivalence
may be a symbolic decision or a complete XOR vector, which have different
costs. The directional CM feature quotient is not semantic XOR. Related-root
union already has exact historical evidence; independent family generation is
not an edit trace. Existing applications include configuration-model slices,
hardware restrictions and revision/decomposition studies. Policy-service and
hierarchical-symbolic examples above are hypotheses, not demonstrated uses.

Generic key redesign, dense-copy fusion and an e-graph replacement remain
deferred under their measured profiles. [egg/egglog](https://egraphs-good.github.io/)
offer exact rewrite-space sharing and incremental analysis mechanisms, but a
heavy rewrite workload must first repay saturation and extraction. Broad
projection rewrites, concatenated query lanes, trace-specialized cofactor caches,
full-screen ANF routing and scalar threshold retuning retain their previous
negative dispositions. A feature/autotuning router needs distinct backend
headroom, cheap features, held-out regret/tail checks and cross-host transfer;
the stopped learned and memory selectors do not meet that condition. Sparse
numerical matrices and approximate tensor compression are not justified by the
word “matrix.”

**Reproduction and correctness.** New scripts use exclusive evidence-file writes;
choose a fresh output directory for another run. `freeze` copies the checkout's
current backend, so calling it after integration would make the improved code
the baseline. The following commands instead reuse the exact saved old backend
and fixtures and repeat the confirmation, environment and lifecycle comparisons
without changing the worktree. Source hashes and the original environment are
in the copied manifests; record any environment differences for another host.

```powershell
$evidence = 'docs\audits\2026-09-11-cm-performance'
$rerun = 'docs\audits\2026-09-11-cm-performance-rerun-001'
New-Item -ItemType Directory -Path $rerun -ErrorAction Stop
foreach ($name in @('baseline_bitset_backend.py', 'fixtures.json', 'freeze.json', 'candidate_manifest.json')) {
    Copy-Item -LiteralPath (Join-Path $evidence $name) -Destination $rerun
}
.\.venv\Scripts\python.exe -B scripts\cm_packed_mask_audit.py environment --output $rerun
.\.venv\Scripts\python.exe -B scripts\cm_packed_mask_audit.py confirmation --output $rerun
.\.venv\Scripts\python.exe -B scripts\cm_packed_mask_lifecycle.py --output $rerun
.\.venv\Scripts\python.exe -B scripts\cm_packed_mask_lifecycle.py --output $rerun --timing-only
.\.venv\Scripts\python.exe -B scripts\cm_packed_mask_query_controls.py --output $rerun
```

This repeat is not the historical development campaign and does not create its
missing development files. The exact original phase scripts are preserved
because the CSE control was strengthened before confirmation; see
`PROTOCOL-NOTES.md`. The separate verifier
checks the **saved campaign's** exact schedule, source snapshots, independent
Boolean-vector hashes, scalar counts and paired statistics. It writes an
exclusive receipt, so replay into a copy without the old receipt:

```powershell
.\.venv\Scripts\python.exe -B scripts\cm_packed_mask_verify.py --output <evidence-copy>
.\.venv\Scripts\python.exe -B -m pytest tests\test_packed_mask_construction.py tests\test_bitset_backend.py tests\test_bitset_cse.py tests\test_prepared_flat_evaluation.py tests\test_bitset_engine_policy.py tests\test_context_caches.py -q -p no:cacheprovider
```

`verification_all_sessions.json` verifies **3,780 cold sessions / 102,060
ordered relation outputs**, with zero source, schedule, output-hash or checked
summary mismatches. Another 3,780 warm sessions were asserted exact in the
campaign; their outputs were not independently stored. The bootstrap utility
is shared with the verifier, so statistical code has not received an independent
implementation audit. Counts add 288 exact timing rows and 32 memory rows.
New tests cover every assignment column through k20, reordered and unused axes,
fixed contexts, all Boolean operators, eviction, immutable cache identity and
concurrent readers; existing high-sharing/zero-result and guard tests also pass.

Focused tests: **67 passed**. Additional IR, persistence, serialization,
restricted evaluation, ordering and output-guard checks: **173 passed plus four
subtests**, with two temporary-directory permission errors; both blocked tests
passed on retry (**2 passed**). Total: **242 passed plus four subtests**. No
semantic test failure occurred. The entire repository suite and historical paid
campaigns were not rerun. Review `TEST-COMMANDS.md` for the exact broader command.

The strongest next local work is a byte-accounted cache/lifecycle trace, followed
by confirmation of the already separate native-batch successor. Larger symbolic,
incremental or hardware work should follow a workload that activates its cost,
with the improved shared BitSet/CSE controls included from the start.
