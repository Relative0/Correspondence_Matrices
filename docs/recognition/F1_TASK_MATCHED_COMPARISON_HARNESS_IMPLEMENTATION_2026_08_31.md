# F1 task-matched comparison harness: first implementation slice

**Date:** 2026-08-31  
**Status:** implemented and contract-tested; no new cross-method timing claim

The repository already contained a fail-closed comparative foundation for complete and reduced
relations, exact counts, SAT status, witnesses, partial contexts, version histories, equivalence
deltas, streamed relations, and persistence lifecycles. F1 now adds the missing first-class
`gf2_decomposition` task and `exact_gf2_artifact` delivery type.

Four exact arms share this artifact boundary:

- bounded exhaustive CM/GF(2);
- C16 descriptor-screened CM/GF(2);
- C17 policy-selected exact analysis; and
- C17 advice-off exhaustive analysis.

Every arm delivers the same canonical best-artifact document, including an explicit no-artifact
document when no bounded compression exists. The adapter checks source digests and reconstructs
every materialized candidate before delivery. The independent required-output digest remains
outside comparative timing, while artifact reconstruction is charged inside the task path.

The contract refuses attempts to credit a decomposition result as an exact count or complete
truth relation. It also refuses mismatched artifact kinds and tampered result digests. This keeps
the website's complete-relation kernel measurements separate from decomposition, SAT, and count
claims.

Focused comparative, dispatcher, and decomposition verification passed with **39 tests and 117
subtests**. This is infrastructure evidence only. The next F1 run should build frozen per-task
tables from the C18 corpus, retaining kernel-only and end-to-end columns, memory/artifact size,
cold/warm lifecycle, and explicit refused/ineligible cells.

