"""Print P7 execution-readiness reasons from the isolated V4 upload tree."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


HERE = Path(__file__).resolve().parent
BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V4-20260830.zip"
CODE = r"""
import json
from pathlib import Path
from cmbench.comparative.p7 import execution_readiness

root = Path.cwd()
freeze = json.loads(
    (root / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json")
    .read_text(encoding="utf-8")
)
print(json.dumps(execution_readiness(freeze, root), indent=2))
"""


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cm-p7-readiness-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(BUNDLE) as archive:
            archive.extractall(root)
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(root)
        environment["PYTHONNOUSERSITE"] = "1"
        completed = subprocess.run(
            [sys.executable, "-B", "-c", CODE],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
