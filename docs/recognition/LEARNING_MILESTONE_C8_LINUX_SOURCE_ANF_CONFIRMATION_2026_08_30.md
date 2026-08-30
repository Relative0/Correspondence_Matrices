# CRSE Learning Milestone C8: Linux source-ANF confirmation

Date: 2026-08-30  
Status: **complete and independently verified**  
Production promotion: **no**

## Scope

C8 is the second-machine follow-up to C7. It ran the unchanged 40-case sealed
Yosys dataset on a Secure Runpod Linux CPU using the frozen 14-file package. No
model was trained, no case was relabeled, and the remote machine fetched no
dataset.

The six exact methods were set source ANF, uncached packed source ANF, cold
cached packed source ANF, warm-stream cached packed source ANF, direct
big-integer truth-vector ANF, and NumPy truth-vector ANF. Each method/case pair
was timed nine times with deterministic rotated method order and one CPU thread.

## Verified lifecycle

The corrected single-port run uploaded all 14 files and returned 2,160 raw
measurements and 240 per-case summaries. The pod used two vCPU, 4 GB RAM, the
pinned Python 3.13.15 image, 12 GB ephemeral disk, no persistent volumes, and a
$0.06/hour rate. It was deleted 35.194 seconds after creation. Final v1 and v2
pod details return HTTP 404 and both account inventories are empty. Estimated
compute cost was $0.000587.

## Linux results

| Method | Split | Median total | p95 total | Maximum |
| --- | --- | ---: | ---: | ---: |
| set source ANF | sealed A | 0.051 ms | 0.425 ms | 0.568 ms |
| set source ANF | sealed B | 0.053 ms | 0.940 ms | 1.790 ms |
| packed source ANF | sealed A | 0.098 ms | 0.488 ms | 0.571 ms |
| packed source ANF | sealed B | 0.123 ms | 1.051 ms | 1.922 ms |
| cached packed, cold | sealed A | 0.102 ms | 0.499 ms | 0.572 ms |
| cached packed, cold | sealed B | 0.131 ms | 1.054 ms | 1.907 ms |
| cached packed, warm | sealed A | 0.096 ms | 0.498 ms | 0.573 ms |
| cached packed, warm | sealed B | 0.119 ms | 1.057 ms | 1.928 ms |
| direct bitset truth ANF | sealed A | 0.092 ms | 0.919 ms | 1.035 ms |
| direct bitset truth ANF | sealed B | 0.113 ms | 2.212 ms | 4.572 ms |
| NumPy truth ANF | sealed A | 0.201 ms | 1.058 ms | 1.146 ms |
| NumPy truth ANF | sealed B | 0.265 ms | 2.403 ms | 4.750 ms |

All six methods achieved 1.000 classification and canonical-partition accuracy.
Semantic mismatches were zero.

## Cross-machine interpretation

Three results reproduced clearly across Windows and Linux:

1. **Exactness transferred.** Every representation returned the same canonical
   partition on all 40 externally derived cases.
2. **Packed ANF beat the retained NumPy path.** Warm packed ANF was 2.099x and
   2.226x faster at median on Linux, with 2.125x and 2.274x p95 speedups. The
   local C7 medians were 2.130x and 2.157x.
3. **Set ANF remained fastest on the sparse external family.** It was 1.875x and
   2.245x faster at median than warm packed ANF on Linux. The same ranking held
   locally.

The stronger direct-bitset comparison was machine sensitive at the median.
Locally, warm packed ANF was 1.124x and 1.096x faster. On Linux, direct bitset
was about 1.046x and 1.052x faster. Packed ANF still won the Linux p95 by 1.846x
and 2.093x, so its robust advantage is tail control rather than universal median
latency.

Warm caching improved Linux median latency over a cold per-case cache by 1.066x
and 1.103x. Its sealed-B p95 was 0.3% slower, so the frozen combined
median-and-p95 cache criterion correctly remained false. Cross-case caching is
not yet a robust promotion condition for this small suite.

## Verification

The lifecycle verifier checked the pod resources, frozen hashes, retrieved
artifact hashes, 2,160-row identity, dependency versions, cleanup watchdog, and
final provider inventories.

A separate semantic verifier then replayed all 2,160 method/case/repetition
results locally, including cold and warm cache state, recomputed all 240 per-case
medians, summaries, and criteria, and matched the retrieved artifact exactly.

Both verifiers passed. Semantic mismatches: **zero**.

## Decision and next boundary

C8 confirms an exact representation portfolio rather than a universal packed
replacement. Set ANF is the correct current default for sparse low-interaction
source DAGs. Packed ANF remains valuable when explicit set-product growth causes
tails, while direct bitset ANF is a competitive fallback.

The next strongest implementation is a cheap analytic dispatcher using only
pre-execution source-DAG counters. Its thresholds must be frozen on development
data that predates C7/C8; neither sealed Yosys split nor these Linux timings may
be used for tuning. Evaluation should report selection regret against all three
exact paths and preserve truth-vector confirmation.

All 18 research tracks and all eight application areas remain preserved.

## Evidence

- Remote study: `docs/recognition/c7_linux_confirmation/runpod-c7-linux-single-port-execute-001/evidence/run-output/yosys-c7-linux-confirmation`
- Lifecycle verification: `docs/recognition/c7_linux_confirmation/RUNPOD_C7_LINUX_SINGLE_PORT_FINAL_VERIFICATION_20260830-045932-420152.json`
- Semantic replay: `docs/recognition/verification/yosys-source-anf-linux-confirmation-20260830-001.json`
- Local C7 run: `docs/recognition/runs/yosys-source-anf-confirmation-20260830-002`
- Corrected authorization: `docs/recognition/c7_linux_confirmation/RUNPOD_C7_LINUX_SINGLE_PORT_AUTHORIZED_2026_08_30.json`
- Machine summary: `docs/recognition/learning_milestone_c8_linux_source_anf_results.json`
