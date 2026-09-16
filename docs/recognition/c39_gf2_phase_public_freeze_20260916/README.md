# C39 public GF(2) phase benchmark freeze

`FREEZE.json` is the pre-timing contract for the C15/C16 phase benchmark. It
was frozen at 2026-09-16T07:49:08+00:00 with digest
`da68866d14b449fc3127aa28f83cfb0c72bfb90ea0ec1f21ca09db47db8355dd`.

The corpus contains 19 bounded cones, one deterministic representative from
each eligible file in the public EPFL arithmetic and random-control BLIF
slice. The local source mirror is pinned to
`0060e156826e733d69bf5b3322d1bdd0d03a1f9a`. The decoder found no eligible
bounded cone in `random_control/dec.blif`; every other source file supplies
one selected cone.

Selection uses source identity and cone metadata only: it hash-ranks eligible
cones within each source file, then hash-ranks the one-per-file
representatives. It does not inspect C15/C16 timing, candidate counts, or
decomposition outcomes. The freeze records each source-file hash, root node,
support order, source metadata, truth-vector hash, a balanced 190-cell
analysis schedule, and the exact code closure.

The primary measurement calls uninstrumented `analyze_exact_gf2` and
`analyze_screened_exact_gf2` on the frozen truth vector. It reports the sum of
per-case medians across five balanced rounds. A separate three-round pass uses
the opt-in recorder and reports direct wall-clock scopes for layout, family
screening or legacy constructors, canonical descriptor work, strict artifact
admission, reconstruction, and final ordering. Recorder scopes are explicitly
non-additive and are excluded from the primary timing ratio.

Every public case must have a byte-identical C15/C16 selected artifact and
exact reconstruction. The generated controls additionally exercise each
artifact family and dense negative behavior. The default retention budget is
four; the prior proof and exhaustive small-table test establish that a budget
of at least one preserves the C15-selected partition artifact under the frozen
selection rule.

This is a public prospective confirmation slice for C15/C16/C21: the selection
was frozen before C39 timing. It is not development-blind because this project
previously inspected the local EPFL mirror in unrelated work. It therefore
supports an internal-control comparison and a reproducible public benchmark,
not an independent state-of-the-art claim.

The raw run directories follow the repository's ignored-run convention. Their
paths and SHA-256 identities are retained in [RESULTS_MANIFEST.json](RESULTS_MANIFEST.json).
