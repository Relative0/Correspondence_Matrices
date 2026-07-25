# CM Session 2026-07-24 — Audit V4 state and findings

Predecessor: `CM_SESSION_2026-07-23_AUDIT_V3_STATE_AND_FINDINGS.md`  
Full report: `CM_AUDIT_V4_2026-07-24.md`

## State

- Audited `main` at `6419b21`; `origin/main` remains `5dd6ec7`.
- Local `main` is still five commits ahead. Nothing was committed, pushed,
  deployed, published, or sent to a pod.
- The worktree began with user-owned untracked
  `FABLE_AUDIT_V4_KICKOFF.md`; it was preserved.
- System Python 3.10.11 test baseline: exactly 159 passed.
- Benchmark Python: `.venv` 3.13.5, numpy 2.3.2.
- Native CUDD unavailable; Docker Desktop/WSL engine stopped. Primary same-box
  CUDD rerun remains blocked.

## Findings

1. Latent fixes `cc52f43`, `f80a1cd`, `96294ac`, and `1cf4bcf` are confirmed.
2. Independent Review F2–F5 statistics reproduce. F5 remains 4/29 all-live,
   median semantic support 16, with three constants including n=28 trial 1.
3. Every committed wrapper CUDD raw/summary value reconstructs and all 2,700
   backend identities/correctness fields pass.
4. The wrapper CUDD chart uses median build time across ten random orders,
   although surrounding prose describes a best-of-10 policy. Numeric values are
   correct; the label is imprecise.
5. Best-of-k search cost is excluded and the retained BDD is chosen by node
   count then time.
6. Generic summary aggregation drops NaNs and commonly reports
   ratio-of-medians, so incomplete campaigns require explicit paired survivor
   accounting.
7. Current chart arrays match their CSV sources, but hand-embedded arrays remain
   a drift risk.
8. Browser visual QA was blocked because no browser backend was exposed.

## New V4 evidence

- Immutable 49-formula corpus, SHA-256
  `a1cb0763889c8f91de2fcc5a3fd86b0bc007afd728736452a84b39bf441f909d`.
- 301 packed-evaluation raw rows: 294 executed paired observations, seven
  intentional guard skips, zero mismatches.
- Controlled paired CM/Bitset medians: 1.053 (`live_k=8`), 0.948
  (`live_k=12`), 0.925 (`live_k=16`).
- Local autoref symbolic-build and query controls, all correct; explicit CUDD
  requests failed closed.
- Partial/family and remote-mock CLI evidence with words off/on, all correctness
  flags successful and provenance fields truthful.

## Next authorized actions

1. If desired, authorize a commit containing the V4 corpus, scripts, CSVs, and
   reports.
2. In a future live Linux/CUDD session, run the exact corpus through CM, Bitset,
   and CUDD in one container and collect fixed-order, best-of-k all-in,
   dynamic-reorder, query, and extraction totals.
3. Repeat the two-page light/dark render inspection when browser control is
   available.

Do not push the five existing local commits or these V4 artifacts without
Brian's explicit authorization.
