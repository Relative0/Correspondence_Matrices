# CM Deep Performance Optimization Backlog

This backlog starts from the 2026-08-25 audited tree. It assumes exact complete-output semantics, the existing fail-closed budget/guard, and the evidence-role correction that BX1 is tuning while B2/EPFL are reused validation.

## Completed after the original audit

### DP-R3 — Bounded provenance consolidation

- Completed 2026-08-27: the three repeated exact-file SHA-256 helpers were consolidated into `cmbench/reporting/provenance.py` with a compatibility re-export, transitive source-snapshot coverage, focused tests, and an exact quick smoke.
- The three-round smoke passed exactness/integration but was too small and noisy for an overhead claim; its timing gates failed and are retained as inconclusive.
- Broader audit-driver consolidation is deferred because distinct timing, corpus, and artifact contracts should not be coupled without a measured reliability benefit.

## Ready to implement or prototype locally

### DP-R1 — Compact canonical ordering/key prototype

- Surface: `CMIRBuilder._canonicalize_commutative_args`, `make_xor`, `make_eqv`, `CMNode.key`, foreign adoption.
- Evidence: interning is 21–26% of measured compile; canonicalization is about 6%; deep structural tuple comparison can follow unfolded occurrences on sharing-heavy graphs.
- Prototype: attach/use a builder-local compact canonical rank or digest for ordering while preserving exact existing child order, `CMNode.key`, structural hashes, and foreign adoption behavior.
- Gate: exact ordered IR and packed hashes on BX1/B2/EPFL plus high-sharing B3; paired cold compile; `tracemalloc`; no key/digest/persistent-path regression.
- Stop rule: reject an effect within ordinary noise, any worse high-sharing tail, or any semantic/canonical ordering ambiguity.

### DP-R2 — Harden estimates before a production temporary-memory policy

- Surface: `cmbench/output_budget.py`, local/remote wrappers and configuration.
- Evidence: output estimates and typed refusals exist; some production callers still allow `None`. The 2026-08-27 dense diagnostic found the current `2 * output_bytes` temporary estimate below median `tracemalloc` peak by 3.51x to 38.73x on the bounded cases.
- Work: first implement and validate representation-specific conservative estimates across dense, bigint, and word-packed paths without changing defaults. Then measure compatibility of the proposed versioned 16 MiB benchmark/remote and 64 MiB direct profiles.
- Gate: refusal before allocation, no partial artifact, typed status propagation, compatibility plan for callers that currently opt out.
- Note: estimator work is authorized by the backlog; the numeric defaults and newly possible refusals still require Brian’s explicit API-policy approval.

### DP-R4 — Second-machine confirmation of the one-memo preparation change

- Run the explicit-arm `scripts/cm_prepare_memo_ablation.py` unchanged on a materially different CPU/OS.
- Gate: exact outputs, no material aggregate regression, and memory direction consistent. This is confirmation, not an untouched selector gate.

## Needs a real workload

### DP-W1 — Byte/cost-aware compiled-artifact cache

Required trace fields: compiler/schema/options key, structural key, artifact and retained bytes, build cost, lookup/serialize time, hit/miss/evict, process/cold-start boundary, family/version/context ID, subsequent evaluation count, output type, and cache budget.

Compare no cache, current entry-LRU, byte-LRU, then size/cost-aware admission. Report hit and saved-time curves, eviction churn, phase changes, RSS plateaus, disk bytes, invalidation, and corrupt/stale artifact tests. Do not adopt TinyLFU from a synthetic all-hit pass.

### DP-W2 — Incremental compilation across real edits

Compare:

1. cold CM compile;
2. current structural subtree/root cache;
3. minimal tracked-query red-green prototype;
4. sharing-aware CSE-flat incumbent.

Include digest/validation time, affected structural region, retained dependency state, wrong-hit adversarial tests, and `q` after each version. Independently regenerated family formulas are not an edit trace.

### DP-W3 — Feature-based backend selection

Only pursue if `k=13..15` traffic is material. Freeze a tuning corpus and a new untouched circuit-held-out corpus before fitting. Candidate features: `k`, `s`, flat instruction and primitive-op counts, operator mix, sharing factor, peak live word buffers, output kind, cache state, expected `q`, and `B`.

Required metrics: geomean and maximum regret, `>=2x` misroute rate, selector overhead, blocked/round-robin stability, memory-limit behavior, and cross-machine transfer. No production integration from in-sample or B2/EPFL-only validation.

### DP-W4 — Repeated partial-context break-even

Trace original/remaining support, contexts, overlap/locality, phase changes, queries per context, output kind, cache budget, process lifetime, and BDD manager/order lifetime. Keep BDD build, restriction, symbolic query, and exhaustive extraction separate. Compare BitSet fixed/restricted, CM compile-once, and BDD build-once.

### DP-W5 — Related policy/circuit versions

Reopen family reuse only with real revisions. Report total task work, not merely CM versus uncached CM. Include generation/loading outside timed windows and compare hash-consed CSE-flat and task-matched symbolic incumbents.

### DP-W6 — Exact independent-block decomposition

Needed input: repeated formulas with demonstrable disjoint support blocks or dominant layout/lift materialization. Prototype implicit broadcast/Kronecker combination and lazy permutation plans. Gate on a proof of block independence, exact final layout, lower peak memory, and total-cost improvement; final materialization remains exponential.

## Needs external dependencies or hardware

### DP-X1 — Native/JIT word fusion

- Approval: install Numba/LLVM or build a native extension.
- Preconditions: a real repeated batch where words-kernel time dominates compile, binding, copies, and output.
- Candidate: flat opcode/operand arrays, preallocated `uint64` scratch, fused binary/ternary patterns, AVX2 baseline, optional AVX-512 `VPTERNLOG`, scalar fallback.
- Gate: exact reference equality, cold/warm compile, dispatch/copy/conversion, held-out batch, CPU feature dispatch, per-thread concurrency, peak memory.
- Semantic rule: never compile arbitrary Python packed bigints as fixed-width integers.

### DP-X2 — Native CUDD context frontier

- Approval/dependency: confirmed working `dd.cudd` on the benchmark host.
- Measure fixed/dynamic orders, manager reuse, node count, computed-cache/reorder statistics, build, restriction, query, and exhaustive extraction separately.
- Purpose: task-matched symbolic/context workloads, not generic complete-output replacement.

### DP-X3 — Streamed large-output hardware study

- Requires a caller that accepts chunks/streaming rather than one packed integer.
- First compare bounded single-process tiling. Add processes/GPU/remote only if measured compute amortizes transfer/startup and aggregate memory fits the budget.
- Claimed benefit may be bounded peak memory or latency-to-first-chunk, never removal of total output work.

## Theoretically blocked under the current artifact

### DP-T1 — Sub-exponential complete explicit output

Returning all values over `k` live variables requires `2^k` bits. Packed storage/output work is `Omega(2^k/w)`. BDD, SAT, factorized, and oracle results are different artifacts until expanded.

### DP-T2 — Universal Kronecker/tensor shortcut

Only decomposable independent blocks have guaranteed product structure. Arbitrary Boolean functions do not. Numerical/approximate low-rank methods violate exact semantics; reconstructing the requested vector restores the output lower bound.

### DP-T3 — Quotient as semantic XOR

The CM directional feature quotient is not XOR and must not be timed as an equivalent semantic difference.

### DP-T4 — Global semantic canonicality from current keys

Current normalization/digests establish engineering identity under documented rules and collision assumptions, not a theorem over all semantically equal Boolean expressions.

## Tested and rejected for now

| ID | Candidate | Evidence | Reopen condition |
|---|---|---|---|
| DP-N1 | Maintain both identity and structural build memos | Removing identity memo: BX1+B2 ratio 0.9601, EPFL 0.9768, traced peak 0.882, exact outputs | None unless legacy path changes; legacy still keeps identity memo |
| DP-N2 | Automatic words at `k=6` | Multiple-fold/catastrophic regret in accepted crossover evidence | Never without new paired evidence |
| DP-N3 | Universal thresholds 14 or 15 | Focused and cross-machine gap study trades circuit gains for synthetic catastrophic misses | New feature selector and untouched gate, not another scalar retune |
| DP-N4 | Optimize CM/CSE-flat residual | B1 parity; corrected structural win is workload-specific; public wrapper remains slower | Repeated end-to-end workload repays preparation |
| DP-N5 | Broad pass fusion | Preparation cost distributed; no dominant duplicate traversal | Measured removable allocation/traversal at one boundary |
| DP-N6 | E-graph replacement | Rewrite/canonicalize small; extraction/memory/correctness cost | Real heavy rewrite/edit stream |
| DP-N7 | Deep `CMNode.key` equality for validation | Unfolds high-sharing EPFL and becomes impractical | Do not reopen; use exact O(`s`) DAG signature |
| DP-N8 | Cache admission policy from all-hit replay | No realistic byte/access distribution | DP-W1 trace |
| DP-N9 | CM family/context dominance | Helps CM versus itself but loses strongest incumbents | DP-W4/W5 workload crosses break-even |
| DP-N10 | Direct bigint JIT | Fixed-width semantics mismatch | Never; use explicit word arrays |
| DP-N11 | Multiprocessing/GPU/distributed default | Startup/copy/output/memory do not amortize | DP-X3 streamed kernel-dominant workload |
| DP-N12 | Sparse numerical matrices | Packed Boolean truth vectors are not a sparse numerical-LA workload | Proven exact block sparsity with task-matched operations |

## Priority

1. Harden temporary-memory estimates; agree on defaults only after compatibility evidence if these APIs are being productized.
2. Prototype compact canonical ordering/key comparisons with exact compatibility gates.
3. Obtain real cache/version/context traces.
4. Build a feature selector only if the gap has production volume and a new untouched corpus is frozen.
5. Consider native/JIT kernels only after a repeated batch makes the word kernel dominant.
