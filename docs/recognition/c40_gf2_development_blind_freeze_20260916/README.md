# C40 development-blind confirmation, peak-memory, and contract-adapter evidence

`FREEZE.json` is the pre-analysis contract for C40. It was frozen at
2026-09-16T10:27:18+00:00 with digest
`0ab6e0ff13745fa6b2617a2deadb5a010a70fbb4c60dee24be2f201fa07f6a28`.

The source is the public [General Boolean Function Suite](https://github.com/boolean-function-benchmarks/benchmarks),
pinned locally at `d30b23004a45e0e8fb2e47613720d5a040fb6677`. The repository
was newly acquired for C40, after the C15/C16 implementation and C39 corpus
selection. It contains 46 BLIF files; the frozen protocol hash-ranks bounded
three-to-eight-variable cones within each source, then hash-ranks those
one-per-source representatives and retains 20. Timing, memory, candidate
counts, and decomposition results do not enter selection.

“Development-blind” is deliberately scoped here: these source files were not
used to develop C15/C16 or select C39, and C40 selection was frozen before C40
analysis. Local provenance cannot prove that contributors had no prior general
familiarity with public arithmetic or Boolean-function families. The upstream
checkout has no license file; any redistribution needs separate rights review.

The C40 run passed all functional conditions: every one of the 20 public cases
and all 12 structured controls produced a byte-identical selected C15/C16
artifact, and every materialized artifact reconstructed its frozen source
truth vector. The predefined sum of five per-case median analysis-only times
was 2,484,568,300 ns for C15 and 628,583,300 ns for C16, a 3.9526 times
repository-internal speedup on the recorded Windows host.

Peak memory uses three balanced rounds in fresh child processes per method and
case. The child establishes a baseline after imports and garbage collection,
then records `PROCESS_MEMORY_COUNTERS_EX` peak working set, sampled working
set, private usage, and Python `tracemalloc` peak over one analysis call. On
the sum of case medians, C15/C16 ratios were 1.75 for process peak working-set
delta, 1.80 for sampled working-set delta, 1.78 for private-use delta, and
2.15 for `tracemalloc` peak. These are platform-specific process observations,
not a general memory-complexity theorem; raw baselines and final values are
retained because import-time high-water marks can affect the OS measure.

The ABC contract probe uses the pinned public Berkeley ABC ACD runner on the
same frozen C40 truth vectors. The external adapter accepts a result only when
it supplies a complete artifact under `crse-exact-cm-gf2-artifact/v1` and that
artifact exactly reconstructs the source truth vector. All 20 ABC calls were
valid, but all 20 were `incompatible`: its fixed 4-LUT ACD output reports
feasibility, LUT cost, and delay, not the required factor payload. This is an
honest output-contract finding, not an external speed or quality comparison.

The local raw run directories are ignored by repository policy. Their file
identities, together with the adapter and runner hashes, are in
[`RESULTS_MANIFEST.json`](RESULTS_MANIFEST.json). The manuscript-facing account
is in the [C40 follow-up report](../../research/c16_c21_exact_decomposition_software_note_2026_09_16/C40_CONFIRMATION_MEMORY_AND_CONTRACT_ADAPTER.md).
