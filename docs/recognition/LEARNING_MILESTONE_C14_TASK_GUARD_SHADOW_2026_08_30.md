# Learning milestone C14: task guard and exact shadow execution

Date: 2026-08-30

## Purpose

C13 showed that the same exact representation policy can be excellent for a
latency-tail objective and poor for sparse throughput. C14 therefore selects a
policy from declared task metadata before expression execution. It does not
inspect the formula to justify activation and it never changes the exact result.

The frozen task contract distinguishes throughput, latency-sensitive,
repeated-query, and memory-sensitive work. Unknown platforms and unsupported
tasks abstain to ordinary set ANF. Out-of-range advice is refused. A global
switch bypasses advice, and bounded shadow mode returns the production result
while timing and comparing the alternative exact arm.

## Frozen policy

| Task | Selected policy |
| --- | --- |
| Throughput | separate no-sentinel set ANF |
| Latency-sensitive | 4,096-pair in-kernel sentinel |
| Repeated query with at least two expected uses | 4,096-pair sentinel |
| Memory-sensitive | separate no-sentinel set ANF |

The policy was serialized before the frozen evaluation corpus was opened and is
bound to Windows, AMD64, CPython 3.13.5. A Linux identity, any other platform
identity, insufficient expected reuse, unsupported task, and out-of-range input
all take conservative paths in the unit contract.

## Test and measurement contract

- Frozen C6 confirmatory and C12 sealed A/B slices: 76 cases.
- Six modes: advice disabled, four declared tasks, and throughput with shadow.
- Nine balanced repetitions, one thread, 1,024-entry cache, 120-second wall
  limit.
- Policy cost charged once per compiled split/mode/variable-count workload.
- Production execution, shadow execution, and independent exact-check costs
  retained separately.
- Exact output and canonical partition checked independently for every row.
- Frozen artifact, source, policy, and input hashes verified after the run.

The run produced 4,104 raw timing samples and 456 method/case rows. Independent
verification reproduced every median and aggregate, verified five artifacts and
five measured source files, and found zero semantic or shadow mismatches.

## Results

| Split | Throughput vs advice-off | Latency sequence vs advice-off | Latency p95 vs advice-off |
| --- | ---: | ---: | ---: |
| C6 confirmatory development | 1.0068x | 18.918x | 27.876x |
| C12 sealed A | 0.9999x | 0.889x | 0.802x |
| C12 sealed B | 0.9729x | 0.739x | 0.738x |

The throughput task stayed inside the predefined 3% no-material-regret band on
all three splits. The latency task retained the dense-tail benefit, selecting 13
packed continuations and 23 set completions on C6. It remained slower on sparse
C12, as C13 predicted. Shadow execution matched the production partition on all
684 shadow timing samples while retaining its full cost rather than presenting
shadow work as free.

## Decision

The local C14 research gate passed: exactness, shadow equivalence, dense-tail
protection, and the throughput no-regret condition all held. This establishes a
controlled operational candidate, not a universal or production-enabled
dispatcher. Production promotion remains false because the policy is calibrated
to one Windows identity and the underlying sentinel's sparse profitability is
platform and workload sensitive.

The next implementation milestone is E1/R07: an equal-budget BDD order and
compilation study with task-specific build, query, and amortization objectives.

## Evidence

- `docs/recognition/runs/task-guard-shadow-20260830-001`
- `docs/recognition/verification/task-guard-shadow-20260830-001.json`

