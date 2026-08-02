# CM Gap Corrected E3 — Independent Spot Replication (2026-08-03)

## Verdict

**INDEPENDENT REAGGREGATION PASSED.**

Every archived point estimate, deterministic count, break-even value, and
derived statistic of the corrected E3 results reproduces from the archived
raw rows under an independently written aggregation; an independent
cell-stratified bootstrap with its own RNG stream lands within ±0.005 of
every archived stratified CI endpoint. This closes the acceptance review's
same-session caveat for its §4A section (deterministic reaggregation), which
the acceptance handoff nominated as the sufficient spot-audit.

Machine-readable evidence:
`deliverables_n22_24\cm_gap_independent_spot_replication_results_2026_08_03.json`
(SHA-256 `24c9c739205b459f2d932ece82d39afaa02c41b47e82ed1643617740d17338c6`).

## Independence disclosure

- This replication was executed by a **new agent session** (Claude Code,
  2026-08-03), not the session that authored the corrective pass or its
  acceptance review. It was run against the committed tree at
  `eab8879edcb7fb13582ad9bdff7ea7c00238774d` (= `origin/main`).
- The reaggregation implementation
  (`tmp\cm_gap_post_acceptance_2026-08-03\independent_reaggregation_2026_08_03.py`,
  SHA-256 `13d6a83688d4d40c5f07e979393f3235be1546a0794260bcb54abc8ef566fd16`)
  was written from scratch in this session. It imports **Python stdlib only**
  (json, math, hashlib, random, csv, os, sys, collections) — no project
  module, no numpy, none of `cm_gap_e3_corrected_2026_08_02.py`, no prior
  review probe, no prior aggregation helper.
- **The driver's aggregation code was never opened or consulted.** Where the
  archived summary's definitions were not documented, they were recovered by
  candidate-testing against the archived data itself (see "Discovered
  definitions"), never by reading the prior implementation.
- All statistics helpers (geomean, median, sample sd, Pearson r, percentile
  interpolation, bootstrap) are self-implemented in the script.
- Inputs were the two frozen artifacts only: the corpus JSONL and the
  results JSON. Archived summary blocks were read solely as comparison
  targets; the recomputation path consumes only the 192 per-formula raw rows
  and the corpus records.
- The bootstrap uses `random.Random("cm-post-acceptance-independent-bootstrap-2026-08-03")`
  with 20,000 draws — a different generator (stdlib Mersenne Twister), seed,
  stream, and draw count from the driver's archived numpy bootstrap (2,000).
- No timing was rerun anywhere in this phase; all comparisons are against
  the archived deterministic data, as the protocol requires.

## Inputs verified

| artifact | SHA-256 |
|---|---|
| `CM_gap_e3_corrected_corpus_2026_08_02.jsonl` | `8a6da87cc8b13f6123cb11adfa77b5d69bcd0a086666abea7df633ef92f6e68a` (matches results `_meta.corpus_sha256` and every prior record) |
| `cm_gap_e3_corrected_results_2026_08_02.json` | `66cde08a4722ec4bff4693c0e8ce426acb6dc2756ee821d2c89942819977ec9b` |
| `CM_gap_e3_corrected_summary_2026_08_02.csv` | `39ea2df45c25a415580ea3533e52845d9990cfc1bc4c1bf037f127d29c17b53f` |

Results→corpus linkage: all 192 result rows join their corpus records by id
with exact agreement on structural hash, truth SHA-256, stratum, family,
shape, unfolded occurrences, and structural DAG nodes; per stratum, 64/64
distinct structural hashes and 64/64 distinct truth functions.

## What reproduced (19/19 checks green)

Comparison policy (fixed before running): integers/booleans/IDs/label sets
bit-exact; floats recomputed from the same archived doubles at relative
tolerance 1e-9; independent stratified bootstrap endpoints within ±0.005.

1. **All 60 summary rows** (30 groups × blocked/round-robin — the full
   independently reconstructed grid of 3 strata × [stratum, 4 families,
   2 shapes] + 8 family×shape interactions + all): `n_formulas`, `geomean`,
   `median`, `sigma_log`, `df`, `n_distinct_truth` all reproduce.
   **Maximum float relative deviation 2.0e-16** (one ulp; summation-order
   noise). Headline confirmed: blocked all-corpus geomean
   0.8879217710221067, strata 0.8707/0.8687/0.9247; round-robin all
   0.9049; every integer exact.
2. **Break-even recomputes exactly** for all 192 formulas under one rule:
   never-break-even iff `cse_kernel_us − cm_kernel_us ≤ 0`, else
   `max(0, ceil((cm_prep_us − cse_prep_us)/(cse_kernel_us − cm_kernel_us)))`.
   The 30 never-break-even IDs match as a set; median over the 162 breaking
   formulas = 78.5 exactly; family split 17 impeqv_dom / 9 mixed /
   4 andor_dom / 0 xor_dom and shape split 24 tree / 6 shared both confirmed.
3. **Derived statistics** match the recorded acceptance-review values to
   0 relative deviation: instruction-ratio geomean 0.6927770203 (xor_dom
   0.4547), executed-op ratio median 1.000 (family geomeans 0.9136–0.9733,
   share below parity 34.4%, min 0.4737), prep multiple 4.2993905408 (range
   rounds to 2.0–6.1), CM/CSE-flat geomean 0.9849806190 (192 rows),
   corr(log instr ratio, log kernel ratio) 0.8240074016, wrapper overhead
   median 22.7 µs (report's "23 µs").
4. **Distinct truth-function counts** per group recomputed from corpus
   truth SHA-256s; all match.
5. **Independent stratified bootstrap** (family×shape cells fixed, own RNG):
   8/8 `stratified_by_cell` rows within ±0.005 on both endpoints — worst
   |Δ| 0.00113 (round-robin live_k=12 lower endpoint). Blocked all-corpus:
   mine [0.876258, 0.899060] vs archived [0.876441, 0.899072]. The 52
   plain per-formula bootstrap rows also all landed within ±0.005
   (informational; archived 2000-draw Monte-Carlo error dominates at n=16).
6. **Raw-row internal consistency**: per-row `blocked_ratio_median` equals
   the median of its four round ratios; `prep_ratio_cm_vs_cse` equals
   `cm_prep_us/cse_prep_us`; wrapper overhead equals total − kernel;
   `packed_equal_all_arms` true on all 192; schedule/rounds/repeats uniform.
7. **Summary CSV** agrees with the results-JSON summaries on all 60 rows at
   1e-12 (both derive from the same aggregation; cross-format consistency).

## Discovered definitions (documentation nuances, not defects)

- **Summary median is a log-space median.** The archived summary's `median`
  is `exp(median(log r))`: with even group sizes it interpolates the two
  middle *logs*, i.e. the geometric mean of the two middle ratios. A plain
  arithmetic median mismatches all 60 rows in the ~5th decimal; the
  log-space definition reproduces all 60 **bit-exactly**. All display-
  rounded values cited in the accepted reports (3 decimals) are unaffected.
  This is coherent with the rest of the pipeline (geomean, sigma_log, and
  the bootstrap all operate on logs) but is worth one documentation line if
  the summary schema is ever formalized.
- **Break-even rule** as in item 2 above (ceil, clamped at 0; never iff no
  kernel gain). Recorded here because no prior document states the exact
  tie/edge handling.

## Process disclosure (for auditability)

The first run of the replication script used the plain arithmetic median
and returned `INDEPENDENT REAGGREGATION FAILED` on exactly the 60 `median`
fields (all other checks green). Root cause was diagnosed read-only
(candidate medians tested against three groups, then all 60 rows), the
log-space definition was confirmed bit-exact, the script was corrected, and
the premature FAILED-verdict JSON — created minutes earlier by this same
session — was deleted and regenerated at the same path by the corrected
script. No pre-existing artifact was touched at any point. Diagnostic
script preserved at
`tmp\cm_gap_post_acceptance_2026-08-03\diagnose_median_basis.py`.
Under the protocol's mismatch rule this counts as a definitional recovery,
not a data discrepancy: the archived numbers were never in conflict with
the raw rows under any coherent definition tested, and the final
implementation reproduces them exactly under the stated one.

## Environment

- Interpreter: `C:\Users\brian\Documents\CM_Computation\.venv\Scripts\python.exe`
  (Python 3.13.5); no third-party packages used by the replication script.
- Repository state during replication: `main`, HEAD = `origin/main` =
  `eab8879edcb7fb13582ad9bdff7ea7c00238774d`; working tree contained only
  the expected pre-existing untracked items plus this phase's new files.

## Files

- This report: `deliverables_n22_24\CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md`
- Evidence JSON: `deliverables_n22_24\cm_gap_independent_spot_replication_results_2026_08_03.json`
  (`24c9c739205b459f2d932ece82d39afaa02c41b47e82ed1643617740d17338c6`)
- Scratch (preserved): `tmp\cm_gap_post_acceptance_2026-08-03\`
  (`independent_reaggregation_2026_08_03.py`
  `13d6a83688d4d40c5f07e979393f3235be1546a0794260bcb54abc8ef566fd16`,
  `diagnose_median_basis.py`, `inspect_schema.py`)

**INDEPENDENT REAGGREGATION PASSED**
