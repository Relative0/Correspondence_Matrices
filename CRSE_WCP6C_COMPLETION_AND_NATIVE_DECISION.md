# WCP-6C completion and next native decision

Date: 2026-08-28. C implementation, verification and local checkpoint: COMPLETE.
S venue effects, P native probes, B toy Git and product execution: NOT APPROVED.

## Completed checkpoint

Controller: C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator
Branch: main.
Commit: `6aaf8df4d615471aca94a3e5afcc683972b11a9f`
Direct parent: `8e2fbbb591e3eccf99aa13ce8d6abde2886866b5`
Message: Prepare isolated fixture proof harness and admission

Exactly 14 files changed: 3,631 additions, 3 deletions, within the approved
7,500/300 caps. Ten creates and four modifications match the original grant.
All raw source hashes and normalized/index/committed blobs below were independently
checked. The index is empty and the tracked worktree is clean. The only remaining
untracked status is the pre-existing `coordination/prompts/`, preserved unread.
One local commit was created. No push, amend, second commit, reset or cleanup.

Authority: WCP-6C revision 2026-08-28.1, immutable proposal
`CRSE_WCP6_ISOLATION_AND_NATIVE_PROOF_PROPOSAL.md`, raw SHA-256
`f654fdc0f539bc7134e9c7a7fe28e424768ce94476b7f1f5766fcc97af0a7ec8`.
The proposal remains unchanged. This handoff records completion; it is not a new
native permit or an extension of the product decisions.

## What was implemented

- A complete independent toy-fixture subject, with its own operation/attempt/fence,
  command, environment, image/harness/runtime/venue bindings, roots, resource/time
  limits, exact synthetic Git objects and expected administrative delta. Legacy
  references are provenance only; old approvals/contracts are unchanged.
- A closed consume/dispatch/stop/observe/commit model and shared one-use in-memory
  store. A new wrapper cannot replay the same spent store. Uncertain outcomes
  retain barriers; conflicting terminal reports stay conflicting; no automatic retry.
  This is not durable ownership, native authority or cross-OS exactly-once execution.
- Bounded canonical parsing and independent synthetic inventory/delta validation:
  identities, held intervals, ancestors, reparse/alias/link/stream exclusions,
  protected bytes/config, exact Git objects/refs/index and worktree backlinks.
- Private source-only Windows candidate bodies with fixed ABI layouts/prototypes,
  lazy DLL binding, owned resource tracking, suspended-create attributes, bounded
  concurrent readers, cancellation handling and one shutdown path. Imports and
  proposed entry are inert/rejecting. Native bodies were not invoked or installed.
- A qualified test-only supervisor and 179 new closed tests, alongside the unchanged
  901-case existing matrix. The fixture helper changes only its TEST_ROOT literal.
- ADR-0028, a producer/evidence/native-probe matrix, readiness report and updated
  status/plan/next-actions records. Historical controller reports remain historical.

Controller records:
`coordination/WORKSPACE_CREATE_FIXTURE_PROOF_READINESS.md`
`docs/decisions/ADR-0028-isolated-fixture-proof.md`

## Verification and retained evidence

Retained root:
C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp6c-tests-20260828-01

| Final gate | Result |
| --- | --- |
| Exact 19-module pytest matrix | 1,080 passed without warnings; pytest 231.24 s; supervised 237.047 s |
| Exact eight-path Ruff lint | Passed |
| Exact eight-path Ruff format-check | Passed; eight files already formatted |
| Strict mypy, including private native bodies | Passed; exact invocation reported 91 source files |
| Supervisor qualification | 117 cases; 1.004 s; no child/database/native starts |
| Final scope/raw/index/committed-blob review | Passed; exact parent, 14 paths, 3,631 additions / 3 deletions |

Nine application checks completed with eligible records, confirmed root/host
closure and no primary/cleanup supervision failure. Eight exited 0; the first
pytest exited 1 with two ordinary new-test failures and 1,074 passes. Its overflow
case reached the document cap before the drain assertion; its AST test matched a
comment instead of an annotation. Both failures and their full bounded logs remain.
Corrections preserved the caps and rejecting gates, with additional shared-store
replay and strict post-after-stop regressions. No source/test edits followed the
final relevant passes.

Usage: preflight 1/3; qualification 1/3; pytest 2/4; lint 2/6; formatter 2/6;
format-check 1/6; mypy 2/6. No full suite, build, coverage, installation or native
test was added. The supervised launches used only the pinned direct base Python
and Ruff, with A's fixed venv binding and cleared check environment. No fallback.

Retained root: 247 files, 92,979,174 bytes. Synthetic fixture DBs: 91 per pytest run,
182 total; largest 581,632 bytes. Metadata only was read for this count, never DB
contents. New tests created zero DBs and zero native resources under resource
sentinels. The empty root-level disabled-hooks directory was created once for Git
maintenance; it adds no file bytes. All residue remains.

Supervisor raw and normalized body SHA-256:
`b1609249e768d4e4cb653b7c13918be3a70b8aa21229454d63f3614883cda96c`.
Its sixteen retained mechanism function bodies, including the four required pure
helpers, match A after newline normalization. The complete new source/AST was
reviewed, parsed, frozen and qualified before any check. Every application binds
the actual passing qualification raw hash. A's exact pinned records replaced
historical predecessor reconstruction; historical passes were not counted as C.

| Evidence file | Raw SHA-256 |
| --- | --- |
| preflight-1.json | `0e1cf9a44d1eb2390f0ead6580f6ff83bf958eb6f2015d942d7e738a8ab6dd6d` |
| supervisor-selfcheck-1.json | `e9babff908f75fa5e037e3667b283a77adcb023f98cda64a04ba0a3b357205cf` |
| ruff-format-1.result.json | `b8fc88d5c746318c536b6a10bc9ea8cfc5515f07da907c706ff94ae5e35bdb1c` |
| ruff-lint-1.result.json | `155af9c82456ed91ecd362ae451078fba54a8884bb537789f5e7cce1a81b5df7` |
| mypy-1.result.json | `c2ffa38147bdffd82203f479f8f734bb664e1a42022f8327a5fa4e2b543a36ef` |
| pytest-1.result.json | `13f8d497e12c11332e3d97ce603163c2146b944559491017fe41925e95b1e96d` |
| ruff-format-2.result.json | `e7e0ee95fd0ba4e5ee9d39e3237ab98a24923d1dc1f6ed321d50fed755da568d` |
| ruff-lint-2.result.json | `2f13714692f0ebf7a8c97b7a539df05d0b2605c4891773cca48151e61251f2c0` |
| mypy-2.result.json | `e8dd2f26a2c305e70fd659cadcb4495f4d2df0c0c0653a70ac60be6282194f87` |
| pytest-2.result.json | `820a4c9b42c538860139b7338d758a0d00aaa1f668f324569c77fa5d7e2398d7` |
| ruff-formatcheck-1.result.json | `caac99cdc7fba933439b864a8f085225a3ba50a509be0c52835fc7fbedc82f3b` |

## Maintenance diagnostics and checkpoint recovery

The initial sandboxed read-only Git check failed before any write; its approved
filesystem-sandbox retry succeeded. Three mistaken absent read paths were corrected
without reading content there. The new native-file parent directories were absent;
the first file creation failed, then the exact granted parents were created using
a filesystem exception. This was not Windows privilege elevation or a native effect.

Read-only Git diff initially rejected stderr. Bounded inspection identified only
expected LF-to-CRLF warnings on the four granted modified paths. Subsequent review
accepted only those exact warnings and still rejected other stderr. Effective
attributes were empty, and all staged/committed normalized blobs matched the freeze.

There was ONE explicit stage, TWO commit invocations and ONE actual local commit.
The first commit invocation returned exit 128 with no new commit; its wrapper
retained the exit classification, not full stderr. Independent HEAD/index/raw-blob
checks proved that the frozen 14-file index remained intact and HEAD was still the
approved parent. Read-only Git identity diagnostics reproduced "Author identity
unknown" with the cleared environment, and resolved both existing author and
committer identities when USERPROFILE was inherited as C:\Users\brian.

The evidence-backed retry used that existing profile for normal identity resolution,
already permitted by C. It did not set author values, read/print config contents,
edit Git configuration, restage, amend or create a second commit. It used the same
pinned maintenance Git, empty disabled-hooks path, disabled fsmonitor/automatic
maintenance/signing, bounded drains and owned timeout handling. The successful
maintenance command including its pre/post checks finished in 4.388 seconds.
Final direct parent, all index/tree blobs, raw files, empty index and clean tracked
state were independently verified. No blind retry or native launch occurred.

## Exact frozen controller files

Raw hashes describe the working bytes at freeze and after commit. Git blobs are
the independently calculated LF-normalized object IDs, checked against both index
and committed tree. Modes were 100644, stage zero, with exactly these paths.

| Controller-relative path | Raw SHA-256 | Normalized / committed Git blob |
| --- | --- | --- |
| `coordination/NEXT_ACTIONS.md` | `e8e09837a624fa524d92e976fdb6be49f73d93cd8b1f5a0ceca3837fda60f9c7` | `c97de1a175593cd02d81e2fd1a34796ca308a364` |
| `coordination/PROGRAM_STATUS.md` | `772647f331e2eb8efd1fb5c2741fc33139c312c58c167c84351d47c5e740a4d2` | `474aa09a0e486895c01f39105cc1ea4ac95c322a` |
| `coordination/WORKSPACE_CREATE_FIXTURE_PROOF_READINESS.md` | `795c0da9844d241d71371af856ce354b027411d7794b10cbe8df98e9101b635d` | `ccd604229d1763f76107df8e7460f9fd6dc77c5e` |
| `coordination/plans/ACTIVE_PLAN.md` | `0fd815181eee17f0a162091941005d691722e0c0a6a60f6f9561fafa53e6ece7` | `a29b88a045b074c7ea25185a30be72cb02603530` |
| `docs/decisions/ADR-0028-isolated-fixture-proof.md` | `fc36551eb88a29ee32ddf14bbc96c3e09bd7b1c53a4a3c8788fca339eebfddf1` | `49f6fdbcc48e9bea1e28d72d7461efa35356bc0e` |
| `src/fractilate_orchestrator/adapters/workspace_create_fixture.py` | `5dee87fe917563a599c23b7d9f12f1d8563c803ad984e803704faea01e38492e` | `5b7f61e729adf998cb4a4e39f8ae969ab5c51a79` |
| `src/fractilate_orchestrator/domain/workspace_create_fixture.py` | `3ed3d66e18d7fa9a2abde4f27c717b7a437812997c5a9e2b0970203d928a3102` | `611eefd47ccd50294c6635c1c5e63e28a4c72b05` |
| `src/fractilate_orchestrator/services/fixture_workspace_create.py` | `307f9239af3e7715aff636f79e21fdf28e6e73997da3bcdaed11fbee37839db3` | `8e8d3bc23d7ae017297d2f1fac3d17dcd1462766` |
| `tests/fixtures/workspace_create_linkage/fixture_store.py` | `35e6d25a2c4eb787d8bbb6760e5599db9ebf7eff80ca9ec6cdb18cbc47c576ac` | `9ed1cf3bb41aa2a900bfbddd4e2f043b03e2e9b8` |
| `tests/integration/test_fixture_workspace_boundary.py` | `fd4e081b91e4912a1010cf8fef375df2b3de5d8b41309ef77a75020209af9306` | `9e59a3e87662b9881fef42a629e6a759c34f5ae3` |
| `tests/unit/test_workspace_create_fixture_contract.py` | `a09b1d3eba437c6cc867ed54c2b3439bb1ae9a0fba7a9f2c5de74115d7d48103` | `1a479b459693d743b5609b85578a52cf88e7a8ac` |
| `tests/unit/test_workspace_create_fixture_protocol.py` | `99e5603a0fb50b4a70a771349abe85f421ad6f526a2960400a114533536b45a0` | `81b701dfa2a05015aeb53ab5ce238c7eaf951d65` |
| `tools/native/wcp6_fixture_probe.py` | `b29241d723f354e0e3997015733ab971411553875c52b4a12ac55886980684df` | `6e114561c5103c26868154ac180fd0033269d607` |
| `tools/run_wcp6c_checks.ps1` | `b1609249e768d4e4cb653b7c13918be3a70b8aa21229454d63f3614883cda96c` | `ec853d13970fc2bd02a2b143202bbd3bc816b4db` |

## What remains unproved

Model-ready is not native-ready. No P probe, fixture initialization, worktree-add,
VM operation, security/service change, SDK/worker/verifier launch, production
installation or product effect occurred. Existing native gates remain unchanged.

The private candidate does not implement trusted operator authentication, outer
VM controls, protected observer/manifest/consume/evidence storage, complete native
ancestor/volume/alias/ADS/config capture, runtime lifetime closure or trusted export.
Exclusive target creation explicitly rejects rather than pretending a create/open
race is solved. Native console-host adoption is absent; unknown Job members block
closure. Fixed ABI/process/pipe/cancellation/owned-stop bodies are source candidates,
not observed guarantees. Real durable consumption outside rollback remains absent.

The synthetic v2-index/loose-object Git layout is intentionally narrow. Before B,
independently reconcile the selected Git's actual bytes and complete administrative
delta; do not silently permit extensions or arbitrary metadata changes. No actual
toy repository/base is asserted to exist. The test supervisor's process sampling
is maintenance supervision, not proof of lifetime containment or loader closure.

## Next owner input and grouped S/P/B decisions

No further approval is needed for completed C. Native work cannot advance until
you nominate an existing retained, network-disconnected Windows VM, identifying
its platform/host and exact VM, or request an exact provisioning proposal.
Do not provide credentials. This is the next input, not approval to start a VM.

The earlier read-only local facts did not establish a usable venue or hardware
readiness. Denied CIM fields remain unknown. Windows Sandbox was not selected:
discard-on-close conflicts with retained failure evidence unless retention/export
policy is separately revised. No local platform or alternate host is assumed.

Once a venue is named, group the following into the separately approved S packet:
exact inspection/setup/staging effects and paths; guest OS/tooling availability;
VM/runtime/disk budgets; observer/account/ACL arrangement; disconnected network
and enumerated integration controls; independent stop ownership; retained disk
and bounded trusted export, without writable host mappings. No installation,
download, reboot, security policy or service change is implied by that preparation.

P then needs its own immutable exact benign-probe manifest, frozen guest runtime
hashes and invocations, independently established outer containment/stop, complete
evidence producers and shared finite counters. P excludes fixture Git/worktree
effects. After accepted P evidence, B separately binds the independent new subject,
durable consumption, exact initialization and at most one toy worktree-add.
Unknown consume/stop means retained barriers/evidence and no automatic retry or
snapshot rollback to erase the attempt. Ordinary steps can be grouped within each
exact permit; unknown venues/effects cannot be approved by invented defaults.

Original product decisions 1-5 remain bound only to plan
`3de7b3f41fea771a8d24fa8085724152e407ba0386f37d7296237cd84e2c1373`
and bundle `a100fa9df965c5de378c87bfadc4b825ad7f68d8db156ee66badaf9a4a171815`.
`workspace.create/v1` remains unapproved. This controller preparation does not
build or benchmark the recognition-learning product itself.
