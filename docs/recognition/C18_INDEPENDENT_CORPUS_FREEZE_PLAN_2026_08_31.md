# C18 independent-source corpus freeze

## Purpose

C18 tests the frozen C17 exact dispatcher on circuits outside the Yosys generator family used
for C15-C17 engineering. No C17 threshold or arm may be refit from this evaluation slice.

## Phase 1: VTR BLIF

The local VTR checkout is pinned by commit and license hash. The freeze scans its existing BLIF
benchmarks without network access, admits combinational cones with 3-10 live variables and at
most 256 source nodes, caps each circuit at eight cones, and selects by a stable SHA-256 order.
Every selected cone retains the original source hash, root name, support, topology metadata,
packed truth vector, and exact truth digest. Truth-vector digests present in C16 and duplicates
within C18 are excluded.

The frozen data is evaluation-only. `training_use=false` and `policy_refit_allowed=false` are
checked by the replay verifier.

## Phase 2: LogikBench RTL

The local LogikBench checkout is inventoried now, including its repository license and commit.
RTL sources are not mixed into phase 1 because synthesis would add a new transform and tool
version. A later package must freeze the exact Yosys command, version, per-benchmark license,
output BLIF hash, and semantic equivalence check before those cones enter evaluation.

## Next execution

Run the unchanged C17 policy on the verified VTR slice with direct exhaustive, direct screened,
C17 selected, and advice-off arms. Report aggregate, 5th-percentile, and minimum-case speedups
by support and circuit. A direct call-site bypass for tiny tasks may be evaluated as a separate
predeclared arm; it must not alter exact artifact identity.
