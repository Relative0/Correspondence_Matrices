# B1 — Corrected E3 fresh replay (2026-08-03)

Campaign: comprehensive benchmark refresh (CM_COMPREHENSIVE_BENCHMARK_PROMPT_2026-08-03).
Git: HEAD = origin/main = `eab8879edcb7fb13582ad9bdff7ea7c00238774d`; working tree had no
tracked modifications. Benchmarks on `.venv` Python 3.13.5 / numpy 2.3.2, Windows 10.0.19045.

## Protocol

Frozen corpus `CM_gap_e3_corrected_corpus_2026_08_02.jsonl` (SHA-256 verified
`8a6da87c…f6e68a`) through the frozen driver `cm_gap_e3_corrected_2026_08_02.py`
(SHA-256 verified `421c32af…773a8`), `--corpus <frozen> --out-dir
deliverables_n22_24\b1_e3_replay_2026_08_03` (new directory; archive untouched).
Default parameters (rounds 4, rr-passes 60, bootstrap 2000). All 192 formulas passed the
packed-equality assertion across cm/cse/cse_flat/raw arms and the wrapper, with
truth-SHA re-verification at measurement time. Wall time 44.4 s.

Acceptance evaluated by an **independent reaggregation** from raw rows
(`b1_acceptance_check_2026_08_03.py`, own bootstrap RNG, 4000 draws, no reuse of the
driver's summarize()); machine evidence `b1_acceptance_check_results_2026_08_03.json`.

## Results

| check | archived | fresh replay | status |
|---|---|---|---|
| identity fields (hashes, truths, per-arm instruction/op/load/buffer counts) | — | exact, 0/192 mismatches | PASS |
| all-corpus blocked geomean cm/cse | 0.888 [0.876, 0.899] | **0.8876** [0.873, 0.902] (stratified) | PASS (CI overlap) |
| per-stratum geomeans (k=8/12/16) | 0.871 / 0.869 / 0.925 | 0.875 / 0.868 / 0.921 | consistent |
| cm/cse_flat kernel geomean | 0.985 | **1.004** | PASS (≈parity; see note) |

Note on cm/cse_flat: the fresh value 1.004 sits on the other side of parity from the
archived 0.985 (timing-noise-scale shift, ~1.9%). Both values say the same thing the
optimization decision already recorded: CM and CSE+sharing-aware-flatten are
kernel-equivalent on this corpus; the ~1.5% synthetic residual is not stable in sign
run-to-run and must not be cited as a CM advantage.

Scope: one local Windows box, this synthetic generator only; superseded numbers
(0.843, 128×/240×) remain superseded.

## Verdict

**B1 REPLAY CONFIRMED** — the corrected-E3 headline (0.888 [0.876, 0.899] vs plain CSE;
≈parity vs CSE-flat) reproduces on current code; this replay is the reference workload
for B6.
