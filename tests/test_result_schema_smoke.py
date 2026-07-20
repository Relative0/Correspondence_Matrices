import csv
import subprocess
import sys


def test_tiny_benchmark_raw_schema(tmp_path):
    out_prefix = tmp_path / "cm_bench_smoke"
    subprocess.run(
        [
            sys.executable,
            "cm_bench.py",
            "--sizes",
            "2",
            "--trials",
            "1",
            "--max-depth",
            "2",
            "--out-prefix",
            str(out_prefix),
            "--no-sympy",
            "--no-robdd",
            "--no-dd",
            "--no-espresso",
            "--no-bdd-sop",
            "--no-numba",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    raw_path = tmp_path / "cm_bench_smoke_raw.csv"
    with raw_path.open("r", newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))

    for column in ["n_vars", "trial", "expr_style", "cm_time_s", "bitset_time_s"]:
        assert column in row

