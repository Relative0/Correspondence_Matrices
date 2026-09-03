# CM post-benchmark neural eligibility reassessment

Date: 2026-09-03  
Status: **verified complete; neural training remains prohibited**

## Decision

Architecture-comparison retry 002 is now incorporated as exact, source-bound,
one-host development evidence. The reassessment recomputed per-case diagnostic
labels, the best fixed method, the per-case oracle, and charged economics for 22
task/cohort surfaces. It did not fit a selector, train a model, consume a new
corpus, run timings, create a cloud resource, change production routing, or
publish a result.

Only one surface crosses the `1.10x` gross point gate:

| Surface | Complete cases | Best fixed | Gross headroom | Historical-recognition-only speedup |
|---|---:|---|---:|---:|
| resident version history | 3 | `sat/resident_engine` | `1.137580420x` | `0.520856231x` |

Its diagnostic labels are two `sat/resident_engine` cases and one
`cnf/resident_engine` case. The best fixed sum is 355,668.5 ns and the per-case
oracle sum is 312,653.5 ns, leaving only 43,015 ns of gross gain. At most 3,560.5
ns per case of total recognition and model overhead could preserve `1.10x`.
Charging only the historical 123,400 ns-per-case recognition allowance makes
the optimistic speedup less than one while still assigning zero cost to model
inference, exact verification, and fallback.

This is a new gross signal worth recording, not a training authorization. The
surface contains only three complete case clusters; the source campaign and its
independent verifier explicitly prohibited selector or neural claims; and no
charged candidate survives the `1.05x` prospective gate. Advice remains
disabled, every case abstains, and the exact fallback is unchanged.

## Other exact surfaces

The main fixed-versus-oracle point estimates remain below the development gate:

| Surface | Gross oracle headroom |
|---|---:|
| complete explicit relation, all runnable cases | `1.006013802x` |
| repeated q64 restrictions, all cases | `1.051098149x` |
| repeated q64 restrictions, fresh cases | `1.058240197x` |
| related multi-root outputs, all cases | `1.024095858x` |

The observed C36 restriction subset remains effectively closed at
`1.000542985x`. Retry 002 does not separately time q1/q4/q16, so no query-count
selector surface is manufactured from its prefix correctness digests.

## Neural task disposition

- C5 decomposition/cut proposal remains a frozen negative artifact.
- Partition ranking remains stopped until a sound early-termination or
  certificate mechanism materially avoids exact global-best completion work.
- Backend selection has one small gross version-history signal, but its charged
  economics and evidence sufficiency fail.
- Any future version-history work must begin with analytical controls and a
  source-blind expanded development protocol capable of sub-3.6 microsecond
  total recognition. This artifact does not authorize that execution.

## Implementation and evidence

- `cmbench/recognition/post_benchmark_neural_gate.py`
- `scripts/cm_post_benchmark_neural_eligibility.py`
- `scripts/crse_post_benchmark_neural_eligibility_verify.py`
- `tests/test_post_benchmark_neural_gate.py`
- development artifact:
  `docs/recognition/runs/post-benchmark-neural-eligibility-development-20260903-001/`
- evidence checkpoint:
  `27e88d26a780da0840cd9ed221c1f8966dfeb039`
- assessment SHA-256:
  `40bd8e37a475090496beaf88d17ce31442e57190060d2b94b46dac650be3e8df`
- independent status: `verified_no_training`, byte-identical replay

## Verification

- Focused post-benchmark gate, prior neural reassessment, and benchmark-analysis
  suite: 14 passed.
- Broader gate, freeze, campaign, package, analysis, and reassessment regression
  suite: 34 passed.

No frozen benchmark or neural artifact was overwritten.
