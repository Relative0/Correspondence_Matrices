import csv
import subprocess
import sys


def test_tiny_benchmark_reports_correctness_reference_columns(tmp_path):
    out_prefix = tmp_path / "cm_bench_ref"
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

    with (tmp_path / "cm_bench_ref_raw.csv").open("r", newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))

    assert row["correctness_reference"] == "eval_expr_tt"
    assert row["tt_ref_available"] == "True"
    assert row["tt_ref_source"] == "generate_benchmark_expr"

