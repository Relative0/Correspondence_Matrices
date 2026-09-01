# C22 source-packed exact GF(2) portfolio implementation

**Date:** 2026-08-31  
**Status:** opt-in implementation and tests complete; no fresh timing claim; production disabled

C22 exposes the C21 packed source-ANF path through a bounded exact dispatcher boundary. Advice-on
requests packed source-ANF truth construction followed by screened exact CM completion. Advice-off
uses exhaustive CM. A refused source-ANF computation falls back to exhaustive CM, and explicit
shadow mode executes the alternate exact arm and requires identical best-artifact identity.

The execution record binds the frozen policy digest and records requested and selected arms,
fallback reason, source truth digest, exact artifact identity, analysis counts, stage timings, and
shadow agreement. The selected source result is independently replayed through the ordinary
expression evaluator inside the charged exact-check stage.

The frozen policy cites the verified C21 run manifest and dataset fingerprints. It is deliberately
marked `fresh_confirmation: false` and `production_promotion: false`. The policy always selects the
best fixed C21 arm; it does not encode the post-hoc width rule and does not train a router on C21.

Focused tests cover selected execution, advice-off, both shadow directions, source refusal with
exact fallback, policy save/load and tamper rejection, malformed task refusal, and result tamper
rejection. Fresh-source and second-machine evaluation remain required before any default change.

## Evidence

- Implementation: `cmbench/recognition/gf2_source_portfolio.py`
- Policy: `docs/recognition/c22_source_portfolio_policy.json`
- Tests: `tests/test_gf2_source_portfolio.py`
- C21 report: `docs/recognition/LEARNING_MILESTONE_C21_TASK_MATCHED_GF2_METHOD_TABLE_2026_08_31.md`

