# CUDD ROBDD Extraction Report

Date: 2026-06-26

## 1. Executive Summary

CUDD did not install or import on this native Windows environment. The installed `dd` package is `0.5.7` from a pure Python wheel (`py3-none-any`), so it provides `dd.autoref` but not compiled modules `dd.cudd`, `dd.sylvan`, or `dd.buddy`.

Follow-up on 2026-06-26: Docker Desktop was running, and the Docker-backed WSL2 Linux path worked. Inside `python:3.10-slim`, `pip install dd` selected the compiled manylinux wheel, and `dd.cudd` imported successfully from `dd/cudd.cpython-310-x86_64-linux-gnu.so`. CUDD benchmarks were then run in Docker and are summarized in the addendum below. See `CUDD_WSL_install_and_benchmark_report.md` for the full Linux/Docker run log.

The benchmarks therefore used `dd.autoref` with the label:

`ROBDD/dd.autoref - AST build, best-of-k variable order`

New extraction benchmarks show a clear split:

- ROBDD symbolic build can be within the same order of magnitude as CM no-reinflate for the tested expressions.
- ROBDD build plus flat truth-table extraction is much slower, especially at `n=16`, because extraction evaluates all assignments through `dd.autoref`.
- Bitset remains the flat-output winner.
- CM no-reinflate remains the best CM path measured here.

With CUDD in Docker/Linux, symbolic ROBDD build became much faster: at `n=16`, CUDD build-only was 0.000201s for `mixed_no_constants` and 0.000138s for `balanced_all_vars`. However, CUDD build plus truth-table extraction was still dominated by extraction: 0.620295s and 0.513589s respectively at `n=16`.

## 2. CUDD Installation Attempts

| Attempt | Command | Result | Notes |
|---|---|---|---|
| Environment audit | `python - <<PY ... import dd.cudd ... PY` | `dd.autoref` OK; `dd.cudd`, `dd.sylvan`, `dd.buddy` failed | Native Windows 10, CPython 3.10.11 AMD64. |
| Installed package metadata | `python -m pip show dd` | `dd 0.5.7` installed | Location: base Python site-packages. |
| Wheel inspection | installed wheel `WHEEL` metadata | `Root-Is-Purelib: true`, `Tag: py3-none-any` | The current install is a pure Python wheel. |
| PyPI versions/files | `python -m pip index versions dd`; PyPI JSON for `dd 0.5.7` | Latest is `0.5.7`; compiled wheel available for manylinux CPython 3.10, not native Windows | Windows resolves to pure Python wheel. |
| Path A: clean venv wheel | `python -m venv .venv-cudd-wheel`; `pip install dd`; `from dd import cudd` | Failed | Installed `dd-0.5.7-py3-none-any.whl`; `ImportError: cannot import name 'cudd' from 'dd'`. |
| Source documentation inspection | unpacked `dd-0.5.7.tar.gz`; read `README.md`, `setup.py`, `download.py` | Documented path found | `python setup.py install --fetch --cudd`; `download.py` runs Unix-style `./configure` and `make` for CUDD. |
| Path B: documented native source path | `.venv-cudd-source`; `python setup.py install --fetch --cudd` | Failed before CUDD compile | Dependency install hit DNS failures, then `setup.py` failed with `ModuleNotFoundError: No module named 'pkg_resources'` under newer setuptools. The documented build path also depends on Unix-style build tools. |
| Candidate env var path | `DD_CUDD=1 ...` | Not run as a claimed supported path | No `DD_CUDD` option was found in `dd 0.5.7` setup files or docs; supported flags are `--fetch` and `--cudd`. |
| Path C: WSL/Linux | Not run locally | Recommended | PyPI has a Linux CPython 3.10 compiled wheel for `dd 0.5.7`; WSL/Linux should be the reproducible path to try next. |

Recommended WSL/Linux path:

```bash
python3 -m venv .venv-cudd
source .venv-cudd/bin/activate
python -m pip install --upgrade pip setuptools wheel cython
python -m pip install dd
python - <<'PY'
from dd import cudd
print("CUDD OK", cudd)
PY
```

Do not claim CUDD is available unless `from dd import cudd` succeeds.

## 3. Backend Identity

Environment:

| Item | Value |
|---|---|
| OS | Windows-10-10.0.19045-SP0 |
| Python | 3.10.11, MSC v.1929 64 bit (AMD64) |
| Architecture | AMD64 |
| Installed `dd` | 0.5.7 |
| Installed wheel type | Pure Python wheel, `py3-none-any` |

| Backend | Import success | Version/module | Used in benchmark |
|---|---:|---|---:|
| `dd` | yes | `dd`, version `0.5.7` | yes |
| `dd.autoref` | yes | `dd.autoref` | yes |
| `dd.cudd` | no | `ModuleNotFoundError` | no |
| `dd.sylvan` | no | `ModuleNotFoundError` | no |
| `dd.buddy` | no | `ModuleNotFoundError` | no |

## 4. Benchmark Semantics

- `robdd_build_time_s`: symbolic AST-to-ROBDD graph construction using `dd.autoref`. It does not include flat truth-table extraction.
- `robdd_tt_extract_time_s`: ROBDD-to-flat-output extraction. Current implementation iterates all `2^n` assignments in benchmark variable order and evaluates with backend restriction/evaluation.
- `robdd_total_build_plus_extract_time_s`: build plus any reorder time plus extraction time.
- `bitset_time_s`: flat packed truth-table evaluation.
- `cm_no_reinflate_time_s`: structural CM compile/evaluate path with dense CM reinflation avoided.
- `cm_cached_exec_s_per_eval`: repeated CM no-reinflate evaluation after compilation/cache.

## 5. Results: Build Only

Medians, seconds. Backend: `dd.autoref`; order: `best-of-k`; sweeps: 10.

| style | n | build_time | nodes | bitset | cm_no_reinflate | cm_cached_eval |
|---|---:|---:|---:|---:|---:|---:|
| mixed_no_constants | 4 | 0.000998 | 6 | 0.000051 | 0.000487 | 0.000245 |
| mixed_no_constants | 8 | 0.001565 | 25 | 0.000073 | 0.001588 | 0.001315 |
| mixed_no_constants | 12 | 0.003198 | 90 | 0.000120 | 0.001932 | 0.001398 |
| mixed_no_constants | 16 | 0.005725 | 307 | 0.000332 | 0.002904 | 0.002770 |
| balanced_all_vars | 4 | 0.000482 | 6 | 0.000029 | 0.000250 | 0.000140 |
| balanced_all_vars | 8 | 0.000825 | 30 | 0.000047 | 0.000858 | 0.000652 |
| balanced_all_vars | 12 | 0.001018 | 68 | 0.000065 | 0.001032 | 0.000698 |
| balanced_all_vars | 16 | 0.001732 | 162 | 0.000208 | 0.001436 | 0.001068 |

## 6. Results: Build + Truth-Table Extraction

Medians, seconds. Extraction status was `ok` and extraction correctness was `True` for all rows.

| style | n | build_plus_extract | extract_time | bitset | cm_no_reinflate | cm_cached_eval |
|---|---:|---:|---:|---:|---:|---:|
| mixed_no_constants | 4 | 0.001396 | 0.000397 | 0.000051 | 0.000487 | 0.000245 |
| mixed_no_constants | 8 | 0.009124 | 0.007559 | 0.000073 | 0.001588 | 0.001315 |
| mixed_no_constants | 12 | 0.173563 | 0.169361 | 0.000120 | 0.001932 | 0.001398 |
| mixed_no_constants | 16 | 2.818734 | 2.813987 | 0.000332 | 0.002904 | 0.002770 |
| balanced_all_vars | 4 | 0.000708 | 0.000226 | 0.000029 | 0.000250 | 0.000140 |
| balanced_all_vars | 8 | 0.004445 | 0.003603 | 0.000047 | 0.000858 | 0.000652 |
| balanced_all_vars | 12 | 0.066700 | 0.065846 | 0.000065 | 0.001032 | 0.000698 |
| balanced_all_vars | 16 | 1.134393 | 1.133145 | 0.000208 | 0.001436 | 0.001068 |

Selected ratios:

| style | n | build/bitset | build+extract/bitset | build/cm_no_reinflate | build+extract/cm_no_reinflate |
|---|---:|---:|---:|---:|---:|
| mixed_no_constants | 16 | 17.24 | 8487.61 | 1.97 | 970.71 |
| balanced_all_vars | 16 | 8.31 | 5440.74 | 1.21 | 790.08 |

## 7. Interpretation

ROBDD is not competitive with bitset as a flat output generator in this environment. Once truth-table extraction is included, `dd.autoref` is thousands of times slower than bitset at `n=16`.

ROBDD symbolic build is more competitive. At `n=16`, build-only `dd.autoref` was about 1.2x to 2.0x CM no-reinflate for these two regimes, and about 8x to 17x bitset. That is a different and fairer story than comparing symbolic construction against flat-output execution.

Extraction changes the comparison sharply. Build-only ROBDD can be presented as a symbolic construction baseline. Build plus extraction should be presented separately as a flat-output baseline, where it loses badly to bitset and CM no-reinflate in this environment.

CM no-reinflate remains the best CM path measured here. Bitset remains the flat-output winner. CUDD could change absolute ROBDD build and extraction constants, but it was not available on native Windows here, so no CUDD performance conclusion is justified.

## 8. Slide Recommendations

Use separate labels:

- `ROBDD/dd.autoref - symbolic build`
- `ROBDD/dd.autoref - build + truth-table extraction`
- `ROBDD/CUDD - symbolic build` only if `from dd import cudd` succeeds
- `ROBDD/CUDD - build + truth-table extraction` only if CUDD extraction is actually benchmarked
- `CM no-reinflate + persistent cache`
- `Bitset flat execution`

Recommended wording: "ROBDD build-only is symbolic graph construction; ROBDD build+extract is the comparable flat-output path."

## 9. Remaining Limitations

- CUDD is still unavailable on native Windows, but works in Docker/Linux on WSL2.
- Extraction is measured only up to `--robdd-tt-extract-max-n`; current benchmark used `n <= 16`.
- `best-of-k` variable ordering is not the same as CUDD dynamic reordering.
- CUDD dynamic reordering was run in Docker/Linux and reported available/used, but it is a separate fixed-order probe and not directly comparable to best-of-k.
- `dd.autoref` extraction uses assignment-by-assignment backend evaluation, so it is intentionally simple but not optimized.

## 11. Docker/Linux CUDD Addendum

Docker/WSL2 backend identity:

| Item | Value |
|---|---|
| Runtime | Docker Desktop on WSL2 |
| Image | `python:3.10-slim` |
| Python | 3.10.20 |
| Platform | Linux x86_64, glibc |
| `dd` | 0.5.7 |
| `dd.cudd` | import OK |

CUDD build-only medians:

| style | n | build_time | nodes | bitset | cm_no_reinflate | cm_cached_eval |
|---|---:|---:|---:|---:|---:|---:|
| mixed_no_constants | 16 | 0.000201 | 307 | 0.000177 | 0.001895 | 0.001183 |
| balanced_all_vars | 16 | 0.000138 | 162 | 0.000188 | 0.001688 | 0.001409 |

CUDD build+truth-table-extraction medians:

| style | n | build_plus_extract | extract_time | bitset | cm_no_reinflate | cm_cached_eval |
|---|---:|---:|---:|---:|---:|---:|
| mixed_no_constants | 16 | 0.620295 | 0.620011 | 0.000177 | 0.001895 | 0.001183 |
| balanced_all_vars | 16 | 0.513589 | 0.513460 | 0.000188 | 0.001688 | 0.001409 |

Dynamic reordering probe:

| n | order | reorder_method | reorder_available | reorder_used | build_plus_reorder | build_plus_extract | nodes |
|---:|---|---|---|---|---:|---:|---:|
| 16 | fixed | sift | true | true | 0.002964 | 0.916939 | 68 |

Interpretation update: CUDD changes the symbolic build conclusion substantially. CUDD build-only is competitive with, and often faster than, CM no-reinflate in the Docker/Linux runs. It does not change the flat-output conclusion: build+extract remains far slower than bitset and CM no-reinflate at `n=16`.

## 10. Commands Run

Benchmarks:

```bash
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 5 --expr-style mixed_no_constants --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend autoref --robdd-order-policy best-of-k --robdd-order-sweeps 10 --robdd-measure-tt-extract --robdd-tt-extract-max-n 16 --print-summary --out-prefix bench_autoref_mixed_extract
python cm_bench.py --sizes 4,8,12,16 --trials 5 --max-depth 5 --expr-style balanced_all_vars --require-nontrivial-expr --min-used-var-fraction 0.75 --min-tt-density 0.05 --max-tt-density 0.95 --cm-layout balanced --cm-compare-no-reinflate --cm-use-persistent-cache --cm-eval-repeat 50 --robdd-dd-backend autoref --robdd-order-policy best-of-k --robdd-order-sweeps 10 --robdd-measure-tt-extract --robdd-tt-extract-max-n 16 --print-summary --out-prefix bench_autoref_balanced_extract
```

Outputs:

- `bench_autoref_mixed_extract_raw.csv`
- `bench_autoref_mixed_extract_summary.csv`
- `bench_autoref_balanced_extract_raw.csv`
- `bench_autoref_balanced_extract_summary.csv`
