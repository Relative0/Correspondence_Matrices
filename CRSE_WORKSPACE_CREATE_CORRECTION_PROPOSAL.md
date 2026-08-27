# CRSE-WCP-1R: correct synthetic creation recovery before native work

Revision: **2026-08-27.1**. Status: **proposed; implementation not authorized**.

This document records a focused review and proposes the next bounded controller
maintenance change. It is not an execution instruction until the owner approves
this revision and its separately reported raw-file SHA-256. The earlier approval
of CRSE-WCP-1 does not silently authorize this correction or any native effect.

## Outcome of the review

Two reproduced defects should be corrected before building a native executor or
durable persistence integration on this state machine. The previously reported
206 passing tests remain valid historical results, but did not cover these cases.
No controller files were changed during this review.

### R1: evidence from before dispatch can establish simulated readiness

In `src/fractilate_orchestrator/services/workspace_create.py`, `_classify` checks
that the outcome report is dated at or after dispatch. It does not apply that
lower bound to the nested linked-workspace observation. It also checks the nested
evidence's age against the outcome's timestamp rather than the current observation
fact's timestamp. Those are different checks.

A read-only, in-memory probe used the existing deterministic fixture builders:

```text
preflight observed:       1000 ms
claim and dispatch intent:1001 ms
linked identity observed:1001 ms
dispatch and outcome:     1002 ms
actual result:           simulated_ready; barrier_held=false
```

The linked identity precedes dispatch, yet satisfies the current guard. It cannot
establish a post-creation condition. The correction must check causal order and
freshness of the nested evidence at the actual reconciliation time. Include a
regression for cumulative age: two individually acceptable timestamp gaps must
not make evidence older than the request's limit acceptable at reconciliation.
The cumulative-age case is an additional required test, not a separately executed
probe result from this review.

Review locations: service lines 95-141; domain
`src/fractilate_orchestrator/domain/workspace_create.py` lines 552-603. These are
baseline locations, not stable identifiers after editing.

### R2: contradictory outcomes can clear a conflict and its dispatch barrier

The fold detects a conflicting outcome only when the previous projection is
terminal. Once it becomes indeterminate, another outcome is classified without
preserving that conflict. `_classify` returns `rejected_before_dispatch` for a
no-start report before considering prior uncertainty.

A second read-only probe produced this sequence for the same envelope and fence:

```text
success evidence -> simulated_ready       / barrier=false
exit-code conflict -> indeterminate       / barrier=true
contradictory no-start -> rejected_before_dispatch / barrier=false
another effect, fence 2 -> arm accepted
```

All six original facts remained in the fake journal. The problem is the rebuilt
projection and barrier, not deletion of facts. The third report contradicts the
earlier started-process reports. Its arrival is not reconciliation authority.
The probe armed the second fake effect but did not dispatch it. No real process,
Git mutation, workspace, database, or product effect was used by the fake code.

Review locations: service lines 115-116, 225-254, and 476-487.

The diagnostic was a bounded Python invocation with bytecode disabled, isolated
Python mode, a cleared child environment, a 30-second deadline, and metadata-only
output. It exited zero. It imported existing synthetic fixture helpers but did
not invoke pytest or write a diagnostic script/log. The full suite, native tests,
and CI were not run. This was a focused recovery review, not a complete security
audit of every controller component.

## Exact starting state

Controller checkout:
`C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.

Require HEAD `32043774aa11eb25664e06adb8e09b130f9a53ed` and the eleven raw-file
SHA-256 values below. HEAD does **not** include the uncommitted WCP-1 implementation;
the manifest binds that additional working-tree input. No checkout, staging,
commit, branch/worktree creation, or reset is authorized to manufacture a match.

The approved predecessor proposal remains unchanged at
`C:/Users/brian/Documents/CM_Computation/CRSE_NEXT_CONTROLLER_WORKSTREAM_PROPOSAL.md`,
SHA-256 `56cd8963d94097b1902d5bf53313dcb7b5e772e1f4d44912477a44ed9b2c960e`.

All manifest paths are relative to the controller checkout. Hash raw bytes; do
not normalize line endings or silently refresh this manifest.

| Baseline file | Raw SHA-256 |
| --- | --- |
| `docs/decisions/ADR-0021-workspace-create-contract-bridge.md` | `cdbb6bfddc079b68d7daece787fcc1cd393103b0608161a374e31d9696f91c23` |
| `src/fractilate_orchestrator/domain/workspace_create.py` | `77797f3ad8d4a0cbbbf6bd98dc1b7d1168beb1c0b029b1be5e86926080f9f7e9` |
| `src/fractilate_orchestrator/adapters/workspace_create_intents.py` | `a5b1cbac43c8220944338b3ccf06ebfd50e89700e9b4410e60272167078304b8` |
| `src/fractilate_orchestrator/services/workspace_create.py` | `7db4546953f4f5780bf5c64a2714785875b2c986ce4d7d8db4ba120a7c5aeb34` |
| `tests/unit/test_workspace_create_contract.py` | `85885309664fe2647460364619407da37e5b7337abecfdc8e84a740abf2e0c66` |
| `tests/unit/test_workspace_create_intents.py` | `04b10b861fede73be3fbe92073f948b6137a1c86660a4022504a54ad69c293b7` |
| `tests/unit/test_workspace_create_recovery.py` | `304491497503fa06fc237144c0848167611f3387a4501f6cfaa20b956e4a3987` |
| `coordination/WORKSPACE_CREATE_READINESS.md` | `56265643101ee0cde2c83d58417ff6786a20cf3f66f882e13efbbd796245b701` |
| `coordination/PROGRAM_STATUS.md` | `5122947970dc028af6912f7d54bc5991e79a91cd1aa65a487d0c2bca511fc03c` |
| `coordination/plans/ACTIVE_PLAN.md` | `644b619b73eb62e870382ac07cd0eccb39d837970f659186f32e5d09804c0098` |
| `coordination/NEXT_ACTIONS.md` | `44dd15b71acbf0195d285cb472a5ad2f9920d4758c6efbaffc0231ab08ab58d8` |

Before editing, verify instructions, HEAD, these hashes, and the write targets.
If a hash differs, the proposed ADR already exists, or other controller source,
test, configuration, or tracked files have drifted, stop and report; obtain a
revised exact approval rather than repairing or rebasing the baseline. Preserve
the pre-existing untracked `coordination/prompts/` directory without reading it.
The pre-existing Git global-ignore permission warning is not a reason to inspect
or modify user configuration or claim an exhaustively clean working tree.

## Implementation instructions, effective only after approval

Act as the owner-directed controller maintainer, not a product worker. Use the
existing checkout and one agent, with no delegation. Use the current task's
configured model/effort; this does not select or launch a product worker.

### Correct R1 in the fake coordinator

Before allowing a ready result, require the nested linked identity to fall within
the actual dispatch-to-outcome interval and to remain fresh at the observation
fact's reconciliation timestamp. Preserve the existing preflight, lease, fence,
binding, process-stop, content, and Git-policy checks. Do not increase any limit.

Equality at a boundary may be accepted because the synthetic clock is in integer
milliseconds; evidence strictly before dispatch must fail closed. Future evidence
must fail closed. Check every applicable evidence age against the reconciliation
time, not only against another potentially old timestamp. Invalid or stale linked
identity must not establish ready state or release a held uncertainty barrier.

Implement this in the service's classification path using the existing domain
interfaces. Do not modify the immutable request/evidence schemas, intent bytes,
hash domains, or old v1 contracts to make the failing input appear valid.

### Correct R2 in the deterministic fold

Represent a detected contradictory terminal history explicitly and monotonically
in the rebuilt projection. Derive the conflict from validated, append-only facts;
an in-memory flag that disappears on rebuild or simulated restart is insufficient.
Once detected, ordinary later outcomes must not clear it, produce ready/rejected/
quarantined state, or release its barrier. This slice adds no conflict-resolution
effect, manual override, cleanup, or administrative release mechanism.

Preserve exact-byte duplicate observation idempotency. Preserve the distinction
between missing/uncertain evidence and contradictory evidence: an otherwise valid
late observation after response loss or lease loss may still yield quarantine
under the existing policy when no contradictory terminal history exists. An
uncontested positive no-start result must still reject without permitting a retry
of the same effect. Do not make every indeterminate result permanently terminal
as a shortcut.

Retain the existing conservative rule for differing terminal outcome fingerprints;
this slice need not broaden what counts as compatible terminal evidence. Hold the
program-wide dispatch barrier through repeated conflicting observations, duplicate
replays, and simulated restarts. A second effect must not arm while it is held,
even with a higher fence and a different branch/target. Preserve every source fact.

### Tests and decision record

Add regressions to the existing recovery test module using supplied synthetic
objects only. First reproduce the two findings in tests; then correct them.
Include at least:

1. Linked identity strictly before dispatch; exactly at dispatch; and after the
   outcome. Only correctly ordered evidence can establish readiness.
2. Identity/outcome individually within intermediate age limits but identity too
   old at reconciliation; exact-limit and over-limit boundaries.
3. Ready, conflicting terminal outcome, and a third no-start outcome: all history
   after the conflict remains indeterminate with the barrier held.
4. Repeated/reordered later conflicting outcomes, an exact duplicate, rebuilding
   from the full fact tuple, and coordinator restart preserve the conflict.
5. A second effect with a higher fence and non-overlapping coordinates is denied
   after conflict, including after the third outcome and restart; no extra fake
   driver call is made.
6. Existing successful creation, uncontested no-start, one-use capability,
   missing-response/lease-loss late quarantine, and malformed/partial-result
   behavior remain covered and passing.

Create ADR-0022 as a narrow amendment to ADR-0021's synthetic recovery rules,
reaffirming ADR-0007's append-only/conflict/barrier requirements. Explicitly record
what the owner approved and that no native or durable authority is added. Do not
rewrite the accepted ADR-0021 or change old audit/fencing semantics.

Update the four named coordination documents to distinguish the original 206-test
result, this review's findings, new regression results, and remaining native gates.
Preserve the WCP-1 tool-output deviation and historical approval/CI evidence.

## Exact grants

Paths in the following grant blocks are relative to the controller checkout.

Modify these **6 existing files only**:

```text
src/fractilate_orchestrator/services/workspace_create.py
tests/unit/test_workspace_create_recovery.py
coordination/WORKSPACE_CREATE_READINESS.md
coordination/PROGRAM_STATUS.md
coordination/plans/ACTIVE_PLAN.md
coordination/NEXT_ACTIONS.md
```

Create this **1 file only**:

```text
docs/decisions/ADR-0022-workspace-create-recovery-hardening.md
```

Read grants cover this proposal, the predecessor proposal, all eleven baseline
manifest files, the seven write targets, applicable repository instructions, and:

```text
AGENTS.md
pyproject.toml
docs/decisions/ADR-0003-fake-adapters-and-live-disablement.md
docs/decisions/ADR-0007-external-operation-aggregate.md
docs/decisions/ADR-0012-isolated-workspace-lifecycle.md
docs/decisions/ADR-0014-product-pilot-control.md
src/fractilate_orchestrator/domain/models.py
src/fractilate_orchestrator/domain/external_operations.py
src/fractilate_orchestrator/domain/workspaces.py
src/fractilate_orchestrator/domain/product_pilot.py
src/fractilate_orchestrator/state/external_operations.py
src/fractilate_orchestrator/state/workspaces.py
tests/conftest.py
tests/unit/test_external_operations.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
```

Normal imports and static checking may read installed dependencies and controller
Python modules. Non-mutating Git identity/status/diff checks may detect drift and
review only this change; do not dump unrelated diffs or configuration. No product
code or prompt writes, unrelated untracked contents, `.env*`, private keys, token
caches, credential stores, or local database reads are granted.

Limit this correction to **7 authored files, 700 added lines and 100 deleted
lines relative to the manifest baseline**, not relative to HEAD. No file deletion,
renaming, unrelated formatting, package/dependency change, installation, SQL,
migration, entry-point wiring, or machine-policy change. Count the new ADR in the
budget. If the correction cannot fit, stop for a revised proposal.

## Bounded verification grant

Use the existing controller `.venv/Scripts/python.exe`. Do not install tools.
Authorize at most **three pytest iterations**, one check process at a time:
iteration 1 establishes the new red regressions; iteration 2 verifies the fix;
iteration 3 is reserved for an in-scope correction if necessary. Each iteration
runs exactly these six modules, without coverage or plugin autoload:

```text
tests/unit/test_workspace_create_contract.py
tests/unit/test_workspace_create_intents.py
tests/unit/test_workspace_create_recovery.py
tests/unit/test_workspaces.py
tests/unit/test_product_pilot.py
tests/unit/test_external_operations.py
```

Command shape: `.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider
--basetemp <test-root>/pytest-<iteration>` followed by those six exact paths.
Keep the changed tests process-free; no native Git, listener, SDK, database,
network, worker, or verifier effect may be launched from them.

Also run Ruff lint and format checks on the two changed Python files with
`--no-cache` on **every** Ruff invocation, including any formatter. Run strict
mypy on the controller package with its cache explicitly under `<test-root>/mypy`.
At most three iterations of each static check; no whole-repository formatting.

The sole additional write root for generated check artifacts is:

`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp1r-tests-20260827-01`.

It was absent during preparation. Recheck before creation: if present, stop and
request another exact root. Use create-new semantics for logs and a distinct,
verified-absent `pytest-1`, `pytest-2`, or `pytest-3` child. Never reuse a pytest
basetemp or delete an existing directory. Set TEMP/TMP to this new root. Preserve
the outputs; cleanup is not included.

Launch checks with a cleared environment. Permit only `SYSTEMROOT`, `WINDIR`,
literal TEMP/TMP paths, `PYTHONDONTWRITEBYTECODE=1`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONHASHSEED=0`, `PYTHONUTF8=1`,
`PYTHONIOENCODING=utf-8`, and `PYTHONNOUSERSITE=1`. Never enumerate, print, or pass
ambient credential variables. Use explicit interpreter paths and shell-free
argument lists for check children, hidden windows, and bounded output capture.

Each check is limited to 300 seconds and 1 MiB combined stdout/stderr. Stop after
a limit failure; do not silently increase the budget or resume another iteration.
Do not claim that this maintenance harness proves native Git host containment.
Full suite, build, hosted CI, real-Git/disposable-worktree fixtures, native process
tests, and live smoke tests remain deferred. Record failures or missing tooling
without broadening scope.

## Preserved exclusions and subsequent gates

Do not commit, push, publish, dispatch CI, create or switch a branch/worktree,
start a service, touch a real controller database, or run cleanup. The original
two unintended Ruff cache files remain intact and outside this write grant:

```text
.ruff_cache/0.16.2/12345713942685985175
.ruff_cache/0.16.2/14620263680379791801
```

Their deletion is a separate optional approval, not a prerequisite for this fix.
Do not touch the WCP-1 temporary root or read its raw failure diagnostics.

The original product approval remains bound only to plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle
`a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
No packet is regenerated or treated as durably approved in this correction.

After the correction, review the regressions and resulting diff. Then propose
concrete native executor, linked-worktree identity, and durable-operation linkage
work with exact file grants and separately bounded native fixture authority.
This proposal authorizes none of that implementation. Further prerequisites are
an independently verified new controller checkpoint/CI run, a freshly reviewed
successor product packet, and separate approval for the exact `workspace.create/v1`
effect. Workers, verifiers, cleanup, merge, and every later effect remain gated.

At completion report the exact edits, tests/checks and results, limits consumed,
any deviations, and final scoped Git status/diff. Do not claim native readiness.

## Suggested owner approval

> I approve CRSE-WCP-1R revision 2026-08-27.1, bound to the reviewed proposal's
> raw-file SHA-256: the seven controller-file grants and bounded fake-only checks
> in the new exact temporary root. I do not approve native executor or persistence
> implementation, real workspace creation, worker/verifier execution, commits,
> pushes, CI dispatch, or cleanup.

The file cannot contain its own full-file SHA-256; use the hash supplied with the
reviewed artifact. A changed proposal requires a new review and hash. Tool-level
permission to write the controller checkout may also be required; it does not
substitute for owner approval or authorize a product effect.
