# CM display rebuild — report (2026-08-03)

## Repository state

- `git rev-parse HEAD` at start of session: **`61fec684b7fdb7c914541575900ff5fc1e4f0e6e`**.
- HEAD at build time: **`6e8a283d22fb7cf643753fb6ad2d7fc3f3f2c96f`** — two commits
  landed mid-session (`891f56c` BX1 engine crossover, `6e8a283` BX2 CUDD order
  sensitivity + claim-map addendum). Both are new evidence legs; I read them and
  added two displays (C15, C16) that cover claim-map rows 14 and 15, which the
  base claim map had marked NOT RE-RUN / in-passing.
- **No committed evidence file was modified.** All output is new, under
  `deliverables_n22_24\displays_2026_08_03\`.
- `COMMIT_PUSH_APPROVED = NO` — nothing staged, nothing committed, nothing pushed.

## Deliverables

| file | what |
|---|---|
| `cm_display_build_2026_08_03.py` | build script — reads every raw/summary file, emits the data JSON and the HTML page |
| `cm_display_template_2026_08_03.html` | page template + chart library (no data) |
| `cm_display_data_2026_08_03.json` | generated data arrays with per-display file+field provenance |
| `cm_benchmark_refresh_charts_2026_08_03.html` | **the chart page** — self-contained, 17 panels, 21 charts |
| `CM_DECK_CONTENT_PACK_2026-08-03.md` | slide-by-slide content: chart id + caption + claim-map row |
| `CM_DISPLAY_REBUILD_REPORT_2026-08-03.md` | this file |

Regenerate with:

```bash
.venv/Scripts/python.exe deliverables_n22_24/displays_2026_08_03/cm_display_build_2026_08_03.py
```

## Displays built, and their sources

Every value is read from the file+field listed; nothing is retyped from prose.
The page's own "Data provenance" disclosure on each card carries the same list.

| id | display | claim-map row | source files |
|---|---|---|---|
| `#c1` | Kernel vs plain CSE — forest across 3 scopes | 1, 11, 12 | `b1_.../b1_acceptance_check_results_2026_08_03.json`; `epfl_run_2026_08_03/cm_gap_epfl_analysis_2026_08_03.json`; `b6_.../b6_analysis_2026_08_03.json` |
| `#c2` | Kernel equivalence vs CSE-flat + materiality rule | 10 | same three files (`primary_blocked_cm_cse_flat`, `round_robin_…`, `materiality`, `cm_cse_flat_geomean`) |
| `#c3` | Local strata by live_k; family × shape grid | 1 | `b1_.../CM_gap_e3_corrected_summary_2026_08_02.csv`; acceptance JSON |
| `#c4` | EPFL per-circuit dumbbell (19 circuits, both arms) | 10, 11 | `cm_gap_epfl_analysis_2026_08_03.json` (+ `CM_gap_epfl_summary_2026_08_03.csv` mirror) |
| `#c5` | Cross-platform pod replication, per-pod CIs | 12 | `b6_analysis_2026_08_03.json` |
| `#c6` | Wrapper boundary — CM/BitSet by live_k (REVISED) | 4 | `b2_.../CM_b2_wrapper_summary_2026_08_03.csv` |
| `#c7` | Wrapper overhead decomposition | 5 | same CSV (+ `cm_b2_wrapper_results_2026_08_03.json` raw) |
| `#c8` | Ambient-n irrelevance, V4-C1 protocol re-run | 6, 4 | `b4_.../CM_b4_headline_summary_2026_08_03.csv` |
| `#c9` | Decline rate by n × depth; guard totals | 7 | `b4_.../CM_b4_guard_summary_2026_08_03.csv` |
| `#c10` | Compile scaling — prep vs unfolding / vs structural nodes | 8 | `b3_.../CM_b3_scaling_summary_2026_08_03.csv` |
| `#c11` | Break-even distributions, never-break-even mass | 9 | `b1_.../cm_gap_e3_corrected_results_2026_08_02.json` `formulas[]`; `cm_gap_epfl_results_2026_08_03.json` `rows[]`; EPFL analysis JSON |
| `#c12` | CUDD matched — construction & evaluation panels | 13 | `b5_..._run5/CM_b5_cudd_matched_summary_2026_08_03.csv`, `cm_b5_cudd_matched_results_2026_08_03.json`, `b5_pod_audit_2026_08_03.json` |
| `#c14` | Blocked vs round-robin, every source | 16 | B1 replay + archived summary CSVs; EPFL analysis; B6 analysis |
| `#c15` | Engine crossover (recursive/flat/words) | addendum 15 | `bx1_.../CM_bx1_crossover_summary_2026_08_03.csv`, `cm_bx1_crossover_results_2026_08_03.json` |
| `#c16` | CUDD order search — BDD size & search cost | addendum 14 | `bx2_.../CM_bx2_cudd_orders_summary_2026_08_03.csv`, `cm_bx2_cudd_orders_results_2026_08_03.json`, `bx2_pod_audit_2026_08_03.json` |
| `#corrections` | Superseded numbers, listed once | 2, 3, 4, 5 | `_superseded` block in the build script |
| `#flags` | Claim-map prose vs raw evidence | 9, 16 | computed from the source files (see below) |

Values not present in any summary but derived by the build script, and marked as
such: the break-even histograms and medians (from `formulas[]` / `rows[]`), the
guard totals (summed over 15 cells), BX2's pure 10-build sums (from
`rows[].per_order[].build_us`), and the schedule Δ percentages.

## Hard rules — how each was honoured

- **Superseded numbers** (0.843, 128×/240×, V4 C1 "ahead at 12/16", 23 µs,
  pre-repair n ≥ 18) appear only in the `#corrections` panel and in the two
  places that explicitly name them as superseded (C6's "must not reappear",
  C7's "is superseded"). Verified by scanning the rendered DOM: the only other
  hits were `0.843` as a substring of the `0.8435` xor_dom × tree geomean.
- **≈parity never plotted as a CM win.** C2 states the residual's sign is not
  stable and shows all three scopes straddling 1.00 (1.004 / 0.9998 / 0.96–0.97).
- **Schedules labelled, never pooled.** C14 shows both for every source; no chart
  anywhere combines them.
- **CIs carry their clustering basis** — visible in every forest tooltip and
  every table view (stratified-by-cell / circuit-clustered / per-pod).
- **Scope labels on every chart** (the uppercase line above each title):
  synthetic generator vs EPFL AND/INV cones vs pod platform.
- **live_k on the x-axis**, never nominal n. C8 and C9 are the two charts where
  nominal n appears at all, and both are *about* n's irrelevance.
- **CUDD construction and evaluation are separate panels** (C12), never a
  three-way winner. C16 carries an explicit axis warning that its build window
  (conversion-only) is not B5's (manager-inclusive).
- **Existing public HTML pages untouched** — `cm_benchmark_charts.html` and
  `cm_head_to_head_explained.html` are frozen at V4 and were not opened for
  writing.

## Design/accessibility notes

Palette is the dataviz default's first three categorical slots, validated with
`scripts/validate_palette.js` under `--pairs all` in **both** modes (worst CVD
ΔE 9.2 light / 9.4 dark; worst normal-vision ΔE 24.0 / 20.9 — all pass). Aqua
sits below 3:1 on the light surface, so the relief rule applies: every chart
ships direct labels and a table view. Page is theme-aware (OS preference plus a
`data-theme` override), every chart has a hover/focus tooltip and a table-view
twin, and wide figures scroll inside their own container — the page body never
scrolls horizontally.

Three charts were reworked after looking at the rendered output: C10's "flat
against unfolding" claim was being carried by a confounded cloud, so the
controlled shared-ladder family is now drawn as its own line (that is the money
plot; the caption says why the cloud drifts); C12 panel 2 and C16 panel 2 moved
from log-scale bars to log-scale dot plots, because bars on a log axis imply a
zero baseline that does not exist; and C15's three end-labels collided at k=16,
so labelling is now selective.

## Claim-map rows I could not visualise

**None are unvisualised.** Rows 14 and 15 — which the base claim map recorded as
NOT RE-RUN and "in passing" — became visualisable when BX1 and BX2 landed
mid-session, and are now `#c15` and `#c16`.

Two rows are visualised with a caveat rather than a clean chart:

- **Row 3 (128×/240× retraction)** has no data to plot by construction — it is a
  retraction. It appears in the corrections table only.
- **Row 15's flat-vs-recursive half** is plotted directly; the *reconciliation*
  with the deck-era corpora is prose only, because the deck-era corpora were not
  re-measured this campaign. The chart shows what was measured; the caption says
  both statements are corpus-scoped.

## Flagged — claim-map prose the raw evidence does not fully support

Found while re-reading every number from its source file. Neither changes a
campaign verdict; both change how a sentence should be worded. Both are surfaced
on the chart page (`#flags`) rather than smoothed over.

1. **Row 16 — "blocked and round-robin agree within ~1–2%."** True for the
   archived 2026-08-02 run (+1.91%), for EPFL (+0.78%) and for all five pods
   (+0.51% to +0.92%). **Not true for the B1 fresh replay**, which the campaign
   designates as the reference workload: all-corpus +5.18%, per-cell up to
   +12.93% (xor_dom × shared). Recommend narrowing the claim to the external and
   pod evidence, or restating it as "within ~2% except on the synthetic corpus,
   where the schedule effect is itself run-variable." The "never pooled" half is
   unaffected and is honoured everywhere.
2. **Row 9 — "break-even median 78.5, 30/192 never."** Those are the archived
   run's numbers. The B1 fresh replay reports **median 78.0 over 157 finite and
   35/192 never**. The charts plot the replay values so they match the replay
   headline; the workload-dependence conclusion is unchanged either way.

## Verification

- Build script re-run clean; sanity block re-derives the headline (0.8876
  [0.873, 0.902]), EPFL primary (0.9998 [0.9747, 1.0249]), pod spread
  (0.8773–0.8884), guard totals (3,000 / 0 / 0) and CUDD integrity
  (`robdd_is_cudd` and full-extraction equality both true on all 192 rows).
- Page rendered and inspected in light and dark mode at 1240px: 17 panels, 21
  charts, no console errors, no horizontal body scroll.
- Every number typed into the slide pack was diffed against
  `cm_display_data_2026_08_03.json`. Three mismatches were found and corrected
  in the pack (family/shape figures, BX2 search multiples, the ladder unfolding
  factor); the family/shape mismatch also exposed a real extraction bug in the
  build script — it had been matching `family=F/shape=S` rows as if they were
  family-only marginals — which is fixed, and C3 now plots the interaction grid
  that the summary actually reports.
- No tests were run: this pass touches no production code.

## Not done (deliberately)

- Nothing committed or pushed.
- No benchmark re-run; no evidence file modified.
- The frozen V4 public HTML pages were not edited.
