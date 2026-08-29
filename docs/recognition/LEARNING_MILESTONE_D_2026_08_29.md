# CRSE learning Milestone D: task-matched exact computation

Date: 2026-08-29

Retained run: `docs/recognition/runs/computation-20260829-001/` (local, Git-ignored)

Independent verification: `verification/computation-20260829-001.json`

## Scope

This is the first end-to-end test that starts with an admitted expression and
compares task-appropriate computation through four distinct exact paths:

| Path | Meaning in this experiment |
| --- | --- |
| `direct` | Recursive packed evaluation, including fixed-variable evaluation for point and restriction tasks |
| `cse` | Structural CSE plus sharing-aware flattening and the bigint flat executor |
| `cm_ir` | CM-IR canonicalization/simplification followed by the same flat executor |
| `explicit_cm` | Construction of the bounded dense exact correspondence matrix/truth function, followed by lookup or exact cofactoring |

`explicit_cm` is not the earlier portfolio's `cm` label. The latter is called
`cm_ir` here to prevent that ambiguity.

Four result contracts remain separate: one complete vector, one or more point
assignments, one or more four-variable restrictions, and repeated requests for
the same complete vector. Query counts are 1, 8, and 32 where applicable; the
repeated-vector task uses 2, 8, and 32.

The fitted router is a nine-cell task/query cost policy trained only on measured
generated training costs. It contains no expression, truth table, cached answer,
or semantic authority. A predeclared rule chooses direct for complete/point
tasks and CSE for restriction/repeated-vector tasks. The answer-cache control
computes the first repeated vector exactly and reuses it inside the request.

The rewrite comparison uses equal stop/one-candidate choices. It constructs an
exact local CM, proposes at most one canonical affine, three-input mux, or
three-input majority expression, and performs a complete independent instance
equivalence and strict node-reduction check before substitution. Detection,
candidate generation, proof, backend construction, and task execution are all
inside its total time.

## Finite run and data

- Eight variables; one requested CPU thread; no network or new dependency.
- Cooperative wall budget 120 seconds; actual wall time 7.123 seconds.
- 44 exact generated cases with group-separated train/validation/test/confirmatory
  templates: 24 training and 20 evaluation cases.
- 12 evaluation-only EPFL cones from nine circuits. The selection excludes all
  16 IDs used by Milestone C before choosing the first remaining case per circuit
  and then filling in corpus order.
- One of 42 historical eight-variable records failed the current depth/work
  admission guard and was rejected before timing; 41 remained eligible.
- 1,920 training timing rows and 5,120 evaluation timing rows, all complete.
- 560 unique case/task workloads independently reconstructed by the verifier.

The new EPFL slice contains no exact affine, three-input mux, or three-input
majority root under this bounded detector. That is retained as a natural-domain
negative observation, not converted into a positive benchmark.

## Exactness result

- Zero failed timing cells.
- Zero task-output mismatches across all 7,040 rows.
- All 100 proposed rewrite/workload instances were accepted only after exact
  equivalence and node reduction; they correspond to ten generated affine
  functions under ten task/query contracts.
- No EPFL rewrite was proposed.
- The learned-bypass route made zero model calls and had zero mismatches.
- The independent verifier checked all artifact hashes, rebuilt the fitted policy
  from raw costs, recomputed all 560 workload answers, reproduced rewrite
  decisions for 32 evaluation functions, and passed.

## Paired performance observations

Speedup is comparator time divided by arm time. Values above one are faster.
The table reports the fitted task router against the predeclared task rule.

| Split | Complete vector | Point assignments | Partial restrictions | Repeated vector |
| --- | ---: | ---: | ---: | ---: |
| Validation | 0.893 | 1.099 | 1.427 | 1.024 |
| Test | 0.912 | 0.970 | 1.654 | 1.227 |
| Confirmatory | 0.909 | 0.977 | 1.601 | 1.212 |
| EPFL D | 0.884 | 1.014 | 1.530 | 1.125 |

The fitted policy improved the deliberately coarse restriction rule by selecting
direct evaluation for the smaller query cells and CSE at 32 contexts. It also
improved repeated-vector aggregation. Its lookup overhead made complete-vector
requests 8.8–11.6% slower, and point-task results were mixed. This is a useful
task-routing signal, but not a general promotion result.

The exact answer cache improved repeated-vector work by 1.435–1.452x across all
four evaluation splits. This is a stronger deterministic control than recomputing
an identical output and must remain in future reuse experiments.

Starting from an expression, dense CM construction did not pay back at this
scale. Against the task rule, `explicit_cm` achieved these EPFL D speedups:

| Complete vector | Point assignments | Partial restrictions | Repeated vector |
| ---: | ---: | ---: | ---: |
| 0.093 | 0.293 | 0.271 | 0.472 |

This does not show that CMs are broadly unhelpful. It shows that constructing a
full 256-bit local function for these small requests is expensive when the input
is an expression and that construction is charged. Explicit CMs can still be
appropriate when already available, when they supervise a graph model, or when
reuse and decomposition amortize their cost; those are different contracts.

The one-rewrite arm was a clear negative result. Even accepted affine reductions
were dominated by exact CM construction and complete verification: its speedup
against the task rule ranged from about 0.03 to 0.24 in the retained generated
and EPFL aggregates. A profitable rewrite path therefore needs a cheaper
structural gate, proof reuse, a larger downstream workload, or a compiled proved
rule. Repeating full truth-function detection/proof per request is not viable.

## Scientific limits and next experiment

This is one short local smoke, not a cross-machine replication. The cost policy
uses task kind and query bucket only; it does not yet predict expression-specific
tail risk. EPFL is evaluation-only and nonoverlapping with Milestone C by record
ID, but records still come from the same historical corpus and upstream suite.
The run covers complete output, points, restrictions, and identical-output reuse;
it does not cover SAT, counting, BDD order, version deltas, CM decomposition, or
multi-region scheduling.

The next coherent slice is a compiled rewrite/reuse experiment: prove a small
motif rule once over metavariables, compile a cheap structural matcher, and
compare repeated use against per-instance CM proof. In parallel, freeze a second
task-routing policy with an expression-size feature and test it on a new natural
source family rather than tuning this EPFL slice.
