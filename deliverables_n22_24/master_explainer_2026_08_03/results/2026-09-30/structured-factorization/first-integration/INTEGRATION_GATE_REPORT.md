# Live-vtree exact-factorization integration gate — 30 September 2026

**Integration and development correctness: GO.** This report records the
pre-campaign state; the later frozen measurement and its algorithmic NO-GO
are reported in `CAMPAIGN_REPORT.md`. This is a new, isolated implementation.
Phase 5B's negative algorithmic result remains the result for its original
campaign.

## Implemented path

`integrated_pipeline.py` exposes seven non-oracle methods through
`run_trial(method, instance)`. Inputs contain only original-variable CNF,
carrier partition and an optional ID. The returned record contains the final
tree, real root-reachable SDD size/count, certified direct factors, exact SAT
refinement, move traces, stage times and process memory metadata.

| Method | Implementation |
|---|---|
| B2 | Original balanced vtree, original native `manager.minimize()` |
| B3 | Original syntax component/min-fill vtree |
| B4 | New deterministic syntax-only component and balanced separator tree |
| F1/F2 | Original M1/M2 objectives, fresh CNF compilation for every candidate |
| L1/L2 | Same M1/M2 objectives and candidate policy, one live compiled SDD |

F and L both begin at B3, visit the same first six unseen serialized neighbors
per round for at most two rounds, and use the same tree-string tie break.
L moves the referenced SDD, extracts a candidate, undoes it, and replays the
round winner. It recompiles the CNF once per trial. F compiles once initially
and once for each candidate. Both pass the final **certified direct partition**
to Phase 5B's `exact_refine`, including residual SAT on every nonsingleton
block and final carrier least-common-coarsening. False input returns
`satisfiable=false` and no factor partition. Semantic prime truth never enters
`integrated_pipeline.py`, `live_moves.py`, or `trial_worker.py`.

B4 preserves disconnected primal components as clades. Within each connected
set it chooses the most balanced anchored bipartition, then fewest crossing
primal edges, then lexicographic labels; it recurses on both sides. Its
construction cost is inside the total search-stage timer. This is a candidate
stronger syntax baseline, **not** a proven dominant baseline. Its exact size
limit and eligibility still need freezing before a new performance campaign.

The source copies under `reference/` match the original Phase 5B
`hybrid_core.py` and `benchmark.py` byte for byte. `live_moves.py` and the
development fixture generator match the earlier tooling probe. All new logic
and results are in this sibling directory.

## Correctness gate

`check_integration.py` passed on 36 development inputs: 24 selected Boolean
functions on three variables, true/false/free/literal/tautology controls,
crossing-carrier and nested cases, five earlier probe fixtures used only as
regression cases, and one new planted CNF. This produced **252 method runs**.
Every successful result matched an independent exhaustive semantic partition
and the independently assembled carrier partition; false inputs were reported
explicitly. F1/L1 and F2/L2 matched all **446 candidate evaluations** on
parent tree, target tree, objective score, SDD size/count, direct partition,
best-candidate decisions and final tree. Seven additional fresh-process
`trial_worker.py` checks passed.

`exact_miter.py` encodes the *current* SDD decision DAG as a Tseitin circuit
and asks PySAT for mismatches in both directions against the original CNF.
It passed a matching formula and rejected three deliberately mismatched
formulas, including true/false boundary cases. Equal model counts alone were
never treated as an exactness proof.

`check_stress.py` ran separate watchdog-protected workers at n=12 (100 steps)
and n=16 (80 steps). They mixed root and internal swaps/rotations, successful
moves, 36 deliberately limited failures, immediate undos and longer accepted
walks. The workers performed **398 main-root SAT miter checks**, **337 checks
of a second referenced root**, and 23 fresh-compilation structure checks.
They reversed 119 accepted long-walk moves and recovered the original tree,
function, direct partition and manager live size exactly: 213→213 and
486→486 elements respectively. There were no discrepancies or crashes.

The workers' own high-water working sets were about 79.4 MB and 87.8 MB;
both completed in under 4 seconds. Each worker checked a 1 GiB threshold
after each step, and the parent enforced a 30-second watchdog. On this managed
Windows host, the parent repeatedly reads only ~6 MB for a worker whose own
reading is much higher. Therefore the external memory reading is advisory,
and the current 1 GiB threshold is a **sampled check, not an enforced hard
cap**. A reliable operating-system memory cap, or a revised resource protocol,
must be established before freezing formal timing trials.

## Accounting and limits

`run_trial` charges initial compilation, native GC, forward moves, inverses,
winner replay, candidate extraction/scoring, native minimization where used,
final exact residual SAT and carrier assembly to `search_stage_ns`,
`exact_stage_ns` and `total_ns`. The detailed counters expose compilation,
extraction, move, undo and replay components. Those components do not by
themselves sum to total time: tree construction, scoring, assertions, Python
overhead and cleanup remain inside the inclusive stage totals. No stage time
from this development gate is presented as a performance comparison.

The long-walk tests use size-limited forward moves and uncapped inverses.
The matched L1/L2 implementation currently uses uncapped native moves under
a caller's process watchdog; it has no hard memory bound for large SDDs.
No validation or held-out inputs from a new campaign were generated or run.
No Phase 5B held-out trial was rerun, no objective was retuned, and no archived
Phase 4/5 file was changed. `source_and_archive_verification.json` confirms
byte identity of the four copied sources and no changes among **3,821**
protected archive files.

## Reproduce this development gate

From this directory in PowerShell, using the existing pinned Phase 5B venv:

```powershell
& '../phase5b_output/.venv/Scripts/python.exe' -B check_integration.py
& '../phase5b_output/.venv/Scripts/python.exe' -B check_stress.py
& '../phase5b_output/.venv/Scripts/python.exe' -B verify_scope.py
```

Outputs are `integration_correctness.json` and `.log`, `stress_summary.json`
and `.log`, and `source_and_archive_verification.json`. The checks replace only
these new development result files.

The subsequent Linux hard-cap check, protocol freeze, validation and held-out
comparison are recorded in `CAMPAIGN_REPORT.md`. The development gate above
remains a separate record of what had been established before that campaign.
