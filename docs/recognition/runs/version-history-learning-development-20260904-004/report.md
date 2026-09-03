# Source-blind version-history learning protocol

Date: 2026-09-04  
Status: **implemented and verified mechanically; training remains disabled**

## Outcome

The learning gate consumes only the independently verified post-benchmark
artifact. It hash-checks that artifact, its independent verification, every
bound evidence file, and every bound analysis source. It does not invoke a
benchmark runner, exact backend, cloud job, selector fit, or neural trainer.

It also consumes the Benchmark task's completed 27,648-row query-ladder
analysis through its independent verifier and bound file hashes. At q64 its
best fixed arm is `cse_flat_bigint` and its case-median
geometric-mean slowdown to the per-case oracle is `1.107862216x`.
That is not the required sum-based, fully charged headroom metric; the artifact
explicitly forbids selector/neural claims and still requires cross-machine
replication. The learning gate therefore records it but cannot promote it.

The verified resident version-history surface retains `1.137580420x` gross headroom across only
3 already exposed source groups. The maximum
total overhead preserving 1.10x is only `3560.5 ns/case`.

## Source-blind protocol

Only ten pre-timing structural counts enter the model feature vector. Case and
source identity, provenance hashes, split names, labels, arm order, blocks, and
all timings are forbidden model fields. Opaque source-group hashes are visible
only to the split auditor. Deterministic salted group assignment produces three
development-only buckets; it does not manufacture a prospective split from
already exposed cases.

Cross-split source-group intersections are `0`. Minimum split sizes pass:
`False`. Current labels predate this protocol,
so current control accuracy is retrospective and receives no training credit.

## Ultra-cheap analytical controls

Local `Windows-10-10.0.19045-SP0` development timing used
`time.perf_counter_ns`; it is diagnostic, not cross-host authorization evidence.
No exact backend was executed by the timing harness.

| Feature + control | Median ns/case | p95 ns/case | p95 within budget |
|---|---:|---:|---|
| `bounded_cnf_then_sat` | 2686.7 | 2894.2 | True |
| `fixed_cnf` | 2892.6 | 3430.6 | True |
| `fixed_sat` | 2657.4 | 2786.1 | True |

Even if the retrospective bounded control is credited as an oracle and model
inference, exact verification, and fallback are assumed free, that is only an
optimistic diagnostic. The fully charged speedup is deliberately `null` because
those costs are unmeasured; the gate fails closed instead of substituting zeros.

## C5 certificate / early termination

A ranked partition or exactly reconstructed candidate is not a global-best
certificate. Eligibility requires an independently checked sound bound covering
every unexplored partition, exact candidate reconstruction, unchanged exact
fallback, no completion search, zero adversarial/metamorphic failures, measured
certificate cost, and at least `25%` measured global
completion work avoided after charging that cost. C5 supplies no such certificate.

## Decision

Training, selector fitting, prospective consumption, and routing advice remain
disabled. Every request abstains to the unchanged exact path. A later Benchmark
task result can enter only as an independently verified artifact; this learning
implementation will not reproduce its measurements.
