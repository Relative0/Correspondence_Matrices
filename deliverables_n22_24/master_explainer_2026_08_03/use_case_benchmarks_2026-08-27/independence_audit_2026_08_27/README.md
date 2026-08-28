# Independent feature-model audit tools

These tools audit explicitly named historical runs. They do not select the
newest run automatically, edit shared compiler files, or replace old outputs.
Each output directory must be new. `source_snapshot` records the source
observed by this audit, not a retroactive snapshot of the historical process.

Run from `C:\Users\brian\Documents\CM_Computation` in PowerShell. Replace each
`YOUR-NEW-AUDIT-ID` output with a distinct name; existing directories are refused.

```powershell
.venv/Scripts/python.exe -B deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/independence_audit_2026_08_27/artifact_audit.py --output deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/YOUR-NEW-AUDIT-ID
```

`artifact_audit.py` needs only the Python standard library. It independently
replays CM instructions, CUDD JSON and d4 arc-format graphs against a scalar
CNF oracle; d4/CUDD binaries are not needed. It also checks graph properties,
hashes, observed source stability and clustered aggregate sensitivity.

```powershell
.venv/Scripts/python.exe -B deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/independence_audit_2026_08_27/source_audit.py --source C:/Users/brian/AppData/Local/Temp/codex-cm-feature-model-benchmark-20260827 --output deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/YOUR-NEW-SOURCE-AUDIT-ID
```

`source_audit.py` additionally needs python-sat with CaDiCaL195 and MiniSat22.
It reparses hashed official DIMACS payloads, validates original endpoint
witnesses, regenerates and retains retrospective joint witnesses, reconstructs
every saved residual, and corroborates the Linux refusal using MiniSat22.
Version differences are recorded. An alternative valid witness that does not
reproduce the saved residual causes a failure, not a silently changed corpus.

```powershell
.venv/Scripts/python.exe -B deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/independence_audit_2026_08_27/measurement_audit.py --output deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/YOUR-NEW-MEASUREMENT-AUDIT-ID
```

`measurement_audit.py` reads the explicitly pinned deep-artifact audit named
in its source. It records the source locations of measurement gaps, encoding
components, actual graph counts, final saved BDD orders and point-query mix.
It performs no new timing experiment. Audit-defined normalized byte counts
are accounting examples, not benchmark results for a new serializer.

```powershell
.venv/Scripts/python.exe -m unittest discover -s deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/independence_audit_2026_08_27 -p test_auditors.py -v
```

For the scoped producer-plus-auditor regression, use `frozen_regression.py`
with a new `--output` and the location of the existing pure-Python pytest
installation in `--pytest-library`. It copies and hashes the selected sources,
disables third-party pytest plugin autoloading and tests the snapshot, not the
moving shared worktree. It does not install dependencies. The recorded run
used `C:/Users/brian/AppData/Local/Programs/Python/Python310/Lib/site-packages`.

All tools use independently written audit logic, not third-party
certification. No tool converts a correctness pass into a performance claim.
