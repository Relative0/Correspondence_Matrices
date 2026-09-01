# Learning milestone C29: q8 variance localization

Status: implemented and independently verified; diagnostic only, with shadow and
production promotion refused

## Question

C28 found that the unchanged support-aware candidate was exact and had a positive q8
point estimate on every recorded execution, but it did not survive paired-round
uncertainty. C29 asks where that variation enters: fixed session setup, the timed query
path, execution order, or a particular support width.

C29 does not train or refit a selector. It preserves the frozen C27 corpus, policies,
exact methods, and eight-query workload. The first analysis reads the five frozen C27
executions without rerunning them. A new local diagnostic then executes the candidate
and resident direct-screened control as adjacent pairs while counterbalancing both arm
order and width position.

## Frozen C27 localization

The five frozen executions provide 100 paired q8 width/round cells across two physical
machines.

| Width | total regressions | query regressions | overhead-only regressions | median total | median query | candidate non-query share |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 16/25 | 11/25 | 5/25 | 0.9661x | 1.0041x | 5.01% |
| 4 | 7/25 | 5/25 | 2/25 | 1.0381x | 1.0616x | 3.10% |
| 5 | 3/25 | 3/25 | 0/25 | 1.0310x | 1.0390x | 1.18% |
| 6 | 5/25 | 5/25 | 0/25 | 1.0421x | 1.0445x | 0.36% |

The 0.5972x C28 lower floor comes from Windows n=4 round 3. That cell is primarily a
query-path event: query-only speedup was 0.6152x and candidate non-query work was only
3.49% of total time. Windows n=4 round 2 was the next worst cell at 0.7031x total and
0.7281x query-only. Across all executions, however, n=3 is the persistent width-level
problem: 16 of 25 cells regress in total time.

The frozen data therefore does not support a single-cause explanation. It contains
query-path outliers, while fixed overhead accounts for five additional n=3 regressions
whose query-only ratio was at least 1.00x.

## Counterbalanced local diagnostic

The new Windows run contains 16 blocks, four widths, and two adjacent arms: **128
measurement batches**, **64 paired batches**, and **1,024 timed exact GF(2) queries**.
Every width occupies every width position equally often; each method executes first and
second equally often.

| Width | ratio-of-medians total | query-only | paired total range | candidate non-query share | first | second |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 0.8459x | 0.9784x | 0.7499-1.0076x | 14.37% | 0.8223x | 0.8984x |
| 4 | 0.9689x | 1.0415x | 0.8083-1.2211x | 7.50% | 0.9924x | 0.9954x |
| 5 | 1.0088x | 1.0334x | 0.9365-1.3321x | 2.61% | 1.0226x | 1.0065x |
| 6 | 1.0331x | 1.0423x | 0.7914-1.2135x | 0.96% | 1.0330x | 1.0383x |

The aggregate ratio of width medians is 1.0152x for total time and 1.0380x for query-only
time. Those aggregate values do not pass a promotion gate: n=3 remains materially below
the 0.90x width floor, n=4 remains slightly below 1.00x total, and individual paired
ranges are wide.

The candidate's median decomposed setup is 0.664 ms:

| Setup component | Median |
|---|---:|
| C27 policy load and validation | 0.371 ms |
| C22 policy load and validation | 0.242 ms |
| Session initialization | 0.036 ms |
| Component total | 0.664 ms |

Policy load and validation account for **92.38%** of the median decomposed setup. This
fixed cost is 14.37% of median candidate n=3 total time, 7.50% at n=4, 2.61% at n=5,
and 0.96% at n=6. The first/second-arm medians are close at n=4-n=6, but n=3 still shows
a visible order difference. Immediate adjacency reduces drift exposure; it does not make
the smallest width stable or profitable.

## Decision

C29 localizes three concrete effects:

1. repeated frozen-policy loading dominates candidate setup;
2. that fixed setup cost is large enough to erase the n=4 query-path gain and compounds
   the n=3 loss; and
3. query-path variance remains real, including the Windows n=4 C28 outliers and the new
   n=3 query regression.

The run preserves exactness, but it is local diagnostic evidence and does not supersede
C28's cross-machine ruling. Exact fallback remains mandatory. Shadow and production
promotion remain false.

## Recommended next milestone

C30 should implement an immutable prepared-policy context for the C27 and C22 policies.
It should hash-bind validated policy content, refuse changed-file or digest mismatches,
retain advice-off/fallback/tamper behavior, and charge preparation once at the resident
lifecycle boundary rather than reload both policy files for every eight-query batch.
The unchanged exact query path should then repeat this C29 counterbalanced diagnostic.
Only if n=3/n=4 improve and paired dispersion narrows should an unchanged two-machine
confirmation be frozen. A learned selector remains premature.

## Evidence

- Run: `docs/recognition/runs/c29-variance-localization-windows-20260901-002`
- Frozen localization: `docs/recognition/runs/c29-variance-localization-windows-20260901-002/frozen_localization.json`
- Measurements: `docs/recognition/runs/c29-variance-localization-windows-20260901-002/measurements.jsonl`
- Results: `docs/recognition/runs/c29-variance-localization-windows-20260901-002/results.json`
- Independent verification: `docs/recognition/runs/c29-variance-localization-windows-20260901-002/independent_verification.json`
- Harness: `cmbench/comparative/gf2_variance_localization.py`
- Runner: `scripts/cm_comparative_c29_variance_localization.py`
- Verifier: `scripts/crse_gf2_variance_localization_verify.py`
- Tests: `tests/test_cm_comparative_gf2_variance_localization.py`
