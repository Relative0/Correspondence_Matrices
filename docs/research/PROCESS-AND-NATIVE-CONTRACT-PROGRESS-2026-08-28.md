# Process supervision and native-contract progress

This is the preceding checkpoint. The later
[matched session/version continuation](SESSION-AND-VERSION-CONTRACT-PROGRESS-2026-08-28.md)
executes a bounded portion of the partial-context and version-update work
listed below. This note's counts and raw snapshots remain historical.

This local continuation adds bounded Windows worker supervision and native
adapter correctness controls. It does **not** establish a CM speed advantage,
complete the feature-model measurement repair, approve the production memory
estimator, or authorize another cloud run. Historical evidence and the
downloadable research ZIP are unchanged.

## Results actually obtained

| Verification | Result | Evidence boundary |
| --- | --- | --- |
| [Current focused checks](verification/research-check-v3-final-2026-08-28.json) | 182 passed, no failures/errors/skips | Includes 36 additional tests relative to the preceding 146-test follow-up; not full repository regression. |
| Original downloadable snapshot, extracted after checksum verification | 121 passed, no failures/errors/skips | Overlaps the current checks; not 121 additional independent experiments. |
| [Supervised CM/CSE/direct-CNF pilot](verification/measurement-contract-v3-2026-08-28/summary.json) | All 28 cells passed | Four tiny fixtures, fixed ordering, diagnostic timings only. |
| [Installed native CaDiCaL probe](verification/native-contract-v1-final-2026-08-28/summary.json) | Seven cases passed: 590 complete-vector solves and 41 session queries | Exactness, witnesses and unsatisfiable cores checked against bounded scalar enumeration; no performance comparison. |

The measurement pilot includes 12 fresh-process measurements, eight separate
instruction replays and eight fresh-process structural reloads. All 20 worker
results had a PID observed in their owned Windows job and verified zero active
processes after cleanup. All 15 frozen source files were unchanged; every
scheduled cell was retained, with no unfinished, missing, unexpected or
partial-tail records. See its [plan](verification/measurement-contract-v3-2026-08-28/plan.json),
[ledger](verification/measurement-contract-v3-2026-08-28/cells.jsonl) and
[checksums](verification/measurement-contract-v3-2026-08-28/CHECKSUMS.sha256).

The native probe freezes 17 source files, checks the extension and wrapper
hashes before and after execution, and validates the returned worker identity,
case/session cardinality, call accounting, exact vectors, witnesses and cores
again in the controller. Its owned job was empty after completion and all
frozen sources were unchanged. The seven cases cover zero-variable true and
false relations, unused variables, contradiction, the 64-bit boundary, a
satisfiable eight-variable relation and a seeded unsatisfiable case. It uses
14 solver instances: a separate complete-vector and interactive-session
instance for each case. See the [native plan](verification/native-contract-v1-final-2026-08-28/plan.json)
and [checksums](verification/native-contract-v1-final-2026-08-28/CHECKSUMS.sha256).
The earlier native receipt is retained; the final run additionally verifies
that JSON booleans cannot alias integer assumption literals in returned rows.

These are same-author, same-machine checks with a separate scalar algorithm,
not independent-person reproduction. Dependency compatibility also passed
`pip check`. Hosted CI and Linux enforcement have not been validated locally.

## Windows process/resource controls

[The supervisor](../../scripts/cm_process_supervisor.py) creates an unnamed,
owned Job Object, applies and reads back its limits, starts the worker
suspended without a visible window, assigns it to that job, and only then
resumes it. Normal child processes inherit the job; breakaway flags are not
enabled. Cleanup targets only that owned job, never process names or an
unrelated PID collection.

Default limits are 512 MiB of aggregate job committed memory, eight active
processes, a 15-second worker deadline, 256 KiB each for input/stdout and
64 KiB for stderr. Streams are bounded while reading, not merely checked
after an unbounded capture. A blocked input pipe cannot stall the supervisor.
Timeouts, output-limit failures, nonzero exits and unavailable enforcement
remain distinct outcomes; failed cleanup cannot become success. The
measurement ledger maps an output-limit failure to an error while retaining
the supervisor's precise status and reason.

The deadline includes startup bookkeeping, but Windows process creation
itself is not forcibly interruptible. There is additional bounded cleanup
grace. This is not a guaranteed total wall-time ceiling, CPU quota, filesystem
or network sandbox, or a mechanism for executing hostile programs.

The virtual-environment launcher was observed spawning additional processes.
Consequently the reported worker PID must belong to the observed owned-job
membership, but need not equal the initial launcher PID. An unobserved worker
PID is refused. Polling membership is not cryptographic process attestation;
very short-lived processes can be missed. The reported job high-water counter
comes from the OS rather than summing these PID samples.

[Fifteen supervisor controls](../../tests/test_cm_process_supervisor.py) cover
argument/limit refusals, stream caps, real stdout/stderr floods, nonzero exits,
blocked stdin, a child/grandchild timeout, surviving descendants, initialization
and assignment failures, membership and a paired allocation control. Other
platforms explicitly refuse before launch; their tests assert that refusal
instead of silently claiming equivalent containment or skipping the test.

### Important memory-counter finding

Under a 32 MiB job limit, a 1 MiB allocation succeeded and a 64 MiB committed
allocation was refused. The same 64 MiB request succeeded under a 128 MiB
limit. Allocations were freed, and the probe did not touch 64 MiB of physical
pages. This supports the configured commit-limit control on this host.

However, the initial control also returned a job peak counter of 84,541,440
bytes despite refusing the large allocation. An initial test assumption that
the counter must stay below the cap therefore failed. The corrected test
checks the paired allocation results and retains the raw counter; it does
not clamp it, call it RSS, or infer an out-of-memory cause from it. The exact
accounting explanation is not established by this probe.

Records explicitly flag a reported peak above the configured limit and keep
general memory-limit-hit attribution unknown without a violation notification.
A worker error or controller `MemoryError` is not automatically classified as
a proven memory-limit failure. Same-task process-tree RSS and comparable
native memory measurements remain open.

References: Microsoft's [Job Objects documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
and [extended job limit fields](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
describe job-wide committed-memory limits; Python documents the
[process-creation timeout limitation](https://docs.python.org/3/library/subprocess.html).

## Native adapters: executed versus prepared

[Native contract code](../../scripts/cm_native_contracts.py) and
[19 contract tests](../../tests/test_cm_native_contracts.py) keep these
boundaries explicit:

- **CaDiCaL executed:** installed `python-sat` 1.8.dev20, `Cadical195`, with
  the compiled extension and Python wrapper SHA-256 identities retained.
  Package version alone is not accepted as native availability. This is a
  partial binary/wrapper identity, not a full compiler/build/dependency lock.
- **Session reuse implemented:** one solver is reused across changing and
  cleared assumptions. Complete-vector extraction uses a separate solver
  and explicitly performs every bounded assignment query. Unused variables
  are declared; empty clauses are added explicitly. Unknown results, partial
  or invalid witnesses and invalid cores fail. Cores are not claimed minimal.
- **Constructor terminology corrected:** the inspected CaDiCaL wrapper does
  not support `incr=True` or `warm_start=True`; those flags remain false.
  Reusing a solver for successive assumptions is the tested behavior, not a
  claim that those unsupported constructor modes ran.
- **CUDD/ZDD not executed:** `dd` 0.6.0 is installed, but both compiled bindings
  are absent. No autoref/other pure-Python implementation was substituted.
  Simulated-manager controls check that automatic reordering is disabled
  before construction, fixed order stays fixed, search cost is included, and
  the actual reordered manager/root is exported and independently replayed.
- **Group sifting named accurately:** in the reviewed `dd` 0.6.0 source,
  parameterless `BDD.reorder()` invokes `CUDD_REORDER_GROUP_SIFT`, not ordinary
  sifting. The prepared contract records this method, order maps and counters.
  It is a construction-and-graph-export contract, not yet a complete native
  vector/count/restriction/reload comparison. Historical producer labels and
  results have not been rewritten based on a different wrapper version.
- **d4 not executed:** no explicit hash-pinned binary was configured. Prepared
  controls require matching binary/CNF hashes and the declared variable
  universe, and reject duplicate counts, fractional/scientific counts,
  out-of-universe results and unsupported output dialects. They only accept
  the bounded unweighted, nonprojected legacy integer-count contract. A cold
  CLI scalar count is not labeled a resident query, complete vector, or
  d-DNNF serialization result. Build provenance and native execution remain
  required gates; constructing a command is not authorization to run it.

The adapter tests use deliberately simulated objects where native libraries
are unavailable. They validate control logic, not native solver correctness.
The separately saved CaDiCaL probe is the only new native execution evidence.
The pinned wrapper's [CUDD implementation](https://github.com/tulip-control/dd/blob/v0.6.0/dd/cudd.pyx)
and [PySAT solver documentation](https://pysathq.github.io/docs/html/api/solvers.html)
are reference material; installed source and recorded hashes identify the
interfaces actually inspected for this follow-up.

## Reproduce locally

These commands use already-installed dependencies, new output directories
and no provider credentials. They do not install, commit, push or publish:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_research_check.py --report tmp/research-check-NEW-ID.json
.\.venv\Scripts\python.exe -B scripts/cm_measurement_verify.py --pilot-output tmp/measurement-v3-NEW-ID
.\.venv\Scripts\python.exe -B scripts/cm_native_contracts.py --probe-output tmp/native-contract-NEW-ID
```

The first command now includes supervisor and simulated native-contract
tests; it does not run the native CaDiCaL probe. The second and third use
Windows job enforcement; unsupported platforms retain explicit refusals.
The native probe's top-level `completed` means its planned inspection
finished: inspect `sat.status` and the inventory for actual execution or
refusal. It never means all native backends ran.

The [prepared CI workflow](../../.github/workflows/research-checks.yml) remains
unpublished and has not run on GitHub. Its focused dependencies deliberately
do not install CUDD, PySAT or d4. The older
[v2 progress note](REPRODUCIBILITY-AND-CONTRACT-PROGRESS-2026-08-28.md) and source
snapshots remain historical records, not the current supervisor contract.

## Remaining gates

1. Implement and validate Linux process-tree enforcement and same-task memory
   measurements; do not treat the Windows commit counter as an RSS substitute.
2. Obtain reviewed native CUDD/ZDD/d4 builds, verify dependencies/build identity,
   and run their real ordering, count, graph extraction and reload controls.
3. Add matched CM/native partial-context and version-update tasks, including
   activation-literal histories and fresh-versus-reused baselines. The current
   SAT session probe is not that comparison.
4. Freeze a small real-feature-model pilot, counterbalance order, account for
   all lifecycle costs and refusals, then assess whether broader performance
   work is justified. The M01–M13 repair remains incomplete.
5. Complete hosted CI, full relevant backend regression and external-person
   reproduction before stronger claims or a replacement downloadable release.

No cloud resources, dependency installs, production-default changes, commits,
pushes or deployments were performed in this continuation. Existing unrelated
working-tree changes were left alone.
