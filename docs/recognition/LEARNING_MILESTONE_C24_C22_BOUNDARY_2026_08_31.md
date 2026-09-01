# Learning milestone C24: frozen C22 end-to-end boundary

Date: 2026-08-31  
Status: **locally complete and independently verified; promotion gate failed**

## Question

C23 showed that three direct exact methods were nearly tied on the sealed 48-case
Yosys-family corpus. C24 asks whether the frozen C22 source-packed portfolio remains
profitable when it is exercised through a fail-closed request boundary rather than as
an isolated kernel.

No policy was trained or refit. The C22 policy still selects
`source_packed_anf_screened`, uses `explicit_cm_exhaustive` when advice is disabled,
and uses the same exhaustive arm after a source-path refusal.

## Implementation

The C24 boundary validates the input envelope and expression/truth identity, loads and
validates the frozen policy, compiles a fresh single-query portfolio, executes exact
completion, serializes and verifies the C22 execution, then serializes and independently
checks the delivered artifact. Its record separates input validation, policy load,
compilation, execution, serialization/verification, and wrapper time.

Eight balanced methods were measured for nine rounds over all 48 cases:

1. direct exhaustive CM;
2. direct screened CM;
3. direct compiled-screened CM;
4. direct source-packed ANF with screened CM completion;
5. C22 advice on;
6. C22 advice off;
7. C22 advice on with shadow execution; and
8. C22 advice off with shadow execution.

The shadow methods are diagnostics and were excluded from deployable ranking. The run
contains 3,456 timing records and 64 bounded memory diagnostics.

## Exactness and safety controls

All timed methods returned the same bounded exhaustive-best GF(2) artifact. C24 also:

- injected a source-path refusal for every one of the 48 cases and verified exact
  exhaustive fallback;
- refused an unsupported seven-variable request;
- refused malformed expression metadata and an expression/truth mismatch;
- refused a policy with a changed selected arm; and
- refused a policy containing a duplicate JSON key.

The independent verifier replayed all 48 exhaustive oracles and forced fallbacks,
checked five refusal controls, checked 48 contracts, validated 3,456 timing records and
64 memory records, recomputed the summary, and found zero semantic or artifact
mismatches.

## Results

| Method | Aggregate vs direct exhaustive | Aggregate vs direct screened | Minimum case vs screened |
|---|---:|---:|---:|
| Direct exhaustive | 1.0000x | 0.3094x | 0.2680x |
| Direct screened | 3.2319x | 1.0000x | 1.0000x |
| Direct compiled screened | 3.2385x | 1.0020x | 0.9098x |
| Direct source packed | 3.2305x | 0.9996x | 0.9407x |
| C22 advice on | 2.6910x | 0.8326x | 0.3323x |
| C22 advice off | 0.9406x | 0.2910x | 0.2580x |
| C22 advice on, shadow | 0.7418x | 0.2295x | 0.2046x |
| C22 advice off, shadow | 0.7378x | 0.2283x | 0.2063x |

Direct compiled-screened CM was the fastest deployable fixed method on this Windows
run. Its lead was narrow: the deployable per-case timing oracle had only **1.0169x**
headroom.

The fully charged advice-on boundary was **0.8330x** as fast as its direct source-packed
control. Advice-off was **0.9406x** as fast as direct exhaustive. Advice-on shadow
execution cost **3.6277x** the non-shadow path.

The local promotion contract required all controls to pass, advice-on aggregate speed
at least equal to direct screened, and no individual case below 0.90x direct screened.
The functional condition passed; the aggregate and minimum-case timing conditions did
not. Production promotion therefore remains false, and a Linux replication is not
warranted for this lifecycle.

## Interpretation

The underlying source-packed exact computation remains competitive with screened CM.
The loss appears when a fresh request repeatedly pays validation, policy parsing,
policy compilation, duplicated exact-delivery checks, and response construction. The
fixed cost is most visible on three- and four-variable cases: advice-on reached only
0.3855x and 0.4740x direct screened by width, while the six-variable group reached
0.8680x.

This distinguishes algorithmic performance from boundary profitability. C24 does not
invalidate the C21 or C23 direct-method speedups. It shows that a fresh-engine,
single-query dispatcher cannot spend a narrow fixed-arm advantage on orchestration and
still win.

## Next milestone

C25 should evaluate a resident-session contract with immutable compiled-policy reuse.
It should charge session creation once, validate each query, retain exact fallback and
fail-closed behavior, and compare break-even query counts against resident direct
screened, compiled-screened, source-packed, and exhaustive controls. No production
promotion or new router training should occur unless that repeated-query lifecycle
passes exactness and profitability gates on local and unchanged second-machine runs.

## Evidence

- Run: `docs/recognition/runs/c24-c22-boundary-windows-20260831-001`
- Independent verification: `docs/recognition/runs/c24-c22-boundary-windows-20260831-001/independent_verification.json`
- Boundary: `cmbench/recognition/gf2_source_portfolio_boundary.py`
- Experiment: `cmbench/comparative/gf2_source_portfolio_experiment.py`
