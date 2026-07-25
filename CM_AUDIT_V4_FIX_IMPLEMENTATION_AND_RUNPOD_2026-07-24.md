# Audit V4 fixes and adversarial verification — 2026-07-24

## Decision summary

The audit found real correctness-of-reporting and architecture issues, not a
truth-table correctness failure. The most consequential problems were:

1. headline ratios could silently compare only surviving successes;
2. CUDD best-of-k did not preserve all trials or distinguish isolated build,
   order generation, search, and selected-objective time;
3. mutable evaluation defaults could leak between CLI calls in one process;
4. engine labels could say `words` even when small live support made flat
   bigint the actual implementation;
5. timing columns lacked machine-checkable artifact/timing semantics;
6. chart comparison arrays were duplicated by hand;
7. repeated flat evaluation rebound the same inputs on every call.

All seven are addressed. The full suite passes (194 tests), the same-corpus
RunPod campaign produced zero CM/Bitset mismatches, native `dd.cudd` was
verified for every one of 49 formulas, and both temporary pods were terminated.

## Implemented changes

- `cmbench/results/paired.py`: failure-aware paired aggregation with per-side
  attempted/success/declined/refused/timeout/error/OOM/missing counts. Headline
  ratios are unavailable for incomplete pairing unless explicitly overridden.
  Both ratio-of-medians and median paired ratio are reported.
- `cmbench/backends/robdd_dd.py`: explicit selection objectives, deterministic
  tie-breaking, every order trial serialized, and separate fastest-build,
  smallest-node, selected-build, order-generation, order-search, and all-in
  timings.
- `cm_ir.py`: scoped/default-preservation context managers; `cm_bench.main`
  restores defaults on success and exceptions.
- `cmbench/backends/bitset_engine.py`: one actual-live-support engine policy.
  `live_k < 6` uses/labels flat bigint; `live_k >= 6` uses/labels words when
  requested. Local, remote CM, ordinary, partial, and family paths use it.
- `cmbench/results/timing.py`: structured artifact/timing descriptors with
  strict comparison compatibility and explicit contextual-comparison opt-in.
- `cmbench/corpus.py` and `--corpus-jsonl`: immutable formula and corpus hashes,
  exact formula consumption, and rejection of mixed-corpus aggregation.
- `bitset_backend.py`: relevant-variable bitmask cache keys replace sorting an
  ambient fixed map; prepared raw-expression and CM-node flat evaluators bind
  once for repeated execution.
- `scripts/generate_v4audit_public_chart_data.py`: regenerates versioned chart
  data with source hashes. Both public HTML pages consume that artifact.

Compatibility columns remain where existing consumers may depend on them; new
authoritative fields are additive. Historical CSVs were not relabeled.

## Performance result

`CM_v4fix_cached_eval_{raw,summary}.csv` contains 378 paired observations over
42 corpus formulas, nine interleaved rounds, and zero mismatches.

Prepared evaluation improved median steady-state time by about 1.31–1.82x for
live support 1–5, 1.14x at live 8, and was approximately neutral at live
12–16 (1.00x and 0.97x). Preparation cost was measured separately. Therefore
the prepared API is useful for repeated small-support evaluation, but it is not
a universal large-support speedup and should not replace the words path.

## RunPod result

The final campaign used a fresh secure CPU pod:

- pod `43px70tr4zvttv`;
- 4 vCPU, `$0.12/hour`;
- corpus SHA-256
  `a1cb0763889c8f91de2fcc5a3fd86b0bc007afd728736452a84b39bf441f909d`;
- 49 symbolic formulas: native `dd.cudd` verified for all families;
- 42 explicit packed formulas / 301 raw rows: zero CM/Bitset mismatches;
- best-of-10 CUDD raw rows retain every trial and all timing components;
- termination returned HTTP 204.

An earlier launch, pod `76crq9qxp11ig4`, was interrupted by the local command
timeout and explicitly terminated (HTTP 204). The first completed pod was also
terminated; the final audit JSON records the final pod and cleanup.

Remote packed results reinforce an important pitfall: CM wrapper overhead is
large for tiny support (median CM/Bitset ratios roughly 3.5–4.3x at live 1–4),
narrows at live 12 (1.09x), and becomes modestly favorable at live 16 (0.94x).
Claims must therefore be stratified by actual live support and artifact type.

## Remaining pitfalls and recommendations

1. Do not publish one blended “CM versus Bitset versus CUDD” winner. CUDD build
   produces a symbolic BDD; packed execution produces a truth function.
2. Keep best-of-k isolated-build and all-in-search numbers together. Reporting
   only the selected build understates search cost.
3. Use prepared flat evaluation only when an expression and binding are reused.
   One-shot calls still pay preparation and should use the ordinary API.
4. Keep the historical compatibility columns temporarily, but migrate readers
   to structured timing and paired fields, then deprecate ambiguous ratios.
5. The benchmark CLI remains large and orchestration-heavy. A later refactor
   should split workload construction, execution, row schema, and persistence;
   doing that now would have made this corrective patch needlessly risky.
6. Native CUDD availability depends on a compatible wheel/toolchain. Explicit
   CUDD requests correctly fail closed rather than silently using `autoref`.

## Verification

- Baseline before changes: 159 passed.
- Final: `python -m pytest -q` — 194 passed in 59.48 seconds.
- Generated chart checks: 2 passed.
- RunPod CUDD mode: `available_verified` for all five corpus families.
- RunPod packed equality: true for every attempted paired observation.
- No commit or push was performed.
