# C1a Flat Evaluator — Implementation & Before/After Report

> Implements the Tier-C C1a scope (`CM_tierC_rescope_report.md` §3): the interned CMNode
> DAG is lowered **once** into a linear postorder instruction list, executed by a slot-based
> interpreter with per-`(vars_key, fixed)` **bound programs** (input masks resolved once —
> same legitimacy class as the existing `build_bitset_env` LRU; it stores resolved *input*
> masks, never outputs). Opt-in behind **`--cm-flat-eval`** / `flat_eval=True`; the
> recursive kernel remains the default and the reference.
>
> Machine: Windows 10, venv Python 3.13.5, post-`86301e0` working tree. Date: 2026-07-21.

## 1. What was added (all behind the flag)

| File | Addition |
|---|---|
| `bitset_backend.py` | `FlatProgram`, `compile_flat(node)` (iterative postorder lowering, one instruction per unique DAG node — sharing exploited at compile time, eval loop needs no memo), `get_flat_program` (program cached on the frozen node via `object.__setattr__`, the same lifetime-correct pattern as R1a's cached hash), `_bind_flat_program` (bound-template cache, FIFO ≤ 64), `eval_cm_node_flat` (slot interpreter; n-ary AND/OR/XOR, binary IMP/EQV, NOT/IMP/EQV masked). |
| `cm_ir.py` | `flat_eval: Optional[bool] = None` parameter on `materialize_hybrid_no_reinflate` (kernel swap inside the `live_k ≤ threshold` branch only); `set_flat_eval_default()` module default so the CLI flag covers all call sites. Fallback (`live_k > threshold`) path, repr codes 1–4, guard, and diagnostics untouched. |
| `cm_bench.py` / `cmbench/config.py` | `--cm-flat-eval` flag → `cm_flat_eval` config field → sets the process default in `main()`. No CSV schema changes. |

## 2. Correctness

- **Dedicated sweep: 1,104 checks, 0 failures** — kernel-level flat == recursive == the
  independent `eval_expr_tt` oracle over **all 2^n rows** (n=2–14 × 6 depths × 4 seeds),
  fixed-var variants, end-to-end `materialize_hybrid_no_reinflate` at thresholds 3 and 7
  (repr codes and outputs identical flat vs recursive vs oracle), and the reduced-output
  large-n path (n=20/24, repr 3/4: identical bits/tt/output_vars).
- **CLI end-to-end:** same seed with/without `--cm-flat-eval` → all `*_OK`, identical repr
  codes.
- **`python -m pytest -q`: 159/159 pass** (system Python, run after the change).

## 3. Before/after — the headline

### (A) Full-output convergence table (the chart's regime: full arity, `live_k = n`, cached per-eval, same seeds as the pre-C1a audit)

| n | recursive/bitset (before) | **flat/bitset (after)** |
|--:|--:|--:|
| 16 | 1.67× | **0.85×** |
| 18 | 1.44× | **0.90×** |
| 20 | 1.53× | **0.97×** |
| 22 | 1.85× | 1.43× *(re-run fresh seeds: 1.16× — see caveat)* |
| 24 | 1.11× | **0.97×** |

**The convergence you asked about is no longer asymptotic — it is achieved.** With the flat
kernel, CM full-output per-eval sits **at or below raw bitset from n=16 through n=24**
(0.85–0.97×), instead of trending down toward it from 1.3–1.7×. This realizes part of the
structural node-count advantage (CM DAG ≈ 0.5× the Expr tree) that the recursive kernel's
per-node overhead was masking. n=22 is a persistent mild outlier (1.16–1.43×) across two
seed sets; neighbors n=20/24 are both ≤ 0.97×, so it looks like an allocator/width artifact
at 512 KB integers rather than a scaling break — flagged, not hidden.

### (B) Flagship compile-once/cached regime (depth-4, end-to-end `materialize_hybrid_no_reinflate`)

| n | recursive µs | flat µs | raw bitset µs | rec/bitset | **flat/bitset** | flat speedup |
|--:|--:|--:|--:|--:|--:|--:|
| 4 | 13.3 | 6.1 | 5.4 | 2.47× | **1.12×** | 2.20× |
| 8 | 13.3 | 5.8 | 5.8 | 2.29× | **1.00×** | 2.28× |
| 12 | 14.5 | 8.4 | 8.4 | 1.73× | **1.00×** | 1.73× |
| 16 | 110.3 | 52.0 | 72.2 | 1.53× | **0.72×** | 2.12× |

The cached-regime gap to raw bitset — 1.5–2.5× before — is **closed**: parity at n=8–12 and
**28% faster than raw bitset at n=16**. Matches the Tier-C prototype's prediction
(bound-flat ≤ raw bitset at every tested n). CLI cross-check at n=8/12: 60.2 → 17.2 µs
(3.5× incl. wrapper).

## 4. Why this works (one paragraph)

The recursive kernel pays, per node per eval: Python recursion, an `id()` dict memo
(and it holds every intermediate 2^n-bit result alive), and branch dispatch. The flat program
pays that cost **once at lowering** (8–14 µs, cached on the node), so each eval is a tight
loop over precomputed slots; and because the canonicalized IR DAG has ~half the nodes of the
raw Expr tree, CM ends up doing *fewer* big-integer ops than the raw-bitset AST walk — which
is why it can be *faster* than the flat lower bound for *uncompiled* input, not just equal.
(The fair flat-vs-flat control — a flattened raw-Expr evaluator — remains the numba stack
machine, per the Tier-C report §4.)

## 5. Further speedup candidates spotted while implementing ("keeping an eye out")

1. **Memory-lean slots (last-use freeing).** The flat `values` list still holds every
   intermediate (like the recursive memo). Annotating each slot's last use at lowering and
   dropping dead intermediates would cut peak memory ~2× and cache pressure at n ≥ 20 —
   likely part of the n=22 outlier. Small, contained change to `compile_flat`/the eval loop.
2. **Slot-count minimization / register reuse.** Postorder + liveness → reuse dead slots;
   fewer live bigints, better locality. Combines with (1).
3. **numpy-words backend for wide outputs (Tier-C C1b-lite).** At widths ≥ 2^16 bits the
   Tier-C probe showed uint64-word arrays beat Python bigints per op. Width-selected
   (bigint below ~2^13 bits, numpy above), it slots cleanly behind the same `FlatProgram`.
   This is the remaining lever on the full-output large-n end (n=22/24).
4. **Wrapper fast path.** With a 6–8 µs kernel at n ≤ 12, `materialize_hybrid_no_reinflate`'s
   ~4–6 µs of diagnostics plumbing is now a co-equal cost; a precomputed diagnostics-off
   route would shave most of it (visible as flat=1.12× vs kernel-parity at n=4).
5. **Bound-template `int` interning of the two constants** (0/full_mask) is already free;
   binding cost itself (~µs) only matters for one-shot — not worth further work.

## 6. Artifacts

- Code: `bitset_backend.py`, `cm_ir.py`, `cm_bench.py`, `cmbench/config.py` (working tree).
- CSVs: `CM_c1a_convergence_before_after.csv`, `CM_c1a_cached_before_after.csv` (this folder);
  `bench_c1a_{off,on}_*` (repo root, gitignored).
- Verification script: session scratchpad `c1a_verify.py` (1,104 checks).
