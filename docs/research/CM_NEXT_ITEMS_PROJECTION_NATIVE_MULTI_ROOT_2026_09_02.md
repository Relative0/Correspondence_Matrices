# CM next-items implementation report — projection, native slots, and multi-root sharing

> **2026-09-03 continuation:** the native single-root and multi-root candidates passed
> the frozen, fresh C37 prospective confirmation and now have a disabled-by-default,
> SHA/ABI-validated boundary with exact Python fallback. See
> `CM_C37_NATIVE_EXACT_CONFIRMATION_AND_INTEGRATION_2026_09_03.md`.

> **Superseded next-step note (2026-09-03):** the prospective instruction at the
> end of this report is no longer current. The cache-isolated seven-arm closure in
> `CM_NATIVE_PORTFOLIO_BASELINE_CLOSURE_2026_09_03.md` includes the omitted CSE/CM
> bigint and word controls. Native wins all 18 exposed cases, leaving exactly
> `1.0000x` selector headroom, so prospective-data use and learned routing remain
> stopped under the current gate.

Date: 2026-09-02  
Scope: exact, non-neural CM-family execution used by the C36 repeated-restriction task  
Status: development evidence only; no production policy change and no prospective confirmation data consumed

## Bottom line

The remaining ordered performance items were not all previously implemented. This continuation completed the next three applicable experiments:

1. projection conversion/index cleanup;
2. a fused native exact slot executor;
3. native multi-root/cross-cone compilation on genuine sibling-output arithmetic.

Projection cleanup was exact but missed its continuation gate. The native executor and multi-root union both passed strongly. Once the native executor is included, it wins every exposed single-root C36 case, so the recomputed routing oracle is exactly `1.0000x`; formal routing and learned selection are therefore not justified for this task.

## 1. Projection-internal cleanup

Implemented development-only candidates:

- minimum safe index dtype (`uint16` for C36 widths 11–16);
- 64 separate `uint16` index arrays;
- one contiguous `uint16` index arena;
- packed-integer cofactoring that avoids the byte-per-truth-row vector.

Correctness:

- all 18 exposed C36 cases;
- all 64 restrictions per case;
- 1,152 exact restrictions checked against the scalar full-truth oracle;
- zero relation/count/SAT/witness/canonical-delivery mismatch.

The first timing run exposed a hidden process-global bitset-environment LRU interaction: projection arms warmed other projection arms, while the earlier R0/R1 arms had warmed R2. The cache-isolated replication clears that LRU before each complete task session but preserves reuse within the 64-query task. That replication is the decision-bearing result.

Cache-isolated aggregate case-median q64 totals:

| Method | Accounted total | Result |
|---|---:|---|
| Python R2 reference | 122.232 ms | best fixed |
| `uint16` tuple projection | 123.657 ms | 1.0385x over `uint32`; 0.9885x versus R2 |
| `uint32` control | 128.415 ms | frozen behavior |
| `uint16` flat arena | 129.562 ms | slower than tuple form |
| packed cofactor | 169.152 ms | loses in aggregate |

The `uint16` forms deterministically halve compiled index storage. The fastest projection improves total time by 3.85%, below the predeclared 5% integration gate, and remains 1.17% slower than R2. It is retained as a tested development candidate, not wired into the production path.

Evidence: `docs/recognition/runs/projection-optimization-development-20260902-002/`  
Independent verification: 900 performance sessions, 90 memory sessions, 63,360 raw query rows, 1,152 independently replayed queries, zero mismatches.  
Results SHA-256: `f6aa078b8c258beb254e048eed01742c88ed90f72bd1e9a7230bd8061770eaf9`  
Manifest SHA-256: `6af9b00cedab5476de5b281a89329c6b0d0bbf847c21d0173f3ac04c9afa8f16`

## 2. Fused native exact slot executor

Implemented:

- a portable C11 topological slot loop;
- internally generated live-variable word masks;
- fixed-variable binding in the same native call;
- exact `NOT`, `AND`, `OR`, `XOR`, `IMP`, and `EQV` word operations;
- a bounded `ctypes` adapter over validated DAG-v2 arrays;
- a local MSVC/portable C build path with no dependency download;
- binary ABI and SHA-256 identity in every native row and manifest.

The C36 trace uses live widths 6, 8, and 10, so each exact residual relation occupies 1, 4, or 16 64-bit words. The native loop removes Python opcode dispatch and avoids building Python big-integer environments for every restriction.

Aggregate case-median q64 totals in the balanced native experiment:

| Method | Accounted total | Relative to native |
|---|---:|---:|
| native fused slots | 113.651 ms | 1.0000x |
| cache-isolated Python R2 | 153.271 ms | native is 1.3486x faster |
| `uint16` projection | 153.660 ms | native is 1.3520x faster |

The native executor passes the predeclared `>=1.10x` continuation gate and wins all 18 exposed cases. The per-case oracle speedup over the native fixed backend is `1.0000x`.

Evidence: `docs/recognition/runs/native-fused-slot-development-20260902-002/`  
Independent verification: 324 performance sessions, 54 memory sessions, 24,192 raw query rows, 1,152 independently replayed queries, zero mismatches.  
Results SHA-256: `a97e0413857a6d405011590a4c49b010dcff5d3970107c08469f6e568e9818d0`  
Manifest SHA-256: `49dff06bda152aca569520e01da6cf32f548102ffcc699544c0d0a52fe9f3e14`

Decision: continue the native executor toward a frozen, prospective confirmation package. Do not promote it from exposed C36 timing alone.

## 3. Multi-root / cross-cone native compilation

The experiment uses six genuine sibling-output arithmetic workloads built from the project's pinned Yosys-style semantics:

- two 8x8 multiply output groups;
- one 8+8 add output group;
- one 16-input popcount output group;
- one 4x4-bit adder-tree output group;
- one 5x5 multiply-plus-6-bit-addend output group.

Each workload has three roots, 16 inputs, and the same deterministic 64-query trace. The control compiles and executes three native arenas separately. The candidate serializes the union DAG, executes it once, and emits all three exact roots.

Structural sharing:

| Workload | Sum separate nodes | Union nodes | Sharing ratio |
|---|---:|---:|---:|
| multiply bits 3/4/5 | 173 | 89 | 1.94x |
| multiply bits 5/6/7 | 389 | 177 | 2.20x |
| add bits 4/5/6 | 105 | 46 | 2.28x |
| popcount bits 1/2/3 | 253 | 111 | 2.28x |
| adder-tree bits 2/3/4 | 187 | 84 | 2.23x |
| multiply-add bits 3/4/5 | 248 | 119 | 2.08x |

Aggregate workload-median totals:

| Method | Accounted total | Evaluation |
|---|---:|---:|
| three separate native roots | 111.500 ms | 40.400 ms |
| one native union arena | 89.300 ms | 18.770 ms |

The union path is 1.2486x faster end to end, passes the `>=1.10x` gate, and reduces node count on every workload.

Evidence: `docs/recognition/runs/native-multi-root-development-20260902-002/`  
Independent verification: 240 performance sessions, 12 memory sessions, 48,384 raw output-query rows, 1,152 independently replayed output-query rows, zero mismatches. The run contains its exact native DLL as a manifest-bound artifact.  
Results SHA-256: `3cae2cb08320f351c9c0f07796eb0d7f4618c19b4300efed02a736b93b4b2229`  
Manifest SHA-256: `5e2afff8397beec7049866aafbc4b656d4fb866a1d252a0705d4735500c7e71e`

## Recommendation matrix after these results

| Recommendation | Current disposition |
|---|---|
| projection dtype/index cleanup | implemented and exact; 3.85% gain misses 5% gate |
| packed broadword projection | implemented and exact; aggregate loss |
| fused native slot executor | implemented and exact; passes at 1.3486x |
| multi-root/cross-cone sharing | implemented and exact; passes at 1.2486x on real sibling arithmetic |
| formal structural routing | do not run now; native fixed-backend oracle headroom is 0% on exposed C36 |
| online rent-versus-buy | not useful for the fixed-Q64 task after low-setup native wins every case |
| learned/neural router | do not pursue; simpler exact native backend leaves no oracle headroom |
| cross-query cofactor cache | trace-specialized version already lost; native result removes current priority |
| BDD/d-DNNF contract specialization | not comparable to the current explicit-relation contract; requires a real summary-only task |
| arithmetic structure recovery | remains research-only for wider/different arithmetic contracts; not required to win C36 after native fusion |
| ZDD/sparse ANF representation portfolio | remains a separate sparse-algebra research item; current complete-screen ANF integration already missed its gate |
| native truth-from-ANF | remains unimplemented; only justified for a task where ANF construction is already amortized |

## Measurement correction to carry forward

Performance comparisons must isolate process-global caches at the complete-task boundary. The earlier R2 correctness and work-count findings remain valid, but its timing relative to projection depended on which other arms warmed `build_bitset_env`. New experiments must either:

- clear the cache before every complete task, as these decision-bearing runs do; or
- run each arm in an isolated process with an explicitly declared warm-up lifecycle.

Cross-arm incidental cache warmth is not a backend property.

## Regression verification

- focused exact/performance surface: 43 passed in 46.64 seconds;
- broad non-neural surface: 1,231 passed, 1 unrelated failure, 4 existing `dd` shutdown warnings, and 1,127 subtests passed in 260.47 seconds;
- the unrelated failure is `test_generated_public_chart_data_is_current_and_pages_reference_it`, where a pre-existing generated chart file embeds source revision `5dd6ec77...` while its renderer now emits `d2643523...`;
- PyTorch-coupled modules were excluded because this project virtualenv does not contain PyTorch; the concurrently owned neural reassessment was not modified or attributed here;
- post-cleanup source/artifact hash replay found zero manifest mismatches in all three decision-bearing run directories.

## Next controlled step

Freeze the native single-root and multi-root sources, compiler identity, build command, and binary artifacts, then validate on fresh prospective cases without refitting. The attached implementation program explicitly forbids consuming the reserved confirmation set during development, so this continuation stops before that boundary. Production integration should occur only after that prospective exact replay retains the native advantage and acceptable memory/tail behavior.
