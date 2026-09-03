"""Create a development-only neural readiness artifact without training."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition.neural_reassessment import create_development_artifact


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    assessment = create_development_artifact(args.output)
    print(f"training_allowed={assessment['decision']['training_allowed']}")
    print(f"artifact={args.output}")


if __name__ == "__main__":
    main()
