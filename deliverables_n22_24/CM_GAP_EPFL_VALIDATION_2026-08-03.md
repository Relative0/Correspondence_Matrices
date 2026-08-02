# CM Gap Series — EPFL External Validation (2026-08-03)

Executed per the frozen protocol `CM_GAP_EPFL_PROTOCOL_2026-08-03.md`, as
written, with `EPFL_DOWNLOAD_APPROVED = YES` (granted 2026-08-03). Git
`eab8879` (HEAD = origin/main); benchmarks `.venv` Python 3.13.5 / numpy
2.3.2, Windows 10.0.19045; tests system Python 3.10.11.

## 1. Provenance and extraction

- Shallow clone of `https://github.com/lsils/benchmarks.git` at commit
  `0060e156826e733d69bf5b3322d1bdd0d03a1f9a` into
  `external\epfl-benchmarks` (never staged; contents unmodified). Manifest:
  `cm_gap_epfl_provenance_2026_08_03.json` (20 `.aig` files, SHA-256 each,
  license SHA, on-disk size 111,550,671 bytes total clone).
- New in-repo binary-AIGER parser (delta-decoded per AIGER 1.9) + ASCII
  parser for fixtures; **8 parser/extractor tests pass**
  (`tests/test_epfl_aiger_parser.py`; exhaustive truth-table checks,
  latch rejection, binary/ASCII structural identity, independent bigint
  evaluator vs reference CSE pipeline). No new dependency installed.
- One execution defect was found and fixed **before any campaign timing**:
  the first pilot attempt failed its truth-SHA gate because the measurement
  passed `vars_key` in ascending order while the corpus truth SHA uses
  LSB-first variable order (`_eval_words` packs `vars_key[0]` as the MSB
  axis — verified empirically). Fix: reversed `vars_key` in measurement
  only; the corpus, admission, and truth definitions were untouched, no
  timing data existed yet, and the parser tests were extended to pin the
  convention. This is an implementation-detail correction inside the
  extractor, not a change to any pre-registered rule; the protocol file was
  not edited.
- Extraction (deterministic, protocol §3): **129 admitted cones** from 19
  circuits (per-circuit cap 8), 23 cross/within-circuit duplicates recorded,
  `ctrl.aig` yielded no qualifying cone (rejection histogram recorded — all
  199 candidate cones below semantic support 8). No cone referenced an AIG
  constant literal (the no-constant-node concern was moot). Corpus:
  `CM_gap_epfl_corpus_2026_08_03.jsonl`, SHA-256
  `bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac`.

## 2. Measurement

Pilot (protocol §4): 8 formulas (adder, arbiter), all packed-equality gates
passed, projected full campaign 0.9 min — under the 60-minute gate. Full
campaign: **129/129 rows ok, 0 runtime-guard skips, packed equality across
cm/cse/cse_flat(/raw where eligible) and the wrapper on every formula,
truth SHA re-verified at measurement time**; wall 42.0 s. Raw rows:
`cm_gap_epfl_results_2026_08_03.json`.

## 3. Results (independently reaggregated from raw rows before citation —
`epfl_run_2026_08_03\cm_gap_epfl_reaggregate_2026_08_03.py`, all checks pass)

| statistic | value | 95% CI (circuit-clustered, 4000 draws, seed 20260803) |
|---|---:|---|
| **Primary: CM/CSE-flat blocked geomean** | **0.9998** | [0.9747, 1.0249] |
| CM/CSE-flat round-robin geomean | 1.0076 | [0.9969, 1.0167] |
| Secondary: CM/plain-CSE blocked geomean | 0.9268 | [0.9026, 0.9507] |
| Prep multiple CM vs CSE-flat (geomean) | 4.11× | — |
| Break-even vs CSE-flat | median 174.5 over 74 finite; **55/129 never** | — |
| Instruction ratio CM/CSE-flat (geomean) | 1.000 | — |
| Executed-op ratio CM/CSE-flat (geomean) | 1.000 | — |

By semantic-support bucket (descriptive): 8–10 → 1.018 (n=64); 11–13 →
0.986 (n=36); 14–16 → 0.978 (n=29). Blocked and round-robin agree within
~1% and are never pooled.

Mechanism check: on AND/INV-form circuits CM emits exactly the CSE-flat
instruction and executed-op counts (both ratios exactly 1.000) — there are
no associative same-op chains beyond what sharing-aware flattening already
merges, so the corrected-E3 mechanism (n-ary instruction merging) predicts
parity here, and parity is what is measured. The residual advantage vs
*plain* CSE (0.927) is the flattening effect itself, consistent with the
synthetic mechanism story.

## 4. Materiality rule (§6, applied as pre-registered)

1. CM/CSE-flat geomean ≤ 0.95? **NO** (0.9998).
2. Circuit-clustered CI excludes parity? **NO** (upper 1.0249).
3. Median break-even ≤ 1000 evals? YES (174.5 finite median; but 55/129
   never break even).

Conditions fail ⇒ **CM and CSE+sharing-aware-flatten are declared
kernel-equivalent for real-circuit workloads**; the ~1.5% synthetic
residual is not chased. Per the optimization decision's one-directional
provisionality, **Outcome A converts from provisional to final.**

## 5. Scope

Real AND/INV combinational circuits (EPFL arithmetic + random_control),
cones with syntactic support ≤ 16 and semantic support 8–16, one local
Windows box. The corrected-E3 synthetic result generalizes in the sense
tested: kernel parity with CSE-flat, a real but modest advantage over plain
CSE, mechanism = instruction merging, and prep-cost economics (4.11× here
vs 4.30× synthetic) with break-even structure intact.

## Verdict

**EXTERNAL VALIDATION SUPPORTS GENERALIZATION**
