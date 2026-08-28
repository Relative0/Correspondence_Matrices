# Successful Runpod memory smoke: independent evidence audit

## Outcome

The one approved zero-volume retry completed on August 28, 2026:
**70 focused tests passed; all 312 measurement rows were successful;
the owned pod was deleted and absence independently checked.**

`Run CM safe work campaign` was the sole launch owner. This website-audit
task reviewed the new controller/preflight before creation, added 12
fake-input tests, and subsequently checked saved raw evidence. It did not
launch a duplicate or modify the owner's frozen controller/workload.
[Authorization and pre-create review](RUNPOD-ZERO-VOLUME-AUTHORIZATION-2026-08-28.md).

The pod `s2dpiij1msutml` was created at **09:03:07.375 UTC**, HTTP 201,
request `req_530653b6-91e6-4872-a3e3-480c51596c58`. The verified allocation
was Secure CPU cpu3c, two vCPUs, 4 GB RAM, $0.06/hour, 12-GB container disk,
zero pod volume and no network volume. The approved 65-file bundle was
uploaded using the reviewed token-authenticated HTTPS transport.

The controller retrieved evidence, deleted only its owned pod (HTTP 204),
and found both inventories empty at **09:04:47 UTC**. Its independent
watchdog reported no errors; both host wake guards exited. The separate
read-only check beginning **09:05:49 UTC** found both this pod and the
earlier HTTP pod absent (404) through both detail APIs and empty inventories.
The allocation lasted about **100.30 seconds** by the controller's clock.

Recomputed compute-only cost is approximately **$0.001672**, excluding
storage and provider adjustments. Billing still reported zero records for
its August 27–29 UTC bucket; **this may lag and is not a final zero-cost
invoice**. The pre-create aggregate projection included the $0.01 prior
allocation reserve and storage reserve: $0.03333 versus the $0.10 HTTP cap.
The broader campaign cap remained $0.20. No additional allocation or
replacement is authorized or queued.

## Raw evidence reconciliation

The independent read-only analysis checked:

- Exactly **312 expected cells**, with no duplicate, missing or extra cell:
  two synthetic families (`mixed-chain`, `alternating-tree`), k=6/8,
  dense/bigint/word representations, cold/warm schedules, three recorded
  repetitions and four or five diagnostic windows per call.
- **48 job records**: 36 cold-process jobs and 12 warm-process jobs. The
  312 rows contain **72 comparable representation calls**, not 312
  independent trials or datasets. Every row matched its job metadata.
- All rows reported `ok` and exact agreement with the study's CSE-flat
  reference. Each of the four cases had one consistent output hash across
  representations, schedules and repetitions. This audit did not execute
  an additional independent semantic oracle.
- All **70 distinct JUnit test cases**, with no failure, error or skip;
  all **13 locked dependency versions** matched the returned inventory.
- The ZIP hash and all **41 extracted files** matched archive bytes;
  the **19 snapshotted study sources** matched both their source manifest
  and the approved upload manifest. Runtime reported the owned pod ID,
  65 source files, Python 3.13.15, x86_64 and the pinned image digest.
- Memory-summary row counts, comparable counts, underestimation counts,
  maximum and median ratios recomputed directly from raw rows agreed.

Archive size: 95,100 bytes; uncompressed evidence: 1,160,040 bytes. The
existing 16-MiB bound was not approached. No retrieved source was executed
by this audit and no additional cloud query was needed to reconcile the
owner's separate postflight evidence.

## Memory findings and limits

These ratios compare measured **tracemalloc window peaks** with estimator
values. They are not speedups or whole-process RAM guarantees.

| Representation | Comparable calls | Old estimate too low | Candidate too low | Largest candidate estimate / measured peak |
| --- | ---: | ---: | ---: | ---: |
| Dense | 24 | 24 | 0 | 6.09× |
| Bigint | 24 | 24 | 0 | 77.23× |
| Words | 24 | 18 | 0 | 184.65× |

The old estimator underestimated **66/72** measured windows, with a largest
peak/estimate ratio of **306.61×** in a small dense case. The candidate
covered all 72, but substantial conservatism remains. Observed comparable
peaks ranged from 541 to 54,266 bytes across these small cases; large ratios
must not be mistaken for large absolute memory consumption.

All **1,008 recorded profile decisions admitted** their calls; none refused
or recorded a false admission/refusal. The tiny cases therefore did not
exercise policy boundaries. Underestimating a window here does not itself
prove that an admission policy exceeded its configured memory cap.

Remaining measurement and independence gaps:

1. Only two synthetic families and two small widths ran on one allocation.
   This is not full calibration, a real-world corpus study, or repeated
   machine-level replication. The held-out label is structural, not an
   external team's independent dataset or certification.
2. Tracemalloc is not an OS/RSS upper bound. Recorded RSS high-water values
   are process-lifetime values, not per-window peaks. Warm rows share a
   process; diagnostic windows and reference checks affect cache state.
3. Runtime reported 128 host logical CPUs but affinity to only `[40, 104]`,
   consistent with the two-vCPU assignment. Both captured cgroup-limit
   fields were null; CPU-quota and memory-limit enforcement were not
   independently measured by this evidence.
4. Exactness uses the project's CSE-flat implementation and cross-run hash
   consistency. No new external/scalar oracle was run in this smoke.
5. No CUDD/ROBDD/ZDD, incremental SAT, d4, or real-dataset comparison ran.
   No CM dominance or complete feature-model measurement-gap closure is
   established. The separate 12-file measurement pilot was not uploaded.

`production_estimator_accepted` remains **false**; production defaults are
unchanged. A subsequent experiment should preregister wider-width and
structurally diverse cases, test admission boundaries and overconservatism,
and improve OS memory-limit provenance before any acceptance decision.
That expanded workload needs its own exact scope and launch authorization.

## Reproducible evidence locations

Run directory relative to the project root:

```text
docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/runpod-authorized-20260827-213104/http-ephemeral-execute-001/
```

Within it, use `RUN.json`, `TRANSPORT-FREEZE.json`, `evidence.zip`,
`evidence/run-output/focused.xml`, and
`evidence/run-output/memory/{jobs.json,raw.jsonl,summary.json,source-manifest.json,source_snapshot/}`.
The parent directory contains
`HTTP-EPHEMERAL-FINAL-VERIFICATION-20260828-090555-697553.json`.

| Evidence | SHA-256 |
| --- | --- |
| `RUN.json` | `757d15ad5d1e1a55715060e6317e3d3d0ef42f869e81e2a7a632e3c4cb25d05c` |
| `evidence.zip` | `2a4cdf00e8c4f8803d7e87adb4199a12ccbac9f08f117dd013098b12172d8d73` |
| `memory/raw.jsonl` | `1ba4092dd2fd808086a1ed52d4c5d9f9928bf2942c58e13abdf1bb5edadb0881` |
| `memory/summary.json` | `ae00f9a5dca2871309ae3d6416b5869e9e6069c5db50586c3001a72792d63fce` |
| Final verification | `7fa1699ec849b98aaaf8518b7687b3e4b02e32f5bfedd73d6854cc3401c7dee5` |

Local verification for this continuation: **61 tests passed** (12 new
zero-volume/accounting checks plus 49 existing setup/lookup/transport
checks). This count is separate from the 70 remote focused tests. No full
regression, browser QA, website publication, commit or push was performed.
All nine updated audit/handoff documents passed whitespace and local-link
checks (33 links). `git diff --check` passed; existing line-ending and Git
ignore-permission warnings remain. The unrelated dirty core/website files
were preserved and are not attributed to this continuation.
The [setup handoff](RUNPOD-SETUP-HANDOFF-2026-08-28.md) now identifies the
working HTTP workflow and distinguishes it from historical port-free runs.
