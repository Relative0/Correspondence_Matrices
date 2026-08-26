# Audit Memory

This campaign starts from, and does not supersede without explicit evidence,
the accepted 2026-08-25 audit and correction artifacts.

- Bare CM and flattened sharing-aware CSE are the same kernel class on the
  accepted evidence. Do not optimize their old near-parity residual.
- The accepted local symmetric V3 study found bare CM/CSE-flat `0.890570`
  overall and `0.961234` at `k=16`; the public wrapper was slower at `3.094136`.
  Three fresh same-host runs below show material run-to-run movement without
  changing those qualitative conclusions.
- Preparation remains the leading CM-specific optimization surface. The
  accepted one-memo implementation removes a redundant identity memo from the
  sharing-aware builder while preserving the legacy path.
- Full explicit output remains lower-bounded by `Omega(2^k / w)` packed words.
  A symbolic BDD, stream, quotient, or structural delta is a different artifact.
- `WORDS_AUTO_MIN_VARS=16` remains the conservative supported selector policy.
  It is not a universal crossover theorem.
- Current persistent IR caching is process-local and entry-count bounded. It is
  not a durable cross-process artifact cache.
- B2 and EPFL are reused validation, not untouched selector evidence.
- CUDD construction, reordering, restriction, symbolic query, and exhaustive
  extraction are distinct timing/artifact windows.
- Current digests and keys give documented engineering identity under collision
  assumptions; they do not prove global semantic canonicality.

Campaign outcome: local correctness and safety held; the one-memo gain
replicated locally; a compact exact ordering-label prototype was tested and
rejected; cache/family/context economics remain workload-dependent; cloud and a
new independent selector corpus await explicit egress/download approval.
