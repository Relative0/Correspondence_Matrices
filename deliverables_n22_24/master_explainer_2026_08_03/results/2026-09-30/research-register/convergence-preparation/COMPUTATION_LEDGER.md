# Computation ledger — new audit and preparation

This ledger supplements the original frozen baseline; it does not retroactively rewrite C01–C12 in that baseline.

| ID | Work | Coverage / result | Evidence |
|---|---|---|---|
| N01 | External audit integrity | 85 entries match | imported manifest; `runs/final_correctness/00.log` |
| N02 | Independent external mathematical oracle rerun | All checks pass; substantive results match original | `runs/independent_replay/` |
| N03 | Frozen correctness rerun | Eight commands pass; original counts preserved | `runs/baseline_replay/` |
| N04 | Original Theory replay | PASS with output-path-only portability wrapper | `runs/theory_replay/` |
| N05 | Full old lifecycle replay | 38 cases, 570 trials, 128 queries per trial; 0/38 artifact wins versus packed | `runs/benchmark_replay/` |
| N06 | C1 integration | 65,536 factorization comparisons; 613,656 restricted profiles; 42,192 cut/update comparisons; PASS | `runs/coordinate_integration_v2/`; final correctness replay |
| N07 | C3 source freeze/extraction | 20 designs, two families, 2,861 outputs accounted; 1,088 admitted, 1,773 excluded; 2,119 cut cases | `corpus_v1/` |
| N08 | Independent extraction cross-check | 1,088 truth hashes match, including 31 scalar constant checks | `runs/corpus_crosscheck.json` |
| N09 | Packed/rank binary correctness | 7,070 all-restriction cases per backend through n=3, originals/residuals/reloaded residuals; PASS | `runs/infrastructure_validation_windows/` |
| N10 | Compiled CUDD-inclusive correctness | Same 7,070 cases per backend; 834 original binary round trips and trailing-byte rejections; PASS after adapter lifetime repair | `runs/infrastructure_validation_linux_v2.log` and directory |
| N11 | Lifecycle smoke | Windows 60, Linux 90 tiny trials; PASS; not T3 evidence | `runs/lifecycle_windows/`, `runs/lifecycle_linux/` |
| N12 | Final natural-source lifecycle acceptance | One development output, three methods, two semantics, three modes; separate-process advisory-load path; PASS | `runs/final_lifecycle_acceptance/` |
| N13 | Final one-command correctness | External integrity/oracle, baseline, snapshot integration, packed/rank endpoint validation; PASS | `runs/final_correctness/RECEIPT.json` |
| N14 | Final Linux one-command correctness | Same complete suite including compiled CUDD; PASS after pinning the legacy NumPy dependency; first failed receipt preserved | `runs/final_correctness_linux_v2/RECEIPT.json` |
| C2 | Main T3 campaign | NOT RUN; explicit user hold; no target supplied | `PROTOCOL_C2_PENDING.json` |

Backend tests are new infrastructure evidence, not new proof of optimality or historical priority. Corpus rank histograms describe the declared bounded slice and two fixed cuts; no T3 favorable-regime incidence can yet be reported. Legacy and smoke timings must not be pooled.

**SEND RESULTS/QUESTION TO THEORY**, then continue the pending computation work here once T3 is frozen.
