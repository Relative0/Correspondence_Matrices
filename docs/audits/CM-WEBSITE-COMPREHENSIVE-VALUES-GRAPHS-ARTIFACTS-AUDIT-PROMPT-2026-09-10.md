# Copy-paste prompt — comprehensive CM website values, graphs, and evidence-artifact audit

Project root:

`C:\Users\brian\Documents\CM_Computation`

## Objective

Audit every factual result currently displayed by the public Correspondence
Matrices website, including every number embedded in prose, tiles, tables,
charts, plotted series, annotations, tooltips, legends, captions, alt text, and
generated data. Determine whether each item is the newest accepted evidence for
the same experimental contract, or a correctly labelled historical result.

Produce an implementation-ready audit before changing public claims. Then, only
after the audit is reviewed and explicitly approved, update the authored site
sources, regenerate the site, and add safe downloadable evidence artifacts.

Accuracy and provenance are more important than favorable presentation. Do not
publish a stale value, silently replace a result with a different task, omit an
unfavorable outcome, or promote development/provisional evidence.

Public site:

`https://relative0.github.io/Correspondence_Matrices/`

Website source root:

`deliverables_n22_24\master_explainer_2026_08_03\`

## Hard scope and safety boundaries

1. Read every applicable `AGENTS.md` and inspect repository status before work.
2. Treat the working tree as live and potentially dirty. Preserve unrelated
   changes and untracked files. Never read `.env*`, credentials, tokens, private
   keys, local databases, or credential caches.
3. This is an audit-first task. Do not alter website claims, copy artifacts into
   publication paths, commit, push, deploy, create cloud resources, or make any
   external write until the audit deliverables are complete and the user has
   explicitly authorized the implementation phase.
4. The normal evidence cutoff is accepted, commit-reachable work through
   **2026-09-08**. Inventory September 9–10 work separately as recent/unpublished;
   do not use it for a public claim unless a later review explicitly accepts it.
5. Audit the live deployment, `origin/main`, authored templates/build inputs,
   generated pages/data, and the current worktree as distinct states. Never
   assume they are identical.
6. Do not install dependencies or run unrestricted recursive test discovery.
   Use the repository's established targeted website and research gates.

## Phase 1 — exhaustive claim and graph audit

### 1. Freeze the observed state

Record:

- audit date/time and evidence cutoff;
- live URL and deployed revision/workflow run if discoverable;
- local branch, HEAD, `origin/main`, remotes, and relevant worktrees;
- `git status --short` without modifying the tree;
- SHA-256 hashes of every live/generated site page and generated data asset;
- the builder, templates, content JSON, shared JavaScript/CSS, and workflow used
  to produce the site.

Audit all seven routes and shared assets:

- `index.html`
- `layperson.html`
- `investor.html`
- `expert.html`
- `usecases.html`
- `feature-model-evidence.html`
- `learning-neural-evidence.html`
- generated JSON/JavaScript, chart data, shared assets, social-preview assets,
  and the GitHub Pages workflow

### 2. Inventory every displayed claim

Create one ledger row for every:

- numeric tile or headline;
- ratio, speedup, percentage, count, range, interval, threshold, cost, memory,
  test count, date, revision, or status in prose;
- table cell or derived summary;
- chart series and every plotted point, error bar, reference line, annotation,
  tooltip value, axis transformation, unit conversion, and aggregation;
- qualitative conclusion such as `wins`, `parity`, `failed`, `verified`,
  `current`, `provisional`, `not promoted`, or `never tested`;
- download/evidence link and its claimed role.

Do not limit the audit to visible authored literals. Trace generated values from
template/rendering code through generated site data to the original evidence
field. Inspect client-side chart construction; values that appear only after
JavaScript execution still count.

For each claim, record at minimum:

| Field | Required content |
|---|---|
| Claim ID | Stable unique identifier |
| Location | Page, section/anchor, element, and source template/build location |
| Presentation | Tile, prose, table, chart series/point, tooltip, etc. |
| Displayed claim | Exact displayed value/text, units, rounding, and direction |
| Provenance chain | Renderer token → generated data → file and machine field |
| Contract identity | Requested artifact, numerator/denominator, timing boundary, lifecycle, corpus/split, host/compiler, source hash, schedule, aggregation, and interval method |
| Evidence role | Accepted, provisional, development-only, historical, invalid, stopped, superseded, withdrawn, or unsupported |
| Latest match | Newest accepted evidence for the **same contract** |
| Verdict | Current, current-but-misleading, historical-correctly-labelled, stale, superseded, missing, unsupported, or unverifiable |
| Action | Keep, relabel, replace, add context, move to history, remove, or block pending evidence |
| Downloads | Required public artifacts and their publication status |

### 3. Apply a strict supersession test

A newer date alone does not supersede a result. Before replacing anything,
match all of the following:

- identical requested output/artifact;
- identical ratio direction and comparable numerator/denominator;
- identical timing boundary (kernel, preparation, wrapper, whole call, resident,
  warm/cold, extraction, delivery, cleanup, etc.);
- compatible lifecycle and reuse/query count;
- compatible corpus role and split;
- current/frozen source identity and relevant implementation changes;
- valid schedule/counterbalancing and statistical basis;
- accepted decision status and independent verification where required.

If the contract differs, create a separate scoped result instead of overwriting
the older one. Never pool hosts, runs, formulas, circuits, histories, or cohorts
unless the controlling protocol explicitly authorizes that aggregation.

Machine-readable results control numbers. Decision/adjudication records control
status and promotion. Reports provide interpretation. Missing machine evidence
must be labelled unsupported rather than reconstructed from prose.

### 4. Audit calculations and graph integrity

Independently recompute every displayed derived value from the cited raw or
summary fields, including geometric means, speedups, inverse ratios, percentage
changes, confidence intervals, cluster weighting, minima/maxima, break-even
counts, and chart transforms. Confirm that:

- ratio direction is stated and interpreted correctly;
- `below 1 favors CM` and `above 1 favors CM` conventions are never mixed;
- rounding cannot reverse parity or materiality;
- graph axes, logarithmic scales, error bars, labels, and tooltips match data;
- legends and colors map to the correct series;
- hidden/filtered points, refusals, failed runs, and unfavorable cases are not
  silently dropped;
- charts do not compare unlike artifacts or timing boundaries;
- prose summaries agree with tables and charts on every audience page.

### 5. Known checkpoints — investigate, do not assume exhaustive

At minimum, resolve these already identified issues:

1. The landing tile `CM vs a flattened CSE kernel` displays historical
   `1.0038`, while the builder's current B2/B4 V3 row is `0.8905696773` with
   interval `[0.8740654100, 0.9072717742]`. Determine the correct headline,
   scope, date, and historical placement. Preserve the separate public-wrapper
   result (`3.094136...`) and do not turn a bare-kernel win into a whole-call win.
2. C16 exact screening displays the local Windows `3.5453x` whole-path result;
   audit the later verified Linux values (`3.1779x` whole path and `3.1180x`
   p95) and determine where both should appear.
3. Audit the independently verified C6 packed exact source-ANF results
   (`1.313x` test and `1.637x` confirmatory versus truth-vector ANF), which are
   not presently surfaced as a positive exact-algorithm result.
4. Preserve the feature-model k=16 CM/direct-CNF value (`0.277` with its
   history-cluster interval) as task-specific and performance-provisional. Do
   not upgrade the CM/CUDD k=16 ratio to a robust win because its interval
   crosses parity.
5. Confirm current architecture results and caveats: CM over dense CM, CM versus
   direct BitSet, related multi-root union gains, Windows/Linux native results,
   query-count ladder outcomes, individual regressions, and guarded/opt-in
   status.
6. Treat improvements against an obsolete or deliberately weak CM baseline as
   internal progress, not automatically as a positive use case against the
   strongest current task-matched algorithm.

### 6. Audit positive-use-case coverage

Create a dedicated table of every accepted positive CM or CM-family result.
Include only comparisons with an explicit task, artifact, lifecycle, and strong
applicable control. For each, state:

- what CM method actually won;
- what comparator it beat;
- exact value and interval/variation;
- task/corpus/host and timing boundary;
- whether the gain replicated;
- whether any individual case regressed;
- whether it is implemented, guarded, experimental, or unpromoted;
- where it appears on the website, or why it is missing.

Alongside it, create a `not a positive use case` table for parity, overall losses
with favorable subcomponents, provisional comparisons, unlike-artifact
comparisons, invalid attempts, oracle-only headroom, and development-only
results. This prevents cherry-picking.

## Phase 1 deliverables

Write these under a new dated directory beside the existing website audits:

1. `CM-WEBSITE-VALUE-AND-GRAPH-AUDIT-YYYY-MM-DD.md` — executive verdict plus
   complete claim-by-claim findings.
2. `CM-WEBSITE-CLAIM-LEDGER-YYYY-MM-DD.json` (and CSV if useful) — the
   machine-readable ledger described above.
3. `CM-WEBSITE-POSITIVE-USE-CASE-AUDIT-YYYY-MM-DD.md` — accepted positive cases,
   counterevidence, qualifications, and missing coverage.
4. `CM-WEBSITE-DOWNLOADABLE-ARTIFACT-MANIFEST-YYYY-MM-DD.md` and `.json` — exact
   files to expose, hashes, sizes, licenses/privacy status, claim IDs, and
   proposed public URLs.
5. `CM-WEBSITE-UPDATE-BACKLOG-YYYY-MM-DD.md` — prioritized, implementation-ready
   changes grouped as critical correctness, stale presentation, missing result,
   missing download, and optional UX improvement.
6. `BEFORE-SITE-SHA256-YYYY-MM-DD.json` — live and repository state hashes.

Stop and present the audit for review. Do not begin Phase 2 without explicit
authorization.

## Phase 2 — authorized website and download implementation

After explicit approval of the audit:

1. Make durable changes in builders, content JSON, shared renderers, templates,
   and tests. Treat generated HTML/data as build outputs; never hand-edit them
   as the only fix.
2. Update or add charts from machine-readable evidence only. Keep historical
   series when scientifically useful, clearly dated and visually distinguished
   from current results.
3. Add an `Evidence & downloads` surface, both near relevant claims and in a
   central index. Each item must identify purpose, scope, date, status, format,
   size, SHA-256, and whether it is raw data, analysis, protocol, source freeze,
   independent verification, test result, or narrative report.
4. Prefer stable repository-hosted download links to duplicating large evidence.
   Use immutable commit-pinned GitHub links where practical and direct download
   URLs for downloadable files. If files must live in the Pages tree, use a
   versioned evidence directory and generate its index from the artifact
   manifest.
5. Include the relevant, reasonably sized artifacts for each public result:
   machine summary JSON, raw CSV/JSONL where safe, analysis/adjudication,
   protocol/preregistration, independent verification, checksums/source
   manifest, environment record, and focused test/JUnit results. Link test
   source files when they materially explain validation.
6. Do not publish secrets, credentials, absolute private paths, local databases,
   unnecessary cloud metadata, third-party corpora without redistribution
   permission, unverifiable scratch files, duplicated source snapshots, or huge
   logs/bundles without a clear public purpose. Record exclusions and reasons.
7. Ensure every download exists, matches its recorded hash, is reachable with
   correct path/case/MIME handling, and is associated with at least one claim or
   reproducibility purpose. No dead or decorative evidence links.

## Phase 2 validation

- Rebuild twice from identical sources and prove byte-identical generated
  outputs.
- Recompute every public token and graph point from its cited field.
- Add regression tests that fail when a headline selects a non-current row
  without an explicit historical label.
- Test all evidence/download links locally; after separately authorized
  deployment, verify every public URL returns the expected bytes and SHA-256.
- Parse all JSON/CSV/JUnit and generated HTML; byte-compile changed Python;
  run `node --check` on changed JavaScript.
- Run focused website/publication/research gates and report pre-existing or
  environment-limited failures honestly.
- Perform desktop and mobile browser QA on all seven routes, including graph
  rendering, tooltips, legends, download controls, navigation, overflow,
  accessibility text, and console/network errors.
- Run stale-value searches against both authored and generated content.
- Record before/after hashes, exact commands/results, `git diff --check`,
  `git diff --stat`, and final `git status --short`.

## Completion standard

The audit is complete only when every displayed result and graph datum has a
contract-matched provenance decision and every relevant evidence artifact has a
safe publication disposition. The implementation is complete only when the
site accurately distinguishes current, historical, provisional, negative,
invalid, and unpromoted evidence; exposes verified downloads; passes the stated
checks; and leaves no stale generic headline such as a historical value selected
over an available current result.

Do not commit, push, or deploy unless the user separately authorizes the exact
target and effect.
