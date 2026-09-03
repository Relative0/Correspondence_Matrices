# Learning milestone C35: natural repeated-query lifecycle

Date: 2026-09-01  
Status: **locally complete and independently verified; CM promotion gate failed**

## Question

C34 found no profitable CM path for fresh one-shot natural-function evaluation. C35 tests the
more favorable lifecycle for a compiled exact representation: keep one natural function resident,
then answer many restrictions of that function. Every method must deliver the same complete reduced
relation, exact model count, SAT status, and canonical witness.

This is a representation and lifecycle experiment. It performs no training, model fitting, policy
selection, production write, or production promotion.

## Frozen natural query set

C35 reuses the independently verified 48-case C34/Yosys dataset and selects one case at every
support width from 3 through 10. Selection uses the lowest frozen source-parameter identity in each
width stratum and does not inspect method timings or outputs.

Each selected case receives 64 deterministic partial assignments derived only from its case identity
and query number. Each query fixes one to four variables while leaving at least one variable live.
The eight traces contain 512 semantic queries. They were frozen before C35 timing.

The dataset verifier independently:

- recomputed the eight width-stratified selections;
- regenerated all 512 output-blind partial assignments;
- replayed every expression against its frozen full truth vector; and
- independently projected all reduced relations, counts, SAT results, and witnesses.

It found zero trace or semantic mismatches.

## Aligned methods

Six resident methods were compared:

1. recursive direct AST restriction;
2. compiled sharing-aware flattened structural CSE;
3. compiled canonical CM IR with the same flat bigint executor;
4. full direct truth materialization followed by exact projection;
5. `dd.autoref` ROBDD restriction; and
6. resident CaDiCaL enumeration of every remaining assignment.

The direct, CSE, and CM paths recompute each reduced relation over only the live axes. The full-truth
control materializes the bounded full relation once. The BDD and SAT methods are charged only where
they deliver the same reduced-relation contract; an arbitrary SAT witness or a status-only answer is
not treated as equivalent output.

Every session charges expression decoding, representation construction or compilation, all query
and delivery work, and cleanup. Cumulative totals are recorded after 1, 4, 16, and 64 queries. The
12-block schedule counterbalances every method twice through every execution position for each case.

## Local results

The verified run contains **576 timed sessions and 36,864 timed exact queries**.

| Queries | Best fixed method | CM vs flattened CSE | CM vs direct AST | CM vs full-truth projection |
|---:|---|---:|---:|---:|
| 1 | direct AST | 0.4276x | 0.2665x | 0.4722x |
| 4 | direct AST | 0.5239x | 0.4370x | 1.1017x |
| 16 | flattened CSE | 0.7043x | 0.7800x | 2.2380x |
| 64 | flattened CSE | **0.9303x** | **1.2245x** | **3.3748x** |

CM IR amortizes its compile cost enough to pass direct AST at 64 queries. It does not break even
against flattened CSE at any frozen checkpoint. At 64 queries, flattened CSE is about 1.075x faster
than CM IR in aggregate. CM is faster than CSE on two of the eight cases, but the direct AST remains
the per-case winner on those two widths; CM therefore wins no complete per-case condition.

The full-truth projection arm is a transparent materialization control, not an optimized packed
index. Its negative result does not establish a general claim against truth caching. The strongest
ordinary comparator in this implementation is flattened structural CSE.

Pure-Python `dd.autoref` BDD and complete CaDiCaL enumeration are much slower under this complete
reduced-relation contract. This does not imply that BDD or SAT is slow for its native status/count
tasks, nor does it rank native CUDD, which is unavailable in the local environment.

## Exactness and independent verification

All methods produced the same canonical output digest for every case and block. The independent
verifier replayed eight source expressions, all 512 semantic queries, 48 contracts, 576 measurement
rows, and 36,864 timed query deliveries. It independently recomputed the lifecycle summary and found:

- semantic mismatches: 0;
- trace mismatches: 0;
- oracle mismatches: 0;
- measurement mismatches: 0; and
- summary mismatches: 0.

## What the accumulated evidence justifies

CMs have earned two narrower roles, but not a general evaluator replacement.

First, screened exact CM/GF(2) decomposition is decisively useful inside the CM computation itself.
On the fresh C23 Yosys corpus it was about 3.29x faster than exhaustive CM while delivering the same
globally best exact decomposition. That supports screened/compiled CM as the implementation path for
exact decomposition instead of exhaustive partition work.

Second, CM IR remains useful as a canonical exact representation for simplification, structural
identity, proof-carrying rules, changed-cone invalidation, and portable exact artifacts. Earlier
circuit tests found an approximately 11% advantage over a plain CSE kernel, but the stronger
flattened CSE control was effectively tied. C35 now shows a repeated-query case where CM beats direct
AST after amortization, yet still loses to flattened CSE overall.

The evidence therefore does **not** support replacing a good compiler IR, flattened structural CSE,
AIG, BDD, or SAT engine with CM IR across generic workloads. It supports CM where the task needs CM's
exact algebraic artifact or canonicalization, and it supports continued search for specific resident
query families whose structure rewards CM canonicalization enough to exceed simpler controls.

## Decision and next milestone

The frozen CM promotion gate required at 64 queries:

- at least 1.05x over flattened CSE;
- parity with the full-truth control; and
- a CM win over CSE on at least 75% of cases.

Only the full-truth condition passed. The gate fails, production promotion remains false, and a
second-machine timing replication is not warranted for this surface.

C36 should split the remaining lifecycle question into two task-matched tables:

1. fresh, wider natural repeated restrictions at support 11-16, with more than one case per width,
   efficient packed projection, flattened CSE, CM IR, and native CUDD if available; and
2. persistence/reload and related-version traces, charging serialization, reload, changed-cone
   invalidation, and break-even separately from steady-state queries.

Only an outcome-independent local result with absolute headroom beyond recognition and verification
cost should proceed to second-machine confirmation or learned selection.

## Evidence

- Verified run: `docs/recognition/runs/c35-natural-repeated-windows-20260901-002`
- Frozen dataset: `docs/recognition/c35_natural_repeated_query_dataset.json`
- Dataset verification: `docs/recognition/c35_natural_repeated_query_dataset_verification.json`
- Core adapters: `cmbench/comparative/gf2_natural_repeated_queries.py`
- Experiment: `cmbench/comparative/gf2_natural_repeated_query_experiment.py`
- Independent verifier: `scripts/crse_gf2_natural_repeated_query_verify.py`
