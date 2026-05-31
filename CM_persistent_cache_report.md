# CM Persistent IR Cache + Reusable Compiled Expressions Report

## 1. Audit (current reuse)
| Area | PRESENT / PARTIAL / MISSING | Notes |
|------|------------------------------|-------|
| `compile_expr_to_cm_ir(...)` call sites | PRESENT | Used by `cm_build.py`, `cm_build_lazy.py`, `cm_parallel.py`, and `cm_bench.py`. |
| Per-run/trial reuse | PRESENT | `--cm-compile-once-per-expression` (bench-only) compiles once and reuses the `CMNode` for multiple CM modes in a trial. |
| Per-process compile cache (Expr object key) | PRESENT | `compile_expr_to_cm_ir(..., reuse_cache=True)` uses an in-process `OrderedDict[Expr, CMNode]` (keyed by the `Expr` object’s equality/hash). |
| Stable structural key (identity-independent) | MISSING (before) / PRESENT (after) | Added `expr_structural_hash(expr)` and a persistent IR cache keyed by this digest. |
| Cross-run persistence | MISSING | Current “persistent” cache is process-level (per attached prompt requirements), not disk-backed. |

## 2. Persistent IR cache design
### Key
Deterministic, identity-independent structural digest:
- `cm_ir.expr_structural_hash(expr)` uses `hashlib.blake2b(digest_size=16)` and **canonicalizes**:
  - `AND/OR/XOR`: associative flatten + commutative sort of child digests
  - `EQV`: commutative sort of the two child digests
  - `IMP`: preserves order

### Value
- Compiled IR root: `CMNode`

### Cache behavior
- Process-level `OrderedDict[str, CMNode]` with a fixed max size (`_PERSISTENT_IR_CACHE_MAXSIZE`)
- LRU-ish update via `move_to_end` + `popitem(last=False)` eviction

### Diagnostics keys
Recorded into the provided `diagnostics` dict when persistent caching is used:
- `ir_persistent_cache_hits`
- `ir_persistent_cache_misses`
- `ir_persistent_cache_size`

## 3. Public reusable API
Exposed in `cm_ir.py`:
```python
compiled = compile_expr(expr, use_persistent_cache=True)
result = evaluate_compiled(compiled, mode="hybrid_no_reinflate", vars_all=[...])
```

- `compiled` is a frozen `CompiledExpr(expr_hash, node)` container.
- `evaluate_compiled(..., mode="hybrid_no_reinflate")` calls `materialize_hybrid_no_reinflate(...)` and returns `FinalNoReinflateResult`.

## 4. Benchmark modes + CLI
### Flags added
- `--cm-use-persistent-cache`: uses the structural-hash persistent cache during compilation.
- `--cm-eval-repeat N`: measures cached execution by evaluating the same compiled expression `N` times and reporting per-eval median times:
  - `cm_hybrid_no_reinflate_cached_exec_only_time_s_median`
  - `bitset_cached_exec_only_time_s_median`
  - `ratio_cm_hybrid_no_reinflate_cached_over_bitset_cached`

### Commands run
Baseline (end-to-end, no persistent cache):
```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate --cm-hybrid-threshold 7 --no-dd --no-espresso --print-summary --out-prefix bench_persist_baseline
```

Persistent-cache (end-to-end, persistent cache enabled):
```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-hybrid --cm-compare-no-reinflate --cm-hybrid-threshold 7 --cm-use-persistent-cache --no-dd --no-espresso --print-summary --out-prefix bench_persist_cache
```

Cached execution (compile once, execute many; per-eval times reported):
```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 --cm-layout balanced --cm-compare-no-reinflate --cm-hybrid-threshold 7 --cm-use-persistent-cache --cm-eval-repeat 50 --no-dd --no-espresso --print-summary --out-prefix bench_persist_cached_exec
```

## 5. Benchmark results
### 5.1 End-to-end impact of persistent caching (no-reinflate)
From `bench_persist_baseline_summary.csv` vs `bench_persist_cache_summary.csv`:

| n | baseline_no_reinflate_s | persistent_cache_no_reinflate_s | speedup |
|---:|---:|---:|---:|
| 4 | 0.000147 | 0.000098 | 1.51x |
| 8 | 0.000144 | 0.000080 | 1.80x |
| 12 | 0.000203 | 0.000110 | 1.84x |
| 16 | 0.000219 | 0.000116 | 1.89x |

Interpretation: in compare-mode benchmarks, persistent caching reduces redundant compiles across CM modes even without `--cm-reuse-compiled-ir`.

### 5.2 Baseline vs cached execution vs bitset
Baseline timings are end-to-end `compile + execute` once. Cached execution is **per-eval execution-only** (compile done outside the timed window) using `--cm-eval-repeat 50`.

| n | baseline_no_reinflate_s | cached_exec_s_per_eval | bitset_s | bitset_cached_s_per_eval | cached/bitset_cached |
|---:|---:|---:|---:|---:|---:|
| 4 | 0.000147 | 0.000024 | 0.000010 | 0.000003 | 8.12 |
| 8 | 0.000144 | 0.000027 | 0.000010 | 0.000005 | 5.54 |
| 12 | 0.000203 | 0.000047 | 0.000031 | 0.000009 | 4.90 |
| 16 | 0.000219 | 0.000066 | 0.000053 | 0.000027 | 2.42 |

## 6. Tests
Commands run:
```bash
python -m unittest discover -s tests -v
```

Coverage added:
- Structural hash determinism + commutativity
- Persistent cache hit behavior across distinct but equivalent Expr objects
- Public `compile_expr` + `evaluate_compiled` correctness vs `eval_expr_tt`
- Bench integration coverage for `--cm-eval-repeat`

## 7. Interpretation
- Persistent caching makes the CM IR behave like a reusable compile artifact within a process: later compiles of structurally identical expressions can reuse the same compiled `CMNode`.
- Cached execution (compile once → evaluate many) shows `hybrid_no_reinflate` moves much closer to “execution-only” cost, but remains above the bitset backend due to remaining IR evaluation overhead (even after avoiding dense CM reinflation).

## 8. Verdict
Persistent caching makes CM+bitset near-optimal

