# Bounded counting across overlapping CNF constraints

The previous factorized counter retains exponential packed work for an inseparable cycle, while CUDD handles that example well. Test a materially different mechanism: exact sum-product bucket elimination, whose table size follows the chosen elimination width rather than total connected support. Keep it opt-in and refuse work beyond explicit table, operation and ordering budgets. No approximation, automatic routing or changes to previously sealed sources.

## Prospective admission

Use SoftVarE-Group/feature-model-benchmark commit `afa60ee2c836e7bdc4068e0f4f128ea31158d2ad`. Among tracked `.dimacs`/`.cnf` files, group by the domain/system path, choose the smallest byte-size file per system (lexicographic path tie-break), then take the first 12 systems ordered by chosen byte size and path. Freeze these candidates before downloads. Admit strictly parsed full CNFs with 1–512 declared variables and at most 3,000 clauses, retaining all rejected files and reasons. This is a size-defined feasibility cohort, not a representative sample of the full repository. Do not slice variables. Count assignments to all declared CNF variables; do not equate these with projected feature-product counts without a conversion proof.

Synthetic development uses widths 12/16; confirmation uses widths 22/24 and 80/160. Include overlapping cycles, bounded-band constraints and dense-width refusal controls, with seed 2026091161. The n22/n24 equality-cycle functions were already negative controls in the preceding campaign and are not independent new functions; retain them explicitly as mechanism comparisons. Larger widths and seeded band fixtures supply new structural tests. A recurrence supplies independent cycle counts; CUDD uses arbitrary-precision traversal rather than its floating-point count interface for large bases. Preserve all cases, refusals, regressions and timeout receipts.

## Implementation and comparisons

Implement a strict CNF plan from direct clauses and expression/CM CNF ingress. Perform exact unit propagation, retain forced and unused-variable accounting, then compile a bounded natural or min-fill elimination schedule. Sum products with Python arbitrary-precision integers; per-query fixed assignments select a branch at elimination. Guard the complete schedule before table allocation, release consumed factors, and retain only reusable input tables and schedule metadata between queries. Tests cover arbitrary clauses, constants, contradictory units, unused axes, fixed contexts, reordered names, deep expressions and budget refusal.

Compare cold parse/convert/compile/count/deliver/release and separate warm q1/q8 batches across direct bucket natural/min-fill, CM ingress, current factorized/CSE packed controls where width ≤24, and native CUDD natural/dynamic orders. Nine alternating-order repetitions. Use fresh subprocess limits for public cases, so an unfavorable native ordering cannot consume the whole host. Record exactness, schedule widths/work bounds, preparation costs, resource refusals and process memory. Do not select a winning ordering after confirmation.

## Authorization and source lineage

Continue the existing renewed $5 RunPod authorization. Carry the preceding scalar campaign's **$0.54 reservations** forward; each new attempt reserves $0.18, including failures. New files and a new audit directory preserve the four previous sealed audits, including scalar manifest `3f2667a8c8dda1bcbafeef71662bba9c61ae6b6c8d96178801b2a724595c8a48`. Use the existing authenticated controller/ownership cleanup, with no credentials sent to pods. No commit, push, publication or default integration.

Primary sources: [Dechter, Bucket Elimination](https://www.sciencedirect.com/science/article/pii/S0004370299000594), [the author's publications](https://ics.uci.edu/~dechter/publications.html), [the feature-model benchmark](https://github.com/SoftVarE-Group/feature-model-benchmark), and [dd/CUDD implementation](https://github.com/tulip-control/dd).
