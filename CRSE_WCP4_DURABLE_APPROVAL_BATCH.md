# CRSE-WCP-4: grouped durable approval rehearsal, verification and local checkpoint

Revision: **2026-08-28.1**. Status: **proposed; not approved**.

## One requested approval

Approve the following as one bounded offline development batch:

1. Implement an exact, durable **synthetic owner-decision ledger** and its
   transactionally enforced workspace-create gate in new disposable fixtures.
2. Qualify the adapted supervisor, run the specified regression/adversarial
   matrix, and make in-scope corrections/retests within the stated allowances.
3. Record evidence, review and freeze the candidate, then make **one conditional
   local controller commit** only after all acceptance gates pass.

This groups development, foreseeable testing corrections, documentation and the
checkpoint. It does not authorize actual owner-approval ingestion, installation
into a real controller database, publication, native execution or product effects.
Do not persist this conversation as a real effect approval.

## Verified starting checkpoint

Controller: `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.

Require exact HEAD **`24ab153f3381c4b882127175728082d864aeff08`**,
an empty index and no tracked drift. Its parent is
`b9dd7724a205ef08b5655839ca6db7dd97b5774e`. WCP-3B's one approved local
checkpoint completed, containing exactly nineteen frozen files; its eight WCP-2C
inputs stayed byte-identical. Do not repeat that commit. Untracked
`coordination/prompts/` remains preserved and unread.

WCP-3B passed 342 scoped tests, five-file Ruff lint/format checks and strict mypy
on 84 source files. All supervised checks closed within limits. The first pytest
run had one ordinary exception-expectation failure (341 passed); the corrected
test also verifies the SQLite cause and rollback. Earlier assembly/lint/type
failures remain recorded. This is a local fixture checkpoint, **not hosted-green
CI or production readiness**.

The retained WCP-3 root has 196 files, 57,385,786 bytes and 112 synthetic databases.
Its empty `disabled-hooks` directory was created for the completed maintenance
sequence. No cleanup or old-fixture reuse is included in WCP-4.

## Why this is the next slice

WCP-3 links the two recovery histories and controller audit atomically, but
`SimulatedCreateApproval.owner_approval_persisted` is intentionally false.
Its fixture policy permits zero rows in the existing `approvals` table.
An approval embedded in a workspace command is not an independently persisted
owner decision, revocation history or one-use durable decision consumption.

The next rehearsal should prove that a missing, changed, stale, revoked, consumed
or incorrectly scoped decision cannot arm or fake-dispatch a workspace operation,
including through direct legacy store calls. It should also prove that revocation
does not erase an existing recovery barrier or resurrect a consumed capability.

The result is reusable approval-contract and transaction logic plus evidence for
a later installation proposal. It is **not** a real owner-authentication boundary.
Production installation, trusted owner-input capture and native dispatch remain
unimplemented/unapproved by this batch.

## Exact write grants and implementation ceiling

Create these seven files, all absent during preparation; recheck before writing:

```text
src/fractilate_orchestrator/domain/workspace_create_approval.py
src/fractilate_orchestrator/persistence/workspace_create_approval.py
src/fractilate_orchestrator/services/approved_workspace_create.py
tests/unit/test_workspace_create_approval_contract.py
tests/integration/test_approved_linked_workspace_create.py
docs/decisions/ADR-0025-workspace-create-approval-rehearsal.md
coordination/WORKSPACE_CREATE_APPROVAL_READINESS.md
```

Modify only these seven existing files:

| Existing controller-relative file | Required starting raw SHA-256 |
| --- | --- |
| `src/fractilate_orchestrator/persistence/workspace_create_linkage.py` | `c3ed93e1010943158fead30ac3db65d325caaa5d44465d5a55b3344f71669a8c` |
| `src/fractilate_orchestrator/services/linked_workspace_create.py` | `9d48d169a7fbd1f0163ad17bb0b9a09328017f2fa16593dacc60bde41b2ead51` |
| `tests/fixtures/workspace_create_linkage/fixture_store.py` | `99453a48ac9432065a6bbac640d2080ef056c2a78d8fc29fb8d60ee8222cf242` |
| `coordination/WORKSPACE_CREATE_LINKAGE_READINESS.md` | `325a77c14b1978e4f8c055143bb7343c54a7c081d7b497d3b147e58720cd9e5c` |
| `coordination/PROGRAM_STATUS.md` | `68cdbb2185eea80b181dac6da53ae2b542f80b69ad1c40d27d1a2b0329549f23` |
| `coordination/plans/ACTIVE_PLAN.md` | `04c3e19e6cfa25ac72d1daebe9e00103d59e02ed133d53232c6ce58a8cd50ae2` |
| `coordination/NEXT_ACTIONS.md` | `c907de291fe77e85f75e2d0c2a610ba22e2dd432e235b91920ac4f4424168311` |

At most **fourteen files, 5,000 additions and 500 deletions**, measured against
the exact starting checkpoint above. Count new files by final line count.
Deletions are permitted only within the seven named existing files; no whole-file
deletion, rename or move. Existing historical evidence must remain recognizable
and labeled; do not replace prior failures with a new success-only narrative.

The seven creates are required deliverables. Existing files may change only as
needed for this slice; do not manufacture changes to reach a file count. Preserve
all other files, including WCP-1/WCP-2 Python, existing unit/integration tests, SQL,
schema registration, dependencies, configuration and entry points.

One maintainer, this task's configured model/effort, concurrency one. No delegation,
product worker, SDK client, arbitrary driver, network or helper process.

## Required behavior

### Exact decision contract and conservative lifecycle

Add strict, bounded, domain-separated fixture decision/subject/receipt models.
Use a closed contract vocabulary and distinguish a maintenance/development
decision from a `workspace.create/v1` effect decision; one cannot satisfy the other.

Bind the complete applicable subject: fixture and program identity, controller
checkpoint, operation/effect identity, repository/workstream/job/version, product
base/branch/target, request/binding/envelope/operation-plan hashes, successor
product plan/bundle hashes, authority/evidence digest, decision identifier,
synthetic actor identity, finite validity window and bounded sequence/version.
Prefer exact existing canonical fingerprints to duplicating an incomplete field
subset. Validate all equality links against the retained envelope and reference
rows; changing any bound subject component must invalidate the decision.

Retain the original product plan/bundle approval only as historical provenance.
Do not transfer it to a successor packet or infer effect approval from decisions
1-5, a test pass, a commit or a fixture receipt. Do not parse free-form owner text
or claim cryptographic authentication from an actor string or hash alone.

Keep all old v1 contracts, hash domains and false live/real-owner-authority flags
unchanged. New fixtures must carry explicit synthetic-only provenance. A test
decision may be durably stored while still granting **zero real execution
authority**; do not relabel that storage as `owner_approval_persisted=True` in an
existing model.

Model grant, denial, revocation, reservation and consumption as append-only facts
with exact idempotency keys and request hashes. A duplicate returns the original
receipt without issuing a fresh capability; a reused key with a changed request
fails closed. Denial/revocation is terminal for the referenced grant. A new grant
must never override an already consumed operation, permanent reservation or held
barrier. New authority for changed scope requires a new exact subject/decision,
not mutation of an old grant.

Use explicit synthetic milliseconds and reject invalid types, bool-as-int,
non-finite/negative/out-of-range numbers, malformed UUIDs/hashes, unknown fields,
duplicate JSON keys, oversized bytes and invalid time order before sealing or
materialization. Bound input before decode; revalidate already-typed/copied models.

### Fixture schema and joint transaction

Extend only the test helper to create a closed **approval-required fixture
profile**, with private `wcp4_*` tables/guards and bounded synthetic rows in the
unchanged `approvals` schema. Use existing Approval/ApprovalStatus models where
their semantics actually match; private reservation/consumption facts must not
invent values in old enums or alter the production schema.

Preserve the old WCP-3 profile as an explicit historical rehearsal with its zero-
approval policy. A new approval-required fixture cannot be opened or downgraded
as that old profile. Bind profile, complete expected schema/trigger SQL and
reference identities in retained identity; verify before access and on reopen.
The production store must not bootstrap, discover, install or repair any database.

Only the named fixture helper may create schema, using bounded individual
statements in an explicit transaction. No migration runner, numbered migration,
`Database.connect()`, WAL/SHM, ATTACH, extension, vacuum, automatic adoption,
schema repair or opening an existing controller database.

Persist the typed decision source, mirrored approval row, exact request receipt
and real controller `append_event` audit linkage atomically. Verify independently
from authoritative sources: approval model/columns, full ordered decision fold,
receipt request/response, event correlation/causation and every cached projection.
A checksum or a copied “granted” flag is not a substitute for that replay.

For an approval-required fixture, reserve the exact active decision in the same
transaction as workspace claim/intent. Recheck and consume it in the same
transaction as one-use dispatch consumption. Commit before the exact fake call;
observations/audit commit afterward. Do not open a nested transaction or issue
a capability from an unconfirmed commit.

Enforce admission in fixture SQL as well as Python: direct linkage transactions,
old coordinator calls, generic ExternalOperationStore calls and direct inserts
must not bypass the approval-required profile. Reject synthetic-approval-only
arming or dispatch in that profile. Do not introduce a generic callback,
caller-controlled validation exemption, alternate live driver or permissive
fallback for missing approval metadata.

Preserve WCP-3's independent folds, union barrier, sticky terminal-conflict veto,
increasing epoch/fences, permanent target/branch reservations and source bounds.
Revocation/expiry after arming blocks dispatch; it does not itself prove safe
termination or clear the combined barrier. After consumption or response loss,
never recreate an in-memory dispatch capability on reopen/restart.

A rejected step poisons and rolls back the complete joint transaction even if
caught by the caller. Use closed fault points around approval source/audit,
reservation, consumption and commit; no arbitrary injected callable. After an
uncertain commit invalidate the instance, expose no success receipt/capability,
and require retained-identity verified reopen to determine durable state.

Document that SQL guards, retained identities and exact Python types are misuse
guards under the fixture threat model, not protection against arbitrary code
controlling the same connection/process/filesystem.

### Required adversarial evidence

The matrix must cover:

- valid exact grant and the decision-commit/reserve/consume/fake-call ordering;
- missing/wrong-kind/wrong-subject grants and every bound-field mismatch;
- denied/revoked/expired/future-dated grants, time boundaries and clock regression;
- typed/raw malformed inputs, oversize/cardinality limits and atomic rejection;
- identical replay versus same-key changed request, conflicting or reordered facts;
- revocation between arm and consume using two connections serially, stale epochs/
  fences and copied/replayed/lost capabilities;
- direct legacy coordinator/store/SQL bypass attempts in the approval profile;
- decision/audit/approval-row/receipt/cache/trigger/profile tamper and verified reopen;
- rollback and uncertain commit at each new durable boundary, including caught
  rejection and fake-response loss;
- conflicts and mixed generic/workspace barriers remaining conservative;
- unchanged WCP-3 profile behavior under the full prior nine-module matrix;
- no native driver, subprocess, listener, authentication, SDK or product operation.

Do not weaken negative tests or suppress failures to achieve green results.
Keep the two new test basenames distinct; no import-mode change or rename is granted.

## Read-only inputs

Read this packet, applicable AGENTS.md, all fourteen write targets, all nineteen
files in the starting WCP-3B checkpoint, and the current relevant ADR/coordination
records. The exact extra reference list in WCP-3's approved proposal remains
available read-only, including domain models/enums, workspace/product/operation
contracts, recovery folds, intent adapter, existing audit/external-operation APIs,
database/migration **source only**, both initial SQL files, tests/conftest.py,
tests/helpers.py and the named reference tests.

Read these immutable CM packets in full; raw hashes must match:

- `CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md`:
  `448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c`.
- `CRSE_WCP3_TEST_FILENAME_AMENDMENT.md`:
  `35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4`.
- `CRSE_WCP3_GROUPED_DEVELOPMENT_BATCH.md`:
  `4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e`.

WCP-3 retained root-local evidence named/bound in those packets and its final
readiness report is read-only. The qualified self-check 3 record has raw SHA-256
`0a065f5e929040922a1aed94ac22abcc3e85537fa8486a3980c00bc9314bd5fc`;
the runner it qualified has normalized UTF-8 SHA-256
`c84f39fa8cdd8f2507711aa3f15e8eb2ed35ba98b40d9a27a92d1cb8b1ec5b6a`.
Do not read/reuse old fixture databases or change their evidence.

Normal package/test imports and static analysis may read installed dependencies.
No secrets, .env files, credentials, user-configuration inspection, unrelated
diff contents, product repository/workspace observations or existing databases.
Metadata-only existence/non-reparse checks of the exact proposed targets are allowed.

## New fixture root and finite budgets

Proposed root, absent during preparation:
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp4-tests-20260828-01`.

Revalidate absence and non-reparse ancestors, then create once. Set the named
fixture helper's literal TEST_ROOT to this new root; never allow both roots or
accept an arbitrary caller/environment-selected root. All new cache, logs,
metadata and databases must stay beneath it. Preserve prior roots unchanged.

This batch explicitly permits create-new synthetic SQLite fixtures, fixture-only
DDL/data, controlled corruption/recovery tests and SQLite-managed rollback
journals. No manual deletion/recreation, copy of an old database or cleanup.
Use distinct absent `pytest-1` through `pytest-6` basetemps and one new
`mypy` cache directory.

Preserve DELETE/FULL, foreign_keys ON, temp_store MEMORY, busy_timeout <=1,000 ms
and the **4 MiB database / 256 MiB retained-root caps**. The new helper's per-
iteration database allowance is explicitly **96**, increased from WCP-3's 64
to accommodate the prior 56 fixtures plus the new matrix. This change applies
only to the new WCP-4 root; old usage is not reset. Reject allocation before
exceeding a limit, retaining rollback-journal headroom.

Per database: one synthetic program, sixteen plans/subjects, at most 128 decision
facts total and 128 facts per workspace/generic history, **256 joint receipts
across all three domains**, 2,048 audit rows, 65,536-byte documents. Bound mirrored
approval rows by the same 128-decision ceiling and consumptions by sixteen.
Enforce raw columns, row counts and combined budgets before legacy materialization
and in fixture SQL. Keep implementation and supervisor limits consistent.

| WCP-4 operation | Maximum | Create-new names |
| --- | ---: | --- |
| Parent-only syntax/assembly preflight | 10 | `preflight-1.json` through `preflight-10.json` |
| Formal synthetic supervisor qualification | 5 | `supervisor-selfcheck-1.json` through `-5.json` |
| Exact pytest matrix | 6 | `pytest-1` through `pytest-6` |
| Ruff lint | 6 | `ruff-lint-1` through `ruff-lint-6` |
| Ruff formatter | 6 | `ruff-format-1` through `ruff-format-6` |
| Ruff format-check | 6 | `ruff-formatcheck-1` through `ruff-formatcheck-6` |
| Strict mypy | 6 | `mypy-1` through `mypy-6` |

These are new stage/root allowances, not permission to overwrite evidence or
reset any WCP-3 counter. Spend only needed slots. Preflight/self-check attempts
are <=30 seconds/4 KiB each, without child processes or database calls.

Each real check: <=300 seconds, 1 MiB combined output/evidence, 4 KiB frames,
64 KiB metadata within that total, one application and at most one attributable
exact OS console host (**two OS processes total**). No helper, ordinary child or
host descendant. Both root and host termination and closed streams must be
confirmed. Ordinary inspected code/assertion/assembly failures may be corrected
within unused slots. An actual identity/process/termination/resource violation
stops further checks; recovery or a larger budget requires new approval.

## Supervisor reuse and qualification gate

Use the actual WCP-3B family, not a new permissive launcher. The appendix preserves
its historical assembly reference; it reconstructs the WCP-3B body from the
immutable WCP-3V packet and is **not executable WCP-4 authority as written**.

Adapt only explicit stage bindings: new root, approved packet/hash/checkpoint,
the exact eleven/eight target lists below, WCP-4 counters, 96-fixture accounting
and create-new evidence paths. Keep prior-stage evidence checks on the old root,
read-only; do not point them at nonexistent WCP-4 files or copy records.
Use a separate exact new-root history check for already consumed WCP-4 attempts.

Preserve full classifier definitions, PID/start-time/executable identity,
reparse/root checks, bounded concurrent pipes, known-root peak accounting,
error retention and owned-leaf-before-root shutdown. Never admit a diagnostic
helper or add environment inheritance to resolve a launch failure.

First use parent-only parsing/string checks to catch assembly mistakes. Extract
complete functions with real boundaries, never magic delimiter offsets. Formal
qualification must exercise the same four pure functions as the runner:
`Get-CRelation`, `Get-CShapeFailure`, `Join-CFailures`,
`Get-CAccountedLength`. Cover every WCP-3B classifier/error/accounting case plus
new exact argument/name/root/budget/packet bindings and rejection of old names,
wrong roots, extra targets and out-of-budget names.

Require a passed new formal qualification binding this packet's separately
approved raw hash, starting checkpoint, parent hashes and actual adapted runner
identity before any real check. A syntax-only pass is not qualification.
Real-run preflight must revalidate these bindings. If runner behavior changes,
consume another available formal qualification before checks. Keep failed
attempts; reconstructed evidence must say so and never invent timing or success.
No local .ps1, helper script or executable is created.

## Exact check commands

Controller cwd. Direct Python:
`-B -m pytest -q -p no:cacheprovider --basetemp <new-root>/pytest-N`,
then exactly these eleven paths in this order:

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
```

Ruff uses `--no-cache` and exactly these eight changed Python paths for
`check`, `format`, or `format --check`:

```text
src/fractilate_orchestrator/domain/workspace_create_approval.py
src/fractilate_orchestrator/persistence/workspace_create_approval.py
src/fractilate_orchestrator/services/approved_workspace_create.py
tests/unit/test_workspace_create_approval_contract.py
tests/integration/test_approved_linked_workspace_create.py
src/fractilate_orchestrator/persistence/workspace_create_linkage.py
src/fractilate_orchestrator/services/linked_workspace_create.py
tests/fixtures/workspace_create_linkage/fixture_store.py
```

Strict mypy remains direct Python
`-B -m mypy --cache-dir <new-root>/mypy` using the existing configuration.
Construct absolute Windows basetemp/cache arguments with Join-Path; match that
exact spelling in the argument gate. No extra modules, -k filter, changed import
mode, plugin, full suite, coverage, build, install or hosted CI. The older WCP-2
database/crash-helper integration modules are reference-only and must not run.

## Exact runtime identities and environment

Revalidate these existing files before use; no replacement, install or PATH fallback:

| Subject | Raw SHA-256 |
| --- | --- |
| `C:/Users/brian/AppData/Local/Programs/Python/Python310/python.exe` | `3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260` |
| `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/python.exe` (binding only) | `b2c836c52cdf063180b9ee76f67ac42946101b79ac457f3494035a67c090d961` |
| `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/pyvenv.cfg` | `efe9c8f26884c6ac39ebb57a9f1215a539a423feaf12fe5eec753e28dcef3a55` |
| `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/ruff.exe` | `0cf602e931f311581bce0b1dfc8d5e30717d96af54c65d7b89a9a8d4497b0eeb` |
| `C:/Windows/System32/conhost.exe` (OS-created only) | `b02ee54fb2ec69673386d41119ee8ed083a6eab3bfca6aa2155d20ce68ef8963` |
| `C:/Program Files/Git/cmd/git.exe` (controller maintenance only) | `c954fcc8e65a38450895ca65d308ecaee63f044d16494b5385faa5e036a3facb` |

Python/Ruff launches are shell-free and hidden with cleared environment. Inherit
only SYSTEMROOT/WINDIR. Set TEMP/TMP to the new root,
PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONHASHSEED=0,
PYTHONUTF8=1, PYTHONIOENCODING=utf-8 and PYTHONNOUSERSITE=1.
Direct Python alone gets literal
`__PYVENV_LAUNCHER__=C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/python.exe`.
Do not launch the venv redirector or conhost directly. No credential inheritance,
environment dumps, console sharing or runtime upgrade.

## Acceptance and one conditional local checkpoint

Require all eleven-module pytest tests passing, eight-file Ruff lint and
format-check passing, strict mypy passing, and no unresolved supervisory closure.
Reverify relevant checks after any later source/test correction. Verify old
contracts and unrelated tracked files unchanged, complete evidence/hashes and
all fourteen-file/line/resource limits. Record negative-case coverage, every
failure, actual usage, artifacts and limitations in the new readiness/ADR and
four granted coordination records before freezing.

Then make one local controller checkpoint, with the exact starting HEAD above
and empty index. Freeze the seven new files plus only changed granted existing
files, at most fourteen, and their raw hashes/normalized Git blobs. No unrelated
path, manual config edit, branch/worktree change or CM-workspace commit.

Create one initially absent empty `<new-root>/disabled-hooks` directory.
Use only the exact Git executable above; disable hooks with command-local
`core.hooksPath` set to that directory, and set `core.fsmonitor=false`,
`gc.auto=0`, `maintenance.auto=false`, `commit.gpgsign=false`.
Use no pager, external diff/textconv, signing, hook, auto-maintenance or network.
Existing author identity may resolve normally; do not inspect/print/change user
config or credentials. Stop if identity is unavailable.

At most one deliberate staging invocation and one commit invocation, each
<=60 seconds/64 KiB captured output. Stage explicit frozen paths only.
Verify the exact index, HEAD and raw files immediately before commit.
Message: `Add fixture-only durable workspace approval gate`.

Verify one direct child commit with the exact frozen path/blob delta, empty index
and clean tracked worktree. Put its immutable SHA in the owner handoff; do not
edit controller files or make another commit solely to insert that SHA.
Uncertain outcome requires read-only inspection, never blind retry, amend, reset,
unstage, cleanup or an extra commit.

Continue through the approved batch without routine intermediate approvals.
Stop only for new authority, a hard violation, exhausted allowances or a material
design conflict. Prepare one consolidated proposal for the next separate stage.

## What remains excluded

No real controller database or real owner-decision ingestion; no production
installation/migration/registration; no native workspace/Git product execution,
product inspection, worker/verifier, SDK/app-server, authentication, network,
listener, publication/push, hosted CI, merge/deploy, paid fallback or cleanup.
The fixture decision ledger must not be connected to any live entry point.

Original decisions 1-5 remain bound only to product plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle `a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
**Execution of `workspace.create/v1` remains unapproved.**

## Suggested approval

> I approve CRSE-WCP-4 revision 2026-08-28.1, bound to its separately supplied
> raw-file SHA-256: the fourteen-file synthetic durable-approval implementation,
> new fixture root and stated verification/fix-retest limits, followed only after
> all gates pass by one scoped local controller checkpoint. No real approvals,
> production installation, publication, hosted CI, product effects or cleanup
> are approved.

## Appendix: preserved WCP-3B runner assembly reference

This is historical data, not a command to execute now. It reconstructs the body
whose qualified hash is recorded above. Preserve the immutable source packet.
Adapt under the proposed WCP-4 scope and qualify the resulting complete body
before running any check. The historical check-name allowances and root bindings
below do not carry forward by themselves.

```powershell
$cDoc=(Get-Content -LiteralPath 'C:/Users/brian/Documents/CM_Computation/CRSE_WCP3_TEST_FILENAME_AMENDMENT.md' -Raw).Replace([string][char]13+[char]10,[string][char]10)
$cMarker='```powershell'+[char]10
$cStart=$cDoc.IndexOf($cMarker)+$cMarker.Length
$cRunner=$cDoc.Substring($cStart,$cDoc.LastIndexOf('```')-$cStart).Trim()
$cRunner=$cRunner.Replace('tests/integration/test_workspace_create_linkage.py','tests/integration/test_linked_workspace_create.py')
$cRunner=$cRunner.Replace('if ($cCheckName -notmatch ''^(ruff-lint-[123]|ruff-(format|formatcheck)-[123]|mypy-[123]|pytest-[123])$'') { throw ''Unapproved check name.'' }','if ($cCheckName -notmatch ''^(ruff-lint-[3-6]|ruff-format-[3-6]|ruff-formatcheck-[2-6]|mypy-[3-6]|pytest-[1-5])$'') { throw ''Unapproved check name.'' }')
$cRunner=$cRunner.Replace('foreach ($cPriorFile','if ($cQualificationName -notin @(''supervisor-selfcheck-3.json'',''supervisor-selfcheck-4.json'',''supervisor-selfcheck-5.json'')) { throw ''qualification_name'' }
$cQualified=Read-CMetadata -Path (Join-Path $cRoot $cQualificationName)
if (-not $cQualified.passed -or $cQualified.runner_sha256 -ne $cRunnerHash -or $cQualified.parent_sha256 -ne ''448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c'' -or $cQualified.v_sha256 -ne ''35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4'' -or $cQualified.batch_sha256 -ne ''4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e'') { throw ''batch_qualification_binding'' }
foreach ($cPacket in @(
 @(''CRSE_WCP3_TEST_FILENAME_AMENDMENT.md'',''35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4''),
 @(''CRSE_WCP3_GROUPED_DEVELOPMENT_BATCH.md'',''4a59ce7ad6f77a6a84c9a360cc9b2b2c57fd12ba85109dcb6654daab2f47cc2e'')
)) { if ((Get-FileHash -LiteralPath (Join-Path ''C:\Users\brian\Documents\CM_Computation'' $cPacket[0])).Hash.ToLowerInvariant() -ne $cPacket[1]) { throw ''batch_packet_drift'' } }
foreach ($cOriginal in @(
 @(''mypy-1.result.json'',''9ea59a3ccea914e915901028c0dffb7ce977160159fe741cdf0811d1888142e0''),
 @(''mypy-2.result.json'',''1b3ebb380a0fa7ace557140f478d2a9c7503b091361be99785dfb5d0c5b9d45a''),
 @(''ruff-format-1.result.json'',''ccf000403d81c6980fa8e086e4339e957a4b2f1f709d73eb3cf2a4f671fc464e''),
 @(''ruff-format-2.result.json'',''9a3bc714f6e493cc95ff199e067518d63b2a1846f4108ec0922f2fd903c2ce52''),
 @(''ruff-formatcheck-1.result.json'',''b384fd41b1c3540b1bf89f54d1b169ce21c55ace7ad7668813b68818f8d249e9''),
 @(''ruff-lint-1.result.json'',''f28bf222a0661dbe860f01a252986e654315de54e0975c6a80384762661f1328''),
 @(''ruff-lint-2.result.json'',''743197c9b38b4cdb1bc2df087975cc2f213197c08a3af0536f401e8c3eb47d7c''),
 @(''supervisor-selfcheck-2.json'',''c1410673c0ca91a1830d85485736a3ec249582477198120bd624d1dc4d585d22'')
)) { if ((Get-FileHash -LiteralPath (Join-Path $cRoot $cOriginal[0])).Hash.ToLowerInvariant() -ne $cOriginal[1]) { throw ''historical_evidence_drift'' } }
'+'foreach ($cPriorFile').Replace('if ($cPrior.primary_failure','if (-not $cPrior.eligible -or $cPrior.primary_failure')
$cSha=[Security.Cryptography.SHA256]::Create()
try {$cRunnerHash=[BitConverter]::ToString($cSha.ComputeHash([Text.Encoding]::UTF8.GetBytes($cRunner))).Replace('-','').ToLowerInvariant()} finally {$cSha.Dispose()}
```

