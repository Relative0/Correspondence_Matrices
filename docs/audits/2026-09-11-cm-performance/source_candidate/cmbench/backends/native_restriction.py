"""Guarded exact native restriction engines with deterministic Python fallback."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
from typing import Any

from cmbench.comparative.gf2_native_slots import (
    NativeMultiRootArena,
    NativeSlotArena,
    compile_native_multi_root_arena,
    compile_native_slot_arena,
    load_native_slot_library,
)
from cmbench.comparative.gf2_restricted_evaluators import (
    RestrictedArena,
    compile_restricted_arena,
    eval_restricted_r2,
    prepare_restriction,
)


FEATURE_ENV = "CM_NATIVE_FUSED_SLOTS"
LIBRARY_ENV = "CM_NATIVE_FUSED_SLOTS_LIBRARY"
SHA256_ENV = "CM_NATIVE_FUSED_SLOTS_SHA256"
_TRUE = frozenset(("1", "true", "yes", "on"))
_FALSE = frozenset(("", "0", "false", "no", "off"))
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class NativeRestrictionConfig:
    enabled: bool
    library_path: Path | None = None
    expected_sha256: str | None = None

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None,
    ) -> "NativeRestrictionConfig":
        values = os.environ if environment is None else environment
        flag = values.get(FEATURE_ENV, "").strip().lower()
        if flag in _FALSE:
            return cls(enabled=False)
        if flag not in _TRUE:
            return cls(enabled=False)
        raw_path = values.get(LIBRARY_ENV, "").strip()
        expected = values.get(SHA256_ENV, "").strip().lower()
        return cls(
            enabled=True,
            library_path=Path(raw_path) if raw_path else None,
            expected_sha256=expected or None,
        )


@dataclass(frozen=True)
class NativeRestrictionStatus:
    requested: bool
    active: bool
    backend: str
    fallback_reason: str | None
    library_sha256: str | None
    abi_version: int | None


def _load_guarded(config: NativeRestrictionConfig):
    if not config.enabled:
        return None, NativeRestrictionStatus(
            False, False, "python_r2", "feature_disabled", None, None,
        )
    if config.library_path is None or config.expected_sha256 is None:
        return None, NativeRestrictionStatus(
            True, False, "python_r2", "missing_library_or_sha256", None, None,
        )
    expected = config.expected_sha256.lower()
    if _SHA256.fullmatch(expected) is None:
        return None, NativeRestrictionStatus(
            True, False, "python_r2", "invalid_expected_sha256", None, None,
        )
    try:
        path = config.library_path.resolve(strict=True)
        if not path.is_file():
            raise FileNotFoundError(path)
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            return None, NativeRestrictionStatus(
                True, False, "python_r2", "library_sha256_mismatch",
                observed, None,
            )
        library = load_native_slot_library(path)
    except (OSError, RuntimeError, ValueError):
        return None, NativeRestrictionStatus(
            True, False, "python_r2", "library_load_or_abi_failure", None, None,
        )
    if library.sha256 != expected or library.abi_version != 1:
        return None, NativeRestrictionStatus(
            True, False, "python_r2", "library_identity_or_abi_mismatch",
            library.sha256, library.abi_version,
        )
    return library, NativeRestrictionStatus(
        True, True, "native_fused_slots", None,
        library.sha256, library.abi_version,
    )


def _validate_partition(
    variable_count: int, fixed: Mapping[str, int], remaining: Sequence[str],
) -> tuple[dict[str, int], tuple[str, ...]]:
    fixed_values = dict(fixed)
    remaining_values = tuple(remaining)
    expected = {f"x{index}" for index in range(variable_count)}
    if (
        not fixed_values or not remaining_values
        or set(fixed_values).intersection(remaining_values)
        or set(fixed_values).union(remaining_values) != expected
        or len(remaining_values) != len(set(remaining_values))
        or any(type(value) is not int or value not in (0, 1)
               for value in fixed_values.values())
    ):
        raise ValueError("invalid exact restriction partition")
    return fixed_values, remaining_values


class ExactRestrictionEngine:
    """One-root exact engine. Native is opt-in; Python R2 is always available."""

    def __init__(
        self,
        document: Mapping[str, Any],
        variable_count: int,
        config: NativeRestrictionConfig | None = None,
    ) -> None:
        self.variable_count = int(variable_count)
        if self.variable_count <= 1:
            raise ValueError("variable_count must exceed one")
        self._fallback: RestrictedArena = compile_restricted_arena(document)
        library, status = _load_guarded(config or NativeRestrictionConfig(False))
        self.status = status
        self._native: NativeSlotArena | None = None
        if library is not None:
            try:
                self._native = compile_native_slot_arena(
                    document, library, variable_count=self.variable_count,
                )
            except (ValueError, RuntimeError):
                self.status = NativeRestrictionStatus(
                    True, False, "python_r2", "native_compile_failure",
                    library.sha256, library.abi_version,
                )

    def evaluate(self, fixed: Mapping[str, int], remaining: Sequence[str]) -> int:
        fixed_values, remaining_values = _validate_partition(
            self.variable_count, fixed, remaining,
        )
        if self._native is not None:
            try:
                bindings = self._native.prepare_bindings(fixed_values, remaining_values)
                return self._native.evaluate(bindings, len(remaining_values))
            except (ValueError, RuntimeError, OSError):
                # A native call never changes the exact result contract.
                self._native = None
                self.status = NativeRestrictionStatus(
                    True, False, "python_r2", "native_runtime_failure",
                    self.status.library_sha256, self.status.abi_version,
                )
        prepared = prepare_restriction(fixed_values, remaining_values)
        return eval_restricted_r2(self._fallback, prepared)


class ExactMultiRootRestrictionEngine:
    """Multi-root union engine with separate Python R2 roots as exact fallback."""

    def __init__(
        self,
        union_document: Mapping[str, Any],
        separate_documents: Sequence[Mapping[str, Any]],
        variable_count: int,
        config: NativeRestrictionConfig | None = None,
    ) -> None:
        self.variable_count = int(variable_count)
        documents = tuple(separate_documents)
        if self.variable_count <= 1 or len(documents) < 2:
            raise ValueError("invalid multi-root exact engine")
        self._fallback = tuple(compile_restricted_arena(value) for value in documents)
        library, status = _load_guarded(config or NativeRestrictionConfig(False))
        self.status = status
        self._native: NativeMultiRootArena | None = None
        if library is not None and library.supports_multi_root:
            try:
                candidate = compile_native_multi_root_arena(
                    union_document, library, variable_count=self.variable_count,
                )
                if candidate.root_count != len(documents):
                    raise ValueError("multi-root output count mismatch")
                self._native = candidate
            except (ValueError, RuntimeError):
                self.status = NativeRestrictionStatus(
                    True, False, "python_r2", "native_multi_root_compile_failure",
                    library.sha256, library.abi_version,
                )
        elif library is not None:
            self.status = NativeRestrictionStatus(
                True, False, "python_r2", "native_multi_root_abi_missing",
                library.sha256, library.abi_version,
            )

    def evaluate(
        self, fixed: Mapping[str, int], remaining: Sequence[str],
    ) -> tuple[int, ...]:
        fixed_values, remaining_values = _validate_partition(
            self.variable_count, fixed, remaining,
        )
        if self._native is not None:
            try:
                bindings = self._native.prepare_bindings(fixed_values, remaining_values)
                return self._native.evaluate(bindings, len(remaining_values))
            except (ValueError, RuntimeError, OSError):
                self._native = None
                self.status = NativeRestrictionStatus(
                    True, False, "python_r2", "native_multi_root_runtime_failure",
                    self.status.library_sha256, self.status.abi_version,
                )
        prepared = prepare_restriction(fixed_values, remaining_values)
        return tuple(eval_restricted_r2(arena, prepared) for arena in self._fallback)
