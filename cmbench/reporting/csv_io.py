from __future__ import annotations

from pathlib import Path
from typing import Any


def write_csv(df: Any, path: str | Path, **kwargs: Any) -> None:
    df.to_csv(path, index=False, **kwargs)
