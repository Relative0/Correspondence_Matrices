"""Strict contracts for the staged CM comparative benchmark program.

Importing this package performs no benchmark, dependency install, network
operation, or process launch.
"""

from .contracts import (
    ARTIFACT_KINDS,
    LIFECYCLES,
    RESULT_STATUSES,
    TASKS,
    ContractError,
    canonical_bytes,
    contract_digest,
    validate_contract,
    validate_result,
)

__all__ = (
    "ARTIFACT_KINDS",
    "LIFECYCLES",
    "RESULT_STATUSES",
    "TASKS",
    "ContractError",
    "canonical_bytes",
    "contract_digest",
    "validate_contract",
    "validate_result",
)
