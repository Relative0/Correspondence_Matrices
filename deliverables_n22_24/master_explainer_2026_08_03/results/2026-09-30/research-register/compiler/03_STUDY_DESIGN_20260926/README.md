# Frozen synthetic pair-token study and historical P14 replay

The signed/permuted synthetic primary cell was fixed under [protocol v4](PROTOCOL_V4_SYNTHETIC_CONFIRMATION.md), then measured on 64 held-out formulas. It **failed** the unchanged v3 utility rule: median direct-packed/CM production time ratio **0.2479**, with a 95% hierarchical bootstrap interval **[0.2462, 0.2495]**. Direct packed evaluation was about four times faster in this cell. All four assignments agreed on every formula; all CM outcomes were pure structural. The median process peak-working-set difference was -1.56% for CM under the declared metric, which is dominated by shared interpreter and import memory.

The run is a post-import, cache-reset token-output comparison on unshared two-variable formulas with `N=U=1023`; it does not test natural circuits, ABC/AIG, sharing, prepared reuse, dense output, or process-start costs. The [original protocol v3](../02_CONTRACT_REVISION_20260926/reproducibility/source/paper_program/01_audit/EVALUATION_PROTOCOL_V3.md) remains preserved. V4 was disclosed before held-out timing because no ABC executable was available for the full circuit arm. The eight-formula [pilot](PILOT_RESULTS.json) used disjoint seeds and did not enter the primary analysis. [Post-run clarifications](POSTRUN_CLARIFICATIONS.md) record the exact without-replacement sign sampling and an environment-capture limit without changing the frozen analysis.

## Result files

- [Run freeze](run_v4_001/FREEZE.json): hashes of the fixed protocol, scripts, 64-case corpus, configuration, environment, and initially empty result files, recorded before timing.
- [Primary analysis](run_v4_001/ANALYSIS.json): the frozen median-ratio rule, 10,000-draw hierarchical interval, memory statistic, and per-formula results.
- `run_v4_001/TIMING.jsonl`: 3,840 append-only arm/repetition rows (64 formulas × 30 repetitions × 2 arms).
- `run_v4_001/MEMORY.jsonl`: 128 separate fresh-process arm/formula observations.
- `run_v4_001/FAILURES.jsonl`: empty; no recorded failure.
- [Independent recount](V4_INDEPENDENT_RECOUNT.json): raw-row time and memory point estimates and run counts checked separately from the frozen analyzer.

The source implementation remains unchanged at commit `0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b`; its 63-file snapshot and transitive dependency lock are in `../02_CONTRACT_REVISION_20260926/reproducibility/`.

## Reproduce on Windows

Keep this directory beside `02_CONTRACT_REVISION_20260926` in the `CM Computation` project. Run these commands **in a copy** of the project so the delivered files and hashes remain an immutable record. Python 3.10.11 and the pinned NumPy 2.2.6 were used for the measured run.

```powershell
cd 'CM Computation\03_STUDY_DESIGN_20260926'
python -m venv .venv
.\.venv\Scripts\python -m pip --isolated install -r ..\02_CONTRACT_REVISION_20260926\reproducibility\requirements-checks-lock.txt
.\.venv\Scripts\python verify_v4.py
.\.venv\Scripts\python verify_p14_runtime.py
.\.venv\Scripts\python reproduce_v4.py --output .\replication_01
```

The last command is a new sequential local timing run. It creates a fresh child directory, copies the frozen inputs, checks their hashes, executes the 64 cases and memory observations, and writes a separate analysis. It does not overwrite `run_v4_001`. Allow roughly ten minutes on hardware comparable to the recorded Windows host; timing values can change on another machine, while correctness and the analysis procedure should reproduce. No paid compute, network service, or production code change is required. A separately frozen ABC executable and admission corpus are now in [04](../04_NATURAL_CIRCUIT_EXTENSION_20260926/README.md), with bounded natural secondary timing in [05](../05_NATURAL_TIMING_20260926/README.md); these do not complete the full v3 circuit study.

## Historical P14 reproduction

The independent [P14 bootstrap replay](P14_BOOTSTRAP_REPLAY.json) reads the preserved 51,102 timing rows and reproduces **all 17** archived interval sets using the recorded 10,000 draws and seed. To rerun that analytical check in a project copy:

```powershell
.\.venv\Scripts\python replay_p14_intervals.py
```

The original P14 runtime tree was located at `C:\Users\brian\Documents\CM_Computation\audit_p1_p13_20260918`. The [recovery manifest](P14_RUNTIME_RECOVERY.json) identifies 2,035 packaged files, including all 14 natural BLIFs with holdout-matching SHA-256 hashes. [The portable candidate ZIP](P14_PORTABLE_RUNTIME_CANDIDATE.zip) is independently hash-checked by `verify_p14_runtime.py`. The located code imports successfully. A full invocation of the archived analyzer was attempted and [timed out after 600 seconds](P14_ORIGINAL_ANALYZER_REPLAY.json); the standalone numerical bootstrap replay above is the completed analysis check. The historical freeze hashed its six top-level scripts and two holdouts, but not the complete imported runtime. A compatible local tree therefore does not establish exactly which runtime bytes produced the September 18 timing observations. [The identity-evidence checklist](P14_RUNTIME_IDENTITY_NEXT_STEPS.md) states what contemporaneous record would resolve the gap and what to report if none exists.

No public archive identifier or license/provenance clearance is claimed. The September 22 audit score is a historical assessment of that older draft and has not been reassigned to this study.
