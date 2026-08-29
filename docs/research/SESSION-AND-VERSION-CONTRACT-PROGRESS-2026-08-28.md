# Matched session and version-change contract progress

CM, structural common-subexpression elimination (CSE), direct CNF BitSet and
native CaDiCaL agreed on every scheduled bounded comparison. This closes a
small correctness gap in the [preceding native-contract work](PROCESS-AND-NATIVE-CONTRACT-PROGRESS-2026-08-28.md).
It does not establish a speed or memory advantage, complete the measurement
repair, or justify a production-default change.

## Executed evidence

| Scope | Scenarios | Passed cells | Partial answers | Complete delta results | Native SAT solves | Flat-artifact replays |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [Main pilot](verification/session-contract-v1-2026-08-28/summary.json) | Six synthetic and seven cached real slices | 208/208 | 1,504 | 424 | 40,364 | 216 |
| [Separate known-change control](verification/session-known-change-v1-2026-08-28/summary.json) | One cached Soletta incidence slice | 16/16 | 112 | 32 | 4,124 | 16 |

A cell is one scenario/task/backend/lifecycle session, not one independent
dataset. Each delta result contains the complete earlier vector, later
vector, XOR vector and changed-assignment count. Output totals include the
same requests repeated across methods and lifecycles; they are not counts
of independent scientific observations. All 224 worker cleanups were
verified, with no missing, unexpected, unfinished or partial-tail records.

Every cell ran from a frozen 21-file source/data snapshot in a fresh
Windows-supervised worker. Both runs recorded unchanged frozen sources and
no concurrent changes to their selected live sources during execution.
The plans and scalar oracle vectors were saved before workers started;
neither the oracle nor previously computed outputs were supplied to the
worker. Returned CM/CSE flat programs were replayed using the separate
instruction interpreter in the controller. This is algorithmic checking
by the same author on the same machine, not independent-person replication.

### What the real slices actually showed

The main selection did not use output values or timings: sort the cached
case IDs, restrict to `k=8`, enforce the existing limits of 128 clauses per
version and 32 literals per clause, and take the first eligible ID per
history. No clauses were deduplicated or discarded to gain admission.
The resulting seven slices all had zero changed assignments:

| History | Slice | Earlier valid assignments | Later valid assignments | Changed assignments |
| --- | --- | ---: | ---: | ---: |
| BusyBox | hash | 64 | 64 | 0 |
| Fiasco | hash | 1 | 1 | 0 |
| FinancialServices01 | hash | 1 | 1 | 0 |
| Linux | hash | 1 | 1 | 0 |
| automotive2 | hash | 1 | 1 | 0 |
| soletta | hash | 2 | 2 | 0 |
| uClibc | hash | 4 | 4 | 0 |

These zero changes were retained. They verify no-change handling, not
sensitivity to realistic edits. The different counts also expose how
restricted these conditioned slices are; they do not characterize full
feature-model solution density.

The separately named positive control is
`soletta@2015-06-26_18-38-56->2015-06-26_23-03-00|incidence|k8`.
It has 46 earlier and 47 later residual clauses. Its known nonzero change
was the explicit reason for selecting it after inspecting the cached data.
All methods found four earlier valid assignments, two later assignments,
and exactly two removals. This outcome-selected diagnostic must not be
merged into the main selection to claim representative change coverage.

The six synthetic controls cover zero variables (true/false/true), a unit
flip, the 64-bit boundary, duplicate removal with no semantic change,
unused variables, and a seeded local edit with a disclosed planted witness.
Their first-transition changed counts are respectively 1, 2, 16, 0, 64 and 37.
The tests also cover empty clauses, rollback and cleared assumptions.

### Cached-data provenance and selection limits

Both runs preserve all 120 candidate decisions in their plans. The main
pilot selected seven, excluded 80 outside `k=8`, refused nine under the
bounded case contract, and retained 24 as outside its one-per-history
budget. Each plan also carries the original 21 transition admissions:
20 admitted historically and one Linux transition refused for lack of a
joint satisfying assignment. That earlier refusal was retained, not rerun
or silently dropped.

Inputs are the saved [residual cases](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/configuration-fm-version-delta-full21-2026-08-27/cases.jsonl)
and [admission ledger](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/configuration-fm-version-delta-full21-2026-08-27/admissions.csv),
associated with upstream source commit
`afa60ee2c836e7bdc4068e0f4f128ea31158d2ad`.
The cases SHA-256 is
`3a4a394f458e0064994b4339858401e523f8dea836a3a697120f9db83299ef0e`;
the admissions SHA-256 is
`9afbf841866b26e6bc0615160d1e64c6f627904a8729fdd9837c809fccbb113a`.
Selected vectors were independently enumerated and checked against their
saved packed-vector hashes before any worker ran.

These are conditioned relations with outside variables and auxiliaries
fixed to a saved joint context. They are not existential projections,
whole-model equivalence results, or a new acquisition of the upstream
corpus. The new checks do not independently reproduce the original
acquisition, feature alignment or conditioning pipeline.

## Matched tasks and reuse semantics

[The session driver](../../scripts/cm_session_contracts.py) gives all four
backends the same version-aligned clauses, variable universe and trace.

- Partial configuration returns SAT/UNSAT under the current assumptions.
  The trace visits empty, approximately quarter/half/three-quarter and full
  contexts, clears assumptions, changes versions, and returns to version
  zero. Two-version scenarios have 14 queries; the three-version control
  has 20. This is not the proposed full 64-query-per-level protocol.
- Version delta returns both complete vectors and their XOR/count. It
  includes self-comparison, adjacent versions, reverse transition and a
  repeated transition. A count alone cannot satisfy this contract.
- Fresh means a new representation or solver per partial query, or per
  individual version-vector extraction. Reused means one engine throughout
  the cell. Both still recompute each output; saved-answer lookup is not an
  implementation of either task.

For CM, persistent IR caching is explicitly enabled only in a private pool
inside the sequential worker; the original process-global pool is restored
even on failure. Fresh engines get new pools; reused engines retain their
pool and compiled per-version programs. No production defaults changed.
CM/CSE bind assumptions and evaluate only the remaining live variables,
using the word kernel for at least six free variables and the bigint path
below that. Zero-variable constants have an explicit adapter.

Direct CNF evaluates the clauses over the same remaining variables and can
reuse input columns, but not relation outputs. CSE retains its own compiled
per-version programs. These controls matter: structural and representation
reuse are not unique to CM.

Installed `python-sat` 1.8.dev20 / `Cadical195` is the native comparator.
Both SAT lifecycles preload identical activation-guarded clauses for all
known versions. Each query sets exactly one version selector true and all
others false. Public assumptions cannot inject selectors. Complete-vector
extraction explicitly solves every original-variable assignment in the
same order, without treating selectors as counted variables. This is a
bounded enumeration baseline, not evidence that SAT enumeration is the
best way to compute every version-difference workload.

Fresh and reused SAT therefore differ in instance/learned-state reuse,
not formula encoding. The experiment does not test online arrival of a
previously unknown version, native learned-state serialization, minimum
conflicts, or matched witness/core tasks. The preceding SAT-only witness
and core checks remain separate evidence. Wrapper and extension identities
are checked before and after native work; this is not a complete native
build/dependency lock.

Across the main pilot, each backend created 294 fresh engines versus 26
reused engines. CM and CSE each built 294 fresh programs versus 54 reused
per-version programs. These are audited construction counts, not speedups.
CM persistent-pool hits do not by themselves establish a memory saving.

## Why these timings are not rankings

Each cell has a fresh worker, but fresh representations inside that cell
do not imply fresh interpreters per query. Process-global input-mask caches
may remain warm. SAT preloads all known versions whereas CM/CSE compile
the requested version on demand. The order is fixed and sequential, with
no balanced repetitions or concurrent-workload control.

Per-call preparation/evaluation clocks are diagnostic. Session totals
include export, bookkeeping and cleanup; whole-process controller time
also includes startup, imports and identity checks. Artifact replay occurs
in the controller, outside worker timings. The Windows job peak is an OS
committed-memory counter, not process-tree RSS or representation-only
memory. No ratios, crossover boundaries or memory rankings are supported.

## Regression and reproduction

The [final focused receipt](verification/research-check-session-v1-final-2026-08-28.json)
records 206 current tests passed, with no failures, errors or skips, plus
121 tests from the unchanged original downloadable ZIP after archive,
membership and source-hash verification. Separately, 91 tests passed with
the current directory set to the positive control's frozen source root.
These suites overlap; their counts are not independent experiments.

The persistent-IR-cache suite passed five tests and the persistent-path
consistency suite passed nine. Dependency compatibility passed `pip check`.
`pytest` was not installed, so the additional pytest-style CSE/prepared-flat
suites were not run. Full repository regression and hosted CI remain open.

[The 24 session contract tests](../../tests/test_cm_session_contracts.py)
exercise the exact task results, feature/selector boundaries, fresh/reused
accounting, nonboolean SAT refusal, cleanup, private-pool restoration,
artifact replay, mutated/missing outputs and the selection ledgers. Their
small simulated SAT object tests control logic; only the saved native
pilot establishes actual CaDiCaL execution here.

Use already installed dependencies and a new output directory for every run:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_session_contracts.py --pilot-output tmp/session-NEW-ID
.\.venv\Scripts\python.exe -B scripts/cm_session_contracts.py --pilot-output tmp/session-control-NEW-ID --known-change-control
.\.venv\Scripts\python.exe -B scripts/cm_research_check.py --report tmp/research-check-NEW-ID.json
```

Use `--synthetic-only` instead of `--known-change-control` for the six
synthetic scenarios alone. Unsupported process enforcement or absent
native SAT is recorded as refusal, not a substitute backend. The focused
check includes the new unit tests but does not launch these native pilots.

Saved evidence is readable and individually downloadable from GitHub once
committed and pushed:

- Main: [plan and complete selection ledger](verification/session-contract-v1-2026-08-28/plan.json),
  [scalar oracles](verification/session-contract-v1-2026-08-28/oracles.json),
  [worker ledger](verification/session-contract-v1-2026-08-28/cells.jsonl),
  [frozen sources](verification/session-contract-v1-2026-08-28/source_snapshot),
  [checksums](verification/session-contract-v1-2026-08-28/CHECKSUMS.sha256).
- Positive control: [separate plan](verification/session-known-change-v1-2026-08-28/plan.json),
  [scalar oracles](verification/session-known-change-v1-2026-08-28/oracles.json),
  [worker ledger](verification/session-known-change-v1-2026-08-28/cells.jsonl),
  [frozen sources](verification/session-known-change-v1-2026-08-28/source_snapshot),
  [checksums](verification/session-known-change-v1-2026-08-28/CHECKSUMS.sha256).

The positive-control option was added after the main source freeze; each
run preserves its own exact code rather than replacing the earlier snapshot.
The original research ZIP, source manifest and historical benchmark runs
were not modified. The interactive HTML was not rebuilt in this continuation.

## Next useful work

1. Specify and implement balanced, repeated lifecycle measurements for these
   matched tasks: separate one-off current-version construction, resident
   multi-version use and previously unknown-version arrival. Resolve input
   cache state, extraction/replay obligations and all setup/cleanup costs
   before reporting crossover results.
2. Add tested Linux process-tree enforcement and comparable RSS/native
   memory measurements. The current Windows job counter is not a substitute.
3. Obtain reviewed native CUDD/ZDD/d4 builds and run their actual ordering,
   restriction, counting, extraction and reload contracts. No such native
   execution or dependency installation occurred in this continuation.
4. Extend the predeclared real cohort and `k=12/16` limits only after resource
   controls and output accounting are validated. Reproduce source alignment
   and conditioning independently, retaining exclusions and zero changes.
5. Complete the M01–M13 repair, relevant backend regression, hosted CI and
   external-person reproduction before stronger claims or a replacement
   downloadable release.

No cloud resources, credential access, dependency installs, commits, pushes
or publication were performed. Unrelated working-tree updates were preserved.
