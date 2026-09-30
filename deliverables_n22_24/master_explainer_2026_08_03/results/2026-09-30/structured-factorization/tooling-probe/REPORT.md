# PySDD live local-vtree tooling probe — 29 September 2026

**Verdict: SUPPORTED / tooling GO on the installed Windows PySDD 1.0.6 wheel.**
The same referenced compiled SDD can survive child swaps, left rotations and
right rotations, including below the root, without rebuilding the input CNF.
The native operations restructure the SDD and may perform internal Apply and
compression work; they are not constant-time edits. This finding resolves the
tooling question only. It does not revise the Phase 5B algorithmic gate or claim
an improvement on its frozen held-out campaign.

## What the Phase 5B audit established

- The ZIP's `code/hybrid_core.py` and `code/benchmark.py` are byte-identical to
  the unpacked files. ZIP SHA-256:
  `dfb358444e91c2db51931af4ea1ff0faf9b98bb5de5eb2c95a432218e6fce3e6`.
- `compile_extract` creates a vtree and manager, replays clause disjunctions
  and conjunctions, references the root, optionally calls `manager.minimize`,
  extracts, dereferences and returns a dictionary. It does not return a live
  manager/root session that the caller can move.
- `benchmark.neighbors` already describes exactly the required child swaps
  and binary rotations. Each M-method candidate instead calls
  `compile_extract` anew. Its two-round, six-unseen-neighbors-per-round policy
  is a frozen pilot policy, not a PySDD limitation.
- `objective` uses direct certified factors, root size, residual-cut proxy,
  and the specified optional carrier/defect features. Semantic prime truth
  belongs to the evaluator/oracle control. No replacement truth-driven
  objective was introduced in this probe.
- The read-only diagnostic audit confirms 10,440 occurrence mappings,
  1,020 distinct moves and 174 residual measurements, all marked `ok`.
  All mappings explicitly flag reuse of residual timings. The median recorded
  candidate compilation across those original occurrences is 4.007 ms.
  Those are historical recompilation measurements, not live-move measurements
  or 10,440 independent residual timings; they were not rerun or used to choose
  the synthetic inputs.
- The tooling record accurately identifies CPython 3.10.11, PySDD 1.0.6,
  disabled automatic minimization and the fresh-compilation cost. Its pinned
  environment remains usable; no installation or environment change was needed.

## Concrete supported method

`live_moves.py::LiveSession` compiles once, holds the manager and referenced
root, and exposes `move`, `undo`, `snapshot` and `one_round`.

1. Disable automatic GC/minimization during construction. Reference every SDD
   root that must survive. A Python reference alone does not pin the C node.
2. Call `manager.garbage_collect()` before a move so no dead SDD nodes remain
   inside or above the affected subtree. The prototype verifies `dead_count()==0`.
3. Resolve the subtree by a path of left/right choices from **a fresh
   `manager.vtree()` lookup**. Use the manager-owned vtree, not the separate
   `Vtree` originally supplied to `SddManager.from_vtree`.
4. Invoke the native operation with the mapping below and check its integer
   return value. `1` means success; `0` means the configured limit prevented it.
5. Read the tree and SDD elements afresh, extract certified direct factors,
   and score. Do not cache vtree positions, old child relationships or SDD
   element arrays across an edit.
6. To compare sibling candidates, undo each successful move, then replay the
   selected descriptor once. A rejected *successful* candidate requires an
   inverse; a native return value of `0` already rolls the operation back.

Here `v` is the root of the subtree being replaced, resolved immediately
before the call:

| Desired tree edit | PySDD call | Inverse, resolved again at the same subtree path |
|---|---|---|
| `(A,B)` → `(B,A)` | `v.swap(manager, limited)` | `v.swap(manager, 0)` |
| `(A,(B,C))` → `((A,B),C)` | `v.right().rotate_left(manager, limited)` | `v.rotate_right(manager, 0)` |
| `((A,B),C)` → `(A,(B,C))` | `v.rotate_right(manager, limited)` | `v.right().rotate_left(manager, 0)` |

The asymmetric left/right receiver is important. Invalid leaf/rotation
requests are rejected in Python before entering C. PySDD 1.0.6's `root.ref()`
returns `None` despite its docstring, so do not assign or chain its return value.
Balance references with `deref()` only after all moves/queries finish.

The default prototype uses `limited=0` on these small, bounded inputs.
For a size-limited candidate, initialize the size reference with
`manager.init_vtree_size_limit(manager.vtree())`, set operation limits, then
use `limited=1`. Initialize/update the reference again as the accepted state
changes. Twenty deliberately limited failures were checked for intact tree,
function, direct partition and additional referenced root. An inverse uses
`limited=0`: a capped inverse is not a reliable restoration strategy. This
prototype does not provide a hard time or memory bound for arbitrary inputs,
nor validate concurrent use, WMC caches, or copying between managers.

This method is explicitly supported by the maintainer's
[rotation example](https://pysdd.readthedocs.io/en/latest/examples/build_formula.html#example-4-vtree-rotations)
and [Vtree API](https://pysdd.readthedocs.io/en/latest/classes/Vtree.html).
The installed `pysdd/sdd.pyx` bindings and bundled libsdd-2.0
`op_left_rotate.c`, `op_right_rotate.c`, and `op_swap.c` were inspected for
receiver semantics and rollback. The documentation displays an older version
label; installed-version execution is the basis for this tooling verdict.

Minimal use from this probe directory:

```python
from live_moves import LiveSession

with LiveSession(4, [[1, 2], [-2, 3], [-1, 4]], ((1, 2), (3, 4))) as s:
    parent = s.snapshot()
    ok, native_ns = s.move((), 'left')
    assert ok == 1
    candidate = s.snapshot()             # still the same referenced SDD root
    s.undo((), 'left')
    assert s.snapshot() == parent
    chosen = s.one_round()               # direct-factor/size M2 only
    assert s.compile_count == 1
```

`one_round` checks every neighbor for demonstration. It is not an altered
version of the frozen two-round/six-candidate campaign. Its candidate ordering
and neighbor set were checked against the copied Phase 5B helper.

## Exactness evidence

`verify.py` completed successfully in 13.24 seconds:

| Check | Result |
|---|---:|
| Initial sessions | 546 |
| Forward local moves / inverse local moves | 1,718 / 1,718 |
| Forward swaps / left rotations / right rotations | 1,130 / 300 / 288 |
| Forward moves below the root | 636 |
| State checks | 5,788 |
| Assignment comparisons | 738,184 |
| Nonfalse / false state checks | 5,735 / 53 |
| Three-round searches compared with fresh-compilation selection | 8 (24 rounds; 23 accepted moves) |
| Additional-root round trips | 21 |
| Limited failures / limited successes | 20 / 1 |
| Invalid descriptors rejected before native calls | 2 |
| Disagreements | 0 |

Coverage includes every Boolean function on one, two and three variables,
both three-leaf ordered binary shapes, and new cases through twelve variables.
Additional cases exercise true, false, literals, free variables, trimmed nodes,
non-numeric leaf order, internal rotations and multiple referenced roots.

For each checked state, an independent bitset evaluator traverses the current
SDD DAG and compares **all assignments** to direct CNF evaluation; global
model counts are also checked. Direct partitions are checked against independent
Cartesian projections along the current tree. Every principal forward move is
also compared with a fresh compilation for tree, element size, decision count,
satisfiability and direct partition. Undo checks the restored parent. Equal
model counts alone would not establish exactness; full functions are compared.
Evaluation truth is confined to `verify.py` and never passed to the scorer.

## Move cost versus fresh compilation

Eight fixed synthetic cases (6–12 variables), all 112 initial one-hop
neighbors, seven measured temporal repetitions plus one warmup, randomized
candidate and method order. There are 784 measured candidate triplets and
56 complete-round triplets, with zero structural disagreements. The workload
and measurement definitions were written to `timing_plan.json` before timing.

All values below are per-case medians in **microseconds**. The live candidate
column includes GC checks, tree-path lookup, native move, extraction, unchanged
M2 scoring, and inverse restoration. Initial compilation is excluded from
this amortized column and included in the complete-round table below.

| Synthetic case | Native forward call only | Live candidate + undo | Fresh manager/CNF + score, preloaded vtree | Phase 5B full compile + score |
|---|---:|---:|---:|---:|
| Implication chain, n=6 | 12.4 | 51.4 | 124.9 | 3,156.9 |
| Independent pairs, n=6 | 11.3 | 57.6 | 164.5 | 3,628.6 |
| Interleaved factors, n=8 | 12.7 | 62.1 | 184.0 | 3,157.6 |
| Parity, n=8 | 6.2 | 48.1 | 1,390.4 | 4,999.6 |
| Planted 3-CNF, n=8 | 12.0 | 66.8 | 596.1 | 4,085.3 |
| Implication chain, n=10 | 13.6 | 60.6 | 186.3 | 3,278.3 |
| Planted 3-CNF, n=10 | 14.0 | 88.0 | 988.0 | 4,993.7 |
| Planted 3-CNF, n=12 | 14.2 | 84.4 | 1,765.5 | 5,759.8 |

Paired by target tree, taking each method's median over the seven repetitions
before geometric aggregation, the live/fresh-preloaded ratio is 0.0355–0.4243
across these cases (about 2.4–28.1 times faster). This excludes initial session
setup. The corresponding live/full-Phase-5B ratio is 0.0100–0.0207; much of that
larger difference comes from eliminating temporary-vtree file handling.
The preloaded comparator confirms the benefit is not solely a file-I/O effect.

Complete single-round medians in **milliseconds**, including initial
compilation, GC where needed, all candidates, selection, winner replay for live
search, and closing the sessions:

| Synthetic case | Live | Fresh, preloaded trees | Phase 5B full |
|---|---:|---:|---:|
| Implication chain, n=6 | 0.736 | 1.609 | 32.723 |
| Independent pairs, n=6 | 1.106 | 2.254 | 34.749 |
| Interleaved factors, n=8 | 1.424 | 3.933 | 46.397 |
| Parity, n=8 | 2.275 | 24.057 | 68.463 |
| Planted 3-CNF, n=8 | 2.058 | 12.334 | 57.521 |
| Implication chain, n=10 | 1.676 | 5.030 | 59.886 |
| Planted 3-CNF, n=10 | 3.868 | 24.371 | 93.010 |
| Planted 3-CNF, n=12 | 5.407 | 51.270 | 126.774 |

Live/preloaded whole-round ratios are 0.095–0.491 (about 2.0–10.6 times faster).
Both these paths preload the same target vtrees outside the timer; the full
Phase 5B path includes file serialization/read and cleanup. Candidate-level
fresh-preloaded timings exclude session disposal; full reference timings
include its function-return cleanup. Whole-round timings include explicit
session close and normal Python object lifetime; cyclic GC remains enabled.

These are small, single-process engineering measurements on an uncontrolled
Windows desktop, not confidence intervals, industrial benchmarks or a revised
held-out result. Seven repetitions measure temporal variation, not seven
independent problem samples. Search quality, SAT residual cost and larger-case
resource behavior were not re-evaluated.

## Scope, provenance and reproduction

All new files live in `live_vtree_probe_2026-09-29`, a sibling of the archived
directories. The copied `reference` modules are byte-identical source inputs;
their campaign entry points were never run. Attached-document instructions
were treated as historical content, not authorization to continue old campaigns.

`provenance.py` inventories 3,821 files under `continuity_archive` and
`phase5b_output`, including the installed environment and package-verification
copies. `archive_verification.json` records the final comparison. No held-out
or other campaign input was executed, no objective was retuned, and no semantic
prime truth was used in objectives. No dependency or archived source was edited.

From this probe directory in PowerShell:

```powershell
& '../phase5b_output/.venv/Scripts/python.exe' -B verify.py
& '../phase5b_output/.venv/Scripts/python.exe' -B measure.py
& '../phase5b_output/.venv/Scripts/python.exe' -B provenance.py after
```

These commands rerun only this synthetic probe and replace its local result
files. Keep `-B` to prevent bytecode writes to the preserved environment. Do not
run `provenance.py before` when verifying the existing preservation receipt.

Evidence files: `correctness.json`, `correctness.log`, `timing_plan.json`,
`timing_environment.json`, `timing_raw.json`, `timing_summary.json`, `timing.log`,
`reference_provenance.json`, `archived_diagnostics_audit.json`,
`archive_before.json`, and `archive_verification.json`.

The tooling question is complete. Defer any campaign integration until a
separate protocol and explicit scope authorize a new experiment; preserve all
frozen Phase 4/5 conclusions and artifacts.
