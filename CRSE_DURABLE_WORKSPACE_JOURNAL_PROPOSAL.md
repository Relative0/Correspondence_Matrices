# CRSE-WCP-2: fixture-persistent creation journal and restart proof

Revision: **2026-08-27.1**. Status: **proposed; implementation not authorized**.

This is the next bounded controller-maintenance proposal, not permission to create
the product workspace. Implementation becomes authorized only when the owner
approves this revision and its separately reported raw-file SHA-256. The prior
approval of WCP-1R and the request to commit that work do not authorize this slice.

## Decision requested

Approve an additive SQLite journal and a separate fake-only coordinator, together
with real transaction, reopen, and bounded process-exit tests. The new journal
stores synthetic creation records in newly generated test fixtures only. Dispatch
continues to use the existing exact `FakeWorkspaceCreateDriver`.

This approval would grant 12 controller-file writes, fixture-only schema setup and
database reads/writes, and a narrowly bounded Python crash-helper exception. It
would not grant access to an existing controller/user database, a native Git
executor, real workspaces, workers, verifiers, services, or external effects.

## Verified starting state and evidence

Controller checkout:
`C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.

Require immutable controller HEAD:
`c6107fa889053a34711412be23f2d8d065eb125c`.

That local commit contains the 12-file WCP-1/WCP-1R implementation and its records
(2,819 additions, 9 deletions). The two previously approved proposals are committed
in `C:/Users/brian/Documents/CM_Computation` at
`21635b8e9507b5406e3e91d400fa24db1dfbb29a`. Neither commit was pushed; no hosted CI
was dispatched. Earlier status prose describing this work as uncommitted records
its pre-commit state and is superseded by these commit identities.

Historical WCP-1R evidence is 221 passing tests in the six modules listed below,
passing targeted Ruff checks, and passing strict mypy over 80 source files. The
six committed WCP-1 Python files matched their tested bytes before the commit.
Those checks were not rerun during this proposal's preparation. There is no new
full-suite, build, coverage, native-fixture, or hosted-CI result for this checkpoint.

Before implementation, read the applicable instructions and grant-listed inputs;
verify HEAD, an empty index, no tracked drift from this commit, and absence of all
eight create targets and the proposed temporary root. Do not switch, reset, rebase,
stage, or commit to manufacture a match. Any mismatch requires a revised proposal.
Preserve the existing untracked `coordination/prompts/` without reading its contents.
The existing Git global-ignore permission warning does not authorize inspection or
repair of user configuration, or a claim of exhaustive ignored-file cleanliness.

## Why this slice comes next

The committed recovery fold now preserves causal evidence timing and sticky
terminal conflicts, but `FakeWorkspaceFactSink` still stores its journal in memory.
Its simulated restart cannot prove survival of process termination or an actual
SQLite commit/rollback boundary.

The generic external-operation store already has durable facts, receipts, audit,
and a program barrier. Its conflict handling is not interchangeable with WCP-1R:
some generic conflicts can release a barrier after confirmed termination, whereas
a conflicting workspace terminal history must keep its barrier held. This slice
must not silently map that history into generic success/failure or change the old
aggregate to make the new journal fit.

The existing `Database.connect()` can create directories/databases and enables
WAL; its `read()` path also connects that way. The migration runner automatically
loads numbered SQL files. Therefore this proposal uses an explicitly initialized,
separate fixture schema, with no new numbered migration and no invocation of that
database bootstrap. Integration with the real controller store is a later gate.

The installed interpreter reported Python 3.10.11 and SQLite 3.40.1 without opening
a database. SQLite documents a WAL-reset corruption bug affecting older releases
under overlapping write/checkpoint activity on the same WAL database from separate
threads or processes; the fix is in 3.51.3 and specified backports. This is not
evidence of local corruption. This slice must use rollback-journal `DELETE` mode
and serial fixture access, leave the existing WAL policy unchanged, and defer
real/WAL runtime eligibility or upgrades to a separate review.
[SQLite WAL-reset advisory](https://www.sqlite.org/wal.html).

## Implementation instructions, effective only after approval

Act as the owner-directed controller maintainer, not a product worker. Use the
existing checkout, one agent, and this task's configured model/effort; no delegation
or product-worker selection. Keep runtime concurrency fixed at one.

### 1. Explicitly fixture-only storage

Create an import-inert persistence module. Importing it must not open a database,
create directories, discover configuration, initialize a service, or register a
migration. Require explicit fixture-root, database-path, program-ID, and fixture-ID
inputs. The harness must supply the exact approved temporary root and verify
resolved paths remain inside it, without symlink/reparse-point redirection.

Initialize the schema only in a verified-absent, create-new fixture database. A
reopen must use a fixture path/identity retained by this test run, not discovery of
an arbitrary existing database. Validate the fixture marker, program binding,
schema version/checksum, and expected schema on reopen. Unknown identities, schema
drift, partial setup, and incompatible versions fail closed; no repair, upgrade,
import, backup/restore, or reuse of another run's database.

Keep this schema's DDL inside the new persistence module. Do not create `0003_*.sql`,
change the existing migration runner, invoke `Database.initialize()`, or enroll the
fixture schema in application startup. Set and verify `journal_mode=DELETE`,
`synchronous=FULL`, `foreign_keys=ON`, `temp_store=MEMORY`, and a busy timeout no
greater than 1,000 ms. No WAL, attached databases, extension loading, background
checkpointing, vacuum, or threaded connections. Reopen normally for recovery;
do not apply SQLite's `immutable` shortcut to these mutable fixtures.

Use one synthetic program per database, at most 16 envelopes and 128 facts per
envelope. Validate input type and the existing 65,536-byte document limit before
decoding. Bound stored blob lengths and query cardinality before materializing
results, including when validating corrupted fixtures. Bound receipts/audit rows
as well as facts; reject over-budget appends atomically.

Persist the complete validated envelope, its embedded external-operation binding,
and append-only simulated facts, not just their digests. Preserve the existing
contract/hash domains and canonical representations. Verify recorded-byte hashes,
decoded domain hashes, and indexed fields against the retained source records.
Do not rewrite old v1 schemas or turn any synthetic authority flag true.

Add fixture-local, append-only audit events and durable command receipts keyed by
program plus idempotency key. Bind each receipt to the entire validated request
fingerprint and result. Exact replay must not append again or issue a new dispatch
capability; a reused key with different content must reject. Audit chaining proves
consistency within this fixture, not authenticity against a privileged database
editor or membership in the controller's production audit chain.

### 2. Atomic journal and conservative recovery

Write each logical mutation's source records, receipt, local audit event, derived
projection, and any epoch change in one explicit transaction. Use `BEGIN IMMEDIATE`
for write admission and account for SQLite busy/commit failures; do not rely on an
`executescript` implicit commit. No success receipt or capability may escape an
unconfirmed commit. Roll back failed transactions; if commit outcome is uncertain,
invalidate the instance and require verified reopen, without an automatic retry.
[SQLite transaction semantics](https://www.sqlite.org/lang_transaction.html).

Preserve append-only enforcement with database constraints/triggers as well as
application checks. Enforce contiguous fact indices, immutable bindings, monotonic
program fences, target/branch reservations, and a maximum of one held dispatch
barrier inside the same transaction as admission. Do not rely solely on a Python
lock or a cached projection. Rebuild through the existing
`rebuild_create_projection` and compare against the cache on every relevant load.
Cache or source inconsistencies fail closed rather than silently repairing data.

The first terminal outcome anchor, sticky terminal conflict, causal/freshness
checks, uncertainty, lease loss, and no-automatic-redispatch rules must survive
close/reopen and rebuilding from all retained facts. Ordinary later observations
must not clear a conflict. An uncontested late outcome after missing response or
lease loss may still quarantine under WCP-1R; do not confuse that with conflict
resolution. An uncontested no-start observation does not authorize redispatch of
the same effect.

Attaching a new coordinator must atomically advance the durable epoch and append
the required restart facts for unfinished work. Stale instances must be rejected
using the durable epoch, including across two connections. Failure partway through
attachment must not leave half the journal at a new epoch. Epoch/fact-budget
exhaustion fails closed; it does not create a release mechanism.

### 3. Separate durable-fake coordinator

Add a separate coordinator that accepts only the exact new fixture-journal type
and the existing exact inert fake driver. Reuse the committed domain contracts,
intent preparation, and recovery fold. Do not subclass or weaken the old exact
`FakeWorkspaceFactSink` gate, edit the old coordinator, accept arbitrary driver
callbacks, or add a native/default driver or application entry point.

Commit the envelope, simulated claim, and dispatch intent before returning an
ephemeral capability. Capabilities must be object-identity, instance/epoch,
envelope, owner, fence, and time bound; never serialize or reconstruct one from a
receipt. Validate fresh preflight/approval bindings at dispatch time. Commit the
one-use dispatch-consumption record before calling the fake driver, with the fake
call outside the SQL transaction. Persist the observation or uncertainty afterward
in its own atomic mutation. A crash or invalidated capability is never authority
to dispatch again.

Receipt replay, new coordinator attachment, stale epochs, a lost response, and
conflicting observations must make zero additional fake calls. Preserve the exact
old fake-driver gate: native adapters, subclasses, duck-typed replacements, and
objects claiming to be non-live must be rejected. Persisted simulated approval
records remain simulations; owner permission to test storage is not durable owner
approval for a product effect.

### 4. Tests and explicit non-claims

The new tests must cover at least:

1. Import inertness, explicit create-new initialization, verified fixture reopen,
   wrong root/fixture/program/schema rejection, and bounded malformed/oversize data.
2. Commit/reopen equivalence; rollback with no partial receipt/audit/projection;
   injected failures at initialization, admission, consumption, observation, and
   restart transaction boundaries; uncertain-commit handling with no capability.
3. Same-key replay and conflicting-key rejection, duplicate observations, index
   gaps, mutation/deletion rejection, invalid hashes, and projection corruption.
4. Durable program barrier, monotonic fences, target/branch reservations, and stale
   epochs. Use two connections in serialized same-thread tests for lock/staleness
   cases; no parallel writers, background threads, or WAL races.
5. WCP-1R timing boundaries and sticky-conflict sequences after actual reopen;
   first terminal anchor preservation; late quarantine versus permanent conflict;
   no-start and missing-response behavior with no redispatch.
6. An exact fake-call counter and durable-intent/consumption assertions proving
   fake dispatch does not precede commit and cannot be repeated after restart.
7. Six actual helper-process exit windows: `before_initial_commit`,
   `after_intent_commit`, `after_consume_commit`, `after_fake_call`,
   `before_terminal_commit`, and `after_terminal_commit`. Reopen only after the
   helper has terminated; verify the last committed records and conservative
   resulting projection. The before-commit cases must include an open transaction,
   not merely raise an exception after a completed rollback.

Use separate, newly created sacrificial fixtures for deliberate corruption tests;
no production or other run's database may be opened. Test-only corruption/setup
SQL and SQLite's normal journal recovery are included in the fixture grant below.
Keep crash orchestration in the test helper and test-controlled transaction steps,
not an arbitrary callback/native execution feature in the coordinator.

Process-exit tests exercise SQLite recovery and application ordering, not power
loss, hardware durability, adversarial Windows containment, or a distributed
exactly-once guarantee. SQLite's durability itself has filesystem/hardware
assumptions. [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html).

Create ADR-0023 as an additive fixture-persistence decision. It must preserve
ADR-0007 and ADR-0022; neither the generic controller aggregate nor its barrier,
production audit, migration stream, owner-approval receipts, or native executor is
integrated by this slice. Retaining the exact embedded operation binds fixture
records to that operation; it does not claim those deferred integrations exist.

Create the persistence readiness report and update the four named coordination
documents with actual evidence, resource usage, remaining gates, and any deviations.
Keep prior approvals, historical test/CI evidence, and the WCP-1 output/cache
deviations visible. Mark this checkpoint's new CI status as unverified unless a
separately authorized run is later independently verified.

## Exact file grants

All paths in the following blocks are relative to the controller checkout.

Create these **8 files only**:

```text
docs/decisions/ADR-0023-fixture-workspace-create-journal.md
src/fractilate_orchestrator/persistence/workspace_create_journal.py
src/fractilate_orchestrator/services/durable_workspace_create.py
tests/unit/test_workspace_create_journal_contract.py
tests/integration/test_workspace_create_journal.py
tests/integration/test_durable_workspace_create.py
tests/fixtures/workspace_create_journal/crash_probe.py
coordination/WORKSPACE_CREATE_PERSISTENCE_READINESS.md
```

Modify these **4 existing files only**:

```text
coordination/WORKSPACE_CREATE_READINESS.md
coordination/PROGRAM_STATUS.md
coordination/plans/ACTIVE_PLAN.md
coordination/NEXT_ACTIONS.md
```

Read this proposal, the two committed predecessor proposals, applicable repository
instructions, all 12 write targets, and these exact additional controller inputs:

```text
AGENTS.md
.gitattributes
pyproject.toml
docs/decisions/ADR-0002-sqlite-and-audit-model.md
docs/decisions/ADR-0003-fake-adapters-and-live-disablement.md
docs/decisions/ADR-0007-external-operation-aggregate.md
docs/decisions/ADR-0011-windows-host-containment.md
docs/decisions/ADR-0012-isolated-workspace-lifecycle.md
docs/decisions/ADR-0014-product-pilot-control.md
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

Normal imports and static checking may read controller Python modules and already
installed dependencies. Read-only Git identity/status/diff checks may detect drift
and inspect this work only; no unrelated diffs or configuration dumps. Existing
integration tests above are reference material, not permission to execute them.

Limit the change to **12 authored files, 3,000 added lines and 150 deleted lines
relative to the required controller commit**. Deletions are permitted only inside
the four coordination documents, not whole-file deletion. Include new files in
the count even while untracked. No renaming, old Python/test changes, manifests,
lockfiles, dependencies, installs, other SQL files, CLI/HTTP/scheduler wiring,
configuration changes, or broader formatting. Stop for revision if scope will not
fit; do not weaken tests or invariants to fit the budget.

## Fixture and verification grant

The only new generated-artifact root is:

`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp2-tests-20260827-01`.

It was absent during preparation. Verify absence again before creating it; stop
for a newly approved root if it exists. Use create-new semantics for fixture files,
logs, and distinct `pytest-1`, `pytest-2`, and `pytest-3` basetemp directories. Do not
reuse a basetemp. Set TEMP/TMP and all tool caches to descendants of this root.

Approval is a narrow exception to the normal no-local-database/no-schema-setup
rules: authorize creation, schema DDL, reads, writes, transaction recovery, and
test-only corruption of **only fixtures newly created by this approved run**.
SQLite may create, recover, truncate, and remove its own rollback journals as part
of transactions in those fixtures. This does not authorize manual deletion,
recursive cleanup, opening existing user/controller databases, or copying their
contents. Preserve main fixture databases, logs, and other retained artifacts.

Set a main-database cap of 4 MiB using verified page size and `max_page_count` on
every write connection. Limit each pytest iteration to 64 new fixture databases.
Stop at a 256 MiB aggregate retained-artifact budget; check usage before/after each
check process and at fixture allocation. Bound rows/blobs before writing. These
are application-level budgets, not a claim of a kernel-enforced disk quota.

### Checks

Use the existing `.venv/Scripts/python.exe` only. At most **three pytest iterations**,
each running exactly these **nine modules**, without coverage or plugin autoload:

```text
tests/unit/test_workspace_create_contract.py
tests/unit/test_workspace_create_intents.py
tests/unit/test_workspace_create_recovery.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
tests/unit/test_external_operations.py
tests/unit/test_workspace_create_journal_contract.py
tests/integration/test_workspace_create_journal.py
tests/integration/test_durable_workspace_create.py
```

Command shape: `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider
--basetemp <test-root>/pytest-<iteration>` followed by those nine exact paths.
The six existing modules must remain unchanged and process/database-free as before.
Only the three new modules may use the granted fixtures/helper.

Run Ruff lint and format checks on the **six new Python files** in the create
grant; pass `--no-cache` on every Ruff invocation, including any formatter. Run
strict mypy on the controller package with cache at `<test-root>/mypy`. At most
three iterations of each static check or formatter; no whole-repository formatting.
Do not install missing tools or run a full suite, build, live smoke test, or CI.

Use one check process at a time, a 300-second deadline per check, and at most 1 MiB
combined captured stdout/stderr per check. Launch shell-free with explicit paths
and hidden windows. Clear the child environment; allow only inherited SYSTEMROOT
and WINDIR plus literal TEMP/TMP and these explicit values:
`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONHASHSEED=0`,
`PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `PYTHONNOUSERSITE=1`.
Do not enumerate, print, or forward ambient credentials, PATH, or other variables.
No listener, SDK call, network, Git command, worker, or verifier from any test.

### Bounded crash-helper exception

The new integration tests may launch only this exact command shape, shell-free:

```text
C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/python.exe
  -I -B
  C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/tests/fixtures/workspace_create_journal/crash_probe.py
  <one of the six named cases> <validated run-fixture arguments>
```

The helper may read approved source/test modules and only its assigned newly
created fixture, and may use the same cleared environment. It must not accept
arbitrary code, SQL, import paths, commands, or external paths from arguments.
Permit at most six helper invocations per pytest iteration, one at a time, with
at most the pytest parent and one helper alive. This is a test-harness exception,
not an increase in controller or product-worker concurrency.

Each helper has a 15-second deadline and 64 KiB combined stdout/stderr limit. Emit
only a validated metadata frame of at most 4 KiB containing the named boundary,
fixture identity, and fake-call count; do not dump database contents or raw outcome
payloads. Deliberate `os._exit` is permitted only in that helper at the named crash
boundary, bypassing normal Python transaction cleanup. The helper must never
spawn descendants, run Git/SDK/network calls, or invoke a worker/verifier.

The parent must enforce limits, retain bounded diagnostics, and confirm the helper
has exited before reopening its fixture. On timeout/output-limit failure it may
terminate only its own known helper; if termination cannot be confirmed, stop all
further checks and report. If a parent check times out with a helper active, stop
the helper first, then the owned check process, and confirm both exits. Do not
claim production-grade Windows process-tree containment from this harness.

Any limit breach, unexpected external effect, or missing termination evidence
stops verification; do not silently enlarge budgets or use another iteration.
Record exact process counts, durations, output sizes, fixture totals, and results.

## Preserved exclusions and next gates

No staging/commit, push, publication, CI dispatch, branch/worktree creation or
switching, native Git creation, real workspace, live worker/verifier, controller
service, production migration/database access, runtime upgrade, or cleanup is
authorized. Leave previous temporary roots and the two historical unintended Ruff
cache files untouched; do not read the old raw failure diagnostics.

The product decisions 1-5 remain bound only to plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle
`a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
The immutable product base remains
`1ba3a7312fa99439b57ddb3b4433ead7e86b2c74`, not the current CM checkout HEAD.
The proposed product branch and isolated target remain
`codex/pilot-certified-recognition-engine-v1` and
`C:/Users/brian/Documents/Fractilate-Workspaces/cm-certified-recognition-engine-pilot-v1`.
Do not regenerate a packet or reinterpret those decisions as approval to execute.
`workspace.create/v1` remains separately unapproved.

After this slice, inspect the evidence and prepare the next bounded proposal
without waiting for another request to continue. Remaining work includes real
controller aggregate/audit/barrier integration; native Git execution, linked
identity, and containment under exact fixture authority; runtime eligibility;
an independently verified successor controller checkpoint and hosted-CI run;
and a freshly reviewed product packet. Publication/CI and every product effect
still require their own exact approvals. The old hosted run for controller
`32043774aa11eb25664e06adb8e09b130f9a53ed` does not certify this new checkpoint.

At the next authority boundary, present the concrete artifact and ask for the
needed approval. Report completed work, failed/skipped checks, scope or output
deviations, final scoped Git status/diff, and evidence limitations. Do not call
fixture durability native readiness or silently commit the new implementation.

## Suggested owner approval

> I approve CRSE-WCP-2 revision 2026-08-27.1, bound to the reviewed proposal's
> raw-file SHA-256: the 12 controller-file grants, fixture-only SQLite schema and
> database operations in the exact new temporary root, and the bounded checks and
> six-case crash-helper exception. I do not approve existing database access,
> native Git/workspace creation, workers/verifiers, services, commits, pushes,
> hosted CI, runtime upgrades, or manual cleanup. `workspace.create/v1` remains
> separately unapproved.

The file cannot contain its own full-file SHA-256; use the hash supplied with the
reviewed artifact. Any changed proposal needs a new review and hash. Tool-level
filesystem permission may also be required and does not replace owner approval.
