# C39 phase result and external ACD baseline

The frozen public-corpus run completed successfully. The immutable source
selection is [FREEZE.json](FREEZE.json), with freeze digest
`da68866d14b449fc3127aa28f83cfb0c72bfb90ea0ec1f21ca09db47db8355dd`.
The primary result is in
`../runs/c39_gf2_phase_epfl_windows_20260916_001/results.json`; the external
result is in `../runs/c39_abc_acd_epfl_windows_20260916_003/results.json`.

## C15/C16 result

The predefined statistic is the sum of each public case's median
analysis-only time across five balanced rounds. It excludes BLIF parsing and
truth construction, which are checked before timing.

| Procedure | Median-case sum |
| --- | ---: |
| C15 exhaustive control | 2,614,027,400 ns |
| C16 screened implementation | 755,173,300 ns |

The observed C16-over-C15 speedup on this Windows host is **3.4615 times**.
All 19 public cases selected byte-identical best artifacts in the two paths and
all returned artifacts reconstructed their frozen truth vectors. All 12
structured and dense-negative controls also passed.

This is a comparison with the repository's C15 control. It is not an external
state-of-the-art speed claim, a cross-machine result, or a development-blind
confirmation: the EPFL mirror had been inspected in unrelated project work
before this C39 selection.

## Phase evidence

Phase counters use three separate instrumented rounds. They are direct wall
clock scopes and are not additive. In particular, C15's three constructor
scopes each include that constructor's layout and strict artifact work.

| Phase group | Calls | Aggregate instrumented time |
| --- | ---: | ---: |
| C15 rank constructor | 3,042 | 1,635,282,300 ns |
| C15 cofactor constructor | 3,042 | 2,519,589,800 ns |
| C15 Kronecker constructor | 3,042 | 1,778,378,500 ns |
| C15 outer reconstruction | 6,963 | 1,877,916,700 ns |
| C16 shared partition layout | 3,042 | 798,477,600 ns |
| C16 rank descriptor | 3,042 | 65,167,400 ns |
| C16 cofactor descriptors | 3,042 | 172,194,900 ns |
| C16 Kronecker descriptors | 3,042 | 806,395,700 ns |
| C16 canonical deduplication and ordering | 114 | 253,235,600 ns |
| C16 strict admission and outer reconstruction | 279 | 124,059,900 ns |

The measurements support the implementation explanation: C16 performs one
shared layout per partition, screens every required descriptor, and strictly
admits only a bounded leading set. They do not isolate layout alone within the
inclusive C15 constructor scopes, so they do not support a claim assigning an
exact percentage of the speedup to layout reuse.

## Public ABC ACD capability lane

The external lane uses the public [Berkeley ABC](https://github.com/berkeley-abc/abc)
source at `baf4ddb16acb94fbfe75ac0fe6a99330ba1e315a`, the revision containing
the ACD source cited in the prior-art audit. The tracked
[`abc_acd_truth_runner.cpp`](../../../cmbench/recognition/abc_acd_truth_runner.cpp)
adapter invokes its `ac_decomposition_impl` directly on the same frozen truth
vectors with a fixed 4-LUT target. The result records the executable hash and
every process result.

Across three deterministic rounds, all 19 calls were valid and the per-case
ACD outcome was stable: eight cases were reported decomposable and eleven were
reported not decomposable at the fixed 4-LUT setting. The sum of per-case
median ACD algorithm times was 56,400 ns, but it is **not comparable** with the
C16 result. ABC's output is 4-LUT ACD feasibility, LUT cost, and a delay
profile. C16 must select a byte-identical artifact under a different contract
from XOR-component, GF(2)-rank, cofactor-block, and Kronecker candidates.

## Updated safe wording

> On a prospectively frozen 19-cone public EPFL slice, the C16 implementation
> was 3.4615 times faster than this repository's C15 exhaustive control on the
> predefined analysis-only median-sum statistic, while selecting the same
> canonical artifact and reconstructing every source truth vector. Separate
> phase measurements are consistent with avoiding repeated full artifact
> construction. A public ABC ACD capability lane was run on the same truth
> vectors, but its fixed 4-LUT mapping contract has a different objective and
> cannot support a C16-versus-ABC speed or quality claim.

Do not say that C16 is faster than ABC, implements a new ACD algorithm, or
dominates external decomposition tools. A task-equivalent external comparison
would need an adapter that emits and scores the exact same canonical artifact
contract, or a redesigned shared objective fixed before measurement.
