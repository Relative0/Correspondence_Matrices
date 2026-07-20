from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def measure(fn: Callable[[], T]) -> tuple[T, float]:
    t0 = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - t0

