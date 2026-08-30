# CRSE Milestone D9: frozen natural profitability policy

Date: 2026-08-29  
Status: **complete; exact gate and abstention mechanism, negative profitability result**

## Question

Can a cheap structural policy be trained away from the prior D5/D8 EPFL cases,
bound to a measured machine calibration, frozen, and then used to decide whether
one proved-rule pass is worth paying for on a new natural representation?

## Leakage-controlled design

The run uses the pinned `lsils/benchmarks` checkout at commit
`0060e156826e733d69bf5b3322d1bdd0d03a1f9a` under its MIT license.

- Training: 10 cones from five `best_results/depth` control circuits.
- Validation: two cones from the separate `mem_ctrl` depth circuit.
- Evaluation: 11 cones from six circuit-disjoint `best_results/size` circuits:
  `priority`, `voter`, `div`, `max`, `multiplier`, and `sin`.
- Each cone is measured at 8, 32, and 128 expected reuses.
- The selected split circuits do not overlap. Their expression digests also have
  zero overlap with the D5/D8 natural cases.

The selector uses bounded structural extrema and never consults rule incidence
or timing. Calibration, the 120-row training measurement file, training manifest,
and inert JSON policy are written and hashed before validation or evaluation
BLIF is parsed. The policy accepts only seven cheap structural/calibrated features,
has a maximum depth of three, requires a predicted 5% gain, and falls back to
no rewrite for invalid metadata, calibration mismatch, or a feature outside the
training range.

The BLIF reader handles bounded single-output LUT on-set and off-set tables.
An independent packed LUT evaluator supplies every correctness oracle outside
the timed arms. A saturating reachability scan keeps oversized arithmetic cones
bounded while preserving exact metadata for admitted cones.

## Results

The retained run contains 23 natural cones, 501 measurement rows, and 28,056
repeated complete-vector comparisons. Every comparison agreed with the
independent BLIF oracle. The independent artifact verifier passed all 15 retained
artifacts and reproduced all structural decisions and rule applications.

| Evaluation result | Value |
| --- | ---: |
| Semantic mismatches | 0 |
| Frozen gate applications | 0 / 33 workloads |
| Frozen gate abstentions | 33 / 33 workloads |
| In-range, insufficient predicted gain | 23 |
| Outside training range | 10 |
| Gate vs no-rewrite speedup | 0.9818x |
| Unconditional one-pass vs no-rewrite speedup | 0.4290x |
| Gate regret vs free per-workload oracle | 1.86% |

The fitted cost tree correctly collapsed to one conservative leaf. Its normalized
training costs were 1.000 for no rewrite and 3.141 for one pass. All 33 evaluation
workloads were also individually faster under the measured no-rewrite control,
so the policy's abstention decisions were directionally correct. The gate still
cost 1.8% end to end because its metadata check and decision are charged; it did
not apply a rewrite and therefore did not earn a rewrite speedup.

The negative timing result is not caused by an absence of recognized structure.
At one representative 128-use pass, the evaluation cones contained 43 proved
common-factor applications across seven of 11 cones. Those rewrites reduced the
aggregate flattened CSE operation count from 478 to 437. Training had 104 such
applications and validation had 76. The reduction was too small to repay matching,
rewriting, and rebuilding on these bounded cones.

## Interpretation

Milestone D9 establishes the intended safety architecture:

1. machine calibration is explicit and identity-bound;
2. fitting uses only the training source;
3. the model is inert, bounded JSON;
4. the model is frozen before other splits are loaded;
5. novelty produces abstention;
6. exact BLIF semantics remain authoritative.

It does **not** establish profitable learned rewriting. Unconditional one pass was
about 2.33 times slower than no rewrite, and the learned policy found no positive
region to promote. Production promotion remains refused.

The evaluation uses new optimized BLIF artifacts, a new LUT/SOP representation,
and a circuit-disjoint split, but it remains inside the EPFL suite. This is not
independent benchmark-family confirmation.

## Evidence

- Retained run: `docs/recognition/runs/natural-profitability-policy-20260829-003`
- Verification: `docs/recognition/verification/natural-profitability-policy-20260829-003.json`
- Runner: `scripts/cm_recognition_natural_profitability_policy.py`
- Verifier: `scripts/crse_natural_profitability_policy_verify.py`
- Policy implementation: `cmbench/recognition/profitability_policy.py`
- BLIF implementation: `cmbench/recognition/blif.py`

No network access, dependency installation, cloud resource, deployment, or
external write was used for this milestone.
