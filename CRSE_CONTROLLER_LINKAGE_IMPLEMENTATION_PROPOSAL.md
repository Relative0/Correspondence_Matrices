# CRSE-WCP-3: controller linkage rehearsal in isolated fixtures

Revision: **2026-08-28.1**. Status: **proposed; not approved**.

## Requested decision

Approve an eleven-file implementation and fixture-verification slice that connects
workspace-create records to the existing controller external-operation and audit
APIs **in newly created fixtures only**. Prove a shared transaction boundary and
cross-aggregate program barrier. Do not install the linkage into the real
controller, register a production migration, or enable a native executor.

This follows the verified WCP-2C slice: 301 tests pass, targeted Ruff lint/format
pass, and strict mypy passes 82 source files. All 18 crash helpers and closure
acknowledgments passed. This proposal does not retroactively qualify the two
earlier stopped Ruff invocations or reuse their exhausted budgets.

No further commit is included. If the owner separately asks for a checkpoint,
commit only the explicitly requested files and preserve this verified content;
the conditional checkpoint rule below avoids treating unrelated future HEAD as
an approved base. Publication, hosted CI and every product effect remain separate.

## Exact continuation baseline

Controller: `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.

Require HEAD `b9dd7724a205ef08b5655839ca6db7dd97b5774e`, an empty index,
and exactly the following twelve tracked working-file versions. Other tracked
files must match that HEAD; preserve untracked `coordination/prompts/` unread.
The WCP-2 cumulative delta is 12 files, 2,665 additions and 17 deletions relative
to `c6107fa889053a34711412be23f2d8d065eb125c`, within its original limits.

| Controller-relative baseline file | Raw SHA-256 |
| --- | --- |
| `docs/decisions/ADR-0023-fixture-workspace-create-journal.md` | `d8703229281a4ffb3a1a0680c17d9e27af0919e9b7b949d2d4ac47af746192bc` |
| `src/fractilate_orchestrator/persistence/workspace_create_journal.py` | `3194c6a8b53591e4f327395d77e23c07c31d805334a4c247be9c3f1238d0d60d` |
| `src/fractilate_orchestrator/services/durable_workspace_create.py` | `72ebf2dc7f1b6cef9b8eb60ed7e5e7d38793d063e0eb051a8ee736d2205d0bea` |
| `tests/unit/test_workspace_create_journal_contract.py` | `892b6babe0ef3349dc88740a6d651d402421cdbdb07c21e771acfe3582f8b5b8` |
| `tests/integration/test_workspace_create_journal.py` | `9a9aa012d1a33df1b6601cfa6ad83a778f4b981082e4bfc2c78b07779c987936` |
| `tests/integration/test_durable_workspace_create.py` | `9e56568aa9769331329cd395efbf9e142518b0694dea4735b62263d9e61c873e` |
| `tests/fixtures/workspace_create_journal/crash_probe.py` | `301a132a45e8e62a2a58507d7380c49faed727b2468868efc60a141108d5e8a0` |
| `coordination/WORKSPACE_CREATE_PERSISTENCE_READINESS.md` | `2de68f61db96f7a38d95dfecb9e64e3271a426b2b74244cf3ecb78f7ca09ad86` |
| `coordination/WORKSPACE_CREATE_READINESS.md` | `59c8696eb27d1c7bd4b28aa28ed631e39ae2241866cceb504151c4a6c6b6baa6` |
| `coordination/PROGRAM_STATUS.md` | `9682e7d011e7ae59c13dfc9a755ea4d9a10ae8a6e300d959deafb888b4a16197` |
| `coordination/plans/ACTIVE_PLAN.md` | `74f6926878328e473006e90d660269b52715f8c507a8507ba9105aca1c031b75` |
| `coordination/NEXT_ACTIONS.md` | `eefd18de8d993d85e0b9d730503dcde319373d5ea9b6aa8693397cee1daaafdb` |

Optional, separately owner-requested checkpoint: instead of the HEAD above,
accept only its direct child whose complete tree equals that parent plus exactly
these twelve reviewed file contents, allowing only repository-declared line-ending
normalization independently checked against each raw file. Require no other tree
change, a clean tracked worktree and empty index; record the resulting immutable
SHA before work. This rule authorizes neither committing nor changing content.

Before writing, revalidate this proposal's separately supplied raw hash, the
baseline, runtime identities, absence of all seven create targets, and absence
of the new test root. Do not reset, switch, stage or remove files to obtain a match.
Preserve unrelated CM work and all prior test roots/cache artifacts. Existing Git
global-ignore warnings do not authorize reading or changing user configuration.

## Why a linkage rehearsal is needed

The WCP-2 journal has its own audit, receipts and barrier. Its embedded operation
bytes do not make it part of the controller's `events` chain or
`ExternalOperationStore`. The latter accepts an explicit SQLite connection,
requires a write transaction, and records source, receipt, audit and projection.
Its barrier query currently considers only generic external-operation projections.

The two recovery folds differ: a generic terminal conflict may release its
barrier after confirmed termination, while WCP-1R's conflicting workspace terminal
history must retain a barrier. A shared connection or copied digest alone cannot
resolve that difference.

The production `Database.connect()` creates paths and enables WAL with a
30-second busy timeout. Do not call it, its initialization/migration runner, or
existing database-backed integration fixtures in this slice. Use explicit
create-new DELETE/FULL fixtures instead. Existing WAL/runtime eligibility remains
a separate question; no runtime upgrade or legacy policy change is included.

## Implementation requirements after approval

Use one maintainer agent, this task's configured model/effort, and concurrency one.
No delegation, product worker, SDK client, shell/native Git or arbitrary driver.

1. Add an import-inert, explicitly fixture-only linkage store and a separate
   exact-fake coordinator. Require retained root/file/program/fixture identity;
   never discover a database or use a default path. Keep the verified WCP-2
   implementation unchanged and reuse its validated command models and pure fold.
   Do not add another production database bootstrap or general callback facility.
2. In the new fixture helper only, initialize the unchanged controller schemas
   `0001_initial.sql` and `0002_external_operations.sql`, necessary synthetic
   reference rows, and a private namespaced linkage schema. Use bounded statement
   parsing and individual execute calls within explicit transactions, not an
   implicit-commit script. Do not register a numbered migration or call the
   existing migration runner. Create/reopen must enforce exact schema/identity;
   unknown, partial or incompatible fixtures fail closed without repair.
3. Bind the complete workspace envelope to the exact stored operation plan,
   program, effect identity, repository binding, workstream/job, request hashes,
   fence and epoch. Preserve old schemas/hash domains and all false synthetic
   authority flags. A fixture linkage/approval receipt is not a real owner approval.
4. Use the real `ExternalOperationStore` and `append_event` APIs against the
   supplied fixture connection. Persist linkage sources, generic facts, both
   projections, domain-separated request receipts and controller audit events
   in one explicit transaction. No success receipt/capability escapes an
   unconfirmed commit. A rejected step poisons the complete joint transaction
   even if its immediate exception is caught. Reopen verifies both source histories,
   audit linkage, receipts and caches; never silently repair.
5. Expose a clearly named combined barrier query. Hold it whenever either
   authoritative fold holds a barrier, and permanently retain the workspace
   terminal-conflict veto. Preserve both projections separately; do not relabel
   a generic result as a workspace result or modify the old recovery semantics.
   Reject multiple distinct owners. Enforce cross-table admission in fixture SQL
   as well as application policy so direct legacy-store calls cannot bypass a
   workspace-held barrier in the linked fixture. A wrapper-only gate is insufficient.
   Do not attach these guards to a real controller database.
6. Commit claim/intent and one-use consumption before the exact fake call, outside
   every database transaction; commit observation/audit/receipts afterward.
   Duplicate commands cannot append or reissue capabilities. Enforce durable epoch,
   monotonic fences and permanent target/branch reservations across both histories.
   Restart, response loss, lease loss, stale evidence and conflicts never redispatch.
7. Revalidate typed values before serialization; do not rely on a fixture factory
   to demonstrate malformed raw input rejection. Bound byte length before decode
   and cardinality before materialization. Use explicit fixed synthetic time
   conversion where the existing aggregates use different timestamp forms.
8. Add ADR-0024 explaining the combined policy and deferred installation boundary.
   The strongest result is a verified integration rehearsal, not production
   readiness, Windows containment, power-loss immunity or exactly-once execution.

## Exact controller write grants

Create only these seven currently absent files; parent-directory creation is
limited to the new `tests/fixtures/workspace_create_linkage` directory if needed:

```text
docs/decisions/ADR-0024-fixture-controller-workspace-linkage.md
src/fractilate_orchestrator/persistence/workspace_create_linkage.py
src/fractilate_orchestrator/services/linked_workspace_create.py
tests/unit/test_workspace_create_linkage.py
tests/integration/test_workspace_create_linkage.py
tests/fixtures/workspace_create_linkage/fixture_store.py
coordination/WORKSPACE_CREATE_LINKAGE_READINESS.md
```

Modify only these four existing coordination files:

```text
coordination/WORKSPACE_CREATE_READINESS.md
coordination/PROGRAM_STATUS.md
coordination/plans/ACTIVE_PLAN.md
coordination/NEXT_ACTIONS.md
```

Limit incremental WCP-3 changes to **11 files, 3,000 additions and 150 deletions**
against the manifest-bound starting content, not against an unrelated mutable
HEAD. Deletions only within the four coordination documents; no whole-file
deletion/rename. All existing Python, SQL, tests, dependencies, entry points,
configuration, migrations and prior approved proposals are read-only.

Read this proposal, the four WCP-2/2V/2S/2C proposals, applicable instructions,
all baseline/write targets, and these additional exact controller inputs:

```text
AGENTS.md
.gitattributes
pyproject.toml
docs/decisions/ADR-0002-sqlite-and-audit-model.md
docs/decisions/ADR-0003-fake-adapters-and-live-disablement.md
docs/decisions/ADR-0007-external-operation-aggregate.md
docs/decisions/ADR-0021-workspace-create-contract-bridge.md
docs/decisions/ADR-0022-workspace-create-recovery-hardening.md
src/fractilate_orchestrator/domain/models.py
src/fractilate_orchestrator/domain/enums.py
src/fractilate_orchestrator/domain/external_operations.py
src/fractilate_orchestrator/domain/workspaces.py
src/fractilate_orchestrator/domain/product_pilot.py
src/fractilate_orchestrator/domain/workspace_create.py
src/fractilate_orchestrator/state/external_operations.py
src/fractilate_orchestrator/state/workspaces.py
src/fractilate_orchestrator/adapters/workspace_create_intents.py
src/fractilate_orchestrator/services/workspace_create.py
src/fractilate_orchestrator/services/external_operations.py
src/fractilate_orchestrator/persistence/audit.py
src/fractilate_orchestrator/persistence/database.py
src/fractilate_orchestrator/persistence/migrations.py
src/fractilate_orchestrator/persistence/external_operations.py
src/fractilate_orchestrator/persistence/sql/0001_initial.sql
src/fractilate_orchestrator/persistence/sql/0002_external_operations.sql
tests/conftest.py
tests/helpers.py
tests/unit/test_workspace_create_contract.py
tests/unit/test_workspace_create_intents.py
tests/unit/test_workspace_create_recovery.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
tests/unit/test_external_operations.py
tests/integration/test_external_operation_persistence.py
tests/integration/test_persistence_and_audit.py
tests/integration/test_inert_external_operation_service.py
```

The three existing integration modules are reference-only, not executable grants.
Normal imports/static analysis may read existing package modules and installed
dependencies. No secrets, `.env*`, credentials, user configuration, unrelated
diffs, product repositories, or existing database contents.

## New fixture and verification authority requested

New root, confirmed absent during preparation:
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp3-tests-20260828-01`.
Recheck absence/non-reparse ancestors, create it once, and use create-new evidence
and distinct absent `pytest-1`, `pytest-2`, `pytest-3` basetemps. Never remove or
recreate a pre-existing target or reuse a WCP-2 database/cache.

This is an explicit fixture-only exception for new database creation, schema DDL,
synthetic reference rows, reads/writes, corruption tests and transaction recovery.
SQLite may manage its own rollback journals. No manual deletion, copying an
existing database, WAL/SHM, ATTACH, extensions, vacuum or background work.

Verify DELETE/FULL, foreign_keys ON, temp_store MEMORY, busy_timeout <=1,000 ms,
and page-size/max-page-count enforcing **4 MiB per database**. At most 64 databases
per iteration, 256 MiB retained root, one synthetic program and at most 16 total
operation plans per database. Bound each workspace history to 128 facts, command
receipts to 256, audit rows to 2,048 and serialized documents to 65,536 bytes.
Admission must reject atomically before an append can exceed these limits.

Tests must cover joint rollback/uncertain commit at each boundary, audit/receipt
replay and tamper, raw malformed/type/oversize input, stale epoch/fence, mixed
generic/workspace barrier admission, direct-store bypass attempts, sticky terminal
conflicts, causal/freshness boundaries, copied/replayed capabilities, lost response,
and exact fake dispatch ordering/counters. Include two connections used serially
in one thread; no parallel writers or helper subprocesses.

At most **three pytest iterations**, each exactly these nine modules:

```text
tests/unit/test_workspace_create_contract.py
tests/unit/test_workspace_create_intents.py
tests/unit/test_workspace_create_recovery.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
tests/unit/test_external_operations.py
tests/unit/test_workspace_create_journal_contract.py
tests/unit/test_workspace_create_linkage.py
tests/integration/test_workspace_create_linkage.py
```

Use direct Python `-B -m pytest -q -p no:cacheprovider --basetemp <new-root>/pytest-N`
followed by those paths. The existing seven unit modules stay unchanged; the
existing WCP-2 database/helper integration tests must not run under this grant.

At most three invocations each of Ruff lint, formatter, format-check and strict
mypy. Ruff must use `--no-cache` every time and target exactly the five new Python
files above. Mypy uses the existing package configuration and `<new-root>/mypy`.
No full suite, coverage, build, install, diagnostic child or hosted CI.

Each check: 300 seconds, 1 MiB combined output/evidence, 4 KiB per metadata frame,
64 KiB supervision metadata within that total. One application plus at most one
attributable exact OS console host: **two OS processes maximum**. No ordinary
application descendants, helper processes or host descendants. Keep the qualified
WCP-2C identity, output/error-retention, pre/post hash, owned-leaf-before-root
shutdown and closed-stream/root-size accounting rules. Record the known root
start as at least one application even if later sampling sees zero.

Two optional synthetic inline supervisor checks, no child/database, at most
30 seconds/4 KiB each, may validate adaptation to the new root, exact argv,
no-helper policy and error/accounting paths before a real check. Use new root-local
`supervisor-selfcheck-1.json` and `supervisor-selfcheck-2.json`. An ordinary
assertion failure permits a correction within these two slots; no limit increase.
Any real identity, process, termination or resource violation stops further
checks. Ordinary inspected code/test failures may use remaining slots only.

Exact existing runtime subjects (revalidate before use; never replace/install):

| Subject | Raw SHA-256 |
| --- | --- |
| `C:/Users/brian/AppData/Local/Programs/Python/Python310/python.exe` | `3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260` |
| `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/python.exe` (binding only; do not launch) | `b2c836c52cdf063180b9ee76f67ac42946101b79ac457f3494035a67c090d961` |
| `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/pyvenv.cfg` | `efe9c8f26884c6ac39ebb57a9f1215a539a423feaf12fe5eec753e28dcef3a55` |
| `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/ruff.exe` | `0cf602e931f311581bce0b1dfc8d5e30717d96af54c65d7b89a9a8d4497b0eeb` |
| `C:/Windows/System32/conhost.exe` (OS-created only; never directly invoke) | `b02ee54fb2ec69673386d41119ee8ed083a6eab3bfca6aa2155d20ce68ef8963` |

Launch shell-free, hidden, with cleared environment. Inherit only SYSTEMROOT/WINDIR.
Set TEMP/TMP to the new root, PYTHONDONTWRITEBYTECODE=1,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONHASHSEED=0, PYTHONUTF8=1,
PYTHONIOENCODING=utf-8 and PYTHONNOUSERSITE=1. Direct Python alone gets literal
`__PYVENV_LAUNCHER__=C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/python.exe`.
No PATH fallback, credentials, ambient dumps, console sharing or new launcher.

## Completion and next boundary

Record actual tests, failures, limits, raw final source/evidence hashes, residual
artifacts and all deferred integration gaps. Update the four coordination records.
Review incremental scope and status; preserve unrelated changes and the empty index.
Prepare the next exact proposal without a separate request to continue.

Even a passing rehearsal does not install its schema/guards into the controller
or prove native Git/workspace execution. Real controller installation and approval
persistence, native executor/identity/containment, runtime eligibility, publication/
exact hosted CI, successor-packet review and each live effect remain separate gates.

No commit/staging, push/CI/publication, existing database/migration, product
inspection, native Git/workspace, worker/verifier, listener/network, runtime upgrade
or manual cleanup. Original decisions 1-5 remain bound only to plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle `a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
`workspace.create/v1` remains unapproved.

## Suggested approval

> I approve CRSE-WCP-3 revision 2026-08-28.1, bound to its separately supplied
> raw-file SHA-256: the eleven-file fixture-only controller linkage rehearsal,
> exact baseline/grants/runtime policy, new isolated fixture root and bounded
> verification. I do not approve production installation, existing database
> access, commits, publication/CI, native or product effects, or cleanup.

## Inert supervisor handoff reference

The appendix preserves the inline supervisor used for the WCP-2C pytest runs.
It is **reference only, not a standalone executable or permission to rerun WCP-2**.
After WCP-3 approval, adapt it inline to this proposal's new root/grants/budgets;
remove the old helper allowance and closure channel, preserve identity/error
retention and accounting, and qualify that adaptation synthetically. Do not run
the historical body unchanged. The WCP-2 result records above remain immutable.

```powershell

function Get-CRelation {
 param([int]$ParentId,[long]$ParentStartMs,[string]$ParentRole,[hashtable]$Candidate,[bool]$AllowHelper,[hashtable]$Owner)
 if ($Candidate.ParentId -ne $ParentId -or $Candidate.ProcessId -le 0 -or $Candidate.ProcessId -eq $ParentId -or $null -eq $Candidate.StartMs) { return 'ambiguous' }
 if ([long]$Candidate.StartMs -lt ($ParentStartMs - 1)) { return 'stale' }
 if ([long]$Candidate.StartMs -le ($ParentStartMs + 1)) { return 'ambiguous' }
 if ($ParentRole -eq 'host') { return 'unexpected' }
 if ($Candidate.NativeImage -eq $cConhost) {
  if (-not $Candidate.NativeVerified -or -not $Candidate.HashVerified) { return 'ambiguous' }
  return 'host'
 }
 if (-not $AllowHelper) { return 'unexpected' }
 if ($null -eq $Owner -or $Owner.ProcessId -ne $Candidate.ProcessId -or $Owner.ParentId -ne $ParentId -or -not $Owner.NativeVerified -or -not $Owner.ClosedCase) { return 'unexpected' }
 if ($null -eq $Owner.StartMs -or [Math]::Abs([long]$Owner.StartMs - [long]$Candidate.StartMs) -gt 1) { return 'ambiguous' }
 if ($Candidate.NativeImage -ne $cPython -or -not $Candidate.NativeVerified) { return 'ambiguous' }
 return 'helper'
}
function Get-CShapeFailure {
 param([string[]]$Relations,[bool]$AllowHelper,[string]$ParentRole='application')
 if (@($Relations | Where-Object { $_ -notin @('stale','host','helper') }).Count -gt 0) { return 'unexpected_or_ambiguous_descendant' }
 $cHostCount=@($Relations | Where-Object { $_ -eq 'host' }).Count
 $cHelperCount=@($Relations | Where-Object { $_ -eq 'helper' }).Count
 if ($cHostCount -gt 1 -or $cHelperCount -gt 1 -or (-not $AllowHelper -and $cHelperCount -gt 0) -or ($ParentRole -eq 'host' -and ($cHostCount + $cHelperCount) -gt 0)) { return 'descendant_count' }
 return $null
}
function Join-CFailures {
 param([AllowNull()][string]$Primary,[AllowNull()][string]$Cleanup)
 return [ordered]@{primary=$Primary;cleanup=$Cleanup}
}
function Get-CAccountedLength {
 param([long]$DirectoryLength,[AllowNull()][object]$OwnedStream)
 if ($null -ne $OwnedStream) { return [Math]::Max($DirectoryLength,[long]$OwnedStream.Length) }
 return $DirectoryLength
}
function New-CClosureFrame {
 param([hashtable]$Application,[object[]]$Hosts,[bool]$ChildrenInspected,[bool]$PostHashVerified)
 if (-not $Application.Exited -or -not $Application.NativeVerified -or -not $ChildrenInspected -or -not $PostHashVerified -or $Application.ProcessId -le 0 -or $null -eq $Application.StartMs -or $Application.Case -notin $cCases -or $Hosts.Count -gt 1) { throw 'closure_not_proven' }
 $cClosedHosts=@()
 foreach ($cHostRecord in $Hosts) {
  if (-not $cHostRecord.Exited -or -not $cHostRecord.NativeVerified -or $cHostRecord.ParentId -ne $Application.ProcessId -or $cHostRecord.ParentStartMs -ne $Application.StartMs -or $cHostRecord.NativeImage -ne $cConhost -or $cHostRecord.ProcessId -le 0 -or $cHostRecord.StartMs -le ($Application.StartMs + 1)) { throw 'host_closure_not_proven' }
  $cClosedHosts += [ordered]@{pid=$cHostRecord.ProcessId;parent_pid=$cHostRecord.ParentId;parent_start_ms=$cHostRecord.ParentStartMs;start_ms=$cHostRecord.StartMs;native_image=$cHostRecord.NativeImage;native_image_verified=$true;termination_confirmed=$true;hash_before=$cConhostHash;hash_after=$cConhostHash}
 }
 return [ordered]@{case=$Application.Case;pid=$Application.ProcessId;parent_pid=$Application.ParentId;start_ms=$Application.StartMs;native_image_verified=$true;termination_confirmed=$true;children_inspected=$true;hosts=@($cClosedHosts);confirmed_at_ms=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()}
}
function Test-CClosureBinding {
 param([object]$Frame,[hashtable]$Application)
 if ($Frame.case -ne $Application.Case -or $Frame.pid -ne $Application.ProcessId -or $Frame.parent_pid -ne $Application.ParentId -or $Frame.start_ms -ne $Application.StartMs -or -not $Frame.native_image_verified -or -not $Frame.termination_confirmed -or -not $Frame.children_inspected -or @($Frame.hosts).Count -gt 1) { return $false }
 foreach ($cClosedHost in $Frame.hosts) {
  if ($cClosedHost.parent_pid -ne $Application.ProcessId -or $cClosedHost.parent_start_ms -ne $Application.StartMs -or $cClosedHost.start_ms -le ($Application.StartMs + 1) -or $cClosedHost.native_image -ne $cConhost -or -not $cClosedHost.native_image_verified -or -not $cClosedHost.termination_confirmed -or $cClosedHost.hash_before -ne $cConhostHash -or $cClosedHost.hash_after -ne $cConhostHash) { return $false }
 }
 return $true
}
$ErrorActionPreference = 'Stop'
$cRoot = 'C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp2-tests-20260827-01'
$cRepo = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator'
$cPython = 'C:\Users\brian\AppData\Local\Programs\Python\Python310\python.exe'
$cBinding = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\python.exe'
$cRuff = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\ruff.exe'
$cConhost = 'C:\Windows\System32\conhost.exe'
$cConhostHash = 'b02ee54fb2ec69673386d41119ee8ed083a6eab3bfca6aa2155d20ce68ef8963'
$cOpenStreams = @{}
$cCases = @('before_initial_commit','after_intent_commit','after_consume_commit','after_fake_call','before_terminal_commit','after_terminal_commit')
if ($cCheckName -notmatch '^(ruff-lint-[34]|ruff-(format|formatcheck)-[123]|mypy-[123]|pytest-[123])$') { throw 'Unapproved check name.' }
$cPytest = $cCheckName.StartsWith('pytest-')
$cExecutable = if ($cCheckName.StartsWith('ruff-')) { $cRuff } else { $cPython }
foreach ($cSubject in @(
 @($cPython,'3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'),
 @($cBinding,'b2c836c52cdf063180b9ee76f67ac42946101b79ac457f3494035a67c090d961'),
 @((Join-Path $cRepo '.venv\pyvenv.cfg'),'efe9c8f26884c6ac39ebb57a9f1215a539a423feaf12fe5eec753e28dcef3a55'),
 @($cRuff,'0cf602e931f311581bce0b1dfc8d5e30717d96af54c65d7b89a9a8d4497b0eeb'),
 @($cConhost,$cConhostHash)
)) {
 $cFile = Get-Item -LiteralPath $cSubject[0]
 if ($cFile.Attributes -band [IO.FileAttributes]::ReparsePoint -or (Get-FileHash -LiteralPath $cSubject[0] -Algorithm SHA256).Hash.ToLowerInvariant() -ne $cSubject[1]) { throw 'Runtime identity changed.' }
}
function Read-CMetadata {
 param([string]$Path)
 $cItem = Get-Item -LiteralPath $Path
 if ($cItem.PSIsContainer -or $cItem.Length -gt 4096 -or ($cItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'metadata_file_invalid' }
 return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
}
function Test-CBudget {
 $cStack = [Collections.Generic.Stack[string]]::new()
 $cStack.Push($cRoot)
 $cBytes = [long]0
 $cDatabases = @{}
 while ($cStack.Count -gt 0) {
  $cDirectory = $cStack.Pop()
  if ((Get-Item -LiteralPath $cDirectory).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'redirected_artifact_directory' }
  foreach ($cItem in @(Get-ChildItem -LiteralPath $cDirectory -Force)) {
   if ($cItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'redirected_artifact' }
   if ($cItem.PSIsContainer) { $cStack.Push($cItem.FullName); continue }
   $cBytes += Get-CAccountedLength -DirectoryLength $cItem.Length -OwnedStream $cOpenStreams[$cItem.FullName]
   if ($cItem.Extension -eq '.sqlite3') {
    $cIteration = $cItem.FullName.Substring($cRoot.Length + 1).Split('\')[0]
    $cDatabases[$cIteration] = 1 + $cDatabases[$cIteration]
    if ($cItem.Length -gt 4194304 -or $cDatabases[$cIteration] -gt 64) { throw 'database_budget' }
   }
   if ($cItem.Name -like '*.metrics.json') {
    $cMetric = Read-CMetadata -Path $cItem.FullName
    if ($null -ne $cMetric.limit_failure -or -not $cMetric.termination_confirmed) { throw 'prior_helper_stop' }
   }
  }
 }
 if ($cBytes -ge 268435456) { throw 'root_budget' }
 return $cBytes
}
[void](Test-CBudget)
$cSelfcheck = Read-CMetadata -Path (Join-Path $cRoot 'supervisor-selfcheck-3.json')
if (-not $cSelfcheck.passed -or $cSelfcheck.amendment_sha256 -ne 'ade615be2236e84ce4e8fcbda8280e9b84ad9f38fb54771a0be32dc707c4f505') { throw 'selfcheck_not_passed' }
if ((Get-FileHash -LiteralPath 'C:\Users\brian\Documents\CM_Computation\CRSE_WCP2_CONSOLE_HOST_AMENDMENT.md').Hash.ToLowerInvariant() -ne $cSelfcheck.amendment_sha256) { throw 'amendment_drift' }
$cPriorStop=Join-Path $cRoot 'ruff-lint-2.result.json'
if ((Get-FileHash -LiteralPath $cPriorStop).Hash.ToLowerInvariant() -ne 'c96a5abfb2d19ac428a535119635322a3f2c833d0b5daac8fe1b8cafc85d81e8') { throw 'historical_stop_drift' }
if ($cCheckName -ne 'ruff-lint-3') {
 $cGate = Read-CMetadata -Path (Join-Path $cRoot 'ruff-lint-3.result.json')
 if (-not $cGate.eligible -or -not $cGate.host_termination_confirmed) { throw 'requalification_not_eligible' }
}
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cRoot -File -Filter '*.result.json')) {
 if ($cPriorFile.Name -eq 'ruff-lint-2.result.json') { continue }
 $cPrior = Read-CMetadata -Path $cPriorFile.FullName
 if ($cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw 'prior_check_stop' }
}
$cTargets=@(
 'src/fractilate_orchestrator/persistence/workspace_create_journal.py',
 'src/fractilate_orchestrator/services/durable_workspace_create.py',
 'tests/unit/test_workspace_create_journal_contract.py',
 'tests/integration/test_workspace_create_journal.py',
 'tests/integration/test_durable_workspace_create.py',
 'tests/fixtures/workspace_create_journal/crash_probe.py'
)
$cExpectedArgs = if ($cCheckName -like 'ruff-lint-*') { @('check','--no-cache') + $cTargets }
 elseif ($cCheckName -like 'ruff-formatcheck-*') { @('format','--check','--no-cache') + $cTargets }
 elseif ($cCheckName -like 'ruff-format-*') { @('format','--no-cache') + $cTargets }
 elseif ($cPytest) { @('-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp',(Join-Path $cRoot $cCheckName)) + @('tests/unit/test_workspace_create_contract.py','tests/unit/test_workspace_create_intents.py','tests/unit/test_workspace_create_recovery.py','tests/unit/test_workspaces.py','tests/unit/test_product_pilot.py','tests/unit/test_external_operations.py','tests/unit/test_workspace_create_journal_contract.py','tests/integration/test_workspace_create_journal.py','tests/integration/test_durable_workspace_create.py') }
 else { @('-B','-m','mypy','--cache-dir',(Join-Path $cRoot 'mypy')) }
if (($cExpectedArgs | ConvertTo-Json -Compress) -cne ($cCheckArgs | ConvertTo-Json -Compress)) { throw 'argv_not_approved' }
$cPaths = @{}
foreach ($cSuffix in @('stdout.log','stderr.log','events.jsonl','runtime.json','result.json')) {
 $cPaths[$cSuffix] = Join-Path $cRoot ($cCheckName + '.' + $cSuffix)
 if (Test-Path -LiteralPath $cPaths[$cSuffix]) { throw 'evidence_path_exists' }
}
if ($cPytest -and (Test-Path -LiteralPath (Join-Path $cRoot $cCheckName))) { throw 'basetemp_exists' }
$cState = @{MetaBytes=0L;OutputBytes=0L;Seen=@{};HelperHandles=@{};Hosts=@{};Applications=@{};PeakLiveHelpers=0;PeakLiveHosts=0;PeakProcesses=0;StaleRelationships=0}
$cEvents = $null
function Write-CFrame {
 param([object]$Frame,[string]$Path='')
 $cJson = $Frame | ConvertTo-Json -Depth 6 -Compress
 $cBytes = [Text.Encoding]::UTF8.GetBytes($cJson + [char]10)
 if ($cBytes.Length -gt 4096 -or $cState.MetaBytes + $cBytes.Length -gt 61440 -or $cState.MetaBytes + $cState.OutputBytes + $cBytes.Length -gt 1044480) { throw 'supervision_metadata_budget' }
 if ($Path) {
  $cDestination = [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try { $cDestination.Write($cBytes,0,$cBytes.Length); $cDestination.Flush() } finally { $cDestination.Dispose() }
 } else { $cEvents.Write($cBytes,0,$cBytes.Length); $cEvents.Flush() }
 $cState.MetaBytes += $cBytes.Length
}
function Save-CCandidate {
 param([object]$Frame)
 $cKey = $Frame | ConvertTo-Json -Depth 4 -Compress
 if (-not $cState.Seen.ContainsKey($cKey)) {
  Write-CFrame -Frame $Frame
  $cState.Seen[$cKey] = $true
  if ($Frame.relation -eq 'stale') { $cState.StaleRelationships++ }
 }
}

function Get-CScopedProcesses {
 param([string]$Filter)
 $cMatches=@(Get-CimInstance -ClassName Win32_Process -Filter $Filter -Property ProcessId,ParentProcessId,CreationDate,ExecutablePath | Select-Object -First 17)
 if ($cMatches.Count -gt 16) { throw 'candidate_metadata_count' }
 return $cMatches
}
function Get-CStartMs {
 param([object]$Info)
 if ($null -eq $Info.CreationDate) { return $null }
 return ([DateTimeOffset]$Info.CreationDate.ToUniversalTime()).ToUnixTimeMilliseconds()
}
function Confirm-CGone {
 param([int]$ProcessId,[long]$StartMs)
 $cMatches=@(Get-CScopedProcesses -Filter ("ProcessId=" + $ProcessId))
 if ($cMatches.Count -eq 0) { return $true }
 if ($cMatches.Count -ne 1) { throw 'ambiguous_pid' }
 $cCurrentStart=Get-CStartMs -Info $cMatches[0]
 if ($null -eq $cCurrentStart) { throw 'missing_creation_identity' }
 if ([Math]::Abs($cCurrentStart - $StartMs) -le 1) { return $false }
 if ($cCurrentStart -gt ($StartMs + 1)) { return $true }
 throw 'ambiguous_pid_reuse'
}
function Inspect-CHostChildren {
 param([hashtable]$HostRecord)
 foreach ($cInfo in @(Get-CScopedProcesses -Filter ("ParentProcessId=" + $HostRecord.ProcessId))) {
  $cCandidate=@{ProcessId=[int]$cInfo.ProcessId;ParentId=[int]$cInfo.ParentProcessId;StartMs=(Get-CStartMs -Info $cInfo)}
  $cRelation=Get-CRelation -ParentId $HostRecord.ProcessId -ParentStartMs $HostRecord.StartMs -ParentRole 'host' -Candidate $cCandidate -AllowHelper $false -Owner $null
  Save-CCandidate -Frame ([ordered]@{type='host_child';parent_pid=$HostRecord.ProcessId;parent_start_ms=$HostRecord.StartMs;pid=$cCandidate.ProcessId;start_ms=$cCandidate.StartMs;native_image=$cInfo.ExecutablePath;relation=$cRelation})
  if ($cRelation -ne 'stale') { throw 'console_host_descendant' }
 }
}
function Update-CHost {
 param([hashtable]$HostRecord)
 if ($null -ne $HostRecord.Handle) { $HostRecord.Exited=$HostRecord.Handle.HasExited }
 else { $HostRecord.Exited=Confirm-CGone -ProcessId $HostRecord.ProcessId -StartMs $HostRecord.StartMs }
 Inspect-CHostChildren -HostRecord $HostRecord
 Save-CCandidate -Frame ([ordered]@{type='host_state';parent_pid=$HostRecord.ParentId;parent_start_ms=$HostRecord.ParentStartMs;pid=$HostRecord.ProcessId;start_ms=$HostRecord.StartMs;native_image=$HostRecord.NativeImage;native_image_verified=$HostRecord.NativeVerified;owned_handle_verified=$HostRecord.HandleVerified;exited=$HostRecord.Exited;exit_code=$(if ($HostRecord.Exited -and $null -ne $HostRecord.Handle) { $HostRecord.Handle.ExitCode } else { $null })})
}
function Inspect-CApplication {
 param([int]$ParentId,[long]$ParentStartMs,[bool]$AllowHelper)
 $cRelations=[Collections.Generic.List[string]]::new()
 foreach ($cInfo in @(Get-CScopedProcesses -Filter ("ParentProcessId=" + $ParentId))) {
  $cStart=Get-CStartMs -Info $cInfo
  $cCandidate=@{ProcessId=[int]$cInfo.ProcessId;ParentId=[int]$cInfo.ParentProcessId;StartMs=$cStart;Exited=$false;NativeVerified=($cInfo.ExecutablePath -eq $cConhost);HashVerified=$true;NativeImage=$cInfo.ExecutablePath}
  $cOwner=$null
  if ($AllowHelper -and $cCandidate.NativeImage -eq $cPython) {
   $cOwner=Find-COwner -ProcessId $cCandidate.ProcessId
   if ($null -ne $cOwner) { $cCandidate.NativeVerified=$cOwner.NativeVerified }
  }
  $cRelation=Get-CRelation -ParentId $ParentId -ParentStartMs $ParentStartMs -ParentRole 'application' -Candidate $cCandidate -AllowHelper $AllowHelper -Owner $cOwner
  Save-CCandidate -Frame ([ordered]@{type='child';parent_pid=$ParentId;parent_start_ms=$ParentStartMs;pid=$cCandidate.ProcessId;start_ms=$cStart;native_image=$cCandidate.NativeImage;native_verified=$cCandidate.NativeVerified;relation=$cRelation})
  if ($cRelation -eq 'host') {
   $cKey=[string]$cCandidate.ProcessId + ':' + [string]$cStart
   if (-not $cState.Hosts.ContainsKey($cKey)) {
    $cRecord=@{ProcessId=$cCandidate.ProcessId;StartMs=$cStart;ParentId=$ParentId;ParentStartMs=$ParentStartMs;NativeImage=$cConhost;NativeVerified=$true;HandleVerified=$false;Handle=$null;Exited=$false}
    $cChild=$null
    try {
     try { $cChild=[Diagnostics.Process]::GetProcessById($cCandidate.ProcessId) }
     catch [ArgumentException] { if (-not (Confirm-CGone -ProcessId $cCandidate.ProcessId -StartMs $cStart)) { throw 'host_identity_race' }; $cRecord.Exited=$true }
     if ($null -ne $cChild) {
      [void]$cChild.Handle
      if ($cChild.HasExited) {
       if (-not (Confirm-CGone -ProcessId $cCandidate.ProcessId -StartMs $cStart)) { throw 'host_exit_race' }
       $cRecord.Exited=$true
      } else {
       $cNativeStart=([DateTimeOffset]$cChild.StartTime.ToUniversalTime()).ToUnixTimeMilliseconds()
       $cImage=$cChild.MainModule.FileName
       if ($cImage -ne $cConhost -or [Math]::Abs($cNativeStart - $cStart) -gt 1) { throw 'host_native_identity' }
       $cRecord.Handle=$cChild
       $cRecord.HandleVerified=$true
       $cChild=$null
      }
     }
     $cState.Hosts[$cKey]=$cRecord
    } finally { if ($null -ne $cChild) { $cChild.Dispose() } }
   } elseif ($cState.Hosts[$cKey].ParentId -ne $ParentId -or $cState.Hosts[$cKey].ParentStartMs -ne $ParentStartMs) { throw 'shared_host' }
  }
  if ($cRelation -ne 'helper' -or -not $cOwner.Exited) { $cRelations.Add($cRelation) }
 }
 $cShapeFailure=Get-CShapeFailure -Relations $cRelations.ToArray() -AllowHelper $AllowHelper
 if ($cShapeFailure) { throw $cShapeFailure }
 $cParentHosts=@($cState.Hosts.Values | Where-Object { $_.ParentId -eq $ParentId -and $_.ParentStartMs -eq $ParentStartMs })
 if ($cParentHosts.Count -gt 1) { throw 'additional_console_host' }
 foreach ($cRecord in $cParentHosts) { Update-CHost -HostRecord $cRecord }
}

function Read-CHelperFrame {
 param([string]$Path)
 $cReadClock=[Diagnostics.Stopwatch]::StartNew()
 while ($true) {
  try { $cFrame=Read-CMetadata -Path $Path; if ($null -ne $cFrame) { return $cFrame } }
  catch { if ($cReadClock.ElapsedMilliseconds -ge 250) { throw } }
  if ($cReadClock.ElapsedMilliseconds -ge 250) { throw 'helper_metadata_incomplete' }
  [Threading.Thread]::Sleep(10)
 }
}
function Refresh-CHelper {
 param([hashtable]$Application)
 if ($null -ne $Application.Handle) { $Application.Exited=$Application.Handle.HasExited }
 elseif (-not $Application.Exited) {
  $cProbe=$null
  try {
   try { $cProbe=[Diagnostics.Process]::GetProcessById($Application.ProcessId) }
   catch [ArgumentException] { $Application.Exited=Confirm-CGone $Application.ProcessId $Application.StartMs }
   if ($null -ne $cProbe) {
    [void]$cProbe.Handle
    if ($cProbe.HasExited) { $Application.Exited=Confirm-CGone $Application.ProcessId $Application.StartMs }
    else {
     $cBorn=([DateTimeOffset]$cProbe.StartTime.ToUniversalTime()).ToUnixTimeMilliseconds()
     $cImage=$cProbe.MainModule.FileName
     if ($cImage -ne $cPython -or [Math]::Abs($cBorn - $Application.StartMs) -gt 1) { throw 'helper_native_identity' }
     $Application.Handle=$cProbe; $cState.HelperHandles[$Application.Key]=$cProbe; $cProbe=$null
    }
   }
  } catch [InvalidOperationException] {
   if (-not (Confirm-CGone $Application.ProcessId $Application.StartMs)) { throw }
   $Application.Exited=$true
  } finally { if ($null -ne $cProbe) { $cProbe.Dispose() } }
 }
 if (Test-Path -LiteralPath $Application.MetricsPath) {
  $cMetric=Read-CHelperFrame $Application.MetricsPath
  if ($cMetric.case -ne $Application.Case -or $cMetric.pid -ne $Application.ProcessId -or $cMetric.parent_pid -ne $Application.ParentId -or $cMetric.start_ms -ne $Application.StartMs -or $cMetric.native_image_verified -ne $true -or $cMetric.termination_confirmed -ne $true -or $null -eq $cMetric.exited_at_ms -or $cMetric.exited_at_ms -lt $Application.StartMs -or $cMetric.exited_at_ms -gt ($Application.StartMs + 15000) -or $cMetric.seconds -gt 15 -or ($cMetric.stdout_bytes + $cMetric.stderr_bytes) -gt 65536 -or $null -ne $cMetric.limit_failure) { throw 'helper_metrics_invalid_or_limit' }
  if (-not $Application.Exited -and (Confirm-CGone $Application.ProcessId $Application.StartMs)) { $Application.Exited=$true }
  $Application.ExitBound=[long]$cMetric.exited_at_ms
  $Application.MetricConfirmed=$true
 }
 Save-CCandidate -Frame ([ordered]@{type='helper_state';case=$Application.Case;pid=$Application.ProcessId;parent_pid=$Application.ParentId;start_ms=$Application.StartMs;native_image=$cPython;native_image_verified=$Application.NativeVerified;owned_handle_verified=($null -ne $Application.Handle);exited=$Application.Exited;metrics_confirmed=$Application.MetricConfirmed})
}
function Refresh-COwners {
 if (-not $cPytest) { return }
 $cIteration=Join-Path $cRoot $cCheckName
 if (-not (Test-Path -LiteralPath $cIteration)) { return }
 $cOwnerFiles=@(Get-ChildItem -LiteralPath $cIteration -File -Recurse -Filter '*.owner.json')
 if ($cOwnerFiles.Count -gt 6) { throw 'helper_invocation_count' }
 foreach ($cFile in $cOwnerFiles) {
  $cCase=$cFile.Name.Substring(0,$cFile.Name.Length - '.owner.json'.Length)
  if ($cCase -notin $cCases) { throw 'unknown_helper_case' }
  $cDir=$cFile.Directory
  while ($null -ne $cDir -and $cDir.FullName.StartsWith($cRoot + '\',[StringComparison]::OrdinalIgnoreCase)) {
   if ($cDir.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'redirected_helper_directory' }
   $cDir=$cDir.Parent
  }
  $cOwner=Read-CHelperFrame $cFile.FullName
  if ($cOwner.pid -le 0 -or $cOwner.parent_pid -ne $cProcessId -or $null -eq $cOwner.start_ms -or $cOwner.start_ms -le ($cStartMs + 1) -or $cOwner.native_image_verified -ne $true) { throw 'helper_owner_binding' }
  $cKey=[string]$cOwner.pid + ':' + [string]$cOwner.start_ms
  if (-not $cState.Applications.ContainsKey($cKey)) {
   foreach ($cPrior in @($cState.Applications.Values)) {
    if ($cPrior.Case -eq $cCase -or -not $cPrior.ClosureConfirmed) { throw 'helper_overlap_or_repeated_case' }
   }
   $cState.Applications[$cKey]=@{Key=$cKey;ProcessId=[int]$cOwner.pid;ParentId=$cProcessId;StartMs=[long]$cOwner.start_ms;NativeVerified=$true;ClosedCase=$true;Case=$cCase;Handle=$null;Exited=$false;MetricConfirmed=$false;ExitBound=$null;ClosureConfirmed=$false;OwnerPath=$cFile.FullName;MetricsPath=(Join-Path $cFile.DirectoryName ($cCase + '.metrics.json'));ClosurePath=(Join-Path $cFile.DirectoryName ($cCase + '.host-closed.json'))}
  } elseif ($cState.Applications[$cKey].OwnerPath -ne $cFile.FullName) { throw 'duplicate_helper_ownership' }
  Refresh-CHelper -Application $cState.Applications[$cKey]
 }
}
function Find-COwner {
 param([int]$ProcessId)
 $cFindClock=[Diagnostics.Stopwatch]::StartNew()
 while ($true) {
  Refresh-COwners
  $cFound=@($cState.Applications.Values | Where-Object { $_.ProcessId -eq $ProcessId -and -not $_.ClosureConfirmed })
  if ($cFound.Count -eq 1) { return $cFound[0] }
  if ($cFound.Count -gt 1) { throw 'ambiguous_helper_owner' }
  if ($cFindClock.ElapsedMilliseconds -ge 250) { return $null }
  [Threading.Thread]::Sleep(10)
 }
}
function Complete-CHelperClosures {
 foreach ($cApplication in @($cState.Applications.Values)) {
  if ($cApplication.ClosureConfirmed) { continue }
  $cHosts=@($cState.Hosts.Values | Where-Object { $_.ParentId -eq $cApplication.ProcessId -and $_.ParentStartMs -eq $cApplication.StartMs })
  if (-not $cApplication.Exited -or -not $cApplication.MetricConfirmed -or @($cHosts | Where-Object { -not $_.Exited }).Count -gt 0) {
   if ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() - $cApplication.StartMs -ge 15000) { throw 'helper_host_closure_wall_time' }
   continue
  }
  if (@($cHosts | Where-Object { $_.StartMs -gt $cApplication.ExitBound }).Count -gt 0) { throw 'host_outside_application_lifetime' }
  if ((Get-FileHash -LiteralPath $cConhost -Algorithm SHA256).Hash.ToLowerInvariant() -ne $cConhostHash) { throw 'helper_host_post_hash' }
  $cClosure=New-CClosureFrame -Application $cApplication -Hosts $cHosts -ChildrenInspected $true -PostHashVerified $true
  if ($cClosure.confirmed_at_ms -gt ($cApplication.StartMs + 15000)) { throw 'helper_host_closure_wall_time' }
  Write-CFrame -Path $cApplication.ClosurePath -Frame $cClosure
  $cApplication.ClosureConfirmed=$true
  Save-CCandidate -Frame ([ordered]@{type='helper_host_closed';case=$cApplication.Case;pid=$cApplication.ProcessId;start_ms=$cApplication.StartMs;host_count=$cHosts.Count;elapsed_ms=($cClosure.confirmed_at_ms - $cApplication.StartMs)})
 }
}

function Inspect-CChildren {
 param([int]$ParentId,[long]$ParentStartMs,[bool]$AllowHelper)
 Refresh-COwners
 Inspect-CApplication -ParentId $ParentId -ParentStartMs $ParentStartMs -AllowHelper $AllowHelper
 foreach ($cApplication in @($cState.Applications.Values)) {
  Refresh-CHelper -Application $cApplication
  Inspect-CApplication -ParentId $cApplication.ProcessId -ParentStartMs $cApplication.StartMs -AllowHelper $false
 }
 Complete-CHelperClosures
 $cLiveHelpers=@($cState.Applications.Values | Where-Object { -not $_.Exited }).Count
 $cLiveHosts=@($cState.Hosts.Values | Where-Object { -not $_.Exited }).Count
 $cLiveApps=[int](-not $cProcess.HasExited) + $cLiveHelpers
 $cState.PeakLiveHelpers=[Math]::Max($cState.PeakLiveHelpers,$cLiveHelpers)
 $cState.PeakLiveHosts=[Math]::Max($cState.PeakLiveHosts,$cLiveHosts)
 $cState.PeakProcesses=[Math]::Max($cState.PeakProcesses,($cLiveHosts + $cLiveApps))
 $cCeiling=if ($cPytest) { 4 } else { 2 }
 Save-CCandidate -Frame ([ordered]@{type='process_counts';live_applications=$cLiveApps;live_hosts=$cLiveHosts;total=($cLiveApps + $cLiveHosts);ceiling=$cCeiling})
 if (($cLiveHosts + $cLiveApps) -gt $cCeiling -or $cLiveHelpers -gt 1 -or ($cLiveHelpers -gt 0 -and -not $cPytest)) { throw 'process_ceiling' }
}

function Read-CPipes {
 foreach ($cChannel in $cChannels) {
  if ($cChannel.Done -or $null -eq $cChannel.Pending -or -not $cChannel.Pending.IsCompleted) { continue }
  $cCount = $cChannel.Pending.GetAwaiter().GetResult()
  $cRemaining = 1044480 - $cState.MetaBytes - $cState.OutputBytes
  if ($cCount -gt $cRemaining) { $cKeep = [int][Math]::Max(0,$cRemaining) } else { $cKeep = $cCount }
  if ($cKeep -gt 0) {
   $cChannel.Log.Write($cChannel.Buffer,0,$cKeep)
   $cChannel.Log.Flush()
   $cChannel.Capture.Write($cChannel.Buffer,0,$cKeep)
   $cState.OutputBytes += $cKeep
  }
  if ($cCount -gt $cRemaining) { throw 'combined_output_budget' }
  if ($cCount -eq 0) { $cChannel.Done=$true; $cChannel.Pending=$null }
  else { $cChannel.Pending = $cChannel.Stream.ReadAsync($cChannel.Buffer,0,$cChannel.Buffer.Length) }
 }
}
$cProcess = [Diagnostics.Process]::new()
$cStartInfo = [Diagnostics.ProcessStartInfo]::new()
$cStartInfo.FileName=$cExecutable
$cStartInfo.WorkingDirectory=$cRepo
$cStartInfo.UseShellExecute=$false
$cStartInfo.CreateNoWindow=$true
$cStartInfo.RedirectStandardInput=$true
$cStartInfo.RedirectStandardOutput=$true
$cStartInfo.RedirectStandardError=$true
$cStartInfo.Environment.Clear()
foreach ($cName in @('SYSTEMROOT','WINDIR')) {
 $cValue = [Environment]::GetEnvironmentVariable($cName)
 if ($null -ne $cValue) { $cStartInfo.Environment[$cName]=$cValue }
}
foreach ($cPair in @(@('TEMP',$cRoot),@('TMP',$cRoot),@('PYTHONDONTWRITEBYTECODE','1'),@('PYTEST_DISABLE_PLUGIN_AUTOLOAD','1'),@('PYTHONHASHSEED','0'),@('PYTHONUTF8','1'),@('PYTHONIOENCODING','utf-8'),@('PYTHONNOUSERSITE','1'))) { $cStartInfo.Environment[$cPair[0]]=$cPair[1] }
if ($cExecutable -eq $cPython) { $cStartInfo.Environment['__PYVENV_LAUNCHER__']=$cBinding }
foreach ($cArgument in $cCheckArgs) { $cStartInfo.ArgumentList.Add($cArgument) }
$cProcess.StartInfo=$cStartInfo
$cClock=[Diagnostics.Stopwatch]::StartNew()
$cStarted=$false
$cNativeVerified=$false
$cProcessId=$null
$cStartMs=$null
$cPrimary=$null
$cCleanup=$null
$cExitCode=$null
$cTerminated=$false
$cHostsTerminated=$false
$cChannels=@()
try {
 $cEvents=[IO.File]::Open($cPaths['events.jsonl'],[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 $cOpenStreams[$cPaths['events.jsonl']]=$cEvents
 foreach ($cSuffix in @('stdout.log','stderr.log')) {
  $cChannels += @{Log=[IO.File]::Open($cPaths[$cSuffix],[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);Capture=[IO.MemoryStream]::new();Buffer=[byte[]]::new(8192);Pending=$null;Done=$false;Stream=$null}
 }
 $cOpenStreams[$cPaths['stdout.log']]=$cChannels[0].Log
 $cOpenStreams[$cPaths['stderr.log']]=$cChannels[1].Log
 [void]$cProcess.Start()
 $cStarted=$true
 $cProcessId=$cProcess.Id
 $cProcess.StandardInput.Close()
 $cChannels[0].Stream=$cProcess.StandardOutput.BaseStream
 $cChannels[1].Stream=$cProcess.StandardError.BaseStream
 foreach ($cChannel in $cChannels) { $cChannel.Pending=$cChannel.Stream.ReadAsync($cChannel.Buffer,0,$cChannel.Buffer.Length) }
 $cNativeImage=$cProcess.MainModule.FileName
 $cStartMs=([DateTimeOffset]$cProcess.StartTime.ToUniversalTime()).ToUnixTimeMilliseconds()
 $cNativeVerified=$cNativeImage -eq $cExecutable
 Write-CFrame -Path $cPaths['runtime.json'] -Frame ([ordered]@{check=$cCheckName;pid=$cProcessId;parent_pid=$PID;start_ms=$cStartMs;native_image_verified=$cNativeVerified})
 Write-CFrame -Frame ([ordered]@{type='root_start';pid=$cProcessId;start_ms=$cStartMs;native_image=$cNativeImage;verified=$cNativeVerified})
 if (-not $cNativeVerified) { throw 'root_native_identity' }
 $cNextInspection=0
 while ($true) {
  if ($cClock.ElapsedMilliseconds -ge 300000) { throw 'wall_time' }
  Read-CPipes
  if ($cClock.ElapsedMilliseconds -ge $cNextInspection) {
   Inspect-CChildren -ParentId $cProcessId -ParentStartMs $cStartMs -AllowHelper $cPytest
   $cNextInspection=$cClock.ElapsedMilliseconds + 500
  }
  if ($cProcess.HasExited -and @($cChannels | Where-Object { -not $_.Done }).Count -eq 0) { break }
  [Threading.Thread]::Sleep(10)
 }
} catch { $cPrimary=$_.Exception.Message }
finally {
 if ($cStarted) {
  try {
   if ($cNativeVerified) { Inspect-CChildren -ParentId $cProcessId -ParentStartMs $cStartMs -AllowHelper $cPytest }
  } catch { $cCleanup=$_.Exception.Message }
  try {
   $cHostWait=[Diagnostics.Stopwatch]::StartNew()
   if (-not $cPrimary -and $cProcess.HasExited) {
    while (@($cState.Hosts.Values | Where-Object { -not $_.Exited }).Count -gt 0 -and $cHostWait.ElapsedMilliseconds -lt 5000) {
     foreach ($cHostRecord in @($cState.Hosts.Values)) { Update-CHost -HostRecord $cHostRecord }
     Read-CPipes
     if (@($cState.Hosts.Values | Where-Object { -not $_.Exited }).Count -gt 0) { [Threading.Thread]::Sleep(10) }
    }
   }
   foreach ($cHostRecord in @($cState.Hosts.Values)) {
    if (-not $cHostRecord.Exited) {
     if (-not $cPrimary) { $cPrimary='console_host_lingering' }
     if (-not $cHostRecord.HandleVerified -or $null -eq $cHostRecord.Handle) { throw 'unverified_host_not_terminated' }
     $cHostRecord.Handle.Kill()
     if (-not $cHostRecord.Handle.WaitForExit(5000)) { throw 'host_termination_unconfirmed' }
     $cHostRecord.Exited=$true
    }
   }
   foreach ($cHelper in @($cState.HelperHandles.Values)) {
    if (-not $cHelper.HasExited) {
     if (-not $cPrimary) { $cPrimary='unexpected_live_owned_helper' }
     $cHelper.Kill()
     if (-not $cHelper.WaitForExit(5000)) { throw 'helper_termination_unconfirmed' }
    }
   }
   if (-not $cProcess.HasExited) {
    if (-not $cNativeVerified) { throw 'unverified_root_not_terminated' }
    if (-not $cPrimary) { $cPrimary='root_incomplete' }
    $cProcess.Kill()
   }
   $cTerminated=$cProcess.WaitForExit(5000)
   if (-not $cTerminated) { throw 'root_termination_unconfirmed' }
   $cExitCode=$cProcess.ExitCode
   Inspect-CChildren -ParentId $cProcessId -ParentStartMs $cStartMs -AllowHelper $cPytest
   $cHostsTerminated=@($cState.Hosts.Values | Where-Object { -not $_.Exited }).Count -eq 0
   if (-not $cHostsTerminated) { throw 'host_termination_unconfirmed' }
   if (@($cState.Applications.Values | Where-Object { -not $_.ClosureConfirmed }).Count -gt 0) { throw 'helper_closure_unconfirmed' }
  } catch { if ($cCleanup) { $cCleanup += '|' + $_.Exception.Message } else { $cCleanup=$_.Exception.Message } }
  try {
   $cDrain=[Diagnostics.Stopwatch]::StartNew()
   while (@($cChannels | Where-Object { -not $_.Done -and $null -ne $_.Stream }).Count -gt 0 -and $cDrain.ElapsedMilliseconds -lt 5000) {
    Read-CPipes
    if (@($cChannels | Where-Object { -not $_.Done }).Count -gt 0) { [Threading.Thread]::Sleep(10) }
   }
   if (@($cChannels | Where-Object { -not $_.Done -and $null -ne $_.Stream }).Count -gt 0) { throw 'pipe_eof_unconfirmed' }
  } catch { if ($cCleanup) { $cCleanup += '|' + $_.Exception.Message } else { $cCleanup=$_.Exception.Message } }
 }
 try {
  if ((Get-FileHash -LiteralPath $cConhost -Algorithm SHA256).Hash.ToLowerInvariant() -ne $cConhostHash) { throw 'host_post_hash_changed' }
  Write-CFrame -Frame ([ordered]@{type='final';root_exited=$cTerminated;root_exit_code=$cExitCode;hosts_exited=$cHostsTerminated;console_hash_before=$cConhostHash;console_hash_after=$cConhostHash;host_identities=@($cState.Hosts.Values | ForEach-Object { [ordered]@{pid=$_.ProcessId;parent_pid=$_.ParentId;parent_start_ms=$_.ParentStartMs;start_ms=$_.StartMs;exited=$_.Exited} })})
 } catch { if ($cCleanup) { $cCleanup += '|' + $_.Exception.Message } else { $cCleanup=$_.Exception.Message } }
 foreach ($cChannel in $cChannels) { $cChannel.Log.Dispose() }
 if ($null -ne $cEvents) { $cEvents.Dispose() }
 $cOpenStreams.Clear()
 $cClock.Stop()
 try { $cRootBytes=Test-CBudget } catch { if ($cCleanup) { $cCleanup += '|' + $_.Exception.Message } else { $cCleanup=$_.Exception.Message }; $cRootBytes=$null }
 $cFailures=Join-CFailures -Primary $cPrimary -Cleanup $cCleanup
 $cEligible=$cStarted -and $cNativeVerified -and $cTerminated -and $cHostsTerminated -and -not $cFailures.primary -and -not $cFailures.cleanup -and $cExitCode -in @(0,1)
 $cSummary=[ordered]@{check=$cCheckName;pid=$cProcessId;start_ms=$cStartMs;native_image_verified=$cNativeVerified;exit_code=$cExitCode;primary_failure=$cFailures.primary;cleanup_failure=$cFailures.cleanup;root_termination_confirmed=$cTerminated;host_termination_confirmed=$cHostsTerminated;eligible=$cEligible;elapsed_seconds=[Math]::Round($cClock.Elapsed.TotalSeconds,3);captured_bytes=$cState.OutputBytes;prior_metadata_bytes=$cState.MetaBytes;peak_live_helpers_observed=$cState.PeakLiveHelpers;peak_live_hosts_observed=$cState.PeakLiveHosts;peak_os_processes_observed=$cState.PeakProcesses;stale_relationships=$cState.StaleRelationships;root_bytes_before_summary=$cRootBytes;root_bytes_after_summary=0L}
 try {
  $cSummaryText=$cSummary | ConvertTo-Json -Depth 4 -Compress
  $cSummaryBytes=[Text.Encoding]::UTF8.GetBytes($cSummaryText + [char]10)
  for ($cPass=0; $cPass -lt 4; $cPass++) {
   $cSummary.root_bytes_after_summary=$cRootBytes + $cSummaryBytes.Length
   $cSummaryText=$cSummary | ConvertTo-Json -Depth 4 -Compress
   $cSummaryBytes=[Text.Encoding]::UTF8.GetBytes($cSummaryText + [char]10)
  }
  if ($null -eq $cRootBytes -or $cSummary.root_bytes_after_summary -ne ($cRootBytes + $cSummaryBytes.Length) -or $cSummary.root_bytes_after_summary -ge 268435456) { throw 'final_root_budget' }
  if ($cSummaryBytes.Length -gt 4096 -or $cState.MetaBytes + $cSummaryBytes.Length -gt 65536 -or $cState.MetaBytes + $cState.OutputBytes + $cSummaryBytes.Length -gt 1048576) { throw 'final_metadata_budget' }
  $cFinal=[IO.File]::Open($cPaths['result.json'],[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try { $cFinal.Write($cSummaryBytes,0,$cSummaryBytes.Length) } finally { $cFinal.Dispose() }
  if ((Test-CBudget) -ne $cSummary.root_bytes_after_summary) { throw 'final_root_accounting_mismatch' }
  $cSummaryText
 } finally {
  foreach ($cChannel in $cChannels) {
   $cLines=[Text.Encoding]::UTF8.GetString($cChannel.Capture.ToArray()) -split "\r?\n"
   if ($cLines.Count -gt 90) { $cLines=@($cLines | Select-Object -First 20) + @($cLines | Select-Object -Last 60) }
   foreach ($cLine in $cLines) { if ($cLine.Length -gt 500) { $cLine.Substring(0,500) + ' [display truncated; retained log complete]' } else { $cLine } }
   if ($null -ne $cChannel.Stream) { $cChannel.Stream.Dispose() }
   $cChannel.Log.Dispose()
   $cChannel.Capture.Dispose()
  }
  if ($null -ne $cEvents) { $cEvents.Dispose() }
  foreach ($cHelper in @($cState.HelperHandles.Values)) { $cHelper.Dispose() }
  foreach ($cHostRecord in @($cState.Hosts.Values)) { if ($null -ne $cHostRecord.Handle) { $cHostRecord.Handle.Dispose() } }
  $cProcess.Dispose()
 }
}
if ($cPrimary -or $cCleanup -or -not $cTerminated -or -not $cHostsTerminated -or $cExitCode -notin @(0,1)) { exit 124 }
exit $cExitCode
```
