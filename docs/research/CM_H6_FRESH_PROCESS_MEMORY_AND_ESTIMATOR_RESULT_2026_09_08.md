# H6 fresh-process memory calibration and estimator result

Date: 2026-09-08  
Scope: exact, non-neural representation-specific memory calibration and one candidate  
Decision: **calibration go; estimator/routing no-go and still deferred**

## Result

The corrected H6 calibration completed all 708 frozen rows in newly spawned Python
interpreters. All 236 logical cells had three distinct child processes, exact independent
oracle agreement, stable output ordering and hashes, complete lifecycle handshakes, and
valid externally sampled OS plus matching `tracemalloc` endpoints. Independent replay
reported zero source-closure, schedule, exactness, lifecycle, stability,
memory-accounting, or summary mismatches.

Unlike the earlier inherited-Linux-fork campaign, the fresh-spawn protocol produced a
usable incremental signal. Every arm/lifecycle group and both observed/fresh cohorts had
100% positive median OS task-peak prevalence. Reused prepared-state retention of at least
64 KiB occurred in 52.542% of cells, 211 logical cells supplied stable material signal,
and the reported stable-signal prevalence was 98.578%. Forty-three of 74 matched groups
discriminated arms by both 64 KiB and 10%, a 58.108% prevalence above the frozen 50%
gate. All frozen calibration conditions passed.

That result permitted exactly one separate development-only candidate; it did not permit
production routing or RunPod. The candidate freeze used the six frozen fresh Lane-B
cases for calibration and locked the five observed C36 cases as holdout. Its only input
was preconstruction canonical expression size. An arm-specific nonnegative affine upper
envelope was compared with the identical pooled, arm-agnostic control.

The candidate improved median holdout log-ratio error by 64.928%, materially
underpredicted 1/20 cells (5%), had a 1.01884 median overprediction factor, selected an
arm within 64 KiB of the measured minimum in 4/5 cases, and beat the pooled control in
all six leave-one-fresh-case-out folds. It nevertheless failed the preregistered ordering
gate: only three holdout arm pairs were materially separated by the OS measurements and
the candidate ordered 0/3 correctly, below the required 70%. The multiply-low-cone
holdout exposed the consequential miss: the model selected CM-IR at 321,536 measured
bytes while the measured minimum was 65,536 bytes.

Therefore the frozen decision is `no_go_h6_estimator_and_routing_deferred`. Per protocol,
no second candidate is attempted, no runtime selector or production file is changed, and
no RunPod authorization request is prepared.

## Frozen evidence

### Fresh-process calibration

- Freeze canonical SHA-256:
  `465afe81d33afd28bd68f03418bc70d9889e37b342804e6f8b083cd794554ffb`.
- Raw SHA-256:
  `bf94ca10120442142c3ac28b36245f4538e08ac3766a75b42c2da65c754d7eda`.
- Rows: 708 total: 108 complete-relation, 528 repeated-restriction, and 72
  related-multi-root rows.
- Independent replay: `verified`, 708 rows and 236 logical cells replayed, every mismatch
  count zero, production routing unchanged, and RunPod request not permitted.

### Single estimator candidate

- Freeze canonical SHA-256:
  `937e20304dec769be99b0e0b6892247a4ee8643313a06426b6d1561f6129b915`.
- Calibration/holdout cells: 24/20, each aggregating q1 and q64 over three spawned
  processes.
- Passing conditions: parent validity, cell schedule, holdout error improvement,
  underprediction safety, overprediction bound, near-minimum selection, and leave-one-out
  robustness.
- Failed condition: pairwise ordering, 0/3 versus a frozen 70% minimum.
- Independent replay: `verified`, with zero source, schedule, fit, prediction, metric,
  decision, or summary mismatches.

## Verification

- Focused H2/H3, H6, candidate, historical-freeze/current-drift, architecture,
  restriction, multi-root, native fallback, and ordering/hash suite: 62 passed and one
  optional native skip.
- Maintained `scripts/cm_research_check.py`: 249 current-source tests and 121 immutable
  snapshot tests passed.
- The repaired historical-freeze test checks the September 3 artifact internally, while
  a separate live test still fails closed when current source drifts. No validity check
  was weakened.

Evidence is under:

- `docs/research/verification/cm-h6-fresh-process-memory-freeze-2026-09-08/`;
- `docs/research/verification/cm-h6-fresh-process-memory-attempt-001-2026-09-08/`;
- `docs/research/verification/cm-h6-representation-estimator-freeze-2026-09-08/`;
- `docs/research/verification/cm-h6-representation-estimator-attempt-001-2026-09-08/`.

## Disposition and next boundary

H6 now has a valid local measurement protocol, so future independently preregistered
non-neural studies may use it for descriptive retained/peak accounting. This panel does
not support a representation-memory router: the only allowed candidate failed its
cross-family ordering requirement.

H2 compact keys and H3 dense layout/copy fusion remain deferred under their September 8
profile-first no-go. H9 remains deferred under the binding behavior-change corpus result:
no replacement repositories, Yosys execution, new incremental-hardware machinery,
RunPod work, or cloud request was used. The next implementation phase requires a
genuinely independent active workload and a new preregistration; this stopped panel may
not be mined post hoc for another candidate.
