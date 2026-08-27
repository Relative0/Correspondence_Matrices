# CRSE next controller workstream: contract bridge and fake-only creation tests

Proposal: `CRSE-WCP-1`

Revision: `2026-08-27.1`

Status: prepared for owner approval; implementation NOT authorized by this document.

## Decision requested

Approve one bounded **controller-maintenance implementation**, described below. It will reconcile the product-pilot and workspace contracts and implement a creation coordinator exercised only with supplied evidence and fakes. It will produce code, regression tests, and a readiness report, not merely another design proposal.

This is not approval to execute `workspace.create/v1`, create a branch/worktree, run a product worker or verifier, or alter the approved product packet. It does not finish the native workspace adapter or make the pilot executable.

The owner previously approved decisions 1-5 for the exact historical hashes below and explicitly withheld workspace creation. That approval remains confined to those bytes. It is recorded in the conversation, not asserted here to be a durable controller authorization.

## Preserved product decisions

| Item | Existing approved value |
| --- | --- |
| Product-pilot plan SHA-256 | `3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373` |
| Bundle SHA-256 | `a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815` |
| Controller checkpoint | `32043774aa11eb25664e06adb8e09b130f9a53ed` |
| Hosted-CI run | `32719533654` |
| Product base commit | `1ba3a7312fa99439b57ddb3b4433ead7e86b2c74` |
| Product branch | `codex/pilot-certified-recognition-engine-v1` |
| Intended exact product workspace | `C:/Users/brian/Documents/Fractilate-Workspaces/cm-certified-recognition-engine-pilot-v1` |
| Product worker | `gpt-5.6-sol`, effort `xhigh` |
| Product worker prompt SHA-256 | `b40fd899b20c8615e94e0f134500fc49a99d291e3139aa9fc9eb327682269d77` |
| Product scope correction | 20 create-new files and 12 exact read grants; 32 grants total |

The earlier prompt commits remain historical inputs. Do not edit their contents, silently change the product base to current HEAD, or infer missing packet fields from this summary. The original verifier, environment, temporary-root, and limit choices are not changed by this proposal. The controller test settings below are separate from the product verifier settings.

## Findings behind the next step

1. **The two current contracts disagree.** The product contract requires `codex/pilot-*`. The existing workspace-v1 contract requires `codex/workspace-<identity>` and derives a child directory beneath `approved_workspace_root`. A pure, non-mutating compatibility check using the previously supplied inputs produced branch `codex/workspace-d5fa44ba570e69de` and target `C:/Users/brian/Documents/Fractilate-Workspaces/cm-certified-recognition-engine-pilot-v1/fractilate-d5fa44ba570e69de1a9d979d`, not the approved branch and intended exact workspace. Prior schema-level review did not establish end-to-end compatibility.
2. **Existing dispatch remains inert.** Workspace-v1 is fixture-only and forbids Git mutation. The external-operation service accepts only its exact fake driver type. There is no approved native workspace-creation path to invoke.
3. **Linked-worktree evidence needs its own contract.** The existing read-only observer rejects a Git administrative directory outside the observed repository root. A linked worktree normally has such an external private administrative directory. Do not weaken that observer to accommodate a live worktree.
4. **Historical observation hashes are not fresh content snapshots.** The previous status and raw-diff metadata hashes do not establish byte-for-byte preservation of the primary working tree or its entire Git directory. CM has advanced since the approved base and has unrelated local work. Fresh, explicitly scoped evidence will be required before a future effect.
5. **New controller code needs new checkpoint evidence.** The historical CI success cannot certify code added after that checkpoint. Native process control, durable workspace-operation linkage, and independent verification remain separate outstanding prerequisites.

At preparation, the controller HEAD was still the checkpoint above; its untracked `coordination/prompts/` directory was left untouched. The product base still existed and was an ancestor of current HEAD. The product worker prompt's raw-byte hash still matched. The hosted run was independently checked on 2026-08-25; it was not re-verified during this preparation: [historical CI run](https://github.com/btheorystartups/Fractilate-Orchestrate/actions/runs/32719533654).

Relevant local contracts: [workspace v1](C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/src/fractilate_orchestrator/domain/workspaces.py:113), [product pilot](C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/src/fractilate_orchestrator/domain/product_pilot.py:173), [inert dispatch gate](C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/src/fractilate_orchestrator/services/external_operations.py:214), and [read-only observer](C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/src/fractilate_orchestrator/adapters/read_only_git.py:104).

## Implementation instructions, effective only after owner approval

### 1. Role, checkout, and boundaries

Act as the owner-directed controller maintainer in `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`, not as a product worker dispatched through the Orchestrator. Work in the existing checkout. Do not create or switch branches or worktrees. Do not delegate to other agents.

Before editing, recheck HEAD, repository instructions, and the exact write targets. Require controller HEAD `32043774aa11eb25664e06adb8e09b130f9a53ed`. If it changed, a proposed new file already exists, or an existing write target has unrelated edits, stop and report the conflict. Do not overwrite or reinterpret the approval. Unrelated dirty paths are not a reason to clean or reset anything.

Implement only additive contracts and fake-only orchestration. Preserve existing v1 serialized bytes, hash domains, validators, event/fencing semantics, tests, and `Literal[False]` authority flags. Do not broaden the existing fake dispatch gate or wire a new service into CLI, HTTP, scheduler, SDK, or database entry points.

### 2. Reconcile exact identity without silently migrating approvals

Create a versioned, immutable workspace-create request and pilot-binding envelope in a new module. Use explicit, distinct fields for the allowed parent and the exact target. The human-readable branch and target are explicit request inputs; the stable identity binds them and must not replace them with generated names.

Specify canonical serialization and domain-separated hashes. Keep the dependency graph acyclic: exact request inputs and their digest first, pilot/binding references next, external-operation envelope last. Do not derive a path from a bundle digest when that bundle also contains a prompt or working directory depending on the derived path. Hash equality proves identity, not human permission.

The bridge must compare checkpoint, repository binding, source, exact base, branch, exact target, worker working directory, contract versions, effect identity, and evidence references. Reject missing or conflicting values. A legacy v1 mismatch remains a mismatch: do not coerce it into compatibility or mark the historical packet executable. Model a successor candidate separately, requiring fresh owner approval before use. Do not regenerate the real product packet in this slice.

Add ADR-0021 documenting the additive extension and its precise relationship to ADR-0012 and ADR-0014. Supersede only the naming/binding assumptions necessary for the new contract; retain the old contracts for existing callers and retain all live-disablement rules. Do not change audit or fencing guarantees to make the new design easier.

### 3. Implement intent generation and a fake-only coordinator

Provide deterministic typed command intents with explicit executable identity, argv, working directory, environment-name policy, limits, and expected evidence. They are data, never shell strings to execute. The only callable driver in this slice must be an exact, inert fake that records intents and returns supplied outcomes. Reject arbitrary callbacks, subclasses, and adapters that claim live execution is available. Use an in-memory fake fact sink, not controller persistence.

Model the create-only sequence: validate binding and fresh evidence; check exact effect/fence/lease; record simulated claim and dispatch intent; consume a single-use fake dispatch capability; collect supplied outcome and linked-worktree evidence; classify the result. Clearly label all generated facts as simulated. No real approval is consumed and no real operation is claimed.

Creation intent must use the exact immutable base and branch, refuse an existing branch or target, and contain no force/reset/remote-guessing behavior. The intent must not include cleanup, recovery mutation, branch deletion, checkout of the primary repository, fetch/pull, submodule initialization, LFS execution, or any network action. Repeated identical requests must not yield a second simulated dispatch. Unknown completion must not trigger an automatic retry.

Do not expose even an unused subprocess/native runner in these modules. Keep imports and public constructors auditable. Pure path handling is acceptable; filesystem discovery is not part of the new service. Existing repository code may be read and existing pure tests may run under the separate grants below.

### 4. Evidence and failure semantics

Define evidence for the source repository, exact target, private Git administrative directory, common Git directory, backlink, HEAD, branch, cleanliness, and observation freshness. Parse supplied bounded fixtures; do not read any real target. Require all relationships to agree. A linked worktree's private admin name must be observed, not guessed from the target basename.

Separate status/diff metadata digests from content-manifest digests. A manifest must state its scope, exclusions, completeness, and capture identity. Incomplete or secret-excluding evidence must not claim a complete filesystem snapshot. Future source-Git evidence must distinguish permitted new branch/worktree metadata from protected pre-existing state: creating a linked worktree cannot leave the entire source `.git` byte-identical.

Reject ambiguous Windows paths, case aliases, traversal, alternate streams, device/UNC spellings, protected-root overlap, and supplied symlink/junction/reparse-point or changed-identity evidence. Lexical checks are not proof against a filesystem race; native handle/identity checks are deferred and must remain an explicit blocker.

Classify at least: rejected before dispatch; simulated ready with complete matching evidence; known partial result requiring quarantine; and indeterminate completion requiring investigation. An exit code of zero alone is insufficient. Stale fences, lease loss, restart, malformed/truncated output, exceeded limits, absent stop proof, and partial writes must never produce ready state or automatic cleanup/retry. Reconcile a stale outcome without granting its stale claimant authority to perform another effect.

### 5. Test the hidden Git effects without executing Git

Use hostile supplied configuration/attribute evidence in tests. Unknown policy evidence must fail closed. Cover hooks, clean/smudge/process filters, fsmonitor helpers, configuration includes, automatic maintenance, prompts, remote helpers, and submodule behavior. No test may execute those helpers.

A future native executor must prove these are disabled or rejected before mutation and separately prove process-tree termination and its filesystem/network boundary. Environment variables or a few `-c` options alone do not establish containment.

Git documents that worktree creation shares repository state and that `-B` can reset an existing branch; `worktree add --dry-run` is not a supported substitute for a fake executor. See [git-worktree](https://git-scm.com/docs/git-worktree). Checkout can invoke configured filters, including persistent processes: [gitattributes](https://git-scm.com/docs/gitattributes). Hooks and fsmonitor are additional configurable execution surfaces: [git-config](https://git-scm.com/docs/git-config).

## Exact implementation grants

All paths in the next two blocks are relative to the controller root above. No CM product code or product prompt writes are granted. The proposal file itself is an input, not an authority source.

Create these 8 files only:

```text
docs/decisions/ADR-0021-workspace-create-contract-bridge.md
src/fractilate_orchestrator/domain/workspace_create.py
src/fractilate_orchestrator/adapters/workspace_create_intents.py
src/fractilate_orchestrator/services/workspace_create.py
tests/unit/test_workspace_create_contract.py
tests/unit/test_workspace_create_intents.py
tests/unit/test_workspace_create_recovery.py
coordination/WORKSPACE_CREATE_READINESS.md
```

Update these 3 files only, with concise current-status additions/corrections that preserve historical evidence:

```text
coordination/PROGRAM_STATUS.md
coordination/plans/ACTIVE_PLAN.md
coordination/NEXT_ACTIONS.md
```

Read permission includes the 11 write targets and these existing files; it does not grant execution of their workflows:

```text
AGENTS.md
pyproject.toml
docs/decisions/ADR-0001-repository-boundary.md
docs/decisions/ADR-0002-sqlite-and-audit-model.md
docs/decisions/ADR-0003-fake-adapters-and-live-disablement.md
docs/decisions/ADR-0005-read-only-git-observer.md
docs/decisions/ADR-0007-external-operation-aggregate.md
docs/decisions/ADR-0011-windows-host-containment.md
docs/decisions/ADR-0012-isolated-workspace-lifecycle.md
docs/decisions/ADR-0013-independent-verifier-contract.md
docs/decisions/ADR-0014-product-pilot-control.md
src/fractilate_orchestrator/domain/models.py
src/fractilate_orchestrator/domain/workspaces.py
src/fractilate_orchestrator/domain/product_pilot.py
src/fractilate_orchestrator/domain/external_operations.py
src/fractilate_orchestrator/domain/verifiers.py
src/fractilate_orchestrator/state/workspaces.py
src/fractilate_orchestrator/state/external_operations.py
src/fractilate_orchestrator/services/external_operations.py
src/fractilate_orchestrator/services/product_pilot.py
src/fractilate_orchestrator/adapters/git_workspace.py
src/fractilate_orchestrator/adapters/fake_git_workspace.py
src/fractilate_orchestrator/adapters/read_only_git.py
src/fractilate_orchestrator/adapters/inert_external_operation.py
src/fractilate_orchestrator/persistence/external_operations.py
tests/conftest.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
tests/unit/test_external_operations.py
```

Normal imports/type-checking may read installed dependencies, tracked controller Python modules, and applicable repository instructions. Bounded, non-mutating Git identity/status/diff checks are allowed to detect drift and review only this work. Do not dump Git configuration or unrelated diffs. No `.env*`, credential stores, tokens, private keys, local databases, or unrelated untracked file contents may be read, printed, edited, or committed. Broader implementation reads/writes require an explicit grant amendment.

Limits: 11 changed files, at most 3,000 added lines and 100 deleted lines; deletions only in the three coordination documents. One implementation agent; one check process at a time; no subprocesses launched by new code/tests. No dependency installation or new dependencies. Do not edit package manifests, lockfiles, existing source/tests, CI, SQL, security policy, or machine settings.

## Required acceptance tests

| Area | Required result |
| --- | --- |
| Compatibility regression | Existing v1 vectors and false authority flags remain unchanged; pilot/workspace naming and target mismatch is explicitly rejected. |
| Successor contract | Synthetic exact-branch/exact-target binding round-trips; changing any authority-relevant field changes the proper digest; no self-referential hash requirement. |
| Approval separation | Missing, stale, wrong-contract, wrong-bundle, or wrong-effect evidence cannot create a fake capability; a human approval string or hash alone never authorizes execution. |
| Path and Git identity | Case/junction/escape/overlap/backlink/common-directory/base mismatches fail closed; valid synthetic linked-worktree evidence is accepted only for its exact binding. |
| Intent policy | Exact argv/cwd/environment/limits are asserted; forced branch reset, implicit HEAD, remote guessing, cleanup, and helper execution are rejected. |
| Failure and recovery | Duplicate request, lease loss, stale fencing, restart at each boundary, partial results, output overflow, timeout, and unknown termination cannot redispatch or report ready. |
| Non-execution | AST/import/call-boundary checks and fake counters establish that no native runner, Git effect, network call, listener, SDK turn, database mutation, or real workspace inspection occurred. |
| Evidence honesty | Metadata-only/incomplete snapshots and fake facts cannot satisfy native-readiness or full-preservation claims. |

Use the existing `.venv/Scripts/python.exe`; it was present during preparation. Check tooling availability without installing anything. Run the six unit-test files listed below, Ruff on the six new Python files, and strict mypy on the controller package with a dedicated cache directory. If tooling is missing or a failure is pre-existing, report it and do not broaden scope to repair it.

```text
tests/unit/test_workspace_create_contract.py
tests/unit/test_workspace_create_intents.py
tests/unit/test_workspace_create_recovery.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
tests/unit/test_external_operations.py
```

Test command shape: `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --basetemp <test-root>/pytest-<iteration>` followed by those six exact paths. Use a distinct, verified-absent child (`pytest-1`, `pytest-2`, or `pytest-3`) for each iteration. Set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and disable bytecode writes. Use Ruff `--no-cache`; direct mypy's cache to `<test-root>/mypy`.

The only additional write grant is synthetic test/cache output under `C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp1-tests-20260827-01`. This path was absent during preparation. Recheck before creating it; if present, stop and request a new exact root. Never reuse an existing pytest basetemp, delete an existing tree, or place test output in a product workspace. Set TEMP/TMP to that dedicated root for checks. Preserve outputs for review; cleanup is not granted.

Each check has a 300-second wall-time budget and a 1 MiB captured-output budget; stop after a limit failure. At most three focused test iterations. These are implementation-task limits, not claims that the future native sandbox is implemented. The full test suite, package build, hosted CI, disposable real-Git fixtures, and live smoke tests are outside this fake-only approval; report them as deferred, never passed.

## Completion and the gates that remain

Report exact changed files, checks and results, unresolved blockers, and final scoped diff/status. In `WORKSPACE_CREATE_READINESS.md`, distinguish simulated evidence from native evidence and explicitly state **live workspace creation remains disabled**. Do not claim the historical owner approval is durably stored. Do not commit, push, open a PR, start a listener, migrate a database, or dispatch any operation.

After this slice, the remaining sequence is:

1. Review this code and authorize any subsequent native-executor/durable-linkage work separately. Prove safe process launch/termination, linked-worktree filesystem identity, bounded observations, and recovery with separately approved fixtures. A fake-only pass does not satisfy those gates.
2. Obtain separate authorization for commits/publication or CI dispatch as needed. Select and independently verify the resulting exact controller SHA and its hosted-CI run; the old run cannot certify the new implementation.
3. Prepare a successor product packet with the reconciled contract, fresh properly scoped evidence, exact effect payload, and a field-by-field comparison to the previously approved packet. Preserve product choices where possible; obtain renewed approval for the changed packet/hashes. No silent transfer of approval.
4. Only when the required live prerequisites and exact packet are ready, ask separately for **that exact `workspace.create/v1` effect**. Workspace creation still does not approve worker execution, verification, cleanup, merge, or any later effect.

## Suggested owner response

> I approve implementing CRSE-WCP-1 revision 2026-08-27.1 as specified in the reviewed proposal: the 11 controller-file grants, dedicated synthetic test root, and bounded fake-only checks. I do not approve real workspace creation, live worker/verifier execution, commits, pushes, or other external effects. My earlier product approval remains bound only to its original plan and bundle hashes.

Bind that response to the proposal's raw-file SHA-256 supplied alongside this document. The file cannot contain its own full-file hash. If the document changes, review and hash it again. Tool-level permission may also be needed because the controller repository is outside this task's writable workspace; that is separate from authorization for a product effect.
