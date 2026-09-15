# Continue CM implementation and historical replay work

This handoff follows a completed, verified publication. Continue the implementation
plan; do not restart the previous research or redeploy the completed release.
No new research code, test run, paid run, or publication was performed in the
handoff-preparation turn.

## Workspace and approved scope

Root: `C:\Users\brian\Documents\CM_Computation`.
The root worktree has unrelated changes: never stage, revert, or commit them.
The completed release checkout is `build/cm-closures`, branch
`codex/cm-count-closures`, at
`f2178bd4e2f5e76e4857527c5ca809d65e044273`.
Its last observed status contained only untracked `_site/` and `build/` output.

Create a separate isolated checkout or worktree at this commit for new research,
using a `codex/` branch. Preserve the completed checkout and all sealed audits.
Git operations on the existing checkout use a command-local
`-c safe.directory=C:/Users/brian/Documents/CM_Computation/build/cm-closures`.
Do not change global GitHub authentication: the active account is btheorystartups;
Relative0 publication used repository-local authentication.

The user authorizes continuing the implementation and testing plan and prefers
autonomous routine work. Read, implement scoped reversible changes, prepare
experiments, and run appropriately short tests without repetitive confirmation.
Do all useful authorized preparation before requesting any missing approval.
The prior explicit publication approval covered the completed f2178bd4 release;
do not treat it as blanket authorization to publish future changes. Preserve the
user's restrictions on secrets, destructive actions, commits, and external writes.
Do not spawn subagents unless subsequently requested or required by applicable
instructions.

## Read first, then fetch only relevant evidence

Paths below are relative to the root unless they start with `build/cm-closures`:

1. `docs/audits/2026-09-12-cm-closures-publication/NEXT-IMPLEMENTATION-PLAN.md`
2. `docs/audits/2026-09-12-cm-closures-publication/REPORT.md`
3. `docs/audits/2026-09-12-cm-closures-publication/COST-AND-CLEANUP.json`
4. `build/cm-closures/docs/audits/2026-09-12-cm-count-closures/REPORT.md`
5. `build/cm-closures/docs/audits/2026-09-12-cm-count-closures/REGRESSION-TRIAGE.json`

Read the exact implicated sources and tests next. Avoid dumping entire audit trees
or reading all historical manifests into context.

## Completed baseline

- Live site: https://relative0.github.io/Correspondence_Matrices/latest-results.html#evidence-frontiers
- Commit f2178bd4 was pushed to Relative0/Correspondence_Matrices main. All 147
  live-file checks passed: 145 byte comparisons and 2 full manifest comparisons.
  Live graph interactions and wide/narrow layouts passed. Exact-commit Pages and
  Windows/Linux focused CI passed. There are 18 panels, 1,467 records, 23 figures.
- All 120 fixed admitted contexts have completed exact counts, with independently
  implemented agreement for 119. Decisionmaking (`additional-09`), context 7,
  has a completed d4 result only. Ganak attempts hit memory/deadline limits.
- Bounded component counting completed 7/15 cases, adding Fiasco and uClibc to
  earlier coverage. All 336 completed timed query outputs in 135 cells matched
  independent counts. Two feature cases hit the 100,000-node cap; all six
  independent cases hit the 20-million-work cap. Performance was mixed; the
  production default was not changed.
- Broad Linux replay: 1,773 passed plus 1,181 passing subtests, 18 failures,
  3 errors, 3 skips. This phase recovered 17 prior failing IDs and introduced
  zero new failing IDs. The full historical suite is not green.
- Cumulative exact public fixture restoration is 318 files. The EPFL discrepancy
  was an asymmetric line-ending comparison: original retained bytes match upstream.
  Do not reopen it as unknown provenance or change old hashes.
- Actual video production was audited as presentation-only. Zero natural backend
  sessions were admitted. Do not manufacture a production task to claim real use.

## First implementation deliverable

Work from `cmbench/comparative/component_counts.py` and
`tests/test_component_counts.py` in the new isolated checkout. Preserve the original
implementation for comparison. Add bounded diagnostics that identify propagation,
component construction, branching and cache costs, including the resource-limit
reason and partial statistics when a call refuses. Preserve existing callers'
exception behavior. Use diagnostics to select one targeted optimization, not a
bundle of speculative changes.

Keep exact projected-count semantics: counted-variable branches add, hidden-only
branches use existential OR, and components must include shared hidden variables.
Keep arbitrary-size integer counts, fresh per-query caches, and resource limits.
Existing tests include 1,280 small cases in two cache modes, hidden witnesses,
large integers, invalid inputs and refusals. Run relevant controls for any semantic
change; add tests for newly observed mechanisms rather than mirroring code.

Prepare a new frozen paired protocol for the 15 original cases. Reused cases are
development evidence, not independent prospective validation. Preserve all
refusals, regressions and overheads; disclose any change in work accounting.
Do not claim speed or coverage improvements before remote measurements finish.

## Historical replay deliverable

Use the 21 exact IDs and messages in REGRESSION-TRIAGE.json:

- 9 Windows DLL cases: prepare an isolated replay with matching Windows runtime,
  original native binaries and inputs. Substantial execution needs an appropriate
  remote Windows environment; a Linux RunPod cannot load the historical DLLs.
- 9 other source/interpreter replay checks: recover the original frozen identities
  and run the unchanged verifier against the restored snapshot.
- 3 packages require an exact 38,464-byte backend with SHA-256
  `4b80a27fa4de67bf35fb13d76ea9d6cd679bfb6dafc8b554741f4987c49bcbdc`.
  A bounded search of 117 surviving same-named files, 2 Git versions and 77 pinned
  archive members found no match. Search further only if a new archive/source is
  available. Do not reconstruct an approximation or rewrite expected hashes.

Distinguish historical snapshot replay from current-code regression. Restoring a
missing prerequisite may reveal further failures; the categories are observations,
not guarantees that each test will then pass.

## Remaining secondary work

Prepare an independent method or verified decomposition for Decisionmaking
context 7; avoid another deadline-only retry without a concrete reason.
For real consumer work, consult
`docs/video_factory/CM_VIDEO_SERIES_CURRENT_STATE_HANDOFF_PROMPT.md` only if a new
independently needed job exists. The earlier capture adapter is ready; actual
backend demand must be observed before new integration claims.

## Runtime, budget and immutable receipts

Prefer `.venv/Scripts/python.exe` under the root, with `-X utf8 -B`.
Use PowerShell syntax. Computation expected to take more than several seconds
belongs on RunPod, or the required remote Windows runner. Short tests and local
implementation/preparation can proceed. Do not run a broad local suite as a
workaround for the cloud budget.

The latest ledger records $10.00 in cumulative nonrefunded reservations, fully
allocating the existing authorization. The conservative rate/lifetime estimate
is $0.7929903217852114, not posted billing and not a refund of reservations.
All 9 pods from the latest phase were deleted; the local preview server is stopped.
No new paid allowance was granted in the handoff request. Complete useful unpaid
implementation/preparation first; obtain a new or explicitly revised budget only
when a concrete remote execution package is ready.

Science seal, inside build/cm-closures:
`docs/audits/2026-09-12-cm-count-closures/FINAL-MANIFEST.json`
SHA-256 `df889ae125afc114917460a32ede7e82f6145d7dfb559dacbc6b72f3258d5548`.

Publication seal, under the root:
`docs/audits/2026-09-12-cm-closures-publication/FINAL-MANIFEST.json`
SHA-256 `125bd30ee08c11ac6cbd4e1f7a7fdad5a6a450d2a45a66e8bea3a003a388f89f`.

Do not write inside either sealed audit. The working original-release verification
entrypoint is `scripts/verify_cm_count_closures_release.py`. It fixes reporting
metadata around the unchanged sealed verifier; do not edit the old sealed source
to remove its recorded serialization defect. Use a new audit directory for new work.

Report actual changes, passing checks, remaining blockers, and next concrete
execution steps. Do not repeat a completed website deployment or benchmark merely
because this is a new thread.
