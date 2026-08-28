# CRSE-WCP-6: path to an attended native workspace fixture

Revision: 2026-08-28.1. Status: proposed, not approved.

## One decision available now; native launch remains a later decision

Approve Preparation Batch A below: private Windows-backend implementation,
bounded offline runtime inspection, inert adversarial tests and fix/retest,
readiness evidence, one conditional local checkpoint, and preparation of the
exact attended-fixture permit. This includes explicit execution of the fixed
test supervisor and qualification cases printed below; no document reconstructor
needs a separate approval later.

Native Batch B is described to make the complete path and disposable targets
clear. It is NOT authorized by approval of A and is not yet ready for approval.
Its exact implementation checkpoint, actual executable/dependency manifest,
immutable fixture base and independently enforced containment must first exist.
No native fixture, product workspace or production controller is enabled by A.

Continue through all ordinary A steps without asking after each check. Stop for
a changed scope/limit, unresolved identity/resource/closure failure, missing
required evidence, or the actual A-to-B native-effect boundary.

## Starting checkpoint and completed WCP-5

Controller: C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator.

Require exact HEAD 5b7df4d9f17f02abcba959a31b6a42eae15fe163, empty index and clean
tracked files. Its parent is 6fd2d5a797bb355412ff61ea180c6fb9aa2f038a.
The one WCP-5 commit completed: 12 files, 2,882 additions / 3 deletions.
Do not repeat that commit, amend it, or create a documentation-only follow-up.

WCP-5 passed 737 scoped tests without warnings, six-file Ruff lint/format checks
and strict mypy on 90 sources. Its formal fixed-runner qualification passed 89
cases. All nine application checks confirmed closure within limits.
The first test iteration's oversized test-ID setup/teardown errors, initial
typing findings, earlier execution rejection and unsubmitted assembly failure
are retained. A no-start causal/freshness gap found during review has passing
boundary regressions. No native guarantee is established by those passes.

Retained WCP-5 root:
C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp5-tests-20260828-01.
It has 249 files, 92,928,359 bytes, 182 SQLite fixtures (91 per iteration), and
the empty disabled-hooks directory. No old database or root may be reused,
overwritten or cleaned. Formal record SHA-256:
da132f1e01e95691be9b05d6965873eba241ab79f8ade09669a99f90951700cd.
The immutable WCP-5 fixed-runner packet SHA-256 is
e95ad9324681dceae26b3ccb5ba05abdcd2f65d8501af623202e987cd79c1e4a.

The controller index and tracked worktree were independently checked clean after
the commit. The pre-existing untracked coordination/prompts/ remains unread.
Preserve it and every unrelated CM/controller change. No push or hosted CI ran.

## Preparation Batch A: exact write scope

Create these eight files only after independently checking absence:

```text
src/fractilate_orchestrator/domain/workspace_create_attended.py
src/fractilate_orchestrator/adapters/workspace_create_windows.py
src/fractilate_orchestrator/services/attended_workspace_create.py
tests/unit/test_workspace_create_windows.py
tests/unit/test_attended_workspace_create.py
tests/integration/test_attended_workspace_boundary.py
docs/decisions/ADR-0027-attended-native-workspace-fixture.md
coordination/WORKSPACE_CREATE_ATTENDED_READINESS.md
```

Modify these five files only:

```text
tests/fixtures/workspace_create_linkage/fixture_store.py
coordination/WORKSPACE_CREATE_NATIVE_READINESS.md
coordination/PROGRAM_STATUS.md
coordination/plans/ACTIVE_PLAN.md
coordination/NEXT_ACTIONS.md
```

At most 13 files, 6,500 additions and 300 deletions against the exact WCP-5 base.
Count new files by final line count. No rename, delete, broad rewrite or cleanup.
The fixture helper may change ONLY its TEST_ROOT literal to the new A root;
preserve both profile schemas, DDL, receipts/row caps and all other behavior.

Do not edit WCP-5's native domain/adapter/service or its two tests. Their public
native boundary must continue unconditionally rejecting all caller tokens and
their readiness blockers must remain. No modification of old contracts/hash
domains, fake argv, WCP-4 ledger/coordinators, SQL/migrations, dependencies,
configuration, SDKs, CLI/registered entry points or production wiring.
One maintainer, current configured model/effort, concurrency one; no delegation.

### Frozen WCP-5 raw baselines (all twelve are read-only inputs)

Only the five named MODIFY grants above may depart from these bytes in A.

| Controller-relative path | Raw SHA-256 |
| --- | --- |
| coordination/NEXT_ACTIONS.md | a9c4cf49ecd44bb57cd0d218a0aaa386c96ac96a69b4e98c17423a39ec7b45ce |
| coordination/PROGRAM_STATUS.md | b0c07f992df131f8c7fa0cbd6d99e2561481bb62dc866fe3fd89c5516d24a2ec |
| coordination/WORKSPACE_CREATE_APPROVAL_READINESS.md | 2173e80a41ff90fdbc2bcb74001472fa09ffce2216e4129361eb3c49af2a4d61 |
| coordination/WORKSPACE_CREATE_NATIVE_READINESS.md | 527aff9074b3360ba867be4afa4ad35cb947bb4d9e66859da80cd86743e37979 |
| coordination/plans/ACTIVE_PLAN.md | 527ba61c1afd774665e52fc848e973c61ae6646e99ad511d8684fb3660ad50fe |
| docs/decisions/ADR-0026-native-workspace-adapter-rehearsal.md | d217ae62f36e3a3b800f4724c948099447fe4b43fb1a3b03f0a7c06f289b9455 |
| src/fractilate_orchestrator/adapters/workspace_create_native.py | e296d5ee361de12752cef744815fcf24e028269dfc10fc52e83a968ab9831a3d |
| src/fractilate_orchestrator/domain/workspace_create_native.py | a1d260bbdad152751b36978e918aa416175bbeafa15332fd83534917ca04fa09 |
| src/fractilate_orchestrator/services/native_workspace_create.py | 0ca38cf6fa47c3acf621e192c9ee5d6f1bb4f6320cb37400627adf420271a553 |
| tests/fixtures/workspace_create_linkage/fixture_store.py | c43af89edca6187beef4e97eabdc1fddfab32f6eb531106c1db3dfccc40cca19 |
| tests/unit/test_workspace_create_native_adapter.py | 7531ffa1ca5842a3de18453627324b2d98bb42268bdbad98e62dcfa17f45743b |
| tests/unit/test_workspace_create_native_contract.py | 475a0df48b39d3baf3a7db5d5259e8c267db79797709c69d7e03576dfd847348 |

## A implementation and proof requirements

1. Define new bounded, domain-separated attended-fixture preparation and
   prerequisite contracts. Reference exact request/operation/scope and retain
   provenance. A fixture permit is not a real owner approval, production receipt
   or reusable execution capability. Missing trusted effect authority must fail
   closed; no actor string, hash, environment variable, boolean or copied model
   enables an OS call.
2. Implement the Windows-facing primitives privately and lazily, behind a fixed
   private protocol and a closed inert double. Code may be defined in A but no
   actual native adapter operation is invoked. Imports and public preparation
   remain resource-free; there is no CLI, listener, autostart or driver registry.
   Keep the separate WCP-5 public boundary unchanged and disabled.
3. Specify exact ownership/lifetime for file/ancestor/executable handles; stable
   volume/file/final-path identity; absence/race handling; complete content
   scopes; expected new Git metadata versus protected state; private/common Git
   links. If an absence/content guarantee cannot be enforced, return a typed
   blocker. Never promote string equality, a supplied lease or metadata-only hash
   to independently authenticated native evidence.
4. Specify exact image/hash, bounded argv/Windows argument encoding, cwd, cleared
   environment, explicit inherited handle list, null stdin, suspended creation,
   containment before resume and independent egress denial. Include PID plus
   creation identity and handle ownership. Permit only one exact application
   and at most one attributable exact console host, no wrapper or helper.
5. Implement bounded concurrent stdout/stderr drain and shutdown ordering with
   cancellation, backpressure, time/output/process limits, startup partial
   failures, owned leaves before root and confirmed process/stream/reader/handle
   closure. Preserve primary and cleanup failures independently. Unknown
   enforcement, cancellation or closure must block/quarantine, never be assumed.
6. Model consume-before-dispatch and observation-after-stop, including no-start
   causal/freshness bounds. Retain attempt/operation/fence identity, replay
   conflicts, response/commit uncertainty, partial effects and permanent no-retry.
   A may not install persistence or claim a cross-OS exactly-once transaction.
7. Add negative, boundary and import-inertness tests in the three new modules.
   Replace native constructors with rejecting sentinels and use only the closed
   inert double. Test malformed/copied/oversized inputs, policy/identity drift,
   PID reuse, unknown helpers/hosts, handles/startup, both pipes, cancellation,
   stop/close failures, late/conflicting observations and missing native permits.
   The new integration module exercises admission/order only, not a native
   fixture. It must create zero SQLite databases and zero native resources.
8. Add an inert bounded PE-import/dependency-manifest parser if needed for the
   allowed offline inspection below. Malformed/truncated/cyclic/oversized or
   noncanonical import names fail closed. Static imports and binary hashes do not
   prove which modules Windows will actually load or which helpers Git may spawn.
9. Record each missing guarantee explicitly in ADR-0027/readiness. Mock passes,
   offline inspection, the local checkpoint and a fixture permit do not satisfy
   production installation, real owner intake or product execution approval.

Use primary Microsoft Learn Win32 and official Git documentation only for
additional research, without login, downloads, installation or external writes.
ADR-0026's cited references are inputs, not native proof. Keep the distinction
between documented behavior, design choices, observed data and unproven inference.

## A read-only runtime investigation: actual files, no native launch

This is a narrowly scoped exception to the no-native-resource rule for the
trusted maintainer's read-only inspection, NOT for the adapter or new tests.
Do not execute candidate Git images, native APIs through the new adapter,
fixtures, DLL entry points, SDKs, WSL/container/VM tools or installers.

The already measured maintenance image is:
C:/Program Files/Git/cmd/git.exe
SHA-256 c954fcc8e65a38450895ca65d308ecaee63f044d16494b5385faa5e036a3facb.

That hash alone does not prove it is a helper-free workspace launch image.
A may inspect/hash that file and the explicitly named candidate
C:/Program Files/Git/mingw64/bin/git.exe if present. Do not assume equivalence,
copy/replace either image, run --version, or silently switch the launch target.
The final B permit must name the independently selected image and actual hash.

For offline dependency investigation, allow at most 64 distinct PE files,
including the two explicit executables above, 32 MiB per file and 256 MiB total
bytes read. DLL resolution is limited to these exact directories:

```text
C:/Program Files/Git/mingw64/bin
C:/Program Files/Git/usr/bin
C:/Windows/System32
```

Only the two explicit Git executables above and DLL basenames obtained from their
bounded import/forwarder graph are eligible. Resolve only simple ASCII basenames
ending .dll in those directories, reject separators/colon/dot segments/aliases,
check non-reparse ancestors and files, and never follow links outside them.
No recursive directory/content scan, DLL load or configuration/credential read.
API-set names, unresolved imports, dynamic loads, alternate search paths,
architecture mismatch or runtime helpers remain blockers, not guessed resolutions.
Do not treat a static graph as a complete loaded-runtime manifest.

Read-only OS version/architecture and current administrator-eligibility booleans
may be collected; no account identifiers, token data or security policy contents.
Do not create/modify firewall/WFP rules, ACLs, privileges, services, scheduled jobs,
VM/container settings, registry or machine security policy. If enforcement requires
such changes, prepare a concrete separate decision; do not elevate or improvise.

At most four parent-only runtime-inspection attempts: <=60 seconds each, no child,
create-new runtime-manifest-N.json (N=1..4) within A's root, <=64 KiB per record
and combined output/evidence per attempt. Record exact files/hashes, missing
dependencies and limitations. Retain failures; no overwrite. A positive offline
manifest cannot itself open the B native gate.

## A read-only source and evidence inputs

Read applicable AGENTS.md, all thirteen write targets/absence checks, all twelve
WCP-5 baselines, ADR-0021 through ADR-0026, and current status/plan/next/readiness
records. Read the immutable WCP-5 packets, their named parent packets and exact
historical qualification/result logs. Do not evaluate a parent reconstructor.

Additional source-only inputs are the existing workspace-create contracts,
intents, services, journal/linkage/approval persistence and fake coordinators;
the sixteen exact test modules below, fixture helper, tests/conftest.py,
tests/helpers.py and pyproject.toml. Installed dependency source may be read by
the scoped static/tests. No secrets, .env files, credentials, key/token stores,
user configuration, production/local databases or unrelated diffs.

Metadata-only checks of the A root/ancestors and exact proposed B paths are
allowed. No B creation/content inspection or real product observation is included.

## A root, checks and finite budget

Proposed new A root (not yet created or observed for this proposal):
C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6-tests-20260828-01.

Check absence and non-reparse ancestors, then create it once. Retain all evidence.
Only the helper's root literal may move. Six distinct pytest-N basetemps and one
mypy cache belong inside this root. Do not reuse old fixtures or clean anything.

Per-root budgets: parent preflight 10; formal qualification 5; pytest 6;
Ruff lint/formatter/format-check 6 each; mypy 6. Parent preflight/qualification
<=30 seconds/4 KiB, no application/DB. Runtime inspection has its separate four
bounded parent-only slots above. New fixture DB limits remain 96 per pytest
iteration, 4 MiB each and 256 MiB aggregate root, with DELETE/FULL,
foreign_keys ON, memory temp, <=1,000 ms busy timeout and journal headroom.

Application checks remain <=300 seconds, 1 MiB combined output/evidence, bounded
pipe buffers and 4 KiB metadata frames/64 KiB metadata, one application plus at
most one attributable exact console host (two OS processes), no helper.
Use the fixed supervisor below; preserve its actual buffers, accounting,
identity checks, concurrent draining, error retention and owned shutdown.
All qualification/assertion and real application failures remain recorded.

Revalidate these six WCP-5 identities before work and again at the applicable
launch/commit boundary:

| Runtime or binding | Raw SHA-256 |
| --- | --- |
| C:/Users/brian/AppData/Local/Programs/Python/Python310/python.exe | 3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260 |
| C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/python.exe | b2c836c52cdf063180b9ee76f67ac42946101b79ac457f3494035a67c090d961 |
| C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/pyvenv.cfg | efe9c8f26884c6ac39ebb57a9f1215a539a423feaf12fe5eec753e28dcef3a55 |
| C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/ruff.exe | 0cf602e931f311581bce0b1dfc8d5e30717d96af54c65d7b89a9a8d4497b0eeb |
| C:/Windows/System32/conhost.exe | b02ee54fb2ec69673386d41119ee8ed083a6eab3bfca6aa2155d20ce68ef8963 |
| C:/Program Files/Git/cmd/git.exe | c954fcc8e65a38450895ca65d308ecaee63f044d16494b5385faa5e036a3facb |

Only direct base Python or the exact Ruff image launches for checks. The venv
Python path is a binding, not a launcher. Inherit only SYSTEMROOT/WINDIR, set
TEMP/TMP to A's root, PYTHONDONTWRITEBYTECODE=1,
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONHASHSEED=0, PYTHONUTF8=1,
PYTHONIOENCODING=utf-8 and PYTHONNOUSERSITE=1. Only Python gets the fixed
__PYVENV_LAUNCHER__ binding. No PATH fallback, installation or credential
inheritance. Conhost may be observed as an OS-created child, never invoked.

Python: -B -m pytest -q -p no:cacheprovider --basetemp <A-root>/pytest-N,
then exactly these sixteen modules in this order:

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
tests/unit/test_workspace_create_approval_contract.py
tests/integration/test_approved_linked_workspace_create.py
tests/unit/test_workspace_create_native_contract.py
tests/unit/test_workspace_create_native_adapter.py
tests/unit/test_workspace_create_windows.py
tests/unit/test_attended_workspace_create.py
tests/integration/test_attended_workspace_boundary.py
```

Ruff: check --no-cache, format --no-cache, or format --check --no-cache,
then exactly these seven paths in this order:

```text
src/fractilate_orchestrator/domain/workspace_create_attended.py
src/fractilate_orchestrator/adapters/workspace_create_windows.py
src/fractilate_orchestrator/services/attended_workspace_create.py
tests/unit/test_workspace_create_windows.py
tests/unit/test_attended_workspace_create.py
tests/integration/test_attended_workspace_boundary.py
tests/fixtures/workspace_create_linkage/fixture_store.py
```

Mypy: direct Python -B -m mypy --cache-dir <A-root>/mypy with the existing strict
configuration. Use Join-Path Windows spelling for absolute cache/basetemp argv.
No extra module, -k, plugin, full suite, coverage, package build, native test or CI.

## A fixed-code execution authorization and qualification

Approval of A expressly authorizes extracting and executing ONLY the exact
supervisor and bounded qualification fences below after raw packet and body
hash verification. It does not authorize executing any prose, reconstructor,
observation-supplied expression, callback or arbitrary document script.

Supervisor normalized UTF-8 SHA-256:
2f511fd052aaefd9d648827bb7a0db8c93c2daf1e2c1d714d1d74a7666102d38.
Qualification-case normalized UTF-8 SHA-256:
3becc228434a2bd1f362303a0bd4db63fc52c842574da6462ffb933a34cb85d3.
Document-generation data-only QA passed: both complete fences parse, all four
pure function definitions match WCP-5 bytes, and each target/argv/qualification
gate occurs once. No body or qualification case executed, no WCP-6 root was
created and no native effect occurred. This is not formal qualification or a
WCP-6 test result; all future A/B work remains unapproved.

The complete packet raw SHA-256 is supplied separately with the approval request.
The trusted parent must pin that owner-approved hash BEFORE reading executable
fences, verify it independently, then set cApprovedPacketHash to that pinned
literal. Never accept a newly observed document hash as its own authorization.
This external binding avoids a self-referential packet hash inside its own body.

Set cRunnerHash only after hashing the normalized complete supervisor body.
Parse complete AST boundaries; require the four pure classifier/error/accounting
definitions byte-identical to WCP-5 and its WCP-3 reference. Treat cDoc as the
unchanged WCP-3 amendment TEXT, never execute its reconstructor. For the
qualification cases, cWcp5ApprovedPath is the original immutable WCP-5 packet.

Before a formal attempt, validate the exact absent
<A-root>/supervisor-selfcheck-N.json name (N=1..5) independently. Use a new record
and a bounded writer; never globally replace historical filenames. Run every
prior 89-case qualification check and the new bindings printed below. Record
actual assertion count, timing, all historical packet hashes, wcp6_sha256,
runner/case hashes, checkpoint, root, exact sixteen/seven target arrays,
database_limit=96 and output filename. No child/DB is part of qualification.
Bind and recheck the actual passing record's raw hash before EVERY application.

For an application, supply only the approved cCheckName/cCheckArgs,
cQualificationName, cRunnerHash and owner-pinned cApprovedPacketHash to this
exact supervisor. A passed qualification is mandatory; ordinary test/lint/type
findings may be corrected within scope/remaining slots. Actual process, identity,
resource or closure violations stop further applications pending a new decision.

## A completion and one conditional local checkpoint

Require the full sixteen-module matrix, seven-path Ruff lint/format-check and
strict mypy green after corrections; zero real native/resource calls from the
new tests; immutable evidence; actual runtime findings and blockers documented;
in-scope diff; no unresolved supervision failure; and unrelated files unchanged.

Freeze the eight creates plus only changed granted files, at most thirteen, by
raw SHA-256 and normalized Git blob. Require the exact WCP-5 base and empty index.
Create once the absent empty <A-root>/disabled-hooks directory. Use only the exact
maintenance Git executable, no pager, core.hooksPath set to that directory,
core.fsmonitor=false, gc.auto=0, maintenance.auto=false, commit.gpgsign=false,
and no external diff/textconv. Existing author identity may resolve normally;
do not inspect/change configuration or use native B candidates for maintenance.

At most one explicit staging operation and one conditional local commit,
<=60 seconds/64 KiB output each. Message:
Add guarded Windows workspace fixture backend

Verify exact base/index/raw files before commit and its direct parent, frozen
paths/blobs, empty index and clean tracked worktree afterward. No second commit,
amend, reset, unstage, blind retry, push or CM commit. Put the exact SHA in the
handoff, not a documentation-only follow-up commit.

Then prepare the exact Batch B permit with observed facts. Do not invoke B.
If any native guarantee remains missing, report it and scope its resolution;
do not describe a blocked fixture run as ready for approval.

## Native Batch B outline — NOT an execution grant

The following are exact proposed disposable targets, not claims they exist or
that they are safe. They must be checked absent/non-reparse before any later
separately approved creation:

```text
Session root: C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6-native-20260828-01
Toy source: C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6-native-20260828-01/source
Allowed workspace parent: C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6-native-20260828-01/workspaces
Exact workspace: C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6-native-20260828-01/workspaces/fixture-one
Scratch: C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6-native-20260828-01/scratch
Evidence: C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6-native-20260828-01/evidence
Exact fixture branch: codex/crse-wcp6-fixture-one
```

The controller and C:/Users/brian/Documents/CM_Computation are protected roots,
never source/workspace/temporary targets. Real product paths are out of scope.

The later B permit must bind, before approval:

- Actual tested native implementation checkpoint and exact private attended
  invocation/harness hash; no public dispatch bypass or synthetic-to-real grant.
- Exact selected Git executable and complete observed runtime/helper/DLL closure,
  support/architecture and child policy, not just the cmd/git.exe hash or a static
  import graph. Unknown or unsupported closure blocks, without install/fallback.
- Two tiny synthetic source files with exact bytes, deterministic Git author/
  committer metadata, tree and immutable base SHA, plus exact init/add/commit
  argv and empty template/hooks/config inputs. No network, signing, filter,
  submodule, external template, original repo or real controller database.
- Independently established process/egress enforcement and stable path/absence/
  content identity. Command flags and policy booleans cannot substitute. If
  privilege or machine-wide policy is required, it needs its own concrete owner
  decision before B can be eligible; none is approved here.
- Every inherited handle, environment value, launch command, intended effect,
  expected Git/worktree delta and observation recipe. No ambient discovery.
- A single attended session, proposed ceiling 12 exact process-start attempts,
  at most one actual worktree-add attempt, one application plus one exact host
  concurrently, <=30 seconds per application and <=600 seconds session,
  <=1 MiB combined output/evidence and <=64 MiB session root. These are proposed
  ceilings, not permission to run twelve arbitrary commands.
- Benign fixed-code pipe/cancellation/stop/containment probes with exact image/
  argv/hash and owned resources, then the one toy workspace effect only if every
  prerequisite passes. Synthetic negative cases do not substitute for native
  enforcement evidence. Never retry an uncertain workspace effect.
- Owned leaf-before-root stop, confirmed exits and closed streams/readers/handles,
  immutable pre/post Git/content observations, residual inventory and conservative
  quarantine. Keep both primary and cleanup errors. No unowned termination.
- No automatic/manual deletion or recursive cleanup: retain the disposable tree,
  incomplete effects and evidence. Any later cleanup names exact targets in a
  new decision. Persistent controls/resources may not be left unexplained.

B can only demonstrate this tightly scoped disposable fixture. It still cannot
authenticate a real product owner's decision, install a production controller,
prove cross-OS exactly-once execution, or approve the product pilot.

## Explicit exclusions and A approval wording

No A native API/workspace/Git fixture call, real product observation, worker/
verifier, SDK/authentication, owner capture, production/local DB read/install/
migration, listener, network outside primary-document reads, deployment, merge,
publication/CI, paid fallback, cleanup, delegation or system-security change.

Original product decisions 1-5 remain bound only to plan
3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373
and bundle a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815.
Execution of workspace.create/v1 remains unapproved.

> I approve Preparation Batch A of CRSE-WCP-6 revision 2026-08-28.1,
> bound to the supplied raw packet, fixed-supervisor and qualification hashes:
> the thirteen-file private implementation, bounded offline runtime inspection,
> new A evidence root, exact inert checks including execution of the printed
> fixed PowerShell supervisor/qualification, scoped fixes/rechecks and one
> conditional local checkpoint, followed by preparation of the exact B permit.
> I do not approve Native Batch B, native fixture/product effects, real owner
> intake, production installation, system-security changes, publication or cleanup.

## Exact fixed A supervisor (data until A is approved)

<!-- BEGIN FIXED WCP6 SUPERVISOR -->
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
if ($cApprovedPacketHash -notmatch '^[0-9a-f]{64}$') { throw 'missing_owner_pinned_wcp6_hash' }
$cRoot = 'C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp6-tests-20260828-01'
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
 @('CRSE_WCP5_NATIVE_ADAPTER_BATCH.md','de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295'),
 @('CRSE_WCP6_ATTENDED_NATIVE_FIXTURE_PROPOSAL.md',$cApprovedPacketHash)
)) { if ((Get-FileHash -LiteralPath (Join-Path 'C:\Users\brian\Documents\CM_Computation' $cPacket[0])).Hash.ToLowerInvariant() -ne $cPacket[1]) { throw 'packet_drift' } }
$cHeadText=[IO.File]::ReadAllText((Join-Path $cRepo '.git\HEAD')).Trim()
if ($cHeadText.StartsWith('ref: refs/heads/')) { $cHeadText=[IO.File]::ReadAllText((Join-Path $cRepo ('.git\'+$cHeadText.Substring(5)))).Trim() }
if ($cHeadText -cne '5b7df4d9f17f02abcba959a31b6a42eae15fe163') { throw 'checkpoint_drift' }
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
$cWcp5Root='C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp5-tests-20260828-01'
foreach ($cOriginal in @(
 @('mypy-1.result.json','213a3c06273a13dc4ec57ca7e3fcd695806cdad0ffd906474d378be77165858d'),
 @('mypy-2.result.json','73147ebe6cd867fb31bb589dd9edd34f40c4e52020de7f8b230ac668ae9390df'),
 @('preflight-1.json','6c10051823d06a95e83183c2c9103de34b26e33ebeee3c89af79b056cfe5b62c'),
 @('preflight-2.json','093e263322af706addd0415caad84023967e8c025dfe29895e38e5c59a232971'),
 @('preflight-3.json','3b5b678304abfff94abc57545b7452a83ab96303fc5172b6fe3b433c4a6bdeb9'),
 @('pytest-1.result.json','6dd9729fc48d3bfc148de866589457c63777610a314377f8feccac05ad8a836b'),
 @('pytest-2.result.json','08e0ad099a4704630721b093947246fadd20a0bb215a19e3bdd0514f623a220a'),
 @('ruff-format-1.result.json','12fac37ab54603bd7b59db834b754d64d3a961c8e45ea14d390db5f1f2a1a6bd'),
 @('ruff-format-2.result.json','62f9afc0ddeeacf9e48bad5eb33f8ec3f8afabe3e46dde6c6d32fdd85cd42b78'),
 @('ruff-formatcheck-1.result.json','23cb8c420e9b0b1ffcb567b3d040eb39066f386438217b08d054976d99611b60'),
 @('ruff-lint-1.result.json','f0cdb5ca01f03b1be431690defde2f838a4242a8f9f56e36d5aa60874913cf29'),
 @('ruff-lint-2.result.json','db8e7bb7ca3d0175966142f407d9814c444bfa572acfedee9c88f2eba43b9ea0'),
 @('supervisor-selfcheck-1.json','da132f1e01e95691be9b05d6965873eba241ab79f8ade09669a99f90951700cd')
)) { if ((Get-FileHash -LiteralPath (Join-Path $cWcp5Root $cOriginal[0])).Hash.ToLowerInvariant() -ne $cOriginal[1]) { throw 'wcp5_evidence_drift' } }
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cWcp5Root -File -Filter '*.result.json')) {
 $cPrior=Read-CMetadata -Path $cPriorFile.FullName
 if (-not $cPrior.eligible -or $cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw 'wcp5_check_stop' }
}
if ($cQualificationName -notmatch '^supervisor-selfcheck-[1-5]\.json$') { throw 'qualification_name' }
$cQualified=Read-CMetadata -Path (Join-Path $cRoot $cQualificationName)
if (-not $cQualified.passed -or $cQualified.runner_sha256 -ne $cRunnerHash -or $cQualified.parent_sha256 -ne '448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c' -or $cQualified.v_sha256 -ne '35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4' -or $cQualified.batch_sha256 -ne '4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e' -or $cQualified.wcp4_sha256 -ne 'e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22' -or $cQualified.wcp5_sha256 -ne 'de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295' -or $cQualified.wcp6_sha256 -ne $cApprovedPacketHash -or $cQualified.checkpoint -ne '5b7df4d9f17f02abcba959a31b6a42eae15fe163' -or $cQualified.root -ne $cRoot -or $cQualified.database_limit -ne 96) { throw 'wcp6_qualification_binding' }
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cOldRoot -File -Filter '*.result.json')) {
 $cPrior=Read-CMetadata -Path $cPriorFile.FullName
 if (-not $cPrior.eligible -or $cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw 'old_check_stop' }
}
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cRoot -File -Filter '*.result.json')) {
 $cPrior = Read-CMetadata -Path $cPriorFile.FullName
 if (-not $cPrior.eligible -or $cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw 'prior_check_stop' }
}
$cTargets=@('src/fractilate_orchestrator/domain/workspace_create_attended.py','src/fractilate_orchestrator/adapters/workspace_create_windows.py','src/fractilate_orchestrator/services/attended_workspace_create.py','tests/unit/test_workspace_create_windows.py','tests/unit/test_attended_workspace_create.py','tests/integration/test_attended_workspace_boundary.py','tests/fixtures/workspace_create_linkage/fixture_store.py')
$cExpectedArgs = if ($cCheckName -like 'ruff-lint-*') { @('check','--no-cache') + $cTargets }
 elseif ($cCheckName -like 'ruff-formatcheck-*') { @('format','--check','--no-cache') + $cTargets }
 elseif ($cCheckName -like 'ruff-format-*') { @('format','--no-cache') + $cTargets }
 elseif ($cPytest) { @('-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp',(Join-Path $cRoot $cCheckName)) + @('tests/unit/test_workspace_create_contract.py','tests/unit/test_workspace_create_intents.py','tests/unit/test_workspace_create_recovery.py','tests/unit/test_workspaces.py','tests/unit/test_product_pilot.py','tests/unit/test_external_operations.py','tests/unit/test_workspace_create_journal_contract.py','tests/unit/test_workspace_create_linkage.py','tests/integration/test_linked_workspace_create.py','tests/unit/test_workspace_create_approval_contract.py','tests/integration/test_approved_linked_workspace_create.py','tests/unit/test_workspace_create_native_contract.py','tests/unit/test_workspace_create_native_adapter.py','tests/unit/test_workspace_create_windows.py','tests/unit/test_attended_workspace_create.py','tests/integration/test_attended_workspace_boundary.py') }
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
<!-- END FIXED WCP6 SUPERVISOR -->

## Exact bounded A qualification cases (data until A is approved)

<!-- BEGIN WCP6 QUALIFICATION CASES -->
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
$cRoot='C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp6-tests-20260828-01'
. ([scriptblock]::Create($cTargetStmt))
Assert-C ($cTargets.Count -eq 7) 'seven_targets'
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
Assert-C ($cExpectedArgs.Count -eq 24 -and $cExpectedArgs[-1] -eq 'tests/integration/test_attended_workspace_boundary.py') 'sixteen_modules'
foreach ($cDamage in @('extra','old-name','old-root','forward-root')) {
 $cCheckArgs=@($cExpectedArgs)
 if ($cDamage -eq 'extra') {$cCheckArgs += '-k'}
 elseif ($cDamage -eq 'old-name') {$cCheckArgs[-1]='tests/integration/test_workspace_create_linkage.py'}
 elseif ($cDamage -eq 'old-root') {$cCheckArgs[7]=$cCheckArgs[7].Replace('wcp6','wcp5')}
 else {$cCheckArgs[7]=$cCheckArgs[7].Replace('\','/')}
 $rejected=$false; try {. ([scriptblock]::Create($cArgGate))}catch{$rejected=$true}
 Assert-C $rejected 'rejected_args'
}
Assert-C ($cRunner.Contains('$cDatabases[$cIteration] -gt 96')) 'database_budget'
Assert-C ($cRunner.Contains('268435456') -and $cRunner.Contains('4194304')) 'byte_budgets'
Assert-C ($cRunner.Contains('300000') -and $cRunner.Contains('1048576') -and $cRunner.Contains('65536')) 'check_budgets'
Assert-C ($cRunner.Contains('e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22')) 'approved_packet_binding'
Assert-C ($cRunner.Contains('5b7df4d9f17f02abcba959a31b6a42eae15fe163')) 'checkpoint_binding'
foreach ($cPacket in @(@('CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md','448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c'),@('CRSE_WCP3_TEST_FILENAME_AMENDMENT.md','35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4'),@('CRSE_WCP3_GROUPED_DEVELOPMENT_BATCH.md','4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e'),@('CRSE_WCP4_DURABLE_APPROVAL_BATCH.md','e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22'))) {
 Assert-C ((Get-FileHash -LiteralPath (Join-Path 'C:/Users/brian/Documents/CM_Computation' $cPacket[0])).Hash.ToLowerInvariant() -eq $cPacket[1]) 'raw_packet_identity'
}

$cQualGate=@($cAst.EndBlock.Statements | Where-Object {$_.Extent.Text.StartsWith('if (-not $cQualified.passed')})[0].Extent.Text
$cGood=@{passed=$true;runner_sha256=$cRunnerHash;parent_sha256='448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c';v_sha256='35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4';batch_sha256='4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e';wcp4_sha256='e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22';wcp5_sha256='de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295';wcp6_sha256=$cApprovedPacketHash;checkpoint='5b7df4d9f17f02abcba959a31b6a42eae15fe163';root=$cRoot;database_limit=96}
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
Assert-C ($cTargets[0] -eq 'src/fractilate_orchestrator/domain/workspace_create_attended.py' -and $cTargets[-1] -eq 'tests/fixtures/workspace_create_linkage/fixture_store.py') 'wcp6_targets'
Assert-C ($cRunner.Contains('$cWcp4Root=''C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp4-tests-20260828-01''')) 'preserved_wcp4_root'
Assert-C ($cRunner.Contains('85b52f7d2f83313cb8d8c7b968960652ad1d41a3e30179ec1d706a09c6bd3b73')) 'preserved_wcp4_qualification'
Assert-C ((Get-FileHash -LiteralPath $cWcp5ApprovedPath).Hash.ToLowerInvariant() -eq 'de6abfd3917f6bfefdd9ed95d663fea7210786c67a4fdf3cf08757783c838295') 'wcp5_raw_identity'

Assert-C ($cRunner.Contains('$cWcp5Root=''C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp5-tests-20260828-01''')) 'preserved_wcp5_root'
Assert-C ((Get-FileHash -LiteralPath 'C:/Users/brian/Documents/CM_Computation/CRSE_WCP6_ATTENDED_NATIVE_FIXTURE_PROPOSAL.md').Hash.ToLowerInvariant() -eq $cApprovedPacketHash) 'wcp6_raw_identity'
```
<!-- END WCP6 QUALIFICATION CASES -->
