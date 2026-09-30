# Live-vtree integration development revision — 30 September 2026

This sibling directory repairs the prospective campaign harness and adds
developmental factor-exposure controls. It was later frozen as a separate
new campaign, reported in `CAMPAIGN_REPORT.md`. The original
`live_integration_2026-09-30` source, raw results, selection and
reports remain unchanged, as do the archived Phase 4/5 files. No previous
held-out input was rerun and no search objective or budget was changed.

**Harness repair.** `campaign_integrity.py` now validates the full registered
job sequence, unique `(id, method, repetition)` keys, row identity, source and
selection hashes, resource metadata, successful correctness flags, partitions,
positive stage times and explicit failure statuses. Selection and analysis
also re-evaluate saved exact partitions against independent CNF truth. The
runner checks old rows before resuming and new rows before appending. A semantic discrepancy is saved
as a raw row and stops the campaign, while later selection/analysis rejects it.
The validation winner is recomputed when the selection receipt is loaded; a
missing selection file cannot be recreated after held-out rows exist.

The worker returns its effective `RLIMIT_AS`, which the parent verifies against
the intended cap. The allocation negative control also checks its observed
limit. SIGSEGV and other signals are distinguished from SIGKILL; timeout,
memory error, malformed output and cap/identity disagreement retain separate
statuses. Mechanism GO now requires every planned fresh/live pair, zero
decision mismatches and a search-cost gain for both objectives. An incomplete
pair cannot become a favorable survivor-only mechanism result. Algorithmic GO
also requires mechanism GO because matched implementation was a prerequisite
for this integration gate.

`check_harness.py` fault-injects nine malformed saved-row cases, a forged
selection, an incomplete fresh/live pair, and seven worker outcomes. All were
rejected or classified as intended. It also ran a mocked validation → selection
→ held-out → analysis sequence, verified resume without duplicate rows, and
rejected a forged saved semantic partition. No formal worker ran in that check.

**Positive factor-exposure controls.** `dev_fixtures.py` contains three fixed
six-variable CNFs built from independent factors plus redundant cross clauses.
The cross clauses change the syntax graph but not the Boolean function. These
are development cases only; they are not validation or held-out candidates.
For all three, independent exhaustive truth is finer than B3's direct
partition, and the existing two-round/six-candidate M1 and M2 searches reach
the finest partition with identical fresh/live decisions.

| Development case | B3 direct blocks | L1/L2 direct blocks | Residual SAT calls: B3 → L1/L2 |
|---|---:|---:|---:|
| XOR pairs | 2 | 4 | 5 → 2 |
| XOR plus equivalence | 2 | 4 | 5 → 2 |
| XOR plus triple block | 2 | 3 | 6 → 4 |

These checks prove the integration can expose missed factors on constructed
small examples. They are not a new performance claim or a basis for changing
the original held-out NO-GO.

**Hostile branch repair.** The stress worker now checks the original CNF,
second referenced root and memory after every failed move in the later branch,
as well as after immediate and long-sequence inverses. The revised deterministic
walk forced 6 such later failures at n=12 and 5 at n=16. Both workers passed;
the main-root and second-root miter counts were 215/215 and 172/172. The
original live allocation was restored after each long walk. These remain small
Windows development stress cases, not proof of large-SDD memory safety.

**Verification.** The pinned Phase 5B virtual environment ran:

```powershell
& '../phase5b_output/.venv/Scripts/python.exe' -B check_harness.py
& '../phase5b_output/.venv/Scripts/python.exe' -B check_integration.py
& '../phase5b_output/.venv/Scripts/python.exe' -B check_stress.py
```

All passed: 39 development cases, 273 method runs, 518 matched candidate
evaluations, seven fresh-process worker checks, and the two revised stress
walks. The associated JSON and logs remain in this revision directory.

**Linux preflight.** The actual worker and larger SDDs ran locally in disposable
`python:3.11-slim` Docker containers (image digest
`sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e`),
with 4 GiB container memory and 2 GiB `RLIMIT_AS` per worker. Python 3.11.16,
PySDD 1.0.6, python-sat 1.9.dev15 and the pinned dependencies were used.
The real `trial_worker.py` entrypoint reported the cap and raised `MemoryError`
when a 512 MiB allocation was attempted under 256 MiB. Capped
B3/F1/L1/F2/L2 developmental trials returned the independent exact result;
live methods compiled once and reduced residual SAT calls from five to two.
Isolated failure checks returned `timeout` for the watchdog and `native_crash`
for SIGSEGV. The test-only modes cannot be reached by normal campaign calls.

| Capped live-SDD stress | Initial / restored live elements | Main / second-root SAT miters | Peak RSS |
|---|---:|---:|---:|
| n=20, 100 steps | 718 / 718 | 215 / 215 | 144 MB |
| n=24, 80 steps | 907 / 907 | 172 / 172 | 225 MB |
| n=28, 40 steps | 2,631 / 2,631 | 87 / 87 | 210 MB |
| n=32, 20 steps | 5,648 / 5,648 | 44 / 44 | 323 MB |

The separate n=32, 50-step attempt reached its 45-second watchdog and remains
recorded in `linux_scale_timeout_32x50.json`. The shorter n=32 walk completed
in about 25 seconds. This is a workload cost limit, not an observed exactness
failure; it does not establish that larger walks fit a future 20-second formal
worker watchdog. `linux_preflight_results.json` and `linux_scale_results.json`
retain the full results and source hashes. The containers used `--rm` and no
Runpod resource was created.

No old manifest, freeze receipt, selection, validation rows or held-out rows
were copied here. A new 36-record prospective `candidate_manifest.json` and
`CAMPAIGN_PROTOCOL.md` were prepared here before the subsequent freeze. The
generator uses independent modules with redundant syntax bridges and two
prime-control families. It excludes all prior held-out, prior integration,
tooling-probe and developmental CNFs. No new formal instance was evaluated
for B3 factor exposure, search outcome or complete time while drafting.
The Linux receipts predate this generator revision and therefore pin the
tested worker/preflight source, not the new manifest. The subsequent formal
freeze repeated the capped-worker controls on Linux. See `CAMPAIGN_REPORT.md`
for the separately frozen 756-row campaign and its mechanism GO / algorithmic
NO-GO. The registered protocol and manifest are unchanged after freeze.
