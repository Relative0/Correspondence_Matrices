# Independent active CM workflow profile result

Date: 2026-09-08  
Decision: `no_go_no_material_component`

## Disposition

| Question | Result |
|---|---|
| Workload independence | Established for exactly one active workflow |
| Measurement validity | Valid on retry 002; complete schedules and independent replay passed |
| Component materiality | No H2 or H3 component passed the frozen gate |
| Candidate eligibility | No |
| Candidate result | Not applicable; no candidate was frozen, implemented, or timed |
| Production status | Unchanged; research-only instrumentation and records |
| RunPod request | Not permitted and not prepared |

The local phase closes without an implementation candidate. The result does not reopen
H2, H3, H6 routing, or H9, and it does not support a runtime selector, native activation,
production-default change, or public performance claim.

## Source checkpoint and isolation

A fresh fetch on 2026-09-08 found that
`origin/codex/cm-h2-h3-h6-gates-20260908` was not merged into `origin/main`.
The experiment therefore used a detached fresh worktree at the exact reviewed commit:

- selected ref: `refs/remotes/origin/codex/cm-h2-h3-h6-gates-20260908`;
- selected commit: `43fffcfaa53aab0d2ce95ca902c11e8f23484dfe`;
- fetched `origin/main`: `c9af2a3c80388e467944bd706036996db9eed9b8`;
- worktree: `C:\Users\brian\Documents\CM_Computation\tmp\cm-independent-active-20260908`.

The original checkout was already dirty. `CHECKPOINT.json` records 120 tracked and
untracked entries by path only. Their contents were not used or changed, and no secret,
credential store, private database, or unrelated user-content file was read.

## Discovery and independent admission

Exactly one workflow passed the predeclared provenance/task rule: the maintained
deep-series chapter compiler's `truth_layout_payload` subworkflow. Its purpose is to
produce exact expression/matrix data embedded in executable educational-video render
contracts, a concrete caller-visible artifact. It was not created for CM profiling:

- the validated CM video factory first appears in commit
  `8facd287c99dc737d86831edbd0ebbd7ec486694`, authored by `btheorystartups` on
  2026-08-31 with subject `Add validated CM video factory and proof artifacts`;
- the deep-series compiler source appears in commit
  `d2c82000674524d99ed95dc4c547716b01acfd33`, authored by `btheorystartups` on
  2026-09-01 with subject
  `Record CRSE learning milestones and research media evidence`;
- reviewed source contains 203 tracked chapter contracts and 150 qualifying real call
  occurrences: 75 `expression_matrix` and 75 `representation_compare` occurrences;
- 140 occurrences use the main four-live-variable expression and 10 retain the ambient
  `D` low-sharing/control condition;
- original-checkout path metadata contained 95 current deep-series/video-factory entries,
  supporting ongoing local use without reading their unrelated contents.

The exact contract is a fixed `A,B,C,D` ambient order, `AB=00,01,10,11` row order,
`CD=00,01,10,11` column order, and a canonical hashed render payload. Selection was
made from metadata and source contracts before candidate timings or memory were opened.
It was not based on compact keys, dense layout, estimator behavior, native execution,
incremental compilation, or an expected CM advantage.

The remote worker and CRSE computation experiment were excluded as benchmark-purpose
workloads. The learning handoff was excluded because it does not execute CM. Hardware
and configuration revisions were excluded by the binding H9 disposition. No public
repository, generated benchmark, replacement corpus, or post-hoc workload was admitted.

## Frozen experiment

The sole arm was unchanged current source: DAG-v2 deserialization, canonical CM-IR
construction with persistent/reuse caches disabled, fixed layout, dense materialization,
row-major string conversion, delivery of the caller-retained payload, and canonical
serialization. The cold lifecycle included the whole path. The reused lifecycle retained
only the parsed expression, compiled CM-IR, and layout; it rebuilt and serialized every
output. Output caching was forbidden.

The freeze required two warmups and seven uninstrumented repetitions for every
occurrence/lifecycle, plus separate one-shot `cProfile` attribution. H2 was eligible only
on cold calls; H3 covered cold and reused dense calls. Fresh-process memory used the H6
controller solely as infrastructure, three new child processes for each distinct
cohort/primitive/lifecycle cell. It retained absolute endpoints, signed prepared,
retained, and post-release deltas, nonnegative peaks, child PIDs, handshakes, and sampling
counts. No H6 case or estimator was used to select or interpret the workload.

Correctness required the independent scalar-Boolean render-contract oracle, stable
ordering and hashes, all Boolean functions through three variables, all 16 ambient
assignments of both admitted functions, identity-shared versus tree-expanded
metamorphics, commutative ordering, low-sharing controls, cold/reused agreement, and an
independent standard-library replay.

The frozen component gate required all of: at least six applicable cells, at least 15%
aggregate exclusive share, at least 10% median cell share, at least 50 microseconds
median exclusive time, at least 50% prevalence at 10%, at least 10% aggregate share in
both the main and ambient-control cohorts, and the additional peak-excess condition for
allocation/copy components.

## Measurement validity

Attempt 001 is retained as a failure: all 300 profiling rows completed, but an adapter
used `_LineReader.next` against the H6 infrastructure's `_LineReader.get` API and stopped
before the first memory row. Its profile file, zero-byte memory file, freeze, and failure
record remain in evidence. No memory result or materiality summary existed when the
fault was diagnosed.

Retry 002 changed only that instrumentation adapter and its handshake/command decoding,
then sealed a new source closure before rerunning both schedules. It is valid:

- 300/300 profile rows and 24/24 fresh-process memory rows completed;
- seven raw timing repetitions and three distinct child PIDs per memory cell completed;
- all oracle, order, output-hash, structure-hash, schedule, handshake, endpoint, and
  source-closure checks passed;
- no profile, memory, PID, refusal, or zero-duration failure was dropped;
- the independent standard-library verifier replayed all 150 oracle occurrences, all
  300 profile rows, all 24 memory rows, and the complete materiality decision with zero
  mismatches.

Descriptive caller-visible medians were 426,700 ns cold and 113,250 ns reused. The
fresh-process median working-set and private peak/retained deltas were 0 bytes for both
lifecycles, as expected for this task below OS page-resolution. `tracemalloc` still
recorded the signed endpoints: cold median peak delta 276,359.5 bytes and retained delta
272,544 bytes; reused median peak delta 187,743.5 bytes and retained delta 184,204 bytes.
The zero OS deltas are retained data, not filtered observations.

## Materiality result

| Component | Cohort | Aggregate | Median cell | Median exclusive | Prevalence at 10% | Pass |
|---|---:|---:|---:|---:|---:|---:|
| key creation | H2 | 5.80% | 5.62% | 72.60 us | 1.33% | No |
| hashing | H2 | 1.34% | 1.28% | 16.60 us | 0.00% | No |
| interning | H2 | 3.45% | 3.28% | 42.35 us | 0.67% | No |
| dense lifting | H3 | 3.61% | 3.96% | 36.60 us | 0.00% | No |
| allocation | H3 | 0.34% | 0.31% | 3.40 us | 0.00% | No |
| conversion | H3 | 4.65% | 5.13% | 47.70 us | 0.00% | No |
| temporary copies | H3 | 2.11% | 2.20% | 22.20 us | 0.00% | No |

The largest aggregate component, key creation, reached only 5.80%, and only two of 150
applicable cells reached the 10% per-cell floor. No component approached the required
15% aggregate plus 50% prevalence combination; none passed both cohort floors. Therefore
the materiality result is **no passing component**.

## Candidate and production disposition

The continuation rule permits a candidate only when exactly one component passes. Zero
components passed, so candidate eligibility is false. No candidate was frozen,
implemented, benchmarked, or compared. Production code, caches, defaults, routing,
website claims, and native behavior remain unchanged. No runtime selector was fitted or
enabled. H9 remains deferred; no repository was added, Yosys was not run, and no
incremental-hardware work or BlackParrot reinterpretation occurred.

RunPod authorization is not permitted because the local materiality and candidate gates
did not all pass. No request was prepared and no RunPod operation was performed.

## Verification

- New focused instrumentation tests: `3 passed`.
- Broader focused CM architecture set with workspace-local pytest temp: `32 passed,
  1 skipped, 1 failed`.
- The one failure is pre-existing and unrelated:
  `test_candidate_freeze_is_deterministic_and_blind_to_memory_values` compares stored
  H6 Git-blob hashes (LF bytes) with a Windows checkout materialized as CRLF. The four
  stored hashes exactly match their Git blobs but not their CRLF worktree bytes.
- `scripts/cm_research_check.py`: passed, including 249 current tests and 121 immutable
  snapshot tests; no cloud workload and no performance workload were started by it.
- New-file whitespace check: passed; final status and evidence hashes are recorded with
  this result.

The machine-readable controlling records are under
`docs/research/verification/cm-independent-active-workflow-2026-09-08/`. Retry 002 is
bound by freeze SHA-256
`d6ca7259b3277decde4058c06fd795595c1af01d08479c7ec67cd62b3826838a`, raw profile
SHA-256 `9293a1406f0fe681699260976cb9618ca68fee3347dd37ef5fe1f885e3be29d7`, raw memory
SHA-256 `c6c6251be14673ee42b463d5100fae8b1b7b8e289065ef4e74db0ea8d1ba4ba8`, and canonical
summary SHA-256 `609ae529aced346cfd1366aff515c26f0586c092e6f1670ec5b9378b98c00d97`.
