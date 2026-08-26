# DP-R1 Rejection Record

Decision: **rejected and reverted after the smoke gate**.

The prototype assigned exact immutable rational labels in public-key order and
used those labels for commutative child ordering. It preserved the ordered CM
DAG and exact packed result for all 25 BX1/B2/EPFL smoke formulas, but failed
both performance and memory gates decisively:

| Corpus | Rows | Candidate / baseline preparation geomean | 95% clustered interval | Traced peak ratio |
|---|---:|---:|---:|---:|
| BX1 | 10 | 1.6315 | [1.6315, 1.6315] | 1.1959 |
| B2 | 6 | 1.6952 | [1.6952, 1.6952] | 1.2131 |
| EPFL | 9 | 2.1936 | [2.0173, 2.2815] | 1.3218 |
| All | 25 | 1.8317 | [1.6786, 2.2194] | 1.2440 |

All 25 candidate rows were slower. The result is large enough that a
representative expansion cannot plausibly rescue this mechanism under the
pre-registered keep gate. The prototype's sorted descriptor insertion and
rational-label maintenance cost more than the deep comparisons they replaced.

Raw rows, environment metadata, and an exact source snapshot are retained as
`dpr1_smoke_*` in this campaign directory. The production `cm_ir.py` was
restored to its pre-experiment SHA-256; no DP-R1 runtime code was kept.
