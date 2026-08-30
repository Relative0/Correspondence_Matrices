# CRSE Learning Milestone C6: packed exact source ANF

Date: 2026-08-30  
Status: **complete and independently verified**  
Production promotion: **no**

## What changed

C6 follows the strongest C5 result rather than adding another neural
hyperparameter sweep. It is a deterministic exact-algorithm milestone; no model
was trained.

For at most ten live variables, the full ANF coefficient vector occupies at
most 1,024 bits. C6 stores that vector in one Python integer:

- polynomial addition over GF(2) is integer XOR;
- Boolean polynomial multiplication is exact OR-convolution;
- subset-zeta transforms implement the convolution with bounded integer
  operations instead of enumerating monomial pairs;
- a 1,024-entry LRU caches products by the complete variable count and operand
  values; and
- a product-pair gate frozen from the validation split refuses an expensive
  uncached symbolic path and falls back to exact truth-vector ANF.

The packed result still crosses the existing exact acceptance boundary. Every
positive source proposal is checked by recomputing its truth vector and exact
partition witness. A fallback is the complete truth-vector ANF computation, not
an approximate or learned answer.

## Frozen experiment

The comparison retained C5's exact 188-function, 94-pair EPFL dataset and its
circuit-disjoint splits. It measured five paths with five cold-start-charged
repetitions per case:

1. C5 set-based source ANF;
2. packed source ANF without a product cache;
3. packed source ANF with bounded cross-case product caching;
4. cached packed ANF with the validation-frozen fallback gate; and
5. exact truth-vector construction plus ANF.

The 90th-percentile validation rule froze the uncached product-pair budget at
16,789 before test or confirmatory evaluation. The final run contains medians,
p95, maxima, cache hits and misses, conceptual and executed product-pair counts,
peak terms and bytes, and every fallback decision.

## Held-out results

| Method | Split | Median total | Speedup vs truth ANF | p95 total | p95 speedup | Maximum |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| set source ANF | test | 0.326 ms | 2.136x | 2.617 ms | 2.304x | 3.408 ms |
| set source ANF | confirmatory | 0.466 ms | 1.227x | 61.379 ms | 0.121x | 160.294 ms |
| packed source ANF | test | 0.544 ms | 1.281x | 2.779 ms | 2.169x | 3.804 ms |
| packed source ANF | confirmatory | 0.382 ms | 1.496x | 4.115 ms | 1.799x | 5.641 ms |
| cached packed source ANF | test | 0.531 ms | 1.313x | 2.771 ms | 2.176x | 3.888 ms |
| cached packed source ANF | confirmatory | 0.350 ms | 1.637x | 4.034 ms | 1.836x | 5.820 ms |
| budgeted hybrid | test | 0.538 ms | 1.295x | 2.790 ms | 2.161x | 3.900 ms |
| budgeted hybrid | confirmatory | 0.400 ms | 1.433x | 7.507 ms | 0.986x | 9.013 ms |
| truth-vector ANF | test | 0.697 ms | 1.000x | 6.029 ms | 1.000x | 6.431 ms |
| truth-vector ANF | confirmatory | 0.572 ms | 1.000x | 7.405 ms | 1.000x | 8.320 ms |

All five methods achieved 1.000 exact classification and canonical-partition
accuracy with zero semantic mismatches. The hybrid used no fallback on the
held-out square circuit and seven on the three confirmatory circuits. Across all
splits, 11 fallbacks reproduced the truth-vector result exactly.

The packed coefficient vectors reached at most 1,022 terms and 128 bytes. The
bounded cache recorded 1,099 exact hits and avoided 1,135,492 conceptual
monomial-pair products in the cached arm. The hybrid's gate and cache reduced
executed conceptual pairs further, although the packed convolution never
materializes those pairs.

## Interpretation and stability boundary

C6 removes the 63.7 ms C5 confirmatory p95 tail from the uncached and cached
packed cores. Both pass the cost boundary with comfortable p95 margins. The
gated hybrid missed its confirmatory p95 boundary narrowly: 7.507 ms versus
7.405 ms for truth-vector ANF, about 1.4% slower. The packed core advances;
the validation-frozen gate does not.

The retained development history matters. Run `001` rebuilt transform masks on
every multiplication and failed cost. After immutable per-dimension mask caching,
run `002` passed median speed but missed the hybrid confirmatory p95 by about
1.8%. Run `003` passed that fragile boundary by about 1.4%. The final run `004`
removed use of the retained dataset witness even as a fallback acceptance
marker; exact acceptance now comes solely from the completed truth-vector
fallback. It missed hybrid p95 by about 1.4%, confirming that the packed core is
the robust result and the gate should not become a default policy.

## Verification

The independent verifier:

- regenerated the retained 188-function C5 dataset byte for byte;
- reconstructed all 188 truth tables from packed ANF coefficients;
- matched all 188 packed polynomials to the C5 set-based implementation;
- replayed all 940 method/case results and eight cache streams;
- replayed the validation-only budget selection and all 11 fallbacks;
- recomputed every summary and criterion; and
- checked all retained artifact, source, and C5 dependency hashes.

Verification status: **pass**. Semantic mismatches: **zero**.

## Next boundary

The next strongest step is a sealed independent-family confirmation with a
small human-authored decomposition suite, followed by a second OS/machine
timing run. It should freeze the packed core before loading those cases and use
only the hard admission fallback. The validation-frozen product-pair gate is a
retained negative control. Neural cut fitting remains paused.

All 18 research tracks and all eight application areas remain preserved.

## Evidence

- Final run: `docs/recognition/runs/natural-source-anf-hybrid-20260830-004`
- Independent verification: `docs/recognition/verification/natural-source-anf-hybrid-20260830-004.json`
- Failed-cost pilot: `docs/recognition/runs/natural-source-anf-hybrid-20260830-001`
- Optimized development repeat: `docs/recognition/runs/natural-source-anf-hybrid-20260830-002`
- Acceptance-boundary development repeat: `docs/recognition/runs/natural-source-anf-hybrid-20260830-003`
- Machine summary: `docs/recognition/learning_milestone_c6_packed_source_anf_results.json`
