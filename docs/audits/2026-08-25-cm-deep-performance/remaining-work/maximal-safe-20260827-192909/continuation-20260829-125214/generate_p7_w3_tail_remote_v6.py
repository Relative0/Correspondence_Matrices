"""Generate immutable remote programs for the final bounded W3 development tail."""

from __future__ import annotations

from pathlib import Path

from generate_p7_w3_split_remote_v4 import build


HERE = Path(__file__).resolve().parent
PARTITIONS = {
    "ir-development-b-light": ("p7-ir", 17, 15),
    "ir-development-sqrt": ("p7-ir", 32, 1),
    "ir-development-square": ("p7-ir", 33, 1),
    "relation-development-a": ("p7-relation", 0, 17),
    "relation-development-b-light": ("p7-relation", 17, 15),
    "relation-development-sqrt": ("p7-relation", 32, 1),
    "relation-development-square": ("p7-relation", 33, 1),
}


def main() -> int:
    for partition_id, (policy, offset, limit) in PARTITIONS.items():
        target = HERE / ("runpod_p7_w3_tail_remote_v6_" + partition_id.replace("-", "_") + ".py")
        if target.exists():
            raise FileExistsError(target)
        target.write_text(build(partition_id, policy, offset, limit), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
