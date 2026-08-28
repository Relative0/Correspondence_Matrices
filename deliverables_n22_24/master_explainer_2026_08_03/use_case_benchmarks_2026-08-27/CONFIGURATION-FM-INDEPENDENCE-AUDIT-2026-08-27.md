# Feature-model shootout: independence and measurement audit

Audit date: 2026-08-27. Scope: the saved full-40 endpoint, native supplement,
and full-21-transition runs named below. This report does not automatically
apply to later trials or updates from another task.

## Bottom line

The saved bounded Boolean outputs pass substantially stronger correctness
checks. Performance conclusions remain provisional: the audit found 13
measurement/independence gaps, eight marked high priority. No timing was
rerun, no shared compiler/backend file was edited, and no historical run was
rewritten. The new audit evidence is separate from the original evidence.

In particular, do not use the historical cold-d4/warm-popcount ratio as a
speedup, the real version-delta extraction ratio as a warm-kernel ranking,
or raw serialized byte ratios as intrinsic representation compactness.

## What now passes

| Check | Coverage | Result |
| --- | --- | --- |
| CM serialized instruction replay, ignoring its cached answer | 240 endpoint cases | Exact agreement |
| ROBDD JSON replay without importing CUDD | 240 endpoint cases | Exact agreement |
| d-DNNF arc-graph replay without importing/running d4 | 240 endpoint cases | Exact agreement |
| Independent exhaustive scalar CNF oracle | 5,591,040 assignments per representation | Zero mismatches |
| d-DNNF deterministic OR, decomposable AND, free-variable-aware structural counting | All saved d-DNNF graphs | Passed |
| Official input hashes, strict DIMACS parsing, original endpoint witnesses and exact source-to-slice reconstruction | 40 inputs / 240 slices | Passed |
| Retrospective joint-witness reconstruction and exact source-to-delta reconstruction | 20 admitted transitions / 120 case pairs | Passed |
| Refused Linux transition checked with a second solver implementation | CaDiCaL195 and MiniSat22 | Both UNSAT |
| Frozen-snapshot scoped regression suite | 22 tests | Passed |

The artifact checker contains no imports from the CM compiler, benchmark
producers, or prior auditors. It uses a separate scalar CNF oracle, a separate
flat-instruction interpreter, a separate complemented-edge BDD interpreter,
and a separate d4 arc-format interpreter. The latter also computes counts
structurally, including variables omitted from a graph. Corruption controls
exercise wrong opcodes, bad dependencies, invalid BDD order, cycles, dangling
edges, nondeterministic ORs, and nondecomposable ANDs.

This is implementation independence, not external third-party certification.
It validates these saved bounded relations, not the underlying methods for
every possible input.

### Source and refusal qualifications

The original endpoint witnesses were retained and checked. Original joint
version witnesses were **not** retained. The new source audit regenerates
valid joint witnesses, saves them, and reproduces every saved residual clause
and assignment digest exactly. Those are explicitly labeled retrospective
witnesses; they are not presented as recovered original process state.

The reconstruction also succeeded across a runtime change: the historical
run used Linux/Python 3.10.20/python-sat 1.8.dev24; this audit used the existing
Windows virtualenv, Python 3.13.5/python-sat 1.8.dev20, with the CaDiCaL195
backend and original clause order. Both versions are recorded. No timing
comparison is made across those environments.

The refused pair is:

`Linux@2013-11-06T06_39_45+01_00 -> 2013-12-11T15_52_34+01_00`.

MiniSat22 independently confirms that the combined CNF is UNSAT under exact
feature-name identification. Each original model separately remains SAT.
There was no direct pair of opposite named unit clauses; no machine-checked
DRAT/LRAT proof was produced. Thus this is two-solver corroboration, not a
formally checked UNSAT certificate. The file named `refusal-certificate.json`
records these limits explicitly.

## Measurement gaps and required interpretation

The machine-readable register includes source hashes and function locations:
[measurement-gaps.json](runs/configuration-fm-measurement-audit-2026-08-27/measurement-gaps.json).

| ID | Gap | What remains valid / what must change |
| --- | --- | --- |
| M01 | Incomplete cold construction | CM compile time excludes lowering and first binding/word-plan/scratch work. Warm output sessions remain warm observations; a complete cold total needs new explicit phases. |
| M02 | Asymmetric version-delta extraction | CM includes first materialization/execution while CUDD begins with built roots. Do not rank warmed kernels using this ratio. |
| M03 | Cold external d4 versus warm popcount | The numerator includes process startup, parsing and solving; the denominator is one `bit_count` on an existing vector. Separate cold count, warm count, and vector-construction-plus-count. |
| M04 | Historical reload checks and timers differ | New instruction replay closes correctness, but historical CM reload measured JSON parsing and inspected the cached vector. CUDD reload omitted manager creation. Neither is a normalized load-and-first-query measure. |
| M05 | Unequal byte/node contracts | CM included a cached hex vector and pretty JSON; raw d4 lacked the full variable universe. d4 internal statistics differed from serialized graph counts in all 240 cases. Use the newly audited counts and separated size components. |
| M06 | Whole-process sampled RSS | RSS includes interpreter/import/input-mask overhead, is sampled at 1 ms, and compares complete-vector production with count-only d4. It is not baseline-subtracted representation memory or an OS high-water mark. |
| M07 | CUDD fixed-order label not enforced | The runner declared an initial order but did not disable automatic reordering or record its counters. All 240 final saved orders equal the declared order, but execution history is not certified. |
| M08 | Actual sifted graphs absent | The producer checked equality after reordering, but only metrics/flags were saved. Actual sifted graphs are not independently replayable from the saved evidence. |
| M09 | Fresh/reused and timing protocol incomplete | Real transitions lack matched fresh later-version arms; CM/CUDD phases run in fixed sequence and SAT enumeration is one-shot. Cache hits alone do not establish a reuse speedup. |
| M10 | Transition weighting differs from protocol | One Linux refusal leaves unequal observations by history. Original pooled summaries are not equal-history summaries. Corrected descriptive aggregates are supplied separately. |
| M11 | Historical dirty source not pinned | HEAD alone does not identify the implementation loaded from an uncommitted worktree. Current snapshots cannot retrospectively establish that source state. Future performance runs need immutable source/dependency identities and host-load records. |
| M12 | Local, sparse, mostly unchanged coverage | Outside features and auxiliaries are fixed, not existentially projected. Random points are mostly invalid; most sampled deltas are zero. No whole-model, natural-session, dense-solution, or domain-dominance conclusion follows. |
| M13 | Failure/timeout evidence is fail-fast | The external wrapper raises before final tables rather than retaining a per-cell timeout/failure row. No timeout is present in the completed saved run; future runs should retain incremental outcomes. |

The frozen protocol also describes an endpoint incidence tie-break involving
feature names, while the runner actually uses DIMACS variable IDs. The source
audit reconstructs the actual ID-based selection exactly. Preserve that
discrepancy in protocol accounting; do not silently describe the historical
selection as a different one.

Official `dd` v0.5.7 initializes its CUDD manager with automatic reordering
enabled, and an unparameterized `reorder()` invokes **group sifting**. The
appropriate historical labels are “declared-initial-order CUDD” and “CUDD
group-sifting supplement,” with the saved-order qualification above.
[Pinned official source](https://raw.githubusercontent.com/tulip-control/dd/v0.5.7/dd/cudd.pyx)

The d4 graph interpreter follows the official non-certified arc-literal
format. Its node/arc counts describe the serialized file, separately from
internal implementation counters.
[Pinned official format description](https://github.com/crillab/d4/blob/333370cc1e843dd0749c1efe88516e72b5239174/README.md)

## What the size audit changes

Median `k=16` bytes illustrate why the old raw byte ratios need qualification:

| Component / encoding | Median bytes |
| --- | ---: |
| Original CM pretty JSON, including cached hex vector | 19,471.5 |
| CM instructions only, compact JSON | 788.5 |
| Cached answer as a separate binary vector | 8,192 |
| Original ROBDD JSON | 936 |
| ROBDD compact JSON | 835 |
| Raw d4 arc file | 66 |
| d4 arc file plus audit-defined variable-universe/order/digest manifest | 316 |

These are measured encoding choices, not theoretical minimum sizes. The
audit-defined d4 bundle is an accounting example, not a new benchmarked
serialization format. User-facing original feature-name maps and executable
runtime dependencies would need consistent accounting across every arm.

The median serialized d-DNNF contains two nodes and one arc at every tested
width. This shows how small many conditioned relations became. It also
explains why interpreting d4's printed internal node counter as the file's
node count was incorrect; it does not mean d4's Boolean answers were wrong.

Full per-case accounting is in
[artifact-contracts.csv](runs/configuration-fm-measurement-audit-2026-08-27/artifact-contracts.csv).

## Statistical and workload robustness

The audit recomputes ratios by history, then gives each of the seven histories
equal weight. Descriptive 95% cluster-bootstrap intervals use 4,000 draws and
a fixed seed. These are sensitivity checks over this small selected cohort,
not population-wide guarantees or corrections for measurement bias.

For historical warm complete-output time, CM/direct-CNF ratios are:

| Width | Equal-history ratio | Descriptive cluster interval |
| --- | ---: | --- |
| 8 | 1.772 | 1.145–2.599 |
| 12 | 1.054 | 0.771–1.419 |
| 16 | 0.277 | 0.201–0.372 |

A ratio below one favors CM for that recorded task only. The `k=12` result
does not establish a reliable winner across histories.

For CM/CUDD warm complete extraction at `k=16`, the equal-history ratio is
0.624, but its interval is 0.216–1.535. Removing BusyBox makes the ratio about
1.0004. The aggregate CUDD comparison is therefore sensitive to cohort
composition; it must not become an unqualified “CM wins” headline.

The version-delta pooled CM/CUDD ratios were approximately 2.42, 2.55 and
2.99. Equal-history weighting changes them to 2.65, 2.80 and 3.29. These
corrected values are explicitly **diagnostic only** because M02 still makes
the underlying work asymmetric.

Other important coverage observations:

- 117 of 120 admitted delta cases are unchanged. The three nonzero cases are
  the first soletta transition's incidence slice at the three widths; each
  removes two assignments. This is local evidence, not model equivalence.
- At `k=16`, only 86 of 20,480 sampled point queries are valid (0.42%). A
  natural interactive or balanced valid/invalid workload could differ.
- At `k=16`, median solution density is 2/65,536. This cohort does not by
  itself establish a dense-solution advantage.
- The same bounded relation can recur: the 80 endpoint cases contain 55, 65
  and 66 distinct relation digests at widths 8, 12 and 16 respectively.

See [clustered-statistics.json](runs/configuration-fm-deep-artifact-audit-2026-08-27/clustered-statistics.json)
and [measurement-summary.json](runs/configuration-fm-measurement-audit-2026-08-27/measurement-summary.json).

## Concurrent-task and reproducibility handling

The user reported active trials in another task. This audit therefore:

- reads historical result directories without rewriting their checksums;
- uses new output directories and an isolated audit-code directory;
- never imports live CM producer code for independent semantic replay;
- snapshots an explicit allowlist of source files and hashes it before/after;
- reruns the scoped regression tests from a copied, hashed source snapshot;
- does not restart Docker, change dependencies, retime the live worktree,
  commit, push, or modify the website.

Each audit's `concurrent-change-check.json` reports unchanged historical
artifacts and no changes to its observed source allowlist during that phase.
This is not a claim that the entire project was idle or that no later update
can occur. The observed modified core files have write times after the old
benchmark manifests; those current files must not be assumed to be the old
benchmark implementation.

Docker's engine was unavailable during this follow-up. The audit used the
existing local virtualenv instead; no environment was installed or changed.
For regression, the already-installed pure-Python pytest 9.0.2 library was
appended after the virtualenv paths, keeping NumPy 2.3.2 and python-sat
1.8.dev20 from the virtualenv. The exact import locations and JUnit report
are retained. The full repository suite was not rerun; the scoped suite
contains the three feature-model producer test files and all new auditor
tests (22 passed). This avoids attributing another task's moving worktree
state to a historical benchmark.

## Evidence and next gate

Historical inputs audited:

- `runs/configuration-fm-history-pilot-full40-2026-08-27`
- `runs/configuration-fm-history-shootout-cudd-full40-2026-08-27`
- `runs/configuration-fm-history-shootout-supplement-2026-08-27`
- `runs/configuration-fm-version-delta-full21-2026-08-27`

New evidence:

- [Artifact replay summary](runs/configuration-fm-deep-artifact-audit-2026-08-27/summary.json)
- [Source reconstruction summary](runs/configuration-fm-deep-source-audit-2026-08-27/summary.json)
- [Linux refusal corroboration](runs/configuration-fm-deep-source-audit-2026-08-27/refusal-certificate.json)
- [Retrospective joint witnesses](runs/configuration-fm-deep-source-audit-2026-08-27/retrospective-joint-witnesses.jsonl)
- [Measurement gap register](runs/configuration-fm-measurement-audit-2026-08-27/measurement-gaps.json)
- [Frozen regression result](runs/configuration-fm-frozen-audit-regression-2026-08-27/summary.json)
- [Audit code and reproduction instructions](independence_audit_2026_08_27/README.md)

Before stronger performance publication, freeze the other task's chosen code
state under a new run identity and rerun matched cold/warm, fresh/shared,
fixed/group-sifted, count/output, and load/reuse cells with explicit host-load
and failure metadata. Keep all old results, refusals and this audit alongside
the new run. Additional datasets should follow that measurement repair rather
than being used to hide the existing limitations.
