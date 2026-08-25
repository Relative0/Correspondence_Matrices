# CM benchmark audit correction — 2026-08-25

## Bottom line

The correction pass found no semantic mismatch or evidence that CM was given
different formulas, variable assignments, fixed inputs, backend thresholds, or
truth targets than its comparators. It did find and correct four audit-quality
problems: EPFL variable-order verification, an inaccurate held-out label, a weak
primary comparator in the symmetric follow-up, and fragmented exact-source
provenance.

The corrected results are less sweeping than “CM beats CSE”:

- Against plain raw-AST execution, both sharing-aware CSE-flat and CM reduce
  work. On the matched B2/B4 successor, CSE-flat/raw is `0.905` and bare
  CM/raw is `0.823` overall.
- Against sharing-aware CSE-flat, bare CM is `0.909` overall on this successor,
  accompanied by `0.952x` as many instructions and about `0.93x` as many
  primitive operations. The benefit narrows with support size: CM/CSE-flat is
  `0.979` at `k=16`.
- The public CM wrapper is not faster. It is `2.797x` CSE-flat overall and
  `1.343x` at `k=16`; against raw current execution it is `2.532x` overall and
  `1.087x` at `k=16`.
- Prior B1/E3 parity (`0.9998`, interval `[0.9747, 1.0249]`) remains valid for
  that workload. The new result establishes workload-specific structural
  reduction, not universal CM dominance.

## What CSE means

Common subexpression elimination (CSE) recognizes repeated expression
subtrees, computes each once, and reuses the result. For example, if `(A AND B)`
appears three times, CSE stores one result instead of evaluating the same tree
three times.

Plain structural CSE may still retain binary associative chains. CSE-flat also
flattens safe single-use associative chains into fewer n-ary instructions. CM
performs this sort of flattening plus its canonical normalization and merging.
CM is beneficial when those transformations remove enough instructions to
repay compilation and wrapper costs, especially when the compiled artifact is
reused. The current evidence does not show that repayment for one-off complete
truth-table calls: preparation remains roughly four times the comparison
compiler in accepted evidence, and the public wrapper remains slower.

## Corrected issues

### 1. EPFL order and frozen truth verification

Problem: the earlier deep-audit driver packed EPFL variables in evaluator order
without asserting each corpus record's frozen truth SHA-256. This did not give
CM an advantage because every timed arm used that same input tuple and agreed,
but it meant most EPFL `packed_sha256` fields were not directly comparable to
the corpus digest.

Correction:

- EPFL semantic variables are mapped back to the frozen corpus's LSB-first
  input axes and reversed for the evaluator's MSB-first key contract.
- Syntactic-but-semantically-dead axes are fixed identically for every timed
  arm, then expanded back into the full syntactic truth table for the frozen
  digest assertion.
- A missing or mismatched truth digest aborts before evidence is written.
- The benchmark CSV distinguishes the reduced semantic packed digest from the
  separately verified frozen digest.

Result: `401/401` frozen digests verified and `401/401` rows had identical
eligible raw-flat, raw-words, CM-flat, CM-words, and wrapper outputs.

### 2. Validation labels

Problem: B2 and EPFL were called held out even though they had informed selector
selection, including rejection of `k=13`.

Correction: BX1 is labeled `tuning`; B2 and EPFL are labeled
`validation_reused`. Future feature-based selector acceptance requires a newly
frozen untouched validation corpus.

### 3. Strongest generic comparator

Problem: the first symmetric successor compared the public CM wrapper primarily
with raw-AST execution. Raw AST is useful as an ablation, but sharing-aware
CSE-flat is the stronger generic structural comparator.

Correction: the primary comparison now uses the same expression object,
support tuple, fixed bindings, current `k=16` flat/words policy, alternating
measurement schedule, batches, and rounds for bare CM and sharing-aware
CSE-flat. Raw AST is explicitly an ablation, and the CM wrapper is reported as
a separate boundary. The CSV includes expected/observed truth hashes and
instruction/primitive-operation counts.

Result: `264/264` frozen digests and all-arm packed outputs passed. The
statistical follow-up uses 24 rounds, an exact common counterbalance cycle for
the four-arm current-policy and six-arm explicit schedules. It reports paired
formula-cluster percentile-bootstrap intervals with 10,000 deterministic
resamples. Each unique frozen formula contributes one mean log ratio, keeping
all ambient-size repeats in the same resampled cluster.

| Live support | Timing rows | Unique formulas | formula-balanced bare CM / CSE-flat | paired formula-cluster 95% CI |
|---:|---:|---:|---:|---:|
| 4 | 32 | 32 | 0.833 | [0.786, 0.880] |
| 6 | 32 | 32 | 0.857 | [0.803, 0.912] |
| 8 | 56 | 40 | 0.866 | [0.838, 0.891] |
| 10 | 32 | 32 | 0.902 | [0.870, 0.938] |
| 12 | 56 | 40 | 0.914 | [0.883, 0.946] |
| 16 | 56 | 40 | 0.961 | [0.929, 0.994] |
| All | 264 | 216 | 0.891 | [0.874, 0.907] |

Ratios below one favor CM. These are evaluator-boundary kernel results after
compilation, not preparation-inclusive or public-wrapper speedups. The
row-weighted headline from the same run is `0.897`; the formula-balanced
headline is primary because the 24 B4 formulas otherwise receive three ambient
size rows apiece. The interval measures formula-to-formula variation
conditional on this machine and run; it does not model between-run timing or
between-machine variation. The existing three-pod replication addresses those
separate robustness dimensions descriptively.

### 4. Exact-run source provenance

Problem: historical environment hashes, manifests, and the later working tree
could refer to different source states.

Correction: every corrected writer refuses overwrite, hashes its corpora and
sources, and captures the listed source bytes used in a sibling
`*_source_snapshot` directory with its own SHA-256 manifest. The statistical
successor expands that list to all eight direct and transitive project modules
in its execution closure. Earlier evidence remains immutable and is not
retroactively described as containing files its manifest omitted.

## Selector results after correction

The full corrected selector replay preserves the policy conclusion:

| Arm / role | Rows admitted | Current-policy regret geomean | Max | Rows `>=2x` |
|---|---:|---:|---:|---:|
| raw / tuning | 80 | 1.0047 | 1.258 | 0 |
| raw / reused validation | 307 of 321 | 1.0112 | 1.591 | 0 |
| CM / tuning | 80 | 1.0030 | 1.193 | 0 |
| CM / reused validation | 321 | 1.0100 | 1.900 | 0 |

The focused `k=13..15` local rerun also preserves the rejection of a universal
width-only threshold change. All `71/71` rows pass frozen truth and all-arm
equality. Under the predeclared `1.10`/zero-catastrophe gate, the current policy
passes raw tuning, raw reused validation, and CM tuning, but fails CM reused
validation because one row reaches `2.174x` regret. No selector change is made.

## Evidence

- `selector/current_corrected_raw.csv` — 401 corrected rows.
- `selector/current_corrected_selector.csv` and
  `selector/current_corrected_summary.json` — selector and phase aggregation.
- `selector/current_corrected_environment.json` and
  `selector/current_corrected_source_snapshot/` — command, environment, corpus
  hashes, and exact sources.
- `selector_gap/current_corrected_raw.csv`,
  `selector_gap/current_corrected_selector.csv`, and
  `selector_gap/current_corrected_audit.json` — 71-row gap rerun.
- `symmetric/audited_v3_raw.csv`, `symmetric/audited_v3_summary.csv`,
  `symmetric/audited_v3_inference.csv`, and `symmetric/audited_v3_audit.json` —
  exact-counterbalance 264-row structural-CSE successor with paired
  formula-cluster inference. `audited_v3_source_snapshot/` preserves all eight
  project modules in the run's execution closure. The earlier
  `symmetric/current_corrected_*` and `audited_v2_*` files remain immutable
  historical correction evidence but are superseded for the local headline.

## Runpod addendum — 2026-08-25

The corrected full, gap, and strongest-comparator drivers were subsequently
replicated on three guarded Runpod CPU pods. All three passed input hashes,
frozen truth, arm equality, exact-source snapshots, and B1 controls; all were
deleted and postflight inventory returned zero pods. Estimated new accrued
exposure was `$0.005812` and cumulative recorded exposure was `$0.027027` under
the `$1` hard cap; these are runtime-rate estimates, not provider invoice data.

The full selector gate passed on all pods, while the focused `k=13..15` gate
failed on all pods, preserving the decision not to change the selector. Bare
CM/CSE-flat was `0.903–0.913` overall and `0.975–0.977` at `k=16`; the public CM
wrapper remained slower. See
`../correction_runpod_2026_08_25/CM_CORRECTED_RUNPOD_PASS_2026-08-25.md`.
