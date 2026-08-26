# Optimization Backlog Update

## Ready to implement

- No additional production performance change cleared the evidence gates.
- Keep the new EPFL chunk combiner and its two correctness tests; it closes a
  reproducibility gap without affecting runtime semantics.
- Keep the fail-closed Runpod memo campaign tooling; the completed three-pod
  campaign passed every gate and left zero active pods.

## Needs a real workload

- Byte/cost-aware process-local caching and any durable compiled-artifact cache:
  require access distribution, artifact bytes, restart rate, cache budget, and
  invalidation expectations.
- Family/incremental compilation: require real expression edit/version traces.
- Partial-context routing: prioritize traces near `n=16`, `c~500`, high overlap,
  and 50%--75% fixed, where the synthetic grid found approximate break-even.
- Batched/native word kernels: require a real repeated batch where kernel cost
  dominates preparation, binding, copying, and output.

## Needs dependencies, hardware, or another frozen corpus

- Native CUDD restriction/query/extraction study.
- Numba/LLVM or compiled AVX2/optional AVX-512 kernel prototype.
- Any replacement feature selector needs another independently frozen circuit
  family; i10 is now consumed held-out evidence and may not be used to tune its
  replacement.

## Theoretically blocked or different artifact

- Removing complete-output `Omega(2^k / w)` work while returning the same
  packed vector.
- Treating BDD, streamed output, quotient, or structural delta as the same
  artifact as exhaustive semantic output.
- Formal semantic canonicality claims from collision-assuming engineering keys.

## Tested and rejected

- Universal support-only selector thresholds below 16.
- The preregistered BX1-trained ridge feature selector: failed untouched i10
  transfer with 7 raw and 11 CM catastrophic routes.
- DP-R1 exact rational order labels.
- Generic synthetic family/cache claims of incumbent dominance.
- Raising the output guard as an "optimization."
