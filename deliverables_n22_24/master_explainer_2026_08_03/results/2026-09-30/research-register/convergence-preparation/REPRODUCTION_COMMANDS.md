# Reproduction and execution boundaries

Use a **new output directory** for each command. Original archives/results are preserved. Commands below are local; none launches Runpod.

## One-command correctness, Windows

From `C:\Users\brian\Documents\CM_Computation`:

```powershell
& '.\.venv\Scripts\python.exe' '.\convergence_followthrough_20260928\reproduce.py' --output '.\convergence_followthrough_20260928\runs\recheck_new'
```

This verifies the external audit, reruns its independent checker, the frozen baseline correctness suite, C1 integration against the pinned main-source snapshot and exhaustive persistence backend tests. CUDD tests are included automatically when that interpreter provides `dd.cudd`. The Windows project environment does not; the Linux environment does. The frozen legacy adapter requires NumPy (tested at 2.3.2). SymPy is only needed for separately replaying the original Theory verifier.

## Compiled comparator, Linux x86_64 / CPython 3.12

From the package root, create a local environment and use the supplied pinned wheels:

```sh
python3.12 -m venv runtime/replay-venv
runtime/replay-venv/bin/python -m pip install --no-index --find-links runtime/wheels -r runtime/requirements-linux.lock
runtime/replay-venv/bin/python reproduce.py --output runs/recheck_linux_new
runtime/replay-venv/bin/python acceptance.py --output runs/acceptance_linux_new
```

The bundled CUDD wheel is platform/ABI-specific; do not claim it supports Windows or another Python ABI. `runtime/requirements-linux.lock` and the delivery manifest pin the wheels and dependencies. On this machine the tested environment is `runtime/linux-venv`; that large machine-specific environment is excluded from the delivery ZIP. Its environment/binary hashes are recorded.

## Original timing replay

```powershell
& '.\.venv\Scripts\python.exe' '.\convergence_followthrough_20260928\inputs\external_audit\ASTRA_Convergence_Audit_2026-09-28\reproduce.py' benchmark --output '.\convergence_followthrough_20260928\runs\legacy_timing_new'
```

This executes the original 38-case reference campaign. It does not test T3. Reproduction changes wall times; compare endpoint/query identity and answer correctness, not exact nanoseconds. Original raw rows, new raw rows, query hashes, full phases and environment records are retained.

## New lifecycle infrastructure

```sh
runtime/replay-venv/bin/python lifecycle.py smoke --output runs/smoke_new --methods packed_binary coordinate_rank_baseline cudd_fixed_order_binary
```

Smoke fixtures validate independent and cumulative update semantics, zero/constants, unequal cuts and binary persistence under three lifecycle modes. Each child writes command/config, stdout, stderr, result and execution records; timed-out children remain recorded. `acceptance.py` adds raw-source handling on one development case and file-specific advisory eviction. It does not run held-out scientific performance cells. Full phases and per-query answers are saved; no unexecuted batch is extrapolated.

`fresh_process_load` is a new consumer process after a separate producer. Imports are outside its method phases but inside parent wall time. OS-cache state is uncontrolled unless advisory eviction is requested; even then physical coldness is not proven. Page-cache eviction is a file hint, not a machine-wide flush. Absolute peak RSS includes the process runtime and validation. Both serialized bytes and process memory are reported.

## Corpus reproduction

`corpus_v1/` includes all pinned BLIF sources, their license, protocol, output statuses, case tables and per-design incidence. To regenerate extraction without changing its input selection, copy the frozen `sources/`, `PROTOCOL.json` and `PROTOCOL.sha256` into a new directory, then run:

```sh
python corpus.py screen --output new_corpus_directory
```

The protocol selects all primary outputs, structural support <=12, two deterministic cuts and a prospective design-level split. Re-extraction is not a new preregistration or a new independent benchmark family. The supplied complete `SCREEN.json` preserves excluded outputs.

## Main T3 campaign

**Do not run it yet.** `PROTOCOL_C2_PENDING.json` has null hypothesis/contract fields and no main-campaign launcher. When Theory arrives, freeze a new target and protocol hash before outcomes. A Runpod package will additionally need the chosen resource budget/image, hardware, exact setup/run command and failure/continuation policy; none is invented here.
