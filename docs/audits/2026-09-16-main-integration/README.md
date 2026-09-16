# Main integration review — 2026-09-16

## Baseline and intent

This review promotes the reconciled local baseline
`516b813211235f3a56635baf9873fda342b7a584` toward `main` without touching the
protected dirty checkout.  The intent is a single current code baseline, not a
blind merge of every historical preservation branch.

## Included

- The seven reviewed reconciliation commits: Windows pytest profile, pair
  compiler improvements, research pipeline, paper workbench, video authoring
  source, and the root-reconciliation manifest.
- `4ab57e5` (cut-fusion phase two), merged as `1cdd8981`:
  - Adds the cut-fusion implementation and 11 focused tests.
  - Preserves the 49.42 MiB sealed research/evidence package.
  - `tests/test_cut_fusion.py` passed (11 tests).
  - Its phase-two verifier passed, including 13,104 exact confirmation rows;
    the evidence correctly records a `STOP` decision rather than a speedup
    claim.
  - Its independent audit verifier passed when directed to a temporary output
    path; its normal write-once output remains sealed.

## Deliberately retained outside `main`

| Branch | Reason not promoted unchanged |
| --- | --- |
| `codex/cm-family-repair-20260915` | Its own verifier reports that its publication record no longer matches current `cm_bench.py`. |
| `codex/cm-site-hash-portability-20260910` | It conflicts with every current site evidence page.  The current focused website verifier passes all 14 tests, so the old normalization patch is superseded. |
| `codex/cm-sympy-timing-repair-20260915` | It has an add/add conflict with the current claim-cleanup module.  Reconciliation commit `0fa87428` intentionally replaces its timing envelope with the newer result-contract validation. |
| `codex/cm-original-dirty-preservation-20260908` | Historical preservation content mixes an old fixture deletion, stale site copies, and legacy video packages.  It remains a recoverable local branch, but is not a safe current-code merge. |

The data-coupled current SymPy tests still require frozen audit inputs that are
preserved in the local recovery archives.  Their absence from a clean source
worktree is expected and was not treated as a source regression.

## Final checks before promotion

- `python -B -m compileall -q cmbench scripts tests native` passed.
- `python -B -m pytest -q tests/test_cut_fusion.py tests/test_cm_learning_neural_website.py` passed: 25 tests.
- `git diff --check 516b8132..HEAD` passed.

The protected checkout remains on `codex/cm-dirty-preservation-20260914` and
was not switched, reset, cleaned, or edited during this integration.
