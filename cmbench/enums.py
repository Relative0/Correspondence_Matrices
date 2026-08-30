from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class ROBDDOrderPolicy(StrEnum):
    FIXED = "fixed"
    EXPR = "expr"
    INTERACTION = "interaction"
    RANDOM = "random"
    BEST_OF_K = "best-of-k"


class PartialOutputMode(StrEnum):
    REMAINING_VARS = "remaining-vars"
    FULL_VARS = "full-vars"


class CMExecTarget(StrEnum):
    LOCAL = "local"
    RUNPOD = "runpod"


class BackendStatus(StrEnum):
    OK = "ok"
    SKIPPED = "skipped"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

