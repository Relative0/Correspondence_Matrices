# Tooling and environment

Actual maintained backends were installed and exercised on Windows 10 x64, CPython 3.10.11. PySDD 1.0.6 provides compiled reduced/compressed SDDs, explicit vtrees and native manager minimization. PySAT python-sat 1.9.dev15 supplies the assumption-capable Glucose4 backend (`g4`). Graph baseline construction is explicit Python greedy min-fill; networkx 3.4.2 is installed but not required by the algorithm. psutil 7.2.2 records process peak working set. Exact runtime/machine data and the dependency freeze are in `data/environment.json` and `requirements-lock.txt`.

The machine has 6 physical/12 logical CPUs and about 33.6 GB RAM. Pipeline trials run sequentially as fresh worker processes. Other user processes are not controlled; there is no claim of an isolated performance laboratory. Python's monotonic QueryPerformanceCounter timer reports 100 ns nominal resolution. Measured runtime variation includes operating-system and temporary-file effects.

## Installation record

Created a scoped `.venv` inside the new Phase 5B directory. Initial normal and pinned pip attempts downloaded wheels but stalled writing pip's external HTTP cache. `faulthandler` identified the stack in `tempfile._mkstemp_inner` via pip's cache writer. These attempts were interrupted, preserving logs. Disabling pip caching avoided the unwritable cache path; no permission settings were changed.

Successful commands, from the Phase 5B directory:

```powershell
python -m venv .venv
& '.venv/Scripts/python.exe' -m pip install --no-cache-dir --disable-pip-version-check --no-deps --only-binary=:all: --timeout 15 --retries 0 pysdd==1.0.6 python-sat==1.9.dev15 networkx==3.4.2 psutil==7.2.2 six==1.17.0
& '.venv/Scripts/python.exe' -m pip install --no-cache-dir --disable-pip-version-check --only-binary=:all: Cython
& '.venv/Scripts/python.exe' -m pip check
```

Cython resolved to 3.3.0. It satisfies PySDD's declared dependency; compiled-wheel runtime checks already worked before its installation. The final dependency check reports no broken requirements. The lockfile records exact versions including pip/setuptools. Installation logs retain failed/stalled attempts and the successful commands' output. For a fresh reproduction use the pinned lockfile, not an unpinned Cython request.

## Measurement definitions

`sdd_size` is the actual root's PySDD `size()` (decision elements); `sdd_count` is the actual root `count()` (decision nodes). These are reachable-root metrics, not manager allocation totals or emulated truth-table sizes. No generic edge-count equivalence is assumed. Native B2 uses `manager.minimize()`, with the root referenced and automatic minimization disabled during ordinary compilation. M methods recompile candidate trees; every recompile is charged.

Glucose counters come from `accum_stats()`: conflicts, decisions, propagations and restarts. A persistent solver retains its clause database between assumptions, but no retained-learned-clause count is exposed or inferred. Probe and residual sessions are separate and both charged in total-runtime/work analyses. SAT solve time excludes encoding/setup, which is recorded separately and included in total.

Process peak working set is OS-reported and includes Python/dependencies. The code explicitly labels the endpoint-RSS fallback on other platforms. The 15-second watchdog covers full worker lifetime; reported successful algorithm runtime excludes interpreter startup/input parsing. `process_wall_seconds` permits inspection of that difference.

Tool provenance: [PySDD maintainer repository](https://github.com/ML-KULeuven/PySDD), [PySDD 1.0.6 release files](https://pypi.org/project/PySDD/1.0.6/), [PySAT installation documentation](https://pysathq.github.io/installation/). These support tool availability; all numerical results in this package come from local execution.
