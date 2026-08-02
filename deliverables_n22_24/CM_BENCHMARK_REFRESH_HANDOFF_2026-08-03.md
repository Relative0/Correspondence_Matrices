# CM Benchmark Refresh — Handoff (2026-08-03)

Self-contained record of the comprehensive benchmark campaign
(`CM_COMPREHENSIVE_BENCHMARK_PROMPT_2026-08-03.md`). All seven benchmark
families executed; deck can be rebuilt from
`CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md`.

## Repository state

- `main`, HEAD = origin/main = `eab8879edcb7fb13582ad9bdff7ea7c00238774d`
  (recorded before and after; `git diff --stat` empty — **no tracked file
  was modified**). All campaign outputs are new untracked files.
- Benchmarks: `.venv` Python 3.13.5, numpy 2.3.2, Windows 10.0.19045
  (AMD Ryzen 5 PRO 5650U). Tests: system Python 3.10.11.
- Full suite after adding Python files: **334 passed, 0 failed, 4 subtests,
  196.4 s** (baseline 326 + 8 new EPFL parser tests;
  `--basetemp tmp\pytest_cm_bench_2026-08-03`).

## Per-benchmark verdicts (reports end with the same lines)

| leg | verdict | evidence dir |
|---|---|---|
| B1 E3 replay | REPLAY CONFIRMED (0.8876, identity exact, cm/cse_flat 1.004 ≈parity) | `b1_e3_replay_2026_08_03\` |
| B2 wrapper boundary | COMPLETE — deck claim REVISED (BitSet leads at all live_k ≤ 16) | `b2_wrapper_2026_08_03\` (+ pilot dir) |
| B3 compile scaling | COMPLETE — scaling claim CONFIRMED (985 µs on 8.4M-unfolded ladder) | `b3_scaling_2026_08_03\` |
| B4 guard + n=16–24 | COMPLETE — guard CONFIRMED (0 violations / 3,000), headline REVISED | `b4_sweep_2026_08_03\` |
| B5 CUDD matched (pod) | COMPLETE — CUDD boundary CONFIRMED same-box (192/192 full-extraction equal) | `b5_cudd_2026_08_03_run5\` |
| B6 5-pod replication | CROSS-PLATFORM REPLICATION PASSED (5/5, spread 0.011) | `b6_pod_replication_2026_08_03\` (+ `_run2\`) |
| B7 EPFL external | EXTERNAL VALIDATION SUPPORTS GENERALIZATION (0.9998 vs CSE-flat; Outcome A now FINAL) | `CM_GAP_EPFL_VALIDATION_2026-08-03.md` |

Costs: **$0.0158 total pod spend** (cap $5), all pods terminated; one ~111 MB
EPFL clone (never staged). Machine-readable:
`cm_benchmark_refresh_manifest_2026_08_03.json`.

## Failure log (all pre-measurement, none affecting evidence)

- RunPod proxy 404 race on `/put` right after bootstrap health (3 pods lost,
  ~$0.002; fixed with retry).
- B5 dd install: env-var route installs pure-python dd 0.5.7; correct route
  is `setup.py install --fetch --cudd` (+cython, gcc); dd.cudd.Function has
  no `^` operator (use `bdd.apply`); CUDD tarball host times out sometimes
  (retry). Worth remembering for any future CUDD pod.
- EPFL extractor: `_eval_words` packs `vars_key[0]` as the MSB axis; the
  corpus truth convention is LSB-first — measurement passes reversed
  vars_key (caught by the truth-SHA gate before any timing; parser tests pin
  the convention).

## Headline story for the rebuilt deck

1. Kernel level: repaired CM is 7–13% faster than plain structural CSE
   (0.888 synthetic, 0.927 external, 0.877–0.888 across 5 Linux pods) and
   **kernel-equivalent to CSE+sharing-aware-flatten everywhere** (1.004
   local, 0.9998 external, 0.96–0.97 pods). Mechanism: n-ary instruction
   merging. Outcome A is final: differentiators are canonical keys,
   persistent cache, serde — not kernel speed.
2. Wrapper level: BitSet leads at every measured live_k ≤ 16 on
   exact-support corpora; overhead 50–91 µs. The old "modestly ahead at
   12/16" sentence must not reappear.
3. Costs: prep 4.1–4.3× CSE; break-even median 78.5 (synthetic) / 174.5
   finite with 55/129 never (EPFL) — reuse-count dependence is the story.
4. CUDD: compact builds, but packed output 74×–12,800× slower; keep it a
   separate comparison, never a three-way winner.

## Proposed commit decomposition (DO NOT EXECUTE — `COMMIT_PUSH_APPROVED = NO`)

1. `bench(epfl): external validation campaign (SUPPORTS GENERALIZATION)` —
   `tests/test_epfl_aiger_parser.py`,
   `deliverables_n22_24/cm_gap_epfl_extract_2026_08_03.py`,
   `CM_gap_epfl_corpus_2026_08_03.jsonl`, `cm_gap_epfl_results_2026_08_03.json`,
   `CM_gap_epfl_summary_2026_08_03.csv`, `cm_gap_epfl_provenance_2026_08_03.json`,
   `CM_GAP_EPFL_VALIDATION_2026-08-03.md`, `epfl_run_2026_08_03/`
2. `bench(refresh): local B1–B4 refresh drivers and evidence` —
   `cm_b2_wrapper_boundary_2026_08_03.py`, `cm_b3_compile_scaling_2026_08_03.py`,
   `cm_b4_guard_family_sweep_2026_08_03.py`, `b1_e3_replay_2026_08_03/`,
   `b2_wrapper_2026_08_03/`, `b2_wrapper_pilot_2026_08_03/`,
   `b3_scaling_2026_08_03/`, `b4_sweep_2026_08_03/`
3. `bench(pods): B5 CUDD matched + B6 cross-platform replication` —
   `cm_b5_*.py`, `cm_b6_*.py`, `b5_cudd_2026_08_03*/`,
   `b6_pod_replication_2026_08_03*/`
4. `docs(bench): claim map, manifest, campaign handoff` —
   `CM_BENCHMARK_REFRESH_CLAIM_MAP_2026-08-03.md`,
   `cm_benchmark_refresh_manifest_2026_08_03.json`,
   `CM_BENCHMARK_REFRESH_HANDOFF_2026-08-03.md`
   (plus, if desired, the seven pre-existing post-acceptance deliverables per
   the master handoff's own decomposition)

Never stage `.claude\`, `tmp\`, `external\`, or historical prompts. Stage
files individually. Commit messages end with the repo's
`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` convention.

## Remaining decisions for Brian

- Approve the commit decomposition above (and the earlier post-acceptance
  deliverables still uncommitted from the previous pass).
- Rebuild the deck per the claim map (claim 4's slide needs rewriting).
- Optional next work, in the optimization decision's own ranking: prep-cost
  profiling (top surface now that Outcome A is final), reuse-distribution
  measurement, cache-behavior study.

**BENCHMARK REFRESH COMPLETE**
