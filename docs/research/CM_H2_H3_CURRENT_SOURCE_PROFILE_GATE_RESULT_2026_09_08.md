# H2/H3 current-source profile-first gate result

Date: 2026-09-08  
Scope: exact, non-neural CM construction and dense materialization  
Decision: **no-go; close H2 and H3 as still deferred**

## Result

Retry 002 completed all 237 frozen rows from the already admitted complete-relation,
repeated-restriction, related-multi-root, and smaller-query workloads. Every row matched
the independent stored oracle, preserved its declared output order and canonical
SHA-256, retained seven uninstrumented timing repetitions, and completed separate
profile and retained/peak-memory passes. Independent replay found zero source-closure,
oracle, exactness, ordering/hash, memory-accounting, or summary mismatches.

No preregistered H2 or H3 component passed the materiality gate. The largest H2
component was canonical key creation/order preparation at 7.878% aggregate exclusive
self time (7.965% median cell share), below the 15% aggregate and 10% median floors and
material in only one third of applicable cells. Interning was 3.762% aggregate and
hashing 0.146%. The three conservative H2 buckets together accounted for 11.786%, still
below the individual-component continuation threshold. Serialization was separately
attributed at 10.327% in the H2 cold scope; it was not an H2 key component and would in
any case miss the same 15% aggregate floor.

The largest H3 component was dense lifting/alignment at 3.886% aggregate exclusive
self time (3.970% median). Conversion was 3.716%, temporary copies 3.666%, and generic
allocation 0.135%. Together those conservative H3 buckets accounted for 11.402%, but
no individual component approached the frozen 15% threshold or the required 50%
prevalence at a 10% cell share.

Therefore the protocol prohibits a representation candidate. No production file,
default, routing rule, serialized identity, or public claim was changed. No RunPod
authorization request is prepared because the first local continuation condition did
not pass.

## Cold, reused, and memory observations

These are descriptive medians over case medians, not new routing thresholds:

| Workload / current operation | Cold median | Reused median | Median sampled RSS peak / retained | Median traced peak / retained |
|---|---:|---:|---:|---:|
| complete relation, dense full reinflation | 1.7165 ms | 0.4961 ms | cold 24,576 / 0 B; reused 20,480 / 0 B | cold 64,922 / 54,175 B; reused 42,952 / 35,141 B |
| repeated restriction, CM IR bigint q1 | 2.0439 ms | 0.0947 ms | both 20,480 / 0 B | cold 52,362 / 39,950 B; reused 20,250 / 16,191 B |
| repeated restriction, CM IR bigint q64 | 11.7094 ms | 4.1162 ms | cold 210,944 / 210,944 B; reused 24,576 / 6,144 B | cold 528,229 / 463,732 B; reused 388,564 / 327,400 B |
| related roots, sharing union q64 | 21.1292 ms | 13.1106 ms | cold 919,552 / 897,024 B; reused 659,456 / 647,168 B | cold 1,535,094 / 1,268,818 B; reused 1,243,001 / 1,041,108 B |
| related roots, separate roots q64 | 28.8459 ms | 17.6928 ms | cold 815,104 / 796,672 B; reused 616,448 / 591,872 B | cold 1,549,190 / 1,280,716 B; reused 1,252,233 / 1,050,210 B |

RSS is current working set sampled every 1 ms between a post-GC baseline and artifact
retention/release boundaries; it is not a process-lifetime high-water mark. Signed
retained deltas remain in raw evidence. `tracemalloc` uses the same boundaries and is
reported separately because it covers Python-tracked allocation rather than all native
NumPy memory. Smaller-query fresh/resident and structural-reload rows are also retained
in the raw file; they are exact task controls and are outside the H2/H3 component scope.

## Attempt 001 and retry boundary

Attempt 001 retained 237 exact rows but failed closed because ctypes truncated the
64-bit Windows current-process pseudo-handle, so sampled RSS was unavailable. Its
summary remains evidence of an invalid memory gate and is not used for the decision.
Retry 002 set the Windows API return/argument types and strengthened validation to
require RSS availability. It did not change a workload, repetition, timing boundary,
threshold, or continuation rule. Retry 002's freeze was sealed before rerunning at
`05fcfa622da6d3a6812687ad70829a5d8d30ff672ed68f7c09a007f7346078e3`.

## Verification

- Retry 002 rows: 237/237 complete; 30 complete-relation, 120 restriction, 48
  multi-root, and 39 smaller-query rows.
- Independent replay: status `verified_no_go_close_h2_h3_still_deferred`; all mismatch
  counts zero; verification SHA-256
  `db677332f0eae0baf910f5a448a232ef08ef1a97342f5ff937b4f789a149f134`.
- New exhaustive and metamorphic tests: all Boolean functions through three variables,
  identity-shared versus tree-expanded expressions, commutative ordering, structural
  signatures, and exact dense output passed.
- Focused new/existing architecture suite: 132 passed, 1 optional skip, 1 known
  stale-freeze replay test deselected. The undelected run was 132 passed, 1 skipped,
  1 failure; an untouched current-main worktree has 20 source-hash differences from
  that 2026-09-03 freeze, so this is pre-existing rather than caused by this phase.
- Maintained `scripts/cm_research_check.py`: passed 249 current tests and 121 immutable
  snapshot tests.

Evidence is under
`docs/research/verification/cm-h2-h3-profile-gate-retry-002-2026-09-08/`:
`FREEZE.json`, `RAW.jsonl`, `SUMMARY.json`, and `INDEPENDENT_VERIFICATION.json`.
Attempt 001 is retained separately under
`docs/research/verification/cm-h2-h3-profile-gate-2026-09-08/`.

## Disposition

H2 compact canonical CM keys and H3 dense CM layout/copy fusion remain deferred. The
current compact builder-local interning keys and dense materialization behavior remain
unchanged. H9 remains deferred under its binding corpus result: no repository
substitution, Yosys execution, incremental-hardware machinery, or cloud request was
performed. A later H2/H3 phase requires a newly preregistered task whose admitted
profile independently activates one of these costs; it cannot reinterpret this stopped
panel after the fact.

