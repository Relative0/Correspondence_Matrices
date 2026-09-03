"""Build the native runtime and execute the corrected query-ladder follow-up."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.architecture_query_ladder_followup import (
    functional_smoke,
    run_campaign,
)
from scripts.cm_architecture_comparison_campaign import _build_native


DEFAULT_FREEZE = (
    ROOT / "docs/recognition/architecture_query_ladder_followup_freeze_20260903/FREEZE.json"
)
DEFAULT_ORACLES = (
    ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, default=DEFAULT_FREEZE)
    parser.add_argument("--oracles", type=Path, default=DEFAULT_ORACLES)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--compiler", default="cc")
    parser.add_argument("--max-seconds", type=float, default=420.0)
    parser.add_argument("--functional-smoke", action="store_true")
    parser.add_argument("--local-platform-validation", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise SystemExit("output must be a new path inside the project")
    freeze_path = args.freeze.resolve()
    oracles_path = args.oracles.resolve()
    freeze = _load(freeze_path)
    oracles = _load(oracles_path)
    runtime = output.parent / f".{output.name}-native-runtime"
    if runtime.exists():
        raise SystemExit("native runtime path already exists")
    library, identity = _build_native(runtime, args.compiler, args.local_platform_validation)
    if args.functional_smoke:
        result = functional_smoke(ROOT, freeze, oracles, library)
        identity["role"] = "local_functional_query_ladder_validation_only"
        result["local_platform_validation_only"] = bool(args.local_platform_validation)
        result["runtime_binding"] = identity
        result["freeze_file_sha256"] = _sha256(freeze_path)
        result["oracles_file_sha256"] = _sha256(oracles_path)
        output.mkdir(parents=True)
        _write_json(output / "functional_smoke.json", result)
    else:
        if args.local_platform_validation:
            raise SystemExit("local platform validation cannot emit decision-bearing timing")
        identity["role"] = "decision_bearing_linux_query_ladder_followup"
        result = run_campaign(
            project_root=ROOT,
            freeze_path=freeze_path,
            oracles_path=oracles_path,
            native_library_path=library,
            output_dir=output,
            max_seconds=args.max_seconds,
        )
        _write_json(output / "runtime_binding.json", identity)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
