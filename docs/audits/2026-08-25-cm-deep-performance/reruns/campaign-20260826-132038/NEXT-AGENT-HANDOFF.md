# Next-Agent Handoff

## Exact state

- Repository: `C:\Users\brian\Documents\CM_Computation`
- Branch / HEAD: `main` / `0f833bc389778f7f915deb7acd4499d207e0ec21`
- `origin/main`: `1fd3907dbc1986cb2d8a9f0f8cab2b5920a415ce`
- No commit, stage, push, or dependency installation was performed. The
  explicitly approved follow-up downloaded the pinned Berkeley ABC i10 source
  and used three Runpod CPU pods for `$0.002815`; all were terminated and the
  postflight inventory found zero pods.
- Latest full suite: `368 passed, 4 subtests passed in 95.82s` (the earlier
  release and post-tooling full passes were also green).
- External-follow-up focused gate: `86 passed, 4 subtests passed in 3.27s`;
  deterministic
  two-build site regeneration, JSON/HTML parse, byte-compile, and JavaScript
  syntax checks all passed.
- Production `cm_ir.py` was restored byte-for-byte after DP-R1 rejection.

Campaign-owned retained files outside this directory:

- `scripts/cm_combine_memo_ablation.py`
- `tests/test_cm_combine_memo_ablation.py`
- `deliverables_n22_24/cm_memo_runpod_worker_2026_08_26.py`
- `deliverables_n22_24/cm_memo_runpod_campaign_2026_08_26.py`
- `scripts/cm_heldout_abc_i10_selector.py`
- `tests/test_cm_heldout_abc_i10_selector.py`
- `deliverables_n22_24/heldout_abc_i10_2026_08_26/`
- `deliverables_n22_24/memo_runpod_2026_08_26/`

Preserve unrelated untracked `.claude/`, `external/`, `tmp/`, and both
`The Broken Silence.*` files exactly. Preserve all pre-existing website/audit
edits and every historical benchmark artifact.

## Results to carry forward

- Fresh symmetric V3 bare CM/CSE-flat runs: `0.908991`, `0.908879`, `0.904905`;
  three-run geomean `0.907590`; exact outputs throughout.
- Fresh one-memo BX1+B2: `0.973437 [0.968471, 0.982526]`, 272 rows.
- Fresh one-memo EPFL: `0.974627 [0.965820, 0.983220]`, 129 roots.
- Memo smoke peak ratio: `0.882005`; no exact mismatches.
- Current selector remains k16; scalar retune gate failed on one `2.284338`
  catastrophic CM validation route.
- Guard rerun: 16/16 direct cases exact, 16/16 public refusals.
- DP-R1: exact but `1.8317x` time and `1.2440x` peak; rejected/reverted.
- Partial synthetic break-even signal: n16/c500/fixed 0.50 gave CM/BitSet
  `0.952`; fixed 0.75 gave `0.997`. Not a production claim.
- Three-pod one-memo confirmation: BX1+B2 `0.972147--0.978781`; EPFL
  `0.969411--0.976902`; every host exact; total cost `$0.002815`; zero pods.
- Untouched ABC i10: 144 exact cones, 16 per k=8..16. Current k16 regret was
  `1.012285` raw and `1.012460` CM, zero catastrophes. The frozen feature model
  failed at `1.121191`/`1.136482` with 7/11 catastrophes and is rejected.

## Completed approval-gated work

Runpod and the first independent held-out selector study are complete. See
`EXTERNAL-RUNS-RESULTS.md`. Do not repeat the same campaign merely for another
point estimate, and do not tune a replacement selector on i10 while continuing
to call it held-out.

Native CUDD/Numba remain optional and absent. The next selector study needs a
different independently frozen circuit family and a preregistered model that
first clears its BX1 cross-validation catastrophic-route gate.

## Claims that must not be resurrected

- No optimization claim from the old `0.9998` CM/CSE-flat residual.
- No universal support-only crossover theorem.
- No production feature-selector claim from the failed i10 transfer study.
- No reuse of i10 as both tuning and untouched validation.
- No claim that B2/EPFL are untouched held-out data.
- No removal of the `2^k` complete-output lower bound.
- No quotient-as-semantic-XOR timing.
- No blended BDD build/restrict/extract window.
- No global semantic canonicality theorem from current keys.
