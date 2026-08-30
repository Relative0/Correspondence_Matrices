# Milestone C15/R06: exact CM/GF(2) decomposition

Date: 2026-08-30  
Status: implemented, measured, and independently verified; functional gate passed; timing replication gate failed

## What was implemented

C15 adds bounded, reconstructible correspondence-matrix artifacts over GF(2):

- recursive disjoint-support XOR factors discovered from exact ANF interaction components;
- exact GF(2) matrix rank with explicit row coefficients and basis rows;
- repeated and complemented row/column cofactor blocks; and
- exact block Kronecker factors.

Every artifact declares the complete variable order, row and column variables,
variable masks, matrix dimensions, conceptual factor-bit cost, full-truth size,
source semantic hash, and payload hash. Strict loading rejects duplicate keys,
nonfinite values, malformed dimensions, invalid references, changed hashes, or
any factor payload that does not reconstruct the complete source truth vector.
Dense functions simply receive no compression artifact.

The tests cover variable permutation, input and output negation, transpose and
partition orientation, repeated/permuted blocks, exact rank recomposition,
Kronecker recomposition, artifact save/reload and tampering, and dense
incompressible negatives.

## Frozen source family

The retained Windows run is
[`c15-exact-cm-gf2-windows-20260830-001`](runs/c15-exact-cm-gf2-windows-20260830-001).
It uses 40 frozen cases derived from independently authored
YosysHQ/yosys-bench generator semantics at commit
`52ff6fa991f2ab509618d8aaad02f307aac78848`:

- 20 unused raw generator outputs; and
- 20 exact disjoint-XOR compositions of source functions.

The positive compositions are deliberate mechanism cases, so this result does
not claim that the corresponding decompositions occur naturally at a measured
frequency. Selection did not use timing. Eight deterministic dense 8-variable
truth matrices and four structured artifact-family cases provide separate
negative and mechanism controls.

## Exact results

All functional criteria passed:

- disjoint XOR recovery was 20/20 on the source-composed cases;
- raw-source XOR false positives were 0/20;
- all four artifact families were recovered on their structured controls;
- all eight dense incompressible controls were rejected; and
- every accepted artifact rebuilt its complete source truth vector exactly.

The independent verifier replayed 40 source cases through explicit truth/CM,
packed source ANF, and ROBDD paths (120 exact representation replays), then
reconstructed 46 retained artifacts and checked 600 timing rows. It found zero
semantic mismatches.

## Task-equivalent timing

Each timed method produced the same complete truth vector and then ran the same
64-partition GF(2) candidate analyzer. Five balanced rounds charged both
representation construction and exact artifact analysis.

| Exact route | Median sum across 40 cases |
| --- | ---: |
| Explicit CM/truth materialization | 24,815,225,600 ns |
| Packed source ANF | 25,218,225,600 ns |
| ROBDD build and enumeration | 25,550,099,300 ns |

Packed source ANF was 0.9840x the explicit-CM route, so it was about 1.6% slower
in this whole-path study. Explicit CM was 1.0296x faster than ROBDD. The shared
exact decomposition analyzer dominates these totals, which is why the three
representation routes are close. These figures compare equivalent complete
artifact tasks; they do not contradict earlier kernel-only CM/CSE studies.

The functional implementation is accepted, but the predeclared second-machine
timing gate required packed source ANF to beat explicit CM by at least 10%.
It failed. No Runpod resource was created and cost was $0.

## Limits and next use

The analyzer searches a deterministic bounded partition set rather than claiming
exhaustive optimal factorization for arbitrary variable counts. It supports at
most ten variables and Boolean GF(2) semantics only. It does not learn values,
approximate dense functions, or prove an unbounded algebraic generalization.

The strongest next step is to use these exact artifacts as certificates and
targets in a partition-ranking study: predict a small candidate set on larger
source cones, reconstruct every proposal exactly, and compare against the same
bounded exhaustive candidate budget plus advice-off fallback. A timing study
should first reduce or amortize the common exact analyzer, because this run shows
that representation selection alone has little whole-path headroom.
