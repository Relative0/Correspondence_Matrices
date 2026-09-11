"""Opt-in, byte-bounded positional truth-column reuse.

The budget covers admitted column payload (width keys, column tuples and integer
columns), not allocator RSS, LRU bookkeeping, in-flight builds or caller-held environments.
Evicted columns stay alive while callers retain them. No global cache is used.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping, Sequence
import sys
import threading
from types import MappingProxyType

from bitset_backend import _build_bitset_env_cached


def ordered_basis(names: Sequence[str]) -> tuple[str, ...]:
    if isinstance(names, (str, bytes)):
        raise ValueError("basis must be a sequence of names, not a string")
    basis = tuple(names)
    if any(not isinstance(name, str) or not name for name in basis):
        raise ValueError("basis names must be nonempty strings")
    if len(set(basis)) != len(basis):
        raise ValueError("basis names must be unique")
    return basis


class PackedMaskCache:
    """Share immutable columns across renamed bases, with an explicit LRU budget.

    ``max_width`` bounds every build, including nonadmitted entries. Builds and
    clears serialize under one lock, so concurrent misses cannot multiply the
    build workspace. A zero byte budget is an uncached, guarded builder.
    """

    def __init__(self, *, max_bytes: int, max_width: int = 20) -> None:
        if type(max_bytes) is not int or max_bytes < 0:
            raise ValueError("max_bytes must be a nonnegative integer")
        if type(max_width) is not int or not 0 <= max_width <= 30:
            raise ValueError("max_width must be an integer from 0 through 30")
        self._max_bytes = max_bytes
        self._max_width = max_width
        self._entries: OrderedDict[int, tuple[tuple[int, ...], int]] = OrderedDict()
        self._lock = threading.RLock()
        self._bytes = self._hits = self._misses = self._evictions = self._bypasses = 0

    @property
    def max_width(self) -> int:
        return self._max_width

    def columns(self, width: int) -> tuple[int, ...]:
        if type(width) is not int or not 0 <= width <= self._max_width:
            raise ValueError("mask width exceeds the configured build limit")
        with self._lock:
            entry = self._entries.get(width)
            if entry is not None:
                self._hits += 1
                self._entries.move_to_end(width)
                return entry[0]
            self._misses += 1
            # Bypass the named global LRU; this cache owns all admitted columns.
            env = _build_bitset_env_cached.__wrapped__(
                tuple(f"x{i}" for i in range(width))
            )
            columns = tuple(env.values())
            size = sys.getsizeof(width) + sys.getsizeof(columns)
            size += sum(sys.getsizeof(value) for value in columns)
            if size > self._max_bytes:
                self._bypasses += 1
                return columns
            while self._entries and self._bytes + size > self._max_bytes:
                _key, (_old_columns, old_size) = self._entries.popitem(last=False)
                self._bytes -= old_size
                self._evictions += 1
            self._entries[width] = (columns, size)
            self._bytes += size
            return columns

    def environment(self, names: Sequence[str]) -> Mapping[str, int]:
        basis = ordered_basis(names)
        return MappingProxyType(dict(zip(basis, self.columns(len(basis)))))

    def clear(self) -> None:
        """Release cache-owned columns and reset counters, serialized with builds."""
        with self._lock:
            self._entries.clear()
            self._bytes = self._hits = self._misses = self._evictions = self._bypasses = 0

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "entry_bytes": self._bytes, "max_bytes": self._max_bytes,
                "entries": len(self._entries), "hits": self._hits,
                "misses": self._misses, "evictions": self._evictions,
                "bypasses": self._bypasses,
            }
