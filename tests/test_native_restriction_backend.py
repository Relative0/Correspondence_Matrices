from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Not, Or, Var, Xor
from cmbench.backends.native_restriction import (
    FEATURE_ENV,
    LIBRARY_ENV,
    SHA256_ENV,
    ExactMultiRootRestrictionEngine,
    ExactRestrictionEngine,
    NativeRestrictionConfig,
)
from cmbench.comparative.gf2_multi_root import expressions_to_multi_root_dag


ROOT = Path(__file__).resolve().parents[1]
FROZEN_LIBRARY = (
    ROOT / "docs/recognition/c37_native_exact_confirmation/"
    "frozen_native_v3/cm_fused_slots.dll"
)


def expression():
    shared = Xor(Var(0), Var(1))
    return Or(And(shared, Var(2)), And(shared, Not(Var(3))))


def restriction():
    return {"x0": 1, "x3": 0}, ("x1", "x2")


def test_feature_is_disabled_by_default_and_python_fallback_is_exact() -> None:
    engine = ExactRestrictionEngine(expr_to_json_dag(expression()), 4)
    fixed, remaining = restriction()
    assert engine.status.requested is False
    assert engine.status.backend == "python_r2"
    assert engine.evaluate(fixed, remaining) == 0b0011


def test_environment_requires_explicit_path_and_hash() -> None:
    config = NativeRestrictionConfig.from_environment({FEATURE_ENV: "1"})
    engine = ExactRestrictionEngine(expr_to_json_dag(expression()), 4, config)
    assert engine.status.requested is True
    assert engine.status.active is False
    assert engine.status.fallback_reason == "missing_library_or_sha256"


def test_changed_native_binary_is_refused_before_loading(tmp_path: Path) -> None:
    changed = tmp_path / "changed.dll"
    changed.write_bytes(b"not a native library")
    config = NativeRestrictionConfig(True, changed, "0" * 64)
    engine = ExactRestrictionEngine(expr_to_json_dag(expression()), 4, config)
    assert engine.status.active is False
    assert engine.status.fallback_reason == "library_sha256_mismatch"
    assert engine.evaluate(*restriction()) == 0b0011


def test_multi_root_python_fallback_preserves_output_order() -> None:
    roots = (expression(), Xor(Var(0), Var(2)), And(Var(1), Var(3)))
    engine = ExactMultiRootRestrictionEngine(
        expressions_to_multi_root_dag(roots),
        tuple(expr_to_json_dag(root) for root in roots),
        4,
    )
    assert engine.evaluate(*restriction()) == (0b0011, 0b0101, 0)


@pytest.mark.skipif(not FROZEN_LIBRARY.is_file(), reason="frozen Windows DLL unavailable")
def test_confirmed_library_activates_only_with_matching_sha256() -> None:
    expected = hashlib.sha256(FROZEN_LIBRARY.read_bytes()).hexdigest()
    config = NativeRestrictionConfig.from_environment({
        FEATURE_ENV: "true",
        LIBRARY_ENV: str(FROZEN_LIBRARY),
        SHA256_ENV: expected,
    })
    engine = ExactRestrictionEngine(expr_to_json_dag(expression()), 4, config)
    assert engine.status.active is True
    assert engine.status.library_sha256 == expected
    assert engine.evaluate(*restriction()) == 0b0011


@pytest.mark.skipif(not FROZEN_LIBRARY.is_file(), reason="frozen Windows DLL unavailable")
def test_confirmed_multi_root_union_activates_and_preserves_order() -> None:
    roots = (expression(), Xor(Var(0), Var(2)), And(Var(1), Var(3)))
    config = NativeRestrictionConfig(
        True,
        FROZEN_LIBRARY,
        hashlib.sha256(FROZEN_LIBRARY.read_bytes()).hexdigest(),
    )
    engine = ExactMultiRootRestrictionEngine(
        expressions_to_multi_root_dag(roots),
        tuple(expr_to_json_dag(root) for root in roots),
        4,
        config,
    )
    assert engine.status.active is True
    assert engine.evaluate(*restriction()) == (0b0011, 0b0101, 0)


def test_invalid_partition_is_rejected_before_either_backend() -> None:
    engine = ExactRestrictionEngine(expr_to_json_dag(expression()), 4)
    with pytest.raises(ValueError, match="partition"):
        engine.evaluate({"x0": 1}, ("x1", "x2"))


def test_native_runtime_failure_permanently_falls_back_exactly() -> None:
    class BrokenNative:
        def prepare_bindings(self, fixed, remaining):
            raise RuntimeError("simulated native failure")

    engine = ExactRestrictionEngine(expr_to_json_dag(expression()), 4)
    engine._native = BrokenNative()
    engine.status = engine.status.__class__(
        True, True, "native_fused_slots", None, "a" * 64, 1,
    )
    assert engine.evaluate(*restriction()) == 0b0011
    assert engine.status.active is False
    assert engine.status.fallback_reason == "native_runtime_failure"
    assert engine._native is None
