# FABLE CM HANDOFF — System Map & Current Capabilities

> **Purpose.** Onboarding brief for the next research agent (Fable) whose job is to find
> *more speedups* for Correspondence Matrices (CM), the CM IR, the no-reinflate path, and
> related execution machinery. This file is the **map + current-state**. The companion file
> [`FABLE_CM_SPEEDUP_AGENDA.md`](FABLE_CM_SPEEDUP_AGENDA.md) is the **prioritized research
> agenda** (where the actual speedup work lives).
>
> Prepared by a preliminary-analysis pass on 2026-07-20. Repo state verified: **159/159 tests
> pass** (`python -m pytest -q`, ~2.5 min). Working tree clean at commit `af23e8a`.

---

## 0. TL;DR — what you are inheriting

- CM has been reframed (correctly, and the evidence supports it) from *"a Boolean evaluator
  that should beat bitset"* into **"a structure-preserving compiler / operator-calculus IR
  that reduces a Boolean problem, then delegates flat execution to bitset."**
- The **best-performing CM path today** is:
  ```python
  compiled = compile_expr(expr, use_persistent_cache=True)          # cm_ir.py:789
  result   = evaluate_compiled(compiled, mode="hybrid_no_reinflate", # cm_ir.py:807
                               vars_all=[...])
  ```
  i.e. **compile Expr → CM IR (canonicalized/interned DAG) → hybrid_no_reinflate execution →
  packed bitset / TT-vector output → reuse compiled IR via structural-hash cache.**
- **Bitset is still the flat-execution lower bound** and is not expected to be beaten one-shot.
  The realistic speedup goal is **closing the residual gap** in the reuse/compile-once regime
  and **extending feasibility** (large-n, reduced-live-var).
- **Where the time actually goes now** (this is the whole game for you):
  - One-shot: **IR compilation dominates**, not bitset execution.
  - Compile-once/cached: after compile cost is amortized, the residual is **CM-node bitset
    evaluation + per-node Python dispatch/alignment/wrapping scaffolding**.
- Dead ends already proven (do **not** re-litigate): CM_parallel (multiprocessing),
  threshold-only partial-hybrid, boundary micro-opts as a primary lever, "dense CM beats
  bitset". See §6.

---

## 1. Repository shape

Root is a single-package Python project (`C:\Users\brian\Documents\CM_Computation`). The
benchmark `.venv` is Python 3.13.5; system tests use Python 3.10.11. Two things share the name
`cm_bench.py`: the **root** one (208 KB, the
real driver) and a small legacy copy inside `Correspondence_Matrices/` (an older git submodule
snapshot — ignore it for perf work).

### 1.1 Core execution stack (this is what you optimize)

| File | Role | Notes for perf work |
|---|---|---|
| [`cm_ir.py`](cm_ir.py) (65 KB, 1598 lines) | **The heart.** CM IR DAG, canonicalizing builder, interning, structural-hash caches, all materialize modes, no-reinflate. | Contains ~all hot paths. See §3 and the AGENDA. |
| [`bitset_backend.py`](bitset_backend.py) | Packed-bitset kernel + **CM-node bitset evaluator** `eval_cm_node_bitset`. | The flat lower bound *and* the CM execution kernel. |
| [`cm_build.py`](cm_build.py) / [`cm_build_lazy.py`](cm_build_lazy.py) | Thin wrappers: `compile_expr_to_cm` = compile IR + `materialize_cm` (dense). Default `materialize_mode="partial_hybrid"`, `hybrid_threshold=7`. | Public dense-matrix entry points. |
| [`cm_normalize.py`](cm_normalize.py) | Layout (`canonical_layout` balanced vs legacy_square), lifting, LRU permutation caches, `combine_pointwise`. | Alignment/lift cost lives here. |
| [`cm_parallel.py`](cm_parallel.py) | Process-based parallel CM materialization. | **Deprioritized** — negative result (§6). |

### 1.2 Operator-calculus / formalism modules (CM-native value, not the speed story)

| File | Role |
|---|---|
| [`cm_token.py`](cm_token.py) | 4-bit token for 2×2 operators; O(1) composition via 16×16 LUTs (`cm_compose`). |
| [`cm_pair.py`](cm_pair.py) / [`cm_build_pair.py`](cm_build_pair.py) | Pair-aware compiler: collapse 1-row-var × 1-col-var subtrees to a token, compose in O(1). |
| [`cm_operator_difference.py`](cm_operator_difference.py) | Quotient `A\B = A & ~B`, symmetric delta, overlap/containment, feature counts, transforms. |
| [`cm_lm.py`](cm_lm.py) / [`cm_render.py`](cm_render.py) | Logical-measurement bra/ket helpers and LaTeX/MathJax rendering. |

### 1.3 Expression library, benchmark harness, remote exec

- [`cm_exprlib.py`](cm_exprlib.py) — Boolean AST (`Var/Not/And/Or/Xor/Imp/Eqv`), `random_expr`,
  and the correctness oracle **`eval_expr_tt`**. Also Tseitin CNF + `miter_equiv`.
- [`cm_expr_serde.py`](cm_expr_serde.py) — Expr ↔ JSON (for remote).
- [`cm_bench.py`](cm_bench.py) — the CLI driver + all experiment loops (still monolithic).
- [`cmbench/`](cmbench/) — refactored stable helpers (config, context, expr generators,
  families, partial-contexts, equivalence, dd/robdd backend, result schemas, reporting). See §4.
- [`numba_backend.py`](numba_backend.py) — optional JIT stack-machine evaluator (control baseline).
- `cm_remote_*.py`, `cm_runpod_*.py` — optional RunPod remote execution of the no-reinflate
  path. Never on by default; not relevant to core speedups.

### 1.4 Where the prior knowledge lives (read these, in priority order)

1. [`CM_pre_writing_validation_report.md`](CM_pre_writing_validation_report.md) — **the frontier**:
   n=32 feasibility, compile-once/eval-many, cached-exec overhead profile. Verdict "ready to write".
2. [`CM_ir_cost_report.md`](CM_ir_cost_report.md) — IR-stage cost decomposition + reuse/cache flags.
3. [`CM_no_reinflation_report.md`](CM_no_reinflation_report.md) — the no-reinflate win.
4. [`CM_final_robustness_report.md`](CM_final_robustness_report.md) — 5-seed + stress-style + sampled correctness (0 mismatches).
5. Experiment A/B/C reports (`CM_experiment_A/B/C_*.md`) — families, partial contexts, operator quotient.
6. ROBDD/CUDD reports (`ROBDD_CM_fair_comparison_report.md`, `CUDD_ROBDD_extraction_report.md`,
   `CUDD_WSL_install_and_benchmark_report.md`, `ROBDD_CM_equivalence_report.md`).
7. `AGENT_HANDOFF_CM_POST_MERGE.md`, `cm_handoff_notes.md` — older baselines (treat as history).
8. `C:\Users\brian\Downloads\CM-Comparisons-Draft.pdf` — the paper/deck (thesis + all charts).

> **Note on terminology drift:** the deck/paper calls the persistent structural-hash cache the
> **"Structural-Hash Compiled-IR Cache"**; older CSVs/docs call it "persistent cache". Same thing.
> The no-reinflate representation codes were extended: **1**=full TT vector, **2**=full packed
> bitset, **3**=reduced packed bitset (live-vars only), **4**=reduced TT vector. Codes 3/4 are
> the large-n path added after the older ChatGPT-thread docs were written.

---

## 2. The CM IR data model (what you'll be manipulating)

`CMNode` — frozen dataclass, [`cm_ir.py:303`](cm_ir.py). Immutable & hashable so it doubles as a
memo/intern key.

```
CMNode(
  kind: str,                    # "const" | "var" | "not" | "binary"
  key:  Tuple[object, ...],     # canonical structural key (interning + memo key)
  vars: Tuple[str, ...],        # sorted-unique live vars in subtree (precomputed at build)
  const_value: Optional[int],   # 0/1 for const, else None
  op:   str = "",               # "" | "NOT" | "AND" | "OR" | "XOR" | "IMP" | "EQV"
  args: Tuple[CMNode, ...] = (),# child DAG edges (shared via interning → DAG not tree)
  var_name: str = "",           # only for kind=="var"
)
```

- **Builder:** `CMIRBuilder` ([`cm_ir.py:314`](cm_ir.py)) canonicalizes during build — flattens
  associative AND/OR/XOR, sorts commutative args, folds constants, applies negation/annihilation
  rewrites — and interns every subtree through `_intern` ([`cm_ir.py:330`](cm_ir.py)).
- **Two caches:**
  - *Reuse (identity) cache* `_COMPILED_IR_CACHE: OrderedDict[Expr, CMNode]`, max 4096
    ([`cm_ir.py:62`](cm_ir.py)) — keyed by the `Expr` object; enabled via `reuse_cache=True` /
    `--cm-reuse-compiled-ir`.
  - *Persistent structural-hash cache* `_PERSISTENT_IR_CACHE: OrderedDict[str, CMNode]`, max
    16384 ([`cm_ir.py:70`](cm_ir.py)) — keyed by `expr_structural_hash(e)`
    ([`cm_ir.py:95`](cm_ir.py), blake2b, canonical); hits across *distinct but equivalent* Expr
    objects. Enabled via `use_persistent_cache=True` / `--cm-use-persistent-cache`.
- **Public API surface** (entry points for Fable):
  `compile_expr` (789), `evaluate_compiled` (807), `CompiledExpr` (778),
  `compile_expr_to_cm_ir` (721) / `_cached` (740) / `_persistent` (157),
  `materialize_ir` (935), `materialize_cm` (1321),
  `materialize_hybrid_no_reinflate` (1408), `FinalNoReinflateResult` (1391),
  `expr_structural_hash` (95), and cache-stat/clear helpers (66–82, 841–850).

---

## 3. The four execution modes (and where time goes)

There are **three `materialize_mode`s** handled in `_materialize_ir_tagged`
([`cm_ir.py:964`](cm_ir.py)) — `numpy`, `hybrid`, `partial_hybrid` — plus the **separate
top-level** `materialize_hybrid_no_reinflate` ([`cm_ir.py:1408`](cm_ir.py)).

| Mode | What it does | Output | Status |
|---|---|---|---|
| `numpy` | Dense NumPy hypercube at every node. No bitset. | dense CM matrix | baseline/reference |
| `hybrid` | Root may collapse to a single bitset eval if `live_k ≤ threshold`; else numpy. | dense CM matrix | improves over numpy |
| `partial_hybrid` | Root forced numpy; **children** may collapse to bitset. Default wrapper mode. | dense CM matrix | preserves structure; **not faster** than hybrid |
| **`hybrid_no_reinflate`** | Threshold test; return **packed bitset** (codes 2/3) or **TT vector** (codes 1/4). Never builds a dense 2-D CM matrix. | packed bitset / TT vector | **BEST current path** |

Dispatch details you'll touch:
- Mode branch: [`cm_ir.py:1109-1136`](cm_ir.py). Root collapse permission set at
  [`cm_ir.py:1318`](cm_ir.py) (`allow_bitset_collapse = (mode=="hybrid")`).
- Live-var reduction per node: [`cm_ir.py:1107`](cm_ir.py)
  `live_vars = tuple(v for v in cur.vars if v not in fixed_map)`.
- Bitset boundary: `materialize_bitset` → `eval_cm_node_bitset(...)` at
  [`cm_ir.py:1000`](cm_ir.py) (and the no-reinflate direct call at
  [`cm_ir.py:1475`](cm_ir.py)).

### 3.1 Measured cost profile (the numbers that matter)

**One-shot `hybrid_no_reinflate` (threshold 7, `CM_ir_cost_report.md`):** IR compile dominates.

| n | total µs | ir_compile | bitset_eval | ratio vs bitset |
|--:|--:|--:|--:|--:|
| 4 | 160 | 107 | 37 | 18.4× |
| 8 | 168 | 120 | 32 | 16.3× |
| 12 | 303 | 212 | 67 | 7.9× |
| 16 | 195 | 113 | 65 | 3.7× |

**With compiled-IR reuse (cache hit):** compile cost → 0, ratio collapses.

| n | total µs | bitset_eval | ratio vs bitset | cache hit |
|--:|--:|--:|--:|--:|
| 4 | 70 | 42 | 7.6× | 1 |
| 8 | 55 | 35 | 5.2× | 1 |
| 12 | 75 | 57 | 2.7× | 1 |
| 16 | 108 | 76 | 1.6× | 1 |

**Cached-exec overhead profile (`--cm-profile-cached-exec`, `CM_pre_writing_validation_report.md`):**
after compile is removed, the residual at nominal n=16 is *dominated by the CM-node bitset
evaluation itself* (55.3 of 63.7 µs); dispatch/var-order/result-wrap are small fixed costs
(~2 µs each) that only dominate for tiny reduced outputs.

| n | cm_cached µs | bitset_eval | dispatch | var_order | result_wrap | ratio |
|--:|--:|--:|--:|--:|--:|--:|
| 4 | 26.8 | 18.3 | 2.11 | 0.97 | 2.15 | 12.2× |
| 8 | 24.9 | 18.4 | 2.02 | 1.05 | 1.89 | 10.0× |
| 12 | 42.8 | 35.6 | 2.16 | 1.29 | 2.09 | 5.7× |
| 16 | 63.7 | 55.3 | 2.27 | 1.41 | 2.35 | 2.1× |

> **Reading:** For a real speedup you must attack **either** (a) IR compilation cost (helps
> one-shot & first-touch), **or** (b) the CM-node bitset evaluator + Python-level per-node
> scaffolding (helps the cached/compile-once regime, which is the flagship use-case). Both are
> laid out concretely in the AGENDA.

---

## 4. Benchmark harness — how to measure anything

Driver: `cm_bench.py`. `main()` at [`cm_bench.py:4330`](cm_bench.py) parses args
(`build_config_and_context` in [`cmbench/cli.py`](cmbench/cli.py)) and dispatches on the
`--bench-*` flag ([`cm_bench.py:4570`](cm_bench.py)). Writes `{out_prefix}_raw.csv` (per-trial)
and `{out_prefix}_summary.csv` (per-n medians).

### 4.1 The flags you will use constantly

```
--sizes 4,8,12,16          # variable counts
--trials 5  --max-depth 4  --seed 123
--cm-layout balanced
--cm-compare-no-reinflate   # run the no-reinflate variant (the good path)
--cm-use-persistent-cache   # structural-hash compiled-IR cache
--cm-eval-repeat N          # amortize compile → measure cached per-eval cost
--cm-hybrid-threshold 7     # live-var collapse threshold (sweep 5..9)
--cm-report-ir-breakdown    # emit per-IR-stage timing columns
--cm-compile-once-per-expression   # compile once, separate *_exec_only_time_s
--cm-reuse-compiled-ir      # reuse compiled IR across modes in a trial
--cm-profile-cached-exec    # dispatch/var-order/bitset/result-wrap breakdown
--large-n-safe --cm-max-full-output-vars 16   # n>16 structural (reduced-output) mode
--no-dd --no-espresso --no-sympy --no-robdd --no-bdd-sop --no-numba   # isolate CM vs bitset
--print-summary --out-prefix bench_xxx
```

**Canonical "profile the CM path" command** (start here):
```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 4 --seed 123 \
  --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache \
  --cm-eval-repeat 100 --cm-profile-cached-exec --cm-report-ir-breakdown \
  --cm-hybrid-threshold 7 --no-dd --no-espresso --no-sympy --no-robdd \
  --no-bdd-sop --no-numba --print-summary --out-prefix bench_profile
```

**Paper reproduction:** [`run_paper_benchmarks.ps1`](run_paper_benchmarks.ps1) regenerates the
`paper_*` CSVs (exact n≤16, large-n structural, 5-seed robustness, stress styles).

### 4.2 Experiment types (`--bench-*`)

| Selector | Function | Tests |
|---|---|---|
| *(default)* | `run_bench` / `time_backends_on_expr` ([`cm_bench.py:2587`/`1311`](cm_bench.py)) | CM vs bitset/numba/robdd/dd/sympy/... on random exprs |
| `--bench-equivalence` | `run_equivalence_bench` (4046) | equivalent/near-miss pairs; robdd/bitset/cm/sympy |
| `--bench-expression-family` | `run_expression_family_bench` (1106) | amortized cost over related-expr families (cache reuse) |
| `--bench-partial-contexts` | `run_partial_context_bench` (701) | fixed-var contexts: CM-cache vs no-cache vs bitset vs ROBDD-restrict |
| `--bench-operator-difference` | `run_operator_difference_bench` (3926) | quotient/delta modes (CM-native) |
| `--bench-cm-transformations` | `run_cm_transformation_bench` (3392) | 2×2 operator-table transforms |

`cmbench/` module roles (config/context/enums/availability/timing; expr/{generators,families,
partial_contexts,equivalence,eval,diagnostics,visitors}; backends/{robdd_dd,bitset_utils};
results/{schema,flatten,single_expr,...}; reporting/{csv_io,summary_tables}) are documented in
[`docs/cmbench_architecture.md`](docs/cmbench_architecture.md). **When you add a backend/metric,
extend `cmbench/results/schema.py`’s `BackendResult`/`TimingBreakdown` + `flatten.py` so CSV
columns stay stable** — schema-stability tests (`tests/test_single_expr_schema_stability.py`,
`tests/test_run_bench_output_compatibility.py`) will guard you.

### 4.3 Diagnostics you can trust (already instrumented — reuse them, don't rebuild)

IR-stage timers: `ir_compile_time_s`, `ir_intern_time_s`, `ir_canonicalize_time_s`,
`ir_rewrite_time_s`, `ir_live_vars_time_s`, plus `subtree_cache_hits/misses`,
`ir_persistent_cache_hits/misses/size`. No-reinflate: `nr_bitset_eval_time_s`,
`nr_fallback_materialize_ir_time_s`, `nr_tt_vector_build_time_s`. Cached-exec:
`cached_exec_{dispatch,var_order,fixed_handling,bitset_eval,result_wrap,other}_time_s`. Final
output: `final_output_representation_code`, `final_cm_materialization_performed`,
`live_vars_max`, `materializations`. Full list in [`CM_ir_cost_report.md`](CM_ir_cost_report.md)
§2 and the cm_ir.py agent map. **Instrumentation is off by default** (gated by the report flags),
so it does not pollute production timing.

---

## 5. Current, validated capabilities (what's real vs roadmap)

**Validated in experiments (safe to build on):**
- No-reinflate is the best CM flat-output path (n=16 ≈ 1.7× bitset at threshold 9; ~2.4×
  cached at n=16 threshold 7).
- Structural-hash compiled-IR cache: 1.51×–1.89× end-to-end; compile-once/eval-many is the
  natural usage model and works.
- n=32 **structural/reduced-live** feasibility (no dense 2^n): reduced packed-bitset output
  (repr code 3); runtime tracks *reduced live-var count*, not nominal n.
- Correctness: reference `eval_expr_tt`; 5-seed robustness + sampled correctness (3 seeds ×
  n∈{20,24,28,32} × 1000 samples = **0 mismatches**). 159/159 tests pass.
- Bitset is the flat lower bound; ROBDD/CUDD is the symbolic-build/equivalence baseline (its
  *build+extract* for flat output is 100s–1000s× slower than bitset — a separate task).

**Prototype / partially developed:** CM IR structural representation, live-var reduction,
basis-normalization scaffolding, backend delegation, structural-hash reuse detection, pair-aware
token compiler, operator quotient/difference.

**Roadmap / not proven:** canonical CM structural equivalence (current equivalence is
*output-based* — do **not** call it canonical), automatic backend routing + cost model, larger-n
beyond structural feasibility, real-workload validation, flattened/codegen IR evaluator.

---

## 6. Proven dead ends — do NOT reopen without a new idea

| Idea | Why it's parked |
|---|---|
| **CM_parallel** (multiprocessing) | Structural reduction removes the dense work; activation rate ~0 in optimized grids, intermittent tiny wins only. Not the scalability story. |
| **Threshold-only partial_hybrid** | Preserves structure but adds boundary + parent-combine overhead; does not beat full hybrid. Needs a *cost model*, not tuning. |
| **Boundary micro-optimizations as primary lever** | Real but not dominant (~1.4–2.0× on boundary only); didn't close the gap. Already done (alignment fast-path, uint8-copy removal). |
| **"Dense CM beats bitset one-shot"** | Refuted. Bitset wins flat execution; don't chase it. |
| **Comparing CUDD build-only to bitset flat output** | Different tasks; only fair with extraction included. |

The **legitimate** speedup frontier is: IR compilation cost, the CM-node bitset evaluator +
per-node Python scaffolding, and reduced-live-var/large-n execution. That is the AGENDA.

---

## 7. Environment & gotchas

- Windows 10, Python 3.10.11, `.venv` at repo root. Use `.\.venv\Scripts\python.exe` (the
  paper scripts fall back to `python`).
- **CUDD (`dd.cudd`) does NOT import on native Windows** — only `dd.autoref` (pure Python).
  CUDD numbers were produced in Docker/`python:3.10-slim` (WSL2). Keep this caveat when
  comparing symbolic-build baselines.
- Full test suite ≈ 2.5 min. Fast smoke: `python cm_bench.py --sizes 3 --trials 1 --max-depth 2
  --out-prefix smoke --print-summary`.
- Correctness must stay **outside timed windows** (benchmark fairness invariant). Reference is
  always `eval_expr_tt`. Don't regress this.
- The n>16 path must never accidentally materialize 2^n — the `--cm-max-full-output-vars` guard
  raises instead ([`cm_ir.py:1461`](cm_ir.py)). Preserve that guard.

---

## 8. Where to go next

Read [`FABLE_CM_SPEEDUP_AGENDA.md`](FABLE_CM_SPEEDUP_AGENDA.md). It ranks the concrete speedup
targets (with `file:line`, a hypothesis, how to measure, expected payoff, and risk) so you can
start the deep dive immediately.
