# B5 — CUDD matched comparison on RunPod (2026-08-03)

Authorization: `POD_REPLICATION_APPROVED = YES` (hard $5 cap);
`DEPENDENCY_INSTALL_APPROVED` pod-side only. dd.cudd does not build on
Windows; this fills Audit V4's blocked same-box primary experiment with a
matched-cost run on one Linux pod.

## Provenance

- Pod: RunPod `cpu3c` SECURE, 2 vCPU, AMD EPYC 7713, image `python:3.10`
  (full; gcc/make for the CUDD build), Linux 6.17.0-35, terminated after
  collection. **Cost of the successful run: $0.0021** (runs 1–4 failed
  pre-measurement — proxy 404 race, dd 0.5.7 env-var install route, missing
  `^` operator on dd.cudd.Function, CUDD tarball fetch timeout — each
  terminated, $0.0065 combined; all recorded in the per-run audits).
- On-pod installs (pod only): numpy 2.2.6, cython, **dd 0.5.7 built from
  source with `setup.py install --fetch --cudd`** — `import dd.cudd`
  verified before measurement; **fail closed, no autoref fallback path
  exists in the worker**. `robdd_is_cudd`-equivalent identity asserted on
  every row (manager module must be `dd.cudd`).
- Corpus: the frozen corrected-E3 corpus (192 formulas, k∈{8,12,16}),
  SHA-256 verified on-pod before measurement.

## Correctness bar (exceeds the archived 64-sample mode)

CM/CSE-flat complete packed equality before timing on all 192 formulas;
**CUDD full 2^k-extraction packed equality vs the CM bits on all 192
formulas** (exhaustive, not sampled); plus the seeded 256-assignment
re-check. Zero mismatches.

## Results (medians per stratum; construction and evaluation separate)

| live_k | CM prep µs | CSE-flat prep µs | CUDD build µs | CM kernel µs (full 2^k) | CSE-flat kernel µs | CUDD 256-eval µs | CUDD full-extract µs | CUDD nodes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8  | 266 | 78  | 2,488 | 15.4 | 16.7 | 403 | 1,139 | 17 |
| 12 | 388 | 107 | 2,507 | 24.2 | 25.1 | 585 | 25,584 | 42 |
| 16 | 521 | 129 | 2,580 | 45.4 | 47.4 | 994 | 580,357 | 78 |

CUDD conventions: fixed natural variable order, single build, no reordering,
no order search — matched to the packed pipelines' one-shot prep. Wall 43.2 s.

## Reading

1. **Construction:** CUDD build is ~5–10× CM prep and ~20–30× CSE-flat prep
   at these sizes (small cones; CUDD's strength — compact symbolic form —
   is real: 17–78 nodes vs 2^k truth bits, but costs more to build here).
2. **Equivalent packed output:** the V4 boundary conclusion is confirmed
   with same-box data: full extraction is ~74× (k=8) to ~12,800× (k=16)
   slower than the CM words kernel; even 256 assignments cost ~20× a full
   2^k packed kernel call. CUDD cannot enter a packed-output leaderboard.
3. **CM vs CSE-flat on-pod:** kernels within ~4% (0.96–0.97 pod-side in B6)
   — kernel-equivalence unchanged.
4. Scope: one pod, one CPU model, small-support cones (k≤16), symbolic
   build time vs packed evaluation remain different quantities and are
   reported separately — never as a single three-way winner.

## Verdict

**B5 COMPLETE — V4's CUDD-boundary conclusions CONFIRMED with same-box
matched-cost evidence (previously blocked); CUDD excels at compact symbolic
construction, and packed-output extraction remains orders of magnitude
slower than the words kernels.**
