# B3 — Compile/DAG scaling (2026-08-03)

Git `eab8879`; `.venv` Python 3.13.5, numpy 2.3.2. Driver
`cm_b3_compile_scaling_2026_08_03.py`; 31 deterministic constructed cases
(shared ladders, cyclic n-ary chains, unshared random trees, mixed shared
DAGs, 8×8 multiplier bit cones), all ≤16 syntactic variables so complete
packed equality (cm/cse/cse_flat, and raw under the 60k-unfolded cap) gated
every timing. Best-of-3 timing blocks. Wall 1.0 s.

## Findings

1. **Compile-scaling claim RETAINED.** CM prep scales with structural DAG
   nodes, not tree unfolding: shared_ladder depth 20 (77 structural nodes,
   8.39M unfolded) compiles in **985 µs** — the pathological class that cost
   403 ms pre-repair stays ~3 orders of magnitude better, and deepening the
   ladder by 8 levels (256× more unfolding) adds only ~2× prep.
2. **Unshared-tree class.** Small trees (37 structural nodes) compile at
   ~360 µs; prep grows ~linearly with structural nodes up to ~8.5 ms at 615
   nodes. (The historical "152 µs class" was a smaller compile unit measured
   by the probe; the linear-in-structural-nodes shape is what the disposition
   table retains, and it holds.)
3. **Prep multiple vs CSE is structure-dependent but bounded:** 2.2–7.9×
   across all 31 cases (chains worst at 5.7–7.9×, trees 2.2–4.1×, ladders
   4.7–5.2×, mixed DAGs 3.7–4.6×, multiplier cones 5.1–5.5×) — consistent
   with the corrected-E3 geomean 4.30×.
4. Multiplier bit cones (up to 11.1M unfolded, 319 structural nodes) compile
   in ≤4.8 ms with exact packed equality — no pathological regression.

## Verdict

**B3 COMPLETE — compile/DAG-scaling claim CONFIRMED post-repair (prep tracks
structural nodes; pathological shared-chain class stays in the milliseconds).**
