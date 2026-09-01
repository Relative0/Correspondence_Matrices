# Learning milestone C26: fused hash-bound verified contexts

Date: 2026-08-31  
Status: **locally complete and independently verified; conservative promotion gate failed**

## Question

C25 showed that resident policy and compiled-plan reuse did not remove the C22
boundary's per-query loss. C26 tests the next identified cause: repeated expression
decoding, semantic evaluation, execution-record verification, and artifact replay.

No model was trained and no C22 policy was refit. The sealed C23 corpus, exhaustive-best
oracles, query schedule, and four direct C25 controls remained unchanged.

## Implementation

C26 introduces a `VerifiedGF2RequestContext` that binds:

- case identity and support width;
- the canonical expression digest;
- one evaluated truth vector and its GF(2) truth digest;
- the packed source polynomial and instrumentation when the source path is required;
- an independent equality check between the packed polynomial's truth and the evaluated
  expression truth; and
- a digest over the complete context.

Each successful fused query evaluates the expression exactly once. Exact CM completion
consumes the verified truth directly, without reparsing or reevaluating the expression.
The selected artifact retains a charged final reconstruction before delivery. Resident
sessions still validate the frozen policy once, cache one immutable plan per support
width, enforce query limits and close semantics, and fall back exactly to exhaustive CM.

## Experiment

The experiment retained the C25 counts of **1, 2, 4, 8, 16, and 32 queries per
session**, four support widths, six methods, and five balanced rounds. The four direct
methods used the unchanged C25 batch adapter:

1. resident direct exhaustive CM;
2. resident direct screened CM;
3. resident direct compiled-screened CM;
4. resident direct source-packed ANF;
5. fused C22 advice on; and
6. fused C22 advice off.

The run contains **720 measured batches, 7,560 timed exact queries, and 24 bounded
memory batches**.

## Exactness and refusal controls

C26 used exact forced source refusal on all 48 cases. It also refused truth mismatch,
unsupported width, closed session, exceeded query limit, and tampered setup policy.
Four additional controls changed the context's expression digest, truth, width, or
context digest. All nine refusal controls failed closed.

The independent verifier replayed all 48 exhaustive oracles and fallbacks, checked 48
contracts, all 720 batches and 7,560 query records, semantically rebuilt all **2,520
fused contexts**, checked 2,520 plan-cache records, validated 24 memory batches, and
found zero semantic or artifact mismatches.

## Results

| Queries/session | Fused advice on vs direct screened | Minimum width vs screened | Best fixed method |
|---:|---:|---:|---|
| 1 | 1.0238x | 0.6391x | fused C22 advice on |
| 2 | 1.1705x | 0.7007x | fused C22 advice on |
| 4 | 1.0442x | 0.8621x | fused C22 advice on |
| 8 | 0.9851x | 0.8680x | resident direct screened |
| 16 | 1.0240x | 0.8131x | resident direct source packed |
| 32 | 0.9418x | 0.8852x | resident direct screened |

Fused advice-on was the fastest fixed method at 1, 2, and 4 queries and exceeded
direct screened in aggregate at 1, 2, 4, and 16 queries. Relative to each run's direct
screened control, its normalized result improved over C25 by **1.18–1.49x**, depending
on query count. That cross-run comparison is directional because timings remain
same-machine and retrospective.

The promotion contract also required every support width to reach at least 0.90x
direct screened. No query count satisfied that no-regret floor, so the declared
break-even remains none and production promotion remains false.

## Width-level finding

The fused result isolates the remaining issue to small-support overhead rather than CM
completion generally:

| Queries | n=3 | n=4 | n=5 | n=6 |
|---:|---:|---:|---:|---:|
| 1 | 0.6391x | 0.7202x | 0.9327x | 1.1164x |
| 2 | 0.7007x | 0.7630x | 1.1972x | 1.2461x |
| 4 | 0.8621x | 0.8832x | 1.1075x | 1.0461x |
| 8 | 0.9537x | 0.8680x | 0.9231x | 1.0215x |
| 16 | 0.8131x | 0.9390x | 0.9630x | 1.0638x |
| 32 | 1.0981x | 0.8852x | 1.0909x | 0.8947x |

The packed-source context has a fixed construction and hashing cost that is
disproportionate at n=3 and n=4. Larger supports often profit from fusion.

## Next milestone

C27 should freeze a transparent analytical support rule: use a truth-only verified
screened path for tiny supports and retain the packed fused path for larger supports.
Because C23/C26 would be development evidence for that threshold, profitability must
be confirmed on a newly frozen, previously unused generator corpus. The unchanged six
controls, context-tamper suite, fallback suite, and query schedule should remain.
Second-machine replication is justified only after that fresh local gate passes.

## Evidence

- Run: `docs/recognition/runs/c26-fused-resident-windows-20260831-001`
- Independent verification: `docs/recognition/runs/c26-fused-resident-windows-20260831-001/independent_verification.json`
- Verified context: `cmbench/recognition/gf2_verified_context.py`
- Fused session: `cmbench/recognition/gf2_fused_source_portfolio_session.py`
- Experiment: `cmbench/comparative/gf2_fused_session_experiment.py`

