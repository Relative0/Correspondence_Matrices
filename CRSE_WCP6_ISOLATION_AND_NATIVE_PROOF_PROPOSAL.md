# WCP-6C: grouped implementation and isolated native-proof proposal

Revision: 2026-08-28.1. Feasibility pass: COMPLETE. Batch C: PROPOSED.
No native run, platform installation, VM operation or product effect is approved.

## Decision in plain language

The allowed checks did not establish a usable isolated Windows execution venue.
Continue with one grouped controller implementation, inert-test, correction and
conditional-commit batch, C, below. Native proof needs a separately selected venue
and exact invocation manifest; it must not silently fall back to this live host.

Preferred design: an owner-selected, network-disconnected Windows VM whose disk
and failed-attempt evidence are retained. This is a design preference, NOT a claim
that such a VM exists or that this computer can provision one. No specific VM,
hypervisor installation, account, remote service or paid resource is selected.

The outstanding owner choice is whether to supply an existing suitable Windows
VM, identifying its platform/host and exact VM, or request a separate, exact local
provisioning proposal. Do not supply credentials. C can proceed before this choice;
native phases cannot. An approval of this packet means C ONLY, not the later phases.

## Completed read-only pass and observed facts

Approval was bound to the previous readiness/next-decision packet's raw SHA-256:
`c2379fd062773060cc1cc9b0c01c12398045d2d26ce8bd099e7edb92f0a4fbf6`.
One of three inspection slots was used: 0.326 seconds, 1,534 retained bytes,
less than 3.1 KiB combined metadata stdout/evidence. Slots 2 and 3 remain absent;
they are not a reason to retry denied queries or broaden the inspection.

Record: `C:/Users/brian/Documents/CM_Computation/CRSE_WCP6_HOST_ISOLATION_FACTS_1.json`.
Raw SHA-256: `029867a675b821dc4002f9a201681a73c34b829927a63a560ee489c0902eb67d`.

| Exact allowed observation | Result | What it does NOT establish |
| --- | --- | --- |
| OS registry values | Windows 10 Pro; Professional; 22H2; 19045; UBR 6466 | Hardware readiness, update/support entitlement or isolation enforcement |
| System32/WindowsSandbox.exe | Absent at the exact path | Definitive optional-feature state or impossibility of installation |
| System32/vmcompute.exe | Present; version 10.0.19041.1 (WinBuild.160101.0800) | Available, configured or safe VM venue |
| System32/vmms.exe | Absent at the exact path | Definitive feature inventory |
| vmcompute and hns services | Running; Manual start type | Network denial or Hyper-V management availability |
| vmms service query | Unavailable; status/start type unknown | A proved missing service; the retained error was not that specific |
| CIM HypervisorPresent and three processor properties | Access denied; all unknown; processor count unknown | A negative hardware result |

Only the five approved registry values, three exact files, three named services
and two narrow local CIM queries were inspected. No elevation, helper/systeminfo,
feature-management command, alternate CIM/WMI probe, security-policy read, VM
enumeration, service change, native adapter call or network test was attempted.
Elapsed checks and two-second CIM operation timeouts are metadata-query controls,
not evidence of a native execution supervisor or an OS-enforced isolation boundary.

The six frozen WCP-6 Python/test files, both frozen reports, the original A packet
and four named A evidence records were independently hash-checked. Source and
record contents were read as data; no document code was evaluated. The existing
901-test result belongs to Preparation A, not to this pass. No tests ran here.
Controller checkpoint remains the previously verified
`8e2fbbb591e3eccf99aa13ce8d6abde2886866b5`; this pass did not freshly query Git HEAD.

## Documented capabilities versus the chosen design

Windows Sandbox supports Pro editions and uses hypervisor isolation, but closing
it discards its state; host-installed tools are not automatically available inside
it. These are documented properties, not observations of an installed feature.
[Microsoft: Windows Sandbox](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/)

Its installation additionally needs hardware virtualization and minimum resources;
enabling the Windows feature is a separate system change and can require a restart.
We did not verify those prerequisites or authorize that change.
[Microsoft: installation](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-install)

Sandbox networking and clipboard sharing default on. A future Sandbox design
would explicitly disable both, GPU/audio/video/printer sharing, and avoid writable
host mappings. Configuration supports read-only mappings and Protected Client,
but those settings alone are neither observed enforcement nor an evidence channel.
[Microsoft: configuration](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)

Consequently Sandbox is not selected for the current retention policy: closing it
would destroy residue; keeping it open is not confirmed shutdown; adding a writable
export share creates another host-write surface. Any Sandbox alternative needs an
explicit retention/export-policy revision, not an unmentioned cleanup exception.

Windows 10 Pro is an eligible Hyper-V edition, but hardware requirements include
SLAT, VM-monitor extensions, memory and firmware virtualization. None is established
by the running services. Do not infer that a retained VM can be created here.
[Microsoft: Hyper-V requirements](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/host-hardware-requirements)

A VM has non-network integration channels too. The selected-venue review must bind
file-copy, clipboard/drive redirection and other enabled host/guest interfaces,
while preserving a specifically authorized independent shutdown mechanism. Do not
disable all integration services blindly or change unrelated VMs.
[Microsoft: integration services](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/manage/manage-hyper-v-integration-services)

No AppContainer profile/token/ACL, WFP/firewall rule, WSL/container, existing
vmcompute workload or machine-wide security exception is an approved fallback.

## Approval boundaries for the complete workstream

| Phase | Permitted only after its own approval | Still excluded |
| --- | --- | --- |
| C — available decision now | Exact source/harness preparation, inert checks, bounded corrections, one conditional local commit, consolidated handoff | Native harness execution and all VM/system effects |
| S — venue selection/setup | A named venue and separately enumerated inspection/configuration/transfer effects | Unnamed machines, feature installs, downloads or reboot by implication |
| P — native prerequisite proof | Exact frozen benign probe commands in that venue, with independently established outer containment | Git fixture creation, worktree-add and product effects |
| B — toy workspace effect | Exact new-subject permit, fixture initialization and at most one worktree-add, after P evidence is accepted | Retry of uncertain effects, owner-intake/production installation and product pilot |

S/P/B are a roadmap, NOT executable permits. Their commands, identities and effects
cannot honestly be frozen before the venue/runtime are known. Combine ordinary
steps within each later permit; do not invent defaults to avoid a real boundary.
P deliberately has narrower authority than B, so proof can be gathered without
circularly demanding a prior successful worktree effect. P must still have its
own exact authority, outer isolation and safe termination before any probe starts.

## C: baseline, exact grants and exclusions

Controller root: `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator`.
Require exact HEAD `8e2fbbb591e3eccf99aa13ce8d6abde2886866b5`, current branch `main`,
empty index and clean tracked worktree. Reconcile project AGENTS/status/plan before
editing. Preserve existing untracked `coordination/prompts/` unread. No new branch,
worktree, product workspace, reset, rename, delete or unrelated change is included.

Create exactly these ten controller-relative files, after checking absence:

```text
src/fractilate_orchestrator/domain/workspace_create_fixture.py
src/fractilate_orchestrator/adapters/workspace_create_fixture.py
src/fractilate_orchestrator/services/fixture_workspace_create.py
tools/native/wcp6_fixture_probe.py
tools/run_wcp6c_checks.ps1
tests/unit/test_workspace_create_fixture_contract.py
tests/unit/test_workspace_create_fixture_protocol.py
tests/integration/test_fixture_workspace_boundary.py
docs/decisions/ADR-0028-isolated-fixture-proof.md
coordination/WORKSPACE_CREATE_FIXTURE_PROOF_READINESS.md
```

Modify exactly these four, and no others:

```text
tests/fixtures/workspace_create_linkage/fixture_store.py
coordination/PROGRAM_STATUS.md
coordination/plans/ACTIVE_PLAN.md
coordination/NEXT_ACTIONS.md
```

At most 14 changed files, 7,500 additions and 300 deletions against that base;
count untracked creates by final line count. The helper may change ONLY TEST_ROOT
to C's root below. Keep its DDL, schemas, transaction/receipt semantics and caps.
All WCP-5/WCP-6 implementations, their existing tests, ADR-0027, both old readiness
reports, original contracts/digests/false flags, ledger/coordinators, dependencies,
configuration, SDK and production entry points remain unchanged.

C read grants: these targets; applicable AGENTS and tracked coordination records;
ADRs 0021-0027; the original A packet and previous/current decision packets;
the six frozen WCP-6 source/test files; A's exact qualification/result/runtime JSON
records named in its frozen report; the nineteen test modules defined below;
tests/conftest.py, tests/helpers.py, imported tracked test helper/__init__.py files,
pyproject.toml, and tracked Python under src/fractilate_orchestrator needed by
imports/strict typing. Checks may read their installed dependency code. Allow
exact runtime/binding hash reads below, metadata-only root/ancestor checks and
normal bounded Git index/tree/status/blob inspection for this checkpoint.
No database-content inspection, secrets, .env*, credentials, user config, unrelated
diffs, untracked prompts, historical document reconstruction or native PE scan.

One trusted maintainer, current configured model/effort, concurrency one; no agents,
worker/verifier launch, authentication, installation, migration, remote operation,
network beyond the cited primary documentation, CI, push, deployment or cleanup.
These newly proposed files/root have NOT been checked absent by this read-only pass;
absence and non-reparse checks are mandatory before their future creation.

## C: substantive implementation requirements

1. Make the fixture a complete independent effect subject, not a branch substitution
   authorized by a legacy product request. Bind exact command/image/cwd/environment,
   fixture base/tree/content, all roots, attempt/operation/fence, limits, protocol
   revision, harness/runtime/venue identities and expected metadata delta in a new
   domain. Keep legacy references as provenance ONLY; preserve their bytes/hashes.
   Reject duplicate/unknown/noncanonical/oversized/copied-drift inputs, mixed
   provenance and absent bindings. Unknown venue/runtime data is a blocker.
2. Implement a closed new-subject consume/dispatch/stop/observe state machine and
   independent observation validation. Its in-memory store proves model ordering,
   not durable ownership or cross-OS exactly-once execution. Require consumption
   before any effect, causal/fresh post-observation after confirmed closure, sticky
   conflicts, no retry on uncertainty, and separate primary/cleanup failures.
   Do not reuse legacy consumption to authorize the new branch.
3. Implement bounded observation/delta verification on synthetic bytes and inventories:
   stable file/volume/final-path identities; ancestor/reparse/alias/hard-link/ADS
   exclusions; protected content/config; explicit absence/race evidence; complete
   Git objects/refs, worktree private/common links and backlink relationships.
   Distinguish expected mutable administration from protected state. A path hash,
   timestamp or caller's complete=true is not a native lease or complete inventory.
4. Prepare a genuinely inspectable private guest-only probe harness source with
   fixed ABI layouts, resource ownership, bounded queues/readers and one end-to-end
   stop protocol. Reuse WCP-6 pure encoders/parsers where sound, not its permanently
   rejecting native entries. Do not monkeypatch/remove those gates. The new native
   source must be included in strict type checking without hiding all bodies behind
   an unconditional NoReturn branch; no execution is needed for this static check.
5. The harness may define proof-only native operations but C MUST NOT execute them.
   The harness/new tests must not load native DLLs, create Jobs/pipes/threads/processes,
   enumerate live handles or start fixture Git. Imports are inert. The separately
   scoped test supervisor may launch only the checks below; that is not native proof.
   No production driver/issuer/CLI registration
   is added. A future private probe invocation requires P's trusted operator boundary
   outside fixture-controlled data; supplied JSON, a hash, environment flag or guest
   self-identification cannot authenticate that authority or prove VM isolation.
6. Define explicit producer/trust boundaries for outer-VM controls, trusted observer,
   launch owner, and untrusted target/output. The target must not alter the observer,
   its input manifest or consume/evidence storage. Guest-local privilege/ACL changes,
   if needed, must be separately listed in S/P, never silently performed in C.
   Separate model evidence, static checks, observed native evidence and authorization.
7. Implement the private lifecycle plan for stable leases, exclusive target creation,
   image/loader inputs, suspended creation with Job/handle/child-policy attributes,
   verification before resume, concurrent stdout/stderr, bounded cancellation and
   owned leaves-before-root shutdown. Record acquired resources even on intermediate
   errors; never adopt a reported PID/handle. Close only after completion is confirmed.
   Missing actual absence, runtime, host-attribution or egress enforcement stays blocked.
8. Add closed tests for every gate and transition, import inertness and rejected
   native/resource calls. Include legacy/new-subject substitution, missing provenance,
   PID reuse, unknown hosts/helpers, partial acquisitions, late loader events, both
   streams/EOF, overflow/backpressure, cancellation races, stale/conflicting reports,
   missing links/extra content, consume/commit/response loss and stop/close uncertainty.
   New tests create zero DBs/native resources; never select a real driver as a test fix.
9. Produce a native-probe matrix with exact required evidence for each claimed
   guarantee. Do not report modeled_ready as native-ready or create another wrapper
   that merely repeats legacy results. State unimplemented or untestable guarantees
   explicitly. Prepare the next S/P decision from actual C artifacts; if no venue
   is nominated, record that concrete blocker rather than asking for a launch.

## C: grouped verification and finite correction envelope

Create once, after absence/non-reparse checks, the exact root:
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6c-tests-20260828-01`.
Never reuse old roots. Aggregate cap 256 MiB including caches, journals and evidence;
at most 96 synthetic fixture DBs per pytest run, 4 MiB each, unchanged DB settings.
Budgets: parent preflight 3, formal qualification 3, pytest 4, Ruff lint/formatter/
format-check 6 each, mypy 6. Parent checks <=30 s/4 KiB, no child/DB. Each application
<=300 s/1 MiB combined output/evidence, bounded drains/metadata, one application
plus at most one attributable exact console host, as in A. No native probes here.

Use A's exact six runtime/binding paths and SHA-256 values, section "A root, checks
and finite budget" of the packet raw-pinned below. Revalidate at preflight and
each applicable launch/commit. Only its direct base Python and Ruff launch for
checks; its venv Python is a binding, not an alternate launcher. Clear environment;
inherit only SYSTEMROOT/WINDIR, set TEMP/TMP to C's root and retain A's exact Python
flags/values and fixed __PYVENV_LAUNCHER__ binding. No PATH/installer fallback.

The new test-only PowerShell supervisor is implementation within C's grant, NOT
an arbitrary document evaluator or native executor. C expressly authorizes its
implementation, source review, freezing, qualification and bounded use without a
second approval for ordinary corrections. Preserve A's actual drain/accounting/
identity/owned-stop mechanisms and four pure helper bodies; do not substitute
process polling for containment claims. Replace only task-specific bindings and
input verification needed for this base, root and the exact C surface. Review the
complete resulting AST/source, retain actual raw/body hashes and qualify failure
paths before use. Never execute historical reconstructors or supplied callbacks.
Use the immutable A packet as source/reference, not a license to rerun A's slots.

A packet SHA-256: `928552bbd4706a6c5236bd28bf929e9dfa2f7e4bd120cb0863eadf0028f8ec71`.
A supervisor normalized hash: `2f511fd052aaefd9d648827bb7a0db8c93c2daf1e2c1d714d1d74a7666102d38`.
A cases normalized hash: `3becc228434a2bd1f362303a0bd4db63fc52c842574da6462ffb933a34cb85d3`.

Carry forward A's qualification coverage, adjusting only declared task bindings;
add negative checks for the new target arrays, wrong/native entrypoint, hashes,
budgets and unsafe output names. Historical assertions may use the exact pinned A
records; do not rebuild its predecessor chain. Store create-new bounded preflight,
qualification and application evidence with monotonically consumed numbered slots.
Bind the actual passing qualification raw hash before EVERY application. A change
to the supervisor requires review/requalification within the remaining three slots.

Pytest: direct Python -B -m pytest -q -p no:cacheprovider --basetemp <C-root>/pytest-N,
then A's exact sixteen modules in their printed order, followed by C's three new
test modules in the creation-list order (nineteen total). No -k, plugin, coverage,
build or full-suite expansion. The native harness is never a pytest command/target.
Ruff: A's exact no-cache check/format/format-check prefixes, then C's three new src
modules, tools/native/wcp6_fixture_probe.py, the three new tests and fixture_store.py
in that order (eight paths). Mypy: direct Python -B -m mypy --cache-dir <C-root>/mypy
src tools/native/wcp6_fixture_probe.py, preserving the existing strict settings.
Use absolute Windows spelling for cache/basetemp values. Validate PS syntax as data.

Ordinary scoped test/lint/type failures permit fixes/rechecks within these budgets;
no pause after each success. Any actual identity/process/resource/closure violation,
out-of-scope change, unknown effect or exhausted budget stops further applications.
Retain all failures; do not suppress assertions, weaken gates or reset evidence slots.

## C: acceptance and the single conditional checkpoint

Require the nineteen-module matrix, eight-path Ruff lint/format-check, strict mypy
including native-source bodies, and supervisor qualification green after final edits.
No code/test edit follows final passes without relevant rechecks. Preserve every old
native gate and contract; demonstrate zero new-test native/DB calls. Record actual
case counts, failures, limits, residue and which guarantees remain unproven.

Freeze the exact changed granted paths by raw SHA-256 and normalized/index blobs;
check the diff caps, exact base, empty index, unrelated-file preservation and no
unresolved supervisor failure. Create only the absent empty <C-root>/disabled-hooks.
Use A's pinned maintenance Git with no pager, hooks disabled to that directory,
core.fsmonitor=false, gc.auto=0, maintenance.auto=false, commit.gpgsign=false and
no external diff/textconv. Existing author identity may resolve normally; no manual
config/credential read. One explicit stage and one local commit, <=60 s/64 KiB each:
`Prepare isolated fixture proof harness and admission`.

Verify direct parent, exact frozen paths/blobs, empty index and clean tracked state.
No amend, second commit, reset/unstage, blind retry, push or CM commit. This commit
does not certify native behavior. Put its resulting SHA in one create-new handoff:
`C:/Users/brian/Documents/CM_Computation/CRSE_WCP6C_COMPLETION_AND_NATIVE_DECISION.md`
(<=400 lines/48 KiB), not a second controller documentation commit.

## S/P/B: exact information still required before native authority

The future proposal must identify the owner-selected venue/VM and independent
operator, actual guest OS/runtime/image hashes, usable tooling without installation
by implication, and every host/guest path. Do not transplant this host's runtime
manifest or C:/Users/brian paths into a guest. Bind OS/runtime/staging/disk/export
budgets separately; the 64-MiB toy-root cap does NOT include or authorize a VM image.

Require independent no-egress enforcement before guest/target execution: no attached
network path and no unauthorized integration/redirection channel. A failed ping,
offline string, protocol.allow flag or guest assertion is not proof. No Internet
endpoint is a permitted test sink. Name any benign probe and its containment first.
Keep host repos/home/credentials outside guest mappings; no writable host share.
Name a bounded, trusted evidence-export/verification mechanism and retention location
before launch. A guest-created JSON file/hash is an untrusted claim until validated.
No silent disk mount, file transfer, guest-account/ACL change or remote connection.

P's immutable manifest must enumerate every benign probe's image/argv/cwd/cleared
environment/handles, owned resources, expected failures, counters and stop rules.
Test real ABI/Job-before-resume/child policy, handle identity, reader/cancellation
races, EOF/overflow, owned stop and stable file/content/absence behavior. Bind
runtime loading observations over the required lifetime: static imports or a
module snapshot cannot exclude later DLL/helper loads. If effective enforcement
or observation cannot cover the claimed closure, retain the blocker, not a waiver.
No real target process needs to run merely to test a forged receipt's rejection.
[Microsoft: Jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[I/O cancellation](https://learn.microsoft.com/en-us/windows/win32/fileio/canceling-pending-i-o-operations).

Model C's uncertainty cases without deliberately inducing an uncontrolled native
failure. Native negative probes must remain stoppable by the independent outer
owner. On unknown stop: keep the barrier, cease launches, use only the exact
previously approved VM-stop mechanism if needed, retain disk/evidence and report
the primary AND closure failure. Never kill unowned host processes or revert a VM
snapshot to erase an attempt. A snapshot rollback can also restore spent permits;
consumption/fences must live outside the rollback scope, with no retry after loss.

B must separately bind new-subject durable consume/observe provenance, exact source
initialization and worktree commands, stable isolation/runtime evidence and an
independently verified expected Git delta. Worktrees share administrative state;
not every source .git change is forbidden or every change allowed.
[Git: worktree details](https://git-scm.com/docs/git-worktree)

Retain the proposed two-file fixture bytes/tree/base from the previous packet as
DATA ONLY: base e216cbfcfdf4b50ad102903619f13d4d4986a982, branch
codex/crse-wcp6-fixture-one. No such repository/base is asserted to exist. Reproduce
the object bytes independently and freeze guest-specific paths and invocation.
Old host B paths remain uncreated and unapproved; guest path changes need new binding.

Proposed B ceilings remain <=12 exact start attempts, <=1 worktree-add, <=30 seconds
per application, <=600 seconds for the attended session, <=1 MiB output/evidence
and <=64 MiB toy root. Specify whether P/B share counters; do not reset them across
probe failures or VM rollback. Count denied/helper attempts too. Separately account
for the trusted harness/supervisor and VM lifecycle, not just the application/host
pair; a whole VM is not a two-process job. No unlisted invocation or uncertain retry.

## C approval wording and continuing exclusions

> I approve WCP-6C revision 2026-08-28.1, bound to this proposal's supplied raw hash:
> the fourteen-file implementation including source-only private native harness,
> exact read/create/modify grants, new test-only supervisor implementation and
> execution within the finite envelope, inert tests and scoped corrections,
> one conditional local controller commit and one consolidated handoff. Continue
> through ordinary C steps without intermediate approval requests. I do NOT approve
> S/P/B, elevation, VM/platform/security/service changes, native harness/probe/Git
> fixture execution, product effects, publication or cleanup.

Original product decisions 1-5 remain bound only to plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle `a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
`workspace.create/v1`, owner-intake/production installation and worker/verifier
execution remain separately unapproved. None of C/S/P/B builds or benchmarks the
recognition-learning product itself or transfers authority to its pilot.
