# CM master knowledge base — build report (2026-08-03)

## Repository state

- `git rev-parse HEAD` at start **and** end of session:
  **`6e8a283d22fb7cf643753fb6ad2d7fc3f3f2c96f`** (branch `main`).
- Evidence campaign HEAD recorded in the manifest: `eab8879edcb7fb13582ad9bdff7ea7c00238774d`.
- **No benchmark was re-run. No committed evidence file, archived report or
  frozen public HTML page was modified.** All output is new, under
  `deliverables_n22_24\master_explainer_2026_08_03\`.
- `COMMIT_PUSH_APPROVED = NO` — nothing staged, nothing committed, nothing pushed.
- Prior display-agent output (`deliverables_n22_24\displays_2026_08_03\`) was
  reviewed and **reused, not duplicated** — see "Relationship to the display
  pack" below.

## Page inventory

| file | what it is | audience |
|---|---|---|
| `index.html` | **master knowledge base** — 8 sections, 18 charts, layered depth throughout | everyone; the source of truth |
| `layperson.html` | plain-language cut: the problem, the tools as analogies, the five situations, the decision guide | smart non-programmer |
| `investor.html` | problem breadth, proven vs open, the evidence chain as the credibility argument, priced roadmap | non-technical evaluator |
| `expert.html` | dense: every chart, every interval with its clustering basis, protocol, corrections, full token-provenance table | reviewer / researcher |
| `cm_master_build_2026_08_03.py` | build script — reads evidence, derives every figure, validates every prose token, renders all four pages | regenerability |
| `cm_master_content_2026_08_03.json` | authored prose. **Contains no measured results** — measurements appear only as `{{token}}` | editing without touching code |
| `cm_master_data_2026_08_03.json` | generated data arrays, `_numbers` token table with per-token provenance, `_flags`, `_superseded` | audit |
| `cm_master_shared.css` / `cm_master_shared.js` | shared stylesheet and chart/render library, injected into all four pages | one chart definition, four pages |
| `cm_master_template.html` + three audience templates | page structure only, no data | — |

Regenerate everything with:

```bash
.venv/Scripts/python.exe deliverables_n22_24/master_explainer_2026_08_03/cm_master_build_2026_08_03.py
```

Sizes: `index.html` 296 KB, `layperson.html` 286 KB, `investor.html` 292 KB,
`expert.html` 290 KB. Every page is fully self-contained — no external
stylesheet, script, font, image or network call.

## The one architectural decision worth knowing

**Prose never contains a number.** The content file writes `{{kernel.local}}`;
the build script resolves it from `_numbers`, where each entry carries the file
and field it was read from, and **the build fails if any token has no backing
measurement**. Hovering any bold figure on any page shows its provenance string.

This has three consequences worth stating:

1. A stale number cannot survive an evidence refresh — re-running the build
   either updates it or fails.
2. The four pages cannot drift apart. They render the same `FIG.*` objects from
   the same payload, so a derived page is structurally incapable of showing a
   different value from the master.
3. Editing prose requires no code changes, and adding a claim that is not backed
   by evidence is a build error rather than a review finding.

109 tokens are defined; 87 are referenced by prose. The 22 unused ones are
listed by the build script on every run and are kept because they are cheap and
they document what was checked (e.g. `b1.identity_mismatches`,
`sched.pod.min_pct`).

## Chart → source map

Every chart. Values are read from these files by the build script; nothing is
retyped from any report's prose. Each chart also carries this list in a
"Data provenance" disclosure on the page itself.

| figure | appears on | claim-map row | source files |
|---|---|---|---|
| `kernelForest` — CM vs plain CSE, three scopes | master §4/§6, investor, expert | 1, 11, 12 | `b1_e3_replay_2026_08_03/b1_acceptance_check_results_2026_08_03.json`; `epfl_run_2026_08_03/cm_gap_epfl_analysis_2026_08_03.json`; `b6_pod_replication_2026_08_03/b6_analysis_2026_08_03.json` |
| `flatForest` — CM vs CSE-flat + materiality rule | master §4, investor, expert | 10 | same three files (`new_cm_vs_cse_flat_geomean`, `primary_blocked_cm_cse_flat`, `round_robin_cm_cse_flat`, `materiality`, `pods[].cm_cse_flat_geomean`) |
| `strata` — family × shape grid + live_k forest | master §6, expert | 1 | `b1_e3_replay_2026_08_03/CM_gap_e3_corrected_summary_2026_08_02.csv`; acceptance JSON |
| `epflCircuits` — per-circuit dumbbell, both arms | master §4, expert | 10, 11 | `epfl_run_2026_08_03/cm_gap_epfl_analysis_2026_08_03.json` (+ `CM_gap_epfl_summary_2026_08_03.csv` mirror) |
| `pods` — 5-machine replication with per-pod CIs | master §6, investor, expert | 12 | `b6_pod_replication_2026_08_03/b6_analysis_2026_08_03.json` |
| `wrapperRatio` — CM/BitSet by live_k, cached + uncached | master §4, expert | 4 | `b2_wrapper_2026_08_03/CM_b2_wrapper_summary_2026_08_03.csv` |
| `wrapperCost` — overhead decomposition | master §4, expert | 5 | same CSV + `cm_b2_wrapper_results_2026_08_03.json` |
| `ambientN` — nominal n irrelevance | master §3, expert | 6, 4 | `b4_sweep_2026_08_03/CM_b4_headline_summary_2026_08_03.csv` |
| `guard` — decline rate by n × depth, guard totals | master §4, expert | 7 | `b4_sweep_2026_08_03/CM_b4_guard_summary_2026_08_03.csv` |
| `compileScaling` — prep vs unfolded / vs structural nodes | master §3, expert | 8 | `b3_scaling_2026_08_03/CM_b3_scaling_summary_2026_08_03.csv` + results JSON |
| `breakeven` — three-arm distributions, baselines matched | master §4, investor, expert | 9 | `b1_e3_replay_2026_08_03/cm_gap_e3_corrected_results_2026_08_02.json` `formulas[]`; `cm_gap_epfl_results_2026_08_03.json` `rows[]` (**both** arms); EPFL analysis JSON |
| `cudd` — two panels: construction, then evaluation/extraction | master §4, expert | 13 | `b5_cudd_2026_08_03_run5/CM_b5_cudd_matched_summary_2026_08_03.csv`, results JSON, `b5_pod_audit_2026_08_03.json` |
| `cuddOrders` — node sizes + order-search cost | master §4, expert | addendum 14 | `bx2_cudd_orders_2026_08_03/CM_bx2_cudd_orders_summary_2026_08_03.csv`, results JSON, `bx2_pod_audit_2026_08_03.json` |
| `engines` — recursive / flat / word-packed crossover | master §4, expert | addendum 15 | `bx1_crossover_2026_08_03/CM_bx1_crossover_summary_2026_08_03.csv` + results JSON |
| `schedule` — blocked vs round-robin, every source | master §6, expert | 16 | B1 replay + archived summary CSVs; EPFL analysis; B6 analysis |
| `correctionsTable` — superseded numbers, listed once | master §6, investor, expert | 2, 3, 4, 5 | `corrections` block in the content file; replacement figures resolved from `_numbers` |
| `flagsBlock` — claim-map prose vs raw evidence | master §6, expert | 9, 16 | computed by the build script from the source files |

Quantities **derived by the build script** rather than read from a summary, and
labelled as such on the page: the break-even histograms and medians, the
EPFL matched-baseline arm, the guard totals (summed over 15 cells), the BX2
pure ten-build sums (from `rows[].per_order[].build_us`), the CUDD
extraction-versus-kernel factors, the schedule deltas, and the prep-multiple
geomeans.

## Claim-map coverage

**Every one of the 16 base rows and both addendum rows is either visualised or
explicitly accounted for.** Three are handled with prose rather than a chart,
for reasons intrinsic to the row:

| row | why there is no chart |
|---|---|
| **3** — the 128×/240× retraction | It is a retraction. There is no data to plot by construction. It appears in the corrections ledger with the mechanism of the error. |
| **14** (base form) — "best-of-10 labelling imprecision" | The base row was recorded NOT RE-RUN. BX2 subsequently closed it **with data**, so it is charted as `cuddOrders`; the *labelling* half of the original row is prose, because it was a criticism of how a figure was described, not a measurement. |
| **15**'s reconciliation half | The flat-versus-recursive and words-versus-flat results are charted directly. The *reconciliation* with the deck-era corpora is prose only, because the deck-era corpora were not re-measured this campaign. The chart shows what was measured; the caption says both statements are corpus-scoped. |

## Hard rules — how each was honoured

- **Superseded numbers appear only in the corrections ledger.** Verified by
  scanning the rendered DOM of all four pages for `0.843`, `128×`, `240×`,
  `0.944`, `0.925`, `23 µs`, `78.5`, `30/192`. Every hit resolves to either the
  corrections table or the discrepancy-flags panel, both in the master's §6
  (and the equivalent sections of the derived pages). Two apparent hits are
  coincidental substrings of measured values read from
  `b1_e3_replay_.../CM_gap_e3_corrected_summary_2026_08_02.csv` — a family ×
  shape geomean of `0.8435` and another of `0.944` — and were confirmed against
  the source file.
- **"Kernel-equivalent" language everywhere.** `flatForest`'s caption states
  that the residual straddles parity in both directions and is therefore not a
  win in either. The materiality rule is rendered with its three conditions and
  their pass/fail state, and the page says explicitly that the *failure* is what
  made Outcome A final.
- **Blocked vs round-robin labelled, never pooled.** `schedule` shows both for
  every source. No chart anywhere combines them. The discipline section records
  which campaigns measure both (corrected E3, B1, B6, EPFL) and which are
  blocked-only (B2, B4, BX1, BX2) — a narrowing over the claim map's blanket
  wording, made after checking the per-leg reports.
- **Construction vs evaluation never merged.** `cudd` renders two separately
  captioned panels. `cuddOrders` carries an explicit axis warning that its build
  window (conversion only) is not B5's (manager-inclusive).
- **live_k on the x-axis, with one stated exception.** `guard` is the single
  chart whose x-axis is nominal n, because its question — how often is a randomly
  drawn expression from a namespace of *this size* declined — is genuinely about
  the namespace. Its caption says so. On `ambientN`, nominal n is the *series*,
  not the axis; that is what makes the within-group comparison controlled.
  (The first build got this self-description backwards in both directions; the
  audit caught it.)
- **Every chart carries** a scope label (uppercase line above the title), the
  clustering basis of any CI (in the forest tooltips and the table views), a
  table view of every plotted value, and a provenance list.
- **Baselines are matched before comparison.** See the correction below.

## Corrections I made to the received material

Three things I changed after re-deriving numbers from source, rather than
carrying the summary prose forward:

1. **Break-even comparison was baseline-mismatched.** The handoff's headline
   pairs "break-even median 78.5 (synthetic)" with "174.5 finite, 55/129 never
   (EPFL)". Those are measured against *different baselines* — plain CSE and
   CSE-flat respectively — and are not comparable. I added the EPFL
   **vs-plain-CSE** arm, recomputed from `cm_gap_epfl_results_2026_08_03.json`
   (`rows[].breakeven_evals_vs_cse`): median **105.0** over 100 finite, 29/129
   never. The chart now plots all three arms with an explicit warning about
   which pair may be compared. The matched reading is that real circuits are
   *moderately* worse than synthetic ones, not catastrophically so; the
   `55/129 never` figure is a property of a parity comparison, not of real
   circuits.
2. **Prep multiple and break-even move between the archive and the replay.**
   Recomputed from raw rows: prep geomean **4.40×** on the B1 fresh replay
   versus **4.30×** on the 2026-08-02 archive; break-even median 78.0 with
   35/192 never (replay) versus 78.5 with 30/192 (archive). The site quotes
   prep as a **range across corpora** rather than a single figure, and the
   discrepancy is published in the flags panel. The headline kernel ratio is
   unaffected — replay and archive agree to 0.0003 with overlapping intervals.
3. **The never-break-even mechanism was being misstated.** A formula is
   classified never-break-even exactly when its per-evaluation kernel gain is
   not positive. Preparation cost scales the *finite* counts but plays no part
   in that classification — so "cutting prep would rescue the never-break-even
   population" is wrong, and the page says the opposite explicitly.

## Flagged — summary prose the raw evidence does not fully support

Both are surfaced on the page (master §6, expert §6) rather than smoothed over.
Neither changes a campaign verdict; both change how a sentence should be worded.

1. **Claim-map row 16 — "blocked and round-robin agree within ~1–2%."** True for
   the archived run (+1.91%), for EPFL (+0.78%) and for all five pods (+0.51% to
   +0.92%). **Not true for the B1 fresh replay**, which the campaign designates
   as the reference workload: all-corpus +5.18%, per-cell up to 12.93%.
   Recommend narrowing to the external and pod evidence, or restating as "within
   ~2% except on the synthetic corpus, where the schedule effect is itself
   run-variable". The "never pooled" half is unaffected and is honoured
   everywhere.
2. **Claim-map row 9 — "prep 4.30×, break-even median 78.5, 30/192 never."**
   Archived values. Replay values are 4.40× / 78.0 / 35 — see correction 2 above.

*(Both flags were independently identified by the earlier display-agent pass;
this build re-derived them from source and extended flag 2 to cover the prep
multiple, which the display pass had not checked.)*

## Relationship to the display pack

`deliverables_n22_24\displays_2026_08_03\` was reviewed first and **reused
rather than duplicated**:

- Its chart library (forest, grouped columns, dumbbell, xy plot, tooltip
  binding, theme handling, card/table scaffolding) is carried forward into
  `cm_master_shared.js`, extended with a histogram, a log dot plot, a heat grid,
  a horizontal bar, a decision-flow renderer, a filterable glossary, domain and
  tool card renderers, and the `{{token}}` resolution layer.
- Its extraction logic is carried forward into the build script, with the same
  file/field provenance discipline, plus the EPFL matched-baseline arm and the
  archived-run comparison the display pass did not need.
- Its two flags were re-derived from source and one was extended.
- Its palette and accessibility posture (direct labels plus a table view on
  every chart, because the third categorical colour sits below 3:1 on the light
  surface) are carried forward unchanged.
- **The display pack itself was not modified.** It remains a valid standalone
  chart pack for slide-building; this site is the narrative artifact.

## Adversarial verification round

After the first complete build, five independent audit lenses were run over the
built pages and the build script, followed by a refutation pass that defaulted
to rejecting each reported defect unless it could be verified against a file.
**32 candidates, 27 confirmed, 5 refuted.** All 27 are fixed in the current
build. The findings worth recording:

**The numeric lens came back clean.** 107 of the 109 `_numbers` tokens were
independently re-derived from the raw evidence by a fresh script — not by
re-running the build — and reproduce to full float precision. Zero value
mismatches. The audit went a level deeper than the token table and re-derived
the *summary* layer from the *raw* rows, so the chain raw → summary → token is
verified end to end: `kernel.local` reproduces bit-for-bit as the log-space
geomean over the 192 raw B1 rows, and its interval reproduces exactly by
re-running the 24-cell stratified bootstrap at the recorded seed. The two
remaining tokens are `meta.head` (git HEAD, matches) and `guard.k` (a protocol
constant, now read out of the B4 driver rather than hard-coded). The histogram
bins were checked to sum exactly to their `n_finite` with nothing silently
dropped by the bin edges, and the BX2 search ratio was confirmed apples-to-apples
by reading the driver's timing windows.

**The supersession lens also passed cleanly** — every superseded figure appears
in exactly one place on every page, and the two apparent extra hits were
confirmed to be genuine measured values (`0.8435` and `0.944` are the
`andor_dom/tree` and `xor_dom/tree` cell geomeans). A third apparent hit, "k≥6"
in the wrapper note, was confirmed to describe the driver's dispatch threshold
rather than the retracted performance rule.

What actually failed, and is now fixed:

| class | what was wrong | fix |
|---|---|---|
| **Chart clipping** (2 major, 1 minor) | Hard-coded axis domains were narrower than their own data. The schedule chart drew the External EPFL row and the parity line off-canvas; the compile-scaling scatter clipped 6 of 31 cases out of existence, including the largest; one EPFL dot sat past the axis end. | Every ratio axis now derives its domain from the values it is about to draw, plus any reference line, via a `pad()` helper. Seven hard-coded domains replaced. Verified: zero marks outside any viewBox across all 18 charts. |
| **Lay-layer leakage** (1 major, 6 minor) | The lay override layer was incomplete: tools had `lay_name`/`lay_role` but no `lay_question`, so every "It answers" line was the expert string; scenarios and domains had no lay headings, so the layperson page led with "EDA", "SAT" and "I need a canonical form, an equivalence check, or a compact symbolic object". | Added `lay_question` to all seven tools and all five scenarios, `lay_name` to all ten domains, and rewrote four lay paragraphs that still used "support", "machine words" and "cache" cold. Verified: the only remaining term-of-art on the layperson page is "SAT solver" as a proper name, with its plain-language role and answer line beside it. |
| **A misleading lay claim** (major) | The layperson page attached "and it holds up on real hardware designs" to the synthetic figure, when the real-hardware figure is lower. | Tile now carries both figures, each labelled with its corpus. |
| **Two false self-descriptions** (minor) | The page claimed the ambient-n chart was "the one chart with nominal n on an axis" — it is not (nominal n is its *series*) — while the guard chart, which genuinely does, was not named. | Both captions and the corresponding discipline rule restated to what is actually true. |
| **Count and cross-reference drift** (4 minor) | "Eleven rules" above twelve cards; the investor page said "Twelve"; a scenario pointed at the corrections ledger for a discrepancy that lives in the flags block; the investor "the rest are boundary questions" implied four when the master says two; the layperson lede promised "no jargon, four numbers" against ~20 numeric facts. | Rule count now interpolated from `C.discipline.rules.length` so it cannot drift again; the other three restated. |
| **Ranking inconsistency** (major) | The derived pages ranked the real-workload measurement first; the master ranked preparation-cost profiling first. | The master's frontier is reordered to match the optimisation decision's own ranked list with the two completed legs removed — real-workload first, then prep, then cache. Preparation is now described precisely as the top *optimisation* surface and the third-ranked *test*, which is what the source document says. |
| **Mobile overflow** (major + minor) | The build command in the expert page's regeneration note was a 620px unbreakable token with no scroll wrapper; long pipeline-status pills were `white-space: nowrap`. | `code { overflow-wrap: anywhere }` and wrapping pills. Verified at 375px: `document.body.scrollWidth` is exactly 375 on both the master and expert pages, with no element extending past the viewport. |
| **Build-guard gap** (minor) | The token guard scanned only `{{token}}` syntax, so `T("token")` call sites in the templates and library were invisible to it — a mistyped token there would have shipped a runtime marker. | The guard now also scans `T(…)`/`TV(…)` call sites. This immediately raised the referenced-token count from 87 to 91, i.e. it was previously blind to four real uses. |
| **Provenance completeness** (2 minor) | `prep.min`/`prep.max` and `guard.k` had provenance strings naming no file. | All three now name file and field; `guard.k` is read out of the B4 driver's `max_full_output_vars` rather than hard-coded, so a driver change either updates the page or fails the build. |
| **Two others** (minor) | A dead ternary on the investor page gave `partially-answered` items the wrong pill colour; an unsourced comparative cost claim about unperformed experiments. | Ternary fixed to match the master; cost claim restated as the checkable "local profiling, instrumentation and analysis, with no cloud cost". |
| **Formatting** (minor) | Whole-number repetition counts rendered as "78.0". | New `num1s` formatter drops a trailing `.0` while staying correct if a rebuild moves a median off a whole number. |
| **Two glossary definitions** (minor) | "LM" was circular; "bra/ket measurement" explained a term with something harder. | Both rewritten. |

One defect the audit found had already been fixed mid-run by the rebuild that
caught it independently: scenario 4's plain-language layer had lost a paragraph
to an earlier edit and duplicated its opening.

## Verification performed

- Build re-run clean and idempotent; the sanity block re-derives the headline
  (0.8876 [0.873, 0.902]), EPFL primary (0.9998 [0.9747, 1.0249]), pod spread
  (0.8773–0.8884), break-even both corpora, guard totals (3,000 / 0 / 0), CUDD
  integrity (`robdd_is_cudd` and full-extraction equality both true on all 192
  rows), the BX1 fastest-engine sequence, and the BX2 node ratios.
- Token guard exercised: the build refuses to emit if any prose token lacks a
  backing measurement (it caught three during authoring). Templates and the
  shared library are scanned under the same rule, not just the content file.
- All four pages rendered and inspected: no console errors, no unresolved
  tokens, no unrendered `{{…}}` in any rendered text, no external references,
  no horizontal body scroll.
- Superseded-number DOM scan on all four pages (above).
- Layperson page audited for jargon leakage word by word; three shared strings
  were rewritten as a result — and because the master's §4 lay layer is held to
  the same bar, those rewrites improved the master too.
- **No tests were run: this pass touches no production code.** `git status
  --short` shows only new untracked files under
  `deliverables_n22_24/master_explainer_2026_08_03/` attributable to this work.

## Suggested review order for Brian

1. **`index.html` §4 "Which is better when"** — the heart of the deliverable and
   the section with the stated quality bar. Read only the blue plain-language
   blocks first and check you could answer "when would I want each tool?" from
   them alone. Then read the decision flow at the end of the section.
2. **`index.html` §6 corrections ledger and the two flags** — this is where I
   most need your judgement. Specifically: are you comfortable publishing the
   two discrepancies between the claim map's prose and the raw evidence, and is
   the "why it was wrong" column fair to each retraction?
3. **The break-even chart in §4** — the baseline-matching correction (correction
   1 above) changes how the headline story reads. Confirm you agree that the
   matched pair is the honest comparison to lead with.
4. **`index.html` §5 open frontier** — check the success/failure interpretations
   are the ones you would write, particularly for the three CM-value
   experiments, two of which currently carry negative comparative results.
5. **`layperson.html` end to end** — it is short. The question is only whether a
   non-programmer finishes it able to choose a tool.
6. **`investor.html` §5 and §6** — the "downside case" line on each open item,
   and the roadmap's priority order. Those are judgement calls I made from the
   optimisation decision's own ranking; you may want a different order.
7. **`expert.html` §8 provenance table** — spot-check a few tokens against their
   source files if you want to satisfy yourself the pipeline is honest.
8. Everything else (sections 1, 2, 3, 7) is explanatory and lower-risk.

## Not done (deliberately)

- Nothing committed, staged, or pushed.
- No benchmark re-run; no evidence file, archived report, or frozen public HTML
  page modified.
- The V4-era public pages (`cm_benchmark_charts.html`,
  `cm_head_to_head_explained.html`) were not opened for writing.
- The slide deck's *numbers* were not reused anywhere. Its structure, honesty
  conventions, capability separation, glossaries and claim-boundary framing
  were.
