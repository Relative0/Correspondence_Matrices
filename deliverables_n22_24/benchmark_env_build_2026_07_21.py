"""Fresh old-vs-vectorized bitset environment build audit."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import statistics
import sys
from time import perf_counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from bitset_backend import build_bitset_env, clear_bitset_env_cache  # noqa: E402


def old_build(vars_key: tuple[str, ...]):
    n_vars = len(vars_key)
    n_rows = 1 << n_vars
    env = {}
    for v, name in enumerate(vars_key):
        block = 1 << (n_vars - 1 - v)
        stride = block << 1
        mask = 0
        one_block = (1 << block) - 1
        for start in range(block, n_rows, stride):
            mask |= one_block << start
        env[name] = mask
    return env


def measure(fn, trials: int):
    values = []
    result = None
    for _ in range(trials):
        start = perf_counter()
        result = fn()
        values.append(perf_counter() - start)
    return result, values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="14,16,18,20,22,24")
    parser.add_argument("--new-trials", type=int, default=3)
    parser.add_argument("--old-trials", type=int, default=3)
    parser.add_argument("--old-max-n", type=int, default=20)
    parser.add_argument("--tag", default="py313")
    args = parser.parse_args()
    rows = []
    for n in [int(x) for x in args.sizes.split(",")]:
        vars_key = tuple(f"x{i}" for i in range(n))

        def new_once():
            clear_bitset_env_cache()
            return dict(build_bitset_env(vars_key))

        new_env, new_times = measure(new_once, args.new_trials)
        old_env = None
        old_times = []
        if n <= args.old_max_n:
            trials = 1 if n == args.old_max_n else args.old_trials
            old_env, old_times = measure(lambda: old_build(vars_key), trials)
        identical = old_env == new_env if old_env is not None else None
        rows.append(
            {
                "python": sys.version.split()[0],
                "n": n,
                "new_trials": len(new_times),
                "new_median_s": statistics.median(new_times),
                "new_min_s": min(new_times),
                "new_max_s": max(new_times),
                "old_trials": len(old_times),
                "old_median_s": statistics.median(old_times) if old_times else None,
                "old_min_s": min(old_times) if old_times else None,
                "old_max_s": max(old_times) if old_times else None,
                "old_over_new": (
                    statistics.median(old_times) / statistics.median(new_times) if old_times else None
                ),
                "bit_identical": identical,
            }
        )
        print(rows[-1], flush=True)
    path = HERE / f"CM_env_build_2026-07-21_{args.tag}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
