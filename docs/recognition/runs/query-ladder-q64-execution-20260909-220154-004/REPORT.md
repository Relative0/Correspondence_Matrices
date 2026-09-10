# Exact q64 decision-surface execution report

Date: 2026-09-10

Status: `blocked_pending_second_distinct_physical_host`

This is a fail-closed hardware-independence blocker, not a performance no-go. One
physical host completed and independently verified the exact frozen schedule. No
second distinct physical machine was accessible under the local-only authorization,
and a same-machine VM is non-qualifying. Joint labels and all label-dependent results
remain unopened.

## Parent and baseline closure

- current source checkpoint: `e23a8ca63af923ecdf7f3f5ea01f20594c2f3ff3`
- embedded source checkpoint: `c4cfccd846771a4f72a1b429797b97cdb1ed3d83`
- parent file SHA-256: `3cf5c2672e01aae6130282f2ea1a65de32746597a59689605a2d913a675a0692`
- parent canonical SHA-256: `d31f1f19d43232ece53b24c6202caec7f82d4a57d869d461e74fe75db5ea378e`
- task-contract SHA-256: `64571e31193d7c4e0298ba17c2921311607d4f5ca20f7bd14aced260a29da59d`
- case-set SHA-256: `9a6e978db02508d7eae3f478283140ae7bd471e10307ff7d53644c0bb63ef010`
- label-policy SHA-256: `1251bd0e8aac0f6565f3a46e759ae7bfd482b823737472b5fdcb9d27f00f8c3a`
- baseline-closure file SHA-256: `347ce807e0567e6fc56ecc2eeb7de455ec843db0492991521a4370837d27ba79`
- baseline-closure canonical SHA-256: `3fb1ad9200fe10fa2176cda913d8fb55b987cef88eae94ad733f638979f67ea5`

All 16 exact-arm implementation/build sources are Git-content-identical to the
embedded checkpoint. Windows checkout line-ending normalization was recorded
separately from source-content equality. No qualifying prior 72-case, eight-arm,
q64, 16-block, two-physical-host package was found. The later H2/H3/H6, hardware,
and independent-workflow additions do not introduce a new task-identical q64 arm.

## Sealed child execution freeze and preflight

- child-freeze file SHA-256: `87ca40e32b0ee33e73e557d41d7bbc01ca1a6a1940669a54470d2f8e52a18a6f`
- child-freeze canonical SHA-256: `02e4df3eca592d69598330017070270c08c55e4ef4a70f4dffddf91020984d46`
- child source-closure SHA-256: `7c4af6742e2f39b6d487a8da9149f9f9086ed06bde3987164a7d60bd4b6df690`
- child independent-verification file SHA-256: `669854292ed11c631864544791382028e28581beb1b46d8b8ffccd9d70df7131`
- independent-oracle file SHA-256: `ea769d31fbeff60279671bb34607d7ee6161ece2e9ac4ace51bbc3cefd0c646a`
- independent-oracle canonical SHA-256: `3c35a69df65d433cbfa6bbb8a479e2c9e4a5598ffb04edb71742ac7e785782f2`
- functional-preflight file SHA-256: `c2b026fa7f0d7deeae797cf074e8d2fda4d7f2a8681bdb861e426abb5de46202`

The standard-library scalar oracle covers all 72 frozen cases and all 64 queries.
The synthetic-clock preflight checked 576 case/arm cells: every exact arm matched
the independent oracle. The 16 deterministic counterbalanced orders put every arm
in every position exactly twice, expanding to 9,216 cells per host.

## First physical host

- replication: `windows-physical-001`
- platform: Windows 10.0.19045, AMD64 Family 25 Model 80, 12 logical CPUs
- physical-machine SHA-256: `511b05dff7d58f683f4f188b4aded5bff2ad38857546ff8d238596deb34e9191`
- compiler: Microsoft C/C++ 19.44.35217 x64
- compiler-identity SHA-256: `9a2767299b3da52cb63c9c287ace3b6265b75ddf687c548b5defd6bec7485afe`
- native-library SHA-256: `e35d1f937e8d21977d2bebc2827a93d12aa62812a3c32b0628581eb35cc3abf4`
- expected/completed decision cells: 9,216 / 9,216
- successes/failures/refusals/timeouts: 9,216 / 0 / 0 / 0
- raw-data SHA-256: `a3658971d854f47ac692fcd8d58098b9602a46fb1eb33f97b62288d75fbb9390`
- result SHA-256: `2c006aeaa17953f67980ed1876589213372bb30fbff64560efd5844ca6ad66bd`
- host independent-verification SHA-256: `b2fc1d16ccfc94aecb693aed6c84605d02db6780b89ecd91d23039076889315f`
- charged-cost raw/p95 artifact SHA-256: `6c2dcd18ad183961e505262de5b2a6933ab540143865b58c65ec2bdb5e6533a1`

The independent host verifier found zero schedule, semantic, timing, charged-cost,
or source/artifact mismatches. Same-host label-free p95 costs in ns/case were:
feature/control `186325.29722222223`, bounded inference `37347.13055555556`, exact
verification `219.29861111111111`, and fallback dispatch `446.0722222222222`.
Expected fallback is not computed until joint two-host labels exist.

## Fail-closed disposition

- second physical host: unavailable under current authority
- joint label counts, abstentions, disagreements, and coverage: not derived
- material winner arms/source-group counts: not derived
- gross and fully charged speedups: not derived
- per-host 1.10x gates: not assessed
- normalized `crse-query-ladder-decision-surface-evidence/v1`: not created
- third surface verification: not created
- final decision-surface CLI: not run because its required normalized input cannot
  exist without two distinct verified physical hosts
- candidate/learning eligibility: not assessable
- production status: unchanged and disabled
- RunPod request: not permitted

The only active blocker is
`second_distinct_physical_host_not_available_under_current_local_only_authorization`.
The current bounded second-host bundle is `SECOND_HOST_SOURCE_BUNDLE_V2.zip`, SHA-256
`6baf8e95062b9b80f2dee4a5c98e16983ea0dfb2c111e681cc672e774a45671d`.
`SECOND_HOST_HANDOFF.json` gives exact Windows and POSIX commands. The earlier bundle
is retained and marked superseded rather than deleted.

## Preserved pre-timing attempts

- attempt 001 stopped before oracles or timing because the draft closure named an
  absent source path (`cm.py`)
- attempt 002 stopped before oracles or timing because a byte-only comparison
  misclassified Windows line endings as source drift
- attempt 003 completed preflight but was superseded before timing when the uncharged
  fresh-worker lifecycle was simplified; its bound source therefore was not reused
- attempt 004 is the only decision-bearing attempt

No partial or failed decision-bearing host attempt was discarded or retimed.

## Commands and checks

Preparation and execution:

```text
.\.venv\Scripts\python.exe scripts\cm_query_ladder_q64_execution.py prepare --run-dir docs\recognition\runs\query-ladder-q64-execution-20260909-220154-004 --replication-id windows-physical-001
.\.venv\Scripts\python.exe scripts\cm_query_ladder_q64_execution.py run-host --run-dir docs\recognition\runs\query-ladder-q64-execution-20260909-220154-004 --replication-id windows-physical-001 --max-seconds 14400
.\.venv\Scripts\python.exe scripts\crse_verify_query_ladder_q64_execution.py --run-dir docs\recognition\runs\query-ladder-q64-execution-20260909-220154-004 --replication-id windows-physical-001
```

Verification:

```text
.\.venv\Scripts\python.exe -m pytest -q tests\test_query_ladder_q64_execution.py tests\test_query_ladder_decision_surface.py tests\test_query_ladder_learning_freeze.py tests\test_learning_benchmark_handoff.py
# 47 passed

.\.venv\Scripts\python.exe scripts\cm_research_check.py --report docs\research\verification\cm-q64-first-host-research-check-2026-09-10.json
# passed: 263 current tests and 121 frozen-snapshot tests
```

The final two-host packager was syntax-checked and its one-host fail-closed guard was
exercised. It refused with `exactly two host IDs ... are required` and wrote nothing.

## Boundary confirmation

No model fitting or neural training occurred. No prospective case was accessed. No
memory-learning measurement, cloud/RunPod provisioning, deployment, publication,
production-routing change, commit, or push occurred. Existing modified and untracked
files in the shared working tree were preserved.
