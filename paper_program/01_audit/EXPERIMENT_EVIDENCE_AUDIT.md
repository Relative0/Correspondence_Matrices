# Later code and experiment evidence audit

Audit date: 2026-09-14  
Observed current worktree: `C:\Users\brian\Documents\CM_Computation`, `main` at `72041c23ceebc257afc977c9e744b762bccaf21c`

This audit treats the repository's correction reports as evidence about specific frozen artifacts and timing boundaries. It does not transfer those results to a broader claim such as “CM is faster.”

## Artifact distinctions required in the paper

| Artifact | Meaning | Size/cost implication |
|---|---|---|
| Explicit CM | A Boolean truth relation reshaped by ordered row and column variables | Contains `2^k` bits/cells for `k` live variables; a square layout for `2m` variables is `2^m x 2^m`. |
| CM IR | An interned Boolean-operation DAG with selected rewrites and live-variable metadata | May preserve sharing and avoid dense materialization; it is not globally canonical for Boolean equivalence. |
| FlatProgram | A slot-based instruction stream compiled from an expression or CM IR | Kernel cost depends on instruction count, live support, backend, and retained sharing. |
| Public wrapper | The complete API path including admission, preparation/lookup, binding, dispatch, conversion/materialization, and output contract | The correct boundary for a user-facing speed claim. |

The current code uses an `x_first` true-first basis in core CM functions, while some paper/deck illustrations use a false-first layout. They encode the same relation only after an explicit permutation. Every reproducibility artifact must record the convention.

## Evidence that survives correction

| Evidence item | Result | What it supports | What it does not support |
|---|---|---|---|
| Binary-token audit in this program | All 16 tokens distinct; all 16,384 fusion cases pass | Finite correctness of the two-input pointwise fusion identity | An unbounded compiler proof or performance result |
| Current-worktree diagnostic | 400/400 generated expressions matched an independent evaluator; focused first-argument mutation check was false | A small current-version semantic regression check | Complete implementation correctness |
| Earlier-checkout diagnostic | 400/400 semantic checks passed; first-argument mutation check was true | Version drift exists and aliasing behavior needs explicit tests | A defect in the current worktree |
| B1/E3 and EPFL comparison | CM/CSE-flat kernel parity; residual around `0.9998` in the accepted B1/E3 evidence | A strong sharing-aware baseline can capture the same available structure on these workloads | A CM speed advantage |
| Corrected B2/B4 V3 | Bare CM/CSE-flat `0.890570`, interval `[0.874065, 0.907272]`; at `k=16`, `0.961234`, interval `[0.928974, 0.994177]` | A workload- and machine-conditional bare-program reduction | Universal dominance or end-to-end advantage |
| Corrected public wrapper | CM/CSE-flat `3.094136`, interval `[2.883083, 3.310818]` | The interface/preparation boundary can dominate the kernel benefit | A reason to quote only the bare ratio |
| Three fresh same-host V3 repetitions | Overall `0.904905–0.908991`, geomean `0.907590`; wrapper ratios `2.775383–2.836843` | Directional repeatability plus visible between-run variation | An independent workload or platform-general effect |
| Preparation optimization | One-memo change reproduced at roughly 2.5–2.7% on representative slices; exact outputs retained | A small, mechanism-linked compiler improvement | A CM-versus-incumbent result |
| Untouched Berkeley ABC i10 selector test | 144 exact cones; simple `k=16` rule low regret with zero catastrophes; frozen feature selector had worse regret and 7/11 catastrophic routes and was rejected | Honest held-out transfer for that selection decision | Permission to retune on i10 or acceptance of the failed selector |
| Above-guard bounded kernels | 16/16 direct cases exact; public wrapper refused 16/16 | Limited kernel feasibility above the guard | A supported public feature or speed claim above `live_k=16` |

Primary repository evidence consulted:

- `docs/audits/2026-08-25-cm-deep-performance/CM-DEEP-PERFORMANCE-AUDIT.md`
- `docs/audits/2026-08-25-cm-deep-performance/CM-BENCHMARK-RESULTS.md`
- `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/RUN-RESULTS.md`
- `docs/audits/2026-08-25-cm-deep-performance/reruns/campaign-20260826-132038/EXTERNAL-RUNS-RESULTS.md`
- `docs/audits/2026-08-25-cm-deep-performance/CM-WEBSITE-RESULTS-AUDIT-UPDATE-PROMPT-2026-08-27.md`
- `docs/research/CM_COMPUTATION_DEEP_TECHNICAL_DOSSIER.md`

## Publication interpretation

The repository already contains much stronger evidence discipline than either manuscript: exactness gates, counterbalancing, cluster intervals, workload labels, held-out rejection, explicit output guards, and separation of kernel from wrapper cost. The paper should reuse that discipline and selected immutable artifacts, not reproduce every campaign.

The publishable story is a performance boundary:

1. sharing-aware CSE removes much of the originally claimed advantage;
2. CM IR can still reduce bare compiled work in a defined repeated/shared structure regime;
3. preparation and wrapper costs can reverse that result end to end;
4. complete explicit output is exponential in live support;
5. selection policies require frozen transfer tests and must be reported even when they fail.

## Remaining empirical gate

Before full drafting, create one manuscript-specific preregistration that selects immutable existing results and declares any genuinely new experiments. It must freeze:

- the exact claim and artifact boundary;
- code revision and all transitive source hashes;
- tuning, reused-validation, and untouched-test roles;
- sharing-aware CSE as the primary generic comparator, plus task-matched BDD/bit-vector baselines;
- preparation, lookup, binding, kernel, conversion/materialization, serialization, memory, and whole-call endpoints;
- failure/refusal/timeout accounting, uncertainty method, and negative-result reporting;
- the decision rule for whether the method clears the target venue's utility threshold.

Do not rerun old corpora merely to create new-looking evidence, and do not tune after exposing an untouched test set.

