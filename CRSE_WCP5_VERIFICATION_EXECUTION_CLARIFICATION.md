# WCP-5 verification execution clarification

Revision: 2026-08-28.1. Status: proposed, not approved.

## Exact additional decision

Authorize executing the fixed PowerShell supervisor below and its bounded pure
qualification cases, solely to run the already approved WCP-5 checks. This
clarifies execution of reviewed code; it does not treat arbitrary document
instructions as authority. Do not run this packet before that explicit decision.

The execution reviewer rejected the first proposed preflight because its
reconstructor executed PowerShell extracted from local documents. No command
body, Python/Ruff application, qualification or test ran. The attempt is retained
in preflight-1.json with unavailable timing; it remains consumed. The rejection
has not been bypassed.

The replacement preparation must treat all document fences as data. Read the
exact supervisor fence below, check its normalized UTF-8 SHA-256 against the
fixed-body digest below, parse complete AST boundaries, and confirm
the four pure classifier functions match the historical bytes. No parent
reconstructor or arbitrary document script is to be evaluated.

Fixed supervisor normalized UTF-8 SHA-256:
`47a085ef6d6a2581e3518da6377613b07446e6181e32ab9e4159e12d41f461cc`.
The raw hash of this complete clarification packet binds the qualification cases
as well as the runner; it will be supplied with the approval request.

Only after approval, execute the explicitly reviewed pure functions and exact
binding checks for a new formal qualification; then execute this exact supervisor
body for the approved commands. Record the actual body hash, approved packet
hashes, checkpoint, root, target lists, and output filename. No expression,
callback, plugin, helper script or command supplied by an observation is allowed.

Parent syntax preflights may only parse text before that approval. They cannot
qualify or launch the runner. This packet itself does not authorize even a test
launch, and is not permission for native workspace code.

## Preserved scope, identity and remaining budget

The original WCP-5 packet remains immutable:
`de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295`.
Controller HEAD remains `6fd2d5a797bb355412ff61ea180c6fb9aa2f038a`.
Twelve controller paths, 5,000 additions / 300 deletions, concurrency one,
no delegation, exact runtimes/environment and all exclusions remain unchanged.

The existing WCP-5 root is
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp5-tests-20260828-01`.
It was created under the original approval. No fixture database has been created.
Do not recreate, clean or replace it. Retain both preflight records and every
older root.

Usage at this clarification: parent preflight 2/10 consumed;
formal qualification 0/5; pytest 0/6; Ruff lint/format/format-check 0/6 each;
mypy 0/6. No staging or commit has been attempted. Later parsing-only preflights
must be recorded separately and deducted, not reset by this packet.

Attempt 1 was rejected before its command started. Attempt 2 passed a materially
safer parsing-only check in 0.17 seconds: the fixed runner and qualification text
parse, their boundaries are complete, and four pure function definitions match
the predecessor bytes. No extracted function or runner was evaluated; zero
subprocesses and zero databases were created. This is not formal qualification
or behavioral verification. The two create-new records total 805 bytes:

- preflight-1.json: SHA-256
  `6c10051823d06a95e83183c2c9103de34b26e33ebeee3c89af79b056cfe5b62c`.
- preflight-2.json: SHA-256
  `093e263322af706addd0415caad84023967e8c025dfe29895e38e5c59a232971`.

The exact thirteen pytest modules, six Ruff paths, strict mypy command, runtime
hashes, 300-second/1-MiB limits, two-process ceiling (one application plus at most
one exact attributable console host), no-helper rule, create-new evidence and
96-DB-per-iteration/4-MiB-per-DB/256-MiB-root limits are unchanged from WCP-5.
No native Git, product observation, actual workspace create, worker, verifier,
SDK, network, publication, production DB or cleanup is authorized.

## Finish the existing batch, not another stop after each check

After a passed formal qualification, run the approved checks, correct ordinary
code/test findings within the remaining exact scope and slots, retain all
failures, and rerun relevant checks. A genuine process/identity/resource/closure
violation stops further applications. Larger limits or changed runtime policy
require a new decision.

After every WCP-5 acceptance gate passes, make its single already-approved
conditional local commit with the exact frozen index/base/blobs, disabled
hooks/signing/maintenance and message `Add inert native workspace adapter contracts`.
Do not commit an unverified draft, repeat the WCP-4 checkpoint, push or amend.
Then prepare the consolidated attended-native-fixture proposal; execute none
of that later proposal. Real owner intake and production installation stay separate.

## Approval wording

> I approve WCP-5 verification execution clarification revision 2026-08-28.1,
> bound to its supplied raw packet hash and fixed-supervisor hash. I explicitly
> authorize running that reviewed PowerShell supervisor and its bounded pure
> qualification cases for the exact existing WCP-5 tests/static checks, corrections
> and one conditional local commit, within the remaining original limits.
> Do not execute parent-document reconstructors, native workspace/Git code,
> product effects, publication or cleanup.

## Fixed supervisor body (data until explicitly approved)

The body is the final WCP-4 runner with only WCP-5 stage bindings changed:
root, checkpoint, packet/qualification bindings, historical WCP-4 evidence
guards and the thirteen/six exact target lists. It retains the same four pure
functions and supervision behavior. It assumes the parent has supplied only
the exact cCheckName/cCheckArgs, cRunnerHash and passed cQualificationName.

<!-- BEGIN FIXED WCP5 SUPERVISOR -->
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
$cRoot = 'C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp5-tests-20260828-01'
$cRepo = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator'
$cPython = 'C:\Users\brian\AppData\Local\Programs\Python\Python310\python.exe'
$cBinding = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\python.exe'
$cRuff = 'C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\ruff.exe'
$cConhost = 'C:\Windows\System32\conhost.exe'
$cConhostHash = 'b02ee54fb2ec69673386d41119ee8ed083a6eab3bfca6aa2155d20ce68ef8963'
$cOpenStreams = @{}
if ($cCheckName -notmatch '^(ruff-lint-[1-6]|ruff-(format|formatcheck)-[1-6]|mypy-[1-6]|pytest-[1-6])$') { throw 'Unapproved check name.' }
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
    if ($cItem.Length -gt 4194304 -or $cDatabases[$cIteration] -gt 96) { throw 'database_budget' }
   }
  }
 }
 if ($cBytes -ge 268435456) { throw 'root_budget' }
 return $cBytes
}
[void](Test-CBudget)
$cOldRoot='C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp3-tests-20260828-01'
$cOriginalSelf=Read-CMetadata -Path (Join-Path $cOldRoot 'supervisor-selfcheck-1.json')
if (-not $cOriginalSelf.passed -or $cOriginalSelf.amendment_sha256 -ne '448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c' -or (Get-FileHash -LiteralPath (Join-Path $cOldRoot 'supervisor-selfcheck-1.json')).Hash.ToLowerInvariant() -ne '74dcfa289850910bc0e76175015d490d0861fc1855ad3ee1ee9fc5bd3fb71686') { throw 'historical_selfcheck_drift' }
foreach ($cPacket in @(
 @('CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md','448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c'),
 @('CRSE_WCP3_TEST_FILENAME_AMENDMENT.md','35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4'),
 @('CRSE_WCP3_GROUPED_DEVELOPMENT_BATCH.md','4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e'),
 @('CRSE_WCP4_DURABLE_APPROVAL_BATCH.md','e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22'),
 @('CRSE_WCP5_NATIVE_ADAPTER_BATCH.md','de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295')
)) { if ((Get-FileHash -LiteralPath (Join-Path 'C:\Users\brian\Documents\CM_Computation' $cPacket[0])).Hash.ToLowerInvariant() -ne $cPacket[1]) { throw 'packet_drift' } }
$cHeadText=[IO.File]::ReadAllText((Join-Path $cRepo '.git\HEAD')).Trim()
if ($cHeadText.StartsWith('ref: refs/heads/')) { $cHeadText=[IO.File]::ReadAllText((Join-Path $cRepo ('.git\'+$cHeadText.Substring(5)))).Trim() }
if ($cHeadText -cne '6fd2d5a797bb355412ff61ea180c6fb9aa2f038a') { throw 'checkpoint_drift' }
$cAncestor=Get-Item -Force -LiteralPath $cRoot
while ($null -ne $cAncestor) { if ($cAncestor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'redirected_root_ancestor' }; $cAncestor=$cAncestor.Parent }
foreach ($cOriginal in @(
 @('supervisor-selfcheck-3.json','0a065f5e929040922a1aed94ac22abcc3e85537fa8486a3980c00bc9314bd5fc'),
 @('pytest-1.result.json','2b48fb4ec6c3bb72ade97c5b3175f582bc28766c35781a29d0d22a1bf0e760a5'),
 @('pytest-2.result.json','edc02ab8435569e37e193b424093345c907f088f9cd188baac26976e5aa5dc09'),
 @('ruff-lint-3.result.json','4b769295bc30935d8b7f7183a7fa94f03077eec0cfce91d557916d8d0c2803e2'),
 @('ruff-formatcheck-2.result.json','8c2d4a8dacfb250e05fb178fe49a723691a882c69fd34f96b8bae07c5a0dbec1'),
 @('mypy-3.result.json','9c89d5ba3756e4656b2ea7b507e532aad11f7e686b730d9050f709b069981609'),
 @('ruff-lint-2.result.json','743197c9b38b4cdb1bc2df087975cc2f213197c08a3af0536f401e8c3eb47d7c'),
 @('mypy-2.result.json','1b3ebb380a0fa7ace557140f478d2a9c7503b091361be99785dfb5d0c5b9d45a'),
 @('ruff-formatcheck-1.result.json','b384fd41b1c3540b1bf89f54d1b169ce21c55ace7ad7668813b68818f8d249e9'),
 @('mypy-1.result.json','9ea59a3ccea914e915901028c0dffb7ce977160159fe741cdf0811d1888142e0'),
 @('ruff-format-1.result.json','ccf000403d81c6980fa8e086e4339e957a4b2f1f709d73eb3cf2a4f671fc464e'),
 @('ruff-format-2.result.json','9a3bc714f6e493cc95ff199e067518d63b2a1846f4108ec0922f2fd903c2ce52'),
 @('ruff-lint-1.result.json','f28bf222a0661dbe860f01a252986e654315de54e0975c6a80384762661f1328'),
 @('supervisor-selfcheck-2.json','c1410673c0ca91a1830d85485736a3ec249582477198120bd624d1dc4d585d22')
)) { if ((Get-FileHash -LiteralPath (Join-Path $cOldRoot $cOriginal[0])).Hash.ToLowerInvariant() -ne $cOriginal[1]) { throw 'historical_evidence_drift' } }
$cWcp4Root='C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp4-tests-20260828-01'
foreach ($cOriginal in @(
 @('preflight-1.json','c273e41370d5456c92d21ac3185bee44279b312180dc0aceccf32ab390c73ebf'),
 @('preflight-2.json','f25664ba56a20b650309edb001743a4fa694942ed4f8b7f5d8e26721c4817c25'),
 @('supervisor-selfcheck-1.json','5a041f74881eec2b6eec8f3010f5345a62a6fc92c01c76c51b29c59239e7284c'),
 @('supervisor-selfcheck-2.json','263b8fbb88c1c3296ba55974460b5de77365f31062bce4fe385846c8b6cb609c'),
 @('supervisor-selfcheck-3.json','85b52f7d2f83313cb8d8c7b968960652ad1d41a3e30179ec1d706a09c6bd3b73'),
 @('ruff-format-1.result.json','a6094e778fad80a043ddc0ef822400c40dd1b83984109af64bd062f6840bceef'),
 @('ruff-lint-1.result.json','8ca49bec905ca94c2d0fb5061a3e522460ffb090978fe7fad850a2cff1b93711'),
 @('mypy-1.result.json','7bac7f2d1e874fd4df12d67bb8002be0683f03b592fd017e2fb27aea6196ba73'),
 @('pytest-1.result.json','b81b40a4166afa9e6336a9a70054253828dc93f37ecddd30a4bcc7e17fc8124f'),
 @('ruff-format-2.result.json','eb863fdb7e07518ae4baa88105fdce77cfb316cbaab7256185eaff9351fb8a25'),
 @('ruff-lint-2.result.json','170785e7d4f2327e9b12ff7d0813cb704fc3c220e7f7b8e2b52074bdecd7279c'),
 @('mypy-2.result.json','d004f91607514fa07668a6e6606bc14d2f4de9e7bfa09dac87e15ab852ed5ced'),
 @('pytest-2.result.json','c8dcb2a9c9c6e99b39c73599b149b0d804da2090bd9096c9b231dfa29aed1709'),
 @('ruff-formatcheck-1.result.json','47332a88aa501ac921a5602bcc386f6c98d25846ba4b6e3b707fb7a5ac2235aa')
)) { if ((Get-FileHash -LiteralPath (Join-Path $cWcp4Root $cOriginal[0])).Hash.ToLowerInvariant() -ne $cOriginal[1]) { throw 'wcp4_evidence_drift' } }
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cWcp4Root -File -Filter '*.result.json')) {
 $cPrior=Read-CMetadata -Path $cPriorFile.FullName
 if (-not $cPrior.eligible -or $cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw 'wcp4_check_stop' }
}
if ($cQualificationName -notmatch '^supervisor-selfcheck-[1-5]\.json$') { throw 'qualification_name' }
$cQualified=Read-CMetadata -Path (Join-Path $cRoot $cQualificationName)
if (-not $cQualified.passed -or $cQualified.runner_sha256 -ne $cRunnerHash -or $cQualified.parent_sha256 -ne '448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c' -or $cQualified.v_sha256 -ne '35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4' -or $cQualified.batch_sha256 -ne '4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e' -or $cQualified.wcp4_sha256 -ne 'e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22' -or $cQualified.wcp5_sha256 -ne 'de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295' -or $cQualified.checkpoint -ne '6fd2d5a797bb355412ff61ea180c6fb9aa2f038a' -or $cQualified.root -ne $cRoot -or $cQualified.database_limit -ne 96) { throw 'wcp5_qualification_binding' }
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cOldRoot -File -Filter '*.result.json')) {
 $cPrior=Read-CMetadata -Path $cPriorFile.FullName
 if (-not $cPrior.eligible -or $cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw 'old_check_stop' }
}
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cRoot -File -Filter '*.result.json')) {
 $cPrior = Read-CMetadata -Path $cPriorFile.FullName
 if (-not $cPrior.eligible -or $cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw 'prior_check_stop' }
}
$cTargets=@(
'src/fractilate_orchestrator/domain/workspace_create_native.py',
'src/fractilate_orchestrator/adapters/workspace_create_native.py',
'src/fractilate_orchestrator/services/native_workspace_create.py',
'tests/unit/test_workspace_create_native_contract.py',
'tests/unit/test_workspace_create_native_adapter.py',
'tests/fixtures/workspace_create_linkage/fixture_store.py'
)
$cExpectedArgs = if ($cCheckName -like 'ruff-lint-*') { @('check','--no-cache') + $cTargets }
 elseif ($cCheckName -like 'ruff-formatcheck-*') { @('format','--check','--no-cache') + $cTargets }
 elseif ($cCheckName -like 'ruff-format-*') { @('format','--no-cache') + $cTargets }
 elseif ($cPytest) { @('-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp',(Join-Path $cRoot $cCheckName)) + @('tests/unit/test_workspace_create_contract.py','tests/unit/test_workspace_create_intents.py','tests/unit/test_workspace_create_recovery.py','tests/unit/test_workspaces.py','tests/unit/test_product_pilot.py','tests/unit/test_external_operations.py','tests/unit/test_workspace_create_journal_contract.py','tests/unit/test_workspace_create_linkage.py','tests/integration/test_linked_workspace_create.py','tests/unit/test_workspace_create_approval_contract.py','tests/integration/test_approved_linked_workspace_create.py','tests/unit/test_workspace_create_native_contract.py','tests/unit/test_workspace_create_native_adapter.py') }
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
<!-- END FIXED WCP5 SUPERVISOR -->

## Pure qualification reference (data until explicitly approved)

Run complete AST function boundaries only after matching the exact fixed body.
Use the prior four-function bytes as read-only reference; evaluate no parent
packet reconstructor. The qualification writer must independently validate its
exact absent output name supervisor-selfcheck-N.json with N in 1..5 and record
actual timings/case count. Never substitute a historical evidence filename.
The following cases are intended; they have not run in WCP-5.

<!-- BEGIN WCP5 QUALIFICATION CASES -->
```powershell

$cCases=0
function Assert-C([bool]$ok,[string]$name) { if (-not $ok) {throw $name}; $script:cCases++ }
$cTokens=$null; $cErrors=$null
$cAst=[Management.Automation.Language.Parser]::ParseInput($cRunner,[ref]$cTokens,[ref]$cErrors)
Assert-C ($cErrors.Count -eq 0) 'full_syntax'
$cConhost='C:\Windows\System32\conhost.exe'
$cPure=@($cAst.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in @('Get-CRelation','Get-CShapeFailure','Join-CFailures','Get-CAccountedLength')},$true))
Assert-C ($cPure.Count -eq 4) 'complete_functions'
foreach ($cFunction in $cPure) {
 Assert-C ($cDoc.Contains($cFunction.Extent.Text)) ('unchanged_'+$cFunction.Name)
 . ([scriptblock]::Create($cFunction.Extent.Text))
}
$cBase=@{ProcessId=20;ParentId=10;StartMs=1003L;NativeImage=$cConhost;NativeVerified=$true;HashVerified=$true}
foreach ($cCase in @(
 @(@{},'application','host'),
 @(@{StartMs=998L},'application','stale'),
 @(@{StartMs=999L},'application','ambiguous'),
 @(@{StartMs=1000L},'application','ambiguous'),
 @(@{StartMs=1001L},'application','ambiguous'),
 @(@{StartMs=1002L},'application','host'),
 @(@{StartMs=$null},'application','ambiguous'),
 @(@{ParentId=99},'application','ambiguous'),
 @(@{ProcessId=0},'application','ambiguous'),
 @(@{ProcessId=10},'application','ambiguous'),
 @(@{NativeImage='helper.exe'},'application','unexpected'),
 @(@{NativeVerified=$false},'application','ambiguous'),
 @(@{HashVerified=$false},'application','ambiguous'),
 @(@{},'host','unexpected'),
 @(@{StartMs=998L},'host','stale')
)) { $cCandidate=$cBase.Clone(); foreach ($k in $cCase[0].Keys) {$cCandidate[$k]=$cCase[0][$k]}; Assert-C ((Get-CRelation 10 1000 $cCase[1] $cCandidate) -eq $cCase[2]) 'relation' }
foreach ($cCase in @(
 @(@(),'application',$null),@(@('host'),'application',$null),
 @(@('stale','host'),'application',$null),@(@('stale','stale'),'host',$null),
 @(@('host','host'),'application','descendant_count'),
 @(@('unexpected'),'application','unexpected_or_ambiguous_descendant'),
 @(@('ambiguous'),'application','unexpected_or_ambiguous_descendant'),
 @(@('host'),'host','descendant_count')
)) { Assert-C ((Get-CShapeFailure -Relations $cCase[0] -ParentRole $cCase[1]) -eq $cCase[2]) 'shape' }
foreach ($cCase in @(@($null,$null),@('primary',$null),@($null,'cleanup'),@('primary','cleanup'))) {
 $cBoth=Join-CFailures $cCase[0] $cCase[1]
 Assert-C ($cBoth.primary -eq [string]$cCase[0] -and $cBoth.cleanup -eq [string]$cCase[1]) 'failures'
}
foreach ($cCase in @(@(0,$null,0),@(5,$null,5),@(0,@{Length=9},9),@(10,@{Length=9},10),@(2,@{Length=14},14))) {
 Assert-C ((Get-CAccountedLength $cCase[0] $cCase[1]) -eq $cCase[2]) 'accounting'
}
Assert-C ($cRunner.Contains('$cState.PeakProcesses=1')) 'known_root_peak'
Assert-C ($cRunner.Contains('$cLiveHosts -gt 1') -and $cRunner.Contains('-gt 2 -or')) 'process_limits'
Assert-C ($cRunner.IndexOf('$cHostRecord.Handle.Kill()') -lt $cRunner.IndexOf('$cProcess.Kill()')) 'leaf_before_root'
$cNameGate=@($cAst.EndBlock.Statements | Where-Object {$_.Extent.Text.StartsWith('if ($cCheckName -notmatch')})[0].Extent.Text
$cTargetStmt=@($cAst.EndBlock.Statements | Where-Object {$_.Extent.Text.StartsWith('$cTargets=')})[0].Extent.Text
$cArgStmt=@($cAst.EndBlock.Statements | Where-Object {$_.Extent.Text.StartsWith('$cExpectedArgs =')})[0].Extent.Text
$cArgGate=@($cAst.EndBlock.Statements | Where-Object {$_.Extent.Text.StartsWith('if (($cExpectedArgs')})[0].Extent.Text
$cRoot='C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp5-tests-20260828-01'
. ([scriptblock]::Create($cTargetStmt))
Assert-C ($cTargets.Count -eq 6) 'six_targets'
foreach ($cCheckName in @('pytest-1','pytest-6','ruff-lint-1','ruff-lint-6','ruff-format-1','ruff-format-6','ruff-formatcheck-1','ruff-formatcheck-6','mypy-1','mypy-6')) {
 . ([scriptblock]::Create($cNameGate))
 $cPytest=$cCheckName.StartsWith('pytest-')
 . ([scriptblock]::Create($cArgStmt))
 $cCheckArgs=$cExpectedArgs
 . ([scriptblock]::Create($cArgGate))
 Assert-C ($true) 'allowed_exact_args'
}
foreach ($cCheckName in @('pytest-0','pytest-7','ruff-check-1','ruff-lint-7','mypy-0','mypy-7','pytest-1.extra')) {
 $rejected=$false; try {. ([scriptblock]::Create($cNameGate))}catch{$rejected=$true}
 Assert-C $rejected 'rejected_name'
}
$cCheckName='pytest-1'; $cPytest=$true
. ([scriptblock]::Create($cArgStmt))
Assert-C ($cExpectedArgs.Count -eq 21 -and $cExpectedArgs[-1] -eq 'tests/unit/test_workspace_create_native_adapter.py') 'thirteen_modules'
foreach ($cDamage in @('extra','old-name','old-root','forward-root')) {
 $cCheckArgs=@($cExpectedArgs)
 if ($cDamage -eq 'extra') {$cCheckArgs += '-k'}
 elseif ($cDamage -eq 'old-name') {$cCheckArgs[-1]='tests/integration/test_workspace_create_linkage.py'}
 elseif ($cDamage -eq 'old-root') {$cCheckArgs[7]=$cCheckArgs[7].Replace('wcp5','wcp4')}
 else {$cCheckArgs[7]=$cCheckArgs[7].Replace('\','/')}
 $rejected=$false; try {. ([scriptblock]::Create($cArgGate))}catch{$rejected=$true}
 Assert-C $rejected 'rejected_args'
}
Assert-C ($cRunner.Contains('$cDatabases[$cIteration] -gt 96')) 'database_budget'
Assert-C ($cRunner.Contains('268435456') -and $cRunner.Contains('4194304')) 'byte_budgets'
Assert-C ($cRunner.Contains('300000') -and $cRunner.Contains('1048576') -and $cRunner.Contains('65536')) 'check_budgets'
Assert-C ($cRunner.Contains('e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22')) 'approved_packet_binding'
Assert-C ($cRunner.Contains('6fd2d5a797bb355412ff61ea180c6fb9aa2f038a')) 'checkpoint_binding'
foreach ($cPacket in @(@('CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md','448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c'),@('CRSE_WCP3_TEST_FILENAME_AMENDMENT.md','35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4'),@('CRSE_WCP3_GROUPED_DEVELOPMENT_BATCH.md','4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e'),@('CRSE_WCP4_DURABLE_APPROVAL_BATCH.md','e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22'))) {
 Assert-C ((Get-FileHash -LiteralPath (Join-Path 'C:/Users/brian/Documents/CM_Computation' $cPacket[0])).Hash.ToLowerInvariant() -eq $cPacket[1]) 'raw_packet_identity'
}

$cQualGate=@($cAst.EndBlock.Statements | Where-Object {$_.Extent.Text.StartsWith('if (-not $cQualified.passed')})[0].Extent.Text
$cGood=@{passed=$true;runner_sha256=$cRunnerHash;parent_sha256='448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c';v_sha256='35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4';batch_sha256='4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e';wcp4_sha256='e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22';wcp5_sha256='de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295';checkpoint='6fd2d5a797bb355412ff61ea180c6fb9aa2f038a';root=$cRoot;database_limit=96}
$cQualified=$cGood.Clone()
. ([scriptblock]::Create($cQualGate))
Assert-C $true 'exact_qualification'
foreach ($cKey in $cGood.Keys) {
 $cQualified=$cGood.Clone()
 $cQualified[$cKey]=if ($cKey -eq 'passed') {$false} elseif($cKey -eq 'database_limit') {64} else {'wrong'}
 $rejected=$false;try {. ([scriptblock]::Create($cQualGate))}catch{$rejected=$true}
 Assert-C $rejected ('qualification_'+$cKey)
}

Assert-C ($cRunner.Contains('de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295')) 'wcp5_packet'
Assert-C ($cTargets[0] -eq 'src/fractilate_orchestrator/domain/workspace_create_native.py' -and $cTargets[-1] -eq 'tests/fixtures/workspace_create_linkage/fixture_store.py') 'wcp5_targets'
Assert-C ($cRunner.Contains('$cWcp4Root=''C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp4-tests-20260828-01''')) 'preserved_wcp4_root'
Assert-C ($cRunner.Contains('85b52f7d2f83313cb8d8c7b968960652ad1d41a3e30179ec1d706a09c6bd3b73')) 'preserved_wcp4_qualification'
Assert-C ((Get-FileHash -LiteralPath $cApprovedPath).Hash.ToLowerInvariant() -eq 'de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295') 'wcp5_raw_identity'

```
<!-- END WCP5 QUALIFICATION CASES -->
