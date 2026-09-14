# CM benchmark portfolio disposition

Date: 2026-09-15. This record answers whether the September 13 catalog's 80 proposed test families became completed benchmarks and which remaining work is worth pursuing after the attribution audit and matched biology pilot.

## Decision

The current benchmark program is complete for its immediate decision: **the present implementation has no demonstrated CM-specific performance advantage that justifies broader or paid scaling**. The catalog was a research menu, not an 80-item execution checklist. Every catalog entry was originally marked `recommended_not_executed` with zero frozen inputs, and the execution prompt explicitly said not to implement all 80 before obtaining a useful core result.

That core result now exists. The attribution audit classified 41 material claims, validated native controls on all 22 closed biology models and found no isolated CM performance effect. The bounded successor screen retained 108 cells, 105 successes, three timeouts and zero count mismatches. The matched local biology pilot then retained 288 cells, 255 successes, three timeouts, 30 explicit refusals and zero output disagreements. At q64 the primary family-weighted CM/raw total-session ratio was 1.0025. Every completed matched pair used the same normalized query plan and evaluator, so more repetitions would refine timing around the same mechanism rather than test a distinct CM algorithm.

The frozen 396-session all-closed-model replication in `NEXT_LOCAL_PLAN.json` is therefore deferred. The earlier proposed 2,400-base-case cloud campaign should be treated as **superseded as a blanket objective**, not as unfinished mandatory work. Its individual families remain available when a new mechanism or concrete use case supplies a reason to run them.

## Disposition of the 80-family catalog

“Covered” below means sufficient evidence exists for the present decision. It does not mean every source and scale named in the September 13 catalog was downloaded and executed.

| Catalog area | IDs | Current evidence and disposition |
| --- | --- | --- |
| Hardware and logic design | H01–H10 | Prior task-matched hardware, complete-vector, multi-root and equivalence studies already established task-specific wins and losses, while the attribution audit found no general CM-specific effect. Do not launch a fresh EPFL/Yosys/IWLS/VTR sweep unless a new CM representation mechanism or an actual hardware consumer defines a falsifiable claim. |
| Configuration and feature models | F01–F10 | Previous feature-model work validated original/concrete projections, exact counts, conditioning and representation limits on public models. The useful remaining case is an actual ordered configurator history for F08/F09/F10; generated histories add little after the current no-go. Defer until such a consumer trace exists. |
| SAT, counting and verification | C01–C08 | C04 and parts of C05 received exact native-counter and projection controls, including d4/Ganak and adversarial contracts. Broader SATLIB/competition coverage would compare native algorithms rather than isolate CM under the current implementation. C01–C03 become relevant only if CM gains a distinct SAT mechanism. Weighted counting, dependency optimization and QF_BV (C06–C08) require new semantic adapters and are out of scope absent a product need. |
| Biology, reliability and probability | B01–B08 | B01 semantics/corpus and B03/B04 fixed-point/perturbation work are covered by the 22-model correctness audit and 288-session matched pilot. B02 asks a different simulation question and does not resolve the fixed-point result. Fault-tree and Bayesian probability lanes B05–B08 require weighted/domain adapters; pursue only for a specific reliability or inference use case. Open-model source recovery is provenance work, not a reason to extend performance timing. |
| Policies and data filtering | P01–P06 | No natural CM consumer or preserved policy/data semantics has been demonstrated. Building six adapters would be speculative. Defer the entire area until a concrete policy, bitmap or eligibility workload is supplied. |
| Affine logic and coding | A01–A06 | Prior affine, packed and bucket studies exercised the main algebraic mechanisms. Those methods are algorithmically general, so expanding LDPC/CRC/GF(2) corpora without a matched CM-specific ablation would not repair attribution. Reopen only with a distinct CM mechanism and a native M4RI/XOR-aware baseline. |
| Synthetic mechanism and boundary tests | S01–S16 | Existing local campaigns and regression suites cover constants, sharing, parity, decomposition, width, cache and 24–32-variable boundaries well enough to explain current behavior. The catalog-specific 600-case expansion is unnecessary. Repeat targeted mechanisms only after relevant implementation changes; do not accumulate more synthetic repetitions to manufacture confidence. |
| Lifetime and delivery tests | L01–L08 | Cold/warm preparation, retained/rebuild sessions, cache pressure, fresh processes, bounded streaming, hard memory/deadline limits and cleanup have been exercised. Concurrency, soak and independent consumer traces are production-readiness questions; they are premature without a candidate speedup or real consumer. L08 becomes valuable when a genuine ordered request trace exists. |
| SymPy and representation controls | Y01–Y08 | Y01's historical approximately 76× eight-variable observation was recovered and correctly classified as unlike-task timing. Y08's contribution-ladder principle was implemented in the matched biology ingress experiment. Y02–Y05 remain a worthwhile **separate local claim-cleanup study**: fully consumed truth tables, `lambdify` evaluation, SAT/equivalence and separately scored simplification. Y06 is worthwhile only if expression quality is a product objective; Y07 should wait for a stable attributable release. |

## What to do next

The only generally worthwhile next benchmark is the bounded task-matched SymPy study Y02–Y05. It resolves a visible historical claim with modest local cost and has a clear matched-output contract. It should be a new task because it has different adapters, evidence and success criteria from the completed biology session work. It is optional claim cleanup; it is not required to support the current no-go conclusion.

Return to this biology task only after one of these triggers:

1. a new CM representation or preprocessing mechanism produces a different normalized plan from the raw path under a matched algorithm contract;
2. a real repeated-query consumer supplies an ordered trace and invalidation rules;
3. an explicit request calls for the already frozen 396-session local replication despite the absence of a development signal; or
4. open-input biology becomes a target and original-source annotations are needed to classify the 190 open models without guessing.

Do not spend cloud budget on the 2,400-case catalog, run all 80 families for completeness, or promote comparator-only d4/Ganak and AEON/oracle results into CM claims. Hardware, feature-model, policy, weighted-inference and reliability work should start from a specific caller and output contract, not from the existence of a catalog entry.

## Custody

The detailed evidence remains in the September 14 attribution audit and this September 15 session audit. `AUDIT_MANIFEST.json` binds this disposition with the pilot plan, original ledger, reporting addendum, analysis, source snapshots, test results and handoff. No paid compute, publication, upload or push was performed for this continuation.
