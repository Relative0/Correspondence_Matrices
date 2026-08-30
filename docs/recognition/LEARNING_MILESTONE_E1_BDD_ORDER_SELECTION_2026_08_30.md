# Learning milestone E1: bounded BDD order and compilation selection

Date: 2026-08-30

## Purpose

E1 adds a task-matched exact ROBDD layer and tests whether bounded variable-order
advice repays its own search and inference costs. The selected BDD is always
checked independently; the order policy proposes a compilation strategy, not a
Boolean answer.

The implementation provides:

- fixed, expression first-occurrence, source-interaction, and seeded random
  best-of-k orders;
- objectives for node count, cold build time, and build plus eight partial
  restriction queries;
- a depth-two bounded cost tree that ranks the four order strategies;
- exact BDD SAT witnesses, counts, restrictions, and equivalence checks;
- deterministic reachable-graph serialization with explicit variable order;
- strict reload and independent graph replay without importing `dd`.

`dd.autoref 0.6.0` is the portable control used here. Native CUDD and dynamic
reordering were unavailable and are not silently substituted or claimed.

## Corpus and protocol

The deterministic corpus contains 20 generated order-sensitive formulas across
mux, adder-carry, comparator, and hidden-component families at six to nine
variables. Twelve cases train the bounded cost tree, four are validation, and
four are sealed test. All 20 alpha-structural digests are distinct; training and
evaluation have zero alpha overlap.

The official run used five balanced repetitions and four seeded random orders
for best-of-k. It retained 720 training and 600 evaluation timing rows. Order
generation, every searched build, and every searched partial query are charged.
Feature and tree-decision time are charged to the learned arm. Exact checking is
separate from the timed strategy path.

Independent verification regenerated all 20 cases, refit all three model
objectives byte-for-byte, reproduced 120 per-case summaries and every aggregate,
and replayed 298 unique selected-order artifacts. SAT witnesses, exact counts,
partial restrictions, equivalence, serialization, reload, and independent truth
replay all matched.

## Sealed-test results

| Strategy | Sum of BDD nodes | Cold build total | Build + eight restrictions |
| --- | ---: | ---: | ---: |
| Fixed | 69 | 0.900 ms | 1.693 ms |
| First occurrence | **39** | **0.750 ms** | **1.434 ms** |
| Interaction | 40 | 1.035 ms | 1.702 ms |
| Random best-of-four | 51 | 4.012 ms | 7.350 ms |
| Cost tree, including features/decision | 39 | 1.182 ms | 1.871 ms |

First occurrence was the strongest deterministic control on this slice: it used
43.5% fewer summed nodes than fixed order, built 1.20x faster, and completed the
repeated-restriction workload 1.18x faster. The interaction heuristic reached
nearly the same node count but cost more to compute and build.

Random best-of-four did not include the deterministic orders as free candidates.
Once all four searches were charged, it was 5.35x slower than first occurrence
for cold build and 5.12x slower for build plus restrictions.

The fitted models collapsed to a single safe leaf selecting first occurrence.
They matched the per-case base-policy node oracle, but their overhead produced a
1.621 geometric-mean cost ratio to the sealed cold-build oracle and 1.316 for
build plus restrictions. This is a retained negative result for learned routing:
the deterministic first-occurrence rule is better at this scale.

## Decision

The exact BDD artifact and task adapters are ready for further bounded research.
No learned order policy or random search is promoted. Use first occurrence as the
current deterministic control on this generated slice, while keeping fixed and
interaction orders for order-sensitive checks. Do not generalize this ranking to
native CUDD, natural circuits, feature models, or larger support.

The next roadmap item is E2/R10: exact SAT, assumptions, incremental sessions,
and equivalence-miter guidance with independently checked witnesses and explicit
session invalidation.

## Retained development evidence

- `docs/recognition/runs/bdd-order-e1-smoke-20260830-001` — incomplete corpus
  generator smoke; no measurements started.
- `docs/recognition/runs/bdd-order-e1-smoke-20260830-002` — successful small
  smoke before final unit separation.
- `docs/recognition/runs/bdd-order-e1-20260830-001` — complete but superseded
  because one field mixed node and time units.
- `docs/recognition/runs/bdd-order-e1-20260830-002` — official corrected run.
- `docs/recognition/verification/bdd-order-e1-20260830-002.json` — independent
  regeneration, refit, aggregation, and semantic replay.

