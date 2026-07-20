# CM Speedup Phase 2 — R1/R2/R3 Implementation Report

> Implements the three approved targets from `CM_speedup_investigation_phase1.md`.
> All changes are **output-identical** (no flags needed: hash values, digests, and env masks
> are byte-for-byte unchanged; only *when/how often* they are computed changed).
> Machine: Windows 10, Python 3.10.11, base commit `af23e8a`. Date: 2026-07-20.

## 1. Changes

| ID | File | Change |
|---|---|---|
| R1a | [cm_ir.py](cm_ir.py) `CMNode` | Explicit `__hash__` producing the identical dataclass-generated value, computed once and cached on the instance (`_cached_hash` via `object.__setattr__`). `__eq__` untouched. |
| R1b | [bitset_backend.py](bitset_backend.py) `eval_cm_node_bitset` | Per-call memo keyed by `id(node)` instead of the node (O(1) vs O(subtree) per lookup; nodes are alive for the whole call). |
| A4 | [cm_ir.py](cm_ir.py) `materialize_hybrid_no_reinflate` + `_materialize_ir_tagged.rec` | `live_vars = node.vars` short-circuit when `fixed` is empty. |
| R2 | [cm_ir.py](cm_ir.py) | Digest logic hoisted to module-level `_structural_digest(e, memo)`; `expr_structural_hash` unchanged in output; `compile_expr_to_cm_ir_persistent` shares **one** digest memo across the whole build → each subtree hashed once (was quadratic). |
| R3 | [bitset_backend.py](bitset_backend.py) `_build_bitset_env_cached` | numpy `packbits` mask construction for `n_vars > 10`; original loop kept below (faster at small n). Identical env dicts. |

Environment note: `.venv` needed `requests` (cm_bench import chain) — installed 2.34.2.
Tests were run with system Python (`python -m pytest -q`), which is where pytest lives;
the venv has no pytest.

## 2. Correctness

- **`python -m pytest -q`: 159 passed** (161 s).
- **Post-change oracle sweep vs `eval_expr_tt`: 2,856 checks, 0 mismatches** — 6 expression
  styles × n∈{2..14} × 6 trials, covering: no-reinflate at thresholds 3 and 7; dense
  `materialize_cm` in `numpy`/`hybrid`/`partial_hybrid`; fixed-var evaluation; the
  persistent-compile path (node keys identical to plain build); and the reduced-output
  large-n path (repr code 3, n=20/24, 200 sampled assignments each).
- Invariant spot-checks: cached hash equals the generated dataclass hash; numpy env equals
  the loop env at n=11/12/14; persistent-cache keys unchanged.
- The `--cm-max-full-output-vars` guard and all modes/diagnostics untouched.

## 3. Measured results

### Controlled A/B (git-worktree of HEAD vs new code, 3 interleaved rounds, medians, instrumentation off)

Cached per-eval `materialize_hybrid_no_reinflate` (compile-once regime):

| case | HEAD µs | new µs | Δ |
|---|--:|--:|--:|
| n=4 (live_k=4) | 114.4 | 22.6 | **−80%** |
| n=8 (live_k=5) | 48.2 | 14.0 | **−71%** |
| n=12 (live_k=7) | 76.4 | 24.8 | **−68%** |
| n=12 (live_k=5) | 84.8 | 31.2 | **−63%** |
| n=16 (live_k=4) | 153.7 | 114.5 | −26% |
| n=16 (live_k=5) | 185.6 | 149.1 | −20% |

Cold persistent compile: n=4 −53%, n=8 par (noise; tiny expr), n=12 −11%, n=16 −17%.
(Absolute "new" times match the Phase-1 prototype predictions; percentage deltas vs the
Phase-1 tables differ because HEAD itself measured faster in the A/B session.)

Env-build first touch: n=14: 14.3→1.1 ms; **n=16: 138.8→6.8 ms; n=18: 1525→37 ms**.

### Canonical benchmark (HANDOFF §4.1 command), before = `bench_profile_fable_*`, after = `bench_profile_fable_after_*`

Cached per-eval and ratio vs bitset-cached:

| n | before µs | after µs | ratio before | ratio after |
|--:|--:|--:|--:|--:|
| 4 | 78 | 38 | 17.9× | **5.0×** |
| 8 | 62 | 31 | 5.7× | **3.1×** |
| 12 | 165 | 66 | 8.2× | **2.1×** |
| 16 | 225 | 133 | 2.6× | **1.9×** |

One-shot no-reinflate medians: 257→148 µs (n=4), 241→141 (n=12), 306→167 (n=16);
`nr_bitset_eval_time_s` medians: 82→31, 50→26, 129→48, 170→87 µs. `NoReinflate/Bitset`
one-shot ratio at n=16: 3.7×→**1.9×**. All `*_OK` columns OK.

**Which regime moved:** R1a/R1b/A4 moved the cached/compile-once regime (the flagship),
2.6–4.9× per-eval; R2 moved one-shot/first-touch compile (biggest on larger exprs; par on
tiny ones); R3 removed a first-touch cliff that grows exponentially in the env width.

## 4. Residual picture

At n≤12 the remaining cached gap to raw bitset is ~2–3× and is now mostly wrapper
scaffolding + per-node Python dispatch (tens of µs). At n=16 the residual is genuine
2^16-bit bigint arithmetic; ratio 1.9× and unlikely to close much further without
reduced-output usage. Tier C (flat evaluator) should be re-scoped against these new,
much smaller baselines before committing effort.

## 5. Artifacts

- Code: `cm_ir.py`, `bitset_backend.py` (working tree, uncommitted).
- CSVs: `bench_profile_fable_{raw,summary}.csv` (before),
  `bench_profile_fable_after_{raw,summary}.csv` (after).
- Sweep/probe scripts in session scratchpad (`sweep_post_change.py`, `ab_micro.py`, …).
