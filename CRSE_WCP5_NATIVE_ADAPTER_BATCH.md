# CRSE-WCP-5: grouped native-adapter development and inert verification

Revision: **2026-08-28.1**. Status: **proposed; not approved**.

## One requested approval

Approve one bounded development batch: implement a private native workspace-adapter
boundary and deterministic native-operation state machine, verify it using inert
host/process doubles plus the full prior matrix, correct/retest within the limits,
record evidence, and make one conditional local controller checkpoint after all
gates pass.

**This does not authorize running native workspace code or Git against any product
or disposable repository.** It develops the next prerequisite; actual attended
native fixture proof, real owner-input capture, production installation and product
effects remain later, separate decisions. No fixture approval is real authority.

This groups implementation, foreseeable corrections, verification and the local
checkpoint. Continue through these authorized steps without routine intermediate
approval requests. Stop for genuinely new authority, exhausted limits, a material
design conflict or an actual supervisory violation.

## Starting checkpoint and preserved evidence

Controller: `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.

Require exact HEAD **`6fd2d5a797bb355412ff61ea180c6fb9aa2f038a`**, empty index and no tracked drift.
Its parent is `24ab153f3381c4b882127175728082d864aeff08`. WCP-4's single approved
local commit completed with exactly fourteen files, **2,581 additions / 34 deletions**.
Do not repeat that commit or edit its records to insert its resulting SHA.

WCP-4 passed **436 tests**, eight-file Ruff lint/format checks and strict mypy on
87 sources. The first pytest run had 434 passes and two failures: a typed test
construction error and a real caught-legacy-rejection rollback gap. Both corrections
are covered by the final pass. Lint/type findings and a parent-only qualification
evidence-name failure are retained. The original qualification file was not overwritten.
Final qualification passed 83 cases. All nine application checks closed within limits.

The WCP-4 root retains 249 files, 91,761,444 bytes and 181 synthetic databases
(90 / 91 across two iterations), plus the empty disabled-hooks directory.
No cleanup or database reuse is included. Its final qualification record is
`supervisor-selfcheck-3.json`, raw SHA-256
`85b52f7d2f83313cb8d8c7b968960652ad1d41a3e30179ec1d706a09c6bd3b73`.
The final runner normalized UTF-8 hash is
`fd20941342f5501683e01170bda8d4b43a5d09b991014821023a0d612fb32127`.
The earlier qualified runner and all per-check hashes remain in
`coordination/WORKSPACE_CREATE_APPROVAL_READINESS.md`.

This is local fixture evidence, not hosted CI or native readiness. Preserve
untracked `coordination/prompts/` unread and all unrelated CM/controller work.

## Why this slice

The durable decision/claim/dispatch ordering is now rehearsed. The actual native
boundary is still missing: synthetic path strings, supplied identity facts and
Git policy booleans cannot establish live filesystem identity, stable containment,
safe process creation, complete output accounting or stopped-tree evidence.

Develop that boundary privately, with a complete inert failure matrix, before
requesting an attended native run. Keep this distinct from real owner-intake and
production database work. Do not imply that this batch will produce a usable
production executor, or that passing mocks proves Windows/Git behavior.

## Exact twelve-file write grant

Create these seven files, currently absent; recheck absence before writing:

```text
src/fractilate_orchestrator/domain/workspace_create_native.py
src/fractilate_orchestrator/adapters/workspace_create_native.py
src/fractilate_orchestrator/services/native_workspace_create.py
tests/unit/test_workspace_create_native_contract.py
tests/unit/test_workspace_create_native_adapter.py
docs/decisions/ADR-0026-native-workspace-adapter-rehearsal.md
coordination/WORKSPACE_CREATE_NATIVE_READINESS.md
```

Modify only these five existing files, requiring the following starting raw hashes:

| Controller-relative path | Raw SHA-256 |
| --- | --- |
| `tests/fixtures/workspace_create_linkage/fixture_store.py` | `a740fc2d2cc2a8dc285e51a9bac33a3a5f18e7c90901b75ba8eb59bf342852fc` |
| `coordination/WORKSPACE_CREATE_APPROVAL_READINESS.md` | `e84cd1f2b37c1aab4d4b4c61bf0cb2e186f7bdc18c96102d1bcb15bf09fd2363` |
| `coordination/PROGRAM_STATUS.md` | `f9d10f6e99065a2c12b97703b234b3613f121c8420dba4c1024cffd98bfa15a2` |
| `coordination/plans/ACTIVE_PLAN.md` | `d6147acfd4ac38052461c06c2ceb988e28fd2fdf48480aa09ad7481bcd4741c4` |
| `coordination/NEXT_ACTIONS.md` | `ccf2b6b7f90d088363566205d46bceb13fc737a4902455f75cd6038f62d35865` |

At most **12 files, 5,000 additions and 300 deletions** against the exact starting
checkpoint. Count the seven new files by final line count. No whole-file deletion,
rename or move. Preserve historical evidence. Only the helper's literal test root
may change in its existing behavior; its two profile schemas and current limits
must remain unchanged. Do not weaken or edit existing test modules or runtime
guards to get green results.

No modification of old v1 contracts/hash domains/false flags, the WCP-4 ledger or
coordinator, numbered SQL, migrations, schema registration, dependency/configuration
files, entry points or production wiring. All seven new files are deliverables;
existing records change only as needed. One maintainer, configured model/effort,
concurrency one. No delegation, SDK, product worker or extra helper.

## Required implementation

### New contracts, not retroactive authority

Define a strict, bounded, domain-separated native preparation/observation contract
which references the full retained request, envelope, operation and exact decision
subject. Preserve the distinction between synthetic inputs, a native *proposal*,
independently observed native evidence and actual execution authority.

A WCP-4 synthetic grant/capability must be rejected at a native-dispatch boundary.
No constructor default, actor string, hash, old decisions 1-5, maintenance approval,
test pass or local commit may mint real effect authority. Real owner authentication
and a real controller installation do not exist yet and must remain explicit blockers.
Do not add a permissive native fallback to either existing fake coordinator.

The public service is a preparation/readiness boundary with no registered launch
entry point and no mechanism to mint a usable real execution capability. It must
fail closed on the missing production/native prerequisites. A fully implemented
OS-facing code path may be defined privately but must not be invoked in this batch.

Use a new contract for any native argv or environment requirements; do not change
the old fake command intent's v1 bytes. Bind exact executable/hash, cwd/argv,
environment names and values where appropriate, allowed handles, controller/
source/target/forbidden roots, immutable base, exact branch and request scope.
Bound numbers, strings, bytes, collections and state history before materialization;
reject bool-as-int, duplicate keys, copied-model drift, nonfinite clocks, path aliases,
unknown fields and invalid time order. Keep diagnostics bounded and content-minimal.

### Native boundary and deterministic state machine

Use primary Microsoft/Git documentation to design and implement the boundary.
Keep OS calls lazy and imports inert. Isolate the OS-facing implementation behind
a fixed private protocol so tests can use a closed inert double; do not introduce
a caller-controlled validation bypass or arbitrary callback/driver registration.

Cover, in appropriate order:

1. Exact preflight binding and freshness; source/parent/target/executable identities;
   reparse/alias rejection; immutable base and branch/target absence.
2. Explicit handle ownership and lifetime; race detection across validation and use;
   complete required content scopes and expected new Git metadata distinguished
   from protected source state.
3. Shell-free bounded process creation, cleared environment, disabled inherited
   handles except an exact allowlist, null/closed stdin, disabled helpers/hooks/
   signing/filters/maintenance, and explicit network/egress limitations.
4. Application versus console-host identity/counts; PID **and** creation identity;
   no launcher-wrapper assumption; no unowned process termination. A policy flag
   is not proof of containment. Unknown/unsupported containment must block.
5. Concurrent bounded pipe draining, wall/output/process limits, cancellation,
   known-owned leaf-before-root shutdown, confirmed exits and closed streams.
6. Post-create identity and expected Git delta, immutable retained observations,
   uncertain/partial/no-start/timeout/response-loss outcomes and quarantine.
7. Durable decision consumption before any future effect, observation afterward,
   and no retry/capability recreation after response or commit uncertainty. Do not
   claim a cross-OS exactly-once transaction.

The deterministic state machine and fixed inert doubles may exercise these steps
without creating OS resources. Do not actually load/call native APIs for filesystem
inspection, create processes/handles/jobs, run Git, open sockets or inspect a product
path during imports or tests. Ordinary Python/Ruff applications launched by the
approved supervisor are the only application processes authorized in this batch.

Do not manufacture native evidence from a simulation. Where a native guarantee
cannot be implemented or proven in the permitted scope, represent a typed blocker
and document the precise additional proof needed. Do not silently downgrade a
requirement or substitute an unsupported platform workaround.

### Required adversarial evidence

Add the two distinct new unit modules, covering:

- exact binding/argv/env/handle policy and every security-relevant subject change;
- rejection of synthetic capabilities and missing real authority;
- malicious/oversized/raw/copied inputs and strict time/numeric handling;
- unknown path identity, alias/reparse changes, stale or incomplete observations;
- missing/mismatched executable, launch failure, PID reuse and extra/helper/host
  descendants, missing containment and unsupported platform states;
- pipe backpressure/output limits, deadline/cancellation and simultaneous primary/
  cleanup errors, owned termination order and unconfirmed shutdown;
- evidence before dispatch, changed base/branch/target, unexpected Git delta,
  incomplete manifests, partial writes and stopped-tree uncertainty;
- response loss, consumed capabilities, late/conflicting observations and replay;
- import and public-service non-execution, with OS/process/network constructors
  replaced by rejecting sentinels where applicable;
- the complete thirteen-module matrix below, without modifying legacy tests.

The new tests create **zero SQLite databases and zero native resources** themselves.
The unchanged prior eleven modules continue their already scoped synthetic fixtures.
A test double validates the implementation's decisions, not the platform's guarantees.
Document this limitation conspicuously.

## Read-only inputs

Read this proposal and applicable AGENTS.md completely. Read all twelve write
targets (or verify new-target absence), all fourteen files in the starting
checkpoint, and their relevant ADR/readiness records. Additional source-only inputs:

```text
src/fractilate_orchestrator/domain/workspace_create.py
src/fractilate_orchestrator/adapters/workspace_create_intents.py
src/fractilate_orchestrator/services/workspace_create.py
src/fractilate_orchestrator/persistence/workspace_create_journal.py
src/fractilate_orchestrator/domain/external_operations.py
src/fractilate_orchestrator/domain/workspaces.py
src/fractilate_orchestrator/domain/product_pilot.py
src/fractilate_orchestrator/domain/models.py
src/fractilate_orchestrator/domain/enums.py
tests/unit/test_workspace_create_contract.py
tests/unit/test_workspace_create_intents.py
tests/unit/test_workspace_create_recovery.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
tests/unit/test_external_operations.py
tests/unit/test_workspace_create_journal_contract.py
tests/unit/test_workspace_create_linkage.py
tests/integration/test_linked_workspace_create.py
tests/conftest.py
tests/helpers.py
pyproject.toml
docs/decisions/ADR-0021-workspace-create-contract-bridge.md
docs/decisions/ADR-0022-workspace-create-recovery-hardening.md
docs/decisions/ADR-0023-fixture-workspace-create-journal.md
docs/decisions/ADR-0024-fixture-controller-workspace-linkage.md
```

The read-only parent packets in CM_Computation must match:
- `CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md`: `448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c`.
- `CRSE_WCP3_TEST_FILENAME_AMENDMENT.md`: `35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4`.
- `CRSE_WCP3_GROUPED_DEVELOPMENT_BATCH.md`: `4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e`.
- `CRSE_WCP4_DURABLE_APPROVAL_BATCH.md`: `e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22`.

Read the WCP-4 readiness-bound root-local logs/results/qualification records as
needed; preserve their exact hashes and read no old fixture DB contents. Normal
test/static imports may read installed dependencies.

Read-only HTTPS documentation research is limited to primary Microsoft Learn
Win32 documentation and official Git documentation, with no login, downloads,
installation or external writes. This is a documentation exception, not network
permission for the adapter or tests. Cite sources and distinguish documented
guarantees from inferences and mocked evidence.

No secrets, .env files, credentials, local databases, user-configuration inspection
or unrelated diff contents. Metadata-only absence/non-reparse checks of the exact
new targets/root are allowed. Do not inspect real source/product/worktree paths.

## Root, runtime and finite verification budget

New root, currently absent:
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp5-tests-20260828-01`.

Recheck absence and non-reparse ancestors; create once. Set only the fixture helper's
literal TEST_ROOT to this root. No arbitrary root/env selection, old DB reuse,
manual deletion or cleanup. Retain distinct absent `pytest-1` through `pytest-6`
basetemps and a new `mypy` cache. Existing DELETE/FULL, foreign_keys ON, memory temp,
<=1,000 ms busy timeout, 4 MiB DB, 256 MiB root, 96 DB/iteration and all WCP-4 row/
document/joint receipt caps remain unchanged. Reserve rollback-journal headroom.
Only the already authorized helper creates fixture schema in explicit transactions.

New-root limits: parent-only preflight 10; formal qualification 5; pytest 6;
Ruff lint/formatter/format-check 6 each; strict mypy 6. Use create-new
`preflight-N.json`, `supervisor-selfcheck-N.json`, `pytest-N`, `ruff-lint-N`,
`ruff-format-N`, `ruff-formatcheck-N`, `mypy-N` evidence names. Never overwrite
records or reset a prior stage's usage. Parent preflights/self-checks are
<=30 seconds/4 KiB and no child/database.

Each real check remains <=300 seconds, 1 MiB combined output/evidence, 4 KiB frames,
64 KiB metadata, one application plus at most one attributable exact console host
(two OS processes total), no helpers or host descendants. Preserve the qualified
classifier functions, native PID/start/image checks, concurrent bounded pipes,
known-root peak accounting, error retention and owned-leaf-first shutdown.

Reuse the actual WCP-4 supervisor family. The appendix preserves its assembly as
historical reference, **not runnable WCP-5 authority**. Adapt only explicit stage
bindings: new root, exact new proposal/checkpoint/parent hashes, thirteen/six target
lists, counters and evidence paths. Old evidence checks remain on the old roots.
Require a passed new formal qualification of the actual adapted body, rechecked
before each application. Exercise all 83 prior classifier/binding cases plus the
new exact target/root/packet cases. Use complete AST function boundaries. Validate
the *exact output evidence filename* before formal execution; never globally
replace historical qualification filenames. Create no helper .ps1/executable.

Ordinary inspected code/assertion/assembly errors may be corrected/retested within
unused slots. Retain failures and label reconstructed evidence/timings honestly.
An actual identity/process/termination/resource violation stops further checks;
recovery or larger limits requires new owner authority.

Revalidate the six existing runtime/maintenance raw identities from WCP-4:
- `C:/Users/brian/AppData/Local/Programs/Python/Python310/python.exe`: `3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260`.
- `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/python.exe`: `b2c836c52cdf063180b9ee76f67ac42946101b79ac457f3494035a67c090d961`.
- `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/pyvenv.cfg`: `efe9c8f26884c6ac39ebb57a9f1215a539a423feaf12fe5eec753e28dcef3a55`.
- `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/ruff.exe`: `0cf602e931f311581bce0b1dfc8d5e30717d96af54c65d7b89a9a8d4497b0eeb`.
- `C:/Windows/System32/conhost.exe`: `b02ee54fb2ec69673386d41119ee8ed083a6eab3bfca6aa2155d20ce68ef8963`.
- `C:/Program Files/Git/cmd/git.exe`: `c954fcc8e65a38450895ca65d308ecaee63f044d16494b5385faa5e036a3facb`.

Direct base Python only; the venv interpreter is a binding, not a launch target.
Use shell-free hidden applications with cleared environment, inheriting only
SYSTEMROOT/WINDIR and setting TEMP/TMP to the new root, bytecode/plugin autoload
disabled, hash seed 0, UTF-8/utf-8 and no user site exactly as WCP-4.
Only Python gets the exact fixed __PYVENV_LAUNCHER__ binding. No PATH fallback,
runtime replacement/install, credential inheritance or conhost invocation.

### Exact commands

Direct Python `-B -m pytest -q -p no:cacheprovider --basetemp <new-root>/pytest-N`,
then exactly:

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
```

Ruff `check --no-cache`, `format --no-cache` or
`format --check --no-cache`, then exactly these six paths:

```text
src/fractilate_orchestrator/domain/workspace_create_native.py
src/fractilate_orchestrator/adapters/workspace_create_native.py
src/fractilate_orchestrator/services/native_workspace_create.py
tests/unit/test_workspace_create_native_contract.py
tests/unit/test_workspace_create_native_adapter.py
tests/fixtures/workspace_create_linkage/fixture_store.py
```

Mypy: direct Python `-B -m mypy --cache-dir <new-root>/mypy`, existing strict
configuration. Use Join-Path Windows spelling for absolute cache/basetemp argv.
No extra module, -k, plugin, coverage, full suite, build, native test or hosted CI.

## Acceptance and one conditional local checkpoint

Require all thirteen-module tests, six-file lint/format-check and strict mypy
passing, all relevant rechecks after corrections, complete failure/evidence
records, in-budget exact scope, old contracts/unrelated files unchanged and no
unresolved supervisory closure. Record actual native limitations and later
attended-proof requirements in the new ADR/readiness and four granted records.

Then freeze the seven new files plus only changed granted existing files, at most
twelve, with raw hashes and normalized Git blobs. Require the exact starting HEAD
and empty index. Create one absent empty `<new-root>/disabled-hooks`.
Use only the exact Git executable, command-local core.hooksPath to that directory,
core.fsmonitor=false, gc.auto=0, maintenance.auto=false and commit.gpgsign=false.
No pager, external diff/textconv, signing, hooks, auto-maintenance or network.
Existing author identity may resolve normally; do not inspect/change configuration.

At most one explicit staging invocation and one local commit, each <=60 seconds
and 64 KiB captured output. Message:
`Add inert native workspace adapter contracts`.
Verify exact index/base/raw content immediately before commit, then one direct
child, exact frozen paths/blobs, empty index and clean tracked worktree afterward.
Put the immutable SHA in the handoff; no second documentation commit, amend,
reset, unstage, blind retry, push or CM-workspace commit.

Prepare the next consolidated **attended native-fixture proof** proposal, including
actual Git/runtime closure and exact disposable targets, but execute none of it.
Native proof must never stand in for trusted real owner intake or production
installation. Product workspace creation still requires its own separate decision.

## Explicit exclusions and approval wording

No native workspace/Git call, real product observation, worker/verifier, SDK,
authentication, live owner capture, production DB/install/migration, listener,
network other than the narrow documentation read exception, publication/CI,
merge/deploy, paid fallback, cleanup or delegation.

Original decisions 1-5 remain bound only to plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle `a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
**Execution of workspace.create/v1 remains unapproved.**

> I approve CRSE-WCP-5 revision 2026-08-28.1, bound to its separately supplied
> raw SHA-256: the twelve-file private native-adapter development and inert-test
> batch, narrow primary-documentation reads, new fixture root and bounded
> correction/retest allowances, followed only after all gates pass by one exact
> local controller checkpoint. I do not approve native calls, real approvals,
> production installation, publication, product effects or cleanup.

## Appendix: immutable WCP-4 assembly reference

Historical reconstruction only. It requires the original CM packets and old-root
evidence. Do not execute this body with WCP-5 arguments without the explicit
adaptation and fresh qualification above. It defines the historical runner but
does not launch it. The verified normalized body hash is
`fd20941342f5501683e01170bda8d4b43a5d09b991014821023a0d612fb32127`.
Extract complete fence-line boundaries, not the first backtick substring: the
assembly itself contains quoted fence text. Keep evidence output names separate
from historical filenames when adapting it.

```powershell
$ErrorActionPreference='Stop'
$cDoc=[IO.File]::ReadAllText('C:/Users/brian/Documents/CM_Computation/CRSE_WCP3_TEST_FILENAME_AMENDMENT.md').Replace([string][char]13+[char]10,[string][char]10)
$cMatch=[regex]::Match($cDoc,'(?s)```powershell\n(.*?)```')
if (-not $cMatch.Success) { throw 'missing_runner_reference' }
$cRunner=$cMatch.Groups[1].Value.Trim()
$cRunner=$cRunner.Replace('fractilate-crse-wcp3-tests-20260828-01','fractilate-crse-wcp4-tests-20260828-01')
$cRunner=$cRunner.Replace('^(ruff-lint-[123]|ruff-(format|formatcheck)-[123]|mypy-[123]|pytest-[123])$','^(ruff-lint-[1-6]|ruff-(format|formatcheck)-[1-6]|mypy-[1-6]|pytest-[1-6])$')
$cRunner=$cRunner.Replace('$cDatabases[$cIteration] -gt 64','$cDatabases[$cIteration] -gt 96')
$cA=$cRunner.IndexOf('$cSelfcheck = Read-CMetadata')
$cZ=$cRunner.IndexOf('foreach ($cPriorFile',$cA)
$cRunner=$cRunner.Substring(0,$cA)+'$cOldRoot=''C:\Users\brian\AppData\Local\Temp\fractilate-crse-wcp3-tests-20260828-01''
$cOriginalSelf=Read-CMetadata -Path (Join-Path $cOldRoot ''supervisor-selfcheck-1.json'')
if (-not $cOriginalSelf.passed -or $cOriginalSelf.amendment_sha256 -ne ''448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c'' -or (Get-FileHash -LiteralPath (Join-Path $cOldRoot ''supervisor-selfcheck-1.json'')).Hash.ToLowerInvariant() -ne ''74dcfa289850910bc0e76175015d490d0861fc1855ad3ee1ee9fc5bd3fb71686'') { throw ''historical_selfcheck_drift'' }
foreach ($cPacket in @(
 @(''CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md'',''448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c''),
 @(''CRSE_WCP3_TEST_FILENAME_AMENDMENT.md'',''35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4''),
 @(''CRSE_WCP3_GROUPED_DEVELOPMENT_BATCH.md'',''4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e''),
 @(''CRSE_WCP4_DURABLE_APPROVAL_BATCH.md'',''e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22'')
)) { if ((Get-FileHash -LiteralPath (Join-Path ''C:\Users\brian\Documents\CM_Computation'' $cPacket[0])).Hash.ToLowerInvariant() -ne $cPacket[1]) { throw ''packet_drift'' } }
$cHeadText=[IO.File]::ReadAllText((Join-Path $cRepo ''.git\HEAD'')).Trim()
if ($cHeadText.StartsWith(''ref: refs/heads/'')) { $cHeadText=[IO.File]::ReadAllText((Join-Path $cRepo (''.git\''+$cHeadText.Substring(5)))).Trim() }
if ($cHeadText -cne ''24ab153f3381c4b882127175728082d864aeff08'') { throw ''checkpoint_drift'' }
$cAncestor=Get-Item -Force -LiteralPath $cRoot
while ($null -ne $cAncestor) { if ($cAncestor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw ''redirected_root_ancestor'' }; $cAncestor=$cAncestor.Parent }
foreach ($cOriginal in @(
 @(''supervisor-selfcheck-3.json'',''0a065f5e929040922a1aed94ac22abcc3e85537fa8486a3980c00bc9314bd5fc''),
 @(''pytest-1.result.json'',''2b48fb4ec6c3bb72ade97c5b3175f582bc28766c35781a29d0d22a1bf0e760a5''),
 @(''pytest-2.result.json'',''edc02ab8435569e37e193b424093345c907f088f9cd188baac26976e5aa5dc09''),
 @(''ruff-lint-3.result.json'',''4b769295bc30935d8b7f7183a7fa94f03077eec0cfce91d557916d8d0c2803e2''),
 @(''ruff-formatcheck-2.result.json'',''8c2d4a8dacfb250e05fb178fe49a723691a882c69fd34f96b8bae07c5a0dbec1''),
 @(''mypy-3.result.json'',''9c89d5ba3756e4656b2ea7b507e532aad11f7e686b730d9050f709b069981609''),
 @(''ruff-lint-2.result.json'',''743197c9b38b4cdb1bc2df087975cc2f213197c08a3af0536f401e8c3eb47d7c''),
 @(''mypy-2.result.json'',''1b3ebb380a0fa7ace557140f478d2a9c7503b091361be99785dfb5d0c5b9d45a''),
 @(''ruff-formatcheck-1.result.json'',''b384fd41b1c3540b1bf89f54d1b169ce21c55ace7ad7668813b68818f8d249e9''),
 @(''mypy-1.result.json'',''9ea59a3ccea914e915901028c0dffb7ce977160159fe741cdf0811d1888142e0''),
 @(''ruff-format-1.result.json'',''ccf000403d81c6980fa8e086e4339e957a4b2f1f709d73eb3cf2a4f671fc464e''),
 @(''ruff-format-2.result.json'',''9a3bc714f6e493cc95ff199e067518d63b2a1846f4108ec0922f2fd903c2ce52''),
 @(''ruff-lint-1.result.json'',''f28bf222a0661dbe860f01a252986e654315de54e0975c6a80384762661f1328''),
 @(''supervisor-selfcheck-2.json'',''c1410673c0ca91a1830d85485736a3ec249582477198120bd624d1dc4d585d22'')
)) { if ((Get-FileHash -LiteralPath (Join-Path $cOldRoot $cOriginal[0])).Hash.ToLowerInvariant() -ne $cOriginal[1]) { throw ''historical_evidence_drift'' } }
if ($cQualificationName -notmatch ''^supervisor-selfcheck-[1-5]\.json$'') { throw ''qualification_name'' }
$cQualified=Read-CMetadata -Path (Join-Path $cRoot $cQualificationName)
if (-not $cQualified.passed -or $cQualified.runner_sha256 -ne $cRunnerHash -or $cQualified.parent_sha256 -ne ''448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c'' -or $cQualified.v_sha256 -ne ''35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4'' -or $cQualified.batch_sha256 -ne ''4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e'' -or $cQualified.wcp4_sha256 -ne ''e34f81e9c911aa82bce84d0295465f4f3859e5537f740cecdc8e175285be8d22'' -or $cQualified.checkpoint -ne ''24ab153f3381c4b882127175728082d864aeff08'' -or $cQualified.root -ne $cRoot -or $cQualified.database_limit -ne 96) { throw ''wcp4_qualification_binding'' }
foreach ($cPriorFile in @(Get-ChildItem -LiteralPath $cOldRoot -File -Filter ''*.result.json'')) {
 $cPrior=Read-CMetadata -Path $cPriorFile.FullName
 if (-not $cPrior.eligible -or $cPrior.primary_failure -or $cPrior.cleanup_failure -or -not $cPrior.root_termination_confirmed -or -not $cPrior.host_termination_confirmed -or $cPrior.exit_code -notin @(0,1)) { throw ''old_check_stop'' }
}
'+$cRunner.Substring($cZ)
$cRunner=$cRunner.Replace('if ($cPrior.primary_failure','if (-not $cPrior.eligible -or $cPrior.primary_failure')
$cA=$cRunner.IndexOf('$cTargets=@(')
$cZ=$cRunner.IndexOf('$cExpectedArgs',$cA)
$cRunner=$cRunner.Substring(0,$cA)+'$cTargets=@(
''src/fractilate_orchestrator/domain/workspace_create_approval.py'',
''src/fractilate_orchestrator/persistence/workspace_create_approval.py'',
''src/fractilate_orchestrator/services/approved_workspace_create.py'',
''tests/unit/test_workspace_create_approval_contract.py'',
''tests/integration/test_approved_linked_workspace_create.py'',
''src/fractilate_orchestrator/persistence/workspace_create_linkage.py'',
''src/fractilate_orchestrator/services/linked_workspace_create.py'',
''tests/fixtures/workspace_create_linkage/fixture_store.py''
)
'+$cRunner.Substring($cZ)
$cRunner=[regex]::Replace($cRunner,' \+ @\(''tests/unit/test_workspace_create_contract\.py''[^}\n]*\) \}',[Text.RegularExpressions.MatchEvaluator]{param($m) ' + @(''tests/unit/test_workspace_create_contract.py'',''tests/unit/test_workspace_create_intents.py'',''tests/unit/test_workspace_create_recovery.py'',''tests/unit/test_workspaces.py'',''tests/unit/test_product_pilot.py'',''tests/unit/test_external_operations.py'',''tests/unit/test_workspace_create_journal_contract.py'',''tests/unit/test_workspace_create_linkage.py'',''tests/integration/test_linked_workspace_create.py'',''tests/unit/test_workspace_create_approval_contract.py'',''tests/integration/test_approved_linked_workspace_create.py'') }'})
$cSha=[Security.Cryptography.SHA256]::Create()
try { $cRunnerHash=[BitConverter]::ToString($cSha.ComputeHash([Text.Encoding]::UTF8.GetBytes($cRunner))).Replace('-','').ToLowerInvariant() } finally { $cSha.Dispose() }
```
