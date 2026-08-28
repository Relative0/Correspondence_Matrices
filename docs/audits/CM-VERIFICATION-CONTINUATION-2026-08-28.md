# CM verification continuation — 2026-08-28

Latest continuation: the separately approved zero-volume Runpod smoke
succeeded at 09:04 UTC: 70 passing remote tests, 312 successful rows and
verified pod deletion. Separate 09:05 UTC checks confirmed absence and
guard exit. This task independently reconciled the 312-cell grid, 72
comparable calls, archive, snapshots, locked versions and memory summaries.
The old estimate was too low in 66/72 calls; the candidate covered all but
can be very conservative. Production acceptance remains false. All 61 local
setup/lookup/transport/accounting tests passed. No duplicate was launched.
See [the successful-smoke audit](../runpod/RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md).
The feature-model pilot and earlier failures below retain their distinct
historical scopes; this smoke does not close their remaining gaps.

First HTTP-retry continuation: `Run CM safe work campaign` made the sole
authorized creation request at 08:38 UTC (HTTP 201). Its controller refused
a reported zero-GB pod volume versus the approved ten GB before source
upload, deleted the pod, and verified cleanup; final 08:41 UTC inventories
were empty and pod detail returned 404 on both APIs. No workload ran and
no replacement is queued. This task's final 23 independent transport tests
plus 26 setup/lookup tests all pass (49 total). It did not launch a duplicate.
See `docs/runpod/RUNPOD-HTTP-RETRY-INDEPENDENT-AUDIT-2026-08-28.md` for the
prelaunch fixes, Windows PID correction, evidence hashes and cost caveat.

Reconciliation at 08:18 UTC: the other task's authorized project-root
credential lookup completed at 08:08 UTC and matches the campaign result:
both inventories HTTP 200/zero pods; supplied pod HTTP 404. This task
verified the saved evidence and added 10 passing offline lookup tests with
fake credentials/clients. It did not repeat authentication or run a cloud
workload. The transport/scope review is
`docs/runpod/RUNPOD-TRANSPORT-REVIEW-2026-08-28.md`. These new helper tests
are separate from the 60 earlier tests and the 28-cell measurement pilot.

Access update, 08:09 UTC: after explicit authorization, the memory-smoke
credential successfully listed pods through both Runpod APIs (HTTP 200),
but both inventories were empty and the supplied pod ID returned 404.
No cloud workload ran. See `docs/runpod/RUNPOD-READONLY-ACCESS-2026-08-28.md`.
The local verification report below records the earlier preparation state.

## Outcome

The bounded measurement verification runner and new static navigation checks
are implemented. All **60 distinct tests** passed: 17 runner tests, 6 new
static navigation checks, 21 existing website/evidence checks, and 16 existing
credential-free setup checks. The 17 runner tests also passed from the frozen
source snapshot, not just the live checkout.

The functional pilot passed **all 28 scheduled cells**: 12 fresh-process
measurements across four cases and three arms, 8 independent instruction
replays, and 8 fresh-process structural reloads. All scheduled cells were
retained, no cell was unfinished, frozen-source hashes remained unchanged,
and no concurrent change was observed in the 12 allowlisted source files.

These are correctness and measurement-plumbing results. **They are not new
CM speedup claims, native CUDD/d4 results, cloud execution, full regression,
or completion of the 13-gap measurement repair.**

## New implementation

- `scripts/cm_measurement_verify.py`: bounded CNF inputs, scalar oracle,
  CM/CSE/direct-CNF adapters, complete cold preparation-plus-first-execution
  timing, separate warm recomputation samples, structural serialization,
  strict bounded reload, fresh subprocesses, exclusive source snapshots,
  a preregistered cell ledger, and incremental outcomes.
- `tests/test_cm_measurement_verify.py`: 37 deterministic fixtures over
  k=0,1,5,6,7,8; all three arms agree with the scalar oracle. Includes
  clause-order/duplication and variable-permutation properties, corrupt
  structures, ignored cached answers, phase accounting, balanced-schedule
  construction, mocked timeout/memory/exit/malformed-output failures,
  interruption, partial ledger tails and source mutation.
- `tests/test_cm_website_navigation.py`: static HTML shells, declared routes,
  literal local-file targets, alternative-text attributes, and unresolved
  build placeholders. It checks 19 literal local-file references; it does
  not exhaustively resolve JavaScript-generated links or fragments.

The zero-variable CM/CSE case uses an explicit constant-program adapter
because the expression AST has no constant node. It is labeled, not presented
as ordinary expression compilation. At fewer than six live variables the
executor uses bigint flat evaluation; at six and above it uses NumPy words.
The tests exercise both sides of that boundary.

## Evidence locations

Pilot directory:

```text
C:\Users\brian\Documents\CM_Computation\deliverables_n22_24\master_explainer_2026_08_03\use_case_benchmarks_2026-08-27\runs\measurement-contract-functional-pilot-2026-08-28
```

It contains `plan.json`, `cells.jsonl`, `summary.json`, the 8 structural
artifacts, the 12-file source snapshot/manifest, and `CHECKSUMS.sha256`.
The plan names the cases, arms, every scheduled cell, and the explicit limits.
No prior benchmark directory was rewritten.

The four fixtures are zero-width tautology, k=6 boundary relation, k=7
contradiction, and one seeded k=8 CNF. This deliberate tiny test selection
does not represent a domain workload or a balanced performance population.

## Website verification and small correction

The feature-model evidence page was missing direct audience-summary routes.
Added Simple One-Pager, Technical Summary and Investor overview links to its
top navigation in both the source template and generated page. The exact
template-expansion test passes. No evidence values, chart ratios, historic
audit status or shared compiler code were changed in this continuation.

Browser verification was attempted using the Browser skill. The browser URL
policy explicitly blocked access to the local `file://` page. The attempt
stopped; no localhost, alternate browser, raw protocol, or other workaround
was used. Consequently no screenshot, rendered-DOM, responsive-layout,
keyboard, theme, or interactive-control check is claimed.

Most content is JavaScript-generated. Initial new static-test assumptions
about pre-rendered headings/navigation were corrected after inspecting that
architecture; those initial failures were test-design errors, not evidence
that the pages were blank. The remaining direct-navigation inconsistency was
fixed and all static checks now pass.

## Runpod

At the time of initial local preparation, no authenticated Runpod request or
cloud run had occurred. The subsequent campaign-key check and reconciled
root-loader check above supersede that pending-access state. Inventory
requests succeeded but returned zero pods. No cloud workload ran, and
creation readiness remains unverified.

A 55,948-byte bundle contains exactly the 12 frozen source/test files plus
their manifest, no credentials or user datasets. It has **not** been uploaded.

Read the exact gate and limitations:

```text
C:\Users\brian\Documents\CM_Computation\docs\runpod\RUNPOD-VERIFICATION-GATE-2026-08-28.md
```

The present runner labels its pilot local. A remote-provenance extension,
fresh bundle identity, dependency validation, exact target/upload/cost
approval, and independent cleanup gate are required before a cloud launch.
The separate memory-smoke task's old source bundle and consumed approvals
were not repurposed. Saved provider HTTP 500/404 outcomes remain historical
observations and were not presented as fresh checks.

## What still needs implementation or measurement

- Complete fresh/shared version-update arms and realistic partial sessions.
- Native CUDD ordering assertions, actual reordered artifacts, ZDD admission,
  and matched d4 count/output contracts.
- Process-tree high-water memory and enforced whole-process resource limits.
  The pilot records no memory metric; its injected memory failure is a unit
  control, not an OS memory-limit test.
- Counterbalanced real timings: the schedule constructor is tested, but this
  pilot intentionally uses fixed ordering and its timings cannot rank arms.
- Stronger worker protocol validation for every timing/artifact field and
  hard streaming output/process-tree limits. Current workers are known
  leaf processes; output size is checked after completion.
- Reproducible native dependency identities and remote provenance. Source
  hashes alone do not pin an installed environment.
- Broader adversarial property coverage, including non-CNF AST operations,
  and genuine external reproduction by another person.

The full next-run protocol remains
`CONFIGURATION-FM-MEASUREMENT-RERUN-PROTOCOL-2026-08-28.md` in the feature-model
benchmark directory. This continuation builds part of its entry gate; it
does not relabel historic measurements as repaired.

## Reproduction commands

From `C:\Users\brian\Documents\CM_Computation`:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_cm_measurement_verify.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_cm_website_navigation.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p '*website.py' -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_cm_runpod_readiness.py -v
```

For another local pilot choose a **new** output directory:

```powershell
.\.venv\Scripts\python.exe -B scripts\cm_measurement_verify.py --pilot-output tmp/measurement-verification-NEW-ID
```

The original pilot directory refuses overwriting. Use its frozen snapshot
when reproducing the exact tested implementation. No dependency installation,
commit, push, publication or change to the other task's five core/test files
was performed here.
