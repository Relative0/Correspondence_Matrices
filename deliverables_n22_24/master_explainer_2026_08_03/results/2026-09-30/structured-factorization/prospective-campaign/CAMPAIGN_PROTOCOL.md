# Prospective live-vtree integration gate — registered protocol

**Status at registration: unfrozen, with no validation or held-out trials.**
This protocol applies only to this new sibling revision. It does not amend the
Phase 5B negative result or the earlier frozen integration campaign.

## Preflight evidence and limit

The Linux preflight used disposable Python 3.11 containers with 4 GiB memory,
2 CPUs, pinned dependencies and a 2 GiB worker `RLIMIT_AS`. The real worker
reported its effective cap; a 512 MiB allocation failed under a 256 MiB test
cap. Capped B3/F1/L1/F2/L2 developmental trials agreed with independent exact
truth. Native failure and watchdog controls were classified separately.
Longer live-SDD walks passed dual-root SAT miters and restoration at n=20
(100 steps), n=24 (80), n=28 (40) and n=32 (20). The n=32, 50-step walk hit
a 45-second watchdog. These results are in `linux_preflight_results.json`,
`linux_scale_results.json` and `linux_scale_timeout_32x50.json`. They
justify a bounded n<=14 trial, not a larger-walk throughput claim. Repeat
the capped-worker smoke on the intended formal Linux host at freeze.

## Question and fixed methods

Compare complete exact factorization by B2/B3/B4, fresh-compiled M1/M2
(F1/F2), and live-M1/M2 (L1/L2). F/L start from the same B3 tree and use
the same local-neighbor order, six unseen candidates per round, at most two
rounds, objectives and tie order. The implementation of each candidate's
SDD is the sole intended difference: fresh compilation versus local movement
of a referenced compiled SDD. Every method then uses the same exact residual
SAT and carrier assembly. Semantic prime truth is used only by the separate
evaluator; it is never passed to a worker or used to score a search move.

## Inputs and reservation

`campaign_inputs.py` deterministically generates the 36 records in
`candidate_manifest.json`. Validation contains four families at n=8,10,12
(12 CNFs): equivalence-pair weave, equivalence/cardinality weave, split
implication paths and a prime equivalence ring. Held-out contains six
different families at n=8,10,12,14 (24 CNFs): equivalence ladder bridge,
cardinality/equivalence bridge, dual cardinality bridge, split implication
DAG, global at-most-one and connected nested gates. The product families
combine independent modules with redundant cross-module clauses. Those
clauses are supersets of module clauses and cannot change Boolean truth;
their purpose is to conceal factors from a syntax-only tree. The ring and
global at-most-one are prime controls. Some carriers cross syntax clusters.
Every clause has a negative literal, giving an explicit all-zero satisfying
assignment. No formal instance has been screened by B3 outcome or semantic
prime partition.

Regeneration must match the manifest's parsed structure exactly. A canonical
CNF exclusion check rejects duplicates within the manifest and equality with
the 30 Phase 5B held-out CNFs, 36 prior integration CNFs and 11 development
or tooling CNFs. Developmental six-variable positive controls are evidence
for the harness only; they are not part of either formal split. Family
identities remain disjoint across splits. This is a synthetic integration
gate, not a public-corpus or scale result.

## Execution and resources

Use Python 3.11 on Linux with at least 4 GiB available to the container.
Run one fresh worker process per method, instance and repetition, serially.
The worker sets `RLIMIT_AS=2 GiB` before importing PySDD/PySAT and returns
the observed cap. The parent enforces a 20-second watchdog. `RLIMIT_AS`
bounds virtual address space; peak resident memory is recorded separately.
Reject the campaign if the actual worker cap negative control or capped
exactness smoke fails on that host. Do not run formal trials on Windows.

Run three repetitions, in the predetermined shuffled order for each split.
The inclusive worker `total_ns` charges initialization, compilation,
minimization, moves, inverses, replay, extraction, residual SAT and carrier
assembly. Process-wall time includes interpreter and I/O overhead. Failures
receive 40-second PAR2. Stop issuing jobs after 90 minutes of cumulative
process-wall time across splits; report incompleteness as censored. Do not
extend this ceiling after inspecting outcomes. Retain raw successful and
failed rows, move traces, stage costs, stderr tails and resource diagnostics.
Stop immediately after a semantic or carrier-partition mismatch, retaining
the failing row.

## Freeze and sequential decision

Before any formal run, pin the manifest, this protocol, source hashes,
requirements and environment in `campaign_freeze.json` on the intended
Linux host. The receipt must predate validation rows. Subsequent commands
verify the hashes, environment and full job sequence. A needed source,
protocol or manifest fix after freeze requires a new dated campaign
directory; do not rewrite the receipt or resume incompatible rows.

Run validation first. Select one baseline from B2/B3/B4 and one live
challenger from L1/L2 by the lowest geometric mean of per-instance median
PAR2-adjusted **complete** time, with method-name ties. Lock the choice
and validation-results hash before any held-out job. Fresh methods remain
matched mechanism controls, not post-hoc challengers. No objectives,
budgets, method set, generator or selection rule may be changed from
validation or held-out observations.

For held-out, form a ratio of selected challenger to baseline from each
instance's median of three repetitions. Bootstrap the 24 log-ratios
10,000 times with seed 2026093021; sorted draw 9499 is the one-sided
95% upper ratio. Mechanism GO requires complete F1/L1 and F2/L2
instance/repetition pairs, zero candidate/final decision mismatches,
live paired search-stage geometric ratios below 1 and both upper bounds
below 1. Algorithmic GO also requires mechanism GO, no more challenger
failures than baseline, paired complete-time geometric ratio <=0.90,
its upper bound <1 and no independent exactness discrepancy. Report both
gates even if they differ; factor exposure alone cannot substitute for
complete-time benefit.

## Formal sequence

Run on the local Linux Docker host used for preflight, with 4 GiB container
memory and 2 CPUs. No paid resource is needed. From this directory:

```sh
python -B campaign_runner.py freeze
python -B campaign_runner.py validation
python -B campaign_runner.py select
python -B campaign_runner.py heldout
python -B campaign_runner.py analyze
```

At registration, no formal command had run. Preserve the Phase 4/5 archives
and earlier frozen held-out records unchanged.
