# Checks and reproducibility

All Python commands used the existing
`C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe` with `-B`.
Pytest used `-p no:cacheprovider`. No optional package was installed. Commands
ran in the repair worktree unless explicitly described as a baseline read.

## Final results

| Check | Result |
|---|---|
| Baseline affected suites | 152 passed, four subtests |
| Final combined affected + research-CI focused suites + package test | **448 passed, one skipped, four subtests; one pre-existing chart-data failure** |
| Research check, after dependency repair | **286 current tests + 121 frozen-snapshot tests passed** |
| Final origin-counter correction + cache/packaging regression selection | **63 passed, four subtests** |
| Predecessor primary manifest | 57 artifacts; 46 predecessor/input bindings; 14 baseline bindings verified |
| Predecessor follow-on manifest | 19 artifacts verified |
| Protected worktree checkpoint | Tracked statuses/dirty-file hashes and all files in both predecessor audit directories unchanged |
| Git diff check | Passed; no staged files, new commit, push or merge |

The final combined pytest selection was the affected tests listed below, the
focused test list in `.github/workflows/research-checks.yml`, and
`tests/test_cm_runpod_p7_functional_scout_v2.py`:

```text
test_cm_family_repairs.py
test_cm_persistent_ir_cache.py
test_persistent_path_consistency.py
test_foreign_node_interning.py
test_cm_no_reinflate.py
test_output_budget.py
test_expression_family_bench.py
test_evaluation_defaults_scope.py
test_bitset_engine_policy.py
test_share_aware_flatten.py
test_build_memo.py
test_prepared_flat_evaluation.py
```

The final log is `final-broad-tests.txt`. These tests cover opposite explicit
settings/defaults, words precedence/output width, CLI CSV/summary serialization,
default-off timing, deterministic nested wall/CPU clocks, exceptions and mid-family
failure, truncated references, reduced-output validation, full/fixed/permuted
bases, q64 all-fixed assignments, packed/fallback behavior, budget neighbors,
refusal before execution, cache regime/options, eviction, foreign-node GC/id
pressure, subclass substitution, reentry and failure cleanup.

No test asserts a timing threshold. The fake-clock test independently supplies
the enclosing and child readings (50/20 wall units; 10 total CPU units), and
checks the exclusive partition and exception record. The source-plan tests check
canonical keys and program operations as well as the reduced traversal count.

## Pre-existing failures kept visible

`test_generated_chart_data_is_current_and_pages_reference_it` fails on its
generated source-identity digest. It reproduces on the unchanged baseline:
`baseline-chart-test.txt` records one failure and one pass. No public chart or
historical data was regenerated.

Both standalone commands were run on candidate and baseline:

```powershell
python -B scripts/verify_cm_application_evidence.py
python -B scripts/verify_cm_count_closures_release.py
```

They stop at the same unchanged source identities respectively:
`scripts/cm_application_oracle.py` and
`cmbench/comparative/component_counts.py`. Candidate/baseline and LF-normalized
hashes are in `SOURCE_IDENTITY_DIAGNOSTIC.json`; logs are
`application-verification.txt`, `closure-verification.txt`, and their `baseline-`
counterparts. These checks are **not claimed as passed**. Their artifacts and
seals were left untouched.

## Failures corrected during this repair

- Pytest's default temp directory was inaccessible. The first worktree-local
  retry lacked its parent directory; creating the new worktree's `tmp` parent
  and using fresh, named basetemps resolved setup. Failed logs remain.
- The research report writer rejects an audit-directory target. Retrying with
  `--report tmp/repair-research-check-final.json` obeyed its allowed boundary;
  the final report is copied into this audit when sealed.
- Importing the new tracer from core CM broke the current dependency closure
  against a standalone manifest. It was a new regression (the baseline package
  test passed). Core now accepts an optional caller observer; the manifest and
  ZIP were not changed. The final package test and full research check pass.
- Early cache telemetry equated root-only policy with root hit position. A new
  sentinel establishes that subtree policy can hit its root. Final telemetry
  reports both axes independently. Superseded mechanism records are retained.
- Final review added eviction/reinsertion origin coverage. Keys inserted in the
  current call are excluded from the prior-call class even if they were present
  initially. The original entry count remains independent. The 63-test final
  rerun passes; final-source timing and mechanism records use the v2/v3 suffixes.

## Diagnostic reruns

Use **new output paths**; scripts refuse to overwrite their outputs. Baseline
code is read from `../cm-time-attribution-20260915`; it is not edited.

```powershell
python -B docs/audits/2026-09-15-cm-family-repair/measure.py --repo . --blocks 21 --output tmp/new-final-timings.json
python -B docs/audits/2026-09-15-cm-family-repair/paired_resident.py new-resident-record.json
python -B docs/audits/2026-09-15-cm-family-repair/diagnose.py new-mechanism-record.json
```

The first script separates timed blocks, cProfile and tracemalloc. Resident
comparisons do not run cProfile/tracemalloc. Mechanism traces and retained-cache
passes are separate. Source-attached programs/bindings are resident in warm API
cells; cold compile resets persistent state outside the measured span; family
cache clearing belongs to each family call. The worker records raw block data,
output correctness and canonical/source/program identities.

`summarize.py` recomputes the tables and structured summary into new files and
refuses existing outputs. Its assertions verify exact identity, the prepass
change, same-family shapes and nested phase conservation. Its current outputs
are sealed; do not rerun it over them.

Historical worker metadata has two documented limitations: the initial cProfile
fields were misnamed as CPU; fallback output bytes use a packed-equivalent count.
The summary explicitly corrects their interpretation without changing raw data.
OS process startup is not reconstructed from a Python-entry import timer.

## Final verification

```powershell
python -B docs/audits/2026-09-15-cm-family-repair/preservation.py --verify
python -B docs/audits/2026-09-15-cm-family-repair/seal.py --verify
git status --short
git diff --stat
git diff --check
```

Predecessor `make_manifest.py --verify` commands were run from their original
evidence worktree; their source bindings must not be checked against modified
candidate code. No held-out confirmation input, cloud resource, external
spending, scientific-disposition change, commit or push occurred.
