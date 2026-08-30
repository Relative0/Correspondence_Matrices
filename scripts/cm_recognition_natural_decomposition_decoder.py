"""Run the validation-only minimum-cut decoder follow-up."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.natural_decomposition_decoder_experiment import (
    DEFAULT_BASE_RUN, DecoderConfig, run_decoder_experiment,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE_RUN)
    args = parser.parse_args(argv)
    result = run_decoder_experiment(DecoderConfig(), args.output, args.base)
    print(json.dumps({"status": result["status"], "criteria": result["criteria"],
                      "wall_seconds": result["wall_seconds"], "row_count": result["row_count"]}))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
