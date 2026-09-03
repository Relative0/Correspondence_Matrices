# CM native exact-portfolio baseline closure

**Date:** 2026-09-03  
**Scope:** development-only, cache-isolated q64 replay on the already exposed C36 cohort  
**Decision:** fixed native optimization supported; prospective confirmation, routing, and neural training remain stopped

## Why this run was required

The September 2 native fused-slot experiment compared native execution only with
Python R2 and optimized projection. A separate task-identical engine run had found
`cse_bigint` fastest on all 18 cases, but its timing could not be combined with the
native run because complete-task cache isolation and scheduling differed.

This run closes that development baseline gap in one source-bound experiment. It
compares R2 per-query execution, CSE bigint/words, CM-IR bigint/words, optimized
`uint16` projection, and fused native slots.

Both bigint and word environment caches are cleared before every complete q64 task.
Reuse within each 64-query task remains part of the measured lifecycle. No prospective
case, training data, model, router, or production path was used.

## Verified result

Artifact:
`docs/recognition/runs/native-portfolio-development-20260903-001/`

| Method | Sum of 18 case medians |
|---|---:|
| **native fused slots** | **111.451 ms** |
| CSE bigint | 141.849 ms |
| `uint16` projection | 152.670 ms |
| CM-IR bigint | 157.753 ms |
| R2 per query | 163.927 ms |
| CSE words | 215.322 ms |
| CM-IR words | 235.134 ms |

Native is `1.272744728x` faster than the best non-native fixed method, CSE bigint.
It wins all 18 exposed cases. The best fixed total and the per-case oracle are both
111,451,100 ns, so selector headroom is exactly `1.000000000x`.

The experiment contains 1,764 balanced performance sessions, 126 separate memory
sessions, and 120,960 raw query deliveries. Independent replay found zero artifact,
source, interpreter, native-library, dataset, schedule, correctness, timing, identity,
summary, or decision mismatch.

- Results SHA-256:
  `b2f81e78a9285b9a4f4cbacb4928a03dd1b90cd6637f0663e1dd6e14081772f7`
- Manifest SHA-256:
  `89bca68671d343dee864d06297028e3a2c3d2b87186a29498f7071c813729d64`
- Native library SHA-256:
  `2d444c32d352284ab28474fef5554659f4f08225158d79feedc48633cf4875a0`
- Independent verification: `verified`

## Neural-readiness update

The separate reassessment artifact is:
`docs/recognition/runs/neural-native-portfolio-reassessment-development-20260903-001/`.

It replaces the prior cross-run label-closure uncertainty with one complete,
source-closed seven-arm development table. That makes the 18 native labels valid but
economically useless for training: every label is identical and gross oracle headroom
is zero. Charging only the historical feature allowance reduces the optimistic upper
bound to `0.980459619x`, while still assuming zero model inference, exact verification,
and fallback cost.

Assessment SHA-256:
`f8c83eb8c0d11d46958cfcb77ac1d499898c049f3e07bd66b71f9df247b801cb`

Independent verification: `verified`.

## Decision and next boundary

Keep the native implementation as a strong exact development candidate. Do not infer
production portability or promotion from one exposed Windows cohort.

The previously documented instruction to consume a fresh prospective native cohort is
superseded by the current gate. A fixed-backend improvement is not selector headroom.
Because the complete optimized portfolio has only `1.0000x` per-case-oracle headroom,
no prospective corpus, C37 router, cost model, or neural training is justified.

Future prospective work requires a genuinely new exact task or decision surface with
approximately `1.10x` development oracle headroom after optimized exact baselines. For
partition learning, it also requires a sound early-termination or certificate mechanism
that avoids material global-best completion work.

## Test hardening

The local native tests now discover the retained manifest-bound DLL by default on this
Windows checkout instead of silently skipping execution. Multi-root workload tests also
recompute the six arithmetic workloads through an independent scalar arithmetic oracle,
rather than relying only on the packed-expression evaluator. The new portfolio verifier
supports read-only replay after its verification record exists.

The focused exact/native/reassessment suite passed `131` tests and `282` subtests. The
broad non-neural suite passed `1,251` tests and `1,128` subtests, with the same four
pre-existing `dd` BDD cleanup warnings. The generated-public-chart test remains outside
that broad run because its checked-in generated JavaScript records an older renderer
source revision; this pre-existing documentation-generation mismatch is unrelated to the
native portfolio result and was not regenerated in this work.

Historical run directories and their source-bound files were not overwritten.
