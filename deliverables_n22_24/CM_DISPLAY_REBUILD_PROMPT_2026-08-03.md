# CM Display Rebuild — Prompt for a new agent session (2026-08-03)

Copy-paste everything below into a new session.

---

## PROMPT

Act as a data-visualization/deck-rebuild agent for the CM project. The
2026-08-03 comprehensive benchmark refresh is complete and committed
(`61fec68` on `main`); your job is to build the displays (updated slide-deck
content and/or HTML chart pages) from the refreshed evidence. Do not re-run
benchmarks; do not modify any committed evidence file; write all new outputs
to new dated paths under `deliverables_n22_24\`. `COMMIT_PUSH_APPROVED = NO`
unless Brian states otherwise.

**Repository:** `C:\Users\brian\Documents\CM_Computation`, branch `main`.
Record `git rev-parse HEAD` first. Python for any data prep:
`.venv\Scripts\python.exe` (3.13.5, numpy 2.3.2).

**Read first, in order:**
1. `deliverables_n22_24\CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md` —
   the authoritative claim-by-claim map (CONFIRMED / REVISED / SUPERSEDED)
   with slide-rebuild guidance. Every display must be traceable to a row here.
2. `deliverables_n22_24\CM_BENCHMARK_REFRESH_HANDOFF_2026-08-03.md` —
   campaign overview, per-leg verdicts, headline story (§"Headline story for
   the rebuilt deck" is the narrative skeleton for the deck).
3. `deliverables_n22_24\CM_GAP_CONSOLIDATED_AUDIT_AND_ERRATUM_2026-08-02.md`
   §4–5 — corrected-E3 definitions and the supersession table.

**Data sources per display (raw rows are JSON; summaries are CSV; every
summary is derivable from its raw file):**

- **Kernel headline (CM vs plain CSE, ≈parity vs CSE-flat)**
  - Local synthetic: `b1_e3_replay_2026_08_03\cm_gap_e3_corrected_results_2026_08_02.json`
    (+ `CM_gap_e3_corrected_summary_2026_08_02.csv`; acceptance check in
    `b1_acceptance_check_results_2026_08_03.json`). Headline: 0.8876
    [0.873, 0.902]; strata 0.875/0.868/0.921; cm/cse_flat 1.004 (≈parity —
    NEVER plot the residual as a CM win; its sign is not stable).
  - External (EPFL): `cm_gap_epfl_results_2026_08_03.json`,
    `CM_gap_epfl_summary_2026_08_03.csv`,
    `epfl_run_2026_08_03\cm_gap_epfl_analysis_2026_08_03.json`. Primary:
    cm/cse_flat 0.9998 [0.975, 1.025] (circuit-clustered); secondary cm/cse
    0.927 [0.903, 0.951]; per-circuit table inside the analysis JSON.
  - Cross-platform: `b6_pod_replication_2026_08_03\b6_analysis_2026_08_03.json`
    — 5 pods, geomeans 0.877–0.888, per-pod CIs; report per-pod, never pooled.
- **Wrapper boundary (REVISED claim — rewrite this display)**
  - `b2_wrapper_2026_08_03\cm_b2_wrapper_results_2026_08_03.json` +
    `CM_b2_wrapper_summary_2026_08_03.csv`: cached/uncached ratios and
    wrapper-overhead decomposition at live_k ∈ {4,6,8,10,12,16}.
  - `b4_sweep_2026_08_03\cm_b4_sweep_results_2026_08_03.json` +
    `CM_b4_headline_summary_2026_08_03.csv`: same protocol as the old V4 C1
    slide, live_k × ambient-n grid (shows ambient n is irrelevant).
  - Message: BitSet leads at every live_k ≤ 16 (1.3–1.8×); the old
    "CM modestly ahead at 12/16" sentence and chart must not reappear.
- **Guard/decline** — `b4_sweep_2026_08_03\CM_b4_guard_summary_2026_08_03.csv`
  (decline rate by n × depth; 0 wrong guards in 3,000 trials).
- **Compile/DAG scaling** —
  `b3_scaling_2026_08_03\cm_b3_scaling_results_2026_08_03.json` + summary
  CSV: prep vs structural nodes across 5 case families; the money plot is
  prep-vs-unfolded (flat) against prep-vs-structural-nodes (linear);
  pathological ladder 8.4M unfolded → 985 µs.
- **Prep / break-even economics** — B1 rows (`cm_prep_us`, `breakeven_*`)
  and EPFL analysis JSON (`prep_multiple 4.11×`, break-even median 174.5
  finite, 55/129 never). Good display: break-even distribution with the
  never-break-even mass called out.
- **CUDD matched (same-box, new evidence)** —
  `b5_cudd_2026_08_03_run5\cm_b5_cudd_matched_results_2026_08_03.json` +
  `CM_b5_cudd_matched_summary_2026_08_03.csv`: per-stratum medians of CM
  prep / CSE-flat prep / CUDD build (construction) and CM kernel / CUDD
  256-eval / CUDD full-extract (evaluation). Keep construction and
  evaluation as SEPARATE panels; never render a single three-way winner.
  Provenance (pod CPU etc.): `b5_cudd_2026_08_03_run5\b5_pod_audit_2026_08_03.json`.

**Per-leg narrative reports (use for captions/prose):**
`b1_e3_replay_2026_08_03\CM_B1_E3_REPLAY_REPORT_2026-08-03.md`,
`b2_wrapper_2026_08_03\CM_B2_WRAPPER_BOUNDARY_REPORT_2026-08-03.md`,
`b3_scaling_2026_08_03\CM_B3_COMPILE_SCALING_REPORT_2026-08-03.md`,
`b4_sweep_2026_08_03\CM_B4_GUARD_FAMILY_SWEEP_REPORT_2026-08-03.md`,
`b5_cudd_2026_08_03_run5\CM_B5_CUDD_MATCHED_REPORT_2026-08-03.md`,
`b6_pod_replication_2026_08_03\CM_B6_POD_REPLICATION_REPORT_2026-08-03.md`,
`CM_GAP_EPFL_VALIDATION_2026-08-03.md`.
Costs/provenance: `cm_benchmark_refresh_manifest_2026_08_03.json`.

**Hard rules:**
- Superseded numbers (0.843, 128×/240×, V4 C1 "ahead at 12/16", pre-repair
  n≥18 ratios, archived 23 µs overhead) appear nowhere except an explicit
  "corrections" slide if one is wanted.
- Blocked and round-robin schedules are labeled and never pooled; CIs shown
  with their clustering basis (stratified-by-cell vs circuit-clustered vs
  per-pod).
- Every number rendered must be re-read from the raw/summary files, not
  retyped from prose; state file + field provenance in a build script so the
  charts are regenerable.
- Scope labels on every chart: synthetic generator vs EPFL AND/INV cones vs
  pod platform; live_k on the x-axis, never nominal n.
- The existing public HTML pages are frozen at Audit V4 — build new pages or
  a new deck rather than editing archived report files.

**Deliverables:** your choice of (a) new HTML chart page(s) with embedded
data arrays generated by a script, and/or (b) a slide-content markdown pack
mapping each slide to its chart + caption + claim-map row. End with a short
report listing every display, its data source files, and any claim-map row
you could not visualize.
