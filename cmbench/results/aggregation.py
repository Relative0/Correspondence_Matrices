from __future__ import annotations

from typing import Any, Callable


def safe_median(series) -> float | None:
    try:
        return float(series.dropna().median())
    except Exception:
        return None


def safe_first(series) -> Any | None:
    try:
        values = series.dropna().tolist()
        return values[0] if values else None
    except Exception:
        return None


def safe_all(series) -> bool | None:
    try:
        values = series.dropna().tolist()
        return all(values) if values else None
    except Exception:
        return None


def safe_any(series) -> bool | None:
    try:
        values = series.dropna().tolist()
        return any(values) if values else None
    except Exception:
        return None


def build_agg_spec(
    median_cols: list[str],
    first_cols: list[str] | None = None,
    all_cols: list[str] | None = None,
    any_cols: list[str] | None = None,
) -> dict[str, tuple[str, Callable[..., Any]]]:
    spec: dict[str, tuple[str, Callable[..., Any]]] = {}
    for col in median_cols:
        spec[f"{col}_median"] = (col, safe_median)
    for col in first_cols or []:
        spec[col] = (col, safe_first)
    for col in all_cols or []:
        spec[f"{col}_all"] = (col, safe_all)
    for col in any_cols or []:
        spec[f"{col}_any"] = (col, safe_any)
    return spec
