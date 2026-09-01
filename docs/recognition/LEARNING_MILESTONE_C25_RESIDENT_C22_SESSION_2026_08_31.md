# Learning milestone C25: resident C22 repeated-query sessions

Date: 2026-08-31  
Status: **locally complete and independently verified; resident promotion gate failed**

## Question

C24 established that the frozen C22 source-packed portfolio is exact and fail-closed,
but loses to direct screened CM when every request reloads and recompiles the policy.
C25 tests whether bounded repeated-query sessions recover that loss by reusing an
immutable validated policy and compiled portfolio state.

No policy was trained or refit. All computations remain exact GF(2) decompositions and
all delivered artifacts are bound to the same exhaustive-best oracle.

## Resident implementation

A resident session:

- validates and freezes the C22 policy once at session setup;
- lazily compiles and caches one portfolio for each support width encountered;
- enforces a declared query limit of at most 256;
- validates the expression/truth identity on every query;
- performs exact CM completion and exact artifact replay on every query;
- serializes and verifies every delivered response;
- retains exact exhaustive fallback after source-path refusal; and
- refuses queries after its limit or after session close.

The benchmark used query counts **1, 2, 4, 8, 16, and 32**, four support widths, six
methods, and five balanced rounds. This produced **720 batches and 7,560 timed exact
queries**, plus 24 bounded memory batches.

The sealed C23 corpus is uneven by support width: 2, 6, 12, and 28 cases at widths
3–6. Each condition used the complete available group and cycled deterministically
when its session contained more queries than distinct cases. Every method within a
condition received the same ordered query sequence.

## Controls and verification

The direct resident controls were exhaustive CM, screened CM, compiled-screened CM,
and source-packed ANF with screened exact completion. C22 advice-on and advice-off were
the two resident boundary methods.

The functional gate independently exercised exact forced fallback on all 48 cases and
refused a truth mismatch, unsupported width, closed session, exceeded query limit, and
tampered setup policy. All controls passed.

The independent verifier replayed 48 exhaustive oracles and 48 forced fallbacks,
checked 48 contracts, all 720 batch records, all 7,560 query records, 2,520 resident
cache records, and 24 memory batches. It recomputed the complete summary and found zero
semantic or artifact mismatches.

## Results

| Queries/session | Advice on vs direct screened | Minimum width vs screened | Best fixed method |
|---:|---:|---:|---|
| 1 | 0.7747x | 0.4137x | resident direct screened |
| 2 | 0.7855x | 0.4245x | resident direct source packed |
| 4 | 0.8186x | 0.5059x | resident direct screened |
| 8 | 0.7697x | 0.4506x | resident direct screened |
| 16 | 0.8444x | 0.5087x | resident direct source packed |
| 32 | 0.7992x | 0.5447x | resident direct screened |

The median C22 setup cost across widths stayed near **0.41–0.44 ms**, and all queries
after the first query in a same-width session hit the compiled cache. Even so, no
tested query count reached aggregate parity with direct screened CM, so the declared
break-even query count is **none through 32 queries**.

The resident promotion gate required all functional controls, aggregate advice-on
speed of at least 1.00x direct screened, and every support width at least 0.90x direct
screened. The exactness condition passed and the profitability conditions failed.
Production promotion remains false, and no second-machine timing run is warranted.

## Interpretation

Policy load and compilation were not the full C24 loss. C25 successfully amortized
them, but the resident query still repeats work that direct adapters avoid: expression
evaluation during input validation, another reference evaluation in selected-arm exact
checking, another during execution-record verification, and final delivery replay.
Those checks make the boundary conservative and exact, but their per-query cost cannot
be amortized by longer sessions.

The direct screened/source-packed ranking remained close and changed with query count,
which agrees with C23's machine-specific near tie. There is no useful timing headroom
for a learned router in this evidence; C25 is lifecycle engineering, not model
training.

## Next milestone

C26 should implement a hash-bound verified request context that decodes and evaluates
the expression once, carries the proven truth identity into exact completion, and
retains one final independent artifact reconstruction. It must prove that removal of
duplicated evaluations does not weaken refusal, fallback, or artifact-optimality
contracts. The same six resident methods and query-count schedule should then be rerun.
Only a local exactness and profitability pass would justify an unchanged Linux
replication.

## Evidence

- Verified run: `docs/recognition/runs/c25-c22-resident-windows-20260831-002`
- Independent verification: `docs/recognition/runs/c25-c22-resident-windows-20260831-002/independent_verification.json`
- Pre-timing failed attempt: `docs/recognition/runs/c25-c22-resident-windows-20260831-001/FAILED_ATTEMPT.json`
- Session implementation: `cmbench/recognition/gf2_source_portfolio_session.py`
- Experiment: `cmbench/comparative/gf2_resident_session_experiment.py`

