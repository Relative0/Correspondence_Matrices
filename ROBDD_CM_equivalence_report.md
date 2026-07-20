# ROBDD / CM Boolean Equivalence Report

## 1. Executive Summary

Native Windows results cover `dd.autoref`, bitset packed truth-table comparison, CM no-reinflate output comparison, and SymPy. `dd.cudd` is not importable in this environment (`importlib.util.find_spec("dd.cudd")` returned `None`), so no CUDD numbers are claimed here.

For these small exact-truth-table-safe sizes (`n=4,8,12,16`), bitset is fastest overall because full packed outputs are cheap at this scale. ROBDD/autoref is competitive and shows the expected canonical-equivalence shape: comparison itself is effectively free after BDD construction, around 0.16 to 0.21 microseconds per repeated compare. CM no-reinflate is correct but currently pays compile plus output-evaluation cost; its compare step is also tiny, but it is not yet a canonical structural equivalence method.

## Phase 1 Audit

| Capability | Present / Missing | Evidence | Plan |
| ---------- | ----------------- | -------- | ---- |
| dd-backed ROBDD build | Present | `cm_bench.py`: `select_dd_module`, `expr_to_dd_bdd`, `run_robdd_dd_backend` | Reused same manager/order for pair equivalence. |
| `dd.autoref` fallback | Present | `select_dd_module("auto")` falls back to `dd.autoref` | Tested native Windows autoref smoke runs. |
| `dd.cudd` backend | Optional / unavailable here | `find_spec("dd.cudd")` returned `None` | Keep backend separated; do not claim CUDD results. |
| Bitset packed evaluation | Present | `bitset_backend.py`: `build_bitset_env`, `eval_expr_bitset` | Compare packed integer outputs. |
| CM no-reinflate path | Present | `cm_ir.py`: `compile_expr`, `evaluate_compiled`, `materialize_hybrid_no_reinflate` | Compare no-reinflate payloads (`bits` or `tt`). |
| Structural CM hash | Present but not semantic | `cm_ir.py`: `expr_structural_hash` | Record diagnostics; do not use as equivalence oracle. |
| SymPy support | Optional / present here | `expr_simplify.py`: `_to_sympy`, `simplify_via_sympy` | Use XOR simplification as optional backend. |
| Pair generation | Added | `generate_equiv_pair` in `cm_bench.py` | Supports identical, rewritten, semantic, near-miss, random independent. |
| Equivalence CLI | Added | `--bench-equivalence`, `--equiv-pair-style`, `--equiv-compare-repeat`, `--equiv-backends` | Writes normal raw/summary CSVs. |

## 2. Benchmark Semantics

ROBDD equivalence builds `f` and `g` in the same BDD manager with the same variable order. The equivalence decision is `root_f == root_g`, verified by tests on `x & y` vs `y & x`, `x` vs `~~x`, and `x` vs `~x`.

Bitset equivalence evaluates both expressions to packed truth-table integers and compares the integers.

CM equivalence compiles both expressions through the public CM IR API and evaluates with `hybrid_no_reinflate`. It compares returned packed bitsets or truth-table vectors. This is output equivalence, not a canonical symbolic CM equivalence layer.

All reported totals separate construction/evaluation from the final compare step.

## 3. Results: Equivalent Pairs

Run: `bench_equiv_autoref_rewritten`, 5 trials, `mixed_no_constants`, `rewritten_equiv`, best-of-10 ROBDD order sweeps, compare repeat 1000.

| backend | n | build/eval total s | compare per call s | total s | ok |
| --- | ---: | ---: | ---: | ---: | --- |
| ROBDD/autoref | 4 | 0.001036 | 0.000000164 | 0.001271 | True |
| ROBDD/autoref | 8 | 0.001486 | 0.000000151 | 0.001636 | True |
| ROBDD/autoref | 12 | 0.003050 | 0.000000168 | 0.003216 | True |
| ROBDD/autoref | 16 | 0.003581 | 0.000000185 | 0.003756 | True |
| Bitset | 4 | 0.000076 | 0.000000500 | 0.000076 | True |
| Bitset | 8 | 0.000073 | 0.000000500 | 0.000073 | True |
| Bitset | 12 | 0.000294 | 0.000001400 | 0.000295 | True |
| Bitset | 16 | 0.000691 | 0.000002800 | 0.000694 | True |
| CM no-reinflate | 4 | 0.002929 | 0.000001700 | 0.002931 | True |
| CM no-reinflate | 8 | 0.003942 | 0.000021100 | 0.004008 | True |
| CM no-reinflate | 12 | 0.006061 | 0.000023900 | 0.006179 | True |
| CM no-reinflate | 16 | 0.006561 | 0.000040400 | 0.006594 | True |

## 4. Results: Near-Miss Pairs

Run: `bench_equiv_autoref_nearmiss`, 5 trials, `mixed_no_constants`, `near_miss`, best-of-10 ROBDD order sweeps, compare repeat 1000.

| backend | n | build/eval total s | compare per call s | total s | ok |
| --- | ---: | ---: | ---: | ---: | --- |
| ROBDD/autoref | 4 | 0.000839 | 0.000000158 | 0.000998 | True |
| ROBDD/autoref | 8 | 0.001312 | 0.000000160 | 0.001476 | True |
| ROBDD/autoref | 12 | 0.003599 | 0.000000212 | 0.003811 | True |
| ROBDD/autoref | 16 | 0.005029 | 0.000000159 | 0.005188 | True |
| Bitset | 4 | 0.000053 | 0.000000500 | 0.000054 | True |
| Bitset | 8 | 0.000058 | 0.000000400 | 0.000058 | True |
| Bitset | 12 | 0.000190 | 0.000000900 | 0.000191 | True |
| Bitset | 16 | 0.000387 | 0.000000900 | 0.000388 | True |
| CM no-reinflate | 4 | 0.001860 | 0.000002000 | 0.001863 | True |
| CM no-reinflate | 8 | 0.003221 | 0.000020600 | 0.003323 | True |
| CM no-reinflate | 12 | 0.007048 | 0.000034000 | 0.007096 | True |
| CM no-reinflate | 16 | 0.005153 | 0.000034900 | 0.004921 | True |

## 5. CUDD vs Autoref

CUDD was not available in the native Windows environment, so no CUDD/autoref speedup table is reported. The benchmark supports `--robdd-dd-backend cudd`; run the same commands in the WSL2/Docker environment where `dd.cudd` imports successfully.

## 6. Interpretation

ROBDD's canonical advantage is visible in the compare phase: once both functions are represented in the same reduced manager and order, equality is essentially pointer/function identity and costs far less than construction.

CM currently competes only as output equivalence. Its compare step is small, but it still evaluates or materializes enough output representation to compare payloads. To compete with ROBDD on symbolic equivalence, CM would need a proven canonical structural equivalence layer.

Bitset remains the strongest exact flat-output method for these sizes. That does not contradict ROBDD's symbolic advantage; it reflects that `n<=16` full packed truth tables are still cheap.

The slide/paper claims should keep ROBDD/CUDD symbolic build/equivalence separate from ROBDD build plus truth-table extraction. The latter is a different task and was previously much slower.

## 7. Slide Recommendations

Use these labels:

- `ROBDD/CUDD - canonical equivalence`
- `CM no-reinflate - output equivalence`
- `Bitset - packed truth-table equivalence`
- `ROBDD/CUDD - symbolic build`
- `ROBDD/CUDD - build + truth-table extraction`

Do not label CM no-reinflate as canonical equivalence unless a canonical structural method is added and validated.
