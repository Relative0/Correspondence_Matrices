import csv
import subprocess
import sys
from pathlib import Path


def test_tiny_cli_run_writes_expected_raw_and_summary_files(tmp_path) -> None:
    script = Path(__file__).resolve().parents[1] / "cm_bench.py"
    out_prefix = tmp_path / "phase5_tiny"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--sizes",
            "3",
            "--trials",
            "1",
            "--max-depth",
            "2",
            "--out-prefix",
            str(out_prefix),
            "--no-sympy",
            "--no-espresso",
            "--no-bdd-sop",
            "--no-numba",
            "--no-dd",
            "--no-robdd-dd",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw_path = Path(f"{out_prefix}_raw.csv")
    summary_path = Path(f"{out_prefix}_summary.csv")
    assert raw_path.exists()
    assert summary_path.exists()
    with raw_path.open(newline="") as f:
        raw_rows = list(csv.DictReader(f))
    with summary_path.open(newline="") as f:
        summary_rows = list(csv.DictReader(f))
    assert raw_rows
    assert summary_rows
    assert {"n_vars", "trial", "expr_style", "cm_time_s", "bitset_time_s"} <= set(raw_rows[0])
    assert {"n_vars", "cm_time_s_median", "bitset_time_s_median", "trials"} <= set(summary_rows[0])
