from __future__ import annotations

from dataclasses import dataclass, field
import importlib
from typing import Mapping


@dataclass(frozen=True)
class BackendAvailability:
    dd_cudd: bool = False
    dd_autoref: bool = False
    pyeda: bool = False
    sympy: bool = False
    numba: bool = False
    cm_lazy: bool = False
    cm_pair: bool = False
    runpod_modules: bool = False
    errors: Mapping[str, str] = field(default_factory=dict)


def _try_import(name: str, errors: dict[str, str]) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception as exc:
        errors[name] = repr(exc)
        return False


def detect_backends() -> BackendAvailability:
    errors: dict[str, str] = {}
    runpod_modules = _try_import("cm_runpod_config", errors) and _try_import("cm_remote_executor", errors)
    return BackendAvailability(
        dd_cudd=_try_import("dd.cudd", errors),
        dd_autoref=_try_import("dd.autoref", errors),
        pyeda=_try_import("pyeda", errors),
        sympy=_try_import("sympy", errors),
        numba=_try_import("numba", errors),
        cm_lazy=_try_import("cm_build_lazy", errors),
        cm_pair=_try_import("cm_build_pair", errors),
        runpod_modules=runpod_modules,
        errors=errors,
    )

