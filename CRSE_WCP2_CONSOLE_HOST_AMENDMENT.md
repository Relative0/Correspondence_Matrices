# CRSE-WCP-2C: bounded Windows console-host accounting and verification

Revision: **2026-08-28.1**. Status: **proposed; further verification not approved**.

## Requested decision

Approve one exact Windows console-host runtime subject, bounded accounting for
that OS overhead, two bounded synthetic supervisor checks, and resumption of the
remaining fixture-only verification. Increase the cumulative Ruff lint ceiling
from three to **four** invocations: iteration 3 requalifies the runtime, and
iteration 4 verifies corrected source. Do not reset either failed invocation.

This changes maintenance-process accounting, not controller concurrency or the
product worker policy. There is still one check at a time and one named crash
helper at a time. No additional worker, arbitrary child, interpreter, installer,
terminal session, or native product effect is authorized.

This is a new decision after WCP-2S's mandatory stop. Prior approval of WCP-2S,
the owner's commit request, or knowledge that `conhost.exe` is a Windows component
does not authorize this exception automatically.

## Evidence and completed commits

- Review documents: CM_Computation commit
  `6ce1f3fbc49df93e11ea53e7d1c24de3ac4885d7`.
- Unverified controller draft checkpoint:
  `b9dd7724a205ef08b5655839ca6db7dd97b5774e`, parent
  `c6107fa889053a34711412be23f2d8d065eb125c`.
- Exactly 12 controller files, 1,970 additions and 17 deletions relative to that
  parent. No old Python module/test changed. The no-fix recheck changed none of
  the six new Python files. Only `coordination/NEXT_ACTIONS.md` was Git-normalized
  from CRLF to LF; its staged content was independently compared.
- Both requested commits were local; no push or hosted CI ran.

The WCP-2V Python preflight passed. Both WCP-2S synthetic self-checks passed.
Ruff lint iteration 2 then recorded native Ruff PID 31068, start Unix milliseconds
1787854187949, and direct child PID 25448, start 1787854187965, image
`C:/Windows/system32/conhost.exe`. The child was created 16 ms after Ruff, not
before it. The supervisor did not admit it as an authorized helper.

Ruff was stopped through its identity-verified owned process handle. Root exit
-1 and termination were confirmed, elapsed 0.466 seconds. Retained output is
7,892 stdout bytes and zero stderr bytes, plus 512 pre-result metadata bytes and
a 427-byte final result. The output contains partial lint diagnostics, not a
completed lint result. A later scoped query found neither PID nor direct-child
relationship present. Console identity came from Windows metadata; no independent
console-host exit code or earlier native-handle ownership was established.

Microsoft identifies `conhost.exe` as the console API host. The precise
allocation call path in this invocation was not proven. Hidden-window launch
settings are not evidence that no OS host exists. No flag change, new launcher,
console attachment, or suppression experiment has been attempted.
[Microsoft console definitions](https://learn.microsoft.com/en-us/windows/console/definitions),
[process creation flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags).

The first Ruff invocation's missing process/output evidence remains unresolved;
the second run does not retrospectively identify its child. No further check,
formatter, mypy, pytest, helper, SQLite connection, or schema setup has run.

## Preserved authority and exact continuation baseline

The unchanged, committed review documents remain the governing prior grants:

| Document in CM_Computation | Approved raw SHA-256 |
| --- | --- |
| `CRSE_DURABLE_WORKSPACE_JOURNAL_PROPOSAL.md` | `90b2a59a402344721d673bc19f4b70b4b4f372b789a0f7ea9e7ccb1d5ddf3089` |
| `CRSE_WCP2_VERIFICATION_RUNTIME_AMENDMENT.md` | `b837236b2810746593ac832a004baa307eaa6d9d22eec6bd779a028b1e6868b0` |
| `CRSE_WCP2_CHECK_SUPERVISION_AMENDMENT.md` | `a5cc85b2a6ae3632f4852593df2bed58d3c59a1f8427db0b81f4dcd1957560f6` |

Require controller HEAD `b9dd7724a205ef08b5655839ca6db7dd97b5774e`,
empty index, no tracked drift, and this raw working-file manifest. This new
checkpoint explicitly supersedes the former c6107fa HEAD precondition; it does
not reset the cumulative scope budget. Do not switch/reset/stage to make a match.

All twelve files now exist. Allow modification only of these existing targets;
no additional controller file, rename, or deletion is granted. Keep the cumulative
ceiling, relative to c6107fa, of **12 files, 3,000 additions, 150 deletions**.
Deletions from pre-WCP-2 content remain confined to the four coordination documents.
Formatting/corrections must not weaken tests or invariants to fit.

| Controller-relative file | Raw working-file SHA-256 |
| --- | --- |
| `docs/decisions/ADR-0023-fixture-workspace-create-journal.md` | `dde03ca3d6bcd165750ad7a5e49b46c199daac82f357cecbf11ca0240ea715d6` |
| `src/fractilate_orchestrator/persistence/workspace_create_journal.py` | `7618fb50590ef9684f4084a643336ec67481114ce7a8aaca050535e2d1581b2c` |
| `src/fractilate_orchestrator/services/durable_workspace_create.py` | `006e6fa30dc0537db474a3f412b44306cf62e497cf015af9fa85240e97930e21` |
| `tests/unit/test_workspace_create_journal_contract.py` | `1254807bf5e23afdca5a4ba667ef88f0e4887adb57d154570c8309b6fafd9470` |
| `tests/integration/test_workspace_create_journal.py` | `4796c15312da2e7763fb613a7dcd8e8252e9845af873822c449be8a31c977fc7` |
| `tests/integration/test_durable_workspace_create.py` | `92f27ce0481a84914bcb95835d42339cdc84bfdc1b18fb6fca9ce1cd94952ac9` |
| `tests/fixtures/workspace_create_journal/crash_probe.py` | `b38e9f1eea31d361accf64249a10421043abae9127bb1ad0c0dea2929fd7a83a` |
| `coordination/WORKSPACE_CREATE_PERSISTENCE_READINESS.md` | `b7ff87ec337463e294352e7dee6f8843191369a5d59ddfe519d96c050b26e712` |
| `coordination/WORKSPACE_CREATE_READINESS.md` | `1724a9198715c944e9ddb14fc3cd1452eb6417e6e6f1889d81257db4dc912967` |
| `coordination/PROGRAM_STATUS.md` | `2ffdaf9cc1e8945c05a364facd6a2500aba0b12d996535638efc1c3eba1cf86d` |
| `coordination/plans/ACTIVE_PLAN.md` | `9bf96bd588488aa41c895eb32c5653ef7ce19794ba18d09eb3a3bc894d6d72a8` |
| `coordination/NEXT_ACTIONS.md` | `aed4e8d546d57b5e65a408364996f845066ce17f9d7321262f45d434a7fc154e` |

Controller root:
`C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.

Preserve unrelated `coordination/prompts/` unread and unrelated CM work untouched.
The existing Git global-ignore permission warning is not permission to inspect
or repair user configuration or claim exhaustive ignored-state cleanliness.

Continue only in the same non-redirected owned root:
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp2-tests-20260827-01`.

It contains exactly these **11 files, 9,905 bytes**, measured after stream closure:

| Artifact | Bytes | Raw SHA-256 |
| --- | ---: | --- |
| `preflight-1.runtime.json` | 107 | `9465354bb2a437b8e17bf7be002ad9714824c3cd2ca71dbed74e32af0646d2bc` |
| `preflight-1.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `preflight-1.stdout.log` | 110 | `87901c91aca006c66ef7f6f95e2f929c6aa484802ce91cc25a0e38aafb819097` |
| `ruff-lint-1.runtime.json` | 107 | `a1d8cdd2dd2a86b565fc502b40431b6dda7b60febcec6db63c136dc41e2f431b` |
| `ruff-lint-2.events.jsonl` | 403 | `c44bede29717cb47849e437571cefd4c4b56d369cfd2a2b7d2bc5d06e0a9a45b` |
| `ruff-lint-2.result.json` | 427 | `c96a5abfb2d19ac428a535119635322a3f2c833d0b5daac8fe1b8cafc85d81e8` |
| `ruff-lint-2.runtime.json` | 109 | `dcc37b67780a08b16fe480882d256a20c3f5b5ae8da177e3a4bac9d4908e5851` |
| `ruff-lint-2.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `ruff-lint-2.stdout.log` | 7892 | `0aef167b98448a0da2ed65385f59e467006060bd1064ea66c2413c65c3b4702a` |
| `supervisor-selfcheck-1.json` | 582 | `43981f461b52cc95a3d233360be46f05145fe707bcf0746a1488d909abf15a22` |
| `supervisor-selfcheck-2.json` | 168 | `378c92832ece97b287d4c7f25390b60c262a8fb77480ba6d8b7e186e2877ee0f` |

Revalidate root/ancestors, names, sizes and hashes before continuing. Preserve
these bytes and all prior roots/cache artifacts. No database, basetemp or cache
exists here. Never delete/recreate the root, overwrite old logs, or manufacture
missing historical measurements.

## Exact new runtime subject and process ceilings

The sole added runtime subject is:

- `C:/Windows/System32/conhost.exe`
- Raw SHA-256:
  `b02ee54fb2ec69673386d41119ee8ed083a6eab3bfca6aa2155d20ce68ef8963`
- Observed regular, non-reparse file; 867,840 bytes; file version
  `10.0.19041.1 (WinBuild.160101.0800)`.

Permit read-only revalidation of this exact file and native process metadata.
Do not download, replace, repair, register, configure, directly invoke, or choose
arguments for it. Permission is only for an OS-created console host attributable
to an exact already-approved runtime invocation. File hashing does not certify
all DLLs, operating-system integrity, or adversarial containment.

Keep the four WCP-2V runtime subjects/hashes, direct Python/Ruff launches, hidden
window policy, explicit argv, cleared environment, literal venv bootstrap and
existing installed dependencies unchanged. No environment additions, PATH
fallback, console sharing/attachment, launcher replacement, install or upgrade.

The revised check-related **OS-process** ceilings are:

| Invocation | Application processes | Optional exact console hosts | Total ceiling |
| --- | ---: | ---: | ---: |
| Direct Ruff, strict mypy, or approved metadata preflight | 1 | 1 | 2 |
| Pytest with its one named crash helper | 2 | 2, at most one per application | 4 |

No ordinary application child of Ruff/mypy/preflight is allowed. Pytest's only
application child remains the exact direct-Python helper with a closed case and
retained fixture arguments. A console host may have **no descendants**. Old or
shared hosts, another host binary, extra hosts, shells, Git, SDK, workers and
verifiers remain disallowed. The maintenance supervisor itself is outside these
check-child counts, as before. Controller/worker concurrency remains one.

## Supervisor and helper requirements

1. Retain native application image/PID/start identity from owned handles. Bind
   every observed console host to the exact owned parent's PID/start lifetime,
   the native image path and pre/post executable hash. Reject stale parent-PID
   matches using creation evidence; ambiguous identity remains a stop condition.
   Native image/start evidence may come from the owned handle or scoped Windows
   metadata, but termination requires an identity-verified owned handle.
2. Inspect only the owned applications, their console hosts and direct-child
   relationships. Retain bounded PID/parent/start/image/exit/count metadata,
   never command lines, environment dumps, unrelated process lists or credentials.
   Do not classify an arbitrary executable as OS overhead based on its name.
3. Count all observed live hosts against the ceilings. Observe host descendants
   as well as application descendants. Retain initial/final/state-change evidence,
   and report observation limits honestly; sampling is not kernel containment.
4. Preserve WCP-2S's unconditional bounded output/error retention, including the
   original failure if cleanup also fails. The combined evidence ceiling remains
   1 MiB per ordinary check, 4 KiB per metadata frame and 64 KiB supervision
   metadata within that total. No silent truncation or extra output allowance.
5. Correct root accounting: directory metadata for still-open logs understated
   the previous result. Count owned open-stream lengths or close all such streams
   before the post-check metadata scan, then include the final result. Preserve
   the inaccurate historical field and its correction record, rather than editing
   the old result. The 256 MiB retained-root cap is unchanged.
6. Confirm a helper's exit and closure of its associated console host before
   advancing to another helper or reopening that fixture. The existing bounded
   file-metadata channel may gain one create-new `<case>.host-closed.json` frame
   per case, at most 4 KiB, in that case's already-owned temporary directory.
   Bind it to case, application PID/start, verified host identities and confirmed
   closure. No frame is permission to execute another command or reconstruct a
   capability. Keep the 15-second helper budget inclusive of this coordination.
7. Permit only identity-verified owned shutdown: known console-host leaves and
   the named helper before the root, with confirmed exits. Never kill by name/PID
   alone or kill an unidentified/stale/shared host. Use the existing bounded
   termination-confirmation allowance, not a new runtime budget. Any lingering,
   inaccessible or unknown descendant/termination stops further launches.
8. Keep all console/closure changes in the inline maintenance harness and the
   existing granted test/helper files. No persistent native launcher, controller
   service, new entry point, general subprocess facility or production integration.

## Bounded qualification and remaining checks

Authorize at most **two additional synthetic supervisor self-checks**, using
distinct `supervisor-selfcheck-3.json` and `supervisor-selfcheck-4.json` evidence.
Each uses only inline maintenance-shell logic, synthetic metadata and bounded
in-memory streams, with no subprocess/database and a 30-second/4-KiB cap.
Exercise exact-host acceptance, wrong path/hash, stale PID, missing/ambiguous
identity, extra hosts, a host descendant, helper-host closure ordering, PID-bound
closure frames, open-stream size accounting and initial/cleanup error retention.
An ordinary synthetic assertion failure allows one in-scope correction within
these two slots; a limit breach stops. No real check starts before they pass.

Then run **Ruff lint iteration 3**, direct exact Ruff, `check --no-cache`, no
`--fix`, on exactly the original six new Python paths listed in the manifest.
Use new `ruff-lint-3.*` evidence. Keep 300 seconds/1 MiB and the revised two-process
Ruff ceiling. Require complete bounded diagnostics, confirmed application/host
termination, exact identity and no unexpected descendant. Exit 0 or inspected
ordinary lint findings with exit 1 can qualify; an interrupted/incomplete run,
execution error or ambiguous process evidence cannot.

Only an eligible qualification permits completion of the original fixture slice:

- **Ruff lint iteration 4** is the one newly added lint slot, for final corrected
  source; no additional lint retry. Formatter and format-check retain their three
  unused slots each. Always target exactly the six new Python files and pass
  `--no-cache`, including formatting.
- Strict mypy retains three unused slots, the existing package configuration and
  cache under `<root>/mypy`.
- Pytest retains three unused iterations, each running exactly WCP-2's nine
  modules, plugin autoload/cache provider disabled, with a distinct verified-absent
  `pytest-1`, `pytest-2` or `pytest-3` basetemp. The six old modules are unchanged.
- At most six named helper invocations per pytest iteration, one at a time,
  15 seconds/64 KiB each, 4 KiB helper metadata. No ordinary grandchildren.
- Only newly created run fixtures: original schema/read/write/corruption/recovery
  grant, DELETE/FULL serial access, 4 MiB per database, 64 databases per iteration,
  256 MiB total retained artifacts. No existing database access.
- The one unused WCP-2V metadata preflight slot remains available only if needed,
  under its original probe/content/30-second/4-KiB limits and the console allowance.
- No full suite, coverage, build, runtime installation, arbitrary diagnostic
  command, or additional tests/check slots.

Any real process/identity/termination/resource violation stops all further
checks again. Do not use the final lint slot to investigate another runtime stop.
If the file/test budget is insufficient, report it rather than silently enlarging
it or dropping tests. Preserve both prior stopped runs without retrospective
reclassification.

## Completion and exclusions

After eligible bounded verification, update all four coordination records,
ADR/readiness evidence as appropriate, and review the cumulative delta and Git
status. Prepare the next exact integration/native-readiness proposal without
waiting for another continue request. Do not describe fixture tests as native
product readiness, power-loss proof, or distributed exactly-once execution.

The owner's requested commits were fulfilled by the two checkpoints above.
This proposal grants no further commit/staging, push, hosted CI, publication,
real/native workspace or Git effect, worker/verifier, listener/network effect,
existing/production database, migration integration, manual cleanup, or product
packet regeneration. Original product decisions 1-5 remain bound solely to
their earlier plan/bundle. `workspace.create/v1` remains separately unapproved.

## Suggested owner approval

> I approve CRSE-WCP-2C revision 2026-08-28.1, bound to its separately supplied
> raw-file SHA-256: the exact OS console-host exception, revised OS-process
> accounting, bounded synthetic qualification and helper-host closure evidence,
> correction of root-size accounting, and conditional verification resumption.
> Ruff lint has a cumulative ceiling of four; all other original budgets and
> all product-effect, further-commit, push, CI, database and cleanup exclusions
> remain as specified.

This document is a proposal, not an instruction to execute before exact approval.

## Historical supervisor reference (inert handoff)

The following is the WCP-2S inline supervisor used for the recorded stopped
recheck, retained so its already self-checked logic need not be reconstructed.
It deliberately rejects console hosts and retains the old stopped-gate checks;
**do not execute it unchanged**. It also contains the documented open-stream
size-accounting defect. Only after approving this proposal may it be revised
inline for the exact console-host policy and qualification above. This Markdown
reference is not a new executable file, controller module, or launch authority.

```powershell
function Get-CrseRelation {
 param([int]$ParentId,[long]$ParentStartMs,[hashtable]$Candidate,[bool]$AllowHelper,[hashtable]$Owner)
 if ($Candidate.ParentId -ne $ParentId -or $Candidate.ProcessId -le 0 -or $Candidate.ProcessId -eq $ParentId -or $null -eq $Candidate.StartMs) { return 'ambiguous' }
 if ([long]$Candidate.StartMs -lt ($ParentStartMs - 1)) { return 'stale' }
 if ([long]$Candidate.StartMs -le ($ParentStartMs + 1)) { return 'ambiguous' }
 if (-not $AllowHelper) { return 'unexpected' }
 if ($null -eq $Owner -or $Owner.ProcessId -ne $Candidate.ProcessId -or $Owner.ParentId -ne $ParentId -or -not $Owner.NativeVerified -or -not $Owner.ClosedCase) { return 'unexpected' }
 if ($null -eq $Owner.StartMs -or [Math]::Abs([long]$Owner.StartMs - [long]$Candidate.StartMs) -gt 1) { return 'ambiguous' }
 if (-not $Candidate.Exited -and -not $Candidate.NativeVerified) { return 'ambiguous' }
 return 'owned'
}
function Get-CrseShapeFailure {
 param([string[]]$Relations,[bool]$AllowHelper)
 if (@($Relations | Where-Object { $_ -notin @('stale','owned') }).Count -gt 0) { return 'unexpected_or_ambiguous_descendant' }
 $crseOwnedCount = @($Relations | Where-Object { $_ -eq 'owned' }).Count
 if ($crseOwnedCount -gt 1 -or (-not $AllowHelper -and $crseOwnedCount -gt 0)) { return 'descendant_count' }
 return $null
}
function Join-CrseFailures {
 param([AllowNull()][string]$Primary,[AllowNull()][string]$Cleanup)
 return [ordered]@{primary=$Primary;cleanup=$Cleanup}
}

$ErrorActionPreference = 'Stop'
$crseRoot = 'C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp2-tests-20260827-01'
$crseRepo = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator'
$crsePython = 'C:\Users\brian\AppData\Local\Programs\Python\Python310\python.exe'
$crseBinding = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\python.exe'
$crseRuff = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\ruff.exe'
$crseCases = @('before_initial_commit','after_intent_commit','after_consume_commit','after_fake_call','before_terminal_commit','after_terminal_commit')
if ($crseCheckName -notmatch '^(ruff-lint-[23]|ruff-(format|formatcheck)-[123]|mypy-[123]|pytest-[123])$') { throw 'Unapproved check name.' }
$crsePytest = $crseCheckName.StartsWith('pytest-')
$crseExecutable = if ($crseCheckName.StartsWith('ruff-')) { $crseRuff } else { $crsePython }
foreach ($crseSubject in @(
 @($crsePython,'3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'),
 @($crseBinding,'b2c836c52cdf063180b9ee76f67ac42946101b79ac457f3494035a67c090d961'),
 @((Join-Path $crseRepo '.venv\pyvenv.cfg'),'efe9c8f26884c6ac39ebb57a9f1215a539a423feaf12fe5eec753e28dcef3a55'),
 @($crseRuff,'0cf602e931f311581bce0b1dfc8d5e30717d96af54c65d7b89a9a8d4497b0eeb')
)) {
 $crseFile = Get-Item -LiteralPath $crseSubject[0]
 if ($crseFile.Attributes -band [IO.FileAttributes]::ReparsePoint -or (Get-FileHash -LiteralPath $crseSubject[0] -Algorithm SHA256).Hash.ToLowerInvariant() -ne $crseSubject[1]) { throw 'Runtime identity changed.' }
}
function Read-CrseMetadata {
 param([string]$Path)
 $crseItem = Get-Item -LiteralPath $Path
 if ($crseItem.PSIsContainer -or $crseItem.Length -gt 4096 -or ($crseItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'metadata_file_invalid' }
 return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
}
function Test-CrseBudget {
 $crseStack = [Collections.Generic.Stack[string]]::new()
 $crseStack.Push($crseRoot)
 $crseBytes = [long]0
 $crseDatabases = @{}
 while ($crseStack.Count -gt 0) {
  $crseDirectory = $crseStack.Pop()
  if ((Get-Item -LiteralPath $crseDirectory).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'redirected_artifact_directory' }
  foreach ($crseItem in @(Get-ChildItem -LiteralPath $crseDirectory -Force)) {
   if ($crseItem.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'redirected_artifact' }
   if ($crseItem.PSIsContainer) { $crseStack.Push($crseItem.FullName); continue }
   $crseBytes += $crseItem.Length
   if ($crseItem.Extension -eq '.sqlite3') {
    $crseIteration = $crseItem.FullName.Substring($crseRoot.Length + 1).Split('\')[0]
    $crseDatabases[$crseIteration] = 1 + $crseDatabases[$crseIteration]
    if ($crseItem.Length -gt 4194304 -or $crseDatabases[$crseIteration] -gt 64) { throw 'database_budget' }
   }
   if ($crseItem.Name -like '*.metrics.json') {
    $crseMetric = Read-CrseMetadata -Path $crseItem.FullName
    if ($null -ne $crseMetric.limit_failure -or -not $crseMetric.termination_confirmed) { throw 'prior_helper_stop' }
   }
  }
 }
 if ($crseBytes -ge 268435456) { throw 'root_budget' }
 return $crseBytes
}
[void](Test-CrseBudget)
$crseSelfcheck = Read-CrseMetadata -Path (Join-Path $crseRoot 'supervisor-selfcheck-1.json')
if (-not $crseSelfcheck.passed) { throw 'selfcheck_not_passed' }
if ($crseCheckName -ne 'ruff-lint-2') {
 $crseGate = Read-CrseMetadata -Path (Join-Path $crseRoot 'ruff-lint-2.result.json')
 if (-not $crseGate.eligible) { throw 'recheck_gate_not_eligible' }
}
foreach ($crsePriorFile in @(Get-ChildItem -LiteralPath $crseRoot -File -Filter '*.result.json')) {
 $crsePrior = Read-CrseMetadata -Path $crsePriorFile.FullName
 if ($crsePrior.primary_failure -or $crsePrior.cleanup_failure -or -not $crsePrior.root_termination_confirmed -or $crsePrior.exit_code -in @(3,124)) { throw 'prior_check_stop' }
}
$crsePaths = @{}
foreach ($crseSuffix in @('stdout.log','stderr.log','events.jsonl','runtime.json','result.json')) {
 $crsePaths[$crseSuffix] = Join-Path $crseRoot ($crseCheckName + '.' + $crseSuffix)
 if (Test-Path -LiteralPath $crsePaths[$crseSuffix]) { throw 'evidence_path_exists' }
}
if ($crsePytest -and (Test-Path -LiteralPath (Join-Path $crseRoot $crseCheckName))) { throw 'basetemp_exists' }
$crseState = @{MetaBytes=0L;OutputBytes=0L;Seen=@{};HelperHandles=@{};PeakLiveHelpers=0;StaleRelationships=0}
$crseEvents = $null
function Write-CrseFrame {
 param([object]$Frame,[string]$Path='')
 $crseJson = $Frame | ConvertTo-Json -Depth 6 -Compress
 $crseBytes = [Text.Encoding]::UTF8.GetBytes($crseJson + [char]10)
 if ($crseBytes.Length -gt 4096 -or $crseState.MetaBytes + $crseBytes.Length -gt 61440 -or $crseState.MetaBytes + $crseState.OutputBytes + $crseBytes.Length -gt 1044480) { throw 'supervision_metadata_budget' }
 if ($Path) {
  $crseDestination = [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try { $crseDestination.Write($crseBytes,0,$crseBytes.Length); $crseDestination.Flush() } finally { $crseDestination.Dispose() }
 } else { $crseEvents.Write($crseBytes,0,$crseBytes.Length); $crseEvents.Flush() }
 $crseState.MetaBytes += $crseBytes.Length
}
function Save-CrseCandidate {
 param([object]$Frame)
 $crseKey = $Frame | ConvertTo-Json -Depth 4 -Compress
 if (-not $crseState.Seen.ContainsKey($crseKey)) {
  Write-CrseFrame -Frame $Frame
  $crseState.Seen[$crseKey] = $true
  if ($Frame.relation -eq 'stale') { $crseState.StaleRelationships++ }
 }
}
function Get-CrseOwner {
 param([int]$ProcessId,[int]$ParentId)
 $crseOwners = @()
 $crseIterationPath = Join-Path $crseRoot $crseCheckName
 if (-not $crsePytest -or -not (Test-Path -LiteralPath $crseIterationPath)) { return $null }
 $crseOwnerFiles = @(Get-ChildItem -LiteralPath $crseIterationPath -File -Recurse -Filter '*.owner.json')
 if ($crseOwnerFiles.Count -gt 6) { throw 'helper_invocation_count' }
 foreach ($crseOwnerFile in $crseOwnerFiles) {
  $crseOwner = Read-CrseMetadata -Path $crseOwnerFile.FullName
  if ($crseOwner.pid -eq $ProcessId -and $crseOwner.parent_pid -eq $ParentId) {
   $crseCase = $crseOwnerFile.Name.Substring(0,$crseOwnerFile.Name.Length - '.owner.json'.Length)
   $crseOwners += @{ProcessId=[int]$crseOwner.pid;ParentId=[int]$crseOwner.parent_pid;StartMs=$crseOwner.start_ms;NativeVerified=($crseOwner.native_image_verified -eq $true);ClosedCase=($crseCase -in $crseCases)}
  }
 }
 if ($crseOwners.Count -gt 1) { throw 'duplicate_helper_ownership' }
 if ($crseOwners.Count -eq 1) { return $crseOwners[0] }
 return $null
}
function Inspect-CrseChildren {
 param([int]$ParentId,[long]$ParentStartMs,[bool]$AllowHelper)
 $crseCandidates = @(Get-CimInstance -ClassName Win32_Process -Filter ("ParentProcessId=" + $ParentId) -Property ProcessId,ParentProcessId,CreationDate,ExecutablePath | Select-Object -First 17)
 $crseRelations = [Collections.Generic.List[string]]::new()
 $crseLiveHelpers = 0
 foreach ($crseInfo in $crseCandidates) {
  $crseStart = if ($null -ne $crseInfo.CreationDate) { ([DateTimeOffset]$crseInfo.CreationDate.ToUniversalTime()).ToUnixTimeMilliseconds() } else { $null }
  $crseCandidate = @{ProcessId=[int]$crseInfo.ProcessId;ParentId=[int]$crseInfo.ParentProcessId;StartMs=$crseStart;Exited=$false;NativeVerified=$false}
  $crseOwner = $null
  $crseChild = $null
  $crseNativeImage = $crseInfo.ExecutablePath
  $crseRelation = Get-CrseRelation -ParentId $ParentId -ParentStartMs $ParentStartMs -Candidate $crseCandidate -AllowHelper $false -Owner $null
  try {
   if ($crseRelation -ne 'stale' -and $AllowHelper) {
    $crseOwner = Get-CrseOwner -ProcessId $crseCandidate.ProcessId -ParentId $ParentId
    try { $crseChild = [Diagnostics.Process]::GetProcessById($crseCandidate.ProcessId) }
    catch [ArgumentException] { $crseCandidate.Exited = $true }
    if ($null -ne $crseChild) {
     $crseCandidate.Exited = $crseChild.HasExited
     if (-not $crseCandidate.Exited) {
      $crseNativeStart = ([DateTimeOffset]$crseChild.StartTime.ToUniversalTime()).ToUnixTimeMilliseconds()
      $crseNativeImage = $crseChild.MainModule.FileName
      $crseCandidate.NativeVerified = $crseNativeImage -eq $crsePython -and $null -ne $crseStart -and [Math]::Abs($crseNativeStart - [long]$crseStart) -le 1
     }
    }
    $crseRelation = Get-CrseRelation -ParentId $ParentId -ParentStartMs $ParentStartMs -Candidate $crseCandidate -AllowHelper $true -Owner $crseOwner
   }
   Save-CrseCandidate -Frame ([ordered]@{type='child';parent_pid=$ParentId;parent_start_ms=$ParentStartMs;pid=$crseCandidate.ProcessId;start_ms=$crseStart;native_image=$crseNativeImage;exited=$crseCandidate.Exited;native_verified=$crseCandidate.NativeVerified;relation=$crseRelation})
   if ($crseRelation -eq 'owned') {
    if (-not $crseCandidate.Exited) {
     $crseLiveHelpers++
     $crseKey = [string]$crseCandidate.ProcessId + ':' + [string]$crseOwner.StartMs
     if (-not $crseState.HelperHandles.ContainsKey($crseKey)) { $crseState.HelperHandles[$crseKey] = $crseChild; $crseChild = $null }
     $crseRelations.Add('owned')
    }
    Inspect-CrseChildren -ParentId $crseCandidate.ProcessId -ParentStartMs ([long]$crseOwner.StartMs) -AllowHelper $false
   } else { $crseRelations.Add($crseRelation) }
  } catch {
   Save-CrseCandidate -Frame ([ordered]@{type='child_inspection_error';parent_pid=$ParentId;pid=$crseCandidate.ProcessId;start_ms=$crseStart;relation='ambiguous'})
   throw
  } finally { if ($null -ne $crseChild) { $crseChild.Dispose() } }
 }
 if ($crseCandidates.Count -gt 16) { throw 'candidate_metadata_count' }
 $crseState.PeakLiveHelpers = [Math]::Max($crseState.PeakLiveHelpers,$crseLiveHelpers)
 $crseShapeFailure = Get-CrseShapeFailure -Relations $crseRelations.ToArray() -AllowHelper $AllowHelper
 if ($null -ne $crseShapeFailure) { throw $crseShapeFailure }
}
function Read-CrsePipes {
 foreach ($crseChannel in $crseChannels) {
  if ($crseChannel.Done -or $null -eq $crseChannel.Pending -or -not $crseChannel.Pending.IsCompleted) { continue }
  $crseCount = $crseChannel.Pending.GetAwaiter().GetResult()
  $crseRemaining = 1044480 - $crseState.MetaBytes - $crseState.OutputBytes
  if ($crseCount -gt $crseRemaining) { $crseKeep = [int][Math]::Max(0,$crseRemaining) } else { $crseKeep = $crseCount }
  if ($crseKeep -gt 0) {
   $crseChannel.Log.Write($crseChannel.Buffer,0,$crseKeep)
   $crseChannel.Log.Flush()
   $crseChannel.Capture.Write($crseChannel.Buffer,0,$crseKeep)
   $crseState.OutputBytes += $crseKeep
  }
  if ($crseCount -gt $crseRemaining) { throw 'combined_output_budget' }
  if ($crseCount -eq 0) { $crseChannel.Done=$true; $crseChannel.Pending=$null }
  else { $crseChannel.Pending = $crseChannel.Stream.ReadAsync($crseChannel.Buffer,0,$crseChannel.Buffer.Length) }
 }
}
$crseProcess = [Diagnostics.Process]::new()
$crseStartInfo = [Diagnostics.ProcessStartInfo]::new()
$crseStartInfo.FileName=$crseExecutable
$crseStartInfo.WorkingDirectory=$crseRepo
$crseStartInfo.UseShellExecute=$false
$crseStartInfo.CreateNoWindow=$true
$crseStartInfo.RedirectStandardInput=$true
$crseStartInfo.RedirectStandardOutput=$true
$crseStartInfo.RedirectStandardError=$true
$crseStartInfo.Environment.Clear()
foreach ($crseName in @('SYSTEMROOT','WINDIR')) {
 $crseValue = [Environment]::GetEnvironmentVariable($crseName)
 if ($null -ne $crseValue) { $crseStartInfo.Environment[$crseName]=$crseValue }
}
foreach ($crsePair in @(@('TEMP',$crseRoot),@('TMP',$crseRoot),@('PYTHONDONTWRITEBYTECODE','1'),@('PYTEST_DISABLE_PLUGIN_AUTOLOAD','1'),@('PYTHONHASHSEED','0'),@('PYTHONUTF8','1'),@('PYTHONIOENCODING','utf-8'),@('PYTHONNOUSERSITE','1'))) { $crseStartInfo.Environment[$crsePair[0]]=$crsePair[1] }
if ($crseExecutable -eq $crsePython) { $crseStartInfo.Environment['__PYVENV_LAUNCHER__']=$crseBinding }
foreach ($crseArgument in $crseCheckArgs) { $crseStartInfo.ArgumentList.Add($crseArgument) }
$crseProcess.StartInfo=$crseStartInfo
$crseClock=[Diagnostics.Stopwatch]::StartNew()
$crseStarted=$false
$crseNativeVerified=$false
$crseProcessId=$null
$crseStartMs=$null
$crsePrimary=$null
$crseCleanup=$null
$crseExitCode=$null
$crseTerminated=$false
$crseChannels=@()
try {
 $crseEvents=[IO.File]::Open($crsePaths['events.jsonl'],[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 foreach ($crseSuffix in @('stdout.log','stderr.log')) {
  $crseChannels += @{Log=[IO.File]::Open($crsePaths[$crseSuffix],[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);Capture=[IO.MemoryStream]::new();Buffer=[byte[]]::new(8192);Pending=$null;Done=$false;Stream=$null}
 }
 [void]$crseProcess.Start()
 $crseStarted=$true
 $crseProcessId=$crseProcess.Id
 $crseProcess.StandardInput.Close()
 $crseChannels[0].Stream=$crseProcess.StandardOutput.BaseStream
 $crseChannels[1].Stream=$crseProcess.StandardError.BaseStream
 foreach ($crseChannel in $crseChannels) { $crseChannel.Pending=$crseChannel.Stream.ReadAsync($crseChannel.Buffer,0,$crseChannel.Buffer.Length) }
 $crseNativeImage=$crseProcess.MainModule.FileName
 $crseStartMs=([DateTimeOffset]$crseProcess.StartTime.ToUniversalTime()).ToUnixTimeMilliseconds()
 $crseNativeVerified=$crseNativeImage -eq $crseExecutable
 Write-CrseFrame -Path $crsePaths['runtime.json'] -Frame ([ordered]@{check=$crseCheckName;pid=$crseProcessId;parent_pid=$PID;start_ms=$crseStartMs;native_image_verified=$crseNativeVerified})
 Write-CrseFrame -Frame ([ordered]@{type='root_start';pid=$crseProcessId;start_ms=$crseStartMs;native_image=$crseNativeImage;verified=$crseNativeVerified})
 if (-not $crseNativeVerified) { throw 'root_native_identity' }
 $crseNextInspection=0
 while ($true) {
  if ($crseClock.ElapsedMilliseconds -ge 300000) { throw 'wall_time' }
  Read-CrsePipes
  if ($crseClock.ElapsedMilliseconds -ge $crseNextInspection) {
   Inspect-CrseChildren -ParentId $crseProcessId -ParentStartMs $crseStartMs -AllowHelper $crsePytest
   $crseNextInspection=$crseClock.ElapsedMilliseconds + 500
  }
  if ($crseProcess.HasExited -and @($crseChannels | Where-Object { -not $_.Done }).Count -eq 0) { break }
  [Threading.Thread]::Sleep(10)
 }
} catch { $crsePrimary=$_.Exception.Message }
finally {
 if ($crseStarted) {
  try {
   if ($crseNativeVerified) { Inspect-CrseChildren -ParentId $crseProcessId -ParentStartMs $crseStartMs -AllowHelper $crsePytest }
  } catch { $crseCleanup=$_.Exception.Message }
  try {
   foreach ($crseHelper in @($crseState.HelperHandles.Values)) {
    if (-not $crseHelper.HasExited) {
     if (-not $crsePrimary) { $crsePrimary='unexpected_live_owned_helper' }
     $crseHelper.Kill()
     if (-not $crseHelper.WaitForExit(5000)) { throw 'helper_termination_unconfirmed' }
    }
   }
   if (-not $crseProcess.HasExited) {
    if (-not $crseNativeVerified) { throw 'unverified_root_not_terminated' }
    if (-not $crsePrimary) { $crsePrimary='root_incomplete' }
    $crseProcess.Kill()
   }
   $crseTerminated=$crseProcess.WaitForExit(5000)
   if (-not $crseTerminated) { throw 'root_termination_unconfirmed' }
   $crseExitCode=$crseProcess.ExitCode
  } catch { if ($crseCleanup) { $crseCleanup += '|' + $_.Exception.Message } else { $crseCleanup=$_.Exception.Message } }
  try {
   $crseDrain=[Diagnostics.Stopwatch]::StartNew()
   while (@($crseChannels | Where-Object { -not $_.Done -and $null -ne $_.Stream }).Count -gt 0 -and $crseDrain.ElapsedMilliseconds -lt 5000) {
    Read-CrsePipes
    if (@($crseChannels | Where-Object { -not $_.Done }).Count -gt 0) { [Threading.Thread]::Sleep(10) }
   }
   if (@($crseChannels | Where-Object { -not $_.Done -and $null -ne $_.Stream }).Count -gt 0) { throw 'pipe_eof_unconfirmed' }
  } catch { if ($crseCleanup) { $crseCleanup += '|' + $_.Exception.Message } else { $crseCleanup=$_.Exception.Message } }
 }
 $crseClock.Stop()
 try { $crseRootBytes=Test-CrseBudget } catch { if ($crseCleanup) { $crseCleanup += '|' + $_.Exception.Message } else { $crseCleanup=$_.Exception.Message }; $crseRootBytes=$null }
 $crseFailures=Join-CrseFailures -Primary $crsePrimary -Cleanup $crseCleanup
 $crseEligible=$crseStarted -and $crseNativeVerified -and $crseTerminated -and -not $crseFailures.primary -and -not $crseFailures.cleanup -and $crseExitCode -in @(0,1)
 $crseSummary=[ordered]@{check=$crseCheckName;pid=$crseProcessId;start_ms=$crseStartMs;native_image_verified=$crseNativeVerified;exit_code=$crseExitCode;primary_failure=$crseFailures.primary;cleanup_failure=$crseFailures.cleanup;root_termination_confirmed=$crseTerminated;eligible=$crseEligible;elapsed_seconds=[Math]::Round($crseClock.Elapsed.TotalSeconds,3);captured_bytes=$crseState.OutputBytes;prior_metadata_bytes=$crseState.MetaBytes;peak_live_helpers_observed=$crseState.PeakLiveHelpers;stale_relationships=$crseState.StaleRelationships;root_bytes_before_summary=$crseRootBytes}
 try {
  $crseSummaryText=$crseSummary | ConvertTo-Json -Depth 4 -Compress
  $crseSummaryBytes=[Text.Encoding]::UTF8.GetBytes($crseSummaryText + [char]10)
  if ($crseSummaryBytes.Length -gt 4096 -or $crseState.MetaBytes + $crseSummaryBytes.Length -gt 65536 -or $crseState.MetaBytes + $crseState.OutputBytes + $crseSummaryBytes.Length -gt 1048576) { throw 'final_metadata_budget' }
  $crseFinal=[IO.File]::Open($crsePaths['result.json'],[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
  try { $crseFinal.Write($crseSummaryBytes,0,$crseSummaryBytes.Length) } finally { $crseFinal.Dispose() }
  $crseSummaryText
 } finally {
  foreach ($crseChannel in $crseChannels) {
   $crseLines=[Text.Encoding]::UTF8.GetString($crseChannel.Capture.ToArray()) -split "\r?\n"
   if ($crseLines.Count -gt 90) { $crseLines=@($crseLines | Select-Object -First 20) + @($crseLines | Select-Object -Last 60) }
   foreach ($crseLine in $crseLines) { if ($crseLine.Length -gt 500) { $crseLine.Substring(0,500) + ' [display truncated; retained log complete]' } else { $crseLine } }
   if ($null -ne $crseChannel.Stream) { $crseChannel.Stream.Dispose() }
   $crseChannel.Log.Dispose()
   $crseChannel.Capture.Dispose()
  }
  if ($null -ne $crseEvents) { $crseEvents.Dispose() }
  foreach ($crseHelper in @($crseState.HelperHandles.Values)) { $crseHelper.Dispose() }
  $crseProcess.Dispose()
 }
}
if ($crsePrimary -or $crseCleanup -or -not $crseTerminated -or $crseExitCode -eq 3) { exit 124 }
exit $crseExitCode
```
