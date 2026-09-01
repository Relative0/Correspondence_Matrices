"""Compile a frozen C19 exact-arm tree into a small immutable selector."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .gf2_work_policy import cheap_truth_features, validate_policy


Program = tuple[Any, ...]


def _compile_tree(tree: dict[str, Any]) -> Program:
    if tree["kind"] == "leaf":
        return ("leaf", tree["arm"])
    return (
        "split",
        tree["feature"],
        tree["threshold"],
        _compile_tree(tree["le"]),
        _compile_tree(tree["gt"]),
    )


def _validate_truth_shape(bits: int, n_vars: int) -> None:
    if (
        type(n_vars) is not int
        or not 2 <= n_vars <= 10
        or type(bits) is not int
        or bits < 0
        or bits.bit_length() > (1 << n_vars)
    ):
        raise ValueError("invalid bounded compiled-policy truth vector")


@dataclass(frozen=True)
class CompiledGF2WorkPolicy:
    policy_sha256: str
    selected_candidate: str
    mode: str
    program: Program
    constant_arm: str | None
    requires_features: bool

    def select(self, bits: int, n_vars: int) -> str:
        _validate_truth_shape(bits, n_vars)
        if self.constant_arm is not None:
            return self.constant_arm
        features = cheap_truth_features(bits, n_vars)
        node = self.program
        while node[0] == "split":
            node = node[3] if features[node[1]] <= node[2] else node[4]
        return node[1]


def compile_work_policy(policy: dict[str, Any]) -> CompiledGF2WorkPolicy:
    """Validate and constant-fold a frozen exact-arm policy."""
    validate_policy(policy)
    program = _compile_tree(policy["tree"])
    constant_arm = program[1] if program[0] == "leaf" else None
    return CompiledGF2WorkPolicy(
        policy_sha256=policy["policy_sha256"],
        selected_candidate=policy["selected_candidate"],
        mode="constant_leaf" if constant_arm is not None else "feature_tree",
        program=program,
        constant_arm=constant_arm,
        requires_features=constant_arm is None,
    )

