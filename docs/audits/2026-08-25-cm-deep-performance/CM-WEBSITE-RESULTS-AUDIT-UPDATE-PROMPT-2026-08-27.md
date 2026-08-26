# Copy-paste prompt — CM website results audit and evidence update

Project root:

`C:\Users\brian\Documents\CM_Computation`

## Mission

Conduct a rigorous claim-by-claim audit of the current CM master-explainer
website, replace stale or superseded statements with the latest accepted
repository evidence, add the important 2026-08-26/27 findings that are not yet
represented, regenerate every audience page deterministically, and validate
the result.

This is an evidence reconciliation task, not a marketing rewrite. Preserve the
site's progressive-disclosure design and its separation between equivalent
artifacts, timing windows, corpus roles, accepted results, negative results,
provisional findings, and unanswered workload questions.

## Repository preservation and authority boundaries

Before editing:

1. Read every applicable `AGENTS.md`.
2. Record branch, HEAD, `git status --short`, modified/untracked files, Python
   interpreters, Node version, and relevant package versions.
3. Expect local-only `.claude/`, `external/`, `tmp/`, generated `.pytest*`
   scratch directories, and the files named `The Broken Silence.*`. Do not
   read, modify, stage, delete, or attribute them to this task. Never read
   `.env*`, tokens, credentials, or private configuration.
4. Preserve all unrelated work exactly. Do not commit, push, deploy, publish,
   install dependencies, create cloud resources, or make external writes
   without new explicit authorization.
5. Prefer `.venv\Scripts\python.exe` for the builder and dependency-free
   checks. The established system Python may be needed for pytest because the
   repository virtual environment does not contain pytest.

Current website root:

`deliverables_n22_24\master_explainer_2026_08_03\`

The authored/build sources are:

- `cm_master_build_2026_08_03.py`
- `cm_master_content_2026_08_03.json`
- `cm_master_shared.js`
- `cm_master_shared.css`
- `cm_master_template.html`
- `cm_layperson_template.html`
- `cm_investor_template.html`
- `cm_expert_template.html`

The generated evidence/data and pages are:

- `cm_master_data_2026_08_03.json`
- `index.html`
- `layperson.html`
- `investor.html`
- `expert.html`

Treat generated HTML as build output. Make durable claim/data changes in the
builder, content JSON, shared rendering code, or templates as appropriate,
then regenerate all pages. Do not hand-edit a generated page as the only fix.

## Authoritative evidence order

Read these before assessing website claims:

1. `README.md`
2. `deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md`
3. `deliverables_n22_24/CM_BENCHMARK_REFRESH_CLAIM_MAP_ADDENDUM_2026-08-03.md`
4. `docs/audits/2026-08-25-cm-deep-performance/CM-DEEP-PERFORMANCE-AUDIT.md`
5. `docs/audits/2026-08-25-cm-deep-performance/CM-BENCHMARK-RESULTS.md`
6. `docs/audits/2026-08-25-cm-deep-performance/CM-OPTIMIZATION-BACKLOG.md`
7. `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/RUN-RESULTS.md`
8. `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/EXTERNAL-RUNS-RESULTS.md`
9. `deliverables_n22_24/master_explainer_2026_08_03/CM_WEBSITE_EVIDENCE_UPDATE_2026-08-26.md`
10. `deliverables_n22_24/memo_runpod_2026_08_26/memo_runpod_audit_2026_08_26.json`
11. `deliverables_n22_24/heldout_abc_i10_2026_08_26/abc_i10_selector_audit.json`
12. `docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/RESULTS.md`
13. `docs/audits/2026-08-25-cm-deep-performance/remaining-work/orchestration-20260826-213058/RESULTS.md`
14. `docs/audits/2026-08-25-cm-deep-performance/remaining-work/workload-intake-20260827-002305/RESULTS.md`
15. `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/RESULTS.md`
16. `docs/audits/2026-08-25-cm-deep-performance/remaining-work/three-lane-20260827-011536/DP-R2-TEMPORARY-MEMORY-POLICY-DECISION.md`
17. Machine-readable raw, audit, JUnit, environment, and source-manifest files
    referenced by those reports.

Use the newest accepted artifact for each claim. An increased test count does
not supersede a benchmark ratio. A follow-up smoke does not supersede a
preregistered representative study. If reports conflict, identify timing
window, corpus, schedule, artifact, source hash, and acceptance role before
choosing a value.

## Accepted conclusions that must not regress

- B1/E3 and EPFL remain CM/CSE-flat parity evidence; do not optimize or market
  the approximately `0.9998` residual.
- The accepted B2/B4 symmetric V3 bare-program result is workload-specific,
  not universal: overall `0.890570`, formula-cluster interval
  `[0.874065, 0.907272]`; `k=16` `0.961234`, interval
  `[0.928974, 0.994177]`.
- The public CM wrapper is a separate timing boundary and remained slower:
  overall CM/CSE-flat `3.094136`, interval `[2.883083, 3.310818]`.
- Three fresh same-host V3 repetitions ranged `0.904905–0.908991` with run
  geomean `0.907590`. They confirm direction and expose run-level variation;
  they do not silently replace the accepted V3 point.
- Preparation remains the leading raw optimization surface. The retained
  one-memo improvement reproduced locally and on three Runpod CPU flavors.
- Flat bigint stayed fastest through `live_k=12`; the word-packed engine won
  only at `live_k=16` on the accepted crossover corpus.
- The simple `k=16` engine rule transferred to 144 untouched Berkeley ABC i10
  cones at `1.012285` raw and `1.012460` CM regret with zero catastrophes. The
  frozen feature selector failed at `1.121191`/`1.136482` with 7/11
  catastrophes and was rejected without retuning.
- Direct kernels above the guard completed 16/16 bounded cases exactly, while
  the public wrapper refused all 16/16. The supported public guard remains
  `live_k=16`; there is no above-guard public speed claim.
- Complete explicit output remains `Omega(2^k / w)` work/storage. CUDD build,
  restriction, symbolic query, and full extraction are different artifacts.
- Current CM keys are engineering identity under documented normalization and
  collision assumptions, not a formal theorem of global semantic canonicality.
- Family/context improvements over uncached CM do not establish dominance over
  the strongest applicable incumbent.

## Later results the website must now audit and incorporate

Do not assume each item needs a new chart. Use the smallest clear presentation
and keep provenance near the claim.

### Synthetic cache, family, and context studies

The statement “the persistent cache has never been studied” is stale. Replace
it with the narrower accepted finding:

- the so-called persistent-cache flag was measured as a process-local,
  synthetic all-hit cache;
- it reduced CM relative to no-cache CM, but cached whole-call CM still trailed
  BitSet by `3.13x–12.84x`;
- with 50 cached evaluations, execution-only CM still trailed BitSet by about
  `2.80x` at `k=16`, `3.87x` at `k=12`, `8.91x` at `k=8`, and `11.18x` at
  `k=4`;
- no byte-LRU, durable cache, production working set, hit distribution, RSS
  plateau, or production cache policy is validated.

Related-family results remained slower than BitSet (`5.25x–26.45x` in the
reported high-reuse cells). The partial-context grid found cached CM
`4.85x–7.37x` faster than uncached CM and synthetic near-parity cells at
`n=16, c=500` (`1.108`, `0.952`, and `0.997` CM/BitSet for fixed fractions
0.25/0.50/0.75), but only under three-trial synthetic conditions without a
native CUDD restriction comparator. Present this as a hypothesis surface, not
a production route.

### Metrics-only workload tracing

Add the accepted trace result:

- full-rate V1 and V2 capture were rejected at median whole-call ratios
  `1.3037` and `1.1173`;
- deterministic one-in-16 V3 sampling was retained only as an opt-in bounded
  diagnostic at median ratio `1.0052` with zero exact mismatches, drops, or I/O
  errors;
- its per-emitted-event gate failed, sampling loses exact access order, and the
  schema contains anonymous metrics rather than replayable expressions or raw
  contexts;
- synthetic single/family/context tracing passed mechanics, schema, privacy,
  exactness, and replay-summary checks, but no real workload was found.

### Workload intake and remaining evidence gate

Represent the new strict owner-declared workload manifest/validator and its
meaning: the retained template validates structurally but is deliberately not
ready. Real cache, edit/version, partial-context, selector, and native economics
remain blocked on a named application/caller, artifact/order contract, budgets,
lifecycle, and separate data approvals. Do not describe the manifest as a
captured workload.

### Dependency feasibility

Add the RP-D0 result without converting a dependency-resolution refusal into an
algorithm result:

- three authorized disposable CPU attempts cost `$0.001948` cumulatively and
  ended with zero pods;
- the final run successfully built the pinned pure-Python `astutils==0.0.6`
  wheel, then failed closed because `dd==0.6.0` requires source-only
  `ply<=3.10` while the authorization allowed no PLY source build;
- Numba, `dd.cudd`, CUDD restriction, and native performance were not reached
  and remain untested, not failed;
- no dependency was integrated and no native/SIMD performance claim exists.

### Temporary-memory policy

Add the DP-R2 safety result:

- direct output, benchmark, and remote surfaces have different output guards
  and currently no default temporary limit;
- the current dense estimate (`2 * output_bytes`) was below median
  `tracemalloc` peak by `3.51x–38.73x` on the four bounded diagnostic cases;
- typed refusal still occurred before materialization;
- `tracemalloc` is not an RSS/native-memory upper bound, the four cases do not
  calibrate a universal multiplier, and no default changed;
- the proposed 16 MiB benchmark/remote and 64 MiB direct profiles are a future
  approval decision after estimator and compatibility work, not current
  product settings.

### Audit-tool consolidation and current validation

Record DP-R3 only as a reliability/maintainability change: three duplicate
exact-file SHA-256 helpers became one streaming helper with compatibility and
source-snapshot coverage. Its tiny smoke passed exactness but failed timing
gates and is not a performance improvement claim.

The newest repository validation is 84 focused tests and 391 tests plus four
subtests in the full suite. Present test counts as validation state, not
benchmark evidence, and retain dated older counts only when explaining a
specific earlier campaign.

## Required implementation procedure

1. Create a dated website-audit directory or report beside the master
   explainer. Record preregistration, repository state, authoritative evidence,
   exact commands, and a before-change hash manifest.
2. Build a machine-readable claim ledger covering every numeric or categorical
   result in the builder, content JSON, shared JS, and four pages. Include claim
   text/token, source file and field, evidence date/role, page/audience, status
   (`current`, `stale`, `superseded`, `missing`, `withdrawn`), and action.
3. Search explicitly for stale date ranges, “never studied/unprofiled/untested”
   wording, old test counts, old next-work priorities, universal kernel
   language, guard ambiguity, cache naming, native dependency claims, and
   values copied into prose outside `_numbers`.
4. Update `cm_master_build_2026_08_03.py` so every rendered result is loaded
   from an authoritative machine-readable artifact and receives field-level
   provenance. Update the pinned evidence revision deliberately; never derive
   it dynamically from a dirty checkout.
5. Update authored content and rendering only where required. Preserve the
   master/layperson/investor/expert audience differences and corrections ledger.
6. Regenerate all outputs with the builder. Do not remove negative evidence or
   overwrite historical accepted artifacts.
7. Review every audience page, not just `index.html`, for claim consistency,
   typography, broken navigation, chart/table overflow, mobile layout, visible
   provenance, and progressive-disclosure behavior.
8. Create a dated update report listing old wording/value, new wording/value,
   reason, authoritative source, validation, limitations, and files changed.

## Validation contract

- Run the builder twice from identical sources and prove the generated JSON and
  all four HTML hashes are identical between builds.
- Parse authored content JSON and generated data JSON.
- Byte-compile the builder and all changed Python tooling.
- Run `node --check` on `cm_master_shared.js` when Node is available.
- Parse all four generated pages with Python's HTML parser and inspect them in a
  real browser or the in-app browser when available. Record any environment
  limitation rather than claiming visual QA that did not occur.
- Confirm every new numeric token equals its cited source field and every token
  referenced by prose resolves uniquely.
- Confirm no stale result survives in generated pages by exact search.
- Run focused integrity tests covering builder evidence selection, current CM
  audit integrity, tracing/workload manifest, output budget, and any new website
  tests. Then run the complete repository suite.
- Validate JUnit/JSON/CSV artifacts, `git diff --check`, final source hashes,
  and `git status --short`.
- Do not put hardware-sensitive performance thresholds in ordinary unit tests.

## Completion deliverables

- Updated authored website sources and all regenerated audience pages.
- A claim ledger in CSV or JSON.
- A dated website evidence-update report.
- Before/after page and source hashes.
- Exact validation commands and results.
- A concise stale/superseded/withdrawn claim table.
- A ranked list of genuinely remaining evidence gaps.
- A final handoff that distinguishes task-complete local work from anything
  requiring real workload data, dependency/source-build approval, cloud use,
  deployment, publication, commit, or push.

The task is complete only when the generated website tells the current evidence
story without resurrecting withdrawn claims, promoting synthetic evidence,
blending artifact/timing boundaries, or implying that a proposed policy is
already deployed.
