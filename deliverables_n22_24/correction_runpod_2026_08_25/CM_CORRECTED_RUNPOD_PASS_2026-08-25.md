# Corrected CM Runpod pass — 2026-08-25

## Verdict

The three-pod corrected Runpod campaign passed. Every pod:

- verified the 69-file content-addressed input archive before execution;
- completed the full 401-row selector audit, 71-row selector-gap study,
  264-row matched CSE-flat comparison, and frozen B1 control;
- produced zero frozen-truth or timed-arm output mismatches;
- produced three internally verified exact-source snapshots; and
- was deleted before the campaign proceeded.

A postflight Runpod inventory at `2026-08-25T07:39:18.987622Z` returned zero
pods. Estimated new accrued exposure was `$0.005812`; cumulative recorded
exposure is `$0.027027`, below the `$1.00` hard cap. These figures are
runtime-rate estimates, not provider invoice data.

## Pods and controls

| Pod | CPU | Flavor | B1 geomean | Integrity | New cost |
|---:|---|---|---:|---|---:|
| 1 | AMD EPYC 9655P 96-Core | cpu3c | 0.8879 | pass | $0.001629 |
| 2 | AMD EPYC 9654 96-Core | cpu3m | 0.8814 | pass | $0.002730 |
| 3 | AMD EPYC 4564P 16-Core | cpu5c | 0.8831 | pass | $0.001453 |

All B1 controls passed their frozen acceptance test. The campaign archive was
376,504 bytes with SHA-256
`81d454e7381475e464c4286f9f4ed04d1e43f740e21bd8269b565213388d30dc`.

## Independent artifact and integrity readback

| Pod | Full rows | Full failures | Gap rows | Gap failures | Symmetric rows | Symmetric failures |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 401 | 0 | 71 | 0 | 264 | 0 |
| 2 | 401 | 0 | 71 | 0 | 264 | 0 |
| 3 | 401 | 0 | 71 | 0 | 264 | 0 |

Here a failure means either a frozen truth SHA mismatch or disagreement among
eligible CM, CSE-flat, raw-flat/raw-words, or wrapper arms. The readback was
performed locally from the downloaded CSVs, independently of the remote
worker's acceptance flag.

The nine source-snapshot manifests contained 48 source-file entries in total;
all copied bytes matched their manifest hashes. The final evidence manifest
contains 101 downloaded files, all independently hash-verified.

## Full selector policy

The current `k=16` selector passed its predeclared `1.10` geomean/zero
catastrophe gate on all three pods and all four arm/role cells.

| Pod | raw tuning | raw reused validation | CM tuning | CM reused validation |
|---:|---:|---:|---:|---:|
| 1 | 1.0016 | 1.0176 | 1.0006 | 1.0208 |
| 2 | 1.0039 | 1.0159 | 1.0010 | 1.0163 |
| 3 | 1.0044 | 1.0166 | 1.0012 | 1.0172 |

Values are regret geomeans; 1.0 is the per-row best explicit flat/words
choice. This confirms that keeping `WORDS_AUTO_MIN_VARS = 16` is conservative
on the full frozen corpus. It does not convert reused validation into untouched
held-out evidence.

## Focused k=13..15 study

The focused gap performance gate failed on all three pods, even though all
truth and arm-equality checks passed. Depending on pod and arm:

- tuning regret geomeans were approximately `1.09–1.14`, with `1–3`
  catastrophic rows;
- reused EPFL validation geomeans were approximately `1.13–1.22`;
- no alternative universal scalar threshold cleared both workload types.

This replicates the workload interaction and supports no selector change.

## CM versus sharing-aware CSE-flat

The matched strongest-comparator result replicated closely across three CPUs:

| Pod | bare CM / CSE-flat, all k | bare CM / CSE-flat, k=16 | CM wrapper / CSE-flat, all k | CM wrapper / CSE-flat, k=16 |
|---:|---:|---:|---:|---:|
| 1 | 0.9026 | 0.9766 | 2.7774 | 1.3220 |
| 2 | 0.9118 | 0.9746 | 2.8030 | 1.3676 |
| 3 | 0.9126 | 0.9752 | 2.8109 | 1.3325 |

Ratios below one favor CM. Bare CM is therefore about 9% faster overall on
this B2/B4 workload, but only about 2.4–2.5% faster at `k=16`. The public CM
wrapper remains approximately 2.8x slower overall and 1.32–1.37x slower at
`k=16`. This confirms a modest compiled-program structural reduction, not an
end-to-end CM dominance claim.

### Post-hoc paired formula-cluster intervals

After the campaign, the corrected inference implementation was applied to each
pod's immutable raw CSV. Each row remains a paired CM/CSE timing ratio; all
ambient-size repeats for one frozen formula stay in one cluster; formulas are
resampled uniformly 10,000 times on the log-ratio scale. These intervals were
not preregistered and measure formula-to-formula variation conditional on each
pod run. They do not replace repeated-run uncertainty.

| Pod | Formula-balanced all-k ratio (95% CI) | Formula-balanced k=16 ratio (95% CI) |
|---:|---:|---:|
| 1 | 0.8970 [0.8845, 0.9088] | 0.9752 [0.9618, 0.9866] |
| 2 | 0.9050 [0.8929, 0.9160] | 0.9739 [0.9619, 0.9845] |
| 3 | 0.9072 [0.8952, 0.9183] | 0.9738 [0.9603, 0.9858] |

All six intervals remain below 1.0. This strengthens the workload-specific
kernel result while retaining the original scope limits: B2/B4 formulas,
compiled evaluator boundary, and the observed CPUs.

## Evidence

- `correction_runpod_audit_2026_08_25.json` — campaign guards, input snapshot,
  environments, driver traces, acceptances, costs, and termination results.
- `postflight_runpod_inventory.json` — zero-pod postflight inventory.
- `runpod_evidence_manifest.json` — SHA-256 and size for all 101 campaign files;
  manifest SHA-256:
  `416111240d4f4422f49b661d7cdc5b817cb19908ba4c7c45cc987b6aa079bccd`.
- `pod1_*`, `pod2_*`, and `pod3_*` — raw downloaded evidence, environment
  sidecars, B1 controls, and exact-source snapshots.
