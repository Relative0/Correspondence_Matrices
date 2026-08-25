# CM Deep Performance Optimization Backlog

This backlog begins after the 2026-08-24 audit. Priorities assume the current complete exact-output contract and accepted `live_k<=16` evidence.

Correction (2026-08-25): B2 and EPFL are reused selection-validation data,
not untouched held-out data. Any future selector acceptance requires a newly
frozen untouched validation corpus.

## Ready to implement or validate locally

### DP-R1 — Cross-machine selector confirmation

- Current state: automatic words crossover changed from `k>=6` to `k>=16`.
- Evidence: zero `>=2x` routing regrets in final BX1 tuning and B2+EPFL reused-validation replay; old rule had 38-39 catastrophic tuning rows and 200 reused-validation rows per arm.
- Next: run the unchanged final harness on one materially different CPU/OS with the same corpus hashes.
- Gate: exact equality, no new catastrophic tail, and cluster-bootstrap geomean regret close to 1. Confirm on a newly frozen untouched validation corpus; do not tune on that corpus.
- Dependency/approval: access to another machine only; no new software required.

### DP-R2 — Explicit temporary-memory contract

- Current state: output-budget APIs can limit temporary memory, but some production defaults remain `None`. The audit harness is fail-closed and used 8 MiB.
- Evidence: an early protocol-violating raw EPFL replay approached 2 GiB; final harness recorded 10 protocol skips and 4 budget refusals.
- Next: specify default local and remote byte budgets, refusal schema, override rules, and whether existing unbounded callers retain an opt-out.
- Gate: exact refusal tests before allocation, no partial artifact, correct status propagation, local/remote parity.
- Risk: a default can newly refuse existing callers. This is an API/policy decision, not a safe silent edit.

### DP-R3 — Compact interning-key/node prototype

- Current state: interning is the largest measured compile phase at roughly 21-25%; preparation remains about 4x the fair comparator.
- Prototype: replace only the internal key representation or reduce transient tuple/set allocation while keeping `CMNode` semantics and structural hashes unchanged.
- Gate: B2 and EPFL exact packed hashes; cold compile paired per expression; allocations and retained cache bytes; no regression on high-sharing B3 cases.
- Stop rule: reject effects within ordinary run-to-run noise or any increase in collision/invalidation ambiguity.

### DP-R4 — Benchmark-tool consolidation

- Current state: `scripts/cm_deep_performance_audit.py` provides per-phase, paired-kernel, memory, refusal, cluster-CI, and environment sidecars; the normal benchmark CLI does not expose all fields.
- Next: reuse its timing helpers in the established audit tooling without altering production evaluation.
- Gate: schema documentation, refuse-overwrite tests, smoke under 30 seconds, no hardware assertion in unit tests.

## Needs a real workload

### DP-W1 — Byte-budgeted structural cache

Required trace fields:

- structural key and compiler/policy version;
- artifact bytes and retained bytes;
- hit/miss/eviction and lookup/serialize time;
- process/cold-start boundary;
- expression/version/family identifier;
- subsequent evaluation count and output type.

Evaluate entry LRU against byte-LRU and a size-aware admission policy. Report working-set curves and RSS plateaus. Do not implement TinyLFU or disk persistence from synthetic hit ratios alone.

### DP-W2 — Incremental compilation across edits

Capture actual edit operations and affected structural regions. Compare:

1. cold CM compile;
2. current structural subtree cache;
3. a dependency-query prototype modeled after red-green/Salsa;
4. a hash-consed CSE-flat incumbent.

Include stable-hash time, invalidation, retained memory, and wrong-hit adversarial tests. A family of independently regenerated expressions is not automatically an edit trace.

### DP-W3 — `k=13..15` selector corpus

Only pursue if production has material volume in the gap. Freeze a tuning corpus with those exact supports and a separate circuit-held-out corpus. Candidate features are `k`, executed operations, peak live word buffers, and warm environment state. Keep selector overhead below the saved time and validate schedule stability.

### DP-W4 — Repeated partial contexts

Needed workload dimensions: original/remaining support, context overlap/locality, phase changes, number of repeated queries per context, output kind, BDD manager lifetime, and cache budget. Compare BitSet full/restricted, CM compile-once, and CUDD build-once/restrict with construction, restriction, and extraction kept separate.

### DP-W5 — Related expression families

Current shared-block synthetic families improve CM only 1.18-1.39x and remain far behind BitSet. Reopen only with real revisions or policy families. Include family generation/loading outside timed windows and compare total task-matched work.

## Needs external dependencies or hardware

### DP-X1 — Native/JIT word fusion

- Dependency: Numba/LLVM or a compiled extension; installation/toolchain approval required.
- Preconditions: a real repeated batch where word-kernel time dominates preparation and output conversion.
- Candidate: fuse selected binary/ternary operations into preallocated `uint64` buffers; include AVX2 baseline and optional AVX-512 ternary path.
- Required comparison: current NumPy words, flat bigint, compile/warmup, dispatch, copying, conversion, and memory.
- Semantic rule: do not JIT arbitrary Python bigints as fixed-width integers.

### DP-X2 — CUDD cross-machine/context frontier

- Dependency: a confirmed working `dd.cudd` build on the benchmark machine.
- Purpose: task-matched symbolic build/restrict/query frontier, not complete-output kernel comparison.
- Record fixed/dynamic orders, manager reuse, node count, cache/reorder statistics, build, restriction, and exhaustive extraction separately.

### DP-X3 — Large chunk/stream prototype

- Dependency: a caller that accepts streaming/chunked output rather than one packed integer.
- Benefit sought: bounded peak memory, not asymptotically less output work.
- Compare single-process tiling before multiprocessing/GPU. Add hardware only when chunk computation amortizes transfer/startup and aggregate memory remains bounded.

## Theoretically blocked under the current artifact

### DP-T1 — Removing exponential complete-output size

Returning every value of an arbitrary Boolean function over `k` live variables requires `2^k` bits. Packed storage/work is `Omega(2^k/w)` words. Any sub-exponential BDD, factorization, SAT, or oracle result is a different output artifact until expanded.

### DP-T2 — Universal Kronecker/tensor factorization

Kronecker structure exists for decomposable independent variable blocks. Arbitrary Boolean compositions are not guaranteed to retain it; general factor discovery and reconstruction do not beat the output lower bound. Approximate/numerical low-rank decompositions violate exact semantics.

### DP-T3 — Quotient as semantic XOR

CM directional feature quotient is not semantic XOR. It must never be used as an equivalent semantic-difference timing arm.

### DP-T4 — Formal global canonical equality from current keys

Current normalization and structural digests provide engineering identity under documented rules and collision assumptions. They do not establish a theorem that every semantically equal Boolean expression maps to one global CM object.

## Tested and rejected for now

| ID | Candidate | Evidence | Reopen condition |
|---|---|---|---|
| DP-N1 | Automatic words at `k=6` | 2.06/2.74 raw geomean regret on tuning/reused validation; 39/200 catastrophic rows | Never without new paired evidence |
| DP-N2 | Interpolate crossover at `k=13` | BX1 has no gap samples; one replay showed a 2.18x reused-validation raw misroute | Dedicated frozen `k=13..15` tuning corpus |
| DP-N3 | Optimize CM/CSE-flat residual | B1/E3 parity; corrected B2/B4 bare CM/CSE-flat 0.909 overall and 0.979 at `k=16`, but wrapper/preparation still dominate | Replicated task-matched end-to-end evidence where the structural reduction repays preparation |
| DP-N4 | Broad pass fusion | Preparation time distributed; no dominant duplicate traversal | Allocation/profile shows one fused boundary is material |
| DP-N5 | E-graph replacement | Rewrite/canonicalize not dominant; no downstream kernel benefit established | Real heavy rewrite/edit stream and bounded extraction |
| DP-N6 | New cache admission policy | No realistic size/access trace; synthetic cache gains do not beat BitSet | DP-W1 trace exists |
| DP-N7 | CM partial-context dominance | Cached CM helps itself but loses to BitSet/ROBDD at tested sizes | DP-W4 workload crosses measured break-even |
| DP-N8 | Multiprocessing | Startup/serialization/small chunks do not amortize; memory amplification | Kernel-dominant chunk workload |
| DP-N9 | GPU/distributed | Transfer, output size, and current guard dominate | Streaming API plus much larger measured kernels |
| DP-N10 | Sparse numerical matrix representation | Bit-packed truth values are not a sparse linear-algebra workload | Proven extreme structured sparsity with task-matched ops |

## Priority order

1. Agree and implement temporary-memory policy.
2. Validate selector on a second machine if it is being productized.
3. Obtain real cache/version/context traces.
4. Prototype compact interning only if preparation latency matters to the actual service.
5. Consider native/JIT kernels only after repeated batches make kernels dominant.
