# Environment and provenance

Windows exact checks use the project's existing Python 3.13.5 virtual environment. The compiled comparator uses a task-local WSL Ubuntu 24.04 CPython 3.12 environment. Machine/runtime/package/binary/wheel hashes are in `runtime/environment-*.json`; dependency versions are pinned by `runtime/requirements-linux.lock`. The CUDD Python binding is dd 0.6.0, from the included CPython 3.12 manylinux x86_64 wheel.

Compiler provenance has a specific limitation: upstream wheel compiler flags are not exposed by the installed artifact. The exact wheel and shared-object hashes pin the tested binary; Python's own compiler and CFLAGS are separately recorded. Do not claim a source-built CUDD configuration or infer its optimization flags. A later campaign requiring source-build comparability must freeze that build before timing.

Main project source is a dirty checkout at the HEAD recorded in `MAIN_SOURCE_PIN.json`. File hashes, not HEAD alone, define the tested implementation. The pre-existing repository changes are unrelated to this task; source copies under `main_source_snapshot/` preserve the relevant imported code. Frozen prior packages retain original hashes and attribution.

Infrastructure query seed is 20260928. The original replay retains the original per-case seed construction, query hashes and rotating method order. New smoke execution has a documented deterministic method order; it is validation, not an unbiased performance experiment. The future campaign proposes balanced, seeded rotations but cannot freeze a final analysis without T3.

Per-child timeout is 90 seconds in the lifecycle harness and 300 seconds in the one-command correctness coordinator. Failure/timeout logs and result identity are retained. OS-cache state, CPU isolation and scheduling are not controlled sufficiently for hardware-general timing claims. Linux advisory file eviction is explicitly not certified physical cold disk.

No Runpod resources, cloud image, remote command or spending were used. The future package must pin those fields before launch; they are not silently filled from unrelated historical runs.
