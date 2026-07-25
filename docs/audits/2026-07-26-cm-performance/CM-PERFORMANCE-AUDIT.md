# Correspondence Matrix Performance and Optimization Audit

Date: 2026-07-26
Repository: `CM_Computation`
Audited `HEAD`: `6419b21909b7994cdec0aae04a3c1eaba357bc75`
Audited state: the existing dirty V4 working tree plus the changes listed in this audit

## Executive summary

The CM implementation is an exact Boolean truth-function engine, not a numerical
matrix-multiplication algorithm. Its unavoidable boundary is explicit output:
with \(k\) live output variables, any complete result has \(2^k\) bits, and a
dense CM has \(2^k\) bytes at `bool` precision. The current no-reinflate and
reduced-output paths correctly avoid some unnecessary expansion, but they do not
change that lower bound when a complete output is requested.

This audit found and fixed four high-confidence issues:

1. **P0 concurrent result corruption.** The words evaluator reused mutable NumPy
   scratch arrays across threads. The threaded remote worker could therefore
   return corrupt results for concurrent identical requests. A synchronized
   12-thread probe failed 12/12 calls before the fix and passed 600/600 after it.
   Scratch is now cached per thread.
2. **P0 misleading large-\(n\) correctness status.** A reduced large-\(n\) run
   could report `cm_hybrid_no_reinflate_ok=True` when neither an exact oracle nor
   sampling had run. Unvalidated results now report `None`; sampled mismatches
   force `False`.
3. **P0 incorrect `full-vars` partial-context reference.** Reference generation
   overwrote fixed context values while enumerating output axes. Fixed values
   now remain fixed and are broadcast across their nominal axes.
4. **P1 quadratic wide-operator compilation.** AND/OR complement detection
   linearly rescanned all prior operands. A 512-term profile made 1,296,640
   `_is_negation_of` calls. Constant-time set lookup removed that scan while
   preserving canonical results.

The controlled wide-operator benchmark, using the same script hash, warmups,
11 repetitions, validation, and allocation instrumentation on both sides,
measured:

| Case | Before median | After median | Speedup | Result signature |
|---|---:|---:|---:|---|
| AND, 128 operands | 22.063 ms | 14.105 ms | 1.56× | identical |
| AND, 256 operands | 58.606 ms | 31.033 ms | 1.89× | identical |
| AND, 512 operands | 145.749 ms | 64.893 ms | 2.25× | identical |
| OR, 512 operands | 112.321 ms | 55.248 ms | 2.03× | identical |

An uninstrumented cProfile comparison of five 512-term AND compiles improved
from 1.389 s to 0.280 s (4.96×) and reduced calls from 3.01 million to 0.42
million. The improvement grows with arity; it is deliberately not presented as
a universal end-to-end CM speedup.

The final regression gate passed: **209 tests in 67.80 s**. All new correctness
checks use exact integer/array equality; no numerical tolerance was needed.

## Scope and provenance

The repository was not clean when the audit began. Existing uncommitted V4 work
already changed `bitset_backend.py`, `cm_bench.py`, `cm_ir.py`, configuration,
ROBDD code, tests, reports, and generated deliverables. Those changes were
preserved. The current working tree, rather than `HEAD` alone, is the
authoritative pre-audit implementation.

The controlled compile comparison records exact source hashes:

- before `cm_ir.py`: `32469faa0b4e9cae4f62cffa3dd3ca08154db62a0e21e380d3ff5d2ab0b6a0c2`
- after `cm_ir.py`: `1d1e8d30de765a87142cd59ebf01c8df6fa7f82486f107fb866de0fc9fc6ea41`
- comparison script on both runs:
  `019470b64ae3028e124398bac141ed283eec5faf02dfd65d03843e3882630235`

The final benchmark script adds corrected Windows RSS collection and batching
for useful CPU-time resolution. Those later files are final-state scaling
evidence, not inputs to the compile before/after claim.

No secret files were read. No network, live RunPod worker, GPU, container, WSL,
or native CUDD run was used. Historical data were reviewed but not silently
mixed into new controlled comparisons.

## Current architecture and execution flow

The principal default flow is:

```text
CLI / JSONL corpus / seeded generator
  -> Boolean AST (Var, Not, And, Or, Xor, Imp, Eqv)
  -> optional exact eval_expr_tt reference (normally n <= 16)
  -> CMIRBuilder canonicalization + interning
  -> CMNode DAG with ordered live-variable tuples
  -> execution policy
       dense NumPy / partial hybrid / packed bigint / uint64 words
       optional pair experiment / process-parallel dense combine
  -> dense CM, truth-table vector, or packed integer
  -> exact or sampled validation
  -> pandas aggregation
  -> raw CSV, summary CSV, optional HTML
```

### Authoritative files and symbols

| Area | Current implementation |
|---|---|
| CLI and benchmark orchestration | `cm_bench.py`: `main`, `run_bench`, `time_backends_on_expr` |
| Boolean AST and exact truth-table oracle | `cm_exprlib.py`: AST dataclasses, `eval_expr_tt` |
| CM IR and canonicalization | `cm_ir.py`: `CMNode`, `CMIRBuilder`, `compile_expr_to_cm_ir` |
| Dense/hybrid materialization | `cm_ir.py`: `materialize_ir`, `materialize_cm` |
| Packed/no-reinflate result | `cm_ir.py`: `materialize_hybrid_no_reinflate` |
| Flat and words execution | `bitset_backend.py`: `FlatProgram`, prepared evaluation, `_eval_words` |
| Engine selection | `cmbench/backends/bitset_engine.py` |
| Layout/alignment | `cm_normalize.py` and `cm_ir.align_to_vars` |
| Standard wrapper | `cm_build.py` |
| “Lazy” wrapper | `cm_build_lazy.py`; it now uses the shared IR and is not a separate core algorithm |
| Pair experiment | `cm_build_pair.py` |
| Dense process-parallel path | `cm_parallel.py` |
| Remote protocol and worker | `cm_remote_executor.py`, `cm_runpod_protocol.py`, `cm_remote_worker.py` |
| ROBDD/CUDD adapter | `cmbench/backends/robdd_dd.py` |
| Partial contexts and families | `cmbench/expr/partial_contexts.py`, `cmbench/expr/families.py`, runners in `cm_bench.py` |
| Result aggregation/reporting | `cmbench/results/*`, `cmbench/reporting/*`, and remaining monolithic code in `cm_bench.py` |

`Updates to Integrate/`, the ignored nested `Correspondence_Matrices/` checkout,
old root benchmark CSVs, and historical deliverable scripts are not the current
implementation.

### Data representations

- AST: immutable Python dataclasses.
- IR: frozen `CMNode` objects, interned by canonical structural keys.
- Dense CM: NumPy `bool` arrays, with axes aligned by variable name and finally
  reshaped to row/column layout.
- Packed path: one Python integer whose bit positions are truth-table rows.
- Words path: little-endian NumPy `uint64` arrays plus a compiled `FlatProgram`
  and scratch buffers.
- No-reinflate output: packed integer or one-dimensional `uint8` truth table,
  optionally reduced to proven-live variables.
- Remote input/output: JSON protocol with serialized AST and a packed or vector
  result.
- Benchmark input/output: seeded synthetic ASTs or SHA-validated JSONL corpus;
  CSV and HTML reports.

### Preprocessing and postprocessing costs

Preprocessing includes imports, optional-backend discovery, expression
generation/filtering, truth-table generation, layout selection, and compilation.
Postprocessing includes truth-table conversion, correctness checks, diagnostics,
pandas aggregation, CSV serialization, and HTML rendering.

The existing timing columns do not all represent the same artifact or boundary.
For example, symbolic BDD construction is not comparable to complete packed
truth-function production. The V4 timing descriptors and paired aggregation
helpers improve this, but the rule is not yet enforced across every production
summary.

## Algorithm reconstruction

For an expression DAG with \(u\) unique IR nodes, \(m\) operands in a flattened
associative operator, \(k\) live variables, and machine word width \(W=64\):

1. Compile the AST bottom-up.
2. Flatten associative AND/OR/XOR nodes.
3. Sort commutative operands by canonical structural key.
4. Apply exact Boolean rewrites: constants, duplicates, complements, XOR
   parity, implication/equivalence identities.
5. Intern structurally identical nodes and compute sorted live-variable tuples.
6. Evaluate each unique node, aligning operand axes as needed.
7. Produce the requested full or reduced explicit output.

### Time and space complexity

| Phase | Time | Additional space | Notes |
|---|---|---|---|
| IR compile | structure-dependent; sorting is at least \(O(m\log m)\) for a wide commutative node | \(O(u+m)\), excluding structural keys | The removed complement scan added \(O(m^2)\) work to AND/OR |
| Dense materialization | worst case \(O(u2^k)\) | worst case \(O(p2^k)\) live temporaries | `p` depends on memoization and expression liveness |
| Python bigint packed evaluation | approximately \(O(u2^k/W)\) limb work | masks/intermediates proportional to \(2^k\) bits | Python bigint constants and masks are still monolithic |
| NumPy words evaluation | \(O(u2^k/64)\) word operations | environment about \(k2^k/8\) bytes plus scratch about \(b2^k/8\) | `b` is the scratch-buffer coloring count |
| Dense final CM | \(O(2^n)\) copy | \(2^n\) bytes | Nominal axes may include dead variables |
| Packed final result | \(O(2^k/64)\) plus final copy to Python int | at least \(2^k/8\) bytes | Reduced output uses live `k`, full output uses nominal `n` |

Truth-table density is not exploited by the current exact-output formats. A
truth function with one true row still occupies the same dense or packed output
width as a balanced function. Sparse storage would only help workflows that can
accept a sparse artifact and different query costs; it cannot silently replace
the current output contract.

### Structural assumptions

- Assignment order is exact and MSB-first (`x0` changes slowest).
- Commutative operands are canonicalized; implication preserves order.
- Live variables are sorted naturally (`x2` before `x10`).
- The pair-token representation uses a different local truth ordering and
  explicitly bridges it when materializing.
- Exact Boolean operations have no floating-point conditioning issue.
- Full explicit output is exponential even when compilation is compact.

## Correctness baseline

The authoritative semantic oracle is `cm_exprlib.eval_expr_tt`, not another CM
execution path. It exactly enumerates all assignments for all six Boolean
operators. The normal full reference is limited to `n <= 16`; larger runs must
use reduced exact output, independent assignment sampling, or report validation
as unavailable.

Final regression result:

```text
python -m pytest -q
209 passed in 67.80s
```

The repository virtual environment has the benchmark runtime but initially
lacked pytest. `requirements-dev.txt` now declares the existing test runner.
Tests were run with system Python 3.10.11; performance measurements used the
project `.venv` Python 3.13.5.

New coverage includes:

- wide AND/OR operand retention, complement order independence, and exact output;
- raw-AST and CM-node words evaluation under synchronized thread contention;
- large-\(n\) unvalidated, sampled-pass, and sampled-fail status behavior;
- `full-vars` partial references with fixed variables broadcast correctly.

Acceptance is exact integer equality or `np.array_equal`. Numerical deviation is
recorded as a mismatch count and was zero in every completed benchmark case.

## Benchmark and profiling methodology

Full details and commands are in `CM-BENCHMARK-RESULTS.md`.

The new `scripts/cm_performance_audit.py`:

- isolates compile, packed execution, dense materialization, and reduced-output
  cases in fresh subprocesses;
- uses deterministic expressions;
- records wall and CPU time, median, MAD, p10/p90, throughput, GC collections,
  tracemalloc peaks, Windows peak working-set deltas, source hashes, dependency
  versions, thread settings, and exact result signatures;
- supports `smoke`, `local`, and opt-in `large` suites;
- uses warmups and repeated trials;
- validates every case against an independent exact oracle or a deterministic
  structural signature;
- keeps raw JSONL separate from summaries;
- performs no hardware-sensitive pass/fail assertion in the normal test suite.

Short operations are batched in final-state runs so Windows process CPU time is
not always quantized to zero. The before/after compile comparison predates that
batching and uses the same unbatched script on both sides.

## Profiling results and hotspots

### Whole pipeline

The controlled CLI profile completed 15 balanced-all-variable cases at
`n=8,12,16`, five cached executions per case, and wrote raw/summary CSV:

| Component | cProfile cumulative time | Interpretation |
|---|---:|---|
| Total process | 4.860 s | imports through CSV completion |
| Import machinery | 3.712 s | dominant cold-start cost |
| Backend discovery | 1.501 s | overlaps import time |
| `run_bench` | 1.210 s | generation, backends, aggregation, output preparation |
| pandas aggregation | 0.718 s | material for small smoke runs |

Cold startup is therefore a developer-iteration bottleneck, not a CM kernel
bottleneck. `cm_bench.py` imports most workflows and optional backends before it
knows which flags disable them, then backend discovery imports optional modules
again. Lazy workflow imports are justified but were deferred because this is a
broad compatibility refactor and cannot be credited as a core algorithm gain.

### Wide associative compile

Before:

```text
5 builds, 1.389 s, 3,011,731 calls
make_and: 1.351 s
builtins.any: 1.068 s
_is_negation_of: 1,296,640 calls
```

After:

```text
5 builds, 0.280 s, 418,451 calls
make_and: 0.244 s
no repeated any/_is_negation_of scan
```

The controlled instrumented scaling exponent from width 32 to 512 changed from
approximately 1.26 to 1.02 for AND, and from 1.15 to 1.07 for OR. These are
empirical exponents over this range, not formal complexity proofs.

### Cold versus warm execution

With no warmup, the first packed evaluation paid mask/environment construction:

| Case | First call | Median of next six | First/warm |
|---|---:|---:|---:|
| mixed `n=8` | 22.359 ms | 0.130 ms | 171.9× |
| ambient 32, live 5 reduced output | 15.253 ms | 0.141 ms | 108.1× |
| dense NumPy `n=8` | 1.908 ms | 0.817 ms | 2.33× |

This validates the need to separate first-touch latency from sustained
throughput. It also shows why process-local caches cannot be “warmed” by a
different prior Python process.

## Scalability and memory

Final opt-in measurements remained exact through a complete one-million-bit
packed output at `n=20` and a 262,144-element dense output at `n=18`:

Wall/throughput values below are from the batched final run; allocation/RSS
values are from the companion one-operation run so batching does not inflate
memory peaks.

| Case | Median wall | Median throughput | Traced peak | Peak working-set delta |
|---|---:|---:|---:|---:|
| packed mixed `n=8` | 0.068 ms | 14,700/s | about 5 KiB | about 0.1 MiB |
| packed mixed `n=16` | 0.145 ms | 6,900/s | about 31 KiB | about 1–2 MiB |
| packed mixed `n=18` | 0.212 ms | 4,700/s | about 106 KiB | about 7 MiB |
| packed mixed `n=20` | 0.512 ms | 1,950/s | about 407 KiB | about 30 MiB |
| dense NumPy `n=18` | 2.932 ms | 341/s | about 1.5 MiB | about 6 MiB |
| compile AND width 2,048 | 263.040 ms | 3.8/s | about 3.4 MiB | about 7 MiB |

Windows working-set deltas are page-granular and include allocator first-touch;
they are useful feasibility signals, not byte-exact allocation attribution.
Before/after files have authoritative tracemalloc data but null RSS because the
initial Windows handle declaration was incorrect; final files contain the
corrected RSS telemetry.

The first practical limiter is output and cached-mask memory, not arithmetic
precision. Important retained caches are bounded by entry count rather than
bytes:

- bigint variable environments: 256 entries;
- words environments: four entries (an `n=24` entry is already large);
- bound flat inputs: 64 entries per program;
- compiled IR: 4,096 object-identity entries;
- persistent structural IR: 16,384 entries;
- thread-local word scratch: two widths per program per live thread.

The thread-local race fix necessarily permits one scratch set per concurrently
executing thread. It preserves throughput but changes scratch memory from
per-program to per-program-per-active-thread. A future worker concurrency cap
and byte budget should make that policy explicit.

## Parallelism and hardware utilization

- Dense process parallelism exists in `cm_parallel.py`, with optional shared
  memory and cached process pools.
- Historical stress testing found activation in 0/135 primary cases and no
  consistent gain when forced. Serialization, process startup, shared-memory
  setup, and small chunk sizes dominate ordinary explicit workloads.
- The packed words path uses NumPy vectorized bitwise kernels. It has no GPU,
  distributed, or native-extension path.
- The remote worker uses `ThreadingHTTPServer`. Independent requests can run
  concurrently; the fixed words scratch is isolated per thread.
- No hard-coded worker count was added. The process-parallel path remains
  parked until a representative workload actually amortizes its overhead.
- GPU acceleration is not justified by current evidence: explicit output and
  host/device transfer remain exponential, and existing CPU kernels are
  sub-millisecond through the measured packed range.

## Numerical stability and reproducibility

The core algorithm is Boolean and exact:

- Python integers, `uint64` words, `uint8` truth tables, and NumPy Boolean arrays
  do not introduce rounding drift.
- NOT/IMP/EQV results are clipped or represented at the intended finite output
  width.
- Output comparisons use exact equality.
- Structural cache keys use deterministic BLAKE2b digests; canonical operand
  ordering is deterministic.
- Random benchmark generation uses explicit seeds.

The principal reproducibility risks are not floating-point:

- mutable shared state under concurrency (fixed for words scratch);
- process-local caches and cold/warm ambiguity;
- synthetic generator drift across dependency versions;
- a dirty working tree and uncommitted V4 corpus;
- historical summaries that pool repeated ambient bindings as if they were
  independent formulas;
- no CI matrix across Windows/Linux/macOS and Python/dependency versions.

The V4 corpus has 49 records but fewer unique expressions; controlled live
support 8/12/16 each repeats one expression across seven ambient sizes. Future
inference must cluster by expression hash and add genuinely independent
formulas.

## Prioritized findings

| ID | Priority | Finding | Evidence/root cause | Change and expected impact | Risk/scope/dependencies | Validation | Disposition |
|---|---|---|---|---|---|---|---|
| CM-P0-01 | P0 | Concurrent words corruption | Shared `FlatProgram.word_scratch`; NumPy releases GIL; threaded worker | Per-thread scratch prevents cross-request overwrite | Extra scratch per active thread; no new dependency | 12/12 failed before, 600/600 passed after; raw/CM pytest paths | **Implemented** |
| CM-P0-02 | P0 | Unvalidated large-\(n\) output reported `True` | Status defaulted to success without exact/sampled oracle | `None` until validation; samples control status | Output schema values become more honest; format unchanged | pass/no-oracle/mismatch tests plus integration suite | **Implemented** |
| CM-P0-03 | P0 | `full-vars` partial reference ignored fixed context | Enumeration overwrote context values | Preserve fixed bindings and broadcast axes | Corrects affected benchmark interpretation | exact small reference/bitset tests | **Implemented** |
| CM-P1-01 | P1 | AND/OR complement scan quadratic in flattened arity | 1.30M complement calls in 512-term profile | Set membership makes complement lookup expected \(O(1)\) | Small local rewrite; no dependency | exact signatures, truth tables, 2.03–2.25× at width 512 | **Implemented** |
| CM-P1-02 | P1 | Some equivalence/dense entry points lack a centralized output budget | Direct no-reinflate calls can request complete exponential output | Shared representation-aware output/temporary-byte budget with typed decisions | Additive API/protocol fields and bounded defaults | dense/packed boundaries, refusal, reduction, equivalence, remote round trips, 223-test gate | **Implemented in continuation** |
| CM-P1-03 | P1 | Large caches are entry-bounded, not byte-bounded | One high-\(k\) entry can dwarf many small entries | Track bytes, expose telemetry, cap/evict by bytes | Requires lifecycle and thread policy | cold/warm memory and eviction tests | Deferred |
| CM-P2-01 | P2 | CLI cold start dominates smoke runs | 3.71/4.86 s in imports; disabled backends still imported | Lazy-load workflow-specific and optional modules | Broad import/API compatibility risk | CLI/schema/full suite and startup A/B | Deferred |
| CM-P2-02 | P2 | Main benchmark telemetry remains incomplete | No CPU/RSS/GC/env sidecar or warmup control in normal CSV workflow | New isolated audit tool supplies reproducible core tiers | Does not yet replace all workflow runners | raw JSONL, exact hashes, smoke/local/large | **Partially implemented** |
| CM-P2-03 | P2 | Slow full suite and undeclared test environment | `.venv` lacked pytest; subprocess integration tests dominate | Declare `requirements-dev.txt`; document a fast core slice | None at runtime | 209-test final gate | **Implemented in part** |
| CM-P2-04 | P2 | Prepared flat evaluation is not the normal repeated route | Existing preparation wins at small support but is neutral/slower later | Integrate only behind measured support/repeat policy | Cache invalidation and crossover risk | paired cold/prep/repeat break-even surface | Deferred |
| CM-P2-05 | P2 | Dense multiprocessing usually does not activate or pay back | Existing 135-case stress and current workload sizes | Keep explicit opt-in; do not tune a universal worker count | None | rerun only for demonstrably large kernels | Rejected for now |
| CM-P3-01 | P3 | Tiled/streaming words, GPU, and distributed strategies are unvalidated | Current output is monolithic; design note only | Prototype only for workflows accepting chunks/queries | New APIs/hardware and substantial validation | output-equivalence, transfer, memory, end-to-end task | Research |
| CM-P3-02 | P3 | No real independent workloads or same-environment CUDD downstream campaign | Current evidence is synthetic and platform-split | Freeze public datasets and compare task-matched artifacts | External datasets/infrastructure | pre-registered, clustered, cross-machine campaign | Research |

The detailed unimplemented backlog is in `CM-OPTIMIZATION-BACKLOG.md`.

## Implemented changes

### Constant-time complement detection

`CMIRBuilder.make_and` and `make_or` now maintain:

- `seen`: all retained operands;
- `negated_bases`: bases of retained NOT operands.

For a new NOT node, its base is checked in `seen`; for a non-NOT node, the node
is checked in `negated_bases`. This is exactly equivalent to the previous pair
predicate but avoids scanning `out` for every operand.

### Thread-safe word scratch

`FlatProgram` now owns a `threading.local()` scratch cache. The immutable word
plan and read-only environment remain shared; mutable operation buffers are
thread-isolated. This preserves repeated-evaluation reuse within a request and
allows independent requests to execute concurrently.

An interleaved single-thread microprobe found the thread-local holder within
about 4% of a shared namespace at `n=8` and at parity at `n=12,16`; this is
illustrative, not a formal performance claim.

### Honest large-\(n\) validation status

The benchmark no longer treats successful execution as proof of correctness.
An exact comparison sets the status directly. If exact validation is
unavailable, zero-mismatch independent sampling may set `True`; any sampled
mismatch sets `False`; otherwise the status remains `None`.

### Correct fixed-context reference

In `full-vars` mode, reference enumeration no longer changes variables present
in the fixed context. Their nominal axes repeat the conditioned function,
matching CM and bitset fixed-evaluation semantics.

### Reproducible tooling and developer setup

- Added `scripts/cm_performance_audit.py`.
- Added machine-readable raw and summary data in this directory.
- Added `requirements-dev.txt` for the existing pytest suite.
- Added 15 regression tests without hardware-dependent timing assertions.

### Central explicit-output budget

The continuation added `cmbench/output_budget.py` and applied it to dense and
no-reinflate materialization, reusable compiled evaluation, benchmark
workflows, equivalence/operator-difference paths, and remote execution.
Admission is representation-aware and occurs before the explicit allocation.
Full output is preferred; reduced output requires explicit permission and must
fit independently; otherwise a typed `OutputBudgetExceeded` refusal is
returned at workflow boundaries. Direct APIs are bounded at 256 KiB to retain
the supported dense `n=18` parallel path. Benchmark and remote defaults retain
the stricter 64 KiB and legacy 16-variable policies. See
`OUTPUT-BUDGET-CONTINUATION.md`.

## Rejected or inconclusive experiments

- **Universal end-to-end speedup:** rejected. The measured change targets wide
  compile canonicalization. Packed evaluation and dense materialization were
  outside its causal path and varied within short-run platform noise.
- **RSS before/after comparison:** inconclusive. The initial Windows API handle
  declaration made RSS null in the controlled before/after files. Final-state
  RSS is valid; allocation before/after remains available through tracemalloc.
- **Thread-local latency regression claim:** inconclusive from separate
  subprocess medians. An interleaved holder probe was near parity, and the
  correctness fix is mandatory regardless.
- **Naive multiprocessing:** rejected for current workloads based on existing
  activation and overhead evidence.
- **GPU/distributed/native rewrite:** rejected for implementation now. No
  realistic workload demonstrates that transfer/setup costs are amortized.
- **Sparse truth-table replacement:** rejected as a silent default. It changes
  the artifact and query complexity and would not preserve current output
  semantics.
- **Approximation or reduced precision:** rejected. Boolean output is already
  exact and bit-packed; approximation would change semantics.
- **`n=0` behavior:** deferred rather than guessed. Configuration currently
  accepts zero, while generators and the AST lack a clear constant-only
  contract.

## Remaining risks and recommended next steps

1. Add byte-based accounting and eviction for environment, IR, bound-input, and
   thread-local scratch caches.
2. Add bounded remote-worker concurrency and aggregate memory admission.
3. Freeze a distinct-expression corpus with expected truth digests and cluster
   statistics by expression hash.
4. Extend corpus replay to equivalence, partial-context, family, and operator
   workflows.
5. Refactor CLI imports lazily and measure cold startup before/after without
   changing benchmark artifacts.
6. Define or reject `n=0` explicitly.
7. Add CI on Windows and Ubuntu with supported Python/minimum-current dependency
   combinations; run native CUDD only where positively identified.
8. Prototype tiled output only for an explicit streaming/query API, not as a
   silent replacement for complete packed output.
9. Use real EDA, policy/configuration, and compiler-analysis workloads before
   making general structural-layer performance claims.

## Artifact index

- `CM-BENCHMARK-RESULTS.md`: controlled results, commands, and limitations.
- `CM-OPTIMIZATION-BACKLOG.md`: ordered unimplemented work.
- `FINAL-IMPLEMENTATION-SUMMARY.md`: concise implementation handoff.
- `OUTPUT-BUDGET-CONTINUATION.md`: resource-budget contract and verification.
- `NEXT-AGENT-IMPLEMENTATION-PROMPT.md`: ready-to-run cache/concurrency handoff.
- `benchmark-manifest.json`: machine-readable artifact roles and provenance.
- `before_raw.jsonl`, `before_summary.json`: pre-optimization compile baseline.
- `after_raw.jsonl`, `after_summary.json`: same-script post-compile comparison.
- `final_batched_large_raw.jsonl`, `final_batched_large_summary.json`: final
  sustained wall/CPU scaling and correctness data.
- `final_large_raw.jsonl`, `final_large_summary.json`: final one-operation
  allocation and RSS data.
- `final_cold_warm_raw.jsonl`, `final_cold_warm_summary.json`: first-touch versus
  warm-cache observations.
- `baseline_pipeline_raw.csv`, `baseline_pipeline_summary.csv`,
  `baseline_pipeline.prof`: whole-pipeline baseline.
- `baseline_wide_compile.prof`, `after_wide_compile.prof`: core cProfile A/B.
