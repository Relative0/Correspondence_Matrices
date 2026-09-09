# CM website evidence update — 2026-09-09

## Outcome

The public results site was rebuilt from the accepted repository evidence through 2026-09-08. It now presents positive, negative, invalid, and stopped results together, preserves the established provenance method, and does not imply that recent research changed a production route, default, selector, or RunPod permission.

No push, deployment, cloud request, migration, or other external write was performed.

## Repository and worktree disposition

- `origin/main` and local `main`: `f6339c739c1905c16afb1433ed2ab1db9513404d` (`Record independent active workflow no-go result`).
- Independent workflow branch: `codex/cm-independent-active-workflow-20260908` at `f6339c7`; its worktree is clean and retained.
- Reviewed integration branch: `codex/cm-reviewed-integration-20260909`, created from `origin/main`, with the preserved learning/neural site commit `8033d1d` applied before this evidence reconciliation.
- Earlier reviewed branch: `codex/cm-reviewed-integration-20260908` at `f6339c7`; clean worktree retained.
- Original dirty-work preservation branch: `codex/cm-original-dirty-preservation-20260908` at `c89dc84`. The website/neural subset entered the integration branch as its own commit; unrelated video and RunPod preservation commits were not mixed into the site update.
- The original `main` checkout retains eleven untracked RunPod metadata files under `docs/video_factory/runpod/foundational_three_v1`, `v2`, and `v3`. They were not opened, modified, staged, or removed. No worktree was removed.

## Evidence method

The update follows `docs/audits/2026-08-25-cm-deep-performance/CM-WEBSITE-RESULTS-AUDIT-UPDATE-PROMPT-2026-08-27.md`: machine-readable results control numeric claims; narrative summaries control disposition; invalid attempts remain visible; every public number is bound to a file and field; generated artifacts are rebuilt from source.

The machine-readable ledger is `CM-WEBSITE-CLAIM-LEDGER-2026-09-09.json`. Its fourteen records cover the established architecture/query-ladder/learning evidence plus the September architecture disposition, incremental prototype, two hardware corpus gates, H2/H3 profiling, H6 calibration and estimator, and the independent maintained-caller retry. Invalid first attempts are recorded separately from valid retries.

## Current public dispositions

1. **H2/H3 profile-first gate — no candidate.** The corrected retry was valid across 237 rows. Key creation was the largest aggregate component at 7.88%, but no component met the complete materiality and prevalence gate. H2 and H3 remain deferred.
2. **H6 memory calibration — valid protocol, failed router.** Calibration completed 708 rows over 236 logical cells, with 98.58% stable-signal prevalence and 58.11% arm discrimination. The permitted estimator ordered 0/3 materially separated holdout pairs correctly. No router was promoted.
3. **Independent maintained caller — valid no-go.** Provenance independence was established for one maintained local video truth-layout workflow. The retry verified 300 profile rows and 24 fresh-process memory rows; key creation peaked at 5.80%, and no component passed the complete gate. No implementation or RunPod request followed.
4. **Incremental revisions — prototype not promoted.** Incremental update/cold CM was 0.442×, but update/current persistent cache was 1.104×, retained memory/current cache was 1.678×, and q64 total/CSE-flat was 1.459×. The prototype remains research-only.
5. **Hardware revisions / H9 — stopped before timing.** The first confirmation audit changed only 7/670 stable seeds (1.04%). The corrected selector exposed twelve BlackParrot development transitions, while the second confirmation history scanned 42 commits and admitted zero transitions. No Yosys, timing, selector, or routing claim follows.

All five appear on the master, layperson, investor, and expert pages with audience-specific framing. The expert page exposes the additional verification links.

## Reconciled learning/neural material

The preserved learning/neural route referenced two machine records that do not exist on any retained Git ref:

- `docs/recognition/runs/neural-architecture-reassessment-development-20260902-001/assessment.json`
- `docs/recognition/runs/neural-native-portfolio-reassessment-development-20260903-001/assessment.json`

Their dependent numeric claims were removed rather than reconstructed. The learning page now labels them as unsupported exclusions and links to the retained human report where appropriate. Existing frozen text bindings are accepted only when the raw hash or the LF-normalized hash matches, addressing Git CRLF checkout conversion without rewriting evidence.

## Site and publication changes

- The site builder now loads and fail-closes on all controlling September result schemas, decisions, and verification states.
- `cm_master_content_2026_08_03.json` contains a single current-research disposition model used by every audience renderer.
- `cm_master_shared.js` renders the shared disposition cards and passes every evidence target through `hostedEvidenceHref`.
- All seven published HTML routes and the GitHub Pages workflow were regenerated/reconciled, including `learning-neural-evidence.html`.
- The generated `docs/research/readers/MASTER-EXPLAINER.md` was refreshed because the new `x3` source-bound numbers are now used; the publication formatter now supports that existing website number format.
- Before/after hashes and the two-run deterministic rebuild proof are in `BEFORE-AFTER-SHA256-2026-09-09.json`.

## Validation

- Focused website suite: **46 passed, 28 subtests passed**.
- Publication, learning handoff, freeze portability, evidence, and research-check tests: **62 passed, 112 subtests passed**.
- Repository research gate: **262 current tests and 121 frozen-snapshot tests passed**.
- JSON parsing: content, generated data, claim ledger, and hash manifest passed.
- Syntax: changed Python files byte-compiled; shared JavaScript passed `node --check`.
- Structure: all seven generated HTML pages parsed with Python's standard HTML parser.
- Reproducibility: two builder runs produced byte-identical output for all eight generated site files; every recorded after-hash was rechecked.
- Stale-claim search: no authored-site match for the superseded production/reuse phrasings.
- In-app browser QA: all seven routes rendered at 1440×900 and 390×844 with zero horizontal overflow and no console warnings/errors. The narrow menu expanded and exposed the route/section links. The four audience pages each showed all five dispositions and 10–15 source links. The learning page visibly showed `Unsupported numbers excluded`. The H2/H3 controlling-summary request resolved with HTTP 200 from a repository-root local server.
- An unconstrained `pytest` from the repository root is not a valid project suite: it recursively collects duplicated tests inside archived `source_snapshot` evidence and stops with import-file mismatches. `pytest tests` also cannot collect seven pre-existing neural modules because PyTorch is absent from the project venv. No dependency was installed. The repository's canonical research gate above completed successfully.

## Remaining evidence gaps

- No production workload, production router, or deployed execution path has been validated by the September studies.
- H2/H3 need a component that passes the frozen materiality and prevalence gate before implementation work is warranted.
- H6 needs a representation estimator that passes preregistered holdout ordering before any routing experiment.
- Hardware/H9 needs an admissible held-out revision corpus before Yosys or timing work.
- Incremental compilation needs to beat the existing persistent-cache baseline and satisfy memory/economic gates.
- The two absent neural reassessment machine records remain excluded until authentic, commit-reachable artifacts exist.
