# Four-lane comparison harness: local functional admission

Date: 2026-09-03  
Status: independently verified development artifact; no timing, fresh corpus, training, or promotion

## Outcome

The post-C38 architecture-aware comparison harness is implemented and passes its local
functional admission boundary. The independent verifier reran the complete harness and
reproduced `RESULT.json` byte-for-byte.

This result permits only the next protocol step: freeze a fresh comparison corpus,
schedules, arm configurations, and publication gates. It is not performance evidence and
does not authorize corpus acquisition, RunPod execution, selector fitting, neural
training, production routing, website publication, or any other external write.

## Implemented lanes

### A. Complete explicit relation

One exposed C36 development/regression case at width 11 was evaluated by eight current
arms: dense CM reinflation, CM packed bigint, CM packed words, CM hybrid
no-reinflation, recursive packed CM IR, structural-CSE flat, raw flat, and direct
expression BitSet. All eight returned the same 2,048-byte Boolean vector, exact count,
SAT flag, and canonical first satisfying row as the independent vector oracle.

### B. Repeated exact restrictions

The same exposed C36 case was checked at q1, q4, q16, and q64. Each checkpoint included
Python R2, CM-IR bigint/words, structural-CSE bigint/words, compiled projection, direct
BitSet restriction, and the retained native fused-slot library. All 32 cells returned
the same canonical residual relation, exact count, SAT flag, witness, and digest as the
frozen C36 oracle.

### C. Related multi-root outputs

The historical development workload `multi-multiply8-bits345` was evaluated for all 64
restrictions and all three ordered roots by a sharing-aware Python union DAG, separate
Python DAGs, one native union arena, and separate native arenas. All four arms matched
the direct full-truth oracle. The union structure used 89 unique nodes versus 173 summed
separate nodes, avoiding 84 duplicate nodes. This is a structural fact, not a speedup
claim.

### D. Smaller-query benefits

Exact count, SAT status, canonical witness, partial-context, version-history, and
equivalence-delta were kept as separate sublanes. CM, CSE, direct CNF, and a bounded
simulated SAT control matched the independent scalar oracle under both fresh and
resident lifecycles: 48 functional cells. Structural reload was separately checked for
CM, CSE, and direct CNF: three additional cells, each reconstructed without an answer
cache and matched the exact relation oracle.

## Evidence identity

- Development artifact: `docs/recognition/runs/architecture-refresh-harness-development-20260903-001`
- Plan SHA-256: `dc9be5082320ae290db1c848438e88d07e05e3540646aa76eb1bac9fd9b04dfb`
- Result SHA-256: `b373b7189baac867fa5cc806a02e2f64f778bb2004f13a120eaab19e0017b4c6`
- Verification SHA-256: `2ff01455ebf8936debd6d40ff5ef7c686f352e5463242f4a13335625562992e4`
- Exposed C36 dataset SHA-256: `ce6afdde4321682a5345269ba4d9f7c80a916931f15a7c0cc6f2ca93beb0eaa1`
- Retained Windows native library SHA-256: `2d444c32d352284ab28474fef5554659f4f08225158d79feedc48633cf4875a0`

## Implementation

- `cmbench/comparative/architecture_refresh_harness.py`
- `cmbench/comparative/gf2_multi_root_python.py`
- `scripts/cm_architecture_refresh_harness_development.py`
- `scripts/crse_architecture_refresh_harness_verify.py`
- `tests/test_cm_comparative_architecture_refresh_harness.py`
- `tests/test_cm_comparative_multi_root_python.py`

## Preserved decision boundary

C38 independently confirmed exact Linux/GCC execution and aggregate/multi-root benefit,
but its 0.840x minimum single-root case failed the frozen 0.95x case floor. Native
execution therefore remains guarded/opt-in. The functional harness includes native only
as an exact admitted arm; it does not reinterpret C38, produce a portable per-case
performance claim, or change the no-training decision. Any timed comparison remains a
separate, source-hash-closed campaign requiring a frozen protocol and separate compute
authorization.
