# CM implementation and validation continuation

This plan executes the remaining feasible local work from the September 11
performance investigation. Brian's instruction to continue implementation and
testing is standing authorization for the local phases below, including local
native builds, fresh-process benchmarks, new evidence directories, corrective
edits and routine choices. Each phase progresses automatically when its
prerequisites and correctness checks pass; it does not require another approval
of a routine plan or implementation.

The standing authorization does not include credentials, paid infrastructure,
cloud resources, publishing, deployment, commits/pushes, destructive cleanup or
changes to unrelated work. A task needing any of those is prepared to a concrete
reviewable boundary and recorded while independent local work continues. No
scientific result is promoted by changing a failed gate after measurement.

**Execution order and completion criteria**

| Phase | Implementation and experiment | Continue / stop decision |
| --- | --- | --- |
| P0 — Reproducible continuation | Snapshot current relevant source and the dirty-file inventory; keep the prior audit immutable. Write source-bound protocols and raw results in a separate continuation directory. | Every reported result has exact inputs, source identity, timing scope, uncertainty, correctness and limits. |
| P1 — Bounded positional mask cache | Add an opt-in cache keyed by width, sharing immutable integer columns across named environments. Enforce an explicit retained-entry byte budget, bounded build size, eviction, oversized-entry nonadmission, concurrency and release. Compare existing named LRU, no cache and positional caching. | Exact ordering and cache lifecycle first. Measure hits, renamed bases, phase changes, misses and pressure. Retained-entry bounds must be mechanical; external references and allocator RSS remain separate. Keep existing global defaults. |
| P2 — Exact independent-block counts | Compile a conjunction into groups joined by overlapping support. Count disjoint components, apply the unused-live-variable multiplicity, and support repeated partial assignments. Overlapping blocks merge; inseparable formulas use the exact single-component path or an explicit width refusal. | Exhaustive small oracles, randomized contexts, constants, unused/reordered axes and adversarial overlaps. Measure whole preparation/query sessions against direct packed, structural CSE-flat and available symbolic controls. This returns counts/existence, not a complete vector. |
| P3 — Bounded streaming output | Add a prepared, opt-in packed iterator over aligned assignment ranges using the existing exact flat program. Generate high-axis constants and low-axis packed columns per chunk; preserve output order and final bit count. | Concatenation must equal complete packed output on bounded cases. Enforce total-output and chunk guards before execution. Compare time, time to first chunk, peak/retained allocation and consumer-retention limits; report dispatch regressions. No automatic GPU/process routing. |
| P4 — Existing native batch successor | Inspect and build the separate batch DLL locally; run its exactness tests. Create a new prospective source-bound freeze and independent oracles. Record the standing local authorization against the resulting hashes; run the existing 2,592-cell, 12-block scalar/batch campaign and independent verifier unchanged. | Preserve all outcomes. Use its existing q8/q32/q96 gates. A local pass supports only local evidence; its separate-physical-host requirement remains unmet until an authorized host exists. No native default switch or selector training. |
| P5 — Lifecycle and application admission | Use the new cache/count/stream facilities in explicit development sessions. Compare one-shot and repeated requests; separate serialization, preparation, delivery and cleanup. Inspect available real workload manifests for applicable admitted uses. | Synthetic results justify engineering prototypes, not application adoption. Do not relabel old development corpora as fresh confirmation. Real trace absence becomes an explicit remaining prerequisite. |
| P6 — Wider algorithms and execution | Screen the remaining GF(2)/ANF, persistent artifacts, incremental edits, symbolic hierarchy, compiler and parallel hardware ideas against current evidence and P1–P5 measurements. Implement only a new method with an activated task and affordable local exact control. | Preserve H2/H3/H6/H9 no-go results. Do not repeat failed generic rewrites, fit another router to consumed data, install speculative stacks or confuse compact output with explicit output. Record a concrete experiment and missing prerequisite for each deferred item. |
| P7 — Integration and review | Run relevant repository tests, new exactness/lifecycle checks and source/evidence replay. Review only owned changes and update this plan with outcomes, commands and next actionable boundaries. | No hidden skips, unexplained failures or speedup claims from kernel-only timings. Existing unrelated changes and earlier frozen files retain their original bytes. |

**Experiment rules.** New local cache/count/stream panels use fixed inputs and
seeds, paired alternating arm order and separate development and confirmation
cases. Candidate and baseline pay compilation, cache lookup, binding, conversion
and required output costs. Warm execution is reported separately. A correctness
failure stops that candidate until repaired; all failed attempts are retained.
At least nine timing pairs are used for small local panels, with per-case tails
and bootstrap intervals. Allocation tracing is outside timing. Native timing
uses the already specified stricter prospective schedule and gates.

Production-shared defaults are not changed merely because a synthetic candidate
wins. New APIs have explicit caller limits and exact refusal/fallback behavior.
An optimization that only helps one lifecycle can remain an explicit option.
No claim is made that all hypotheses will succeed or that missing real traces
can be replaced with fabricated application evidence.

**Current status.** P0–P7 have reached their feasible local completion boundaries.
P1–P3 are implemented, with 1,224 verified frozen timing rows / 15,480 cold
outputs, 136 separate memory rows, 60 fresh-child diagnostics, and an additional
216-cell reused-data streaming diagnostic. P4 verified all 2,592 native cells
but returned no-go: q96 speedup was 1.078x, below the existing 1.10x gate. It does
not proceed to a second host. P5's historical applicability replay passed 144
contexts; P6's remaining admission prerequisites are documented. P7 passed 249
tests and four subtests. The original packed-mask audit is immutable, with all
54 artifact hashes matching. See the
[continuation report](../audits/2026-09-11-cm-continuation/REPORT.md) for results,
regressions, verification receipts and the remaining application boundaries.
