# Milestone E2/R10: exact SAT and equivalence guidance

Date: 2026-08-30  
Status: implemented and measured; exact mechanism accepted; learned timing policy retained as a negative result; no production promotion

## What was implemented

E2 adds a bounded expression-to-CNF path for an explicit 1-16 variable
universe. It supports ordinary satisfiability, complete-replacement assumptions
on one resident solver, and equivalence through a satisfiable-difference miter.
One auxiliary allocator is shared by both sides of every miter.

The exact session layer:

- preserves unused original variables in the declared CNF universe;
- validates assumptions and phase hints before solver use;
- independently checks every SAT witness against every emitted clause and the
  active assumptions;
- accepts UNSAT only from the complete `pysat.solvers.Cadical195` contract;
- checks returned UNSAT cores are assumption subsets and reconfirms each core
  with a fresh complete solver;
- replaces assumptions on each solve call rather than accumulating them;
- keys resident sessions by the complete immutable CNF digest and explicitly
  records logical-version invalidation;
- refuses oversized inputs before large allocation; and
- keeps exact counting outside the SAT contract.

Two deterministic advice controls order original-variable phases by occurrence
or interaction component. A third control orders short clauses first. A bounded
depth-two cost tree can choose among fresh default, resident default, resident
occurrence phases, and resident component phases. Invalid or out-of-range
features, disabled advice, and insufficient predicted gain use an exact fixed
fallback. The model selects only execution strategy; it never predicts SAT,
UNSAT, equivalence, a witness, or a core.

Implementation review also found two defects in the older public CNF helper:
its equivalence clauses described the wrong truth relation, and its miter joined
two independently allocated auxiliary namespaces. Both are corrected and have
direct exhaustive regressions.

## Frozen study

The retained Windows run is
[`sat-guidance-e2-20260830-002`](runs/sat-guidance-e2-20260830-002).
Its immutable manifest identifies every result, and its source-fingerprint
artifact covers the E2 adapters plus the principal exact baseline sources. The
dataset contains 20 alpha-distinct formulas across mux, carry,
comparator, and independent-component families:

| Split | Cases | Task instances |
| --- | ---: | ---: |
| Training | 12 | 48 |
| Validation | 4 | 16 |
| Sealed test | 4 | 16 |
| **Total** | **20** | **80** |

Each case contributes single SAT, an eight-query incremental assumption
session, a true-equivalence miter, and a false-equivalence miter. The single-SAT
slice includes 8 raw, 8 forced-UNSAT, and 4 forced-SAT controls. Assumption
sessions contain 80 expected SAT and 80 expected UNSAT answers over the full
dataset.

Training retained 960 raw rows. Validation and sealed evaluation retained 960
more rows with five balanced repetitions of the four fixed actions, the learned
tree, and advice-off fallback. A separate 160-row functional bridge compared
direct truth, CM-IR plus packed execution, structural CSE, exact BDD, and
CaDiCaL on the same satisfiability-status vectors. Those paths perform different
internal work, so the bridge establishes task equivalence and retains diagnostic
timings; it is not a broad cross-representation speed ranking.

## Exactness

All 1,920 SAT measurement rows and all 160 task-comparison rows matched the
independent truth interpreter. Advice-off preserved every answer. The separate
[verification artifact](verification/sat-guidance-e2-20260830-002.json) checked
all file hashes and source hashes, replayed every learned decision, and made 220
fresh trusted-solver calls covering every frozen task and assumption. It found
zero semantic discrepancies.

The implementation tests additionally exhaust every assignment for all seven
expression operators, verify SAT witnesses and UNSAT cores, exercise assumption
replacement, and prove exact-digest cache reuse plus changed-version
invalidation.

## Timing result

The training-selected global fallback was resident default CaDiCaL. The learned
tree used query count first: it kept resident reuse for every eight-query
assumption session and selected fresh construction for some one-query SAT and
miter cells. That is the right qualitative distinction, but it did not repay
feature and decision cost on these small formulas.

| Frozen split | Learned / best fixed, geometric mean | Learned / best fixed, p95 | Learned choices |
| --- | ---: | ---: | --- |
| Validation | 1.0385 | 1.0714 | 20 fresh, 60 resident |
| Sealed test | **1.0420** | **1.0841** | 30 fresh, 50 resident |

The predeclared second-machine gate required the learned arm to be at least 3%
faster than the best fixed action and to stay within a 10% p95 regression. The
tail condition passed, but the learned arm was 4.2% slower in sealed geometric
mean. The local gate therefore failed.

Fresh construction was predictably poor for the eight-query session: its
training cost drove the tree toward resident reuse. Polarity and component
phase controls also failed to beat resident default overall. On these bounded
6-9 variable formulas, the task-matched functional bridge shows why learned SAT
guidance has little headroom: complete packed CSE can calculate the whole truth
vector cheaply, while CNF construction and native solver setup dominate a
single yes/no query. That observation is local to this small generated slice;
it does not generalize to larger SAT instances where truth enumeration grows
exponentially.

## Decision and limits

The exact adapter, session cache, miter, verification, and conservative policy
contracts are accepted research infrastructure. No learned action is promoted.
No Runpod resource was created and cost was $0: Windows is the required first
gate, and the negative local timing result gave no scientific reason for a
second-machine timing run despite the available authorization.

This milestone does not measure exact counting, native CUDD, large CNF corpora,
or production SAT workloads. A future R10 study should start from independently
sourced CNF or hardware miters large enough that solver decisions dominate
adapter overhead. It should retain resident default, fresh default, and
advice-off as controls. The next implementation milestone in the current
sequence is D10/R03-R05: a compile-time no-op rule bypass and larger motifs with
positive measured rewrite headroom.
