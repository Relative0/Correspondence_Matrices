# CRSE-WCP-2V: correct verification runtime process accounting

Revision: **2026-08-27.1**. Status: **proposed; new runtime authority not approved**.

## Exact decision

Amend only WCP-2's maintenance verification runtime. Launch the already installed
base Python directly with one fixed virtual-environment bootstrap value, and run
the already installed Ruff binary directly. Preserve the two-process crash-test
ceiling instead of admitting additional launcher processes.

This supplements, rather than replaces, the owner-approved WCP-2 proposal:
`C:/Users/brian/Documents/CM_Computation/CRSE_DURABLE_WORKSPACE_JOURNAL_PROPOSAL.md`,
raw SHA-256
`90b2a59a402344721d673bc19f4b70b4b4f372b789a0f7ea9e7ccb1d5ddf3089`.
Its 12-file scope, fixture-only database authority, remaining test budgets,
production exclusions, and separate `workspace.create/v1` gate remain in force.
Do not execute this amendment before its own exact approval.

## Finding and current state

The original proposal I prepared omitted Windows launcher overhead. Read-only
inspection found both venv-launcher markers in the approved 3.10.11 executable.
The matching CPython source creates a child interpreter and supplies
`__PYVENV_LAUNCHER__`; its parent waits for that child. The installed Ruff Python
wrapper also launches the Ruff binary. Consequently the original crash-test
command shape would require more OS processes than its stated ceiling, and the
draft PID/termination assumptions need correction.
[CPython 3.10.11 launcher source](https://github.com/python/cpython/blob/v3.10.11/PC/launcher.c).

The twelve approved controller files are drafted, not verified or committed.
No pytest, Ruff, mypy, crash-helper, runtime probe, SQLite connection, or schema
setup has run. The exact WCP-2 temporary root was created after absence and parent
checks and is still empty. No basetemp, database, log, or cache exists there.
The previous implementation's 221-test result does not validate this draft.

No runtime process-count experiment has been performed. Local marker/version
inspection and matching source establish the reason to stop before launch;
the proposed direct-launch binding still needs the bounded preflight below.

## Exact installed runtime subjects

| Subject | Exact absolute path | Raw SHA-256 |
| --- | --- | --- |
| Direct Python executable | `C:/Users/brian/AppData/Local/Programs/Python/Python310/python.exe` | `3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260` |
| Venv redirector, binding only; do not launch | `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/python.exe` | `b2c836c52cdf063180b9ee76f67ac42946101b79ac457f3494035a67c090d961` |
| Venv configuration, read-only | `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/pyvenv.cfg` | `efe9c8f26884c6ac39ebb57a9f1215a539a423feaf12fe5eec753e28dcef3a55` |
| Direct Ruff executable | `C:/Users/brian/Documents/Fractilate/Fractilate-Orchestrator/.venv/Scripts/ruff.exe` | `0cf602e931f311581bce0b1dfc8d5e30717d96af54c65d7b89a9a8d4497b0eeb` |

The Python executable's file version is 3.10.11, length 103,192 bytes. The Ruff
binary is 32,525,824 bytes. Both were observed as regular, non-link files.
These hashes identify the launch files, not an independently certified closure
of every DLL or installed dependency.

Authorize read-only revalidation of these four exact subjects and the existing
Ruff wrapper files `.venv/Lib/site-packages/ruff/__main__.py` and
`.venv/Lib/site-packages/ruff/__init__.py` under the controller root. Normal
runtime/import reads of the existing interpreter libraries and installed venv
dependencies remain allowed. No installation, runtime/configuration edit, new
dependency, global package access for fallback, or credential/configuration dump.

## Environment amendment

Clear every child environment as in WCP-2. For direct Python launches only, add
this one literal, non-secret bootstrap pair:

```text
__PYVENV_LAUNCHER__=C:\Users\brian\Documents\Fractilate\Fractilate-Orchestrator\.venv\Scripts\python.exe
```

The value is fixed; do not inherit or discover it from ambient environment.
It establishes the existing venv binding without launching its redirector. Verify
the resulting binding before running checks; a failed binding does not authorize
a different interpreter, PATH lookup, relaxed isolation, or package installation.

Keep the other allowed names/values unchanged: inherited SYSTEMROOT/WINDIR;
TEMP/TMP set to the exact WCP-2 root; bytecode disabled; pytest plugin autoload
disabled; fixed Python encoding/hash settings; and user-site disabled. Never
enumerate or forward other environment variables. Ruff receives the original
cleared allowlist without this Python-only bootstrap value.

This is a maintenance-harness exception only. Do not modify the product worker's
environment contract, model/effort, prompt, verifier, immutable packet, or any
literal-false authority flag.

## Bounded runtime preflight

Before database or test execution, permit at most two metadata-only direct-Python
preflight invocations for an in-scope harness correction/recheck. Each is bounded
by 30 seconds, 4 KiB combined output, no descendants, and create-new logs under the
existing WCP-2 root. A limit breach stops all checks.

Use the exact direct Python above with `-I -B -c` and a fixed inline probe that
only imports standard-library metadata modules, obtains its own PID/parent PID,
and checks:

- Python version is 3.10.11.
- `sys.prefix` resolves to the controller's existing `.venv`.
- `sys.executable` resolves to the exact venv binding path.
- `sys._base_executable` resolves to the exact direct Python path.
- User-site loading is disabled.
- SQLite's library version is reported without connecting to any database.

Emit only bounded version/count/boolean/PID metadata. Independently verify the
owned process's native image path and start identity from its process handle or
scoped Windows process metadata. Do not use the deliberately rebound
`sys.executable` alone as native-image proof. Do not inspect unrelated process
command lines or environments.

If the interpreter/venv identity, runtime hashes, or actual process shape differs,
stop without database/test execution. In-scope probe/harness corrections may not
change the subjects, bootstrap value, authority, or limits.

## Corrected check and helper launch policy

After successful preflight:

1. Run pytest and strict mypy using the exact direct Python executable with the
   fixed venv bootstrap. Keep WCP-2's nine pytest modules, argument shapes,
   dedicated mypy cache, and all resource/output limits.
2. Run the exact Ruff executable directly, not `python -m ruff`. Keep the six
   new Python targets and `--no-cache` on every invocation. Approved formatting
   and bounded in-scope lint/import corrections may touch only those files.
3. Update only the existing WCP-2 test/helper files and inline maintenance harness
   to launch the exact direct Python for each named crash case with `-I -B` and
   the fixed bootstrap. Do not launch the venv redirector as a helper.
4. Require the pytest PID recorded by the harness to match the actual interpreter
   PID; require each helper PID/start identity to identify the directly launched
   Python process. Validate the bounded metadata channel and confirm helper exit
   before fixture reopen.
5. Permit only one check at a time, one crash helper at a time, at most six helpers
   per pytest iteration, and at most two check-related OS processes alive:
   pytest plus its one helper. Preflight, mypy, and direct Ruff have no authorized
   child process. Internal tool threads are not controller workers; do not add
   threaded SQLite connections or parallel writers.
6. On failure/timeout, terminate only the owned, identity-verified helper first,
   confirm its exit, then stop the owned check process. Unknown termination or
   any unexpected descendant is a stop condition. No process-name killing or
   broader descendant authorization. This remains a bounded fixture harness,
   not proof of adversarial Windows containment.

The maintenance shell supervising these checks is not a product worker or test
child. Scope Windows process metadata to the owned root/helper PIDs and their
direct-child relationships; no unrelated command-line/environment inspection.

All three pytest iterations and all original Ruff/mypy iteration budgets remain
unused. This amendment does not reset budgets after any future failure.
Keep 300 seconds/1 MiB per ordinary check, 15 seconds/64 KiB per helper, and 4 KiB
helper metadata frames. Preserve the original 4 MiB main-database cap,
64 new fixture databases per pytest iteration, and 256 MiB retained-root budget.
No full suite, coverage, build, CI, arbitrary commands, or additional helpers.

## Exact continuation baseline

Require controller HEAD `c6107fa889053a34711412be23f2d8d065eb125c`, an empty index,
and this raw-file manifest of the twelve in-progress WCP-2 inputs. Preserve
unrelated `coordination/prompts/` without reading it. Do not reset, checkout,
stage, or commit to manufacture a match. New drift requires review.

| Controller-relative input | Raw SHA-256 |
| --- | --- |
| `docs/decisions/ADR-0023-fixture-workspace-create-journal.md` | `2ea97409eb37d878f5f1cf5eb147b14c5fe76b3ec1089b2f3b01ace37d8ce711` |
| `src/fractilate_orchestrator/persistence/workspace_create_journal.py` | `7618fb50590ef9684f4084a643336ec67481114ce7a8aaca050535e2d1581b2c` |
| `src/fractilate_orchestrator/services/durable_workspace_create.py` | `006e6fa30dc0537db474a3f412b44306cf62e497cf015af9fa85240e97930e21` |
| `tests/unit/test_workspace_create_journal_contract.py` | `1254807bf5e23afdca5a4ba667ef88f0e4887adb57d154570c8309b6fafd9470` |
| `tests/integration/test_workspace_create_journal.py` | `07effb965378a76a859686e54ef040702f56a832526c6b25356cd6c46f0dc844` |
| `tests/integration/test_durable_workspace_create.py` | `592ab3154c3181aee32c2f941e0d358746befabedebf770089ca55cea68ef07a` |
| `tests/fixtures/workspace_create_journal/crash_probe.py` | `5a8c7afcd695741cd97073ae905e4d7e816ec3fed9edc68f61db4725b4ad3758` |
| `coordination/WORKSPACE_CREATE_PERSISTENCE_READINESS.md` | `14b55fed9051210eced59053b2ba4a63d49e23bd15734095dcc81b5cd0c56237` |
| `coordination/WORKSPACE_CREATE_READINESS.md` | `8263c588400dd2a59f4d7f1c0a010476f17cae85edde73166f29c273b8c83fa8` |
| `coordination/PROGRAM_STATUS.md` | `1a0ce2146c9d36d9d53ebeab3ccd8e6204cbfd5baecd34d86c716819ba50014b` |
| `coordination/plans/ACTIVE_PLAN.md` | `b67c03aa4aaaa89fdcbce6b935f15a6a1b4c168739c25f2edec7d1e608aa3fe1` |
| `coordination/NEXT_ACTIONS.md` | `d22ec270446e39dd8e0b8c5e31a8ce5009b0fbd9a2fe00a9ad58a423b7c62cdf` |

Current draft delta: **12 authored files, 1,814 added lines, 15 deleted lines**
relative to the controller base, including untracked files. WCP-2's final ceiling
remains **12 files, 3,000 additions, 150 deletions**, with deletions only in the
four coordination documents. Formatting, remaining corrections/tests, and final
records must still fit; no new controller-file grant is added.

Continue in the already created, still-empty root:
`C:/Users/brian/AppData/Local/Temp/fractilate-crse-wcp2-tests-20260827-01`.
This is continuation of this run's owned root, not reuse of another run. Reverify
that it is the same non-redirected directory and still empty before the first
preflight; if not, stop and report. Then create only new logs and verified-absent
`pytest-1`, `pytest-2`, or `pytest-3` children. Do not delete the root to satisfy
an absence check. SQLite's own rollback-journal lifecycle remains permitted only
for newly created approved fixtures; manual cleanup stays excluded.

The original WCP-2 proposal and this amendment are review artifacts in
CM_Computation. Do not alter either approved subject while implementing it.

## Completion and preserved exclusions

Finish and review the bounded WCP-2 verification, update all four coordination
documents and persistence readiness report with actual results and limitations,
then prepare the next exact approval gate without waiting for a continue request.

No staging/commit, push, CI dispatch, existing controller/user database access,
production migration, runtime upgrade, native Git/workspace effect, worker,
verifier, listener, network effect, manual cleanup, or product-packet regeneration.
The old product decisions remain bound only to their original plan/bundle;
`workspace.create/v1` remains separately unapproved.

## Suggested owner approval

> I approve CRSE-WCP-2V revision 2026-08-27.1, bound to the reviewed amendment's
> raw-file SHA-256: the exact direct Python/Ruff launch subjects, fixed venv
> bootstrap value, bounded metadata preflight, and corrected process supervision
> for the remaining WCP-2 fixture-only checks. The original file/resource limits
> and all production, product-effect, commit, push, CI, and cleanup exclusions
> remain unchanged.

Use the separately supplied full-file hash; a changed amendment requires a new
review and hash. Tool-level filesystem/runtime permission may also be required
and is not substitute product-effect authority.

