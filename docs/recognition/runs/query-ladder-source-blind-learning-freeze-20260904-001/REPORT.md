# Q64 source-blind learning evidence freeze

Date: 2026-09-04

Status: frozen locally; no labels, timings, model fitting, or cloud execution.

## Frozen cohort

- 72 new deterministic development cases
- source-group splits: 40 fit, 16 validation, 16 audit
- prior alpha-structural overlap: 0
- model-visible features: 13 structural integers
- prospective cases consumed: 0

The case generator, complete query traces, structural feature vectors, source-group
identities, and split assignments were frozen before any method output or timing for
this cohort was produced.

## Cross-host label policy

A case receives an exact-arm label only when every verified host names the same
winner, the runner-up/winner median ratio is at least
1.03x on every host, at least
75% of paired blocks favor the winner,
and the paired p10 ratio is at least 1.00x.
Every disagreement, tie, or threshold failure becomes `__abstain__` and remains
in charged economics while being excluded from model fitting.

## Charged economics

Both physical-machine replications must measure p95 feature/control, bounded model
inference, exact-arm verification, and fallback dispatch on the same host as the
exact timings. Expected fallback also includes the exact-runtime regret for abstained
cases. Cross-host timing reuse and zero-cost imputation are prohibited. Gross and
fully charged speedup must each remain at least 1.10x on every host.

## Boundary

This artifact does not authorize exact timing, a RunPod request, label generation,
model fitting, neural training, prospective access, production routing, or any other
external write. A separately authorized Benchmark task must execute and independently
verify the exact evidence before the learning handoff can be assessed.
