# Feature-model representation battery results

**Run date:** 2026-08-27  
**Protocol:** `CONFIGURATION-REPRESENTATION-BATTERY-PROTOCOL.md`  
**Natural source revision:** SoftVarE-Group feature-model benchmark
`afa60ee2c836e7bdc4068e0f4f128ea31158d2ad`

## Executive result

The comprehensive battery found a real, repeatable crossover rather than a
universal winner.

- For complete packed relations on the three official feature-model payloads,
  direct CNF won at `k=8` and `k=12`, while CM won at `k=16` on both Windows
  and Linux.  The `k=16` CM/direct-CNF ratio was `0.472` on Windows and `0.463`
  on Linux: CM was about `2.12x` and `2.16x` faster respectively.
- CM beat the independent structural-CSE packed evaluator at every natural
  width on both platforms.  Ratios ranged from `0.571` to `0.745`, a roughly
  `1.34x-1.75x` CM advantage.
- CUDD was the strongest symbolic-construction engine once its manager and
  variables existed: expression-to-BDD conversion was `8.6x--12.5x` faster
  than CM compilation.  Fresh CUDD manager/variable setup cost `3.8--7.0 ms`,
  however, so manager lifetime is decisive.
- When the required output was the same complete packed vector, CM was
  `4.1x--5.5x` faster than `dd.autoref` enumeration and `6.4x--8.5x` faster
  than CUDD enumeration on the natural cohort.  This is not a claim that CM is
  a better symbolic representation.
- ROBDDs were dramatically smaller serialized artifacts.  The CM flat program
  plus packed relation was `3.0x`, `4.9x`, and `24.7x` the CUDD JSON size at
  `k=8`, `12`, and `16` respectively.
- CM persistent compilation did not benefit from one-clause synthetic edits:
  median persistent hits were zero and reuse compilation was `1.33x--1.48x`
  fresh CM compilation.  Shared-manager ROBDD updates did benefit, taking
  `0.71x--0.79x` fresh CUDD conversion time and `0.29x--0.45x` fresh autoref
  conversion time.

The evidence supports a task router, not a blanket CM-dominance statement.

## Coverage and correctness

Two separately labeled full runs completed:

| Series | Environment | BDD backend | Cases | Partial rows | Family edits | Wall time |
|---|---|---|---:|---:|---:|---:|
| Windows | Python 3.13.5 / NumPy 2.3.2 / PySAT 1.8.dev20 | `dd.autoref 0.6.0` | 72 | 216 | 54 | 192.8 s |
| Linux container | Python 3.10 / NumPy 2.2.6 / PySAT 1.8.dev24 | `dd.cudd 0.5.7` (native CUDD) | 72 | 216 | 54 | 130.1 s |

Each series contains 18 natural cases—three official models, two deterministic
slice strategies, and `k in {8,12,16}`—plus 54 planted synthetic cases.

The protocol records one pre-result generator feasibility correction.  The
synthetic clause-width set was expanded from `{1,2,3}` to `{1,2,3,4}` after the
first smoke stopped before producing a case: the `k=8`, `64k`, zero-duplicate
cell otherwise had too few distinct planted-satisfying clauses.  No successful
result, sweep dimension, seed, threshold, or requested case count was changed.

Both independent audits passed.  Across the two series they reconstructed:

- 144 complete bounded relations;
- 27,648 partial-context decisions against ROBDD and CaDiCaL;
- 432 CM/CNF/ROBDD serialization round-trips; and
- 108 related-family behavioral deltas.

There were zero relation, point-query, partial-context, count, serialization,
or family-delta mismatches.

## Natural complete-output results

Ratios are equal-weight geometric means over the three histories and two slices
per history.  Lower than 1 favors CM.

### Windows / `dd.autoref`

| `k` | CM / direct CNF | CM / CSE-flat | CM / ROBDD extraction | Median fixed BDD nodes |
|---:|---:|---:|---:|---:|
| 8 | 2.325 | 0.596 | 0.245 | 9 |
| 12 | 1.292 | 0.612 | 0.180 | 13 |
| 16 | **0.472** | **0.745** | **0.221** | 17 |

### Linux / CUDD

| `k` | CM / direct CNF | CM / CSE-flat | CM / ROBDD extraction | Median fixed BDD nodes |
|---:|---:|---:|---:|---:|
| 8 | 2.354 | 0.571 | 0.128 | 9 |
| 12 | 1.730 | 0.673 | 0.118 | 13 |
| 16 | **0.463** | **0.736** | **0.156** | 17 |

The CM/direct-CNF transition reproduced across the two machines despite their
different Python, NumPy, PySAT, and `dd` versions.  It is consistent with the
mechanism observed in the earlier eight-variable pilot: as packed width and
repeated residual work increase, CM canonicalization can amortize its dispatch
and representation overhead.

## Symbolic construction and ordering

Fresh CUDD has two very different timing windows:

| `k` | CM compile | CUDD manager/vars | CUDD expression conversion | CM / conversion |
|---:|---:|---:|---:|---:|
| 8 | 1,394 us | 6,968 us | 145 us | 9.62 |
| 12 | 1,951 us | 3,880 us | 156 us | 12.52 |
| 16 | 2,394 us | 3,839 us | 277 us | 8.63 |

Thus CUDD is clearly stronger for conversion into an already-live manager, but
not necessarily for a one-off fresh-manager call.  A production comparison
must state manager lifetime and charge declaration/setup somewhere.

Best-of-five deterministic random ordering did not improve the natural cohort.
The selected/fixed node ratio was `1.00-1.017`; the natural fixed order was as
good or slightly better.  Search cost was `5.8x-8.6x` one fixed autoref build
and `8.0x-10.3x` one fresh CUDD setup-plus-build.  Reporting only the selected
build would therefore be misleading.

## Point and partial-context queries

For 256 complete-assignment queries, an already-materialized packed relation
was much faster than Python-level BDD restriction or repeated solver calls.
On the natural CUDD run, packed/BDD query-only ratios were `0.020`, `0.021`, and
`0.054` at `k=8`, `12`, and `16`; packed/CaDiCaL ratios were `0.021`, `0.035`,
and `0.089`.  Including CM construction and relation materialization versus
fresh CUDD construction plus 256 queries, the CM workflow ratios were `0.170`,
`0.282`, and `0.370`.  These results apply to the tested `dd` wrapper/API and
batch size, not every possible native BDD query implementation.

Partial contexts produced a different crossover.  The table reports
packed-mask session time divided by CUDD restriction or CaDiCaL assumption
session time; lower favors the packed relation.

| `k` | Fixed fraction | Packed / CUDD | Packed / CaDiCaL | Winner |
|---:|---:|---:|---:|---|
| 8 | 0.25-0.75 | 0.382-0.520 | 0.213-0.280 | Packed |
| 12 | 0.25-0.75 | 0.671-0.754 | 0.421-0.709 | Packed |
| 16 | 0.25-0.75 | 4.865-4.944 | 3.881-6.331 | CUDD/SAT |

At `k=16`, constructing and intersecting 65,536-bit masks for each new context
became more expensive than symbolic restriction or SAT assumptions.  This is a
useful negative result: the complete-output win at `k=16` does not imply a
partial-context-query win at the same width.

## Counting and serialization

Once a packed relation existed, integer `bit_count` was `9.6x-29.7x` faster
than the CUDD count call on the natural cohort.  This excludes construction;
for count-only work, a BDD or dedicated model counter can avoid materializing
the full relation and may remain the correct choice.

CM JSON serialization and reload were faster in these Python paths, but the CM
artifact was much larger because it included the full packed relation.  At
`k=16`, it was about `24.7x` the CUDD JSON size (`39.1x` the autoref JSON size).
This is the expected explicit-output cost, not an implementation accident that
should be hidden.

Python `tracemalloc` is reported in the raw data for the Python arms.  It must
not be used to compare CUDD memory because it cannot see C-extension heap
allocations.  A future subprocess/RSS study is required for native memory.

## Synthetic crossover map

The synthetic suite varied width, clause count (`k`, `8k`, `64k`), exact
duplicate fraction (`0`, `0.5`, `0.9`), and two seeds.  Natural and synthetic
results remain separate.

Across the 27 cells, CM/direct-CNF classification agreed on both platforms:

- 14 robust CM wins;
- 13 robust direct-CNF wins; and
- zero platform-discordant cells.

Every `k=16` cell favored CM, including zero-duplicate cases.  At `k=8`, only
the `64k`/90%-duplicate cell favored CM.  At `k=12`, CM won the three
90%-duplicate cells and the `64k`/50%-duplicate cell.  The strongest cell was
`k=16`, `64k` clauses, 90% duplicates: CM/direct-CNF was `0.0591` on Windows
and `0.0509` on Linux, about `16.9x` and `19.6x` faster.

Against structural-CSE, 20 of 27 cells were robust CM wins, three were robust
losses, and four were platform-sensitive.  Against ROBDD full extraction, 12
cells robustly favored CM, 14 robustly favored ROBDD extraction, and one was
platform-sensitive.  Solution density matters: enumeration from a very sparse
BDD result can be cheaper than constructing a dense packed vector, while dense
solution sets impose explicit output work on the BDD arm too.

## Related-family result

The one-clause synthetic edit did not validate CM's current persistent-cache
economics:

| Backend series | `k=8` CM reuse/fresh | `k=12` | `k=16` | Median CM hits |
|---|---:|---:|---:|---:|
| Windows/autoref run | 1.407 | 1.380 | 1.460 | 0 |
| Linux/CUDD run | 1.329 | 1.367 | 1.479 | 0 |

By contrast, a shared BDD manager reused canonical nodes.  Shared/fresh edit
conversion ratios were `0.446`, `0.420`, and `0.289` for autoref and `0.795`,
`0.727`, and `0.710` for CUDD at `k=8`, `12`, and `16`.

This rejects a current CM version-reuse claim for the tested edit mechanism.
It does not prove that no finer-grained CM cache could work, but such a cache
would be a new implementation requiring new evidence.

## What should be shown to viewers

1. A complete-output crossover chart: direct CNF wins small/sparse cases; CM
   crosses over with width and repeated work.
2. A symbolic-construction chart that separates CUDD manager setup from
   expression conversion.
3. A task selector: complete vector, point batch, partial context, count, and
   compact storage have different winners.
4. The synthetic width/density/duplication phase diagram, explicitly labeled
   mechanism evidence.
5. The negative family result and the explicit-output storage cost.
6. Exactness, refusals, acquisition gaps, and backend/platform labels beside
   every chart.

## Remaining gaps and next tests

- Complete the frozen 40-endpoint natural history cohort from a predownloaded
  archive; the current natural sample has only three models and no adjacent
  versions.
- Replay natural configurator sessions with additions and retractions rather
  than generated fixed contexts.
- Add a competition-grade model counter/d-DNNF and SDD implementation for
  count/conditioning tasks; CaDiCaL enumeration is only a correctness baseline.
- Measure CUDD and CM peak RSS in isolated subprocesses, including manager
  reuse, rather than comparing `tracemalloc` across Python and C heaps.
- Add domain-native batteries after the configuration methodology is stable:
  Cedar policy versions, Biodivine intervention families, DMN Boolean tables,
  Alive2 pure-Boolean predicates, and RevLib classical reversible functions.

## Artifacts

- Windows/autoref run:
  `runs/configuration-representation-battery-autoref-2026-08-27/`
- Linux/CUDD run:
  `runs/configuration-representation-battery-cudd-2026-08-27/`
- Runner: `cm_feature_model_representation_battery.py`
- Independent auditor: `cm_feature_model_representation_battery_audit.py`
- Focused tests: `tests/test_cm_feature_model_representation_battery.py`

Diagnostic smoke directories are retained but are not part of the headline
72-case evidence.
