# Real feature-model history / bounded-neighborhood pilot protocol V2

**Frozen:** 2026-08-27, after source-format inspection but before model admission, correctness evaluation, or timing.

V2 retains every selection rule, arm, correctness check, statistic, threshold, and claim boundary in V1. It makes two artifact-contract details explicit so the four arms evaluate the same bounded object efficiently and reproducibly.

## Source facts frozen before payload parsing

- Exact source commit: `afa60ee2c836e7bdc4068e0f4f128ea31158d2ad` on the official `master` branch.
- Metadata SHA-256 values and license SHA-256 are recorded in the run provenance before any DIMACS parser runs.
- `statistics/Complete.csv` contains seven histories in total: one automotive, one finance, and five systems-software histories. This agrees with the repository's domain-level history counts.
- A DIMACS inspection preflight confirmed that corpus files can map declared variable numbers to original feature names in leading `c <number> <name>` comments. The native `p cnf` header remains authoritative for relation semantics.
- Some source-native DIMACS payloads, notably the selected Linux history, are stored as `.dimacs.zip`; these are admitted only when the archive has exactly one safe regular `.dimacs` member.

## Corrected conditioning contract

All four arms first use CaDiCaL to obtain the same satisfying product and freeze all variables outside the selected eight-variable slice. For the packed arms, apply that fixed context to the CNF before constructing an expression:

1. discard a clause satisfied by any fixed outside-slice literal;
2. remove fixed false literals from the remaining clauses; and
3. retain the resulting clause over slice variables.

This reduction is exact for the V1 local-neighborhood semantics: it is the original CNF under the same fixed outside assignment, not an existential projection. Conditioning before expression compilation avoids charging CM/CSE for dead clauses that the specialized CNF arm also skips. Record conditioning time and residual clause/literal counts separately. `cadical195` continues to query the unmodified native CNF under the identical complete assignments.

If no residual clauses remain, represent true explicitly and require an all-ones 256-bit vector. An empty residual clause is a correctness failure because the satisfying witness must remain in the neighborhood.

## Variable and packed-bit contract

- Slice candidates are original feature variables only: a declared DIMACS variable is eligible when its leading comment provides a nonempty original feature name. If fewer than eight mapped variables exist, record the model as ineligible.
- Incidence is counted in the native CNF for those mapped variables.
- The ordered slice from V1 is also the packed assignment order: slice item 0 is the least-significant assignment bit, and bit `i` of the 256-bit output is the formula value for assignment integer `i`.
- CM/CSE evaluator axes are supplied in reverse local-variable order to match the project's MSB-first environment construction while preserving this external LSB-first contract.

All other protocol provisions remain unchanged. V1 is retained as the preregistration record; V2 is the executable artifact contract.
