# Reproduce Phase 5B

The ZIP contains `continuity_archive/` and `phase5b_output/` as siblings under one package root. Preserve that relationship. The former is the submitted 117-file continuity package with byte-identical Phase 4/5 material; the latter contains all new source, inputs, results, reviews and logs. There are no required credentials or paid services. The virtual environment is intentionally excluded; versions are pinned in `requirements-lock.txt`.

Use Windows x64 / CPython 3.10.11 for the closest replication. Other supported Python/platform combinations may reproduce logical results but will have different wheel versions/timing behavior. Timings are observations, not deterministic expected outputs. Check `SHA256SUMS.txt` and `PACKAGE_MANIFEST.tsv` at the ZIP root before executing anything. `code/verify_package.py` verifies checksums and all required deliverables.

## Clean rerun

From the delivered `phase5b_output` directory, in PowerShell:

```powershell
python -m venv .venv
& '.venv/Scripts/python.exe' -m pip install --no-cache-dir -r requirements-lock.txt
& '.venv/Scripts/python.exe' -m pip check
& '.venv/Scripts/python.exe' code/create_rerun.py ../phase5b_rerun
```

The last command refuses an existing destination. It copies code and frozen inputs/protocol to a new sibling, so the delivered evidence stays unchanged. Set `$phasePython` to the absolute path of the newly created `phase5b_output/.venv/Scripts/python.exe`, then change directory to `../phase5b_rerun`. Run sequentially:

```powershell
& $phasePython -B -u code/reproduce_frozen.py
& $phasePython -B -u code/theory_independent_checks.py
& $phasePython -B -u code/validate_hybrid.py
& $phasePython -B -u code/benchmark.py train
& $phasePython -B -u code/benchmark.py validation
& $phasePython -B -u code/analyze_results.py select
& $phasePython -B -u code/benchmark.py heldout
& $phasePython -B -u code/analyze_results.py final
& $phasePython -B -u code/move_diagnostics.py
& $phasePython -B -u code/sat_reuse_experiment.py
& $phasePython -B -u code/public_controls.py
```

Redirect each principal command's stdout/stderr to a uniquely named log if preserving a second research record. Stop on nonzero exit or correctness disagreement. The benchmark runner stops immediately on an error/disagreement, records timeouts with fixed PAR2 accounting, and refuses to resume if algorithm/protocol hashes changed. The analysis requires every expected instance/method/replicate and verifies fingerprints. Baseline selection refuses to run after held-out exists and records the validation/analysis hashes. Do not rerun the generator over the frozen manifest: it intentionally refuses overwrite.

The archived scripts contain absolute paths from the original Linux machine. `reproduce_frozen.py` copies them and rewrites only those path literals to the current new output directory; a source-relocation manifest records all changes. Do not execute archived scripts in place. New backend code is self-contained; the separate SAT reuse diagnostic intentionally loads the relocated frozen encoders.

## Expected logical results and evidence

- Frozen Phase 4: 65,535 SDD semantic cases; 35,210 CM operator cases; 516 incremental cut queries, all with zero discrepancies.
- Frozen Phase 5: 2,601 decomposable nonfalse n=4 functions; fixed balanced alignment 225; random-vtree average approximately 0.21937716; all 65,535 exposure optima correct; n=3..6 equality counterexamples; all 540 seeded n=5 instances/summary artifacts.
- Independent frozen audit: 458,745 cuts, 983,025 function/vtree pairs and 121,500 n=5 score calls.
- Real-backend validation: 903 compilations, 113 minimizations, 881 direct/semantic/carrier comparisons each, 1,390 cuts, 46 witnesses, 80 support-minimality queries; zero discrepancies. Twenty-two false SDD cases are identified separately.
- Principal campaign: 600 train, 600 validation and 900 held-out rows (2,100 total), with completeness checked before analysis. Numerical runtime outcome and baseline selection can differ on another machine; changing them is not a logical reproduction failure.

All seeds are literal constants in source and manifests: generation 2026092905; execution order 2026092906 (+ split index); repetitions 3101/3102/3103; bootstrap 2026092907; archived n5 seed 20260929. SAT reuse has its own training-only order seed in its output metadata. PySAT/SDD library default search behavior is recorded; the code does not claim cross-platform bitwise solver traces.

`data/*_freeze.json` plus `baseline_selection.json` establish chronology/source provenance. JSONL rows retain trees, partitions, probes, U/W witnesses, SAT counters and every evaluated candidate. CSVs provide flattened per-instance and paired summaries. Diagnostic residual measurements are explicitly cached by input/partition for analysis only. They never alter algorithm objectives or primary timings.

`code/write_reports.py` renders the main outcome reports from the frozen analysis; `code/supplement_reports.py` renders the completed diagnostic summary and updates the theorem-status ledger. The latter expects the original narrative/theorem files to exist, so it is intended for a full package copy, not the minimal clean computational rerun directory. Human review reports are preserved records, not automatically recreated peer reviews. `code/assemble_package.py` builds and verifies the release ZIP after all reports are final; it refuses to overwrite an existing release.

## Scope of replication

The synthetic split is heavily based on repeated module structures with new labels; reproducing it does not establish industrial generalization. Public MIT-licensed PySAT documentation CNFs are separate smoke checks, including an unsatisfiable input. No public industrial benchmark campaign is represented by those controls. A larger campaign needs a new protocol and stronger treewidth/native-search baselines; it must not silently replace this record.
