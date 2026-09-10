# Exact q64 two-host decision-surface result

Date: 2026-09-10  
Status: `verified_complete_scientific_no_go`

The frozen exact-CM q64 measurement package is complete and valid on two distinct
physical machines. The final read-only handoff gate nevertheless abstained. Only
`native_fused_slots` was a stable material winner, covering 18 of 72 source groups
(25%), and fully charged headroom was below 1.10x on both hosts. No fitter, model,
implementation candidate, prospective case, advice path, or production route was
opened.

## Required disposition boundaries

| Question | Result |
|---|---|
| Workload independence | Established only for the pre-existing, source-blind q64 learning contract: its protocol and cohort were frozen before labels/timings and zero prospective cases were consumed. This is not claimed to be an independently active caller workflow and does not revise the separate active-workflow no-go. |
| Measurement validity | Valid. Both 9,216-cell physical-host schedules completed; per-host independent verification and a separate standard-library surface replay found zero schedule, semantic, timing, source/artifact, charged-cost, or summary mismatches. |
| Component/arm materiality | Exactly one arm, `native_fused_slots`, was a cross-host stable material winner, in 18/72 source groups. The other 54 groups abstained; cross-host winner disagreements were zero. |
| Candidate eligibility | No. Frozen support, prevalence, diversity, coverage, split-coverage, and fully charged headroom requirements did not all pass. |
| Candidate result | No candidate was run. The final result is gate abstention, not a failed implementation candidate. |
| Production status | Unchanged and disabled. Advice remains disabled. |
| Further RunPod request | Not permitted or needed. The authorized V3 work is complete, both used pods are absent, and the local scientific gate is a no-go. |

## Frozen identity and source closure

- checkout branch/checkpoint: `main` at
  `e23a8ca63af923ecdf7f3f5ea01f20594c2f3ff3`
- parent freeze file SHA-256:
  `3cf5c2672e01aae6130282f2ea1a65de32746597a59689605a2d913a675a0692`
- parent canonical SHA-256:
  `d31f1f19d43232ece53b24c6202caec7f82d4a57d869d461e74fe75db5ea378e`
- embedded source checkpoint: `c4cfccd846771a4f72a1b429797b97cdb1ed3d83`
- task-contract SHA-256:
  `64571e31193d7c4e0298ba17c2921311607d4f5ca20f7bd14aced260a29da59d`
- case-set SHA-256:
  `9a6e978db02508d7eae3f478283140ae7bd471e10307ff7d53644c0bb63ef010`
- label-policy SHA-256:
  `1251bd0e8aac0f6565f3a46e759ae7bfd482b823737472b5fdcb9d27f00f8c3a`
- baseline-closure file SHA-256:
  `347ce807e0567e6fc56ecc2eeb7de455ec843db0492991521a4370837d27ba79`
- child-freeze file SHA-256:
  `87ca40e32b0ee33e73e557d41d7bbc01ca1a6a1940669a54470d2f8e52a18a6f`
- child source-closure SHA-256:
  `7c4af6742e2f39b6d487a8da9149f9f9086ed06bde3987164a7d60bd4b6df690`
- oracle file SHA-256:
  `ea769d31fbeff60279671bb34607d7ee6161ece2e9ac4ace51bbc3cefd0c646a`

Key runner and verification source identities are:

| File | SHA-256 |
|---|---|
| `cmbench/recognition/query_ladder_q64_execution.py` | `6655e0701c1c443dff84e5a4dd445fcbbc8c44faecee243e17d6bc5dedfd172b` |
| `scripts/cm_query_ladder_q64_execution.py` | `bdf602e1aaf56e608e1993497a131cc2d98ed8172421ab5a249b7b09fb03d399` |
| `scripts/crse_verify_query_ladder_q64_execution.py` | `46630e8b35bd9ab5548046f45b522f15e20f8c15638fc56c1784e7d572ac0930` |
| `scripts/cm_package_query_ladder_q64_surface.py` | `6251fd9e4db885dd623bdd5819099c68c8051c61b45907cc3227b554725ba945` |
| `cmbench/recognition/query_ladder_decision_surface.py` | `be30e67bde02fa903f331cf24008c807485a47efd9fd2bd29813cb36ba220779` |
| `scripts/cm_query_ladder_decision_surface.py` | `008a137577821fc5e113443a27ddab0b610034f3608009c4209dd05d5a55cd93` |
| `scripts/crse_verify_query_ladder_q64_surface.py` | `b3e02b53bbae373e56f65fafa91474a1e793207a753184cef9b76d5e54e4a92e` |

The native source SHA-256 was
`dc614e542cee61634dd7aade2746a297be791d45ad993664cb00433195e15738`
on both hosts.

## Physical-host evidence

| Field | `windows-physical-001` | `physical-002` |
|---|---:|---:|
| Physical-machine SHA-256 | `511b05dff7d58f683f4f188b4aded5bff2ad38857546ff8d238596deb34e9191` | `b682d74af46e2c3476dd6607bb8540a34c013a46e0afae807baa42979e89d286` |
| Compiler identity SHA-256 | `9a2767299b3da52cb63c9c287ace3b6265b75ddf687c548b5defd6bec7485afe` | `7eb2d0cfe404f8c923dbb26fd3c84f22d457197088a88366a2ed7ea44b77055e` |
| Compiler | MSVC 19.44.35217 x64 | GCC 12.2.0 |
| Native-library SHA-256 | `e35d1f937e8d21977d2bebc2827a93d12aa62812a3c32b0628581eb35cc3abf4` | `163095565ef8e9cd89c496dbc31e80662fbc2c660b2a3957fcb44ddd3efd5278` |
| Expected/completed cells | 9,216 / 9,216 | 9,216 / 9,216 |
| OK/failed/refused/timeout | 9,216 / 0 / 0 / 0 | 9,216 / 0 / 0 / 0 |
| Raw SHA-256 | `a3658971d854f47ac692fcd8d58098b9602a46fb1eb33f97b62288d75fbb9390` | `1f46b19f4818f7f57dd33f915d0e5de717fa95b17418e94c32eb97f40219a5f2` |
| Host-verification SHA-256 | `b2fc1d16ccfc94aecb693aed6c84605d02db6780b89ecd91d23039076889315f` | `38409a8b1b85a1eb75f8210d9a336db02433d12ecaea1ef591e80e199a054ab1` |
| Charged-cost SHA-256 | `6c2dcd18ad183961e505262de5b2a6933ab540143865b58c65ec2bdb5e6533a1` | `61c37d2f7c46695b053ae8d13a76e96403dcafa1810fcd136988fae2c6661b94` |

The Linux host was a RunPod Secure Cloud CPU placement on machine
`926o5b6nm7yx`, AMD EPYC 9654, with no hypervisor flag or DMI VM marker. The
physical-machine identity differs from the Windows host. Absolute timings were not
compared between hosts.

## Surface and economics

- label-table SHA-256:
  `9d8925e84f36690cc4820e8ed88029c707a3f57c069442f9063893b8fc271807`
- stable material labels: `native_fused_slots` = 18 source groups
- abstentions: 54
- cross-host winner disagreements: 0
- overall coverage: 25%
- split coverage: fit 25%, validation 25%, audit 25%
- surface-verification SHA-256:
  `d9f9bd27642237fb09102c7258f15d8c352f0b76793a190dc81fd9255b3b2c8c`
- normalized-evidence SHA-256:
  `ff06e9b0ae278e7b26eba894e54248c0bb2b4f8af7c02db76a87e5df5f5f280e`
- assessment SHA-256:
  `c5de8c33915dcddd743af7f89aae72525ae5d6eb631d466d3869193d182c5b3f`

| Host | Best fixed | Gross speedup | Fully charged speedup | 1.10x charged gate |
|---|---|---:|---:|---|
| `windows-physical-001` | `native_fused_slots` | 1.154226 | 0.949341 | fail |
| `physical-002` | `native_fused_slots` | 1.147590 | 0.977972 | fail |

The standard-library-only replay independently re-read all 18,432 raw cells,
recomputed the frozen schedules, exact-output bindings, timing sums, p95 charged
costs, joint labels, surface hashes, and economics, and reported zero mismatches.
Its SHA-256 is
`d547a18c66ab497b53e47d8351ad71ce02f81c72cdd5d2e28bf7f2acb7d0fd96`.

## Final fail-closed gate

The final verifier returned exit code `2`, the expected scientific abstention code,
with the complete blocker list:

1. `insufficient_source_groups_per_label`
2. `fewer_than_two_material_winner_arms`
3. `decision_surface_coverage_below_0_80`
4. `decision_surface_split_coverage_below_0_80`
5. `charged_headroom_below_1_10:windows-physical-001`
6. `charged_headroom_below_1_10:physical-002`

Gross headroom alone exceeded 1.10x on both hosts. Fully charged economics did not,
and the 25% one-label surface also failed the frozen diversity and 80% prevalence
floors. The valid measurement therefore does not authorize a later development fit.

## Preserved failures and invalidated attempts

All pre-timing and transport failures remain in the run directory:

- local attempt 001 stopped before oracles/timing because its draft closure named an
  absent source path;
- local attempt 002 stopped before oracles/timing after byte-only line-ending drift;
- local attempt 003 passed preflight but was superseded before timing after the
  uncharged fresh-worker lifecycle was simplified;
- RunPod prelaunch 001 made no cloud resource after the battery-state preflight;
- RunPod V2 pod `ge36jazrfw8e56` failed before decision timing because V2 omitted
  three frozen transitive verifier dependencies; it was deleted and the failure was
  retained;
- RunPod V3 pod `cks3fraf95ln30` completed all three frozen commands and was deleted.
  The local controller then falsely rejected the retrieved verifier document because
  it looked for nonexistent `rows_checked` instead of frozen `completed_rows`. The
  original failed controller result remains unchanged; the remote completion, local
  exact replay, and postmortem are retained. No repeat cloud run was used to hide or
  replace that failure.

V2 and V3 estimated compute cost totaled approximately `$0.0295893`. Final RunPod
inventories were empty. No credential was included in either bundle or recorded in
evidence.

## Commands and checks

The V3 worker executed exactly the three commands from `SECOND_HOST_HANDOFF.json`:

```text
python3 scripts/cm_query_ladder_q64_execution.py prepare-host --run-dir docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004 --replication-id physical-002 --compiler cc
python3 scripts/cm_query_ladder_q64_execution.py run-host --run-dir docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004 --replication-id physical-002 --max-seconds 14400
python3 scripts/crse_verify_query_ladder_q64_execution.py --run-dir docs/recognition/runs/query-ladder-q64-execution-20260909-220154-004 --replication-id physical-002
```

The post-retrieval local commands were:

```text
.\.venv\Scripts\python.exe -B scripts\cm_package_query_ladder_q64_surface.py --run-dir docs\recognition\runs\query-ladder-q64-execution-20260909-220154-004 --host windows-physical-001 --host physical-002
.\.venv\Scripts\python.exe -I -B scripts\crse_verify_query_ladder_q64_surface.py --run-dir docs\recognition\runs\query-ladder-q64-execution-20260909-220154-004 --freeze docs\recognition\runs\query-ladder-source-blind-learning-freeze-20260904-001\FREEZE.json --host windows-physical-001 --host physical-002
.\.venv\Scripts\python.exe -B scripts\cm_query_ladder_decision_surface.py --evidence docs\recognition\runs\query-ladder-q64-execution-20260909-220154-004\NORMALIZED_EVIDENCE.json --freeze docs\recognition\runs\query-ladder-source-blind-learning-freeze-20260904-001\FREEZE.json --emit-handoff
.\.venv\Scripts\python.exe -B -m pytest -q tests\test_query_ladder_q64_execution.py tests\test_query_ladder_decision_surface.py tests\test_learning_benchmark_handoff.py
.\.venv\Scripts\python.exe -B scripts\cm_research_check.py --report docs\research\verification\cm-q64-two-host-research-check-2026-09-10.json
```

Results: 35 focused tests passed. The research check passed 263 current and 121
frozen-snapshot tests; its report SHA-256 is
`30d59a9b71e1693892a438e3c181f3094fbb91c26f539df36abff0901daac697`.

## Files and shared-tree status

Task-specific source files are the q64 runner/module, host verifier, two-host
packager, decision-surface module/CLI, RunPod bootstrap/controllers/V3 packager, the
standard-library replay, and `tests/test_query_ladder_q64_execution.py`. Append-only
evidence was created under this run directory, plus
`docs/research/verification/cm-q64-two-host-research-check-2026-09-10.json`.

The checkout was already shared and dirty. Existing tracked changes—including the
learning handoff, research docs, website material, and their tests—and unrelated
untracked work were preserved. No tracked file was reset, restored, overwritten, or
staged. The final tracked diff remained 17 files, 387 insertions, and 59 deletions;
these shared changes are not attributed to this second-host continuation. The run
directory is ignored, so its append-only evidence does not appear in short status.

No model training, prospective access, production change, publication, deployment,
commit, or push occurred. Cloud provisioning was limited to the two separately
authorized temporary CPU attempts described above, and both pods were deleted.
