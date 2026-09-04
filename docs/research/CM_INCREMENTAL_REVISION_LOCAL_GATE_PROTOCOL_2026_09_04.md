# CM incremental-revision local gate protocol

Date frozen: 2026-09-04

Scope: exact, non-neural CM-family compilation across naturally adjacent versions

Status: frozen before implementing or timing the new incremental arm

## Question

Can a bounded incremental CM prototype reuse unchanged normalized CNF regions across
real adjacent feature-model revisions, with exact invalidation and an end-to-end
advantage after charging layout, compilation, lowering, evaluation, and retained
Python-owned state?

This is the open H9 experiment from
`docs/CM_ARCHITECTURE_AND_SPEED_INVESTIGATION_PROMPT_2026-09-02.md`. It is not a
neural, learned-routing, production-default, whole-model feature-analysis, or public
speed claim.

## Frozen input and split

Use every one of the 120 cached bounded cases in:

`deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/configuration-fm-version-delta-full21-2026-08-27/cases.jsonl`

- cases SHA-256:
  `3a4a394f458e0064994b4339858401e523f8dea836a3a697120f9db83299ef0e`;
- admissions SHA-256:
  `9afbf841866b26e6bc0615160d1e64c6f627904a8729fdd9837c809fccbb113a`;
- upstream feature-model source commit:
  `afa60ee2c836e7bdc4068e0f4f128ea31158d2ad`;
- 20 admitted natural transitions, three widths (`k=8,12,16`), and two slice
  rules (`incidence`, `hash`);
- the one historically refused Linux transition remains refused.

Transition labels, fixed before this experiment, define the split. `first` and
`middle` are development cases. `last` is the untouched timing-confirmation cohort.
The underlying dataset and earlier non-incremental outcomes are already public, so
“confirmation” means untouched by development of this new arm, not a secret or
independent test set.

## Common normalization and required artifact

Each residual CNF is normalized before any arm-specific construction:

1. repeated literals inside a clause are removed;
2. tautological clauses are removed;
3. clauses are sorted by literal identity;
4. duplicate clauses are removed;
5. any empty clause makes the complete CNF false.

The source multiset and normalized-set additions/removals are both reported. The
required result is the complete packed vector for the earlier version, the complete
packed vector for the later version, and their XOR vector in the saved least-
significant-`x0` assignment order. Every result must match an independent direct-CNF
packed evaluator and the three saved SHA-256 values.

## Arms

All arms receive the same normalized clauses and must return the same required
artifact.

1. `cm_cold`: build the ordinary balanced expression, compile CM IR without a
   persistent cache, and lower it independently for each version.
2. `cm_persistent`: use the current association-preserving persistent CM cache over
   ordinary balanced expressions, isolated to one case.
3. `cm_incremental_radix`: place canonical clauses in a deterministic digest-radix
   conjunction tree, reuse identical expression regions, and compile through an
   isolated bounded persistent CM cache. Only changed radix paths should rebuild.
4. `cse_flat`: independently compile each ordinary expression through structural
   CSE and sharing-aware flattening.
5. `raw_flat`: independently compile each ordinary expression without CSE; this is
   an ablation, not the principal baseline.

No result-output cache is allowed. Reuse is limited to parsing/normalization products,
expression nodes, CM IR nodes, lowered programs, bound inputs, and scratch state named
in the row schema.

## Measurement

- Run five measured rounds per case, rotating arm order deterministically.
- Clear global input masks and isolate every CM persistent pool at the arm-round
  boundary.
- Record earlier construction, later/update construction, flat lowering, a prewarmed
  16-pair evaluation batch, output bytes, normalized/source change, cache hits/misses,
  evictions, retained entries, program metrics, and a cycle-safe `sys.getsizeof`
  traversal of Python-owned retained state.
- Report medians per case. Aggregate ratios by geometric mean per history, then across
  histories. Use a fixed 4,000-draw history bootstrap with seed `2026090401`.
- Report projected resident totals for `q=1,2,4,8,16,32,64` from separately measured
  construction and prewarmed evaluation components. These are break-even diagnostics,
  not a natural query trace or permission to cache returned vectors.

## Frozen gates

1. **Correctness:** zero arm/oracle or saved-hash mismatches in all 120 cases.
2. **Invalidation:** every normalized changed clause is reflected in the later
   compilation identity; returning the earlier program for a changed normalized CNF
   is a hard failure even when the two output vectors happen to be equal.
3. **Activation:** every confirmation history must contain incremental reuse and at
   least one structurally changed confirmation case. Zero semantic-output changes are
   retained and not reselected away.
4. **Update construction:** on confirmation, the history-clustered geometric mean of
   `cm_incremental_radix / cm_cold` later-version construction must be at most `0.90`,
   with its upper 95% history-bootstrap endpoint below `1.0`.
5. **Current-cache comparison:** the corresponding incremental/current-persistent
   point estimate must be below `1.0`.
6. **Memory:** maximum incremental Python-owned retained bytes must be no more than
   `1.25x` the current-persistent arm for the same case; both absolute values and the
   limitations of this estimator remain visible.
7. **End-to-end:** promotion beyond an experimental arm also requires a confirmation
   break-even against `cse_flat` at some declared `q <= 64`, with no individual-history
   correctness failure. A construction-only win is not an application win.

Failing a performance or memory gate retains the result as negative evidence and
stops RunPod work. Passing the local gate permits preparation of a separately frozen
Linux confirmation package; it does not authorize cloud execution, selector fitting,
publication, or a production-default change.
