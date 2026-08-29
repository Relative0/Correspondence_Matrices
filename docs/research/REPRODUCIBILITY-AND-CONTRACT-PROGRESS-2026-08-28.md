# Reproducibility and measurement-contract follow-up

Historical v2 record. The subsequent [process/native-contract follow-up](PROCESS-AND-NATIVE-CONTRACT-PROGRESS-2026-08-28.md)
adds Windows supervision and separate native correctness evidence. The v2
receipts and frozen sources below remain unchanged.

This continuation prepares automated checks and strengthens the small
measurement-verification runner. It is not a new performance comparison,
production-estimator acceptance, hosted CI result or cloud authorization.
The existing downloadable research snapshot remains unchanged.

## Repeatable research checks

Run from the project root, using its virtual environment when available:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_research_check.py --report tmp/research-check-NEW-ID.json
```

The command installs nothing and makes no Git or provider changes. It:

1. Records Python, Node, platform and the six focused-test dependency versions.
2. Verifies the frozen ZIP's whole-file hash, source-commit comment, membership
   and all 4,068 per-file hashes. The manifest comes from that pinned ZIP,
   rather than treating today's working tree as the old release.
3. Checks all six current Markdown readers and runs the allowlisted current
   test suites in fresh interpreters. Missing Node, empty suites, skips,
   expected failures and failed tests cannot count as a clean pass.
4. Extracts only the verified in-memory archive bytes into a new temporary
   directory and repeats the old snapshot's reader check and focused suites.
5. Records the named current harness/test hashes before and after checking.
   A change fails the aggregate result. These hashes are not a full source,
   dependency or dataset snapshot; the ZIP has its own complete source identity.

Extraction rejects path traversal, Windows reserved/ambiguous names,
case-colliding and duplicate paths, links/special files, extra or missing
members, file/directory collisions, oversized expansion and changed content.
No archive code is executed until its pinned identity has passed. Nested
evidence archives receive the existing publication credential/path scan.

The test interpreter also rejects socket connection/binding/name-resolution
calls. That audit hook is defense in depth, not an OS network sandbox, and
does not propagate to child interpreters. The allowlisted tests use fake
clients; the check command is not a general sandbox for arbitrary code.

The [local check receipt](verification/research-check-v2-final-2026-08-28.json)
records the latest run. Current and historical-snapshot counts are separate,
overlapping checks, not independent experiments to add together.

## Prepared CI, not yet executed on GitHub

[research-checks.yml](../../.github/workflows/research-checks.yml) defines
Ubuntu 24.04 and Windows 2025 jobs, Python 3.13, Node 24 and a 15-minute job
limit. It uses commit-SHA-pinned official actions, read-only repository
permission, nonpersistent checkout credentials, and process-local Git
long-path/line-ending settings. It does not publish a website, upload a
release, push a branch, use project secrets or invoke a cloud controller.

[Focused dependencies](../../requirements-research-ci.txt) are exact-version
pins matching the locally tested NumPy/Requests environment. CI requests
binary wheels only and checks dependency compatibility. Python/Node patch
versions and hosted runner images remain moving inputs, and these package
pins are not a wheel-hash lock. The receipt records observed versions; this
is not a bit-for-bit environment reproduction claim. Setup and dependency
installation require network access in the future hosted job.

The local run used Windows 10, Python 3.13.5 and Node 22.18.0. It does not
certify the future Windows 2025/Ubuntu/Node 24 jobs. Only the focused static
workflow safety/structure test was run locally; no dedicated YAML lint or
hosted-run verification is claimed. It becomes active only after the
workflow is deliberately committed and pushed. Existing push confirmation
remains outstanding.

Design references: [official checkout action](https://github.com/actions/checkout),
[setup-python](https://github.com/actions/setup-python),
[setup-node](https://github.com/actions/setup-node), and
[GitHub Actions secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use).
Action tag identities were checked against their official repositories on
August 28, 2026; the workflow stores the resolved commit hashes.

## Measurement protocol v2

[The runner](../../scripts/cm_measurement_verify.py) now validates:

- Allowed worker modes/fields, arm, bounded width and requested warm count.
- Exact request identity and the reported source root/interpreter/PID fields.
  Those reported fields are not OS process binding or attestation.
- Canonical bounded packed output, task/kernel labels and the explicit
  diagnostic-only/no-answer-cache contract.
- All cold and warm timing fields, integer types, bounds, sample counts and
  cold phase sums. Reloads also check every phase and their total.
- Exact reload-file SHA-256 before parsing/executing it, variable universe,
  bounded structural validity and uncontrolled OS file-cache labeling.
- Duplicate/nonfinite JSON, permitted ledger states, unchanged request
  identities and complete plan/ledger reconciliation. Missing, unexpected,
  interrupted and malformed-tail records remain visible.

A controller `MemoryError` is now an error, not evidence that an OS memory
limit was enforced. The v1 source snapshots and records were not rewritten;
new producer/result/plan schemas use v2.

The [new functional pilot](verification/measurement-contract-v2-2026-08-28/summary.json)
passed all **28 scheduled cells** across four tiny fixtures: 12 fresh-process
measurements, eight independent instruction replays and eight fresh-process
structural reloads. All 13 allowlisted source files remained unchanged, and
there were no missing, unexpected or unfinished cells and no partial ledger
tail. The [plan](verification/measurement-contract-v2-2026-08-28/plan.json),
[ledger](verification/measurement-contract-v2-2026-08-28/cells.jsonl) and
[checksums](verification/measurement-contract-v2-2026-08-28/CHECKSUMS.sha256)
retain the exact scope. Fixed ordering and tiny fixtures prohibit performance
ranking; this is validation of the measurement mechanism only.

All **31 measurement tests** also passed when run from that frozen source
snapshot. The combined local check has **146 passing current tests** (25 new
tests in this follow-up) and **121 passing tests from the original download**,
with no skips. Local dependency compatibility also passed `pip check`.

## Remaining gates

The M01–M13 feature-model repair is still incomplete. In particular:

- Hard streaming stdout/stderr bounds, process-tree supervision, OS memory
  enforcement and same-task native-process high-water measurements are open.
  The current leaf-worker runner checks captured output after completion.
- Realistic partial sessions, matched fresh/shared version updates, native
  CUDD ordering and actual reordered artifacts, incremental SAT, and matched
  d4 contracts still need implementation and acceptance tests.
- Actual counterbalanced real-corpus timings, native dependency identities,
  full pytest/backend regression and external-person reproduction remain open.
- The memory estimator remains diagnostic. Wider structural tests and
  admission/refusal boundary calibration are separately scoped work.

Next: implement the process/resource supervisor and native-adapter contract
controls, then freeze a small real-feature-model pilot under the
[measurement-repair protocol](../../deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CONFIGURATION-FM-MEASUREMENT-RERUN-PROTOCOL-2026-08-28.md).
Nontrivial performance work remains for separately authorized Runpod compute.
No new allocation, production-default change, commit, push or deployment was
performed by this follow-up.
