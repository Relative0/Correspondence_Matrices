# Independent report review

Review scope: `REPORT.md` against the already reaggregated predecessor evidence,
the corrected `ladder-run-002.json`, `ladder_summary.json`, task source and
`task-run-001/TASK_RESULTS.json`. This was a read-only evidence review plus
targeted report corrections; no diagnostic timing or fixture execution occurred.

## Checks and findings

- Independently checked all 137 corrected ladder records: each records exact
  complete-output agreement, and every exclusive phase partition sums to its
  own phase-pass wall total. The recorded remainder range is 2.437%–66.092%.
- Independently recomputed the report's k16 cold and resident medians from raw
  samples; the stated CSE/CM-common/public values agree after rounding.
- Checked public-minus-bare k16 and range statements against the corrected
  ladder summary. These are differences of separately measured medians, not
  exclusive causal wrapper fractions.
- Confirmed the task result has 70 declared cells and separate source/import
  provenance. The public family branch returns statistics and hashes references;
  custom family branches deliver CM/CSE packed outputs. The report now explicitly
  distinguishes their contracts.
- The predecessor arithmetic independently reproduces all nine gate point
  ratios. Forty-five recorded predecessor source hashes remain stable, with
  26 saved-binding comparisons matching. Existing semantic flags are checked;
  no predecessor inputs were replayed.

## Targeted corrections made to REPORT.md

1. Replaced ambiguous `2^live-k` notation with the exact remaining-variable
   cofactor output bound.
2. Added the measured library boundary: session construction, cache clearing,
   physical file loading and teardown are excluded. The resident q64 loop repeats
   an identical result without answer caching; it is a persistence diagnostic,
   not evidence of useful application reuse.
3. Added concrete public-minus-bare values and labeled their incremental,
   nonexclusive interpretation.
4. Added the public-family statistics/reference-hash versus packed-output
   distinction, preventing a same-contract interpretation across those arms.
5. Corrected the residual classification: scalar validation is present by code,
   but assigning all 88.2% of CM SAT's residual to it is not a supported causal
   inference. The individual share remains unknown.
6. Removed wording that could imply measured native counting/CUDD evidence.
   Native SAT and existing CNF/factorized-count/portable-BDD evidence remain
   separately identified.
7. Added the post-snapshot flat-metric caveat, and clarified that complete-output
   cost is shared by all competitors with that contract.

## Remaining boundaries

The final synthesis must retain the existing phase dilation, quantized CPU,
tracemalloc scope, statistical independence and unsupported dependency limits.
`TASK_FINDINGS.md`, `PROFILE_RESULTS.json`, `TIME_LEDGER.md`, `ROOT_CAUSE_MATRIX.md`,
`VERIFICATION.md` and the final manifest were being completed by the parent at
review time; final link resolution and full manifest verification belong to that
completion pass. No unsupported optimization, routing or scientific promotion
claim remains in the reviewed report. **No scientific disposition changed.**
