# Convergence audit and computation follow-through

**Audit verdict: RETURN TO BOTH THREADS. Current publication form: technical report.**

The full audit/replay is now performed, and the authorized C1/C3/C4 preparation is implemented. C2 remains held because the user confirmed no frozen T3 target exists. No main T3 performance campaign or Runpod job was launched.

Start with [the audit](ASTRA_CONVERGENCE_AUDIT.md), [decision](CONVERGENCE_DECISION.md), and [Master handoff](HANDOFF_TO_MASTER.md). The exact next dependency is the ready-to-paste [Computation Request to Theory](COMPUTATION_REQUEST_TO_THEORY.md).

## Review and evidence

- [Theorem/priority audit](THEOREM_PRIORITY_AUDIT.md), [fresh primary-source search](PRIMARY_SOURCE_SEARCH.md), [computation validity](COMPUTATION_VALIDITY_AUDIT.md), [portfolio overlap](OVERLAP_AUDIT.md), and seven reports in `REVIEWER_REPORTS/`.
- Original sources and external audit remain separately attributed under `inputs/`. Companion manuscript context is under `context/`.
- New C1 regression bridges LSB/MSB conventions against a pinned main-source snapshot. The independent external checker remains unchanged.
- All 2,861 outputs of 20 source designs are accounted for in `corpus_v1/`; 1,088 outputs from 11 designs meet the structural-support cap. All admitted truths pass an independent cross-check.
- Matched packed binary, retained rank factors, and compiled CUDD support exact queries and residual updates. Bounded exhaustive correctness, lifecycle and natural-source acceptance results are in `runs/`.
- [Computation ledger](COMPUTATION_LEDGER.md), `EXPERIMENT_MANIFEST.csv`, [environment](ENVIRONMENT.md), [commands](REPRODUCTION_COMMANDS.md), and [failed-run history](FAILURE_AND_CONTINUATION_LOG.md) distinguish original evidence, new replay and infrastructure preparation.

The delivery manifest hashes every included file and excludes caches, the machine-specific Linux virtual environment and itself. The ZIP contains the pinned Linux wheels instead of that environment. The verifier checks manifest bytes without executing experiments.

## Boundary

The scientific gap is unchanged: Q_k reconstruction depth is not a storage/runtime prediction, and the old Walsh profile identity is not T3. Corpus/rank screening and tiny lifecycle smoke trials do not confirm an absent hypothesis. Cold-load preparation provides file-specific advisory eviction, not proof of physical cold cache. Upstream wheel compiler flags are unavailable; exact binary/wheel hashes are supplied.

**SEND RESULTS/QUESTION TO THEORY.** Resume the actual C2 campaign in this task after the frozen target arrives, using GPT-6-Astra/high for the mathematical alignment. No further model run is needed before that dependency.
