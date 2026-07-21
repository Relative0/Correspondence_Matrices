# FABLE CM SPEEDUP AGENDA — Prioritized Research Targets

> Companion to [`FABLE_CM_HANDOFF.md`](FABLE_CM_HANDOFF.md) (read that first for the system map,
> the measured cost profile in §3.1, and the proven dead ends in §6). This file is the **ranked
> list of concrete speedup opportunities** for CM / CM IR / no-reinflate, each with a location,
> a hypothesis, how to measure it, expected payoff, and risk.
>
> **The one framing to keep:** there are two cost regimes and they have different bottlenecks.
> - **First-touch / one-shot** → dominated by **IR compilation** (Tier A).
> - **Compile-once / cached (the flagship use-case)** → dominated by the **CM-node bitset
>   evaluator + Python per-node dispatch/alignment/wrapping** (Tier B & C).
> Pick the regime you're improving *before* you touch code, and always report which one moved.

All line numbers are in [`cm_ir.py`](cm_ir.py) unless noted.

---

## How to work each target (protocol)

1. Reproduce the baseline with the canonical profile command (HANDOFF §4.1) and record the
   relevant `*_median` columns. Keep the CSV.
2. Form the hypothesis as a *measurable prediction* on a specific diagnostic
   (e.g. "`ir_intern_time_s` drops ≥30% at n≤8").
3. Implement behind a flag or as a drop-in that preserves output bit-for-bit. **Correctness
   oracle is `eval_expr_tt`; keep checks outside timed windows.**
4. Re-run; diff medians; run `python -m pytest -q` (must stay 159/159).
5. Record: which regime moved, by how much, and whether the residual bottleneck shifted.

Micro-benchmark caveat: n≤16 times are tens of µs — use `--cm-eval-repeat 100`, `--trials 5+`,
and compare medians. Watch for instrumentation overhead: the `ir_timing_enabled` /
`cached_exec_profile_enabled` paths add `perf_counter` pairs and dict writes on nearly every
node — **profile with them on to find hot spots, but confirm wins with them off.**

---

## TIER A — IR compilation cost (helps one-shot & first-touch)

Compile is the dominant one-shot cost (HANDOFF §3.1: 107–212 µs of the ~160–303 µs total). It is
*fully removed* by caching on a hit, so Tier A matters most for **cold cache, large families of
distinct-but-structurally-varied expressions, and the first evaluation** of each expression.

### A1. Redundant `expr_structural_hash` recomputation in the persistent compiler ⭐ high value/low risk
- **Where:** `compile_expr_to_cm_ir_persistent` recursion hashes *every subtree on every compile
  call* ([`cm_ir.py:186`](cm_ir.py) calls `expr_structural_hash`, 95–154, blake2b). This is
  redundant with the intern table, and blake2b over each subtree scales with tree size.
- **Hypothesis:** memoize the structural hash on the `Expr` (or compute it bottom-up once, reusing
  child digests instead of re-serializing the whole subtree) → large drop in persistent-compile
  time on cache-miss builds.
- **Measure:** `ir_compile_time_s` and wall time with `--cm-use-persistent-cache` on a
  *family* workload (`--bench-expression-family`), plus `ir_persistent_cache_*`.
- **Payoff:** medium-high on family/related workloads (the flagship reuse scenario). **Risk:** low
  — hashing is pure; just don't change the digest value (would invalidate cache semantics/tests).

### A2. O(n²) negation scan in `make_and` / `make_or`
- **Where:** `any(self._is_negation_of(node, prev) for prev in out)` at
  [`cm_ir.py:470`](cm_ir.py) and [`cm_ir.py:520`](cm_ir.py) — quadratic in operand count for
  wide associative nodes.
- **Hypothesis:** track negation partners in a `set` of child keys (a node and its negation have
  related keys) → O(n) annihilation detection.
- **Measure:** `ir_rewrite_time_s` / `canonical_rewrites` on wide AND/OR expressions
  (`--expr-style and_or_not`, higher `--max-depth`).
- **Payoff:** low-medium (only bites wide flat operators). **Risk:** low, but must preserve
  the `x ∧ ¬x → 0` / `x ∨ ¬x → 1` folding exactly.

### A3. Canonicalization sort cost
- **Where:** `_canonicalize_commutative_args` ([`cm_ir.py:426`](cm_ir.py)) does
  `sorted(out, key=lambda n: n.key)` for every commutative build; sorting by full tuple `key` is
  comparatively expensive and runs a lot.
- **Hypothesis:** sort by a cheap precomputed scalar (e.g. an integer id assigned at intern time)
  instead of the nested tuple key; or skip the sort when args are already ordered.
- **Measure:** `ir_canonicalize_time_s` / `ir_canonicalize_calls`.
- **Payoff:** low-medium. **Risk:** medium — the sort *defines* canonical form used by interning
  and the structural cache; any change must keep the equivalence classes identical (tests guard).

### A4. Per-node live-vars rebuild during materialize
- **Where:** [`cm_ir.py:1107`](cm_ir.py) rebuilds `live_vars` with a genexpr filtering `fixed_map`
  on *every* `rec` call, even when `fixed` is empty (the common case).
- **Hypothesis:** short-circuit to `cur.vars` when `not fixed_map`; cache `live_vars` on the memo
  entry. Also `_fixed_key_for_node` ([`cm_ir.py:929`](cm_ir.py)) iterates `node.vars` to build the
  memo key every call — skip when `fixed` empty.
- **Measure:** cached-exec `var_order`/`dispatch` columns; overall cached per-eval.
- **Payoff:** small but touches the hottest loop (helps Tier B too). **Risk:** low.

---

## TIER B — CM-node bitset evaluator (helps the cached/flagship regime) ⭐⭐

This is the **single most important target for the flagship compile-once/eval-many story.** In the
cached profile (HANDOFF §3.1), `bitset_eval` is 55.3 of 63.7 µs at n=16 — i.e. *after* compile is
amortized, the residual gap to raw bitset is mostly **`eval_cm_node_bitset`** itself, not the
scaffolding around it.

### B1. Profile and specialize `eval_cm_node_bitset`
- **Where:** [`bitset_backend.py`](bitset_backend.py) `eval_cm_node_bitset(node, live_vars,
  fixed=...)` — recursive CMNode walk producing a packed Python-bigint truth table, with per-node
  `memo`. Called from [`cm_ir.py:1000`](cm_ir.py) and [`cm_ir.py:1475`](cm_ir.py).
- **Why slower than `eval_expr_bitset`:** the CM-node path rebuilds env / re-walks a DAG and does
  Python-level op dispatch per node; the raw bitset baseline (`eval_expr_bitset`) is a tighter AST
  walk. Quantify the delta first — it's the ceiling on how much B can win.
- **Hypotheses to try (in order):**
  1. Ensure the per-node `memo` fully exploits DAG sharing (interned nodes should hit once).
  2. Hoist `build_bitset_env` / the variable-column masks out of the hot recursion; reuse across
     the `--cm-eval-repeat` loop instead of per-eval.
  3. Replace recursive dispatch with an iterative postorder over a *flattened* node list (see C1 —
     B and C1 converge here).
  4. For small `live_k`, the bigint width is `2^live_k` bits; check whether NumPy `uint64`-packed
     ops beat Python bigint at the sizes that actually occur (live_k ≤ ~9 per the diagnostics).
- **Measure:** `nr_bitset_eval_time_s`, `cached_exec_bitset_eval_time_s`, ratio vs
  `bitset_cached_exec_only_time_s`.
- **Payoff:** **high** — directly narrows the flagship 2.1–2.4× cached gap at n=16. **Risk:**
  medium — this is the correctness-critical kernel; bit-exact output required.

### B2. Reuse the compiled bitset env across the eval-repeat / cached loop
- **Where:** env construction inside the bitset kernel + the cached-exec loop in `cm_bench.py`
  (`--cm-eval-repeat`). `build_bitset_env` is already `lru_cache`d by var tuple, but confirm the
  cached path isn't paying env setup per eval.
- **Measure:** `cached_exec_fixed_handling_time_s`, `cached_exec_other_time_s`.
- **Payoff:** medium. **Risk:** low.

---

## TIER C — Flatten / codegen the IR evaluator (the structural bet) ⭐⭐⭐

Named as the top future direction in the pre-writing report ("flattening/codegen/JIT would likely
help by removing recursive IR traversal and wrapper dispatch") and the no-reinflation report. This
is the **highest-ceiling, highest-effort** item — it attacks Tier B's dispatch *and* the wrapper
scaffolding at once.

### C1. Compile a `CompiledExpr` into a flat execution program
- **Idea:** lower the interned DAG into a linear postorder array of `(opcode, arg_slot_a,
  arg_slot_b, out_slot)` instructions (exactly what `numba_backend.flatten_expr_numba` already does
  for the *Expr* AST — steal that shape for the *CMNode DAG*). Execute with a tight loop over
  slots, no Python recursion, no per-node tuple/key allocation, no `if/elif kind==` ladder
  ([`cm_ir.py:1138-1314`](cm_ir.py)).
- **Two backends to prototype:**
  - **(a) Interpreted flat loop** — pure Python/NumPy over the instruction array. Removes recursion
    + dispatch overhead; low dependency risk; measurable immediately.
  - **(b) Numba/codegen** — `@njit` the flat loop (the repo already has an optional numba dep and a
    working stack-machine in `numba_backend.py`). Amortizes JIT across the compile-once/eval-many
    loop — a natural fit for the cached regime.
- **Where it plugs in:** `evaluate_compiled` ([`cm_ir.py:807`](cm_ir.py)) currently only supports
  `mode="hybrid_no_reinflate"`; add `mode="flat"` (or a `CompiledExpr.program` field cached
  alongside `.node`). Keep the existing path as the reference.
- **Measure:** cached per-eval vs bitset-cached at n=12,16; `cached_exec_dispatch_time_s` should
  collapse. Compare interpreted-flat (a) vs numba-flat (b).
- **Payoff:** potentially closes most of the remaining cached gap; also the cleanest asymptotic
  story for the paper. **Risk:** high effort; must reproduce no-reinflate repr codes (1–4) and the
  reduced-output guard exactly. Land it behind a flag with a correctness sweep vs `eval_expr_tt`.

### C2. Cut per-node allocation in the current recursive path (incremental toward C1)
- **Where:** memo keys `(cur, fixed_key, bool)` at [`cm_ir.py:1098`](cm_ir.py) and builder `key`
  tuples allocate per node → GC pressure on large DAGs. The align/combine loops
  ([`cm_ir.py:1193-1235`](cm_ir.py)) allocate a fresh NumPy array per `_serial_combine`.
- **Hypothesis:** intern integer node-ids and key on `(node_id, fixed_key)`; reuse output buffers
  in the numpy combine path (write into a preallocated array where shape allows).
- **Measure:** cached per-eval, allocation counts (optional tracemalloc probe).
- **Payoff:** medium; de-risks C1 by proving the allocation thesis first. **Risk:** medium.

---

## TIER D — Reduced-output / large-n execution (extends feasibility) ⭐⭐

The large-n story rests on **reduced live-var output** (repr code 3): at n=32 only ~5 output vars
materialize. Runtime tracks reduced structure, not nominal n (`CM_final_robustness_report.md`).
This is where CM can avoid a full `2^n` output by explicitly returning a reduced live-variable
representation.  A naive nominal-width bitset would build `2^n`, but a fair bitset baseline can
traverse the AST once, discover the same live-variable scope, and evaluate only that scope.

### D1. Optimize the reduced-output packed-bitset path
- **Where:** `materialize_hybrid_no_reinflate` reduced-output branch,
  [`cm_ir.py:1447-1525`](cm_ir.py); guard at [`cm_ir.py:1461`](cm_ir.py).
- **Hypothesis:** the reduced path still routes through `eval_cm_node_bitset` over `output_vars`;
  the same B1/C1 wins apply. Quantify both capability versus a nominal-width baseline and speed
  versus a fair matched-scope flat bitset; do not conflate those comparisons.
- **Measure:** run `--large-n-safe --sizes 16,20,24,28,32`; report cached ratio *and* an
  explicitly labeled nominal-width comparison plus a matched-scope flat-bitset comparison
  (if the former is disabled above the full-TT cap, say so rather than silently skipping it).
- **Payoff:** this is the **strongest large-n narrative** and directly supports the paper's
  "larger-n validation" open question. **Risk:** medium — keep the anti-materialization guard;
  never enumerate 2^n.

### D2. Stress-style expressions (low reducibility)
- **Where:** `--expr-style {broad,low-reuse,anti-reduction}` retain 16 live vars through n=32 and
  run materially slower (cached ratios up to 8.4× at n=16). These are the adversarial cases.
- **Hypothesis:** identify whether any structural pass (better CSE, XOR canonicalization, factoring)
  reduces live vars on these styles. If not, document the honest ceiling.
- **Payoff:** either a real win or a clean negative result for the paper. **Risk:** low (analysis).

---

## TIER E — Longer-horizon / research bets (scope before committing)

- **E1. Packed-cell / block-encoded CM.** Let CM cells hold words/bitsets instead of single bools
  (named in the no-reinflation report as a "future paper / major architecture revision"): fewer
  outer axes, richer per-cell payload, tighter CM↔bitset integration, less broadcast/reinflate
  overhead. High ceiling, high effort; prototype on 2×2/4×4 blocks first.
- **E2. Cost model for mode/backend selection.** The proven fix for partial-hybrid and the
  precondition for the paper's "automatic backend routing." Replace threshold-only selection with a
  model over `live_k`, DAG shape, expected conversions, and reuse. Start descriptive (fit a model
  to existing CSVs) before making it drive dispatch.
- **E3. Pair-aware token path at scale.** `cm_build_pair.py` composes 2-var subtrees in O(1) via
  LUTs ([`cm_token.py`](cm_token.py)). It currently falls back to the standard compiler for
  non-pairable nodes and reinflates to a full matrix. Investigate a *no-reinflate* pair path and
  whether the O(1) token composition can carry deeper into the DAG.
- **E4. Canonical CM structural equivalence.** Not a speedup, but the paper's biggest credibility
  gap: current equivalence is *output-based*, not canonical. If you build a real canonical-basis
  equivalence layer, it changes the equivalence story (and unlocks reuse-by-canonical-form).
- **E5. CUDD-in-Docker baselines.** The "first priority" open question in the deck: run CUDD
  *canonical equivalence* (not just build/extract) in Docker/Linux so the symbolic comparison is
  fair. Infra, not a CM speedup, but it's the missing baseline everyone will ask about.

---

## Suggested first two weeks

1. **Instrument-confirm the regime split** — rerun the canonical profile command, reproduce
   HANDOFF §3.1 on this machine, confirm compile-dominant (one-shot) vs bitset-eval-dominant
   (cached). *(half day)*
2. **Land A1 + A4** (structural-hash memoization + empty-fixed short-circuit) — low risk, immediate
   compile/first-touch wins, builds familiarity with the builder and cache. *(2–3 days)*
3. **Deep-profile `eval_cm_node_bitset` (B1)** — this is the flagship bottleneck; quantify the
   delta vs `eval_expr_bitset` and try env-hoisting + memo/DAG-sharing before anything structural.
   *(3–4 days)*
4. **Prototype C1(a), interpreted flat evaluator** behind `mode="flat"`, correctness-swept vs
   `eval_expr_tt` — decide whether the numba path (C1b) is worth it based on the interpreted win.
   *(1 week)*

Every change: keep 159/159 tests green, keep correctness outside timed windows, and report which
*regime* moved. If a target turns negative, that's a paper-grade result too — record it in a
short `CM_speedup_<target>_report.md` the way the existing reports do.
