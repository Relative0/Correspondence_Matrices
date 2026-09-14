# Session runner verification

Final relevant suite: **232 passed, 2 skipped in 13.21 seconds**, recorded in `TEST_RESULTS.xml`. The two skips are existing successor-plan/source-bundle checks whose frozen inputs are absent from the source-only integration. There are no new failing/error tests.

The same 232-test selection was rerun before commit with a fresh temporary directory: **232 passed, 2 skipped in 11.89 seconds**. `TEST_RESULTS.xml` retains the earlier complete machine-readable run rather than being rewritten for a timing-only difference.

The 58 new tests cover 19 translator/session tests, 16 supervisor tests, 18 analysis tests, two real runner integration tests and three frozen-evidence tests. Tests exercise all clamp/condition contexts of small generated networks, constants, duplicated/shared expressions, explicit packed versus factorized counts, raw-path independence from CM, canonicalization differences, width refusal, full clamping, retained/rebuild phases, source/query hash rejection and corrected control metadata.

The real-corpus regression checks **all 640 frozen queries for the ten closed models at most 16 targets**, comparing raw and matched CM counts against native CaDiCaL enumeration. Independent read-only review also tested 80 seeded random networks with 3,200 scalar comparisons and confirmed normalized raw/matched CM program identity for every one of the 22 closed models. Those review probes are separate from the pytest count.

Supervisor tests actually launch small Windows processes. They verify suspended-before-assigned execution, assignment-failure cleanup, shared descendant memory limits, a native MemoryError under a hard limit with notification handling disabled, deadline termination, bounded stdout/stderr, whole-job CPU accounting, CPU affinity and child-tree cleanup. Memory is committed bytes, not RSS; denied allocation attempts can appear in peak accounting. The supervisor has no unsafe fallback on other platforms.

Evidence tests verify all 288 terminal cells, original ledger and plan hashes, 13 executed-source snapshots, job cleanup, 57 metadata-only corrections, deterministic analysis reproduction, the withheld confidence gate, and the complete deferred 396-cell design. Measured timing/output rows were not rewritten to match current source.

Run from `C:/Users/brian/Documents/CM_Computation/tmp/cm-consolidation-20260914` with a fresh workspace temp basename:

```powershell
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' -m pytest tests/test_cm_biology_sessions.py tests/test_cm_biology_supervisor.py tests/test_cm_biology_session_analysis.py tests/test_cm_biology_session_runner.py tests/test_cm_biology_session_evidence.py tests/test_cm_biology_attribution_controls.py tests/test_cm_benchmark_attribution_audit.py tests/test_cm_campaign_new_adapters.py tests/test_cm_native_sat_adapter.py tests/test_cm_native_count_adapter.py tests/test_cm_benchmark_core_screen.py tests/test_cm_benchmark_core_screen_v2.py tests/test_scalar_research.py tests/test_bucket_counts.py tests/test_bucket_numpy.py tests/test_packed_queries.py -q --basetemp=tmp/biology-sessions-new-test-run
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' docs/audits/2026-09-14-cm-benchmark-attribution/verify_audit.py
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' docs/audits/2026-09-15-cm-biology-sessions/verify_delivery.py
```

This turn ran the broad relevant surface above. It did not repeat the unrelated 12-minute whole active-suite sweep after additive session changes; the preceding audit recorded 1,751 passes, 45 failures and 31 errors, with every nonpassing ID matching untouched upstream. That repository-wide baseline remains a limitation, not a newly green-suite claim.

`git status --short`, `git diff --stat` and `git diff --check` were reviewed. All session work is additive and uncommitted in the consolidation worktree. The original dirty checkout and previous audit/manifests are untouched. No cloud, paid operation, credentials, installation, commit, push or publication occurred.
