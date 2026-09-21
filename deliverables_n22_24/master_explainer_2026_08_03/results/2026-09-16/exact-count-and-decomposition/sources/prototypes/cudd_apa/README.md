# Local exact `dd.cudd.BDD.count` prototype

This is the source and evidence for the September 16 exact-count prototype,
published with the author's authorization after its isolated local validation.
The experiment uses dd 0.6.0 and CUDD 3.0.0; it is not an upstream dd release
or a change to the default CM backend. The original dirty checkout is preserved.
The dd-derived patch is subject to the bundled `DD-LICENSE` (BSD-3-Clause).
No new license is granted for other project source by this evidence bundle.

## Implementation

Review `dd-0.6.0-apa.patch` for the complete binding change. `patch_dd.py`
applies the same change to a pristine **dd 0.6.0** source release, checking the
original `cudd.pyx` SHA-256 before writing. The compiled, patched source is at
`build/dd-0.6.0/dd/cudd.pyx`; the native extension is alongside it.

* `BDD.count` calls `Cudd_ApaCountMinterm` and returns a Python `int`.
* The default still counts over `support(u)`, not all declared variables.
  An explicit `nvars` may exceed the number of manager variables. A width below
  the support size, or a root from a different manager, remains invalid.
* The APA result is folded from most-significant to least-significant binary
  digits, using the header's `DdApaDigit` size. No float or decimal string is
  used, including for results beyond Python's decimal conversion limit.
* A null APA result raises `MemoryError`. Every successfully returned buffer is
  released with **`Cudd_FreeApaNumber` in `finally`**, including when constructing
  the Python integer raises an exception. CUDD owns its internal traversal
  allocations; the binding owns the single returned APA buffer.
* `operator.index` requires an integer-like width. Unlike the old Cython cast,
  fractional widths are not silently truncated. `nvars >= INT_MAX` is rejected
  because CUDD computes `nvars + 1` in a signed C integer.
* `Function.count` already delegates to `BDD.count` and therefore becomes exact.
* The old `BDD.count` implementation is retained verbatim as `count_double`
  solely as the local benchmark control. It is not a proposed public API addition.

This does not change CUDD itself, ZDD counting, or any production CM backend.
The prototype retains the GIL. Concurrent mutation or reordering during the
Python reference traversal is not supported; benchmark reordering is disabled.

## Build and reproduce

Tested on Ubuntu 24.04 in WSL, CPython 3.12, GCC, Cython 3.0.12,
dd 0.6.0 and CUDD 3.0.0. This is not a Windows-native extension build.
`bootstrap.sh` assumes `gcc`, `g++`, `make`, `readelf`, Python 3.12 with venv,
and Ubuntu's package tools already exist. Run from this directory in WSL:

```sh
bash bootstrap.sh
build/venv/bin/python validate.py tests
build/venv/bin/python validate.py memory
build/venv/bin/python validate.py benchmark
```

The bootstrap downloads dependencies, but does **not** install system packages.
Python headers, Valgrind and matching libc debug symbols are unpacked under
`build/deps`. CUDD is verified against the SHA-256 pinned in dd's release
(`b8e966b4562c96a03e7fbea239729587d7b395d53cadcc39a7203b49cf7eeb69`).
Availability of the matching Ubuntu debug package depends on repository retention.
The local venv, native libraries and source releases remain under ignored `build/`.
The bootstrap itself was assembled from the commands used for this build;
an additional fresh-environment bootstrap replay was not performed.

To use the prototype without changing an installed environment:

```sh
PYTHONPATH="$PWD/build/dd-0.6.0" build/venv/bin/python
```

Then import `dd.cudd` normally. Outside this explicit source path, the shared
Windows environment continues to use its original dd installation.

## Validation and evidence

`test_count.py` covers both Python backends (`dd.bdd` and `dd.autoref`), an
independent exhaustive truth-table oracle for seeded small DAGs, complemented
edges, empty managers, constants, sparse support, widths beyond the manager,
32-bit APA digit boundaries, counts above 2^53, double overflow, a 15,000-bit
integer, explicit reordering, invalid arguments and repeated-call root integrity.
The source release's count/support/reordering tests also run.

Published timings, test output and the memory summary are in `results/`. Full native build and Valgrind logs remain in the original local experiment; they are not included in this source bundle. The allocation check compares a
warmed baseline with 40,000 additional APA calls under Valgrind. The system
CPython reports string-allocation leaks at baseline; these remain visible and
unsuppressed. The differential check requires no increase in combined lost bytes
or definite/indirect losses, no APA allocation frames in definite-leak reports,
and no non-leak errors. This is not a claim
that the entire interpreter is Valgrind-clean. Real allocation failures and
Python conversion failures were not fault-injected; the exception cleanup is
provided by the Cython `try/finally` and reviewed in the generated binding.

Observed results: **57 prototype tests passed**, plus **23 release regression
tests passed** (143 unrelated tests deselected). Across baseline and 40,000
additional calls, combined lost bytes were unchanged at 925,927; there were no
APA allocation frames or non-leak errors. Valgrind classified 205 baseline bytes
differently between definite and possible loss. Its raw processes exit 99 due
to those unsuppressed interpreter leak reports; `memory-summary.json` records
the separate differential check rather than describing those exits as clean.

## Resident-root benchmark

`benchmark.py` retains all roots before measuring, with construction excluded.
It measures APA, the unchanged double implementation, and the unchanged copied
`cmbench/comparative/exact_cudd_count.py` helper against **the same resident CUDD
root**. The helper is loaded directly to avoid importing unrelated CM modules.
Its SHA-256 matches the original dirty-tree file:
`c6d1892c2d2dc51346aa88cbd93c98825fc811a455c00054e0e5840dfd5ec98e`.

All three methods use the same count universe. The helper counts all manager
variables; its result is shifted when an explicit benchmark width is larger.
Native support discovery is included in the API timing. No result cache spans
calls, Python GC is disabled only while timing, and method order rotates across
rounds. Exact results are checked against analytical counts before timing.
The double API's rounding or overflow is recorded rather than treated as an
exact result. Raw per-round times, medians, DAG sizes, environment and hashes are
saved in `results/benchmark.json` (9 rounds, 200 calls per method per round).

Observed medians in microseconds per count:

| Resident case | APA integer | Existing double | Python exact | Double exact? |
| --- | ---: | ---: | ---: | --- |
| True, 128 variables | 3.02 | 2.25 | 1.42 | Yes |
| False, 128 variables | 2.37 | 2.20 | 1.19 | Yes |
| Two-variable sparse support, padded to 128 | 3.10 | 3.11 | 5.72 | Yes |
| OR of 64, padded to 128 | 12.60 | 11.13 | 113.16 | **No: rounded** |
| Parity of 128 | 37.11 | 24.70 | 377.44 | Yes |
| At least 24 of 48, padded to 128 | 116.79 | 34.41 | 1196.41 | Yes |
| Literal, padded to 1100 | 5.72 | Overflow error | 3.35 | No result |

For the three larger diagrams, APA was approximately 9.0–10.2 times faster than
the Python traversal, at 1.13–3.39 times the double API's latency. Constants and
the padded literal favor the Python traversal. These controls therefore support
a precision/performance tradeoff, not an across-the-board speedup.

These are local synthetic count-only measurements, not end-to-end workload
results or a universal performance claim. Large-root traversal and wider APA
integers have different costs; trivial roots can favor the Python helper.

This remains a research prototype. Production integration and upstream submission are separate decisions.
