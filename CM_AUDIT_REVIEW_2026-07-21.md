# Adversarial audit of the 2026-07-21 CM findings

Date: 2026-07-21  
Repository state audited: `fe73f82` plus the changes described here  
Benchmark interpreter: Python 3.13.5, NumPy 2.3.2, dd 0.6.0  
Test interpreter: Python 3.10.11, NumPy 2.2.6, dd 0.5.7, pytest 9.0.2

## Executive verdict

The capability and correctness findings survive. The strongest speed wording does not survive
unchanged.

- Exhaustive full-row checks through n=24 found no wrong result in CM reduced/full output, raw
  bitset, recursive CM-IR bitset, or C1a flat evaluation. Direct `dd.autoref` enumeration also
  passed.
- The old environment builder is independently confirmed as the practical n>16 cliff. The new
  vectorized masks are bit-identical wherever both implementations completed.
- C1a's bound cache contains inputs only and does not memoize operation outputs.
- Flat-vs-flat **kernel** performance is parity to modestly in CM's favor on the audited workloads.
  The inherited “parity to ~1.4x faster” upper end was not robust across expressions/sessions:
  this audit measured roughly parity to 1.20x faster on full-arity medians.
- End-to-end wrapper results are less favorable for tiny reduced outputs: five-session median
  CM/raw-flat ratios were 1.09x-1.43x (CM slower), with individual session medians spanning
  0.88x-1.70x. Publication text must distinguish kernel parity from wrapper timing.
- The decline/selection-bias account is correct. A new explicit
  `cm_hybrid_no_reinflate_declined_count` summary column now prevents it from hiding.
- A material fairness defect was found and fixed: the large-n “matched bitset” timer was calling
  `eval_cm_node_bitset` on the canonicalized CM DAG. It now evaluates a flattened **raw Expr AST**
  over the same output scope and records `bitset_baseline_kind=raw_ast_flat_matched_scope`.
  At ordinary sizes, `--cm-flat-eval` now selects `raw_ast_flat` for the bitset side as well.

The safe headline is: **CM supplies an exact structure-preserving/reduced representation, and its
compiled kernel is competitive with a compiled raw-bitset kernel. It does not establish general
raw speed dominance.**

## 1. Correctness audit

The reproducible harness is `deliverables_n22_24/audit_2026_07_21.py`. It keeps
`eval_expr_tt` outside all timed windows and expands reduced CM results back into the complete
ambient assignment space before comparison.

### Python 3.13.5 result

| Coverage | Result |
|---|---:|
| n values | 16, 18, 20, 22, 24 |
| Expressions | 30 |
| Full rows compared per method | 134,086,656 |
| CM reduced/full vs oracle failures | 0 |
| Raw bitset vs oracle failures | 0 |
| Recursive CM-IR bitset vs oracle failures | 0 |
| C1a flat vs oracle failures | 0 |
| Adversarial kernel failures | 0 |
| Direct `dd.autoref` exhaustive failures | 0 |

The suite includes genuine all-live XOR expressions through n=24, sparse reduced outputs, random
depth-4 trees, single variables, repeated variables, annihilating/constant subtrees, a 256-leaf
deep mixed IMP/EQV/XOR/OR/AND chain, nested NOT, all-fixed evaluation, and
`live_k == hybrid_threshold`. Both repr 2 (full bitset) and repr 3 (reduced bitset) were exercised.

Python 3.10.11 independently passed the same checks at n=16 and n=20 (12 expressions,
6,684,672 rows per method), plus the adversarial and `dd.autoref` suites. Artifacts:

- `CM_audit_2026-07-21_py313_{exhaustive,adversarial,dd_autoref}.csv`
- `CM_audit_2026-07-21_py310_{exhaustive,adversarial,dd_autoref}.csv`

### Bound-cache audit

For both CM-flat and raw-flat, every cached entry is exactly `(input_template, full_mask)`.
Operation slots remained zero in the cached templates after evaluation; every call copies the
template and recomputes every operation output. There is no result memoization. See
`CM_audit_2026-07-21_{py313,py310}_bound_cache.csv`.

## 2. Environment-build cliff

Fresh first-touch medians on Python 3.13.5:

| n | old builder | vectorized builder | old/new | identical |
|---:|---:|---:|---:|:---:|
| 14 | 9.46 ms | 0.84 ms | 11.3x | yes |
| 16 | 86.2 ms | 4.73 ms | 18.2x | yes |
| 18 | 1.08 s | 22.2 ms | 48.8x | yes |
| 20 | 14.0 s | 136 ms | 102.6x | yes |
| 22 | not rerun (prohibitive old loop) | 460 ms | - | indirectly covered by oracle sweep |
| 24 | not rerun (prohibitive old loop) | 2.06 s | - | indirectly covered by oracle sweep |

Python 3.10.11 reproduced the same cliff: 95.9 ms -> 7.28 ms at n=16, 1.22 s ->
23.2 ms at n=18, and 19.3 s -> 115 ms at n=20. Exact data are in
`CM_env_build_2026-07-21_{py313,py310}.csv`.

No other core backend gate was found through n=24. `bitset_backend.py` has no n=16 limit.
`materialize_hybrid_no_reinflate` has the documented parameterized output guard only. The harness
also has `full_tt_max_n=16`, which deliberately skips full truth-table/oracle methods unless raised;
that is a benchmark policy gate, not a CM or bitset capability limit.

## 3. C1a speed/fairness verdict

The original recursive-before/flat-after speedup is real. The fair conclusion is narrower:

- On full-arity, full-output programs, current CM-flat/raw-flat kernel ratios were 0.83, 0.84,
  0.90, 0.89, and 0.94 at n=16/18/20/22/24 (25 samples per method at each n).
- On cached depth-4 programs at n=4/8/12/16, ratios were 0.95/1.14/1.03/0.96. This is parity,
  not a workload-independent 1.4x CM win.
- The diagnostics-off wrapper fast path helps selected small cases (paired generic/fast medians:
  1.15x at n=8 and 1.29x at n=12) but cannot erase the result-object and scope-planning cost.
- In the actual reduced-output CLI path, five-session median CM/raw-flat ratios were 1.15x,
  1.43x, 1.23x, and 1.09x at ambient n=18/20/22/24. All rows were correct and none declined.

Large-output full-arity session ratios were substantially better behaved than the inherited
“+/-30-50%” warning: coefficient of variation was about 6-10%, although n=24 session medians still
ranged 0.85x-1.12x. Tiny microsecond-scale reduced-output ratios were less stable (0.88x-1.70x),
and one earlier run suffered a much larger system outlier. Ratios should therefore still be
reported as ranges/medians, not precise constants.

## 4. Declines and selection bias

An independent 6,000-expression sweep (300 per n/depth cell) confirmed:

- Depth 4 never exceeded 13 live variables at n=16/20/24/28/32; decline count was zero.
- At n=24, measured decline rates were 0%, 0.7%, 23.3%, and 92.0% at depths 4/5/6/8.
- Every accepted result had at most 16 output variables; every `live_k > 16` case was refused.
  Wrong-guard count and oversized-output count were both zero.

A separate n=24/depth-6 CLI run declined 7 of 30 rows. Its summary timing
(`0.001355799963 s`) is exactly the median of the 23 timed survivors, proving the NaN-skipping
selection mechanism. The new summary column reports the missing `declined_count=7` explicitly.
See `CM_audit_2026-07-21_decline_distribution.csv` and `bench_audit_decline_d6_*`.

## 5. Interpreter and optional-backend integrity

- The documented split is real: benchmark Python 3.13.5/NumPy 2.3.2/dd 0.6.0 versus test Python
  3.10.11/NumPy 2.2.6/dd 0.5.7.
- There was no output divergence across interpreters. Performance did diverge enough to prohibit
  mixing them: for the n=16 full-arity raw-flat case, Python 3.10 was about 12% slower, while the
  CM-flat median moved in the opposite direction. Small microbenchmarks were noisier still.
- `dd.cudd` is absent in both environments on this machine. `dd.autoref` passed direct truth-table
  enumeration independently of harness status flags in both versions.
- Numba is absent from the benchmark venv. The existing numba evaluator is a row-by-row uint8
  stack machine, not a packed-word flat executor. It is a useful auxiliary baseline under system
  Python, but it is not the primary fair flat-vs-flat control for these headline runs.

## 6. Framing hygiene

No commit subject in the audited history claims CM speed dominance. Several documents could be
misquoted despite later caveats, so correction banners were added to
`CM_tierC_rescope_report.md`, `CM_c1a_flat_eval_report.md`, and
`CM_convergence_findings.md`. `FABLE_CM_SPEEDUP_AGENDA.md` was corrected to require a
matched-scope raw-flat comparator rather than assuming bitset must enumerate all nominal variables;
`FABLE_CM_HANDOFF.md` now states the interpreter split accurately.

The consolidated session handoff is already substantially honest, but its “parity to ~1.4x
faster” phrase should be replaced for publication by: **kernel parity to a modest workload-dependent
CM advantage; public-wrapper parity to a modest bitset advantage on tiny reduced outputs.**

## 7. Publication recommendation

Publish capability, exactness, reduced structural representation, explicit decline rates, and
flat-kernel competitiveness. Do not publish a single CM-over-bitset speed multiplier. Every speed
table should state all four of: raw versus CM IR, recursive versus flat, kernel versus wrapper, and
full versus matched-reduced output scope.
