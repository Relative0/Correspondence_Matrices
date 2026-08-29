# Comparative task and evidence-reconciliation progress

Date: 2026-08-29

The local comparative framework now executes six matched tasks through CM,
structural CSE, direct CNF and installed native CaDiCaL, under both fresh-engine
and resident-engine lifecycles. A balanced synthetic bundle and a separate
cached-real bridge each passed all 384 planned cells. This extends the preceding
complete-relation P5 smoke; it is not a performance ranking and does not
complete native CUDD/ZDD/d4 readiness.

This note also reconciles concurrent memory, recognition and native-scout work
visible in the shared checkout at the evidence freeze. It does not take
ownership of those other tasks or rewrite their saved records.

## New task-matched result

| Evidence | Result |
| --- | ---: |
| Planned and accepted cells | 384/384 |
| Tasks | 6 |
| Backends | 4 |
| Lifecycles | 2 |
| Accepted semantic rows | 1,856 |
| Native CaDiCaL solve calls | 12,608 |
| Missing, unexpected or unfinished cells | 0 |
| Frozen evidence files, including checksum manifest | 32 |

Every one of the six tasks has 64 cells: four backends, two lifecycles and
eight counterbalance blocks. Those blocks are repeated observations of one
synthetic `k=6` case, not 384 independent formulas. The run exists to check
contracts, scheduling, reuse behavior and evidence integrity. Its clocks are
diagnostic and must not be aggregated into a speed claim.

The final evidence is [comparative-task-pilot-v4-2026-08-29](verification/comparative-task-pilot-v4-2026-08-29):

- [summary](verification/comparative-task-pilot-v4-2026-08-29/summary.json);
- [frozen plans](verification/comparative-task-pilot-v4-2026-08-29/plans.json);
- [independent scalar oracles](verification/comparative-task-pilot-v4-2026-08-29/oracles.json);
- [complete append-only ledger](verification/comparative-task-pilot-v4-2026-08-29/ledger.jsonl);
- [environment and native identity](verification/comparative-task-pilot-v4-2026-08-29/environment.json);
- [frozen source/test snapshot](verification/comparative-task-pilot-v4-2026-08-29/source_snapshot);
- [complete checksums](verification/comparative-task-pilot-v4-2026-08-29/checksums.json).

The read-only verifier accepted all 384 cells, all 32 evidence files and the
complete membership set without mutation. Ten focused tests then passed with
the current directory set to the frozen source snapshot rather than the live
checkout. The earlier v1-v3 directories are retained as development receipts.
V3 was scientifically complete, but the frozen-test execution exposed a
missing transitive `summary_tables.py` source; v4 includes it and is the
current self-contained bundle.

## Cached-real task bridge

The next local gate was also executed rather than left as a proposal. The
[cached-real bridge](verification/comparative-real-task-bridge-v1-2026-08-29)
applies the same six tasks once per backend and lifecycle to the seven
deterministically selected conditioned `k=8` feature-model relations plus the
separate named Soletta known-change control.

| Evidence | Result |
| --- | ---: |
| Scenarios | 8 |
| Planned and accepted cells | 384/384 |
| Accepted semantic rows | 1,856 |
| Native CaDiCaL solve calls | 49,472 |
| Default forward changed counts | 0, 0, 0, 0, 0, 0, 0 |
| Known-change forward count | 2 |
| Frozen evidence files, including checksum manifest | 34 |

Its [summary](verification/comparative-real-task-bridge-v1-2026-08-29/summary.json),
[plan and complete selection ledgers](verification/comparative-real-task-bridge-v1-2026-08-29/plan.json),
[scalar oracles](verification/comparative-real-task-bridge-v1-2026-08-29/oracles.json),
[append-only worker ledger](verification/comparative-real-task-bridge-v1-2026-08-29/ledger.jsonl),
[frozen sources](verification/comparative-real-task-bridge-v1-2026-08-29/source_snapshot)
and [checksums](verification/comparative-real-task-bridge-v1-2026-08-29/checksums.json)
are retained together. The independent verifier accepted all 384 cells and
all 34 files without mutation; 13 task/plan/cohort tests passed from that
frozen source directory.

The bridge preserves both 120-row candidate ledgers and all 21 original
transition admissions. Its default seven remain outcome-independent and all
retain zero forward changes. The Soletta incidence slice remains explicitly
outcome-selected and is not pooled into the default change rate. These are
cached conditioned residual relations, not whole-model equivalence or
existential projection. Their contexts are deterministic generated controls,
not captured configurator sessions. One cell per combination provides real-
residual correctness coverage but no performance repetitions.

## Tasks and semantic obligations

[The task adapter](../../cmbench/comparative/tasks.py) uses the same bounded
scenario, trace and semantic output contract for every backend:

1. **Exact count:** complete valid-assignment count for each version.
2. **SAT status:** exact Boolean answer under each partial assignment.
3. **Canonical witness:** first valid original-axis assignment in ascending
   bounded assignment order, or explicit `null` when unsatisfiable.
4. **Partial context:** ordered answers across additions, retractions, clears
   and version changes.
5. **Version history:** the same explicit context state while moving among
   three versions and returning to the base version.
6. **Equivalence delta:** exact equivalence flag, changed-assignment count and
   full XOR-vector SHA-256 for every declared transition.

An independent scalar CNF loop calculates all expected semantic rows before
the measured adapters. The canonical JSON result hash is pinned in each
contract. The worker output is then checked both against that expected hash
and against the complete independently generated rows. A scalar count cannot
replace a required context sequence; a changed count cannot replace the
declared delta-vector identity; and a solver's arbitrary model cannot replace
the canonical-witness contract.

The control scenario has 32 valid assignments in the base version, 32 after a
duplicate-clause edit and 16 after adding a genuine restriction. Consequently:

- base to duplicate is retained as a zero-change transition;
- duplicate to restricted has 16 changed assignments;
- reversing restricted to base also has 16 changed assignments;
- an incompatible positive assumption in the restricted version is explicitly
  unsatisfiable;
- clearing assumptions and returning to the base version restores the earlier
  answer.

These mechanisms are valuable controls, but generated data is not evidence of
real configurator-session frequency or domain generalization.

## Backend and lifecycle boundaries

- **CM** compiles CM-IR and evaluates the packed flat representation. Its
  private persistent pool behavior remains governed by the earlier session
  controls; no production default changed.
- **CSE** independently compiles the structural-CSE flat representation.
- **Direct CNF** evaluates clauses without calling the CM compiler or using a
  stored answer.
- **SAT** uses installed `python-sat` 1.8.dev20 / `Cadical195`. The saved
  extension SHA-256 is
  `64d3527aa49128215af9ce93a5a3eea98d578932daf68b68b1480da8d5b8b6be`;
  the wrapper SHA-256 is
  `b70978aa7377d040e46a6d125f30aec75947d200966bc6daca74c812c558cfc2`.
  This is partial binding identity, not a complete native build lock.

Fresh-engine cells create a new engine for every task evaluation. Resident
cells retain one engine across the complete trace and compile versions on
demand. Across the run, each backend created 256 fresh engines versus 48
resident engines. These are audited construction counts, not measured
speedups. The run is in-process, does not provide fresh interpreters per cell,
does not measure RSS, and does not control every process-global input cache.

The standard comparative contract does not itself contain a backend field.
The immutable plan binds each contract and cell to its backend; the stricter
task verifier now also binds each returned result to the planned backend and
case. It recomputes semantic byte/hash identity, checks query cardinality,
requires the functional-smoke resource boundary, and refuses native identity
on nonnative arms. Adversarial tests cover forged backend, resource, count,
claim and semantic-output records.

## Test evidence

[Seven task-adapter controls](../../tests/test_cm_comparative_tasks.py) cover
all task/backend/lifecycle combinations with a deliberately simulated tiny SAT
object, reuse counters, canonical witnesses, zero/nonzero deltas, selector
injection, malformed traces, cleanup on error and forged results.

[Three pilot controls](../../tests/test_cm_comparative_task_pilot.py) verify
deterministic plan construction, complete counterbalance, pinned independent
oracles, no-change/change/rollback cases and the 384-cell cardinality.

The current broad comparative pattern passed 58 focused tests, including
concurrent comparative controls already present in the checkout. The exact
final v4 source snapshot passed its 10 task-specific tests, while the later
real-bridge snapshot passed 13 task/plan/cohort tests. These counts overlap and
are not independent experiments.

## Reconciliation with concurrent work

### Existing P5 complete-relation smoke

The other comparative task already retained `p5-local-smoke-20260829-003`:
144/144 correctness cells across dense CM, packed bigint, packed words,
no-reinflation, CSE-flat and raw-flat. P5 and this task pilot are complementary:
P5 broadens CM representation arms for the complete-vector contract; the new
pilot broadens task contracts using four method families. Neither is a timing
campaign.

### Native-readiness scout attempts

The native-scout owner has retained and independently reconciled two consumed
Runpod attempts:

1. Pod `84442bdg4m47x8` matched its resources but a local controller/preflight
   schema mismatch raised `KeyError` before source upload. The owner proved the
   cause and added the missing integration control.
2. Pod `76exgpsv0y39bl` also matched its resources and both bootstrap health
   endpoints became ready. The 2,831,254-byte monolithic `POST /payload` then
   ended in client `ReadTimeout`; there was no upload acknowledgment, no
   `POST /run` and no retrieved workload evidence. Partial payload delivery is
   uncertain, so the controller correctly did not retry the ambiguous request.

Both pods received ownership-only DELETE 204, inventories were empty, detail
lookups returned 404, watchdog/controller guards exited, and the workload did
not run. The second attempt's independent receipt reports a conservative
aggregate comparative bound of `$0.001164632`, with provider billing subject
to lag. Neither attempt supplies CUDD, ZDD, d4, Linux-supervisor or performance
evidence.

The owner has prepared a locally tested 256-KiB chunked transport and a separate
proposal. At this reconciliation point it has no authorization. This task did
not inspect credentials, launch a pod, edit that transport, or duplicate its
ownership.

### Memory and recognition evidence

The separate 35-case corpus-memory run retained 630/630 exact calls and 420/420
whole-child RSS jobs. Its candidate temporary-memory estimate exceeded every
observed call-window peak but produced 18 fixed-4-MiB false refusals; it did not
calibrate or accept a production estimator.

CRSE milestone D8 retained exact Linux output but measured the frozen one-pass
rewrite policy at 0.929x versus no rewrite. It therefore refused unconditional
promotion. That negative result remains relevant: method reuse or a favorable
Windows result is not enough without task-total, environment-stable benefit.

The concurrently completed D9 follow-up trained and froze a bounded policy on
separate EPFL control circuits, then evaluated 33 workloads from circuit-
disjoint optimized BLIF artifacts. It abstained on all 33, with zero semantic
mismatches and 0.9818x task-total speed versus no rewrite; unconditional one
pass was 0.4290x. D9 validates the exact gate and abstention architecture but
again refuses production promotion.

## Gates closed and still open

Closed locally:

- bounded semantic contracts for count, status, canonical witness, partial
  context, version history and exact delta;
- adapters for CM, CSE, direct CNF and native CaDiCaL;
- fresh/resident lifecycle execution and counterbalanced functional schedules;
- complete independent semantic outputs, append-only evidence, checksums and
  frozen-source execution;
- all six task contracts over the seven default cached feature-model slices
  and the separately labeled nonzero-change control.

Still open:

- captured natural real-feature-model traces for all six new task contracts;
- repeated `k=8` scaling and all `k=12/16` work beyond the bounded `k=6`
  battery and one-pass conditioned-`k=8` coverage;
- fresh-process supervision, comparable RSS and balanced performance blocks;
- structural serialization/reload, streamed-output and frontier tasks;
- native CUDD/ROBDD ordering/restriction/extraction/reload;
- ZDD only where its set-family artifact matches the requested task;
- native d4 exact count with hash/build provenance;
- P6 noise/cell-cost calibration, P7 CM ablation, P8 external comparison and
  P9 untouched multi-allocation confirmation;
- full relevant regression, hosted CI and external-person reproduction.

## Next safe execution order

1. Add structural serialize/reload contracts and independent replay for CM,
   CSE and any native structure that actually supports the artifact.
2. Acquire or define a predeclared natural configurator-session trace source;
   the completed cached-real bridge used generated contexts.
3. Consume the native-scout outcome only if its owner later completes an
   explicitly authorized chunked attempt; do not infer native readiness from a
   prepared controller.
4. After native readiness, run a short fresh-process P6 calibration with RSS,
   balanced blocks and complete lifecycle charging.
5. Freeze P7 CM-internal ablations before any P8 external ranking, then use a
   new cohort/allocation for P9 confirmation.

Reproduction uses installed dependencies, a new output path and no provider
credentials:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_cm_comparative_*.py'
.\.venv\Scripts\python.exe -B scripts/cm_comparative_task_pilot.py run --output tmp/comparative-task-NEW-ID
.\.venv\Scripts\python.exe -B scripts/cm_comparative_task_pilot.py verify --output tmp/comparative-task-NEW-ID
.\.venv\Scripts\python.exe -B scripts/cm_comparative_real_task_bridge.py run --output tmp/comparative-real-NEW-ID
.\.venv\Scripts\python.exe -B scripts/cm_comparative_real_task_bridge.py verify --output tmp/comparative-real-NEW-ID
```

No cloud resource, network request, dependency installation, production-default
change, commit, push or publication was performed by this continuation. The
shared worktree's unrelated and concurrently authored changes were preserved.
