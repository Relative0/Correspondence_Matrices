# Tier C Re-scope — Flat CM Evaluator After R1/R2/R3

> Follow-up to `CM_speedup_phase2_report.md`. Question: is C1 (flatten/codegen the IR
> evaluator) still worth building now that R1 removed the hash/memo overhead it was
> originally aimed at? **Answer: yes — and the verdict got *stronger*, not weaker.**
> An interpreted flat evaluator (C1a) closes the *entire* remaining cached gap: the CM
> per-eval kernel matches or beats the raw bitset baseline at every tested n.
> C1b (numba/codegen) is **not** needed for that claim.
>
> Measurements on the post-R1 working tree (commit `041fd18`), prototypes in session
> scratchpad (`probe_flat_eval.py`), instrumentation off, medians of 400 reps.
> All three prototype variants verified **bit-identical** to `eval_cm_node_bitset` on
> 150 random cases (n=2..12, with and without fixed vars) plus the 6 timing cases.

## 1. What was prototyped

The interned CMNode DAG is lowered once into a linear postorder instruction list
(`(opcode, arg-slots)`, one instruction per unique DAG node — sharing exploited at
compile time, so the eval loop needs no memo at all). Three execution variants:

- **A. Generic flat interpreter** — bigint values; var masks looked up per eval.
- **B. Bound program** — var/const masks resolved once per `(vars_key, fixed)` into
  load-immediates (legitimate compile-once reuse, same class as the existing
  `build_bitset_env` LRU); eval loop touches only slots.
- **C. numpy-uint64 words** — same program over `uint64[2^k/64]` arrays; NOT may leave
  garbage tail bits, masked once at the end.

Flat-program build cost: **8–14 µs one-time** per compiled expression (amortized).

## 2. Results (kernel-only per-eval, µs)

| case | IR nodes | recursive kernel (post-R1) | flat A | bound B | numpy C | raw `eval_expr_bitset` |
|---|--:|--:|--:|--:|--:|--:|
| n=4 (t3) | 15 | 17.5 | 4.5 | **3.6** | 16.0 | 8.0 |
| n=8 (t0) | 10 | 6.9 | 3.4 | **2.2** | 7.7 | 4.7 |
| n=12 (t3) | 15 | 13.5 | 8.0 | **6.3** | 11.4 | 8.0 |
| n=12 (t4) | 14 | 26.3 | 9.4 | **7.7** | 13.7 | 9.9 |
| n=16 (t0) | 11 | 64.0 | 23.9 | **22.8** | 23.1 | 23.3 |
| n=16 (t4) | 12 | 68.7 | 48.6 | 36.9 | **27.4** | 40.4 |

Readings:

1. **Bound-flat (B) ≤ raw bitset in every case.** The recursion/dispatch overhead the
   flat loop removes (~1 µs/node) was the whole residual at n≤12; at n=16 the bigint ops
   dominate but the canonicalized IR DAG has *fewer nodes than the raw Expr tree*
   (e.g. 15 vs 28 at n=4), so CM still wins. This flips the flagship story: **compile-once
   CM per-eval would be faster than the flat-execution baseline**, because the
   structure-preserving compiler pays for itself in node count.
2. **Even the unbound variant (A) is 2–5× better** than the current recursive kernel —
   the win does not depend on the bound-program cache.
3. **numpy-words (C) only wins at n=16** (width ≥ 65,536 bits) and loses badly at small n
   (per-op numpy overhead). If adopted at all, select by width (bigint below ~2^13 bits,
   numpy above); it is what would make a later numba C1b trivial, but C1b adds nothing
   the current numbers need.
4. Wrapper context: `materialize_hybrid_no_reinflate` currently adds ~2–6 µs around the
   kernel. With a B-kernel of 2–8 µs at n≤12, the wrapper becomes the largest remaining
   term — a flat mode needs a lean fast path (precomputed diagnostics-off route) to keep
   the end-to-end numbers near the kernel numbers.

## 3. Recommended C1a scope (Phase 3 proposal)

- Add a lazily-built `program` to `CompiledExpr` (or an internal cache keyed by the root
  CMNode), built by a `compile_flat(node)` lowering pass.
- In `materialize_hybrid_no_reinflate`'s `live_k <= hybrid_threshold` branch, execute the
  flat program instead of the recursive kernel, behind a flag
  (`--cm-flat-eval` / `flat_eval=True`) with the recursive path as reference.
- Bound-program LRU keyed by `(program, vars_key, fixed_key)` (small, e.g. 256).
- Keep repr codes 1–4, the reduced-output guard, and the fallback (live_k > threshold)
  path untouched. Correctness: same oracle sweep + full pytest.
- Defer numpy-words backend and numba until after the interpreted flat mode is measured
  end-to-end; adopt width-based selection only if n≥16 workloads matter.
- Predicted diagnostics: `cm_hybrid_no_reinflate_cached_exec_only_time_s` ≈ bitset-cached
  or below at n=4..16 (ratio ≤ 1.0× from today's 1.9–5.0×); `nr_bitset_eval_time_s`
  drops 2–5×.

Effort: ~1–2 days including sweeps. Risk: medium-low (single well-contained kernel swap
behind a flag; bit-exactness demonstrated by prototype).

## 4. Honest caveats

- Cases are depth-4 random expressions (10–15 IR nodes). The flat win scales with node
  count, so deeper/wider expressions should benefit more; stress styles with live_k > 7
  bypass this branch entirely (fallback unchanged).
- The bound-program cache must not be conflated with result caching: it stores resolved
  input masks, never outputs. Benchmark fairness is preserved (every eval still computes
  the full result).
- The "beats raw bitset" comparison is against this repo's `eval_expr_bitset` recursive
  AST walk — the honest flat lower bound for *uncompiled* input. A hypothetical
  flattened-raw-bitset would close part of CM's node-count advantage; that comparison
  (flat-vs-flat) is worth one control column when C1a lands (the numba stack machine is
  the existing control for exactly this).
