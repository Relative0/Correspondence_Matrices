# DP-R1 Pre-change Record

Frozen before implementation on 2026-08-26 (Asia/Bangkok).

- Baseline `cm_ir.py` SHA-256:
  `ff1633ccabd5392512ec0fdf4531773b7a92e0aa52109c6c681bd99357dcb7d7`
- Baseline implementation: accepted sharing-aware one-memo compiler at repository
  HEAD `0f833bc389778f7f915deb7acd4499d207e0ec21`.
- Current mixed-corpus smoke attributes roughly 5.7%--6.6% of instrumented
  preparation to canonicalization, so the theoretical whole-preparation gain
  from changing only ordering is bounded and must be measured.
- Hypothesis: a builder-local, exact, immutable order label can replace repeated
  comparison of deep public `CMNode.key` tuples while preserving their order.
- Prototype scope: the label is derived from a compact descriptor whose child
  fields are already order-preserving labels; labels are inserted between their
  descriptor neighbors. Public keys, child order, digests, cache keys,
  serialization, liveness, lowering, and packed outputs must remain unchanged.

Pre-registered keep gate:

1. zero ordered-DAG, public-key, live-variable, packed-output, cache-identity,
   or compatibility mismatches;
2. at least 2% representative cold-preparation improvement with the paired
   cluster interval below 1.0;
3. no validation-corpus aggregate more than 2% slower;
4. no material high-sharing-tail regression; and
5. no temporary or retained-memory increase.

If any gate fails or the effect is ordinary noise, revert the production
prototype and preserve its measurements as a rejected experiment.
