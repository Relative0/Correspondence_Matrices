# CRSE learning investigation — 2026-08-29

Status: investigation of the implemented local pilot, not a new deployed policy.
Windows software, VM/native execution, and cloud work remain deferred.

## What actually learns

The pilot learns a cost-sensitive decision tree that chooses `direct`, `cse`, or
`cm` exact evaluation. It is not a neural network, an LLM, or an answer cache.
The saved pilot model is 1,684 bytes of JSON, with seven nodes, four leaves, and
maximum depth three. Its split features are query count and expression depth;
all ten features still participate in the out-of-training-range guard.

The model was fitted using 48 training formulas and their measured costs.
Fitting took 5.2726 ms; training-data measurement and associated work took
209.7085 ms. Neither the validation nor test timings entered fitting.
Those costs do not imply that the policy recovers its training cost in use.

Every selected backend computes an exact complete truth vector, checked against
the independent NumPy expression interpreter. The learned model selects work;
it does not decide whether a Boolean equality is true.

The `cm` backend uses the existing canonical CM intermediate representation
and bigint executor. This is not a neural model trained on dense matrix pixels,
nor a comparison of every possible CM algorithm against every solver.

## Why the first pilot slowed down

On its original 16 test formulas, measured geometric-mean speedup versus the
training-selected fixed CSE baseline was 0.612712: a slowdown, not a speedup.
Per-formula medians, then medians across those formulas, were:

| Cost | Microseconds |
| --- | ---: |
| Fixed CSE total | 94.80 |
| Learned feature extraction | 63.40 |
| Learned selection | 10.15 |
| Learned total | 147.25 |

Medians are not additive. Feature extraction accounted for a median 45.2% of
the learned total. A replay that pretends selection and feature extraction are
free gives 1.50005 speedup for the chosen backends; a zero-overhead best-backend
oracle gives 1.64527. Neither is a measured end-to-end speedup. They show that
overhead can consume the available opportunity.

## Exploratory follow-up: pay for fewer features

Two candidate trees were fitted from the same original training costs:

1. Query-count-only: retain `log2_queries`, zero the other input dimensions.
2. Query-count-and-depth: add an iterative depth walk without the full structural
   feature extraction.

Both candidates used the same depth, minimum-leaf, and gain settings. Their
range guards were fitted for their own reduced feature schemas; the original
model's guards were not simply disabled. The original model was retained as a
control. Feature extraction was substituted only in a short-lived diagnostic
process; no research implementation, original model, or production route changed.

A fresh generated corpus used seed 20260829. After excluding structural/renamed
groups already present in the entire first pilot and duplicate groups in the
new pool, the diagnostic measured 32 known-family formulas and eight held-out
mux formulas. One duplicate candidate was excluded before measurement. The run
used five randomized rounds: 1,200 measurements, 37,320 checked query outputs,
and zero mismatches. A prior smaller-pool attempt stopped on duplicate admission
before measurement; it was not an alternative timing result selected for speed.

Geometric-mean speedup versus fixed CSE, including feature and selection costs:

| Method | Fresh known families (32) | Held-out mux (8) |
| --- | ---: | ---: |
| Direct | 0.880658 | 2.172824 |
| Fixed CSE | 1.000000 | 1.000000 |
| CM | 0.488093 | 0.421035 |
| Original learned selector | 0.693336 | 0.697567 |
| Query-count-only selector | 1.229571 | 1.718588 |
| Query-count-and-depth selector | 0.932985 | 1.058801 |

On the fresh known-family set, median query-only feature cost was 1.1 us versus
100 us for the original features. Its worst slowdown was 1.216x; no choice was
at least 2x slower. The depth feature still cost 41.05 us. Direct evaluation
alone outperformed the query-only selector on the mux family overall.

The query-only tree split at `log2_queries <= 1.5`: it effectively chose direct
for the measured single-query cases and CSE for the measured 8/64-query cases.
The threshold between those observations is not a measured universal crossover.
This resembles an ordinary compile-amortization rule. An equally cheap explicit
rule must be a baseline before attributing any gain specifically to learning.

## Evidence and limitations

The original retained pilot is `runs/pilot-20260828-001/`, intentionally ignored
by Git. Its recorded model canonical SHA-256 is
`8c407e75d76c50ae659222d1445e64b523de0b0d1a317ab34935016fbe4b951f`;
the corpus canonical SHA-256 is
`2ccb5ff9a8021ae0bb37371d61b89ec0f8218d03e462e18a90d7ef466dc93a31`.

[The preserved diagnostic summaries](learning_diagnostics_2026_08_29.json)
were transcribed from this task's successful tool outputs. The follow-up ran
only in memory: its raw timing rows and complete fitted candidate artifacts
were not saved. Its dataset digest was
`c56f9f7cd4885bcb61e9b1d6d68b65cd2f354e4e95fb43b83d767b72ce9e8c48`.
A digest and aggregate summary are not a replacement for a reproducible run.

These are tiny, generated, single-machine exploratory results without confidence
intervals or independent replication. Inspecting the first test results informed
the ablation design. Fresh formulas avoided the earlier structural groups, but
this is not full semantic deduplication or an untouched confirmatory benchmark.
No neural learning performance has been measured.

## Recommended next work, not implemented here

1. Make the reduced-feature experiment reproducible, retaining raw rows, source
   and dataset hashes, candidate schemas/models, and all failures.
2. Compare the tiny tree with an equally cheap query-count rule, fixed backends,
   and a feature-cost-aware model. Profile batch and per-request overhead.
3. Use real circuit/configuration families and grouped holdouts; freeze choices
   before a separate confirmatory set. Report clustered intervals and tail loss.
4. Train a richer model only where profiling shows substantial remaining search
   or execution cost. Distill it to a smaller policy if that helps total latency.

[Feature-Budgeted Random Forest](https://proceedings.mlr.press/v37/nan15.html)
explicitly treats feature acquisition as part of prediction cost. That is a
relevant design principle, not evidence that its model would win on these data.

## Verification of the software checkpoint

On 2026-08-29, the project virtual environment passed all 37 focused unittest
tests. The available Python 3.10 pytest environment passed 147 tests and 146
subtests across recognition and eight relevant existing suites. The project
virtual environment does not contain pytest. No full-repository or Ruff result
is claimed. No dependency installation was performed.

The staged whitespace check reports one existing trailing blank line at EOF in
the historical `CRSE_WCP4_DURABLE_APPROVAL_BATCH.md` packet. It is intentionally
retained to avoid rewriting that archived approval text. The computation-first
source, tests, and research notes pass their scoped whitespace check.
