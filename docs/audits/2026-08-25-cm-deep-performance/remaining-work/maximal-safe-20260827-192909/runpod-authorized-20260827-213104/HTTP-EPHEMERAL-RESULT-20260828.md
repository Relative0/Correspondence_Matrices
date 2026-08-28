# Runpod memory smoke passed — August 28, 2026

**The authorized smoke completed on Runpod.** All 70 focused tests passed;
312 raw measurement-window rows are successful and exact, representing
72 recorded representation calls. Evidence was retrieved and independently
verified. The owned pod was deleted, both API inventories are empty, and
both temporary host guards have exited. No further create is authorized or
queued. No production default, estimator coefficient, policy or routing changed.

This is a bounded functional smoke. It is not full regression, representative
estimator acceptance, accepted-corpus compatibility, real-workload evidence,
or a measured guarantee of process-memory enforcement.

## Actual execution

All times are UTC on August 28. Output directory: `http-ephemeral-execute-001`.

| Item | Recorded result |
| --- | --- |
| Create | HTTP 201 at 09:03:07.375164 |
| Pod / request ID | `s2dpiij1msutml` / `req_530653b6-91e6-4872-a3e3-480c51596c58` |
| Resource validation | Secure cpu3c, 2 vCPU, 4 GB RAM, $0.06/hour, 12-GB container disk, zero pod/network volume |
| Runtime | Pinned Python 3.13.15 image digest, x86_64 Linux; all 13 installed package versions match the wheel lock |
| Source upload | All 65 approved files / 691,789 source bytes; no account credential uploaded |
| Bootstrap / worker start | 09:03:55.292337 / 09:03:58.753460 |
| Focused JUnit | 70 tests, zero failures, errors or skips |
| Memory smoke | 312 successful/exact window rows, 72 recorded representation calls; study elapsed 16.697 seconds |
| Evidence archive | 95,100 bytes, 41 files; every extracted file matches its archived bytes |
| Teardown | DELETE 204; both inventories empty at 09:04:47.328386 |
| Watchdog | `controller_cleanup_verified`, no errors; controller and watchdog guards released and exited |

The source bundle and image digest recorded by the remote runtime match the
local transport freeze. The actual commands remained the approved locked
binary installation, `pip check`, `tests/test_output_budget.py`, and the
memory driver with k=6,8, mixed-chain/alternating-tree, no fixed context,
cold/warm schedules and three repetitions. BLAS threads remained one.

Runtime affinity was **[40, 104]**, exposing two CPUs. `logical_cpus=128`
describes the host count, not the allocation. `cgroup_cpu_max` and
`cgroup_memory_max` are null: no cgroup quota-enforcement claim follows from
this run. The 4-GB RAM figure is provider resource metadata.

## Memory interpretation and limits

Only **72** rows are eligible for estimator comparison; the other 240 record
different preparation/conversion/serialization windows. Never use 312 as
the estimator-comparison denominator or sum independent window peaks.

| Representation | Comparable windows | Legacy underestimates | Candidate underestimates |
| --- | ---: | ---: | ---: |
| Dense | 24 | 24 | 0 |
| Bigint | 24 | 24 | 0 |
| Actual word-packed | 24 | 18 | 0 |
| Total | 72 | 66 | 0 |

The candidate stayed above traced peaks in this small sample, but its
conservatism and coverage still need the preregistered larger study. Nothing
was fitted or promoted using these results. k=6,8 and one calibration/one
held-out structural family do not establish large-output behavior, all
contexts, retained RSS, corpus compatibility, or production safety. The
candidate remains `production_estimator_accepted=false` and real-workload
compatibility remains `not measured`.

The independent reviewing task separately checked the complete 312-cell
grid, 48 jobs (36 cold/12 warm), consistent case hashes, 70 unique JUnit
cases, 19 approved source snapshots and all 13 dependency versions. It also
reported all 1,008 diagnostic policy decisions admitted; this smoke does
not exercise their refusal frontiers. Its review is separate from the local
archive/raw/JUnit checks and the live postflight below.

## Independent cleanup and cost reconciliation

`HTTP-EPHEMERAL-FINAL-VERIFICATION-20260828-090555-697553.json` records fresh
read-only checks at 09:05:49 UTC: both v1/v2 pod details return 404 for this
pod and the prior `eidn8uu97y3b6q`; both inventories are empty. Both guards
were released and their process handles report exited. Source, bootstrap,
controller/preflight freezes and evidence checks all pass.

Estimated compute for this attempt is **$0.00167174** over the controller's
100.304630-second interval. Both HTTP allocations together are estimated at
**$0.00177279 compute**, excluding storage. Billing still reports zero
records/charges for the queried Aug 27–29 UTC buckets; **it may lag and is
not a final invoice**. Preflight reserved $0.01 for the prior allocation and
$0.01/hour for new storage. Its maximum 20-minute aggregate projection was
$0.03333334, within the approved $0.10 HTTP / $0.20 campaign caps.

## Local preparation and evidence pointers

The v3 adapter changed the requested and validated pod-volume size to zero,
included the prior-cost reserve in actual-price admission, and used a new
run directory. The new preflight rejects unaccounted billing and preserves
the prior allocation's reserve even while invoices lag. It retains the
Windows launcher/worker binding and read-only liveness checks.

- `check_http_transport_ephemeral.py`: 25 transport cases, four PID-binding
  cases, 28 storage/accounting cases and a real trivial Windows child probe
  passed. No credential/network/workload was used in these local checks.
- The independent task reported all 61 `test_cm_runpod_*.py` discovery tests
  passed before creation. That task launched no duplicate.
- `HTTP-EPHEMERAL-PREFLIGHT-20260828-090024-580129.json`: initial live preflight;
  the controller repeated live checks in `http-ephemeral-execute-001/PREFLIGHT.json`.
- `HTTP-EPHEMERAL-DATA-CHECK-20260828-090825-702020.json`: raw-data diagnostic
  recomputation, locked versions, runtime hash/affinity facts and cost estimates.
- `http-ephemeral-execute-001/RUN.json`, `TRANSPORT-FREEZE.json`,
  `POD-RESOURCE-CHECK.json`, `WATCHDOG-RESULT.json`, `evidence.zip` and
  `evidence/run-output/` preserve the actual run and raw outputs.

Frozen v3 controller SHA-256:
`3296099d0d6c30e83698d1638d7cdc4001fd9158ffce3d68d0d599ee44d4654f`.
Preflight-v2 SHA-256:
`2a784ed20486d85b7484bfe7de037c6872256ef1e6ef10895deae61b6223193b`.
Evidence archive SHA-256:
`2a4cdf00e8c4f8803d7e87adb4199a12ccbac9f08f117dd013098b12172d8d73`.

Both earlier HTTP controllers/output directories and all prior failed-create
evidence remain intact. The 65 source hashes still match. No nontrivial
local computation replaced Runpod. No website edit, staging, commit, push,
publication, credential-file change, or unrelated resource deletion occurred.

## Remaining work and next gate

The smoke gate is passed; the whole maximal-safe performance campaign is
not complete. Representative structural calibration, broader contexts,
accepted-corpus replay, full regression and retained-RSS checks remain.
No application workload has been supplied through this run.

`RUNPOD-NEXT-STRUCTURAL-VALIDATION-PROPOSAL-20260828.md` prepares the next
single bounded structural phase using the same 65-file/13-wheel package.
It is **not authorized or launched**. Full-suite/corpus uploads require a
separately frozen expanded manifest; this proposal does not cover them.
