# Diagnostic revisions before held-out work

1. local-smoke-v1 ran a dense IR evaluation before dense whole-call materialization. That warmed alignment/allocator state. It is superseded, retained unmodified, and must not be called a cold materialization measurement.
2. The driver now places dense whole-call materialization before the IR-only probe and labels the later window accordingly. A cold process still excludes import/compile/feature extraction from the guarded operation window.
3. Complete repetition rows stream from children so a timeout can preserve prior results; partial final JSON is rejected. Failure/skipped repetition rows remain in the denominator.
4. Source snapshots now include transitive reporting/tracing package initializers. local-smoke-final is the authoritative tiny smoke for the final source tree.
5. Added explicit local child gating, live support alongside output width, and environment processor/logical-CPU metadata.
6. No candidate coefficient, profile value, calibration family or held-out family changed. No held-out output was opened or measured.
7. Public PyPI metadata fetching initially encountered a connection reset; the authorized read-only retry succeeded. Initial wheel selection accidentally matched both cp313 and cp313t ABI filenames and stopped before any lock/download. Exact normal-ABI selection and dependency metadata closure then passed. No package archive was downloaded or installed.
