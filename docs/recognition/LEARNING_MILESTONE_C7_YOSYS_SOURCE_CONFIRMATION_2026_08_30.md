# CRSE Learning Milestone C7: independent Yosys source confirmation

Date: 2026-08-30  
Status: **complete and independently verified**  
Production promotion: **no**

## What changed

C7 tests the frozen C6 exact source-ANF implementations on an independently
authored family. No neural model was trained and no C3-C6 labels or EPFL cases
were used to select the cases.

The source fixture contains 13 files extracted without network access from a
pre-existing sparse checkout of `YosysHQ/yosys-bench` at commit
`52ff6fa991f2ab509618d8aaad02f307aac78848` under the ISC license. Exact SHA-256
and Git blob identifiers seal every file. The adapter lowers the documented
semantics of five generator families into the existing Boolean DAG:

- arithmetic addition output bits;
- arithmetic multiplication output bits;
- population-count output bits;
- indexed multiplexers; and
- binary-to-one-hot decoder outputs.

An independent scalar arithmetic oracle checks each truth table before
admission. The frozen selection contains 40 cases, balanced as ten positive and
ten negative cases in each of two sealed splits. It spans 2-10 live variables,
has no semantic duplicates, and has no alpha-structural duplicates.

## Exact paths compared

The run uses nine charged timing repetitions and measures:

1. the retained set-based source ANF;
2. packed source ANF without product caching;
3. packed source ANF with a bounded 1,024-entry product cache;
4. the retained NumPy truth-vector construction plus ANF; and
5. a new direct Python big-integer truth-vector construction plus ANF.

The big-integer path is the stronger practical control. It evaluates each
source DAG directly over packed truth columns and avoids NumPy row-matrix
construction. All paths return an exact canonical decomposition, and every
positive source proposal crosses the same truth-vector witness check.

## Results

| Method | Split | Median total | p95 total | Maximum |
| --- | --- | ---: | ---: | ---: |
| set source ANF | sealed A | 0.066 ms | 0.574 ms | 0.738 ms |
| set source ANF | sealed B | 0.068 ms | 1.206 ms | 2.385 ms |
| packed source ANF | sealed A | 0.121 ms | 0.657 ms | 0.738 ms |
| packed source ANF | sealed B | 0.167 ms | 1.354 ms | 2.568 ms |
| cached packed source ANF | sealed A | 0.128 ms | 0.669 ms | 0.738 ms |
| cached packed source ANF | sealed B | 0.166 ms | 1.388 ms | 2.562 ms |
| direct bitset truth-vector ANF | sealed A | 0.144 ms | 1.265 ms | 1.402 ms |
| direct bitset truth-vector ANF | sealed B | 0.182 ms | 2.836 ms | 5.915 ms |
| NumPy truth-vector ANF | sealed A | 0.272 ms | 1.452 ms | 1.530 ms |
| NumPy truth-vector ANF | sealed B | 0.359 ms | 3.035 ms | 6.128 ms |

Cached packed source ANF was 2.130x and 2.157x faster at median than the NumPy
control, with 2.171x and 2.186x p95 speedups. Against direct bitset truth-vector
ANF, it was 1.124x and 1.096x faster at median, with 1.891x and 2.042x p95
speedups.

The retained set source-ANF path was still faster than cached packed ANF: the
packed path reached only 0.515x and 0.409x of the set path's median throughput,
and 0.858x and 0.868x at p95. This suite has small, sparse polynomials for which
packed transform overhead costs more than explicit set products. Product
caching also supplied no decisive benefit at this scale.

All five paths achieved 1.000 classification accuracy and 1.000 canonical
partition accuracy with zero semantic mismatches.

## Interpretation

C7 confirms that C6 was not an EPFL-only or NumPy-only result. Packed source
ANF remains exact and beats a direct packed truth-vector implementation on an
external generator family, especially in the latency tail. It does not replace
the set representation for every source DAG.

The appropriate architecture is an exact representation portfolio: select set
ANF for sparse low-interaction cases and packed ANF when predicted set-product
growth justifies its fixed transform cost. Both routes retain exact truth-vector
confirmation. The selection policy must be frozen on development data and
tested on sealed families; C7 labels cannot be used to tune it.

## Verification

The independent verifier regenerated the source dataset and provenance byte for
byte, rechecked every fixture hash, reconstructed all 40 truth tables through
three independent representations, matched all 40 packed and set ANFs, replayed
all 200 method/case results and both cache streams, and recomputed every timing
summary and criterion.

Verification status: **pass**. Semantic mismatches: **zero**.

## Next boundary

Freeze a portable C7 timing package and run it once on a second CPU/Linux
machine. The second-machine result should preserve the exact dataset and method
semantics, report cold and warm streams separately, and compare set, packed,
cached packed, and direct bitset truth-vector paths. After that confirmation,
develop the cost-aware exact dispatcher without tuning on either sealed C7
split.

All 18 research tracks and all eight application areas remain preserved.

## Evidence

- Final run: `docs/recognition/runs/yosys-source-anf-confirmation-20260830-002`
- Independent verification: `docs/recognition/verification/yosys-source-anf-confirmation-20260830-002.json`
- Pre-competition-criterion development run: `docs/recognition/runs/yosys-source-anf-confirmation-20260830-001`
- Source fixture: `docs/recognition/source_fixtures/yosys-bench-human-decomposition-20260830`
- Upstream project: `https://github.com/YosysHQ/yosys-bench`
- Machine summary: `docs/recognition/learning_milestone_c7_yosys_source_confirmation_results.json`
