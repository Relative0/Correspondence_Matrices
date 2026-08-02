# CM Gap Series — Post-Acceptance Clarifications R1/R2 (2026-08-03)

Standing clarifications for the two non-blocking findings recorded by the
final acceptance review (`CM_GAP_CONSOLIDATED_REVIEW_2026-08-03.md` §2,
"New findings from this review"). This document is additive: no dated
accepted report, driver, corpus, results file, or acceptance evidence is
amended by it, and none should be — the historical artifacts remain exactly
as reviewed. Written by the post-acceptance independent session, after the
independent spot replication passed
(`CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md`).

## R1 — Identity-basis corpus fields are generation-time values

**Clarification of record.**

- `identity_dag_nodes`, `unfolding_factor_identity`, and the identity-based
  operator-mix field (`operator_mix_identity`) in
  `CM_gap_e3_corrected_corpus_2026_08_02.jsonl` describe the
  **generation-time object graph** — the Python object identities that
  existed when the formula was generated.
- v2 serialization (`expression_v2`) **structurally deduplicates equal
  subtrees**. Two separately allocated but structurally equal subterms
  (e.g. two `Var(3)` leaves) serialize to one definition.
- Consequently, **reparsing the serialized expression can produce different
  identity counts** than the recorded fields (the acceptance review measured
  73/192 records with a smaller reparsed identity DAG; 67 tree, 6 shared;
  small deltas such as 19→18). This is expected behavior, not corruption.
- The original values **remain reproducible from the recorded seeds**:
  regenerating every formula with the driver's generator from its recorded
  seed reproduced all recorded fields and structural hashes 192/192
  (acceptance review, lineage check).
- **No admission rule, benchmark statistic, or accepted conclusion depends
  on the identity-only fields.** Every admission-relevant and every
  results-relevant quantity is structure-determined (structural DAG nodes,
  unfolded occurrences, sharing factor, structural operator mix, structural
  hash, truth SHA-256) and was verified to survive serialization unchanged.

**Practical rule:** treat identity-basis fields as pre-serialization
provenance recomputable via seed; validate corpora against the
structure-determined fields only.

## R2 — Foreign/twin lowering can duplicate flat-program slots

**Clarification of record.**

- When a builder adopts a foreign CMNode (structural adoption creates or
  finds the receiving builder's structurally identical **twin**), the
  foreign object and its twin are distinct Python objects with equal
  canonical keys. If **both identities reach the same root** — the foreign
  object used directly as a child, and the same structure later built
  internally — id-memoized `compile_flat` lowers the shared structure
  **twice** (the acceptance review measured 2 XOR slots for a constructed
  shared subterm where 1 would suffice).
- This **duplicates flat-program slots only**; packed evaluation semantics
  and canonical keys remain exact. No correctness property is affected.
- The behavior **predates compact interning**: the pre-compact-key builder
  never admitted foreign children into the receiving builder's intern table
  either, so an internally built copy was a separate object then too.
  Compact interning did not introduce this; the F4 fix did not regress it.
- **Structural adoption (the F4 fix) restores canonical equivalence and
  ID safety** — equal keys resolve to one interned twin per builder, foreign
  ids are pinned for the builder's lifetime (`_foreign_keepalive`), and
  GC/id-reuse hazards are closed. It **does not promise global
  object-identity unification across builders**, and the documented "local
  twin" model never promised argument-identity dedup between a foreign
  object and its twin.
- Production exposure is narrow: the persistent cache returns one object
  per digest, so mixed identities require mid-compile eviction or
  deliberate cross-builder mixing.
- **No optimization should be made for this narrow behavior without
  profiling a real production workload.** The known cost is a duplicated
  slot in a constructed corner case; there is no evidence it occurs at
  measurable frequency in any real workload.

## Related documentation nuance (cross-reference)

The independent spot replication additionally recorded that the corrected
E3 summary's `median` field is a **log-space median**
(`exp(median(log r))`; geometric interpolation of the two middle ratios for
even n). See `CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md`,
"Discovered definitions". Display-rounded report values are unaffected.

## Status

R1 and R2 remain **non-blocking, informational**. This document is the
one-line-per-item docs clarification the acceptance handoff called for
(§5, "Two one-line docs clarifications"), expanded to standalone form so a
future session needs no other context. It is linked from the
post-acceptance file index
(`CM_GAP_POST_ACCEPTANCE_FILE_INDEX_2026-08-03.md`); the historical
2026-08-02 file index is intentionally left untouched.
