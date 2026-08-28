# CRSE-WCP-3B: grouped offline development, verification and local checkpoint

Revision: **2026-08-28.1**. Status: **proposed; not approved**.

## One requested approval, three ordered stages

Approve the bounded offline batch below as one decision:

1. Correct and qualify the test-command assembly/supervisor continuation.
2. Complete the fixture linkage, regression tests and fix/retest cycles, then
   record final evidence and scope.
3. Only after the acceptance gates pass, create **one local controller commit**
   containing exactly the nineteen listed files. No push or hosted CI.

This consolidates foreseeable development and testing decisions at the owner's
request. It does not approve production installation, product execution, network
activity or cleanup. The existing WCP-3V approval did not authorize this batch.

The changes to existing authority are explicit: three additional synthetic
self-check attempts; two additional pytest iterations; larger but finite static
check allowances; cumulative WCP-3 line ceilings of **4,000 additions / 300
deletions** across the same eleven logical files; and the conditional nineteen-file
local checkpoint. These are proposed increases, **not resets or already consumed
authority**. Preserve all old evidence, failures and usage counts.

## Why a grouped continuation is needed

WCP-3V's exact rename succeeded, with bytes unchanged:
`tests/integration/test_workspace_create_linkage.py` became
`tests/integration/test_linked_workspace_create.py`, raw SHA-256
`5df3224cc19755533b34fbc222eab13814c83bfe861c91b745129d29946cf1cd`.

All nineteen continuation source/baseline hashes, thirty-six earlier evidence
files and five runtime identities matched before that move. The final synthetic
self-check then stopped in its prelude: assistant string assembly produced
`unction Get-CRelation` instead of `function Get-CRelation`. The splice advanced
one character past a four-character here-string terminator. No assertions, Python/
Ruff check application, pytest, fixture database or live effect ran.

The attempt is consumed. Its root-local failure record was authored afterward
from the tool result and says so; it is not a passed self-check. The underlying
qualified process classifier was not changed. A corrected assembly reference
was prepared in memory but was not executed or claimed verified. Do not repeat
attempt 2, overwrite its record, or run checks under the old exhausted allowance.

## Immutable parents and exact baseline

Read the applicable controller AGENTS.md, current coordination/ADR records,
complete parent packets and their required source/reference inputs. Parent packets
remain immutable in `C:/Users/brian/Documents/CM_Computation`:

- `CRSE_CONTROLLER_LINKAGE_IMPLEMENTATION_PROPOSAL.md`, revision 2026-08-28.1,
  raw SHA-256 `448cff9a24be92f5d2e518812cb1b27ef6b49a799a6c50a1b851460cc1dbd37c`.
- `CRSE_WCP3_TEST_FILENAME_AMENDMENT.md`, revision 2026-08-28.1,
  raw SHA-256 `35f40256be2458a3b0d25d96995554627825e67dde64fc32bae0edee7404d8a4`.

Controller: `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.
Require HEAD `b9dd7724a205ef08b5655839ca6db7dd97b5774e`, an empty index,
the following nineteen working-file versions and no other tracked drift.
Preserve untracked `coordination/prompts/` unread. The old integration filename
must remain absent. Do not switch, reset, repair or clean to obtain a match.

The first eleven are the existing WCP-3 implementation/write scope. They may
receive in-scope corrections; no new implementation file or further rename is
granted. Old Python, tests, SQL, dependencies, configuration, migrations and entry
points remain read-only.

| WCP-3 writable file | Starting raw SHA-256 |
| --- | --- |
| `src/fractilate_orchestrator/persistence/workspace_create_linkage.py` | `c3ed93e1010943158fead30ac3db65d325caaa5d44465d5a55b3344f71669a8c` |
| `src/fractilate_orchestrator/services/linked_workspace_create.py` | `9d48d169a7fbd1f0163ad17bb0b9a09328017f2fa16593dacc60bde41b2ead51` |
| `tests/unit/test_workspace_create_linkage.py` | `44830b5071ed5c738aad0cf55a37b11c76588b111322ee1e67e3a692503d88a6` |
| `tests/integration/test_linked_workspace_create.py` | `5df3224cc19755533b34fbc222eab13814c83bfe861c91b745129d29946cf1cd` |
| `tests/fixtures/workspace_create_linkage/fixture_store.py` | `99453a48ac9432065a6bbac640d2080ef056c2a78d8fc29fb8d60ee8222cf242` |
| `docs/decisions/ADR-0024-fixture-controller-workspace-linkage.md` | `99d20c78a5fe7de2562876fac043a9767353b571f505addd37ced7dfe9d67399` |
| `coordination/WORKSPACE_CREATE_LINKAGE_READINESS.md` | `8d51fbfdfc0b0ea34bb91f9e40f52546d13f44570213ffc11092569852ba3176` |
| `coordination/WORKSPACE_CREATE_READINESS.md` | `14dfbbcd455e1ac55b8b770cfa081b1205705671c397cac001a47ed5881e4160` |
| `coordination/PROGRAM_STATUS.md` | `05911ec857b74a0421373322e54e16ca1c64cd549e36fa64dcea62ee6aae6c26` |
| `coordination/plans/ACTIVE_PLAN.md` | `df91d0efd0beeaa2f6db009050852f13ce1da82a495bff8105e06833ed4244e1` |
| `coordination/NEXT_ACTIONS.md` | `882d4353dcb85bb1a7040592b4b10494ce34fd8c3eff380cf28272463aa2fcd6` |

The remaining eight are preserved WCP-2C inputs: read-only during development,
included unchanged in the final checkpoint only if its gates pass.

| Preserved WCP-2C file | Required raw SHA-256 |
| --- | --- |
| `docs/decisions/ADR-0023-fixture-workspace-create-journal.md` | `d8703229281a4ffb3a1a0680c17d9e27af0919e9b7b949d2d4ac47af746192bc` |
| `src/fractilate_orchestrator/persistence/workspace_create_journal.py` | `3194c6a8b53591e4f327395d77e23c07c31d805334a4c247be9c3f1238d0d60d` |
| `src/fractilate_orchestrator/services/durable_workspace_create.py` | `72ebf2dc7f1b6cef9b8eb60ed7e5e7d38793d063e0eb051a8ee736d2205d0bea` |
| `tests/unit/test_workspace_create_journal_contract.py` | `892b6babe0ef3349dc88740a6d651d402421cdbdb07c21e771acfe3582f8b5b8` |
| `tests/integration/test_workspace_create_journal.py` | `9a9aa012d1a33df1b6601cfa6ad83a778f4b981082e4bfc2c78b07779c987936` |
| `tests/integration/test_durable_workspace_create.py` | `9e56568aa9769331329cd395efbf9e142518b0694dea4735b62263d9e61c873e` |
| `tests/fixtures/workspace_create_journal/crash_probe.py` | `301a132a45e8e62a2a58507d7380c49faed727b2468868efc60a141108d5e8a0` |
| `coordination/WORKSPACE_CREATE_PERSISTENCE_READINESS.md` | `2de68f61db96f7a38d95dfecb9e64e3271a426b2b74244cf3ecb78f7ca09ad86` |

Revalidate this packet's separately supplied owner-approved raw SHA-256, both
parents, all nineteen source hashes, five parent runtime hashes and retained
evidence before new writes/checks. Normal imports/static analysis may read the
package/dependencies. No secrets, credential files, ambient environment dumps,
unrelated diffs, product inspection or existing controller database access.

One maintainer, this task's configured model/effort, concurrency one; no delegation.

## Stage 1: assembly correction and qualification

Reuse the actual qualified WCP-3 supervisor preserved in WCP-3V's appendix.
Do not run that historical body unchanged. Keep its identity/classifier,
no-helper/two-process, pipe, output, error-retention and shutdown policies.

Fix the assembly defect by preserving complete function definitions, not by
advancing a magic character count past a delimiter. In particular, if splitting
a here-string, use the actual delimiter's length and verify the resulting
definition begins with `function Get-CRelation`. Do not execute code fragments
merely because an earlier syntax parse succeeded.

Allow up to **ten parent-only syntax/assembly preflights**, each <=30 seconds and
4 KiB evidence, with create-new `preflight-1.json` through `preflight-10.json`.
They may compare strings and inspect PowerShell tokens/AST without executing the
candidate runner, classifiers, external programs, database code or network work.
These are not qualified self-check passes. This explicit allowance is intended
to catch command-construction errors before spending a formal verification slot.

Then allow synthetic attempts `supervisor-selfcheck-3.json`,
`supervisor-selfcheck-4.json`, `supervisor-selfcheck-5.json`: each no subprocess/
database, <=30 seconds/4 KiB and create-new. Prior attempts 1 and 2 stay consumed.
A prelude/ordinary assertion failure consumes its attempt and may be corrected
before the next unused one. If failure precedes normal evidence creation, record
the observed failure separately in that attempt's named record, explicitly
identifying reconstruction and unavailable timings. Never manufacture success.

Qualify full script syntax, exact corrected nine/five target lists, allowed
remaining check names, rejection of old filenames/out-of-budget names, retained
root binding, host identity/count, no helper or host-descendant admission, primary
and cleanup error retention, open-stream accounting and known-root process peak.
Exercise the same pure classifier definitions used by the real runner.

Only a passed new formal self-check may gate a real check. Its evidence must bind
the original WCP-3 hash, WCP-3V hash, this packet's separately supplied approved
hash and the actual adapted runner identity. Real-run preflight must verify those
bindings, this packet's raw hash and the historical result identities. Failed
attempt 2 is preserved as a known assembly failure, not treated as passed.
Changing qualified runner behavior later requires another available formal
self-check. No local helper executable or script is created.

## Stage 2: bounded implementation and verification

Preserve all original WCP-3 behavioral requirements: independent authoritative
folds, sticky workspace-conflict veto, combined program barrier, fixture SQL bypass
guards, actual controller audit/external-operation APIs in one transaction,
poison-on-rejection, verified reopen, typed/raw bounds, durable epoch/fences,
permanent reservations and exact-fake consumption-before-dispatch ordering.
Do not weaken checks or skip failing cases to obtain a pass.

The cumulative line budget becomes 4,000 additions / 300 deletions, still eleven
logical WCP-3 files. At this boundary it is **2,770 additions / 46 deletions**.
Count the seven created files by final line count; conservatively add subsequent
four-document deltas to the existing **74 coordination additions / 46 deletions**.
Do not charge the already verified byte-preserving rename as content deletion or
reset the original baseline. No deletion of an older file is granted.

Retain `C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp3-tests-20260828-01`.
Current contents: **55 files, 11,376,822 bytes, zero .sqlite3 fixtures**.
All original 36 root-local evidence hashes are bound in WCP-3V. The additional
`supervisor-selfcheck-2.json` is 528 bytes, raw SHA-256
`c1410673c0ca91a1830d85485736a3ec249582477198120bd624d1dc4d585d22`.
Keep the root and earlier artifacts; do not recreate, copy old DBs, overwrite
evidence, or perform manual cleanup. New basetemps must be absent.

| Check | Previously consumed | New cumulative maximum | Available names |
| --- | ---: | ---: | --- |
| Pytest | 0 | 5 | `pytest-1` through `pytest-5` |
| Ruff lint | 2 | 6 | `ruff-lint-3` through `ruff-lint-6` |
| Ruff formatter | 2 | 6 | `ruff-format-3` through `ruff-format-6` |
| Ruff format-check | 1 | 6 | `ruff-formatcheck-2` through `ruff-formatcheck-6` |
| Strict mypy | 2 | 6 | `mypy-3` through `mypy-6` |
| Formal synthetic self-check | 2 | 5 | `supervisor-selfcheck-3.json` through `-5.json` |
| Parent-only syntax/assembly preflight | 0 | 10 | `preflight-1.json` through `preflight-10.json` |

Do not spend unused slots unnecessarily. Ordinary inspected failures permit
in-scope correction/retest within these limits. Any actual identity/process/
termination/resource violation stops further checks; this batch does not preapprove
recovery from such a violation. Exhaustion or materially new scope still needs
owner direction. A staged/committed checkpoint is forbidden unless final gates pass.

Each real check retains <=300 seconds, 1 MiB combined output/evidence, 4 KiB frames,
64 KiB metadata, one application plus at most one attributable exact OS console
host. No ordinary child, helper or host descendant. Preserve owned-leaf-before-root
termination, executable/host hashes, confirmed exits and closed-stream accounting.
Retain the five original executable/configuration hashes, direct Python/Ruff
launch, shell-free hidden operation and exact cleared environment. No venv
redirector/conhost invocation, PATH fallback, installs or runtime changes.

Fixture constraints remain DELETE/FULL, foreign keys ON, temp MEMORY, <=1,000 ms
busy timeout, 4 MiB database page cap, <=64 databases per iteration, 256 MiB retained
root, one synthetic program, <=16 plans, 128 facts per history, 256 joint receipts,
2,048 audit rows and 65,536-byte documents. SQLite may manage its own rollback
journals. No WAL/SHM, ATTACH, extension, vacuum, production schema install or repair.

Each pytest iteration uses direct Python `-B -m pytest -q -p no:cacheprovider
--basetemp <retained-root>/pytest-N`, then exactly these nine modules:

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

Each Ruff invocation uses exactly the WCP-3V five-path list with the corrected
integration name and `--no-cache`: `check`, `format`, or `format --check`.
Mypy remains direct Python `-B -m mypy --cache-dir <retained-root>/mypy`.
Use absolute basetemp/cache paths and controller cwd. No extra module, -k filter,
plugin, full suite, coverage, build, helper diagnostic child or hosted CI.

Final acceptance requires a passing exact nine-module run, five-file Ruff lint
and format-check, strict mypy, no failed supervisory closure, verified untouched
eight-file baseline, complete final hashes/evidence and in-budget scope. Any
source/test correction after its relevant green result requires applicable
reverification. Report historical failures and retained artifacts honestly.

## Stage 3: one conditional local checkpoint

This stage is expressly part of the proposed approval, not current authority.
After every Stage 2 acceptance gate passes, update only the granted evidence/
coordination records, review the final diff, freeze raw hashes of all nineteen
files, and make one local controller checkpoint. No CM-workspace commit is included.

The checkpoint must contain exactly these working-file contents relative to the
unchanged baseline HEAD, with only repository-declared line-ending normalization:

```text
src/fractilate_orchestrator/persistence/workspace_create_linkage.py
src/fractilate_orchestrator/services/linked_workspace_create.py
tests/unit/test_workspace_create_linkage.py
tests/integration/test_linked_workspace_create.py
tests/fixtures/workspace_create_linkage/fixture_store.py
docs/decisions/ADR-0024-fixture-controller-workspace-linkage.md
coordination/WORKSPACE_CREATE_LINKAGE_READINESS.md
coordination/WORKSPACE_CREATE_READINESS.md
coordination/PROGRAM_STATUS.md
coordination/plans/ACTIVE_PLAN.md
coordination/NEXT_ACTIONS.md
docs/decisions/ADR-0023-fixture-workspace-create-journal.md
src/fractilate_orchestrator/persistence/workspace_create_journal.py
src/fractilate_orchestrator/services/durable_workspace_create.py
tests/unit/test_workspace_create_journal_contract.py
tests/integration/test_workspace_create_journal.py
tests/integration/test_durable_workspace_create.py
tests/fixtures/workspace_create_journal/crash_probe.py
coordination/WORKSPACE_CREATE_PERSISTENCE_READINESS.md
```

Use existing `C:/Program Files/Git/cmd/git.exe`, raw SHA-256
`c954fcc8e65a38450895ca65d308ecaee63f044d16494b5385faa5e036a3facb`;
revalidate identity before use. No install/replacement or PATH selection.
Only controller-maintenance Git status/diff/hash/index/commit inspection and the
one deliberate staging/commit sequence are authorized, not native product Git.

Create one initially absent, empty `<retained-root>/disabled-hooks` directory.
For this staging/commit sequence, set command-local `core.hooksPath` to that exact
empty directory, `core.fsmonitor=false`, `gc.auto=0`,
`maintenance.auto=false` and `commit.gpgsign=false`. Do not modify Git config.
Use no pager, external diff/textconv, signing, hooks, auto-maintenance or network.
Git may resolve the existing author identity through its normal configuration;
do not manually read/print/change user configuration or credential files. If
identity is unavailable, stop rather than inventing it.

Start with an empty index. Stage the nineteen explicit paths only, never a broad
add. Verify index contents equal the frozen candidate and no other path is staged.
Use at most one staging invocation and one commit invocation, each bounded to
60 seconds and 64 KiB captured output through the execution tool. These are
separately authorized local maintenance operations, not Python/Ruff test runs.
Use commit message `Complete fixture-only workspace controller linkage`.

Recheck source/index/HEAD immediately before committing. Afterward verify exactly
one new child commit of the original HEAD, its exact nineteen-path tree delta,
empty index and no remaining scoped tracked changes. Record the resulting
immutable SHA in the response; do not edit more controller files just to insert
that SHA after committing. Preserve unrelated/untracked files. On uncertain
commit outcome, inspect read-only and never blindly retry, amend, reset or unstage.
No second commit, branch/worktree switch, merge, push or CI is included.

## Completion and next boundary

Continue through this approved batch without requesting another routine
development/test/commit approval while the gates and limits hold. Prepare the next
consolidated packet for genuinely separate work: controller production installation/
real owner-approval persistence, native identity/containment, publication/exact
hosted CI and successor-product review are not included here.

Original decisions 1-5 remain bound only to plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle `a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
**Execution of `workspace.create/v1` remains unapproved.** No worker/verifier,
SDK call, product inspection, network/listener, deployment, production database,
runtime upgrade or manual cleanup is authorized by this batch.

## Suggested approval

> I approve CRSE-WCP-3B revision 2026-08-28.1, bound to its separately supplied
> raw-file SHA-256: the grouped offline assembly correction, bounded development/
> verification allowances and cumulative limits, followed only after all gates
> pass by the exact nineteen-file local controller checkpoint. No push, hosted CI,
> production installation, live/product effect or cleanup is approved.
