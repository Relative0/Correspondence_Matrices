# CM Gap Series — Post-Acceptance File Index (2026-08-03)

Index of the post-acceptance pass only. The historical index
(`CM_GAP_FILE_INDEX_AND_SUPERSESSION_2026-08-02.md`) remains authoritative
for everything up to acceptance and is intentionally not rewritten. Nothing
in this pass supersedes any accepted artifact; this pass added evidence and
documentation only. Repository at `main` = HEAD = `origin/main` =
`eab8879edcb7fb13582ad9bdff7ea7c00238774d` throughout; no tracked file was
modified.

## 1. New artifacts (all untracked, awaiting commit decision)

| path (under `deliverables_n22_24\`) | role | SHA-256 | status |
|---|---|---|---|
| `CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md` | independent reaggregation report — **INDEPENDENT REAGGREGATION PASSED**; closes the acceptance review's same-session caveat (§4A) | `cc3ea8f948edd9f1eb301aa964c238ca467c8fa9c3be8effce24d28d716108f9` | authoritative |
| `cm_gap_independent_spot_replication_results_2026_08_03.json` | machine-readable replication evidence (19 checks, bootstrap deltas, discovered definitions) | `24c9c739205b459f2d932ece82d39afaa02c41b47e82ed1643617740d17338c6` | authoritative |
| `CM_GAP_POST_ACCEPTANCE_CLARIFICATIONS_2026-08-03.md` | R1 (identity-basis fields) and R2 (foreign/twin lowering) clarifications of record | `570480e23ec627935d974f5c503a81e02afc20951f15b2cd16445823bbee8f9e` | authoritative |
| `CM_GAP_EPFL_PROTOCOL_2026-08-03.md` | pre-registered EPFL/AIGER external-corpus protocol incl. materiality rule — **frozen before any external data** | `f38027baa7dbb81a03a604c9eb884bda321c58a766076f3e5b0a8db14cc7c0c5` | authoritative (pre-registration) |
| `CM_GAP_POST_ACCEPTANCE_OPTIMIZATION_DECISION_2026-08-03.md` | Outcome A (provisional) decision; pod **NOT WARRANTED** record; ranked tests/optimizations | `8ca77b299348d5acf77dcde55317f7edda5444f485e80eb8654404fde6f2d395` | authoritative |
| `CM_GAP_POST_ACCEPTANCE_FILE_INDEX_2026-08-03.md` | this file | — | authoritative |
| `CM_GAP_NEXT_PHASE_MASTER_HANDOFF_2026-08-03.md` | self-contained handoff for the next session, incl. next-implementation prompt | — | authoritative |

Scratch (preserved, never to be staged):
`tmp\cm_gap_post_acceptance_2026-08-03\`
(`independent_reaggregation_2026_08_03.py`
`13d6a83688d4d40c5f07e979393f3235be1546a0794260bcb54abc8ef566fd16`,
`diagnose_median_basis.py`, `inspect_schema.py`),
`tmp\pytest_cm_post_acceptance_2026-08-03*` (pytest basetemps).

## 2. Authoritative chain (unchanged by this pass)

Corrected E3 corpus/results/summary/driver, consolidated audit + erratum,
acceptance review + results JSON, acceptance handoff — exactly as listed in
the 2026-08-02 index §3 and the acceptance handoff §2, now committed at
`eab8879` (the handoff's "uncommitted" framing described the pre-commit
state; the commits `c1d6ead`/`882e2c2`/`f378eba`/`eab8879` landed the same
content unchanged — hashes re-verified this pass).

## 3. Superseded map delta

None. No artifact changed status this pass. The 0.843 headline and the
96-formula corpus remain superseded per the historical index; the 0.888 /
0.985 corrected results remain the citable statements, with the
generalization limits restated in the optimization decision.

## 4. Open gates

- EPFL download: `EPFL_DOWNLOAD_APPROVED = NO` — protocol waiting.
- Pod replication: recorded NOT WARRANTED (trigger documented).
- Commit/push: `COMMIT_PUSH_APPROVED = NO` — everything above is
  uncommitted; decomposition proposal in the master handoff.
