# CM Bench Profiling Harness

These commands are for profiling only; they are not part of automated tests.

## Small Full Truth Tables

```bash
python -m cProfile -o prof_single_expr.prof cm_bench.py --sizes 8,12 --trials 5 --max-depth 4 --cm-compare-no-reinflate

python - <<'PY'
import pstats
p = pstats.Stats("prof_single_expr.prof")
p.strip_dirs().sort_stats("cumtime").print_stats(40)
PY
```

## Medium No-Reinflate

```bash
python -m cProfile -o prof_no_reinflate.prof cm_bench.py --sizes 12,16 --trials 5 --max-depth 4 --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 10
```

## Expression Family

```bash
python -m cProfile -o prof_family.prof cm_bench.py --bench-expression-family --sizes 8 --trials 3 --max-depth 4 --family-size 20 --cm-use-persistent-cache
```

## Partial Context

```bash
python -m cProfile -o prof_partial.prof cm_bench.py --bench-partial-contexts --sizes 10 --trials 3 --max-depth 4 --partial-contexts 50
```

## Equivalence

```bash
python -m cProfile -o prof_equiv.prof cm_bench.py --bench-equivalence --sizes 8 --trials 5 --max-depth 4 --equiv-backends all
```

## ROBDD Best-Of-K

```bash
python -m cProfile -o prof_robdd_bestofk.prof cm_bench.py --sizes 8,12 --trials 3 --max-depth 4 --compare-robdd-cm --robdd-order-sweeps 10
```

## CM Persistent Cache Warm Run

```bash
python cm_bench.py --sizes 8,12 --trials 2 --max-depth 4 --cm-compare-no-reinflate --cm-use-persistent-cache --out-prefix warmup_cache
python -m cProfile -o prof_cache_warm.prof cm_bench.py --sizes 8,12 --trials 5 --max-depth 4 --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 20
```

## Sampling Profilers

```bash
py-spy record -o profile_single.svg -- python cm_bench.py --sizes 8,12 --trials 10 --max-depth 4 --compare-robdd-cm

scalene cm_bench.py --sizes 8,12 --trials 5 --max-depth 4 --cm-compare-no-reinflate
```
