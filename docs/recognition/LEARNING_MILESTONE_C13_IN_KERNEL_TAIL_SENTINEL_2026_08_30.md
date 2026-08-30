# Learning milestone C13: in-kernel tail sentinel

Date: 2026-08-30

## Purpose

C13 moved the frozen 4,096 product-pair tail sentinel into the exact set-ANF
evaluation loop. When the budget is crossed, the already-computed polynomial
prefix is converted to packed ANF and execution continues without evaluating the
DAG prefix again. Ordinary set ANF remains a separate function, so disabling
advice does not add a per-product branch or diagnostic counter.

This milestone changes representation only. It does not learn an approximate
answer and it does not relax the exact CM/decomposition acceptance boundary.

## Implementation

- `source_anf_monomials` remains the independent no-sentinel set kernel.
- `source_anf_prefix_with_sentinel` exposes the exact reusable prefix.
- `adaptive_exact_partition_fast` uses a measurement-free sentinel loop and
  packed continuation.
- Detailed product counters exist only in the explicitly measured arm.
- The frozen product-pair budget is 4,096.
- Advice-off calls the original set kernel directly.

## Test and measurement contract

- Generated-expression equivalence through four variables.
- Budget boundaries 0, 1, 4,095, 4,096, and the maximum admitted budget.
- Exact replay across C6, C7, C11, and C12.
- Fifteen balanced repetitions, one thread, 1,024-entry cache, 120-second wall
  limit.
- Independent Boolean truth evaluation and canonical partition verification.
- Raw per-case timings and rejected/unswitched cases retained.

The official run used 188 frozen cases and produced 11,280 raw timing rows and
752 method/case rows. Independent replay reproduced every row and found zero
semantic mismatches.

## Results

| Split | Fast sentinel / ordinary set speedup | p95 speedup | Selected path |
| --- | ---: | ---: | --- |
| C6 confirmatory development | 19.309x | 28.038x | 13 packed continuations, 23 set |
| C6 test development | 1.165x | 1.008x | 1 packed continuation, 31 set |
| C7 A / B | 0.834x / 0.902x | 0.771x / 1.003x | all set |
| C11 A / B | 0.911x / 0.927x | 0.875x / 0.808x | all set |
| C12 sealed A / B | 0.890x / 0.744x | 0.801x / 0.766x | all set |

The dense-tail target was exceeded: C6 p95 protection improved from C12's
15.58x to 28.04x under the solve-only timing contract. The sparse target failed.
On the two C12 splits the sentinel was 10.97% and 25.59% slower even though it
never converted. Advice-off was effectively neutral relative to the separately
timed ordinary set kernel, ranging from 1.002x to 1.019x across the eight splits.

The measured sentinel arm was slower than the fast sentinel on every split.
That is expected and confirms that detailed counters are not suitable for the
production path.

## Decision

C13 is an exact, useful tail-protection primitive, but it failed the sparse
no-material-regret gate. Do not enable it universally. Preserve the negative
result and use the independent no-sentinel function for throughput-oriented
workloads. No second-machine run was started because the required Windows-first
local engineering gate failed.

## Evidence

- `docs/recognition/runs/in-kernel-tail-sentinel-20260830-001` — retained
  incomplete run caused by an artifact-hashing bug.
- `docs/recognition/runs/in-kernel-tail-sentinel-20260830-002` — complete
  diagnostic predecessor.
- `docs/recognition/runs/in-kernel-tail-sentinel-20260830-003` — official fast
  sentinel run.
- `docs/recognition/verification/in-kernel-tail-sentinel-20260830-003.json` —
  independent replay and artifact verification.

