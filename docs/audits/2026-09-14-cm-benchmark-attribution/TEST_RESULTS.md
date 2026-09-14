# Verification results

All commands ran locally from `C:/Users/brian/Documents/CM_Computation/tmp/cm-consolidation-20260914`, using the original project's `.venv/Scripts/python.exe` or existing pinned Ubuntu tools. No dependency was installed, solver substituted, cloud resource contacted or historical evidence regenerated.

## Results

| Verification | Result |
|---|---|
| Final focused suite (11 modules) | **174 passed, 2 skipped**, 11.14 seconds; `focused-tests.xml` |
| Broad supported active `tests/` suite | **1,751 passed, 9 skipped, 1,164 subtests passed; 45 failures and 31 errors**, 714.51 seconds; `broad-tests.xml` |
| Broad failure-ID comparison against untouched upstream baseline | Exactly the same 76 nonpassing `(class, test, outcome)` records; **zero new failing/error IDs**; `TEST_COMPARISON.json` |
| Whole active-suite collection | 1,834 tests collected; 8 collection errors from absent PyTorch or Windows-unavailable `resource`; those same modules excluded below |
| Closed biology native controls | 22 models × AEON/d4/Ganak/CryptoMiniSat = **88 successful checks**, zero timeout/mismatch, five-second per-arm deadlines |
| Independent small biology controls | Ten models at most 16 targets; scalar oracle and CaDiCaL exact enumeration agree with native counts |
| Stored outputs independently checked | 44 input hashes and 46 original-equation witness validations; 15 SAT models and 7 zero-count models |
| New CNF semantic tests | Every state of small fixture networks checked for exactly one auxiliary extension iff it satisfies original equations; constants, free axes, self-negation, shared expressions, clamps and conditions covered |
| Native projection protocol | Six pinned Ganak synthetic probes and four successor-wrapper calls; hidden multiplicity and empty projection correct; invalid support changes count and mixed directives rejected as documented |
| Corpus | 212 archive/admitted hash matches; 22/190 closure reproduced; self-tests: 200 seeded expressions, 786 scalar/table comparisons, canonicalization controls and depth-4000 expression |
| Corpus reproducibility | Two finalized generator runs produced identical JSON, SHA-256 `d2c547a8f3108e7a94a01dfd5601209990b42862ea2d8de770c3171a1642d30d` |
| Statistics | 47 source hashes, successor 108/105/3 reconstruction and published ratios verified; tests reject duplicate measurements and demonstrate repeat-invariant family weighting, censoring retention and withheld single-cluster intervals |
| Query schedules | 22 × 64 distinct valid deterministic assignments; per-model schedule hashes and q1/q8/q64 prefixes validated; **no performance sessions executed** |

The broad run collected the initial 16 new control tests before the final projection additions and audit-invariant module were completed. The final focused sweep includes all **23 new tests** (17 control tests and 6 audit tests), plus relevant historical adapter/factorized/bucket/packed tests. It is the final verification of the edited surface. The two focused skips are historical successor-plan/source-bundle checks whose frozen inputs were excluded from the source-only integration. Actual native/AEON comparisons were separately completed in Ubuntu.

The broad failures are pre-existing source/hash, retained-input and platform-sensitive gates. The baseline XML is recorded with its SHA-256 in `TEST_COMPARISON.json`; comparison uses exact test IDs and failure/error kinds, not only matching aggregate counts. This task does not claim a green repository-wide suite or repair unrelated historical evidence gates. The consolidation report already documented duplicate-module collection errors for unscoped repository `pytest`; this run uses the active `tests/` root.

Initial tests exposed the installed python-sat 1.8.dev20 empty-clause bootstrap indexing defect. The successor projected enumerator handles logical UNSAT before invoking that constructor, with a regression check; no alternate solver was used. Default pytest temp-root access was denied in this sandbox, so subsequent runs used fresh workspace-local `--basetemp` directories. No existing directory was recursively deleted. WSL required the tool's reviewed escalation; local execution was approved, and the exact binary hashes matched the recorded WSL runtime.

## Reproduction commands

Create a fresh, nonexisting basename beneath an existing writable `tmp/` directory for each test run. Pytest may delete an existing `--basetemp`; do not reuse a user directory.

```powershell
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' -m pytest tests/test_cm_biology_attribution_controls.py tests/test_cm_benchmark_attribution_audit.py tests/test_cm_campaign_new_adapters.py tests/test_cm_native_sat_adapter.py tests/test_cm_native_count_adapter.py tests/test_cm_benchmark_core_screen.py tests/test_cm_benchmark_core_screen_v2.py tests/test_scalar_research.py tests/test_bucket_counts.py tests/test_bucket_numpy.py tests/test_packed_queries.py -q --basetemp=tmp/attribution-focused-new

& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' -m pytest tests -q --ignore=tests/test_natural_cut_ranking.py --ignore=tests/test_natural_decomposition.py --ignore=tests/test_natural_variable_cut.py --ignore=tests/test_packed_io_campaign.py --ignore=tests/test_recognition_neural.py --ignore=tests/test_source_anf_hybrid.py --ignore=tests/test_variable_decomposition.py --ignore=tests/test_yosys_source_anf.py --basetemp=tmp/attribution-broad-new

& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' docs/audits/2026-09-14-cm-benchmark-attribution/verify_audit.py
```

## Final scope review

`git status --short` lists only three new library modules, the new local correctness runner, two new test modules and this audit directory. `git diff --stat` and `git diff --check` are empty because **no tracked historical file was edited**; the added files are still untracked and intentionally uncommitted. The manifests enumerate their bytes so an empty tracked diff is not mistaken for no work. The original dirty checkout was left intact. No commit, push, deployment, publication, credential access or paid operation occurred.

Limits: these tests do not establish biological correctness of original translations, pristine heldout independence, a CM performance benefit, or a production-ready repeated-session supervisor. Those distinctions and the implementable next experiment are explicit in the report and handoff.
