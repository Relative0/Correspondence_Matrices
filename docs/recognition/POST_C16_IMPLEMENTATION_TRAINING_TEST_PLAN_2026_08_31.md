# CRSE post-C16 implementation, training, and comparison plan

Date: 2026-08-31  
Status: active implementation queue  
Scope: local-first research; all 18 tracks retained; no production promotion implied

## Starting point

C16 established exact descriptor screening at 3.545x locally and 3.178x on a
second Linux machine. C17 added the bounded exact dispatcher. C18 transferred
it without refitting to 73 VTR cones but exposed an unstable single-round
small-support tail. C19 then used source-cluster-separated LogikBench
development, validation, and confirmation data to freeze an always-screened
exact leaf. Its untouched 24-case confirmation passed at 2.769x aggregate and
0.972x minimum speedup. C20 compiled the leaf without truth features and, over
nine balanced retrospective rounds, reached 1.760x aggregate and 1.463x minimum
on all 11 C18 `n=3-4` controls. Production remains disabled because C19 is
one-machine evidence and C20 is retrospective.

C21/F2 has now completed the first seven-method task-matched table on all 96
frozen LogikBench cones. Packed source ANF was narrowly best at 3.007x over
exhaustive, screened CM reached 2.988x, and the per-case oracle retained only
1.059x headroom before routing overhead. Fresh BDD and proposal-only priority
paths were negative under the fresh single-query lifecycle.

C22 now implements the packed source-ANF arm with exhaustive advice-off and
fallback plus bounded shadow comparison. Its policy is frozen to C21 evidence,
but it has not been evaluated on fresh data.

The learned results remain mixed or negative. Existing matrix, graph, fused,
cut-ranking, BDD-order, SAT-routing, and rewrite-profitability policies have not
beaten their strongest cheap deterministic controls on sealed transfer data.
Further model tuning should therefore follow new data, stronger task labels, and
measured oracle headroom rather than precede them.

## Current execution order after C20

1. Freeze a new source-family confirmation table before using results to
   change any threshold, tree, compiler, or promotion decision.
2. Repeat the unchanged frozen C21/C22 package on a second CPU machine; do not fit on
   C18 or inspect C19 confirmation during selection.
3. Train another neural/classical ranker only if fresh data shows materially
   more oracle headroom than C21's retrospective 1.059x ceiling.

## Recommended sequence

### Phase 1 — C17: production-safe exact-screened GF(2) dispatcher (implemented)

Implement the C16 analyzer as an opt-in exact strategy behind the existing task
and advice contracts.

Deliverables:

- Add a versioned request/result contract for the decomposition task, including
  variable order, partition bound, materialization budget, task objective,
  platform identity, and provenance.
- Keep `explicit_cm_exhaustive` as the advice-off path and exact fallback.
- Add a cheap pre-analysis bypass for cases likely to be overhead dominated.
  Select its threshold only from development data, freeze it, then evaluate it
  without adjustment on sealed and second-machine data.
- Add bounded shadow mode: return the chosen exact result while running the
  alternative exact arm only when explicitly requested and recording its cost.
- Serialize the decision, source digest, policy digest, selected analyzer,
  fallback reason, artifact digest, and exact-check result.
- Refuse unsupported platforms and out-of-range inputs conservatively.

Required controls:

1. exhaustive CM/GF(2) materialization;
2. C16 descriptor screening;
3. source-ANF plus descriptor screening;
4. advice disabled;
5. shadow execution; and
6. a constant small-case bypass, so a learned gate must later beat an equally
   cheap deterministic rule.

Acceptance gates:

- zero semantic, reconstruction, or best-artifact identity mismatches;
- advice-off produces the same artifact as the original exhaustive path;
- no sealed aggregate or p95 regression beyond 3%;
- minimum per-case speedup at least 0.97x after bypass;
- existing C16 aggregate gates remain at least 1.25x whole-path and 1.20x p95;
- save/reload, malformed policy, unknown platform, and shadow mismatch tests;
- production promotion remains false until Phase 2 transfer passes.

Primary tracks: R01, R06, R16, R17, R18.

### Phase 2 — C18-C20: independent transfer and cheap work policy (implemented locally)

Freeze a new source-backed corpus before using its timing results. Prefer the
already present LogikBench and VTR checkouts so this phase needs no download.
Use circuit-disjoint sources such as ISCAS85 controls/ALUs, VTR BLIF circuits,
LogikBench arithmetic and control blocks, and hand-authored dense/no-factor
controls. Do not reuse EPFL or the C15/C16 Yosys family as confirmation data.

Dataset contract:

- 80–160 alpha-distinct bounded cones;
- complete source path, license, upstream identity, file hash, cone identity,
  and extraction parameters;
- 3–10 live variables for full CM/task-matched comparison;
- a separate 11–16-variable task-specific slice that may omit dense CM when the
  declared output budget refuses it;
- circuit-held-out development, validation, sealed test, and source-held-out
  confirmation groups;
- positive partitions, structure-matched hard negatives, dense random controls,
  no-sharing controls, and deliberately overhead-dominated tiny cases;
- no timing-based case selection and no discarded failures.

Run the frozen C17 policy without retraining or threshold changes. Report
coverage, abstention, exactness, median/p95/max cost, per-case regret, and memory.
Promotion requires zero exactness failures and no material regret on every
sealed source group. A negative transfer result keeps C17 opt-in and becomes the
training target for Phase 4.

Primary tracks: R02, R06, R11, R17, R18.

### Phase 3 — F1/F2: task-matched exact method comparison harness (first GF(2) table implemented)

Create one comparison harness, but keep different requested computations in
separate result tables. A method that answers SAT is not credited with producing
a complete truth vector or a decomposition artifact.

| Requested task | Exact methods and controls |
| --- | --- |
| CM/GF(2) decomposition artifact | exhaustive CM, C16 screened CM, packed source ANF plus screening, deterministic interaction/min-cut proposal, ROBDD support/cofactor proposal, structural AIG cut proposal; every proposal crosses the same exact artifact checker |
| Complete truth vector | direct AST interpreter, structural CSE, CM-IR plus packed executor, explicit dense CM construction, word-vector backend, packed ANF evaluation, bounded ROBDD enumeration |
| Point/restriction queries | direct/CSE compiled program, cached compiled CSE, ROBDD restriction, resident SAT assumptions, specialized exact CM/ANF where eligible |
| SAT and equivalence | packed truth control at bounded support, ROBDD, fresh CaDiCaL, resident CaDiCaL, equivalence miter; verify witnesses and trusted UNSAT paths |
| Exact count | packed truth popcount, ROBDD count, bounded d4 adapter if its local build is verified; never substitute SAT status for a count |
| Rewrite/optimization | no-rewrite CSE, D10 indexed proved rules, per-instance CM proof, structural AIG/ABC control when available; charge matching, proof, rewrite, rebuilding, and execution |
| Related versions/sessions | fresh rebuild, exact artifact cache, changed-cone cache, resident SAT, resident BDD, and full invalidation control |

For every table retain both kernel-only and end-to-end measurements. End-to-end
includes representation construction, feature extraction, inference, proposal,
exact verification, compilation, fallback, and requested query execution.
Memory, artifact size, cold/warm behavior, and amortization count are first-class
metrics. The website's historical kernel comparisons must remain labeled as
kernel comparisons rather than being mixed with these complete paths.

Primary tracks: R01, R06, R07, R09, R10, R13, R16, R18.

### Phase 4 — N1: exact-teacher neural and classical model rerun

Resume training only after the Phase 2 corpus and Phase 3 cost labels are frozen.
Models propose a partition, strategy, or abstention; they never certify an
answer.

Training targets:

- partition/cut ranking under exact decomposition benefit;
- probability that screening beats exhaustive materialization after all costs;
- predicted median and p95 cost for each eligible exact backend;
- residual/factor structure and ANF interaction as auxiliary targets;
- novelty, feasibility, and abstention labels; and
- optional functional retrieval, followed by an exact equivalence check.

Matched model comparison:

1. constant action and query/support threshold rules;
2. deterministic ANF interaction, signature, and min-cut heuristics;
3. linear/logistic and quantile regressors;
4. bounded decision tree/rule list;
5. forest or gradient boosting if an optional dependency is separately approved;
6. matrix MLP and matrix CNN;
7. source-DAG GNN preserving sharing, edge roles, negation, and variable identity;
8. fused graph plus CM model; and
9. a larger hierarchical model only if the smaller models show real oracle
   headroom and the dataset supports the added capacity.

Frozen initial training budget:

- CPU first, two threads, three seeds;
- 50,000–250,000 parameters for neural comparisons;
- identical circuit-held-out splits and training examples across representations;
- matched optimizer-step or wall-clock budgets, with parameter count, peak
  memory, training time, inference latency, and artifact size recorded;
- development smoke runs capped at 120 seconds; any larger campaign gets one
  explicit finite manifest before execution;
- no tuning on sealed or source-held-out confirmation groups.

Evaluation gates:

- exact checker accepts every consumed proposal; rejected proposals and their
  costs remain in the results;
- compare accuracy/ranking quality separately from end-to-end profitability;
- calibration and coverage-risk curves on validation only;
- report in-distribution, circuit-held-out, source-held-out, size transfer,
  structure-matched hard negatives, and adversarial near-matches;
- a learned policy advances only if it beats the best cheap deterministic policy
  after feature, inference, exact-check, and fallback costs on both seeds and all
  sealed groups;
- otherwise retain the model as a measured negative result and keep the exact
  deterministic dispatcher.

Primary tracks: R02, R08, R11, R12, R13, R16, R17, R18.

### Phase 5 — E3: larger BDD, SAT, equivalence, and counting workloads

E1 and E2 showed correct infrastructure but too little solver work to repay
learned advice. Build larger task-specific workloads where complete truth
enumeration is no longer the default computational contract.

- BDD: natural held-out circuits, first-occurrence/fixed/interaction orders,
  optional native CUDD and dynamic-reordering controls if available, cold build,
  repeated restriction, count, and equivalence objectives.
- SAT: independently sourced CNF and hardware miters, fresh versus resident
  sessions, assumptions, phase controls, witness/core checks, and version
  invalidation.
- Counting: exact small-support truth and BDD controls plus bounded d4 model
  counting where the executable and license are verified.
- Routing: begin with analytic query-count/amortization rules. Train a selector
  only if the frozen oracle shows meaningful headroom after adapter costs.

No cross-method speed claim is valid unless every arm answers the same task and
uses the same input/output boundary.

Primary tracks: R01, R07, R09, R10, R13, R17, R18.

### Phase 6 — D11: natural proved rewrites with positive oracle headroom

D10 proved that matching is exact but unprofitable on small cones. Search the
Phase 2 corpus offline for larger natural contractions, then measure oracle
headroom before training or enabling a matcher.

- Add only rules proved over metavariables with explicit side conditions.
- Require strict structural decrease, cycle prevention, deterministic overlap,
  provenance, save/reload, and changed-cone invalidation.
- Add a compile-time no-op bypass that costs almost nothing when no rule root is
  possible.
- Compare no rewrite, indexed match, cached match, per-instance CM proof, and
  AIG/ABC rewriting when task equivalent.
- Train profitability only if the development set contains both profitable and
  unprofitable natural regions; otherwise use no rewrite.

Primary tracks: R03, R04, R05, R09, R13, R16, R18.

### Phase 7 — A1: retrieval, uncertainty, and offline adaptation

Build deterministic retrieval before learned embeddings: canonical structural
hashes, exact truth hashes at bounded support, ANF signatures, BDD signatures,
and complement/permutation-aware signatures. Any approximate retrieval result
must be followed by exact equivalence or artifact checking.

Use logged fixed-policy data to create a finite contextual-bandit replay with
recorded propensities, rejection cost, and exact outcomes. Include hard-negative
mining and counterexample replay, but do not adapt production state or retrain
automatically. Compare active selection against fixed stratified sampling and
random sampling under the same labeling budget.

Primary tracks: R08, R09, R14, R17, R18.

### Phase 8 — L1: bounded LLM-assisted rule and strategy proposals

Extend the existing offline provider boundary before making any live model call.

- Define a small declarative Boolean-rule DSL with strict size and operator
  bounds; never execute generated Python or shell text.
- Test malformed, oversized, cyclic, duplicate, unsafe, and unverifiable output
  with deterministic fake providers.
- Compare LLM proposals against grammar enumeration, deterministic identities,
  retrieval, and randomized candidate ordering.
- Prove every rule independently before admission and measure all rejected
  proposals and generation/checking costs.
- Keep model identity, prompts, retrieval hashes, decoding settings, token/call
  limits, latency, cost, and license in the experiment manifest.
- Consider distillation into a small local ranker only after a useful verified
  proposal corpus exists. A live provider, model download, or fine-tune requires
  a separate exact resource and data-transfer approval.

Primary tracks: R05, R13, R15, R16, R17, R18.

## Test program

### Exactness and contract tests

- Exhaust all assignments for small formulas and compare AST, CSE, CM-IR,
  explicit CM, packed ANF, BDD, and SAT status under task-equivalent contracts.
- Property-test variable permutations, negations, transpose/layout transforms,
  restrictions, composition, serialization, and valid-bit masks.
- Check every accepted decomposition by full reconstruction and exact artifact
  identity; test empty/no-factor cases explicitly.
- Check SAT witnesses clause by clause, replay trusted UNSAT contracts, and keep
  exact counting separate.
- Verify advice-off, fallback, timeout, malformed model, unknown platform,
  unsupported task, and out-of-range behavior.

### Data and training tests

- Hash source files, extraction settings, formula groups, split IDs, labels,
  schedules, models, and output artifacts.
- Reject alpha/structural duplicates across splits and report semantic duplicates
  when bounded exact checking can find them.
- Prove that validation/test rows never enter fitting, calibration, threshold
  selection, normalization, or early stopping.
- Save, reload, and reproduce model outputs; reject altered metadata, parameter
  counts, schemas, or state hashes.
- Verify equivariance and invariance only for transformations whose labels are
  transformed correctly.

### Performance and systems tests

- Randomize balanced arm order and summarize per-case medians before aggregates.
- Record median, p95, maximum, worst-case regret, oracle headroom, abstention,
  memory, artifact size, cache hits, build cost, inference, checking, fallback,
  and amortization count.
- Separate cold construction, warm compiled reuse, repeated queries, related
  versions, and answer-cache controls.
- Add deterministic fake RunPod transport tests for packaging, output caps,
  deletion, reconciliation, and no-replacement behavior before any approved
  second-machine run.
- Replicate only after the local scientific gate passes. Freeze exact payload
  hashes and retain bounded raw evidence.

## Promotion policy

No phase changes production defaults merely because it is implemented. A
strategy may be promoted for one declared task/platform identity only after:

1. zero exactness failures and complete independent replay;
2. advice-off preserves the same result contract;
3. sealed circuit- and source-held-out data pass the predeclared whole-path and
   tail gates;
4. the method beats the strongest cheap deterministic control, not only a weak
   ablation;
5. malformed/OOD inputs abstain safely;
6. save/reload and version invalidation are verified;
7. a second machine reproduces the decision; and
8. rollback consists of disabling advice, without changing exact semantics.

## R01–R18 coverage

| Track | Planned work |
| --- | --- |
| R01 | C17/F1 task routing; E3 task-specific exact portfolios |
| R02 | C18 independent subclass corpus; N1 subclass and factor targets |
| R03 | D11 natural verified motifs and macros |
| R04 | D11 end-to-end rewrite profitability and stopping |
| R05 | D11 proved rules; L1 proof-admitted proposals |
| R06 | C17 exact-screened integration; C18 transfer; F1 decomposition methods |
| R07 | F1/E3 BDD, AIG, order, and compilation controls |
| R08 | N1 retrieval models; A1 deterministic signatures and exact follow-up |
| R09 | F1 related-version methods; D11 invalidation; A1 session replay |
| R10 | F1/E3 SAT, equivalence, assumptions, and counting guidance |
| R11 | C18 exact teachers; N1 graph supervision without CM at inference |
| R12 | N1 matched matrix, graph, fused, and hierarchical comparisons |
| R13 | F1/N1/E3/D11 model-family and learning-method comparisons |
| R14 | A1 finite active-learning and contextual-bandit replay |
| R15 | L1 bounded LLM proposals, controls, proof admission, and distillation |
| R16 | C17 bypass; all phases charge inference/training and record efficiency |
| R17 | C17 abstention; N1 calibration/OOD; E3 hardware transfer |
| R18 | Dense, no-sharing, hard-negative, no-headroom, and overhead controls throughout |

## Immediate implementation pass

Phases C17-C21/F2 are now implemented and independently verified locally. The
next pass should (1) add packed source ANF behind an opt-in exact dispatcher
boundary with screened/exhaustive fallback and shadow checking, (2) freeze a
new source-family task table before evaluating that changed portfolio, and (3)
repeat the unchanged methods on a second CPU machine. Retain resident BDD only
for repeated-query contracts. Do not resume neural routing on the retrospective
1.059x oracle headroom; require materially larger headroom on fresh data first.
