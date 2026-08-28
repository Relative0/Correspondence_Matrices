# Feature-model representation battery protocol

**Frozen:** 2026-08-27, before implementing or running the representation battery.

## Purpose

Test where Correspondence Matrices (CMs), packed direct CNF, structural-CSE,
ROBDDs, and incremental SAT are useful on the same bounded Boolean objects.
The campaign is a crossover study, not a search for one universal winner.

The primary natural cohort is every exact official feature-model payload that
completed the preceding diagnostic acquisition at the pinned
SoftVarE-Group/feature-model-benchmark commit
`afa60ee2c836e7bdc4068e0f4f128ea31158d2ad`.  There are three such payloads:
`automotive2@2_1`, `FinancialServices01@2017-05-22`, and
`BusyBox@2007-05-20_17-12-43`.  The unavailable endpoints remain acquisition
failures and are not replaced selectively.

## Natural cases

For each admitted model, obtain one satisfying product with CaDiCaL 1.9.5.
Select two deterministic feature slices at each width `k in {8, 12, 16}`:

- `incidence`: highest native-clause incidence, then variable number; and
- `hash`: SHA-256 order of `model_id|variable`.

Freeze all variables outside the slice to the satisfying product.  Condition
the native CNF exactly as in the V2 pilot.  The resulting bounded relation is
the common semantic object.  Bit `i` uses LSB-first slice-variable order.

## Synthetic mechanism cases

Generate planted-satisfiable CNFs independently of the natural result.  Sweep:

- `k in {8, 12, 16}`;
- raw clause count `k`, `8k`, and `64k`;
- exact duplicate fraction `0`, `0.5`, and `0.9`; and
- two fixed seeds per cell.

Clause widths are seeded in `{1, 2, 3, 4}` and every base clause is made true by a
recorded planted assignment.  Duplicate clauses are retained deliberately:
the suite tests whether canonical structural reuse pays for repeated logical
work.  Each base case has a one-clause planted-satisfiable edit for the family
and behavioral-delta tasks.  Synthetic results are mechanism evidence only.

## Arms

1. `cm`: sharing-aware CM compilation followed by the flat packed evaluator.
2. `cse_flat`: independent structural-CSE compilation and the same packed
   execution engine.
3. `cnf_bitset`: specialized direct packed CNF evaluation using precomputed
   per-width variable patterns.
4. `robdd_fixed`: symbolic ROBDD construction using the requested `dd`
   backend and the natural variable order.
5. `robdd_best5`: five deterministic random orders; report the selected graph
   and the full search cost.  Selection minimizes node count, then build time.
6. `cadical195`: local residual-CNF solver for complete and partial assumption
   queries.  It is not a packed-output arm.

Local Windows results use `dd.autoref`.  A `dd.cudd` run, if available through
the established Linux/Docker environment, is a separately labeled extension;
backend results are never renamed or pooled.

## Task-equivalent cells

### A. Construction and structure

Record expression construction, CM and CSE compile time, BDD manager/variable
setup, BDD conversion time, best-of-five total search cost, node count, flat
instruction count, primitive word-operation count, and Python-traced peak
allocation.  C-extension allocations are explicitly outside `tracemalloc`.

### B. Complete packed relation

Require exact equality of CM, CSE, direct CNF, and ROBDD extraction.  Measure
warm packed execution for CM/CSE/direct CNF.  Measure ROBDD enumeration-based
extraction at every width and assignment-by-assignment extraction only through
`k=12`.  Do not compare symbolic BDD construction directly with packed output.

### C. Complete-assignment queries

Use 256 deterministic assignments per case.  Compare packed bit lookup,
scalar residual-CNF evaluation, ROBDD restriction, and CaDiCaL assumptions.
Report query-only and construction-plus-session time.

### D. Partial-context satisfiability

For fixed fractions `0.25`, `0.5`, and `0.75`, generate 64 deterministic
contexts per case.  Compare packed-mask non-emptiness, ROBDD restriction, and
CaDiCaL assumptions.  Every decision must match.  Report query-only and
construction-plus-session time.

### E. Exact count

Compare packed `bit_count` with ROBDD model count.  Through `k=12`, also record
plain CaDiCaL model enumeration, explicitly labeled as a correctness-oriented
enumeration baseline rather than a state-of-the-art model counter.

### F. Serialization

Serialize the residual CNF, CM flat program plus packed relation, and ROBDD to
deterministic local files.  Record time and bytes.  Round-trip reload must
preserve the exact bounded relation before the artifact is admitted.

### G. Related-family and behavioral delta

On synthetic base/edit pairs, compare independent versus persistent CM
compilation, independent versus shared-manager ROBDD construction, and CSE
compilation.  Record reuse diagnostics, pair construction time, and exact
changed-assignment count.  This does not substitute for missing natural
adjacent versions.

## Timing and statistics

- Seven counterbalanced timing rounds for warm execution/query cells.
- Batch small operations so each recorded sample contains useful work.
- Medians per case; never pool `dd.autoref` and `dd.cudd`.
- Natural summaries are equal-weight model/history-cluster geometric means.
- Synthetic summaries are stratified by width, clause-count tier, and duplicate
  fraction.
- Record raw samples or all case medians, environment, seeds, input hashes,
  exclusions, failures, refusals, and timeouts.

## Acceptance gates

1. Zero exact relation, query, count, delta, or round-trip mismatches.
2. Every input and output artifact is checksummed; the auditor recomputes the
   checksum inventory before accepting aggregates.
3. A performance conclusion requires at least three natural models or a fully
   populated synthetic stratum.  Natural and synthetic claims stay separate.
4. Variable-order search cost is included whenever `robdd_best5` is cited.
5. A solver answer, symbolic graph, count, and complete packed vector are never
   treated as interchangeable outputs.
6. Missing CUDD, d-DNNF/SDD, full-history payloads, or native domain engines are
   reported as coverage gaps, not silently replaced.

## Claim boundary

The natural cases are generated bounded neighborhoods around satisfying
products, not natural configurator sessions and not existential projections.
The battery may establish representation/task crossovers and a dense-duplicate
mechanism.  It cannot establish whole-feature-model enumeration dominance,
production user-session economics, or superiority across the eight application
domains.

## Pre-execution generator correction

The first synthetic smoke stopped before writing any case result: at `k=8`,
the `64k`/zero-duplicate cell requests 512 distinct planted-satisfying clauses,
but fewer than 512 such clauses exist when widths are limited to `{1,2,3}`.
Clause width 4 was therefore added before any successful synthetic case.  No
sweep dimension, seed, requested clause count, duplicate fraction, task,
threshold, or result was changed.
