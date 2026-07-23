# CUDD WSL/Docker Install and Benchmark Report

Date: 2026-06-26

> **2026-07-23 update:** the CUDD numbers below predate the endorsed post-audit code
> state and were run in local Docker. The current apples-to-apples CUDD vs autoref vs
> CM vs Bitset comparison (matched expressions, single-invocation rows, RunPod pod)
> is §7e of `deliverables_n22_24/CM_FABLE_BENCHMARKS_2026-07-21.md`, with outputs
> `deliverables_n22_24/CM_FABLE_{cudd,autoref}_matched_headline_runpod_{raw,summary}.csv`. The environment
> findings in this report (native Windows lacks `dd.cudd`; Linux manylinux wheel
> provides it) were re-verified and still hold.

## 1. Executive Summary

| Question | Result |
|---|---|
| Is a normal Ubuntu/Debian WSL distro installed? | No. `wsl -l -v` lists only `docker-desktop`. |
| Is Docker Desktop's WSL2 Linux runtime available? | Yes. `docker-desktop` is running under WSL2. |
| Did `from dd import cudd` succeed in Linux? | Yes, inside Docker `python:3.10-slim`. |
| Which install path worked? | `pip install dd` on Linux, which selected the compiled manylinux wheel containing `dd.cudd`. |
| Were CUDD benchmarks run? | Yes: mixed, balanced-all-vars, and dynamic-reordering probe. |
| Did dynamic reordering run? | Yes. Summary columns show requested/available/used are all true for `bench_cudd_reorder_extract`. |

Native Windows still cannot import `dd.cudd`, but Docker provides a valid Linux environment on the same machine. The CUDD results below are from Linux in Docker, not native Windows.

## 2. Environment

WSL:

```text
Default Distribution: docker-desktop
Default Version: 2
```

Docker/Linux:

```text
Docker version 28.3.3
Image: python:3.10-slim
Python: 3.10.20
Platform: Linux-6.18.33.1-microsoft-standard-WSL2-x86_64-with-glibc2.41
Architecture: x86_64
dd: 0.5.7
```

Backend import results inside Docker:

| Backend | Result |
|---|---|
| `dd` | OK |
| `dd.autoref` | OK |
| `dd.cudd` | OK, loaded `dd/cudd.cpython-310-x86_64-linux-gnu.so` |
| `dd.sylvan` | `ModuleNotFoundError` |
| `dd.buddy` | `ModuleNotFoundError` |

`pyeda` did not install in `python:3.10-slim` because the image lacks `gcc`. This only disabled Espresso comparison columns; it did not affect CUDD, bitset, or CM measurements.

## 3. Commands Run

CUDD availability check:

```bash
docker run --rm python:3.10-slim bash -lc "
python -m pip install -q --upgrade pip
python -m pip install -q dd
python - <<'PY'
import importlib, importlib.metadata
print('dd_version', importlib.metadata.version('dd'))
for name in ['dd','dd.autoref','dd.cudd','dd.sylvan','dd.buddy']:
    try:
        m = importlib.import_module(name)
        print(name, 'OK', m)
    except Exception as e:
        print(name, 'FAILED', repr(e))
PY"
```

CUDD benchmarks were run with Docker mounting the repository at `/work`:

```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 5 --expr-style mixed_no_constants --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend cudd --robdd-order-policy best-of-k --robdd-order-sweeps 10 --robdd-measure-tt-extract --robdd-tt-extract-max-n 16 --print-summary --out-prefix bench_cudd_mixed_extract
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 5 --expr-style balanced_all_vars --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend cudd --robdd-order-policy best-of-k --robdd-order-sweeps 10 --robdd-measure-tt-extract --robdd-tt-extract-max-n 16 --print-summary --out-prefix bench_cudd_balanced_extract
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 5 --expr-style mixed_no_constants --require-nontrivial-expr --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend cudd --robdd-order-policy fixed --robdd-dynamic-reordering --robdd-reorder-method sift --robdd-measure-tt-extract --print-summary --out-prefix bench_cudd_reorder_extract
```

## 4. Output Files

- `bench_cudd_mixed_extract_raw.csv`
- `bench_cudd_mixed_extract_summary.csv`
- `bench_cudd_balanced_extract_raw.csv`
- `bench_cudd_balanced_extract_summary.csv`
- `bench_cudd_reorder_extract_raw.csv`
- `bench_cudd_reorder_extract_summary.csv`

## 5. CUDD Build Only

Medians, seconds. Backend: `dd.cudd`; order: `best-of-k`; sweeps: 10.

| style | n | build_time | nodes | bitset | cm_no_reinflate | cm_cached_eval |
|---|---:|---:|---:|---:|---:|---:|
| mixed_no_constants | 4 | 0.000093 | 6 | 0.000036 | 0.000210 | 0.000121 |
| mixed_no_constants | 8 | 0.000105 | 25 | 0.000045 | 0.001016 | 0.000659 |
| mixed_no_constants | 12 | 0.000136 | 90 | 0.000068 | 0.000867 | 0.000724 |
| mixed_no_constants | 16 | 0.000201 | 307 | 0.000177 | 0.001895 | 0.001183 |
| balanced_all_vars | 4 | 0.000096 | 6 | 0.000036 | 0.000226 | 0.000134 |
| balanced_all_vars | 8 | 0.000105 | 30 | 0.000043 | 0.000923 | 0.000585 |
| balanced_all_vars | 12 | 0.000107 | 68 | 0.000069 | 0.001062 | 0.000671 |
| balanced_all_vars | 16 | 0.000138 | 162 | 0.000188 | 0.001688 | 0.001409 |

## 6. CUDD Build + Truth-Table Extraction

Medians, seconds. Extraction status was `ok`; extraction correctness was `True` for all rows.

| style | n | build_plus_extract | extract_time | bitset | cm_no_reinflate | cm_cached_eval |
|---|---:|---:|---:|---:|---:|---:|
| mixed_no_constants | 4 | 0.000159 | 0.000067 | 0.000036 | 0.000210 | 0.000121 |
| mixed_no_constants | 8 | 0.001162 | 0.001078 | 0.000045 | 0.001016 | 0.000659 |
| mixed_no_constants | 12 | 0.024006 | 0.023910 | 0.000068 | 0.000867 | 0.000724 |
| mixed_no_constants | 16 | 0.620295 | 0.620011 | 0.000177 | 0.001895 | 0.001183 |
| balanced_all_vars | 4 | 0.000160 | 0.000064 | 0.000036 | 0.000226 | 0.000134 |
| balanced_all_vars | 8 | 0.001223 | 0.001119 | 0.000043 | 0.000923 | 0.000585 |
| balanced_all_vars | 12 | 0.023242 | 0.023101 | 0.000069 | 0.001062 | 0.000671 |
| balanced_all_vars | 16 | 0.513589 | 0.513460 | 0.000188 | 0.001688 | 0.001409 |

Selected ratios:

| style | n | build/bitset | build+extract/bitset | build/cm_no_reinflate | build+extract/cm_no_reinflate |
|---|---:|---:|---:|---:|---:|
| mixed_no_constants | 16 | 1.13 | 3508.22 | 0.11 | 327.34 |
| balanced_all_vars | 16 | 0.73 | 2727.29 | 0.08 | 304.23 |

## 7. Dynamic Reordering Probe

Command used `--robdd-order-policy fixed --robdd-dynamic-reordering --robdd-reorder-method sift`.

| n | build_time | reorder_time | build_plus_reorder | extract_time | build_plus_extract | nodes | reordering_used |
|---:|---:|---:|---:|---:|---:|---:|---|
| 4 | 0.000151 | 0.001207 | 0.001407 | 0.000054 | 0.001461 | 6 | true |
| 8 | 0.000127 | 0.001553 | 0.001665 | 0.001368 | 0.002868 | 20 | true |
| 12 | 0.000173 | 0.001731 | 0.001872 | 0.034789 | 0.036739 | 62 | true |
| 16 | 0.000274 | 0.002636 | 0.002964 | 0.912354 | 0.916939 | 68 | true |

Dynamic reordering was available and used according to the summary fields. It reduced nodes for the mixed `n=16` fixed-order probe, but the probe is not directly comparable to the best-of-k run because order policy and reordering overhead differ.

## 8. Interpretation

CUDD materially improves symbolic ROBDD construction in the Docker/Linux environment. At `n=16`, CUDD build-only is faster than CM no-reinflate and close to bitset for these expression regimes.

CUDD does not make ROBDD competitive as a flat-output generator at `n=16` with assignment-by-assignment extraction. Build+extract remains hundreds to thousands of times slower than bitset, and hundreds of times slower than CM no-reinflate in these runs.

Use CUDD build-only and CUDD build+extract as separate slide series. The build-only series answers the symbolic graph-construction question. The build+extract series answers the flat-output question.

## 9. Limitations

- Results are from Docker/Linux on WSL2, not native Windows.
- There is no normal Ubuntu/Debian WSL user distro installed; Docker is the working Linux path.
- `pyeda`/Espresso columns are absent in Docker because `pyeda` failed to compile without `gcc`.
- Autoref numbers in the earlier report were collected on native Windows, so CUDD-vs-autoref speedup comparisons are cross-environment unless autoref is rerun in the same Docker image.
- Extraction remains the simple all-assignments evaluator.

