# Reproduction commands

The consolidated ZIP contains the unchanged previous delivery as `PRIOR_PHASE_PACKAGE.zip`. Extract it beside this directory if `../convergence_followthrough_20260928` does not already exist. Verify the prior manifest; do not overwrite an existing differently hashed copy. The previous package contains the exact Linux dependency wheels and corpus sources.

Use Linux x86_64 / CPython 3.12 for all eight-method reproduction. From the current package directory:

```sh
python3.12 -m venv replay-venv
replay-venv/bin/python -m pip install --no-index --find-links ../convergence_followthrough_20260928/runtime/wheels -r ../convergence_followthrough_20260928/runtime/requirements-linux.lock
g++ -std=c++17 -O3 -DNDEBUG -fPIC -shared native_count.cpp -o native_count.so
replay-venv/bin/python validate.py --native
```

This one correctness command checks all Boolean functions through n=3, every legal tested path, both orientations, dense/sparse codecs, source disposal, native count endpoints and update-work formulas. It is independent of the Theory implementation. `validate.py` writes its result under `results/`; for reproduction preserve the delivered result first or work in a copy.

The independent frozen Theory checker can be rerun with `python supplement.py theory`. Only the module's output-path binding changes in memory; source bytes remain unchanged.

## Exact experiment commands used

The original execution interpreter was:

`../convergence_followthrough_20260928/runtime/linux-venv/bin/python`

```sh
python prepare.py freeze
python prepare.py prepare
python campaign.py main > campaign_main.log 2>&1
python campaign.py cold > campaign_cold.log 2>&1
python complement_controls.py freeze
python complement_controls.py run > campaign_complement.log 2>&1
python supplement.py theory > theory_replay.log 2>&1
python supplement.py sources > source_preparation.log 2>&1
python supplement.py environment
python analyze.py > analysis.log 2>&1
python report_tables.py
python isolated_memory.py run > isolated_memory.log 2>&1
python minimize_metadata.py
```

`prepare.py freeze` refuses an existing protocol. The delivered protocol is already frozen; do not refreeze it to reproduce results. `prepare.py prepare` deterministically rebuilds factors/incidence from the prior pinned corpus. Main/cold campaign commands refuse an existing raw-results file. Run them in a fresh working copy after moving delivered outputs into a clearly labeled archival subdirectory. Every query batch is executed; no batch sizes are extrapolated.

The source-preparation command separately measures BLIF parsing/extraction, factor discovery and exact source checking on the natural timing panel. Those times are not claimed to be measurements inside the artifact-input trials. The Theory replay and source checks are scheduled outside the campaign to avoid contaminating timings with those checks.

## Timing interpretation

`warm_persistent` constructs and uses the state directly; `fresh_object_reload` serializes, discards the object and loads a new one in the same process. Both include construction/serialization in lifecycle totals. A repeated query batch reuses that residual state. Repetitions use a newly constructed source-specific state and a preseeded legal path; they are not independent source designs.

Cold trials use a separate consumer process and a separately written, fsynced file on Linux `/tmp`. File-specific eviction is followed by `mincore`; the consumer must observe zero resident pages before loading. This certifies the OS page-cache boundary, not physical device/cache coldness. Producer costs and consumer file read/load/online costs are separate, with parent process wall time also recorded. Application imports are included in parent wall time, not mislabeled as artifact load.

Peak RSS is process resident high-water memory, never equated to payload bits. In-process trials share a high-water history. Fresh-process consumer RSS is isolated per artifact trial; producer RSS includes its process history. Native compilation occurs before timing and is environment setup; CUDD factor compilation and sifting occur in each measured construction.

The additional `isolated_memory.py run` command executes the unchanged cold-panel cases/methods from construction through queries in a new process each. It supplies attributable full-lifecycle peak RSS in `ISOLATED_MEMORY.json`; its instrumentation timings and additional executed call counts are kept separate from the primary campaign. Its fixed selection is recorded in `MEMORY_PANEL_PROTOCOL.md` before execution.

`oracle_preparation_ns` is exact expected-answer construction, separately recorded for main trials. Full verification-inclusive lifecycle analysis adds it to the measured method phases. Raw phase totals alone exclude that independent-oracle cost. Raw supplied-factor and histogram persistence files represent the original factors; their current cumulative assignment is online state and is not round-tripped in this benchmark. Packed, CUDD and T3 residual serialization is separately correctness-tested.
