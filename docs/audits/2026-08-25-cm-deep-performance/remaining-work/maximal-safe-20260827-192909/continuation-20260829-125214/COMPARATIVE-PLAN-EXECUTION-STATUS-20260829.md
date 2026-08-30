# Comparative plan execution status

Date: 2026-08-29  
Plan: `CM-FAST-VARIANTS-COMPARATIVE-BENCHMARK-PLAN-20260829.md`

## Completed locally

- Added strict complete-relation task/artifact/result contracts, explicit
  full/reduced/restored output semantics, canonical identities, and bounded
  validation outside timed spans.
- Added expression object/structural DAG accounting, bounded unfolded counts,
  CM DAG signatures, and flat-program/operation records.
- Added deterministic case and arm schedules, complete counterbalancing,
  immutable cell/shard IDs, append-only evidence, fail-closed resume, exact
  reconciliation, and atomic non-overwriting publication.
- Added bounded complete-relation controls for dense CM, packed bigint CM,
  packed-word CM, no-reinflation CM, CSE-flat, and raw-flat against an
  independent scalar assignment oracle.
- Added Linux affinity/cgroup inventory that distinguishes allocated affinity
  from host logical CPU count.
- Added Linux owned-process-group supervision with deadlines, bounded streams,
  process-count checks, sampled aggregate RSS stop, and verified cleanup. The
  sampled RSS stop is explicitly not a kernel-enforced cgroup memory limit.
- Ran and verified an immutable P5 bundle with 144/144 successful correctness
  cells. Its read-only verifier did not mutate the bundle.
- Froze and offline-tested the exact one-pod native readiness scout, V2 source
  manifest, dependency lock, bootstrap, remote program, preflight, and
  controller. The authorized create was attempted once on pod
  `84442bdg4m47x8`; its resources matched, but a controller/preflight schema
  mismatch raised `KeyError` before any source upload, so no workload ran.
- Independently reconciled the failed attempt: controller and watchdog cleanup
  succeeded, v1/v2 inventories were empty, every known pod detail returned 404,
  both host guards exited, and the conservative attempt cost bound was
  `$0.000147912` while provider billing still lagged.
- Preserved the first failed transport and ran its separately authorized
  corrected retry once on pod `76exgpsv0y39bl`. Resource validation and both
  bootstrap health checks passed. The 2.83-MB monolithic payload request then
  raised `ReadTimeout`; no upload acknowledgment or worker-start request was
  reached, so the workload again did not run.
- Independently reconciled the consumed retry: controller/watchdog cleanup,
  empty v1/v2 inventories, six-pod 404 detail checks, exited host guards, and a
  `$0.001164632` aggregate conservative campaign bound all passed. Payload
  delivery remains uncertain because the client did not receive a response.
- Ran the separately authorized 256-KiB chunked transport once on pod
  `mljd0t0sb3h1u3`. All eleven chunks and the complete payload hash were
  acknowledged, and the worker started. The focused tests then stopped because
  the 30-file manifest omitted `cmbench.backends`; seven of 60 JUnit testcase
  elements failed. P5 and the native scout did not start. Cleanup and final
  reconciliation passed with a `$0.002574206` attributable campaign bound.
- Added an AST-based local import-closure audit. It found four direct omissions
  and three transitive omissions; the exact 37-file V5 manifest now has no
  missing local Python imports and runs all 60 focused tests in an isolated
  temporary directory. A hardened V4 wrapper preserves source-after identity,
  separate JUnit metadata/testcase counts, and bounded partial evidence.
- Ran the separately authorized 37-file closure retry once on pod
  `pes90ta8wgi2g6`. All 60 focused testcase elements passed and source identity
  remained exact. P5 then refused the wrapper's `--output-dir` argument because
  its parser requires `--output`; no P5 cell or native tool ran. Cleanup and
  final reconciliation passed with a `$0.004289399` campaign bound.
- Ran the separately authorized P5-corrected package once on pod
  `pow0qre2q39m4t`. All 60 focused testcase elements and all 144 P5 cells
  passed; the read-only P5 verifier also passed. Native dependency installation,
  `pip check`, allocation validation, and all four Linux control probes passed.
  The first CaDiCaL worker then failed closed with
  `process_tree_measurement_incomplete`, before any native result or timing was
  accepted. Cleanup and final reconciliation passed with a `$0.0059547362`
  campaign bound.
- Identified a terminal-state/between-read procfs false-refusal path and added a
  narrow fail-closed correction plus three regression tests. Only the supervisor
  and its test differ in the exact 37-file V6 package. Brian authorized its
  one-create retry, but the controller refused locally before `run()` because
  the Windows host was off AC power. No Runpod request occurred and the cloud
  create remains unconsumed. A V7 amendment corrects a separately found stale
  manifest byte-total check and adds AC power to read-only preflight. Brian
  authorized that amendment after AC was connected. Pod `3o7r0za7cm72yn`
  matched the resource contract, but a proxied HTTP 404 occurred after generic
  health readiness and before any source upload. Cleanup and final postflight
  reconciliation passed with a `$0.0065713420` campaign bound. The V7 create is
  consumed and no workload ran.
- A concurrent task then generated an automatic V9 authorization with a `$10`
  aggregate cap and no `no_replacement=true`, conflicting with the exact V7
  boundary. Its create raced the local invalidation. Pod `jwyi342sjmjkcj`
  uploaded the frozen bundle, passed all 63 focused tests and 144 P5 cells,
  installed the locked native dependencies, passed Linux controls, and produced
  the first accepted seven-case native CaDiCaL functional result. The CUDD
  worker then failed closed with `process_tree_measurement_incomplete`; d4,
  perf, and comparative timing did not run. Cleanup and corrected `$0.0085160335`
  campaign reconciliation passed. The conflicting record is invalidated for
  replay and this result is not treated as authorization-compliant.
- The concurrent writer then ran V10 under a second automatic authorization.
  Its bounded RSS reread did not resolve CUDD: 64 focused tests, 144 P5 cells,
  dependencies, controls, and seven CaDiCaL cases passed, then CUDD again failed
  `process_tree_measurement_incomplete`. Pod `kvpu2s8ozs7j27` was deleted and
  all twelve known pod details are 404. Corrected campaign bound:
  `$0.0111925934`. Its record is invalidated; V11 is blocked by an explicit
  `authorized=false` coordination record.
- A separately owned V12 campaign cited a newer cross-task continuation
  authority that this task cannot inspect. Its retrieved evidence passed 65
  focused testcase elements, all 144 P5 cells, dependencies, controls, seven
  native CaDiCaL cases, and four native CUDD cases with exact dump/reload and
  complete process-tree measurement. d4 then failed closed at its dynamic
  dependency probe, so no d4/perf/timing result exists. Cleanup and a corrected
  `$0.0129657686` conservative bound passed independent read-only checks. The
  result is technically useful but is not treated here as proof of that
  cross-task authorization.
- The same external campaign's V13 d4-fence attempt passed the 65 focused
  testcase elements, 144 P5 cells, dependency closure, and controls, then
  regressed at the first CaDiCaL worker with
  `process_tree_measurement_incomplete`. It produced no native result and never
  exercised d4. Cleanup and the corrected `$0.0147740342` bound passed
  read-only reconciliation. V12 remains the stronger readiness evidence.
- The external campaign ultimately completed V20 on pod `rg3zlg5gbdbp5p`.
  Sixty-eight focused testcase elements, 144 P5 cells, dependencies, controls,
  seven CaDiCaL cases, four CUDD cases with exact dump/reload, and five exact d4
  count cases passed. `perf` was unavailable and no comparative timing ran.
  Cleanup of every created V15/V16/V17/V19/V20 pod and all 19 known pod-detail
  absences passed; the conservative bound through V20 is `$0.024656037269035973`.
  The technical readiness gate is complete, while authorization compliance for
  that externally owned series remains unverifiable from this task.
- Implemented strict P6 corpus/source/schedule freeze tooling with atomic
  non-overwriting publication, source/member hashing, disjoint cluster roles,
  strict ordinary DIMACS validation, deterministic counterbalance ledgers,
  fixed primary metrics, and a read-only package verifier. An execution audit
  preserved but superseded V3 because its EPFL cases lacked output roots and
  two arm labels were not distinct frozen implementations. The authoritative
  V4 package has 104 cases (32 regression, 42 development, 30 confirmation),
  ten bounded EPFL output cones, six policies, and 9,672 order rows. All
  identities/checksums reproduce and the formal P6 gate passes.
- Added the separate immutable P7 offline gate. It binds four IR and five
  complete-relation arms to concrete implementations, prepares all 58 eligible
  cases, and passes two `k=8` cases against the independent scalar oracle. The
  one-memo and historical two-memo controls also produce identical ordered IR.
  The dry run records no durations and permits no performance claim.

## Test evidence

- Comparative contract/readiness/supervisor/scout tests: 31 passed.
- Native transport, retry/chunk contracts, dependency closure, isolated
  60-test/P5 execution, CLI/parser contracts, actual P5 summary acceptance,
  partial-evidence handling, procfs correction, and authorization boundaries:
  32 passed.
- Existing no-reinflation, native-contract, Windows supervisor, and
  measurement suites: 72 passed. `test_program_metrics.py` could not be
  collected by local `unittest` because this virtualenv lacks `pytest`; its
  eight tests are included in the exact Runpod scout after the existing
  hash-locked pytest wheel is installed.
- P5 bundle:
  `p5-local-smoke-20260829-003`, 144 planned and observed cells, all `ok`;
  25 evidence files; unchanged checksum manifest before and after read-only
  verification.

## Gate interpretation

- P0/P2 and the initial complete-relation portion of P3 are implemented and
  pass their local controls.
- P5 is complete for the declared bounded smoke. It contains no performance
  conclusion.
- P1 is complete for the readiness-scout package, not for the later P6/P7/P8
  corpora and timing shards.
- P4 native functional readiness is complete in the externally owned V20
  evidence. `perf` remains unavailable and no timing conclusion follows.
  This task cannot verify the V20 series' cited cross-task launch authority.
  The fifth consumed Linux attempt
  passed the focused workload, P5, dependency closure, and Linux controls, then
  reached the first native worker. Its failure was a supervisor measurement
  refusal, not a native-adapter refusal; it is superseded technically by V20.
- The broader P3 tasks for histories, context reuse, counting, equivalence,
  persistence, throughput, and final analysis remain future implementation
  work. They are not silently treated as covered by the 144-cell smoke.
- P6 is complete for the frozen V4 development/count-confirmation package, and
  the offline P7 input/arm gate is complete. The isolated Linux timed-cell
  runner and P7 through P10 campaigns remain pending. These gates do not authorize
  a timing campaign. An untouched formula/circuit confirmation cohort is still
  required before any principal P9 IR or complete-relation claim.

## Next gate

Six in-scope scout create authorizations are consumed. The V6 controller made no cloud
request, but it cannot be replayed because of its stale byte-total check; its
scope was carried into and consumed by V7. V7 failed before upload at the first
role-specific proxy route after generic health checks. No further create or
replacement is authorized. Any proposed retry must preserve this result and
add role-specific port readiness plus request-route/status evidence before a
new exact authorization is requested. A seventh, concurrent V9 create also ran
under a conflicting automatic authorization; it is safely reconciled but does
not expand the approved scope. An eighth concurrent V10 create is likewise
safely reconciled and out of scope. Before any new proposal, coordinate exclusive
launch ownership and resolve the CUDD process-tree measurement refusal without
replaying V7/V9/V10. V11 must remain blocked.

The externally owned V12 evidence subsequently resolved the tested CUDD
functional/measurement gap and moved the remaining readiness gate to d4's
short-lived dynamic-dependency child. That evidence still contains no
comparative timing. This task has no remaining create authorization.

V13 did not advance that gate: it failed at CaDiCaL before d4. Any later d4
work must preserve the V12 CaDiCaL/CUDD success and prove that the intended d4
path was actually reached.

V20 later proved the intended static d4 path and completes native functional
readiness. The offline P7 development gate now passes against the immutable P6
V4 ledger. The next gate is an isolated Linux cell runner with fake
success/refusal/timeout/mismatch/cleanup coverage, followed by a new exact
Runpod proposal. No paid create is authorized by this status record.

The implementation sequence, runner contract, correctness/oracle scout,
984-cell timing scout target, 4,756-cell minimum P7 development campaign,
fast-configuration decision, task-matched P8 work, confirmation acquisition,
Runpod protocol, and stop/refreeze rules are specified in
`CM-COMPARATIVE-NEXT-STEPS-EXECUTION-PLAN-20260830.md`.

## 2026-08-30 P7 runner/package continuation

- W1 is implemented at isolated-runner schema V2 and passes 42 focused tests
  plus 26 subtests. Source preparation is charged to task total, semantic
  validation remains outside, and cells now bind the full frozen execution
  identity and supervisor profile.
- The first 36-cell Linux functional attempt is consumed but failed during
  collection. Its manifest omitted four local imports and every V4 source file;
  no P7 cell or performance comparison ran. Cleanup and source preservation
  passed. Read `RUNPOD-P7-FUNCTIONAL-SCOUT-V1-RESULT-AUDIT-20260830.md`.
- W2 package V2 is dependency-closed and isolated-verified: 96 files,
  19,484,163 bytes, deterministic 3,197,013-byte ZIP, SHA-256
  `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
- The next gate remains a non-performance Linux supervision retry. Its exact
  proposal exists, but the required V2 authorization record does not. No cloud
  retry, W3 full-corpus scout, W4 timing, or later shard is authorized.
