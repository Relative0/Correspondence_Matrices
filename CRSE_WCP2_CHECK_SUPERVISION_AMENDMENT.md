# CRSE-WCP-2S: evidence-preserving check supervision and bounded resumption

Revision: **2026-08-27.1**. Status: **proposed; resumption not approved**.

## Decision requested

Approve correction of the inline maintenance supervisor and one no-fix direct
Ruff recheck. Resume the remaining WCP-2 verification only if that recheck has
complete, eligible process/termination/output evidence. This explicitly reopens
the stopped verification gate; it does not erase or retrospectively approve an
unidentified process, grant additional descendants, or declare the prior run safe.

This supplements the two owner-approved, unchanged artifacts in CM_Computation:

- `CRSE_DURABLE_WORKSPACE_JOURNAL_PROPOSAL.md`, SHA-256
  `90b2a59a402344721d673bc19f4b70b4b4f372b789a0f7ea9e7ccb1d5ddf3089`.
- `CRSE_WCP2_VERIFICATION_RUNTIME_AMENDMENT.md`, SHA-256
  `b837236b2810746593ac832a004baa307eaa6d9d22eec6bd779a028b1e6868b0`.

All original file, fixture, runtime, environment, and effect boundaries apply
unless this amendment explicitly changes the stopped-gate continuation rule.
No new controller-file grant, interpreter, dependency, child executable,
environment value, process ceiling, or test-budget reset is requested.

## Incident and evidence limitations

The WCP-2V direct-Python preflight passed: native image and venv binding verified,
Python 3.10.11, SQLite 3.40.1 without connecting, matching PID/parent PID,
exit 0, 0.474 seconds, 110 combined stdout/stderr bytes, no observed descendant.
The helper draft was updated for the approved direct runtime and native
handle-based image/start identity checks. No helper or database test ran.

The first direct Ruff invocation used `check --fix --no-cache` on the six approved
new Python files. Its native root image was verified, PID 29324, start Unix
milliseconds 1787848291693. The supervisor raised
`Unexpected descendant count; stop.` It counted raw parent-PID matches before
checking their creation times, and its exception path skipped diagnostic
persistence. Consequently the child count/identities, final native exit code,
Ruff output, duration, and termination outcome were not retained. Shell exit 1
is not an independently collected Ruff exit status.

A later read-only Windows query restricted to PID 29324 and its direct-child
relationship returned no process records. It does not reconstruct the earlier
observation or prove there was never an extra process. The root runtime record
survives. The new journal integration test changed by two lines during Ruff;
the other changes are the reviewed direct-launch helper edits and status records.
All are within the approved twelve-file scope and remain unverified.

Windows documents that parent PIDs can refer to an earlier process whose ID was
reused; creation time is needed to reject such stale relationships. This makes
a false match a possible explanation, **not a finding about this incident**.
[Microsoft Win32_Process documentation](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process).

The harness evidence-retention defect is established from its control flow.
No further check, formatter, mypy, pytest, helper, or SQLite operation was run
after the supervision stop. Preserve this incomplete result; do not fabricate
missing logs, exit status, process identity, or retrospective measurements.

## Exact baseline and retained root

Controller:
`C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.

Require unchanged HEAD `c6107fa889053a34711412be23f2d8d065eb125c`, empty index,
and the following raw-file manifest before correcting anything. Preserve
unrelated `coordination/prompts/` unread. Do not reset, stage, or commit to
manufacture a match; drift requires review.

| Controller-relative file | Raw SHA-256 |
| --- | --- |
| `docs/decisions/ADR-0023-fixture-workspace-create-journal.md` | `bf3a9093b8de6d3c6b09ac85bfca817f50ea14a99129676325abf2a7b02418a9` |
| `src/fractilate_orchestrator/persistence/workspace_create_journal.py` | `7618fb50590ef9684f4084a643336ec67481114ce7a8aaca050535e2d1581b2c` |
| `src/fractilate_orchestrator/services/durable_workspace_create.py` | `006e6fa30dc0537db474a3f412b44306cf62e497cf015af9fa85240e97930e21` |
| `tests/unit/test_workspace_create_journal_contract.py` | `1254807bf5e23afdca5a4ba667ef88f0e4887adb57d154570c8309b6fafd9470` |
| `tests/integration/test_workspace_create_journal.py` | `4796c15312da2e7763fb613a7dcd8e8252e9845af873822c449be8a31c977fc7` |
| `tests/integration/test_durable_workspace_create.py` | `92f27ce0481a84914bcb95835d42339cdc84bfdc1b18fb6fca9ce1cd94952ac9` |
| `tests/fixtures/workspace_create_journal/crash_probe.py` | `b38e9f1eea31d361accf64249a10421043abae9127bb1ad0c0dea2929fd7a83a` |
| `coordination/WORKSPACE_CREATE_PERSISTENCE_READINESS.md` | `10a50e06adc71b0df125c4e45cfc99c4c813bb0a04ead0e16d34a96d15b5be2e` |
| `coordination/WORKSPACE_CREATE_READINESS.md` | `e0ab3a3ca1d92925023919b8180318e79b3b178ebd784f595ca3e349bf45bfb7` |
| `coordination/PROGRAM_STATUS.md` | `67fd654cbcf894e9307f15e431ce0ae857d3711a6afe963d931890338b20f1c9` |
| `coordination/plans/ACTIVE_PLAN.md` | `b2bed56fd23ecf9d9b7779a2608b013f8458b548c037daadb39196978a68ec06` |
| `coordination/NEXT_ACTIONS.md` | `523b42b3771fafbbe4da404ab62215eefb2c6e6e72b20cf151d93192043ab940` |

Current draft delta relative to that controller commit is **12 authored files,
1,906 additions, 16 deletions**, including the eight untracked create targets.
The existing limit remains **12 files, 3,000 additions, 150 deletions**; deletions
are allowed only in the four coordination documents. Remaining formatting,
corrections, tests, and records must fit without weakening invariants.

Continue only in the same owned, non-redirected root:
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp2-tests-20260827-01`.

It contains exactly these four retained files, **324 bytes total**:

| Root-relative artifact | Bytes | Raw SHA-256 |
| --- | ---: | --- |
| `preflight-1.runtime.json` | 107 | `9465354bb2a437b8e17bf7be002ad9714824c3cd2ca71dbed74e32af0646d2bc` |
| `preflight-1.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `preflight-1.stdout.log` | 110 | `87901c91aca006c66ef7f6f95e2f929c6aa484802ce91cc25a0e38aafb819097` |
| `ruff-lint-1.runtime.json` | 107 | `a1d8cdd2dd2a86b565fc502b40431b6dda7b60febcec6db63c136dc41e2f431b` |

No database, basetemp, helper record, cache, Ruff output log, or Ruff final
measurement exists. Revalidate the root/parents, exact entries and hashes before
continuing. Preserve the existing bytes and original runtime record. Do not
overwrite them or create pretend historical stdout/stderr. Create only new,
distinct evidence names and verified-absent pytest basetemp children. Never
delete or recreate the root to satisfy a precondition.

## Required supervisor corrections

Effective only after approval:

1. Keep the WCP-2V exact executable hashes, shell-free hidden launches, cleared
   environment, literal Python-only venv bootstrap, and no fallback unchanged.
   Revalidate those identities before launch. Hold the owned process handle and
   collect native image, PID and start identity before trusting emitted metadata.
2. Classify scoped Windows process candidates using PID **and creation identity**,
   not a raw `ParentProcessId` count. Read only process IDs, parent IDs,
   creation/exit metadata, and native executable identity for the owned
   root/helper and their direct-child relationships. Do not read command lines,
   environments, unrelated process lists, credentials, or user configuration.
3. Record each candidate's bounded metadata before making a stop decision.
   Exclude a stale parent-PID relationship only when creation evidence proves
   the candidate predates the owned parent, allowing for timestamp precision.
   Missing, conflicting, inaccessible or ambiguous identity is a stop condition,
   never permission to ignore a candidate. Account for candidates that exit
   between enumeration and handle inspection; disappearance alone does not
   prove they were authorized or stale.
4. Only pytest may have one helper, and it must match the closed crash case,
   owned helper record, native Python image, start identity, and actual pytest
   PID. No helper descendants; no Ruff/mypy/preflight children. One check at a
   time and at most two check-related OS processes remain the ceilings. Keep
   runtime concurrency one. Do not treat sampling as adversarial containment.
5. Make evidence retention unconditional after process start: use a top-level
   error/cleanup path that preserves bounded captured stdout/stderr, root
   identity, available exit status, timing, stop reason and termination evidence
   even when identity checks, process enumeration or pipe handling fail. Mark
   unknown fields unknown. Preserve the original error alongside cleanup errors;
   a cleanup exception must not suppress diagnostics.
6. Terminate only a known, native-identity/start-verified owned helper first,
   confirm its exit, then the verified owned root as already authorized. Never
   terminate by PID/name alone, terminate a stale match, or kill an unidentified
   candidate. Any uncertain termination or possible unexpected descendant
   stops all further launches and is reported, not converted to successful
   containment.
7. Bound supervision evidence as well as tool output. Use create-new run logs,
   at most 4 KiB per metadata frame and at most 64 KiB total supervision metadata
   per ordinary check, counted within its existing 1 MiB combined evidence
   budget. Record initial/final/state-changing observations, not unlimited
   polling logs. Truncation or metadata-cap exhaustion is a stop condition.
   Preserve 300-second ordinary-check and 30-second/4-KiB preflight limits.
8. Before the live recheck, permit at most two inline, table-driven maintenance
   shell self-checks of the classification/error-retention logic using only
   synthetic metadata and bounded in-memory streams. No subprocesses, SQLite,
   files outside the root, or arbitrary source execution. Each self-check has a
   30-second/4-KiB evidence cap, create-new logs, and covers: older stale PID,
   genuine unexpected child, ambiguous/missing creation time, PID reuse,
   exited-before-inspection, exact owned helper, over-count, and preservation
   of the initial error when cleanup also fails. Failure stops resumption.
   These do not substitute for the native recheck or certify containment.

The inline harness is not a new controller entry point. Any required authored
test/helper corrections remain inside the original six new Python files. Do
not add a persistent supervisor module, plugin, launcher, service, or dependency.

## One recheck, then conditional continuation

After successful synthetic self-checks, run exactly one direct Ruff recheck:

`C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/ruff.exe`
with `check --no-cache` and exactly these six targets, from the controller root:

```text
src/fractilate_orchestrator/persistence/workspace_create_journal.py
src/fractilate_orchestrator/services/durable_workspace_create.py
tests/unit/test_workspace_create_journal_contract.py
tests/integration/test_workspace_create_journal.py
tests/integration/test_durable_workspace_create.py
tests/fixtures/workspace_create_journal/crash_probe.py
```

No `--fix` on this recheck. It is **Ruff lint iteration 2 of 3**, not an extra
diagnostic iteration. Use distinct `ruff-lint-2.*` logs. The normal 300-second,
1-MiB, zero-descendant limits apply. An eligible result requires verified root
identity, no actual/possible unexpected descendant, complete bounded diagnostics
and confirmed exit. Ruff exit 0 or ordinary lint findings with exit 1 can be
eligible after inspecting the diagnostics; neither turns an unverified draft
into passing code. An execution error, identity ambiguity, lost evidence,
resource failure or unexpected child stops again; do not use iteration 3 to
investigate another supervision failure.

Only an eligible recheck authorizes continuing the unused original budgets:

- One remaining Ruff lint iteration, up to three formatter iterations and three
  format-check iterations, all on the same six files with `--no-cache`.
- Up to three strict-mypy iterations with the existing dedicated root cache.
- Up to three pytest iterations, each exactly the original nine modules and
  distinct `pytest-1`, `pytest-2`, or `pytest-3` basetemp.
- At most six named crash helpers per pytest iteration, one at a time,
  15 seconds/64 KiB each, 4 KiB metadata, no grandchildren.
- Original fixture-only SQLite creation/read/write/corruption/recovery grants:
  at most 64 new databases per iteration, 4 MiB each, DELETE/FULL serial access,
  and a 256 MiB retained-root budget.
- The one unused WCP-2V metadata-preflight slot remains available only for a
  necessary in-scope recheck, not as an extra command or changed runtime.

All preceding failures count. Do not silently add retries, tests, fixtures,
output budgets, or runtime processes. Finish the bounded work, update the four
coordination records and persistence readiness report with actual evidence,
review final scope/status, then prepare the next exact approval gate without
waiting for another request to continue. If the remaining budget is insufficient,
report the exact deficiency rather than removing tests or weakening safety.

## Preserved exclusions and suggested approval

No commit/staging, push, publication, hosted CI, production or existing database,
migration integration, native Git/workspace creation, worker/verifier, listener,
network effect, runtime upgrade, manual cleanup, or product-packet regeneration.
Do not read the unrelated CM work or controller prompts. The original product
plan/bundle decisions are unchanged and do not certify this draft.
`workspace.create/v1` remains separately unapproved.

> I approve CRSE-WCP-2S revision 2026-08-27.1, bound to its separately supplied
> raw-file SHA-256: the scoped supervisor corrections, bounded synthetic
> self-checks, one no-fix direct Ruff recheck, and conditional continuation within
> the remaining original WCP-2/WCP-2V budgets. The prior incident remains
> unresolved; process ceilings and all product-effect, commit, push, CI,
> production-database, and cleanup exclusions remain unchanged.

Do not implement resumption from this document until its exact revision/hash is
approved. Tool-level filesystem permission does not replace that owner decision.

