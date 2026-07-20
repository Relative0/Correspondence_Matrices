# CM Speedup Investigation — Phase 1 Report

> **Status:** Investigation complete; no repo code changed. All measurements were made with
> prototype functions / monkeypatches in the session scratchpad, verified **bit-identical**
> against the current implementations and against the `eval_expr_tt` oracle
> (792 sweep checks across 6 expression styles, n=2..14, thresholds 3 and 7, incl. fixed-var
> cases: **0 mismatches**). Machine: Windows 10, Python 3.10.11, repo commit `af23e8a`.
> Baseline CSVs: `bench_profile_fable_raw.csv` / `bench_profile_fable_summary.csv`.
>
> **Headline:** the single biggest cost in the flagship compile-once/cached regime is not the
> bitset arithmetic — it is **`CMNode.__hash__`**. The frozen-dataclass hash recomputes a deep
> nested-tuple hash on every memo lookup, and it accounts for **~57% of total cached-exec time
> at n=12** (cProfile). Fixing it (plus an id-keyed memo in the eval kernel) cuts real cached
> per-eval time by **60–76% at n≤12** and **15–31% at n=16**, with zero output change.

---

## 1. Baseline reproduction (this machine)

Canonical profile command (HANDOFF §4.1) reproduced. One environment fix was needed first:
the venv lacked `requests` (imported unconditionally via `cm_remote_executor` →
`cm_runpod_client`); installed `requests 2.34.2`.

Per-eval cached medians (`--cm-eval-repeat 100`, profile instrumentation ON):

| n | NR cached µs | bitset cached µs | ratio | recorded (HANDOFF §3.1) ratio |
|--:|--:|--:|--:|--:|
| 4 | 78 | 4.4 | 17.9× | 12.2× |
| 8 | 62 | 10.9 | 5.7× | 10.0× |
| 12 | 165 | 20.1 | 8.2× | 5.7× |
| 16 | 225 | 84.9 | 2.6× | 2.1× |

One-shot: `ir_compile` 36–81 µs vs `nr_bitset_eval` 50–170 µs medians. **The two-regime split
holds** (compile matters one-shot, eval dominates cached), with one nuance vs the recorded
numbers: on this machine the eval side is a somewhat larger share than in the recorded tables.
Absolute times are ~2–3.5× the recorded ones — machine speed + profile instrumentation.
All prototype measurements below were taken with instrumentation OFF (`diagnostics=None`).

## 2. Root-cause profile of the cached path (cProfile, 2000 evals)

`materialize_hybrid_no_reinflate` on a precompiled node, n=12 (live_k=7):

- `eval_cm_node_bitset` = **89%** of the call.
- `CMNode.__hash__` = **57% of total time** (224,000 nested hash invocations per 2,000 evals).
  Cause: `@dataclass(frozen=True)` generates `__hash__ = hash((kind, key, vars, …, args, …))`;
  `key` is the *full nested structural tuple* and `args` recursively hashes child CMNodes, so
  **every `memo.get(cur)`/`memo[cur]=` is O(subtree-as-tree size)**, re-paid on every eval.
- At n=16 the same overhead exists (~28%) but genuine full-width bigint work grows: the
  full-output path evaluates at width 2^n (`output_vars = vars_all`) even when only 4–5 vars
  are live — 65,536-bit bigint ops per node.

Cold persistent compile, n=16 (300 compiles): `expr_structural_hash`/`digest_for` = **~48% of
compile time**. Cause: `compile_expr_to_cm_ir_persistent.build()` calls `expr_structural_hash(e)`
for *every subexpression*, and each call re-walks its whole subtree → quadratic hashing
(confirms AGENDA A1). Measured directly: at n=16, total hashing ≈ 830 µs/compile vs ≈ 113 µs
for a single root hash.

## 3. Ranked findings

### R1 ⭐ Cache `CMNode` hashes + id-keyed memo in `eval_cm_node_bitset` — **cached regime**

- **Root cause:** deep dataclass hash recomputed per memo lookup (above).
- **Proposed change (two independent, both bit-transparent):**
  - **R1a:** custom `CMNode.__hash__` that computes the *identical* hash value once and caches
    it on the instance (`object.__setattr__`, lazy). `__eq__` untouched → dict/set semantics
    unchanged everywhere (builder `seen` sets, `_is_negation_of`, `_materialize_ir_tagged`
    memo, eval memo).
  - **R1b:** in `eval_cm_node_bitset` ([bitset_backend.py:110](bitset_backend.py:110)), key the
    per-call memo by `id(cur)` instead of `cur` (nodes are alive for the whole call; two
    structurally-equal distinct objects only lose a memo *hit*, never correctness).
- **Measured effect (real `materialize_hybrid_no_reinflate`, instrumentation off, medians):**

  | case | base µs | R1a+R1b µs | Δ |
  |---|--:|--:|--:|
  | n=4 (live_k=4) | 97.9 | 23.8 | −76% |
  | n=8 (live_k=5) | 45.1 | 17.9 | −60% |
  | n=12 (live_k=7) | 83.0 | 31.1 | −63% |
  | n=12 (live_k=5) | 84.7 | 32.6 | −61% |
  | n=16 (live_k=4) | 161.8 | 112.2 | −31% |
  | n=16 (live_k=5) | 169.5 | 144.2 | −15% |

  R1a alone also speeds the numpy **fallback** path (live_k>threshold, broad-style n=16):
  ~20–45% on 3 of 4 cases (one noisy −3%).
- **Predicted diagnostics:** `cm_hybrid_no_reinflate_cached_exec_only_time_s` and
  `nr_bitset_eval_time_s` / `cached_exec_bitset_eval_time_s` drop 60–80% at n≤12, 15–30% at
  n=16. Cached ratio vs bitset at n=12 should fall from ~8× to ~3×; n=8 to ~1.6×.
- **Effort:** small (R1a ~10 lines in `cm_ir.py`; R1b ~2 lines). **Risk:** low. Hash *value*
  unchanged; 792-check sweep + per-case bit-equality already pass on the prototypes.
  Watch-outs: R1a adds `_cached_hash` to instance `__dict__` (pickle in `cm_parallel` still
  fine — it's just an int); keep `__eq__` untouched.

### R2 ⭐ Shared digest memo in the persistent compiler (AGENDA A1) — **one-shot regime**

- **Root cause:** per-subtree `expr_structural_hash` re-walks each subtree → quadratic.
- **Proposed change:** inside `compile_expr_to_cm_ir_persistent`, compute blake2b digests
  bottom-up with one memo (keyed by `id(subexpr)`) shared across the whole `build()`
  recursion. **Digest values and cache keys are byte-identical** (asserted in probe: same
  `_PERSISTENT_IR_CACHE` key sets, same resulting node keys).
- **Measured effect (cold compile, medians):** n=4: 65→28 µs (−57%); n=8: 90→38 µs (−57%);
  n=12: 554→363 µs (−34%); n=16: 278→181 µs (−35%).
  Warm root-hit compiles get ~5 µs slower in the prototype (memo dict setup on a single
  root-hash walk); if that matters it can be eliminated by hashing the root first and only
  building the memo on a miss.
- **Predicted diagnostics:** `ir_compile_time_s` −35–57% on cache-miss compiles;
  family workloads (`--bench-expression-family`) benefit most on first touch of each variant.
- **Effort:** small-medium (restructure `build()`/`digest_for` in `cm_ir.py:157-217`).
  **Risk:** low — digests provably unchanged; tests guard cache semantics.

### R3 Vectorize `_build_bitset_env_cached` — **first-touch / large-n feasibility**

- **Root cause:** pure-Python bigint mask construction loops over ~2^n block positions.
  Measured first-touch (cache cold): n=12: 1.1 ms; n=14: 14 ms; **n=16: 133 ms; n=18: 1.56 s**.
  Hidden behind a 256-entry LRU, but paid once per distinct var-tuple — and by *both* the CM
  path and the raw-bitset baseline.
- **Proposed change:** build each mask via numpy (`(rows >> b) & 1` → `packbits` →
  `int.from_bytes`). Verified identical dicts. Measured: n=16: 4.4 ms (**30×**), n=18: 32 ms
  (**48×**). Keep the current loop below ~n=10 where it's faster (numpy overhead).
- **Effort:** small ([bitset_backend.py:15](bitset_backend.py:15)). **Risk:** low.
  Mostly invisible in steady-state benchmarks (cache warm), but removes a nasty first-touch
  cliff and matters for any future n≥16-wide env use.

### R4 Negative result — reduced-width eval + numpy expansion to 2^n

Hypothesis: since the full-output path runs every DAG op at 2^n width even when live_k≪n,
evaluate at 2^live_k and expand once. **Refuted as implemented:** unpack→align→`broadcast_to`
→flatten→`packbits` costs 316–657 µs at n=16 (vs 112–154 µs for full-width eval with R1) —
the flatten of a 16-d broadcast view is a strided elementwise gather. A bigint
"repunit-multiplication" expansion could be cheap for missing *MSB* vars only; general
insertion needs interleaving (O(width·log) big-ops) and is unlikely to beat ~26 C-level
bigint ops. **Parked** unless a large-n full-output use-case appears; recorded so it isn't
re-tried naively.

### R5 Analysis — what remains after R1, and what it means for Tier C (flatten/codegen)

After R1, the n≤12 cached residual is ~18–33 µs: ~½ kernel bigint ops + env lookups, ~½
wrapper (`materialize_hybrid_no_reinflate` scaffolding, `live_vars` genexpr, result wrap).
At n=16 the residual (~112–144 µs) is dominated by genuine 65,536-bit bigint ops — neither
dispatch nor hashing. Consequences:

- **C1 (flat interpreted evaluator) should be re-scoped *after* R1 lands:** its target
  (recursion + dict dispatch) shrinks to ~10–20 µs/eval at n≤12 and is negligible at n=16.
  Realistic remaining win is maybe 1.3–1.6× at small n, not the pre-R1 estimate. The numba
  variant would additionally have to handle Python bigints (it can't natively) — a rewrite to
  fixed-width word arrays, i.e. substantial effort for modest post-R1 payoff. Recommend:
  land R1, re-measure, then decide C1 with fresh numbers.
- **A4 (skip `live_vars` rebuild when `fixed` empty)** is real but tiny (~3 µs/eval at n=12);
  fold it into the R1 patch opportunistically.
- **A2/A3 (builder negation scan, canonicalization sort):** visible in the compile profile
  (`sorted` ≈ 100 µs per n=16 cold compile) but secondary to R2; revisit only if compile is
  still hot after R2.

## 4. Recommended Phase 2 (in order)

1. **R1a + R1b (+A4)** — flagship-regime win, ~10 lines, bit-transparent. Verify: canonical
   profile command before/after; `python -m pytest -q` 159/159; correctness sweep vs
   `eval_expr_tt` outside timed windows.
2. **R2** — one-shot/family-regime win, digest-identical by construction.
3. **R3** — small patch, removes the first-touch cliff (include a regression note that
   n=8-scale env builds stay on the loop path).

All three are "drop-in, output-identical" rather than flag-gated *modes* — but per ground
rules I have not touched the repo; if approved I'd still add a temporary escape hatch
(env var or keyword default) for R1a/R1b during the correctness-sweep window, then remove it.

Predicted post-R1 cached ratios vs bitset (rough, from case medians): n=4 ~5×, n=8 ~1.6×,
n=12 ~3×, n=16 ~2.1× (from 17.9× / 5.7× / 8.2× / 2.6×). Note n=16's floor is bigint width,
not Python overhead; the honest lever there is reduced-output (repr code 3) usage, not more
kernel tuning.

## 5. Dead ends respected / re-confirmed

- Did **not** reopen CM_parallel, threshold-only partial-hybrid, boundary micro-opts, or
  "dense CM beats bitset" (HANDOFF §6).
- Added one new parked negative: **R4** (numpy expansion), with the exact numbers above.

## 6. Artifacts

- Baseline: `bench_profile_fable_{raw,summary}.csv` (repo root).
- Probes (scratchpad, session `45f63d0c…`): `probe_hash_cost.py`,
  `probe_cprofile_cached.py`, `probe_fix_candidates.py`, `probe_compile_memo.py`,
  `probe_correctness_sweep.py`.
- Env fix: `pip install requests` into `.venv` (cm_bench import chain).
