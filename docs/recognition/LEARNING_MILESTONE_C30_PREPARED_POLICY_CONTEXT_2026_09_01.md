# Learning milestone C30: immutable prepared-policy context

Status: implemented and independently verified; local no-regret diagnostic passes,
with shadow and production promotion still refused

## Question

C29 found that repeated C27/C22 policy loading and validation consumed 92.38% of the
support-aware candidate's median setup time. C30 tests that diagnosis without changing
the support rule, exact query algorithm, corpus, query count, or counterbalanced schedule.

The implementation validates both frozen policy files once at the resident lifecycle
boundary. It stores only immutable scalar tuples, binds the two policy identities and
source-file hashes into a deterministic context digest, and creates each short session
from that snapshot. The one-time preparation cost is conserved and allocated across all
candidate batches.

## Safety contract

The prepared context adds six independently replayed controls:

- advice-off still selects exhaustive CM and returns the exhaustive-best artifact;
- forced selected-path refusal still falls back to exhaustive CM exactly;
- a C27 source file changed after preparation is refused;
- an incorrect prepared-context digest binding is refused;
- a tampered C27 policy is refused during preparation; and
- a tampered C22 policy is refused during preparation.

Direct construction without the internal validated-construction token is rejected. The
stored dataclass is frozen, and sessions receive fresh policy dictionaries reconstructed
from immutable tuples. Source hashes are checked before and after the timed run.

## Unchanged counterbalanced diagnostic

The run retains C29's 16 blocks, four width positions, adjacent method pairs, and q8 case
schedule. It contains **128 measurement batches**, **64 paired batches**, and **1,024
timed exact GF(2) queries**. The independent verifier replayed all 512 candidate verified
contexts and found zero semantic or artifact mismatches.

| Width | C29 total | C30 charged total | C30 query-only | paired charged range | charged non-query share |
|---:|---:|---:|---:|---:|---:|
| 3 | 0.8459x | **1.0002x** | 1.0110x | 0.9070-1.0620x | 1.98% |
| 4 | 0.9689x | **1.0304x** | 1.0360x | 0.9508-1.1287x | 1.08% |
| 5 | 1.0088x | **1.0243x** | 1.0259x | 0.9415-1.0812x | 0.40% |
| 6 | 1.0331x | **1.0421x** | 1.0425x | 0.9929-1.0904x | 0.12% |

The one-time validated preparation cost was **0.7524 ms**, allocated exactly across 64
candidate batches. Median per-session setup fell from C29's 0.6638 ms to **0.0431 ms**.
The fully charged aggregate ratio of width medians is **1.0360x**, and the minimum-width
ratio is **1.0002x**. This passes the prespecified local diagnostic gate of at least 1.00x
aggregate and 0.90x at every width.

The improvement is largest where C29 predicted it: n=3 improves by 18.25% relative to
the C29 speedup ratio, and n=4 improves by 6.35%. The query-only values remain close to
the C29 path because C30 changes policy lifecycle work rather than the exact query path.

## Decision

C30 confirms the fixed-overhead diagnosis and supplies a safe reusable implementation.
It clears the local point-estimate no-regret gate, but its n=3 margin is effectively
neutral and eight of sixteen n=3 paired blocks remain below 1.00x. Individual paired
ranges also cross 1.00x at n=3-n=5.

This is development evidence from one physical machine, not a replacement for C28's
cross-machine adjudication. Exact fallback remains mandatory. Shadow and production
promotion remain false.

## Recommended next milestone

C31 should freeze the exact C30 package and a prospective replication protocol before
collecting new timing. It should run the unchanged 16-block schedule on at least one
second physical machine, retain lifecycle preparation charges and component timings,
and adjudicate point floors plus paired-block lower bounds without refitting. A same-host
Linux container may test portability but must not count as another physical machine. No
learned selector should be introduced before that replication.

## Evidence

- Run: `docs/recognition/runs/c30-prepared-policy-windows-20260901-001`
- Prepared context: `docs/recognition/runs/c30-prepared-policy-windows-20260901-001/prepared_context.json`
- Controls: `docs/recognition/runs/c30-prepared-policy-windows-20260901-001/functional_controls.json`
- Measurements: `docs/recognition/runs/c30-prepared-policy-windows-20260901-001/measurements.jsonl`
- Results: `docs/recognition/runs/c30-prepared-policy-windows-20260901-001/results.json`
- Independent verification: `docs/recognition/runs/c30-prepared-policy-windows-20260901-001/independent_verification.json`
- Prepared context implementation: `cmbench/recognition/gf2_prepared_support_context.py`
- Session integration: `cmbench/recognition/gf2_support_aware_session.py`
- Experiment: `cmbench/comparative/gf2_prepared_policy_experiment.py`
- Runner: `scripts/cm_comparative_c30_prepared_policy.py`
- Verifier: `scripts/crse_gf2_prepared_policy_verify.py`
- Tests: `tests/test_gf2_prepared_support_context.py`,
  `tests/test_cm_comparative_gf2_prepared_policy_experiment.py`
