"""Small read-only property check of a local CM checkout.

The current workspace is checked by default. Pass ``--repo PATH`` to check a
different supplied checkout. This is not a benchmark.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument(
    "--repo",
    type=Path,
    default=Path(__file__).resolve().parents[2],
    help="CM repository to import (default: current CM_Computation workspace)",
)
args = parser.parse_args()
REPO = args.repo.resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO))

from cm_build import eval_cm_boolean  # noqa: E402
from cm_build_lazy import compile_expr_to_cm_lazy  # noqa: E402
from cm_exprlib import all_assignments_tt, eval_expr_tt, random_expr  # noqa: E402
from cm_normalize import canonical_layout, combine_pointwise  # noqa: E402


def main() -> None:
    rng = np.random.default_rng(20260914)
    checked = 0
    failures: list[dict[str, object]] = []

    for n_vars in range(1, 9):
        names = [f"x{i}" for i in range(n_vars)]
        rows, cols = canonical_layout(names)
        assignments = all_assignments_tt(n_vars)
        for _ in range(50):
            expr = random_expr(n_vars, rng, max_depth=5)
            cm = compile_expr_to_cm_lazy(expr, rows, cols, fixed={})
            observed = np.array(
                [
                    eval_cm_boolean(
                        cm,
                        rows,
                        cols,
                        {names[i]: int(assignment[i]) for i in range(n_vars)},
                        {},
                    )
                    for assignment in assignments
                ],
                dtype=np.uint8,
            )
            expected = eval_expr_tt(expr, n_vars)
            checked += 1
            if not np.array_equal(observed, expected):
                failures.append({"n_vars": n_vars, "expr": repr(expr)})
                break

    left = np.array([[True, False], [False, True]], dtype=bool)
    right = np.array([[False, False], [True, True]], dtype=bool)
    original_left = left.copy()
    combine_pointwise(left, right, "XOR")

    print(
        json.dumps(
            {
                "local_repo": str(REPO),
                "random_expressions_checked": checked,
                "truth_table_failures": failures,
                "all_random_checks_passed": not failures,
                "combine_pointwise_mutates_first_argument": not np.array_equal(left, original_left),
                "scope_note": (
                    "Random finite checks are not a general proof or a performance result. "
                    "The mutation diagnostic matters only if callers reuse the first array."
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
