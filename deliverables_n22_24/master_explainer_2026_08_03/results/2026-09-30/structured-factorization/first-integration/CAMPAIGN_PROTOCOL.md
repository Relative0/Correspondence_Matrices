# Prospective live-vtree integration gate — candidate protocol

**Status: prepared, not frozen, not run.** Freeze only on the intended Linux
host after the hard-cap negative control and a capped PySDD exactness smoke
both pass. The `campaign_freeze.json` receipt must predate every validation or
held-out result. Phase 5B's archived negative result remains untouched.

## Question and fixed methods

Compare complete exact factorization with three non-oracle baselines B2/B3/B4,
fresh-compiled M1/M2 (F1/F2), and live-M1/M2 (L1/L2). F/L use identical B3
initial trees, serialized local-neighbor order, six unseen candidates per
round, at most two rounds, objectives and deterministic ties. The only intended
difference is fresh CNF compilation versus native movement of one referenced
compiled SDD. Every method passes its certified direct partition through the
same residual SAT and carrier assembly. Semantic prime truth is evaluator-only.
No coefficients, objectives, budgets, method set or generator are tuned from
validation or held-out outcomes.

## Inputs and reservation

`candidate_manifest.json` is generated deterministically by
`campaign_inputs.py` and checked against the 30 Phase 5B held-out CNFs and
eight tooling-probe timing CNFs. All inputs have an explicit all-zero witness.
The validation split reserves four templates—component paths, articulation
triangles, window at-most-one and nested implications—at n=8,10,12 (12 CNFs).
The held-out split reserves six other templates—bridged local XOR,
ring equivalence, overlapping at-most-two, nested gate DAGs, ladder grid and
threshold bridge—at n=8,10,12,14 (24 CNFs). Four templates have carriers
crossing syntax clusters. Template identities are disjoint across splits.
This is a bounded synthetic gate, not a public-corpus or scale result.

## Execution and resources

Use Python 3.11 on a Linux Runpod CPU-only Pod with at least 8 GiB host RAM,
or a host of equal capacity. Run one worker at a time, one fresh process per
method/instance/repetition. The worker sets Linux `RLIMIT_AS` to **2 GiB before
PySDD/PySAT imports**; this is a hard virtual-address-space allocation limit,
not a direct RSS limit. A 20-second parent watchdog covers native hangs and
uncapped inverse moves. `ru_maxrss` supplies peak resident memory diagnostics.
The allocation-over-cap negative control must fail with `MemoryError`, and a
2 GiB capped PySDD smoke must produce the independent exact partition before
freezing. No trial is valid on Windows, where this cap is unenforced.

Use three fresh-process repetitions and deterministic shuffled job order per
split. Charge worker setup, compilation, native GC/moves/inverses/replay,
candidate extraction and scoring, B2 minimization, residual SAT and carrier
assembly to inclusive worker `total_ns`. Record process-wall time separately
including interpreter/import/output overhead. Use 40-second PAR2 for each
timeout, memory-cap, crash or error. Stop further jobs after 90 minutes of
cumulative process-wall time across both splits; report remaining trials as
censored. Never extend this ceiling after seeing outcomes. Fail immediately
on a semantic or carrier-partition discrepancy. Keep all raw rows, including
failure status, worker stderr tail, stage costs and move traces.

## Freeze and sequential decision

Pin the eight dependencies in `requirements-lock.txt`. `freeze` checks input
regeneration, reserved families and archived/probe exclusion, the hard-cap
negative control and capped PySDD smoke. It writes source/protocol/manifest
SHA-256 hashes, Python/platform/package environment, exact resource limits,
method order and instance IDs to `campaign_freeze.json`. Every subsequent
command rechecks those hashes and environment. If a source or protocol fix is
needed after freezing, create a new dated campaign directory and receipt;
do not overwrite or silently continue old results.

Run validation, then lock one baseline from B2/B3/B4 and one live challenger
from L1/L2 by the lowest geometric mean of per-instance median PAR2-adjusted
**complete** time. Deterministic method-name order breaks ties. Fresh F1/F2
remain mechanism controls, not post-hoc challengers. Save selection plus the
validation-results hash before starting held-out jobs.

For held-out, pair selected challenger and baseline on each instance's median
of three repetitions. Bootstrap the 24 instance ratios 10,000 times with
seed 2026093021; the sorted draw at index 9499 is the one-sided 95% upper
ratio. Algorithmic GO requires zero independent exactness discrepancies, no
more challenger failures than baseline, paired geometric ratio <=0.90 and
upper ratio <1. Mechanism GO separately requires exact F1/L1 and F2/L2
candidate/final parity and a lower live paired search-stage cost with upper
bootstrap ratio <1. Report both outcomes even if they differ. Do not treat
exposure or residual SAT savings as a substitute for the primary criterion.

## Command sequence on the Linux host

After transferring this new sibling directory to the existing authorized Pod,
create a Python 3.11 virtual environment, install `requirements-lock.txt`,
and run:

```sh
python -B campaign_runner.py freeze
python -B campaign_runner.py validation
python -B campaign_runner.py select
python -B campaign_runner.py heldout
python -B campaign_runner.py analyze
```

Keep the original Phase 4/5 directories and frozen held-out records read-only.
No formal command should run until the Pod configuration, price and authorized
spending ceiling are known. This candidate protocol can be revised only before
`freeze`, with a dated change note; do not use validation or held-out results
to make those revisions.
