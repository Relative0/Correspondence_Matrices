# Remaining algorithms and execution work

This ledger carries the earlier research priorities forward after implementing
the bounded mask cache, independent count components and packed output iterator.
It distinguishes an implemented facility from an admitted application. Local
implementation and testing continue under the current standing instruction;
an absent workload or host is a prerequisite, not an invitation to repeat a
failed experiment with different labels.

| Opportunity | Current local disposition | Concrete next experiment and prerequisite |
| --- | --- | --- |
| Packed truth-mask construction | Integrated; earlier frozen audit verifies exactness and large cold-build savings. | Use the improved shared mask builder in every incumbent. Do not use the old NumPy setup to inflate successor comparisons. |
| Cache ownership and naming | Implemented as `PackedMaskCache`; explicit limits and trace panels. | Admit a real session with changing names, widths and request lifetimes. Compare total request cost and retained references against the existing named LRU. Same-basis hits may favor the existing LRU. |
| Decomposable counts / existence | Implemented as `IndependentCountPlan` for raw expressions and CM nodes. | A real consumer must request counts or existence, and its components must remain narrow. The historical k8 feature-model replay tests applicability but does not establish benefit on full models. Compare against a native symbolic counter when available. |
| Streaming full output | Implemented as `PackedStreamPlan`, with a tile sweep and complete CSE control. | A consumer must accept incremental ordered bytes. Measure a real sink's I/O, buffering and cancellation; choose a chunk budget using independent development data. Retaining every chunk loses the output-memory benefit. |
| Native FFI batching | Built locally; all 2,592 prospective cells verified after the JSON round-trip repair. Q96 speedup was 1.078x, below the frozen 1.10x gate: no-go for this workload. | Do not advance this candidate to a second host or change the gate. A new mechanism would need a distinct prospective workload. Keep the experimental workspace-sharing adapter out of a concurrent service until its ownership and resource limits are explicitly covered. |
| Prepared ingress / persistent artifacts | Existing implementations already preserve structural artifacts and exact fresh reloads. New query plans reuse compilation inside resident sessions; fresh-child diagnostics charge process lifetime separately. | A real reload-heavy task and useful artifact size are required for a new performance gate. The [fresh-process persistence result](FRESH-PROCESS-PERSISTENCE-PROGRESS-2026-08-29.md) is functional evidence, not a speed ranking. Extend its checked structural formats; do not introduce executable deserialization. |
| Exact GF(2) / ANF | Keep the existing packed rank implementation and its rank-only gain. Complete ANF screening previously failed to improve. | Freeze an explicitly algebraic rank or sparse-polynomial query with conversion and construction charged. Demonstrate end-to-end headroom before integrating M4RI or a new native kernel. General Boolean matrices are not numerical low-rank objects. |
| Incremental edits | Current persistent CM cache remains incumbent. Digest-radix prototype stays unpromoted. | A new independently selected revision trace must pass activation. The [local gate](CM_INCREMENTAL_REVISION_LOCAL_GATE_RESULT_2026_09_04.md) had only 3/42 changed confirmation cases, higher retained memory and slower CSE-relative totals. Replay unchanged-result propagation only after workload admission. |
| Hardware changed cones | Both frozen corpus attempts remain stopped. | A distinct preregistered history-selection rule must supply enough active transitions on every confirmation repository before Yosys correctness or timing. Preserve the failures in the [feasibility](CM_HARDWARE_REVISION_FEASIBILITY_RESULT_2026_09_04.md) and [behavior-change](CM_HARDWARE_BEHAVIOR_CHANGE_CORPUS_RESULT_2026_09_04.md) audits. |
| Compact keys / dense copies / rewrite saturation | H2/H3 generic rewrites remain inactive; no e-graph replacement. | A current trace must make key preparation, dense alignment or repeated rewriting materially expensive. Use the existing [profile gate](CM_H2_H3_CURRENT_SOURCE_PROFILE_GATE_RESULT_2026_09_08.md); do not infer the bottleneck from source complexity. |
| Representation estimator / router | H6 estimator and later selector results remain negative; no threshold tuning. | First demonstrate distinct backend headroom on independent tasks, then cheap observable features, held-out regret and tail behavior, and physical-host transfer. [H6](CM_H6_FRESH_PROCESS_MEMORY_AND_ESTIMATOR_RESULT_2026_09_08.md) did not meet the ordering prerequisite. |
| Hierarchical symbolic sharing / ZDDs | Research candidate with no admitted implementation task. | Freeze repeated hierarchical subfunctions or sparse set-family operations; measure compact compose/restrict/equivalence outputs and conversion costs. CFLOBDD and bounded-width decomposition bounds depend on ordering and structure; they do not predict general explicit-vector latency. |
| Threads / processes / GPU | Streaming establishes a single-process baseline; no new hardware routing. | A large admitted task must amortize startup, transfer and synchronization. Compare fused native work first, with aggregate memory and oversubscription controlled. GPU execution requires an available authorized device and a portable exact control. |

The first investigation's [full report](../audits/2026-09-11-cm-performance/REPORT.md)
contains the primary literature links and detailed historical measurements. This
continuation leaves those immutable results intact and reports new local evidence
in its own audit directory. Neither synthetic fixtures nor reused historical
examples are relabeled as a new real application or independent confirmation.
