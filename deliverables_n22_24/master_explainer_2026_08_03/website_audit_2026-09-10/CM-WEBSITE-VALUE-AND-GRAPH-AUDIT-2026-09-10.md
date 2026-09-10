# CM website value and graph audit — 2026-09-10

## Executive determination

The deployed site is byte-for-byte identical to `origin/main` / `HEAD` **81d19034d5a63072b6521b5349b37060e170c377** for all seven HTML routes and `og.png`. It is therefore pushing and publishing correctly. It is **not yet fully current as an evidence summary under the normal 2026-09-08 cutoff**:

1. **Flattened CSE:** `1.0038` is a valid historical B1/E3 local kernel ratio, but it is not the latest current headline. The later exactly counterbalanced B2/B4 V3 bare ratio is **0.8905696773 [0.8740654100, 0.9072717742]**. Because these are CM-time/baseline-time ratios, values below 1 favor CM. Keep `1.0038` only as explicitly historical. Keep the separate public-wrapper result **3.094136**, which shows the wrapper remained slower.
2. **C16 exact screening:** the displayed local Windows **3.545324×** whole-path result is correct for that machine, but the accepted same-contract Linux confirmation is missing: **3.177887×** whole-path and **3.117978×** p95, with 40 cases, 360 measurements, zero semantic mismatches, and zero artifact mismatches.
3. **C6 exact packed source-ANF:** an accepted positive result is missing. Recomputed from the saved same-split total medians, cached packed source-ANF is **1.313448×** faster than truth-vector ANF on test and **1.637157×** on confirmation; p95 speedups are **2.175615×** and **1.835850×**. Accuracy and canonical-partition accuracy are 1.0 with zero semantic mismatches. The packed core advanced; the learned hybrid gate and production promotion did not.
4. **Feature-model k=16:** the displayed CM/direct-CNF warm-output ratio **0.276951 [0.200748, 0.371722]** is correctly shown as promising, task-specific, and performance-provisional. The CUDD ratio **0.624416 [0.215794, 1.535452]** crosses parity and is correctly not a “CM wins” headline.
5. **Current architecture:** the Sep-4 complete-relation, multi-root, small-task, and query-ladder findings are current for the normal cutoff and are materially qualified. The Sep-10 q64 adjudication is post-cutoff and correctly absent; its fully charged native values (**0.949341× Windows, 0.977972× Linux**) fail the 1.10 materiality gate and are not a new positive public use case.

## Frozen states

| State | Identity / finding | Audit use |
| --- | --- | --- |
| Live GitHub Pages | 8/8 assets HTTP 200 and SHA-256-equal to HEAD | what the public sees |
| origin/main | 81d19034d5a63072b6521b5349b37060e170c377 | remote publication source |
| local HEAD | 81d19034d5a63072b6521b5349b37060e170c377 | committed audit source |
| Authored/generated site at HEAD | data, content, builders, templates, shared JS/CSS, seven pages | published claim construction |
| Dirty worktree | 14 status entries; 7 generated site assets differ from HEAD | inventoried only; not treated as public truth |
| Recent Sep 9–10 evidence | q64 two-host no-go and local in-progress site edits | separate unpublished inventory |

The exact hashes and dirty-state list are in `BEFORE-SITE-SHA256-2026-09-10.json`.

## Coverage

- Rendered routes inspected in the in-app browser: **7**.
- Rendered SVG occurrences: **52**; distinct chart definitions: **22**.
- Tables: **141** with **1,619** rendered body rows.
- Link occurrences: **374**.
- Provenance-bearing `span.num[title]` occurrences: **947** with **271** distinct provenance titles across routes. The learning/neural route has no such spans because its tables use plain `T()` output; Phase 2 should expose equivalent token/provenance metadata there and in chart/table values.
- Broken images: **0**. Browser console errors observed: **0**.
- Named provenance-bearing numeric tokens: **417**; referenced from authored/data render paths: **392**.
- Chart/table backing numeric scalar occurrences inventoried: **1165**.
- The JSON/CSV ledger contains **2,318** records, including named values, every numeric scalar in every chart backing block, decision/status claims, missing accepted results, and post-cutoff findings.

## Ratio and timing contract rules applied

- CM/baseline **time ratios** (`kernel.*`, `flat.*`, `symv3.*`, feature-model endpoint ratios): below 1 favors CM.
- Named-candidate **speedups** (`recognition.c16.*`, architecture speedups): above 1 favors the named candidate.
- Kernel, prepared/warm output, wrapper/whole-call, complete-relation, related-root, and repeated-query contracts were not substituted for one another.
- Cross-host absolute timings were not compared. Cross-host evidence is used only when each host reports a within-host ratio under the frozen contract.
- A point estimate is not called positive when its interval crosses parity.
- Obsolete/weak baselines remain historical context, not current-use-case proof.

## Derived-value checks

| Check | Formula / condition | Result | Expected | Verdict |
| --- | --- | --- | --- | --- |
| R-C6-TEST-MEDIAN | 696850 / 530550 | 1.3134483083592499 | 1.3134483083592499 | PASS |
| R-C6-CONFIRM-MEDIAN | 572350 / 349600 | 1.6371567505720823 | 1.6371567505720823 | PASS |
| R-C6-TEST-P95 | 6029500 / 2771400 | 2.175615212527964 | 2.175615212527964 | PASS |
| R-C6-CONFIRM-P95 | 7404900 / 4033500 | 1.8358497582744515 | 1.8358497582744515 | PASS |
| R-FM-K16-CNF-GEOMEAN | geomean(seven equal-history ratios) | 0.27695056244310456 | 0.27695056244310456 | PASS |
| R-FM-K16-CUDD-GEOMEAN | geomean(seven equal-history ratios) | 0.6244162624190654 | 0.6244162624190654 | PASS |
| R-FM-K16-CUDD-PARITY | CI low < 1 < CI high | [0.21579397181382115, 1.5354521589706307] | crosses parity | PASS |
| R-C16-LINUX-WHOLE | verified JSON speedup field | 3.177887162605386 | 3.177887162605386 | PASS |

All eight recomputations pass. The chart renderer and adjacent value tables consume the same embedded committed data, eliminating a separate handwritten chart-value channel.

## Validation executed

- Website surface: **47 tests and 28 subtests passed** across master-site, navigation, feature-model, learning/neural, and recent-disposition suites.
- C6 packed source-ANF: **3 tests passed** with `unittest` in `.venv-crse-neural` (the default `.venv` cannot collect this module because PyTorch is not installed; the neural environment has PyTorch but not pytest).
- C16/GF(2): **8 tests passed**.
- Sep-10 q64 execution evidence: **3 tests passed**.
- Architecture comparison analysis: **3 tests passed**.
- Cross-machine query-ladder package: **8 tests passed**.
- Audit artifact validation: all required files exist; JSON parses; all 2,318 claim IDs are unique; CSV and JSON both contain 2,318 claims; all required claim fields are populated; all eight recomputations pass; all 22 charts are present; no normalized tracked artifact reference is broken; both intentionally absent neural assessments are classified as explicit exclusions.

## Chart audit

| ID | Routes | Section | Accessible name | Backing block | Numeric scalars | Table rows | Verdict/action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CHART-01 | index.html / layperson.html | #fig-assignment-growth | Explicit answer-vector growth | e18_assignment_growth | 9 | 4 | values match HEAD/live; add SVG title/desc |
| CHART-02 | index.html / expert.html | #fig-ambient | grouped columns | e8_ambient_n | 81 | 9 | values match HEAD/live; add SVG title/desc |
| CHART-03 | index.html / expert.html | #fig-compile | Preparation versus unfolded size | e10_compile_scaling | 195 | 31 | values match HEAD/live; add SVG title/desc |
| CHART-04 | index.html / expert.html | #fig-wrapper | Wrapper ratio by live_k | e6_wrapper_ratio | 46 | 6 | values match HEAD/live; add SVG title/desc |
| CHART-05 | index.html / expert.html | #fig-wrapper-cost | grouped columns | e7_wrapper_cost | 23 | 6 | values match HEAD/live; add SVG title/desc |
| CHART-06 | index.html / layperson.html / investor.html / expert.html | #fig-breakeven | Finite versus never-break-even shares | e11_breakeven | 41 | 3 | values match HEAD/live; add SVG title/desc |
| CHART-07 | index.html / investor.html / expert.html | #fig-breakeven-distribution | Break-even distributions | e11_breakeven | 41 | 7 | values match HEAD/live; add SVG title/desc |
| CHART-08 | index.html / investor.html / expert.html | #fig-kernel | CM versus plain CSE across three scopes | e1_kernel_vs_cse | 21 | 7 | values match HEAD/live; add SVG title/desc |
| CHART-09 | index.html / expert.html | #fig-engines | Engine crossover by live_k | e15_engines | 64 | 10 | values match HEAD/live; add SVG title/desc |
| CHART-10 | index.html / expert.html | #fig-guard | grouped columns | e9_guard | 138 | 15 | values match HEAD/live; add SVG title/desc |
| CHART-11 | index.html / expert.html | #fig-cudd-build | grouped columns | e12_cudd | 39 | 3 | values match HEAD/live; add SVG title/desc |
| CHART-12 | index.html / expert.html | #fig-cudd-eval | Evaluation and extraction costs | e12_cudd | 39 | 3 | values match HEAD/live; add SVG title/desc |
| CHART-13 | index.html / expert.html | #fig-cudd-orders | grouped columns | e16_cudd_orders | 38 | 3 | values match HEAD/live; add SVG title/desc |
| CHART-14 | index.html / expert.html | #fig-cudd-orders | Order-search cost | e16_cudd_orders | 38 | 3 | values match HEAD/live; add SVG title/desc |
| CHART-15 | index.html / expert.html | #fig-epfl | EPFL per-circuit ratios | e4_epfl_per_circuit | 68 | 19 | values match HEAD/live; add SVG title/desc |
| CHART-16 | index.html / investor.html / expert.html | #fig-flat | CM versus CSE-flat across accepted workload scopes | e2_kernel_vs_cse_flat | 15 | 9 | values match HEAD/live; add SVG title/desc |
| CHART-17 | index.html / investor.html / expert.html | #fig-roadmap | Roadmap effort by priority | _content.frontier | 12 | 6 | values match HEAD/live; add SVG title/desc |
| CHART-18 | index.html / investor.html / expert.html | #fig-pods | Per-pod replication | e5_pods | 35 | 5 | values match HEAD/live; add SVG title/desc |
| CHART-19 | index.html / expert.html | #fig-schedule | Schedule comparison | e14_schedule | 116 | 8 | values match HEAD/live; add SVG title/desc |
| CHART-20 | index.html / expert.html | #fig-strata | Family × shape interaction grid | e3_local_strata | 47 | 11 | values match HEAD/live; add SVG title/desc |
| CHART-21 | index.html / expert.html | #fig-strata | Local strata by live_k | e3_local_strata | 47 | 11 | values match HEAD/live; add SVG title/desc |
| CHART-22 | index.html / investor.html / expert.html | #fig-discrepancies | Absolute schedule shift | e17_discrepancies | 12 | 5 | values match HEAD/live; add SVG title/desc |

Chart values are intact and backed by visible tables. Every SVG has `role="img"` and an `aria-label`; all 22 landing-page charts have keyboard-focusable marks (246 marks total) and the shared tooltip uses an ARIA live-status region. None has an SVG `<title>` or `<desc>`. Phase 2 should add those elements while retaining keyboard detail and tables. This is an accessibility/traceability improvement, not evidence that plotted values are wrong.

## Contract-level verdicts

| Surface | Current display | Latest accepted same-contract evidence | Verdict | Phase-2 action |
| --- | --- | --- | --- | --- |
| Landing: CM vs flattened CSE | 1.0038 historical B1/E3 local | 0.8905696773 [0.8740654100, 0.9072717742] B2/B4 V3 bare; wrapper 3.094136 | historical value valid, headline stale/ambiguous | lead with B2/B4 V3; retain 1.0038 in a dated historical row |
| C16 latest evidence | 3.545324× local Windows whole path; minimum 0.892796× | 3.177887× Linux whole path; 3.117978× p95; exact 40/40, 360 rows | local correct, cross-machine confirmation omitted | show both machines and preserve no-production qualification |
| Learning C6–C12 timeline | coarse aggregate; no C6 positive numbers | C6 1.313448× test, 1.637157× confirmation; exact; packed core only | material accepted result omitted | split C6 from later milestones and add downloads |
| Feature-model k=16 direct CNF | 0.277 [0.201, 0.372] | same saved warm-output contract | current and properly provisional | retain caveat; do not call cold-pipeline/domain dominance |
| Feature-model k=16 CUDD | 0.624 [0.216, 1.535] | same saved extraction contract | interval crosses parity | retain as inconclusive |
| Architecture/query ladder | Sep-4 current table with limitations | same through normal cutoff | current | preserve task/host/baseline qualification |
| Post-cutoff q64 | not displayed | Sep-10 0.949341× / 0.977972× fully charged no-go | correctly outside default public set | later review may add only as a limitation/no-go |

## What this audit does not authorize

This is Phase 1 only. It does not change public copy or charts, package/copy artifacts into the site, commit, push, deploy, or approve Sep 9–10 findings for publication. Fresh benchmark execution was not needed: calculations were replayed from accepted machine-readable results, and the live deployment was checked against the exact committed assets.

## Review gate

Approve the Phase-2 backlog explicitly before modifying the site. The three evidence-content priorities are: current flattened-CSE headline/labels, C16 Linux confirmation, and the missing C6 positive exact result. Artifact publication also needs an explicit licensing decision and manual privacy review for operational manifests/archives.
