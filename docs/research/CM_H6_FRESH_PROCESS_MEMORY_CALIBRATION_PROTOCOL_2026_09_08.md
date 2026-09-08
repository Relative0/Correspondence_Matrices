# H6 fresh-process memory calibration protocol

Date: 2026-09-08  
Scope: exact, non-neural representation-specific memory accounting  
Status: protocol drafted before decision-bearing execution

## Question

Can fresh spawned processes produce stable, nonzero, representation-discriminating
memory measurements for the current exact CM architecture, where the earlier Linux
`fork`/`wait4` campaign could report only a child peak below its inherited parent
baseline?

This is an H6 measurement-calibration gate. It does not reopen H2 or H3, fit a runtime
selector, alter production routing, activate H8, or identify a new H9 workload.

## Frozen workload

All cases come from the already admitted September 3 architecture-comparison freeze
and its independently generated exact oracles. Selection is made before memory results
are examined. The selected case documents and their stored oracle records are copied
into the H6 freeze itself, so each fresh worker reconstructs only its frozen case rather
than regenerating the full catalog during unmeasured setup.

- Complete relation: the three admitted `controlled_live_*n20*` observed cases and six
  balanced replicate-zero fresh cases spanning all three families, both tree/sharing
  shapes, and both `k=8`/`k=14` widths; compare unchanged
  `cm_dense_full_reinflation` and `direct_expression_bitset`.
- Repeated restriction: the first observed case for each frozen family prefix
  `decoder_index`, `decoder_reverse_shift`, `multiply_low_cone`, `addertree_sum`, and
  `multiply_add_low_cone`, plus the same six balanced fresh cases;
  compare unchanged R2, CM-IR bigint, CSE-flat bigint, and native fused slots at q1 and
  q64.
- Related multi-root: the first three frozen observed and first three frozen fresh
  related-root cases; compare unchanged Python sharing-union and separate-root arenas
  at q64.
- Every logical cell has cold and prepared/reused lifecycles and three independently
  spawned process replicates. Arm order is fixed in the freeze because elapsed time is
  descriptive only and is not a decision metric.

The resulting schedule contains 708 fresh-process rows. Refusals, failures, zero
deltas, unfavorable arms, and all raw samples are retained.

## Process and measurement boundary

Each row starts a new interpreter with `subprocess.Popen`; no `fork` or inherited Python
heap is allowed. The worker loads the frozen catalog, oracle, and native DLL, clears
current caches, collects garbage, starts `tracemalloc`, and then announces a common
post-import baseline. Process launch, imports, catalog/oracle validation, and native DLL
loading are outside task-incremental memory, but the absolute process values remain in
the raw row.

The controller, not the measured worker, samples the child every 1 ms:

- Windows: current and OS-reported peak working set, current private usage, and peak
  pagefile/commit through `GetProcessMemoryInfo`.
- Linux fallback: current RSS and private clean/dirty bytes from `/proc`.

For cold cells the measured phase contains representation construction, bindings,
evaluation, delivery, and serialization. For reused cells the controller records a
separate preparation peak and prepared-state retained boundary, then measures execution
above that prepared baseline. State, output, serialization payload, and required
artifact stay live until the retained boundary; they are then released, caches are
cleared, garbage is collected, and a post-release boundary is recorded.

Python-tracked current, peak, retained, and post-release bytes use the same phase
handshakes. Signed retained deltas are preserved. Nonnegative peak deltas never replace
their absolute endpoints.

Elapsed phase times and process-start latency are descriptive lifecycle diagnostics and
cannot support a speed claim.

## Frozen validity requirements

- every scheduled row exists exactly once and every logical cell has three distinct
  child PIDs and replicates;
- every child exits zero and completes the ready, optional prepared, result, release,
  and post-release handshake;
- every row matches the independent stored oracle and all replicates preserve output,
  ordering, and structure hashes;
- every OS endpoint is available, nonnegative, and internally ordered; every sampling
  thread stops and records at least one execution sample;
- the source closure, parent freeze/oracles, native DLL, raw file, summary, and
  independent replay remain hash-bound;
- any validity failure stops the phase without memory interpretation.

## Frozen calibration gate

The H6 memory signal is usable only if all conditions pass:

1. At least 75% of logical cells in every arm/lifecycle group have a positive median OS
   task-peak delta, taking the larger of working-set and private-usage deltas.
2. Both observed and fresh cohorts independently have at least 70% positive logical
   cells.
3. At least 50% of reused logical cells retain at least 64 KiB of prepared representation
   state by the larger of working-set and private-usage deltas.
4. At least 24 logical cells have a median OS task-peak delta of at least 64 KiB; among
   those cells, at least 75% have replicate range no larger than their median (a frozen,
   deliberately permissive 100% range/median limit).
5. In at least 50% of matched lane/case/query/lifecycle groups, the maximum arm median
   differs from the minimum by at least both 64 KiB and 10% of the smaller nonzero arm
   median. A zero smaller median still requires the absolute 64 KiB floor.
6. Independent replay reports zero source, schedule, exactness, stability, lifecycle,
   memory-accounting, and summary mismatches.

Passing means only `go_memory_calibration_only`. It permits drafting a separate frozen
development-only estimator candidate against unchanged current source. It does not
authorize a default router, production behavior change, RunPod, publication, or a
website claim. Failing any calibration condition closes H6 as still deferred for
routing purposes.

## Required local checks

- focused H6 freeze, operation, process-handshake, summary, and independent-replay
  tests;
- exhaustive small-function, sharing/tree expansion, and low-sharing controls already
  maintained by the H2/H3 and architecture suites;
- the repaired historical-freeze/current-drift tests;
- `scripts/cm_research_check.py` and the maintained non-neural research checks.
