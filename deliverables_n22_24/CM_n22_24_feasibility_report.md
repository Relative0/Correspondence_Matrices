# CM n=22/24 Feasibility Report (extension of n=18/20)

> Extends `CM_n20_feasibility_report.md` to **n=22 and n=24** for the CM
> `materialize_hybrid_no_reinflate` reduced-output path. Same method, same guard
> (`--cm-max-full-output-vars 16`), local-only (RunPod unnecessary — see §1.2 of the n=20
> report; re-confirmed here through n=24).
>
> Machine: Windows 10, Python 3.10.11, `.\.venv\Scripts\python.exe`, commit `1a984e4`,
> 2026-07-21. **No library code changed** → `pytest -q` 159/159 unaffected.
> **RunPod pod-hours: 0** (pod `x82z2pbpofhcgz` verified `EXITED`).

## 1. Verdict

**n=22 and n=24 behave exactly like n=18/20: feasible and bit-correct on the CM
reduced-output path whenever `live_k ≤ 16`, and the guard correctly refuses `live_k > 16`.**
The path's cost tracks the *reduced live-variable count*, so at these sizes it is still a
sub-20 µs cached per-eval — completely flat in nominal `n`. **0 mismatches across 40,000
sampled-oracle checks** over n=16..24. The 16-variable guard is the sole determinant of
feasibility; it never silently produced a wrong or oversized output at any size tested.

## 2. Headline — CM no-reinflate (reduced) vs raw bitset (matched scope)

Depth-4 random expressions, 8 trials/n, cached per-eval medians, `--large-n-safe`,
`--cm-hybrid-threshold 7`. (`CM_n16_24_headline.csv`.)

| n | live_k range | repr | guard fired | CM cached µs | bitset cached µs | ratio | correctness |
|--:|:--|:--|--:|--:|--:|--:|:--|
| 16 | 16 | 1,2 | 0/8 | 123.8 | 73.5 | 1.68× | 8/8 OK, 0/8000 mm |
| 18 | 1–8 | 3,4 | 8/8 | 29.8 | 16.6 | 1.80× | 8/8 OK, 0/8000 mm |
| 20 | 1–13 | 3,4 | 8/8 | 16.4 | 16.4 | 1.00× | 8/8 OK, 0/8000 mm |
| 22 | 1–8 | 3,4 | 8/8 | 19.6 | 11.7 | 1.67× | 8/8 OK, 0/8000 mm |
| 24 | 1–10 | 3,4 | 8/8 | 19.7 | 19.3 | 1.02× | 8/8 OK, 0/8000 mm |

The cached per-eval time is ~16–30 µs for every n ≥ 18 (bounded by `live_k`, which depth-4
random expressions keep small — a depth-d binary tree has ≤ 2^d leaves, so ≤ 16 distinct
vars at depth 4). The CM/bitset ratio bounces between 1.0× and 1.8× — this is µs-scale noise
at these tiny reduced outputs, not a trend; both are far below the n=16 full-output cost.

## 3. Guard behavior across sizes (`CM_n16_24_guard_rate.csv`)

30 expressions per (n, depth); columns are the three guard outcomes. The pattern is
**identical in shape** at every size — depth (hence `live_k`) is the only driver:

| depth | n=18 | n=20 | n=22 | n=24 | outcome |
|--:|:--|:--|:--|:--|:--|
| 2 | 30/0/0 | 30/0/0 | 30/0/0 | 30/0/0 | all clean (bitset, live≤7) |
| 4 | 17/13/0 | 16/14/0 | 16/14/0 | 15/15/0 | all clean (mix of bitset+TT) |
| 6 | 0/23/7 | 0/14/16 | 0/12/18 | 0/8/22 | TT-fallback + some refusals |
| 8 | 0/1/29 | 0/1/29 | 0/0/30 | 0/0/30 | essentially all refused |
| 10 | 0/0/30 | 0/0/30 | 0/0/30 | 0/0/30 | all refused (all n vars live) |

Cells are `repr3 / repr4 / refused`. As n grows, the depth at which functions become
fully-live shifts slightly earlier (more inputs → easier to touch >16 of them), but the
mechanism is unchanged: refusal is the intended `cm_ir.py:1491` `ValueError`, never a crash
or a wrong answer.

## 4. Comparison-method scaling (`CM_n16_24_scaling.csv`)

Full-output raw bitset (2^n-bit result) and the vectorized `eval_expr_tt` oracle, depth-4:

| n | rows 2^n | bitset full-output | result size | `eval_expr_tt` oracle | oracle array |
|--:|--:|--:|--:|--:|--:|
| 16 | 65,536 | 0.09 ms | 8 KB | 3.7 ms | <1 MB |
| 18 | 262,144 | 0.51 ms | 32 KB | 23 ms | <1 MB |
| 20 | 1,048,576 | 1.17 ms | 128 KB | 87 ms | 1 MB |
| 22 | 4,194,304 | 8.80 ms | 512 KB | 602 ms | 4 MB |
| 24 | 16,777,216 | 38.6 ms | 2 MB | 2.47 s | 16 MB |

- **Raw bitset full output scales ~4×/+2n** (it is 4× the bits) but stays at tens of ms
  through n=24 — not a wall, just growth. This is the honest flat lower bound; CM does not
  compete with it at full output (CM's n>16 value is the *reduced* representation).
- **The oracle stays vectorized and cheap**: 2.47 s at n=24 for a full 2^24-row ground
  truth. This re-confirms the n=20 report's central correction — there is no
  "seconds-to-tens-of-seconds per expression" oracle wall, so **RunPod offers no compute
  benefit through n=24**. (In practice we verify via per-assignment sampling, cheaper still;
  the full oracle was only measured here to characterize the ceiling.)
- `dd` (dd.autoref) build is structure-bound, not n-bound (~0.1–0.3 ms at n≤20 from the
  harness); ROBDD/CUDD remains unavailable on native Windows.

## 5. Feasibility ceiling

Nothing in these numbers stops at n=24. The reduced-path cost is `live_k`-bound (flat in n),
the guard cleanly caps materialization at 16 live vars, and even the *full* 2^n oracle is
only ~2.5 s at n=24 (and the full-output arrays are ~2–16 MB). The practical ceiling for the
**full-output** methods (bitset/oracle) is RAM for the 2^n array (~16 MB at n=24, doubling
per +1 n), reached well beyond n=24 on any normal machine. The **reduced CM path** has no
such ceiling — it is bounded only by `live_k ≤ 16`, independent of n.

## 6. Deliverable files

In `deliverables_n22_24/`:
- `CM_n16_24_headline.csv` — §2 (CM no-reinflate vs bitset, cached per-eval, n=16..24).
- `CM_n16_24_guard_rate.csv` — §3 (guard outcome counts by n × depth, n=18..24).
- `CM_n16_24_scaling.csv` — §4 (bitset full-output + vectorized-oracle cost, n=16..24).
- `CM_n22_24_feasibility_report.md` — this report.

Source benchmark CSVs (repo root, gitignored): `bench_n24_headline_*`, `bench_n24_profile_*`,
`bench_n24_dd_*`, plus the n=16..20 set from the prior campaign.
