# CM memory continuation status

Date: 2026-08-29

## Completed locally

The frozen structural Runpod result was reanalyzed as a temporary-memory-only
counterfactual. Across 360 comparable calls, the candidate estimate was above
the recorded `tracemalloc` peak in all 360; the legacy estimate was below the
peak in 285 and above it in 75. Under the exact inclusive rule
`estimate <= limit`, the candidate produces 18 temporary-memory false refusals
at the fixed 4 MiB threshold and none at 16 MiB or 64 MiB. This is separate
from the prior 90 strict-profile refusals that also included the k=16 variable
gate. No RSS conclusion or production acceptance follows from this analysis.

The row-level `estimate-1`, `estimate`, and `estimate+1` decisions, disagreement
intervals, fixed-limit matrix, hashes, and report are in
`boundary-counterfactual/`.

## Completed corpus/oracle/RSS study

Brian authorized the exact frozen proposal, and its one create is consumed.
Pod `4q816o02xw5lxn` ran the 71-file package with the 13 locked wheels on the
approved Secure 2-vCPU/4-GB allocation, 12-GB container disk, zero pod volume,
and no network volume. All 79 focused tests passed. The 35-case grid completed
420 isolated child jobs and 630 calls; every row was `ok`, exact, and matched
the independent scalar oracle. All jobs had external RSS/HWM observations.

The candidate was above the call-window `tracemalloc` peak in all 630 calls;
the legacy estimate was below it in 468. Candidate estimate/peak was 7.91x at
the median and 464.03x at the maximum. At a fixed 4-MiB temporary-memory
limit, the candidate would falsely refuse 18 dense EPFL k=15/16 calls; it had
no false refusals at 16 or 64 MiB and no false admissions at any tested fixed
limit. Whole-child RSS had a 41,115,648-byte median and 45,256,704-byte maximum,
but includes interpreter/import/compile/hash lifetime and is not a per-call
or enforcement measurement.

The controller deleted its owned pod (HTTP 204); both inventories are empty,
all campaign pod details are 404 through both APIs, and both host guards
exited. Billing for the new pod still lagged at the 06:32 UTC check. The
compute estimate is $0.002565 and the conservative campaign bound $0.032565.
See `../runpod-authorized-20260827-213104/HTTP-CORPUS-RESULT-20260829.md`.

## Completed native-scout chunked retry

The separately authorized third scout create is consumed. Pod
`mljd0t0sb3h1u3` matched the approved Secure 2-vCPU/4-GB, pinned-image,
12-GB-container, zero-volume request. Its eleven-chunk upload completed with an
exact payload hash and the worker started, resolving the prior monolithic
transport uncertainty.

The focused tests stopped on a missing local package in the 30-file manifest:
seven of 60 JUnit testcase elements failed with `ModuleNotFoundError` for
`cmbench.backends`. P5 and the native scout did not start. Cleanup, empty
inventories, seven-pod 404 detail checks, guard exit, and conservative cost
reconciliation all passed. The attempt bound is `$0.001409574`; its attributable
campaign bound is `$0.002574206`. See
`RUNPOD-NATIVE-SCOUT-CHUNKED-RESULT-AUDIT-20260829.md`.

A new local dependency-closure audit found all seven omitted direct/transitive
files. The exact 37-file V5 bundle has no missing local Python imports and runs
all 60 focused tests from an isolated temporary directory. A hardened V4
controller and remote wrapper preserve source-after and partial failure evidence.

Brian authorized that exact package, and its one create is consumed. Pod
`pes90ta8wgi2g6` uploaded all 37 files, passed all 60 focused testcase elements,
and preserved matching source identities. P5 then refused the wrapper's
`--output-dir` argument because its parser requires `--output`; P5 did not run
and the native scout did not start. Cleanup and final reconciliation passed with
a `$0.004289399` attributable campaign bound. See
`RUNPOD-NATIVE-SCOUT-CLOSURE-RESULT-AUDIT-20260829.md`.

The separately authorized P5-corrected attempt is also consumed. Pod
`pow0qre2q39m4t` uploaded all 37 files, passed all 60 focused testcase elements,
and completed and independently verified all 144 P5 cells. The native
dependency closure and Linux control probes passed. The first CaDiCaL worker
then failed closed with `process_tree_measurement_incomplete`; no CaDiCaL result,
CUDD result, d4 result, perf boundary, or comparative timing was accepted.
Cleanup and final reconciliation passed with a `$0.0059547362` attributable
campaign bound. See `RUNPOD-NATIVE-SCOUT-P5-RESULT-AUDIT-20260829.md`.

A narrow V6 supervisor correction now handles proven Linux terminal-state and
between-read procfs races while retaining the live-process missing-RSS refusal.
Only the supervisor and its regression test changed from V5. The exact 37-file
V6 package has a complete import closure and 63 focused tests. Brian authorized
its one-create proposal, but the controller refused locally before entering
`run()` because the Windows host was off AC power. No Runpod request or create
POST occurred, the V6 local output directory is empty, and that cloud-create
authorization remains unconsumed.

The AC guard also exposed a stale V5 byte-total check in the frozen V6
controller. A V7 host-preflight amendment corrects that local check, preserves
the V6 failure, uses a fresh shorter local output identity, and adds AC power to
the read-only preflight. Brian authorized its one create after AC was connected.
The fresh preflight passed, and pod `3o7r0za7cm72yn` matched the approved
resource contract. Both generic bootstrap health checks passed, but the next
proxied request returned HTTP 404 before any source upload or worker start. The
controller deleted the pod, both inventories are empty, all known details are
404, and postflight reconciliation passed. The authorization is consumed and no
replacement is authorized. See
`RUNPOD-NATIVE-SCOUT-HOST-PREFLIGHT-AMENDMENT-RESULT-AUDIT-20260829.md`.

A concurrent workspace writer subsequently created a V8/V9 wrapper and an
“automatic” V9 authorization using a `$10` aggregate ceiling. That conflicted
with the exact V7 no-replacement boundary and the `$0.20` campaign cap. This
task invalidated the record for replay, but V9 had already created pod
`jwyi342sjmjkcj`. Its controller retrieved evidence and deleted the pod. Final
read-only reconciliation found empty inventories, all eleven known pod details
404, exited guards, verified watchdog cleanup, and a corrected `$0.0085160335`
campaign bound.

The out-of-scope V9 evidence nonetheless advances the technical record: all 63
focused tests and 144 P5 cells passed, dependencies and Linux controls passed,
and native CaDiCaL passed seven functional cases. The CUDD worker then failed
closed with `process_tree_measurement_incomplete`; d4 and perf did not run. No
performance comparison follows. See
`RUNPOD-CONCURRENT-NATIVE-SCOUT-V9-RESULT-AUDIT-20260829.md`. Its authorization
is preserved under `.invalid-no-replacement`; no further create is authorized.

The concurrent writer also completed a second automatic V10 create before its
authorization file was discovered. Pod `kvpu2s8ozs7j27` passed 64 focused tests,
144 P5 cells, dependencies, controls, and the same seven native CaDiCaL cases.
A bounded RSS reread did not fix CUDD: it again failed with
`process_tree_measurement_incomplete`, before d4/perf. Cleanup and twelve-pod
absence checks passed; the corrected campaign bound is `$0.0111925934`. The V10
authorization is invalidated for replay. A prepared V11 controller is blocked
by `authorized=false`; it has no output directory or create. See
`RUNPOD-CONCURRENT-NATIVE-SCOUT-V10-RESULT-AUDIT-20260829.md`.

An externally owned V12 campaign then ran under a record that cites a newer
cross-task `$10` continuation instruction which cannot be verified from this
task. Pod `omsz7w8fmlhqn0` passed 65 focused testcase elements, 144 P5 cells,
dependencies, controls, seven native CaDiCaL cases, and four native CUDD cases
including exact dump/reload. CUDD process-tree RSS and cleanup were complete.
d4 then failed closed at its dynamic-dependency probe; no d4/perf result or
performance ranking was accepted. Read-only reconciliation verified deletion,
empty inventories, all 13 known details 404, and a corrected `$0.0129657686`
campaign bound. See
`RUNPOD-EXTERNAL-NATIVE-GAP-V12-RESULT-AUDIT-20260829.md`. This technical result
does not make the cross-task authorization verifiable here and grants this task
no further create.

That external task then ran V13 to fence d4's short-lived children. The frozen
37-file transport, 65 focused testcase elements, 144 P5 cells, dependencies,
and controls passed, but the first CaDiCaL worker regressed to
`process_tree_measurement_incomplete`. No CaDiCaL/CUDD/d4/perf result was
created, so V13 did not exercise d4 and V12 remains the stronger readiness
record. Cleanup, 14-pod absence checks, guard exit, and a corrected
`$0.0147740342` campaign bound passed. See
`RUNPOD-EXTERNAL-NATIVE-GAP-V13-RESULT-AUDIT-20260829.md`.

The external campaign continued through V20. V14 and V18 made no create;
V15/V16/V17/V19 failed at progressively narrower d4 setup/output-contract
gates and were cleaned. V20 pod `rg3zlg5gbdbp5p` completed 68 focused testcase
elements, all 144 P5 cells, dependency and Linux controls, seven CaDiCaL cases,
four CUDD cases with exact dump/reload, and five exact d4 counts. `perf` was not
installed and no performance measurement ran. Independent reconciliation found
empty inventories, all 19 known details 404, exited guards, and a corrected
`$0.024656037269035973` conservative bound. See
`RUNPOD-EXTERNAL-NATIVE-GAP-V20-RESULT-AUDIT-20260830.md`.

The immutable P6 V3 record was subsequently found execution-ambiguous: EPFL
rows lacked a frozen output root, `cm-compact-key` duplicated current compact
interning, and `cm-fast-frozen` had no distinct frozen stack. It was preserved
and superseded by
`docs/research/verification/comparative-p6-candidate-v4-2026-08-30`. V4 has
104 cases (32 regression, 42 development, 30 confirmation), ten deterministic
bounded EPFL output cones, and 9,672 order rows. Its formal gate and source
verification pass at freeze SHA-256
`54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd`.
The separate `comparative-p7-offline-gate-v1-2026-08-30` package binds four IR
and five relation arms, prepares all 58 eligible P7 cases, and passes two
non-performance `k=8` oracle dry-run cases. No paid benchmark ran. See
`P6-CORPUS-SCHEDULE-FREEZE-RESULT-AUDIT-20260830.md`.

## Verification

- Proposed remote focused set: 79 passed locally.
- New corpus transport offline set: 14 passed locally.
- Boundary-analysis set: 7 passed locally.
- Combined changed surface: 100 passed locally.
- Package source hashes: 71/71 match; no secret file is listed.
- Remote focused tests: 79 passed; 630/630 calls and 420/420 RSS jobs verified.
- Final read-only inventory/cleanup/evidence verification: complete.
- Native transport/closure/P5/procfs/evidence tests: 32 passed locally; the
  exact V6 package ran all 63 focused tests in isolation. The combined changed
  surface passed 135 tests.
- Latest remote partial success: 60 focused tests and 144/144 P5 cells passed;
  dependency closure and Linux controls passed before the procfs supervisor
  refusal. The later V7 attempt did not upload source or start the workload.
  The concurrent V9 run then passed 63 focused tests, 144/144 P5 cells, and
  seven native CaDiCaL cases before the same fail-closed measurement class
  appeared in CUDD. Concurrent V10 repeated CaDiCaL with 64 focused tests and
  again failed at CUDD despite the bounded reread change. Externally owned V12
  then passed both CaDiCaL and CUDD readiness and stopped at d4's dynamic
  dependency measurement fence.
- Current post-concurrency combined local rerun: 136 tests, 132 passed and four
  historical V6 transport failures/errors caused by the two current supervisor
  files no longer matching the frozen V6 manifest and its former 55-test count.
- A broader Runpod test run under the available global Python 3.10 had 66
  passes, 104 passing subtests, and nine pre-existing failures because
  `pathlib.Path.is_junction` is unavailable before Python 3.12. The pinned
  remote runtime is Python 3.13.15; no unrelated readiness source was changed.

No production default, estimator coefficient, dependency, publication,
commit, or push was changed. The V7 create is consumed; no additional pod or
replacement is authorized. The concurrent V9 create is also consumed and its
conflicting authorization was invalidated for replay. Concurrent V10 is also
consumed and invalidated; V11 is explicitly fail-closed with zero cloud writes.
V12 is safely reconciled as externally owned; its separate authority claim is
not verifiable from this task and is not permission for this task to launch.
Externally owned V13 is also safely reconciled but adds no native result beyond
the already-passing pre-native gates.
Externally owned V20 completes the technical native-readiness gate, but its
cross-task authorization remains unverifiable here and supplies no new create.
The local P6 freeze is ready as runner input, but the isolated Linux cell
runner and its negative controls must pass before a proposal is frozen. The
remaining sequence is recorded in
`CM-COMPARATIVE-NEXT-STEPS-EXECUTION-PLAN-20260830.md`; it is not launch
authority.

## P7 isolated runner/package V2 and failed Linux scout

The initial isolated-runner implementation and a 36-cell Linux functional
proposal were prepared after the plan above. Its one create is consumed. Pod
`1xh6csc4oxy067` matched the resource request and accepted the payload, but
pytest stopped with three collection errors because the 152-file manifest
omitted `cmbench.recognition.features`. Postflight closure analysis also found
three other omitted local imports and found that none of V4's 57 unique source
files was included. No offline-gate verification or P7 cell ran. The pod was
deleted, both inventories were empty, owned details were 404, and the saved
compute estimate is `$0.002207883052031199`. See
`RUNPOD-P7-FUNCTIONAL-SCOUT-V1-RESULT-AUDIT-20260830.md`.

The runner is now versioned at schema V2. Cell identities bind source,
configuration, artifact contract, lifecycle, resource profile, schedule and
worker-source identities; source loading is inside the declared task span;
independent oracle records are source-bound; partial-tail resume and limit
changes fail closed; code and active inputs are checked between cells. The
focused surface passes 42 tests and 26 subtests, including a real one-request/
one-result worker CLI check.

Offline gate V6 passes. Dependency-closed package V2 contains 96 files and
19,484,163 source bytes, including all 57 V4 sources. Its 3,197,013-byte ZIP
has SHA-256 `83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668`.
The AST closure, isolated tests, isolated offline verification, checksums and
read-only verifier all pass. See
`P7-LINUX-ISOLATED-RUNNER-GATE-AUDIT-V2-20260830.md`.

A narrower V2 Linux functional retry is frozen in
`RUNPOD-P7-FUNCTIONAL-SCOUT-V2-RETRY-PROPOSAL-20260830.md` at SHA-256
`b10c1a84115e11af3a733440e463144d111149674e1ae76b2e7d2d5cc491c133`.
It retains 36 functional cells, one create/no replacement, 20 minutes,
`$0.10` phase and `$0.20` attributable-campaign caps, and no performance
ranking. Its exact authorization file is absent; no V2 upload or create is
authorized.
