import subprocess
import sys


def test_cli_help_smoke():
    proc = subprocess.run(
        [sys.executable, "cm_bench.py", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--sizes" in proc.stdout
    assert "--trials" in proc.stdout

