# CRSE-WCP-3V: exact test filename and verification continuation

Revision: **2026-08-28.1**. Status: **proposed; not approved**.

## Requested decision

Approve one byte-preserving rename of the newly authored integration test and
the corresponding exact Ruff/pytest argument correction. Continue the already
approved WCP-3 fixture rehearsal within its remaining budgets. This is not a new
implementation scope, a budget reset, a commit, or permission for a live effect.

Parent proposal:
`C:/Users/brian/Documents/CM_Computation/CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md`,
CRSE-WCP-3 revision 2026-08-28.1, raw SHA-256
`448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c`.
Read that complete immutable packet and its required instructions/inputs. Its
grants, identities, implementation requirements and exclusions remain in force
except for the exact changes below. Do not run its old appendix unchanged.

## Why this correction is required

The packet names both new modules `test_workspace_create_linkage.py`.
Neither `tests/unit` nor `tests/integration` has an `__init__.py`, so the specified
default pytest import mode collides. The integration module also deliberately
imports the unit command helper under that basename. This was found before
pytest; zero pytest slots were spent and no fixture database was created.

Five-file Ruff lint/format and strict mypy on 84 source files pass. First-pass
ordinary lint/type findings were corrected; all seven supervised applications
closed within the original process/resource limits. One 18-case synthetic
supervisor check passed. This static evidence does not establish runtime behavior.

## Exact rename and unchanged scope

Controller: `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.

Move this one new untracked file, preserving its bytes:

- From `tests/integration/test_workspace_create_linkage.py`.
- To `tests/integration/test_linked_workspace_create.py`.
- Required source raw SHA-256:
  `5df3224cc19755533b34fbc222eab13814c83bfe861c91b745129d29946cf1cd`.

Recheck the source identity, exact absolute paths, non-reparse ancestors, and
destination absence before the move. Do not overwrite an existing destination,
use a glob, stage with Git, or perform any other deletion/rename. Verify the
destination has the same raw hash and the old source name is absent. The bytes
remain recoverable under the new name; this is not content deletion or cleanup.

Replace only that integration path in the original create/write grant and in
the two supervisor argument lists (five Ruff targets and nine pytest modules).
Keep the unit filename and its helper import unchanged. No package marker,
conftest change, import-mode option, dependency, old source/test/SQL edit, or
additional test module is granted.

The logical implementation scope remains eleven files. Treat this byte-preserving
move as relocation of the original create target, not 717 deleted/added lines or
a new twelfth implementation file. All WCP-3 additions remain cumulative against
the original manifest: current total **2,715 additions, 43 deletions**, maximum
**3,000 additions, 150 deletions**. Do not reset that accounting at this packet.

The seven original create targets (with the one replacement name) may receive
ordinary in-scope implementation/test corrections; the four named coordination
files may record actual results. No existing WCP-2 source or test is writable.
Count new-file final lines directly; for the four coordination records, conservatively
add future added/deleted lines to the recorded 45 additions/43 deletions.
Their original line-ending-normalized per-file deltas were 5/0 for workspace
readiness, 16/18 for program status, 12/12 for active plan, 12/13 for next actions.
Removing a new-file line can reduce that new file's cumulative addition count;
it does not grant deletion of an older file. Preserve the original file/line caps.

One maintainer, this task's configured model/effort, concurrency one. No delegation.

## Exact continuation baseline

Require unchanged controller HEAD
`b9dd7724a205ef08b5655839ca6db7dd97b5774e`, an empty index, these eleven authored
versions, and the eight unchanged WCP-2C versions below. Other tracked files must
match HEAD; preserve untracked `coordination/prompts/` unread. No optional
checkpoint substitution is authorized by this amendment.

| WCP-3 file before the rename | Raw SHA-256 |
| --- | --- |
| `src/fractilate_orchestrator/persistence/workspace_create_linkage.py` | `c3ed93e1010943158fead30ac3db65d325caaa5d44465d5a55b3344f71669a8c` |
| `src/fractilate_orchestrator/services/linked_workspace_create.py` | `9d48d169a7fbd1f0163ad17bb0b9a09328017f2fa16593dacc60bde41b2ead51` |
| `tests/unit/test_workspace_create_linkage.py` | `44830b5071ed5c738aad0cf55a37b11c76588b111322ee1e67e3a692503d88a6` |
| `tests/integration/test_workspace_create_linkage.py` | `5df3224cc19755533b34fbc222eab13814c83bfe861c91b745129d29946cf1cd` |
| `tests/fixtures/workspace_create_linkage/fixture_store.py` | `99453a48ac9432065a6bbac640d2080ef056c2a78d8fc29fb8d60ee8222cf242` |
| `docs/decisions/ADR-0024-fixture-controller-workspace-linkage.md` | `a6eaa5136845b764dd21740f7a8078c795534b8ea14dad876bb2c94a3fec03b3` |
| `coordination/WORKSPACE_CREATE_LINKAGE_READINESS.md` | `e96a6354727dd915caeb0ad95893d4b196ff2332dfc873adf1f97ae7d16b9028` |
| `coordination/WORKSPACE_CREATE_READINESS.md` | `f3006178dfd56a5f96943882c280f30cf1e3c9382a072cde6786ecf4d92a8140` |
| `coordination/PROGRAM_STATUS.md` | `84fded0abd31a63ff2173c6f9a51fbdaf02a9c25a45a32bb4f7593574ffd465a` |
| `coordination/plans/ACTIVE_PLAN.md` | `b5df4cecf72e51dbeb9486270a6177fc37a94e877e3ccfb4fa1a509616e7baff` |
| `coordination/NEXT_ACTIONS.md` | `7808e0021c561ed401301f1967c278d8f1ec3a6821eb619069d78b5d8ab4329d` |

| Preserved read-only WCP-2C file | Raw SHA-256 |
| --- | --- |
| `docs/decisions/ADR-0023-fixture-workspace-create-journal.md` | `d8703229281a4ffb3a1a0680c17d9e27af0919e9b7b949d2d4ac47af746192bc` |
| `src/fractilate_orchestrator/persistence/workspace_create_journal.py` | `3194c6a8b53591e4f327395d77e23c07c31d805334a4c247be9c3f1238d0d60d` |
| `src/fractilate_orchestrator/services/durable_workspace_create.py` | `72ebf2dc7f1b6cef9b8eb60ed7e5e7d38793d063e0eb051a8ee736d2205d0bea` |
| `tests/unit/test_workspace_create_journal_contract.py` | `892b6babe0ef3349dc88740a6d651d402421cdbdb07c21e771acfe3582f8b5b8` |
| `tests/integration/test_workspace_create_journal.py` | `9a9aa012d1a33df1b6601cfa6ad83a778f4b981082e4bfc2c78b07779c987936` |
| `tests/integration/test_durable_workspace_create.py` | `9e56568aa9769331329cd395efbf9e142518b0694dea4735b62263d9e61c873e` |
| `tests/fixtures/workspace_create_journal/crash_probe.py` | `301a132a45e8e62a2a58507d7380c49faed727b2468868efc60a141108d5e8a0` |
| `coordination/WORKSPACE_CREATE_PERSISTENCE_READINESS.md` | `2de68f61db96f7a38d95dfecb9e64e3271a426b2b74244cf3ecb78f7ca09ad86` |

Revalidate this amendment's separately supplied raw hash, the parent proposal,
all source/baseline hashes, runtime identities and retained evidence before any
write or check. Do not reset, switch, stage, repair, or clean to obtain a match.
Preserve unrelated CM work and previous proposals. Read-only status/diff/hash/
path metadata checks are allowed; secrets and user configuration are not.

## Root and budgets: continue, never recreate

Retain the already created root
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp3-tests-20260828-01`.
At handoff: 54 files, 11,376,294 bytes; zero `.sqlite3` fixtures. Its isolated mypy
cache is existing WCP-3 check output, not a production/controller database.
Recheck non-reparse paths and all listed root-local evidence hashes. Do not remove,
recreate or rename the root or earlier artifacts. Original absence checks apply
only to not-yet-created check evidence and `pytest-1`, `pytest-2`, `pytest-3`.

| Check class | Already used | Allowed remaining names |
| --- | --- | --- |
| Pytest | 0 / 3 | `pytest-1`, `pytest-2`, `pytest-3` |
| Ruff lint | 2 / 3 | `ruff-lint-3` |
| Ruff formatter | 2 / 3 | `ruff-format-3` |
| Ruff format-check | 1 / 3 | `ruff-formatcheck-2`, `ruff-formatcheck-3` |
| Strict mypy | 2 / 3 | `mypy-3` |
| Synthetic supervisor self-check | 1 / 2 | `supervisor-selfcheck-2.json` |

No obligation to spend every slot. A byte-only rename does not invalidate source
content checks, but their historical target name remains explicitly recorded.
After any code correction, use applicable remaining checks and disclose anything
not rerun. Ordinary inspected test/code failures may consume remaining slots;
actual identity/process/termination/resource violations stop all further checks.

The original 300 seconds, 1 MiB combined output/evidence, 4 KiB frames, 64 KiB
metadata, one application plus at most one exact attributable OS console host
remain unchanged. No helper, ordinary child, or host descendant. Preserve owned
identity, pre/post hash, error retention, leaf-before-root shutdown, closed-stream
accounting and the known-root minimum process peak. Per fixture: DELETE/FULL,
foreign keys ON, memory temp, <=1,000 ms busy timeout, 4 MiB page limit, 64 databases
per iteration, 256 MiB retained root and all original row/document limits.

Use the exact direct Python/Ruff executables and all five raw hashes from the
parent packet; never launch the venv redirector or conhost directly. Preserve the
cleared environment and names/values from that packet, including literal
`__PYVENV_LAUNCHER__` for direct Python only. No install, PATH fallback, ambient
dump, network, listener, coverage, build, full suite or existing DB integration run.

## Exact corrected arguments and supervisor handoff

Each pytest iteration uses direct Python:
`-B -m pytest -q -p no:cacheprovider --basetemp <retained-root>/pytest-N`,
followed by exactly, in this order:

```text
tests/unit/test_workspace_create_contract.py
tests/unit/test_workspace_create_intents.py
tests/unit/test_workspace_create_recovery.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
tests/unit/test_external_operations.py
tests/unit/test_workspace_create_journal_contract.py
tests/unit/test_workspace_create_linkage.py
tests/integration/test_linked_workspace_create.py
```

Ruff uses `check --no-cache`, `format --no-cache`, or
`format --check --no-cache`, followed by exactly these five paths:

```text
src/fractilate_orchestrator/persistence/workspace_create_linkage.py
src/fractilate_orchestrator/services/linked_workspace_create.py
tests/unit/test_workspace_create_linkage.py
tests/integration/test_linked_workspace_create.py
tests/fixtures/workspace_create_linkage/fixture_store.py
```

Mypy remains direct Python `-B -m mypy --cache-dir <retained-root>/mypy`.
Use absolute basetemp/cache values in actual argv, with the controller as cwd.

The appendix below is the actual qualified WCP-3 static-check supervisor, retained
as **inert reference**, not permission to run it before this approval. Adapt only
its two old integration-path literals and the continuation guards described here;
do not restore helper allowances or otherwise expand its process policy.

Before a real continuation check, use the one remaining synthetic self-check
(no child/database, <=30 seconds/4 KiB, create-new selfcheck-2 evidence). Cover full
PowerShell parse, exact corrected argv/rejection of the old integration name,
allowed remaining names, old/new root distinction, host identity/count, no helper/
host-child admission, simultaneous primary/cleanup failures, open-stream length
and known-root process accounting. Reuse the qualified classifier, not a different
classifier merely for the self-check. Record both the parent proposal hash and
this amendment's separately supplied raw hash. Do not retry a consumed self-check.

Add continuation preflight guards requiring that passed selfcheck-2 binding and
the actual raw hash of this amendment, in addition to the existing parent-hash/
selfcheck-1 guard. Bind the allowed names above; create-new evidence checks remain.
A supplied hash is not approval: it must equal the separately owner-approved
packet identity and on-disk raw hash. The original seven result records must stay
unchanged and eligible; first lint/mypy exit 1 values are ordinary code failures.
No new local helper script or executable is created by this handoff.

## Completion and excluded effects

Run the corrected bounded matrix, inspect failures and correct only in-scope
files within remaining budgets. Record actual results, final source/evidence
hashes, limits and retained artifacts in the existing WCP-3 readiness/coordination
records. Review scope and empty index; prepare the next exact proposal without
waiting for another request to continue. Do not claim runtime completion until
the required tests actually pass.

No commit/staging, push/publication/CI, existing controller database or migration,
production installation, native Git/workspace, worker/verifier, SDK, network/
listener, runtime upgrade or manual cleanup. The real owner-approval record,
production integration, native containment and successor product packet remain
separate. Original decisions 1-5 stay bound only to plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle `a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
**Execution of `workspace.create/v1` remains unapproved.**

## Suggested approval

> I approve CRSE-WCP-3V revision 2026-08-28.1, bound to its separately supplied
> raw-file SHA-256: the exact byte-preserving integration-test rename, corrected
> arguments and remaining bounded WCP-3 verification. All original cumulative
> limits and exclusions remain. I do not approve commits or live effects.

## Retained root-local evidence manifest

These are immutable historical records; mypy cache contents are not reproduced.
All 36 direct root files are bound below. Preserve the full retained root.

| File | Bytes | Raw SHA-256 |
| --- | ---: | --- |
| `mypy-1.events.jsonl` | 1495 | `6dd909dce8d051d0c647280a2f289cc4fda5679eef2615d6ccb1cb48b3b26c65` |
| `mypy-1.result.json` | 456 | `9ea59a3ccea914e915901028c0dffb7ce977160159fe741cdf0811d1888142e0` |
| `mypy-1.runtime.json` | 104 | `bbcdde523c5e569b21051d2db05425b793b84b678850fa48836badf11a048148` |
| `mypy-1.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `mypy-1.stdout.log` | 1827 | `b4f7a3b0671e2abe24e8a2c34383ea0f83e26b1a5deb8b6eb995f2b88e8a03cf` |
| `mypy-2.events.jsonl` | 1410 | `c24adb7474d2aee4aa0256b4d0e50719bbb2281c14557a96098a8bcb350ba937` |
| `mypy-2.result.json` | 453 | `1b3ebb380a0fa7ace557140f478d2a9c7503b091361be99785dfb5d0c5b9d45a` |
| `mypy-2.runtime.json` | 103 | `211b02244d3fda19197bd9520e85c81e8c8bdbdd31d898316e1f766ac1e3ad52` |
| `mypy-2.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `mypy-2.stdout.log` | 45 | `8227aa84d79369db03f4582ec792ab58f3093cdde56af5590424db3800698e03` |
| `ruff-format-1.events.jsonl` | 541 | `24bd28df2740a83dc2ba9c72e734e4f9c87139923909463eb71cba7e4d8a01cf` |
| `ruff-format-1.result.json` | 451 | `ccf000403d81c6980fa8e086e4339e957a4b2f1f709d73eb3cf2a4f671fc464e` |
| `ruff-format-1.runtime.json` | 111 | `eb92ceac8ccfd2585fb769b68dcf5a75303cb28790d2d85b22059e023f518e52` |
| `ruff-format-1.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `ruff-format-1.stdout.log` | 43 | `0e3227a0576bf4b1300048e70321b65f0c0078106a8c61ad1f3e4e7a641e0bd2` |
| `ruff-format-2.events.jsonl` | 541 | `3c92dd4d374b4bcf188c43855e130cefe05abd5ca085a4c86b4028b03c14d60e` |
| `ruff-format-2.result.json` | 460 | `9a3bc714f6e493cc95ff199e067518d63b2a1846f4108ec0922f2fd903c2ce52` |
| `ruff-format-2.runtime.json` | 111 | `6a9bf2b69196f441019de46bf92285374c3e55f7704b4129c68695b0a5399637` |
| `ruff-format-2.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `ruff-format-2.stdout.log` | 44 | `8e2386a91e134d7c59880fba6492f92667e157bfb1bbece84b5f0b61066c4964` |
| `ruff-formatcheck-1.events.jsonl` | 541 | `70cf61d6a5e86f9612952471a0d3fe36a0f5ecc886c604bc7bb62c93fbc1e9a2` |
| `ruff-formatcheck-1.result.json` | 465 | `b384fd41b1c3540b1bf89f54d1b169ce21c55ace7ad7668813b68818f8d249e9` |
| `ruff-formatcheck-1.runtime.json` | 116 | `cb74df4c7aac29d9e3b10a7ed394ac2403e5e7e77803644d21294f276748db76` |
| `ruff-formatcheck-1.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `ruff-formatcheck-1.stdout.log` | 26 | `f114d83b30c5c657ee43a847a45bafccaea255d82673feb87c26d252c61e29c1` |
| `ruff-lint-1.events.jsonl` | 541 | `67541b040eadca605748a1665ee4ec69a23d38e90056404cbd320649e7ef5ebe` |
| `ruff-lint-1.result.json` | 455 | `f28bf222a0661dbe860f01a252986e654315de54e0975c6a80384762661f1328` |
| `ruff-lint-1.runtime.json` | 109 | `db64b6b1d8fa64fc97b172895707b1b27bf2224da84b1af0a0c029302d0f52de` |
| `ruff-lint-1.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `ruff-lint-1.stdout.log` | 10199 | `d0dedaec0c4e0013ccf625daf29968690752f5b3cfff166c01661df06c7aa9ed` |
| `ruff-lint-2.events.jsonl` | 540 | `78f8093f8acbd1fc6aa1a5297a61d1739aec1c530ae0eb6140a51a2eaacd5291` |
| `ruff-lint-2.result.json` | 457 | `743197c9b38b4cdb1bc2df087975cc2f213197c08a3af0536f401e8c3eb47d7c` |
| `ruff-lint-2.runtime.json` | 107 | `3e72274cd9f2a30668b238f6f21b41fb13bbf46488bc6ea97032e834a218e5c0` |
| `ruff-lint-2.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `ruff-lint-2.stdout.log` | 19 | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| `supervisor-selfcheck-1.json` | 183 | `74dcfa289850910bc0e76175015d490d0861fc1855ad3ee1ee9fc5bd3fb71686` |

## Inert qualified WCP-3 supervisor reference

Supply the exact check name/argv separately only after approved adaptation and
synthetic qualification. This text preserves the pre-amendment names for audit;
do not run it unchanged or treat it as a new grant.

```powershell
function Get-CRelation {
 param([int]$ParentId,[long]$ParentStartMs,[string]$ParentRole,[hashtable]$Candidate)
 if ($Candidate.ParentId -ne $ParentId -or $Candidate.ProcessId -le 0 -or $Candidate.ProcessId -eq $ParentId -or $null -eq $Candidate.StartMs) { return 'ambiguous' }
 if ([long]$Candidate.StartMs -lt ($ParentStartMs - 1)) { return 'stale' }
 if ([long]$Candidate.StartMs -le ($ParentStartMs + 1)) { return 'ambiguous' }
 if ($ParentRole -eq 'host') { return 'unexpected' }
 if ($Candidate.NativeImage -ne $cConhost) { return 'unexpected' }
 if (-not $Candidate.NativeVerified -or -not $Candidate.HashVerified) { return 'ambiguous' }
 return 'host'
}
function Get-CShapeFailure {
 param([string[]]$Relations,[string]$ParentRole='application')
 if (@($Relations | Where-Object { $_ -notin @('stale','host') }).Count -gt 0) { return 'unexpected_or_ambiguous_descendant' }
 $cHostCount=@($Relations | Where-Object { $_ -eq 'host' }).Count
 if ($cHostCount -gt 1 -or ($ParentRole -eq 'host' -and $cHostCount -gt 0)) { return 'descendant_count' }
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
$ErrorActionPreference = 'Stop'
$cRoot = 'C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp3-tests-20260828-01'
$cRepo = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator'
$cPython = 'C:\Users\brian\AppData\Local\Programs\Python\Python310\python.exe'
$cBinding = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\python.exe'
$cRuff = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\ruff.exe'
$cConhost = 'C:\Windows\System32\conhost.exe'
$cConhostHash = 'b02ee54fb2ec69673386d41119ee8ed083a6eab3bfca6aa2155d20ce68ef8963'
$cOpenStreams = @{}
if ($cCheckName -notmatch '^(ruff-lint-[123]|ruff-(format|formatcheck)-[123]|mypy-[123]|pytest-[123])$') { throw 'Unapproved check name.' }
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
  }
 }
 if ($cBytes -ge 268435456) { throw 'root_budget' }
 return $cBytes
}
[void](Test-CBudget)
$cSelfcheck = Read-CMetadata -Path (Join-Path $cRoot 'supervisor-selfcheck-1.json')
if (-not $cSelfcheck.passed -or $cSelfcheck.amendment_sha256 -ne '448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c') { throw 'selfcheck_not_passed' }
if ((Get-FileHash -LiteralPath 'C:\Users\brian\Documents\CM_Computation\CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md').Hash.ToLowerInvariant() -ne $cSelfcheck.amendment_sha256) { throw 'amendment_drift' }
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cRoot -File -Filter '*.result.json')) {
 $cPrior = Read-CMetadata -Path $cPriorFile.FullName
 if ($cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw 'prior_check_stop' }
}
$cTargets=@(
 'src/fractilate_orchestrator/persistence/workspace_create_linkage.py',
 'src/fractilate_orchestrator/services/linked_workspace_create.py',
 'tests/unit/test_workspace_create_linkage.py',
 'tests/integration/test_workspace_create_linkage.py',
 'tests/fixtures/workspace_create_linkage/fixture_store.py'
)
$cExpectedArgs = if ($cCheckName -like 'ruff-lint-*') { @('check','--no-cache') + $cTargets }
 elseif ($cCheckName -like 'ruff-formatcheck-*') { @('format','--check','--no-cache') + $cTargets }
 elseif ($cCheckName -like 'ruff-format-*') { @('format','--no-cache') + $cTargets }
 elseif ($cPytest) { @('-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp',(Join-Path $cRoot $cCheckName)) + @('tests/unit/test_workspace_create_contract.py','tests/unit/test_workspace_create_intents.py','tests/unit/test_workspace_create_recovery.py','tests/unit/test_workspaces.py','tests/unit/test_product_pilot.py','tests/unit/test_external_operations.py','tests/unit/test_workspace_create_journal_contract.py','tests/unit/test_workspace_create_linkage.py','tests/integration/test_workspace_create_linkage.py') }
 else { @('-B','-m','mypy','--cache-dir',(Join-Path $cRoot 'mypy')) }
if (($cExpectedArgs | ConvertTo-Json -Compress) -cne ($cCheckArgs | ConvertTo-Json -Compress)) { throw 'argv_not_approved' }
$cPaths = @{}
foreach ($cSuffix in @('stdout.log','stderr.log','events.jsonl','runtime.json','result.json')) {
 $cPaths[$cSuffix] = Join-Path $cRoot ($cCheckName + '.' + $cSuffix)
 if (Test-Path -LiteralPath $cPaths[$cSuffix]) { throw 'evidence_path_exists' }
}
if ($cPytest -and (Test-Path -LiteralPath (Join-Path $cRoot $cCheckName))) { throw 'basetemp_exists' }
$cState = @{MetaBytes=0L;OutputBytes=0L;Seen=@{};Hosts=@{};PeakLiveHosts=0;PeakProcesses=0;StaleRelationships=0}
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
  $cRelation=Get-CRelation -ParentId $HostRecord.ProcessId -ParentStartMs $HostRecord.StartMs -ParentRole 'host' -Candidate $cCandidate
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
 param([int]$ParentId,[long]$ParentStartMs)
 $cRelations=[Collections.Generic.List[string]]::new()
 foreach ($cInfo in @(Get-CScopedProcesses -Filter ("ParentProcessId=" + $ParentId))) {
  $cStart=Get-CStartMs -Info $cInfo
  $cCandidate=@{ProcessId=[int]$cInfo.ProcessId;ParentId=[int]$cInfo.ParentProcessId;StartMs=$cStart;Exited=$false;NativeVerified=($cInfo.ExecutablePath -eq $cConhost);HashVerified=$true;NativeImage=$cInfo.ExecutablePath}
  $cRelation=Get-CRelation -ParentId $ParentId -ParentStartMs $ParentStartMs -ParentRole 'application' -Candidate $cCandidate
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
  $cRelations.Add($cRelation)
 }
 $cShapeFailure=Get-CShapeFailure -Relations $cRelations.ToArray()
 if ($cShapeFailure) { throw $cShapeFailure }
 $cParentHosts=@($cState.Hosts.Values | Where-Object { $_.ParentId -eq $ParentId -and $_.ParentStartMs -eq $ParentStartMs })
 if ($cParentHosts.Count -gt 1) { throw 'additional_console_host' }
 foreach ($cRecord in $cParentHosts) { Update-CHost -HostRecord $cRecord }
}

function Inspect-CChildren {
 param([int]$ParentId,[long]$ParentStartMs)
 Inspect-CApplication -ParentId $ParentId -ParentStartMs $ParentStartMs
 $cLiveHosts=@($cState.Hosts.Values | Where-Object { -not $_.Exited }).Count
 $cLiveApps=[int](-not $cProcess.HasExited)
 $cState.PeakLiveHosts=[Math]::Max($cState.PeakLiveHosts,$cLiveHosts)
 $cState.PeakProcesses=[Math]::Max($cState.PeakProcesses,($cLiveHosts + $cLiveApps))
 Save-CCandidate -Frame ([ordered]@{type='process_counts';live_applications=$cLiveApps;live_hosts=$cLiveHosts;total=($cLiveApps + $cLiveHosts);ceiling=2})
 if (($cLiveHosts + $cLiveApps) -gt 2 -or $cLiveHosts -gt 1) { throw 'process_ceiling' }
 [void](Test-CBudget)
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
 $cState.PeakProcesses=1
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
   Inspect-CChildren -ParentId $cProcessId -ParentStartMs $cStartMs
   $cNextInspection=$cClock.ElapsedMilliseconds + 500
  }
  if ($cProcess.HasExited -and @($cChannels | Where-Object { -not $_.Done }).Count -eq 0) { break }
  [Threading.Thread]::Sleep(10)
 }
} catch { $cPrimary=$_.Exception.Message }
finally {
 if ($cStarted) {
  try {
   if ($cNativeVerified) { Inspect-CChildren -ParentId $cProcessId -ParentStartMs $cStartMs }
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
   if (-not $cProcess.HasExited) {
    if (-not $cNativeVerified) { throw 'unverified_root_not_terminated' }
    if (-not $cPrimary) { $cPrimary='root_incomplete' }
    $cProcess.Kill()
   }
   $cTerminated=$cProcess.WaitForExit(5000)
   if (-not $cTerminated) { throw 'root_termination_unconfirmed' }
   $cExitCode=$cProcess.ExitCode
   $cExitMs=([DateTimeOffset]$cProcess.ExitTime.ToUniversalTime()).ToUnixTimeMilliseconds()
   if (@($cState.Hosts.Values | Where-Object { $_.StartMs -gt $cExitMs }).Count -gt 0) { throw 'host_outside_root_lifetime' }
   Inspect-CChildren -ParentId $cProcessId -ParentStartMs $cStartMs
   $cHostsTerminated=@($cState.Hosts.Values | Where-Object { -not $_.Exited }).Count -eq 0
   if (-not $cHostsTerminated) { throw 'host_termination_unconfirmed' }
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
 $cSummary=[ordered]@{check=$cCheckName;pid=$cProcessId;start_ms=$cStartMs;native_image_verified=$cNativeVerified;exit_code=$cExitCode;primary_failure=$cFailures.primary;cleanup_failure=$cFailures.cleanup;root_termination_confirmed=$cTerminated;host_termination_confirmed=$cHostsTerminated;eligible=$cEligible;elapsed_seconds=[Math]::Round($cClock.Elapsed.TotalSeconds,3);captured_bytes=$cState.OutputBytes;prior_metadata_bytes=$cState.MetaBytes;peak_live_hosts_observed=$cState.PeakLiveHosts;peak_os_processes_observed=$cState.PeakProcesses;stale_relationships=$cState.StaleRelationships;root_bytes_before_summary=$cRootBytes;root_bytes_after_summary=0L}
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
  foreach ($cHostRecord in @($cState.Hosts.Values)) { if ($null -ne $cHostRecord.Handle) { $cHostRecord.Handle.Dispose() } }
  $cProcess.Dispose()
 }
}
if ($cPrimary -or $cCleanup -or -not $cTerminated -or -not $cHostsTerminated -or $cExitCode -notin @(0,1)) { exit 124 }
exit $cExitCode
```
