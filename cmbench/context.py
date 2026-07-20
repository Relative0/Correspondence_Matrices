from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

from .availability import BackendAvailability
from .config import BenchmarkConfig
from bitset_backend import build_bitset_env
from cm_exprlib import eval_expr_tt
from cm_ir import expr_structural_hash
from cm_normalize import canonical_layout as build_canonical_layout


@dataclass
class BenchmarkRunContext:
    config: BenchmarkConfig
    rng: np.random.Generator
    sample_rng: np.random.Generator
    availability: BackendAvailability

    var_names_by_n: dict[int, tuple[str, ...]] = field(default_factory=dict)
    var_maps_by_n: dict[int, dict[str, str]] = field(default_factory=dict)
    bitset_env_by_n: dict[int, Mapping[str, int]] = field(default_factory=dict)
    eval_grid_by_n: dict[int, np.ndarray] = field(default_factory=dict)
    layout_by_key: dict[tuple[int, str], tuple[list[str], list[str]]] = field(default_factory=dict)
    truth_table_by_key: dict[tuple[str, int], np.ndarray] = field(default_factory=dict)

    def var_names(self, n: int) -> tuple[str, ...]:
        if n not in self.var_names_by_n:
            self.var_names_by_n[n] = tuple(f"x{i}" for i in range(n))
        return self.var_names_by_n[n]

    def var_name_map(self, n: int) -> dict[str, str]:
        if n not in self.var_maps_by_n:
            names = self.var_names(n)
            self.var_maps_by_n[n] = {name: name for name in names}
        return self.var_maps_by_n[n]

    def bitset_env(self, n: int) -> Mapping[str, int]:
        if n not in self.bitset_env_by_n:
            self.bitset_env_by_n[n] = build_bitset_env(list(self.var_names(n)))
        return self.bitset_env_by_n[n]

    def eval_grid(self, n: int) -> np.ndarray:
        if n not in self.eval_grid_by_n:
            rows = 1 << n
            self.eval_grid_by_n[n] = np.array(
                [[(r >> (n - 1 - c)) & 1 for c in range(n)] for r in range(rows)],
                dtype=np.uint8,
            )
        return self.eval_grid_by_n[n]

    def canonical_layout(self, n: int, mode: str):
        key = (n, mode)
        if key not in self.layout_by_key:
            self.layout_by_key[key] = build_canonical_layout(list(self.var_names(n)), mode=mode)
        return self.layout_by_key[key]

    def get_or_compute_tt(self, expr, n: int, key: str | None = None) -> np.ndarray:
        if key is None:
            try:
                key = str(expr_structural_hash(expr))
            except Exception:
                key = repr(expr)
        cache_key = (key, n)
        if cache_key not in self.truth_table_by_key:
            self.truth_table_by_key[cache_key] = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
        return self.truth_table_by_key[cache_key]


def make_context(config: BenchmarkConfig, availability: BackendAvailability) -> BenchmarkRunContext:
    return BenchmarkRunContext(
        config=config,
        rng=np.random.default_rng(config.seed),
        sample_rng=np.random.default_rng(config.seed + 1_000_003),
        availability=availability,
    )
