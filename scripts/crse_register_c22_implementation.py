"""Record C22 implementation readiness without registering a timing result."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
REGISTER = DOCS / "experiment_register.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def main() -> None:
    policy = load(DOCS / "c22_source_portfolio_policy.json")
    if (
        policy.get("status") != "frozen"
        or policy.get("selected_arm") != "source_packed_anf_screened"
        or policy.get("advice_off_arm") != "explicit_cm_exhaustive"
        or policy.get("exact_fallback_arm") != "explicit_cm_exhaustive"
        or policy.get("fresh_confirmation") is not False
        or policy.get("production_promotion") is not False
        or not (DOCS / "C22_SOURCE_PACKED_GF2_PORTFOLIO_IMPLEMENTATION_2026_08_31.md").is_file()
        or not (ROOT / "cmbench/recognition/gf2_source_portfolio.py").is_file()
        or not (ROOT / "tests/test_gf2_source_portfolio.py").is_file()
    ):
        raise SystemExit("refusing C22 implementation registration: evidence incomplete")
    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C22 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    tracks["R01"]["next_experiment"] = (
        "Run the frozen C22 source-packed exact portfolio unchanged on a new source-family table."
    )
    tracks["R06"]["next_experiment"] = (
        "Freeze a new source-family decomposition table and repeat C21/C22 on a second CPU machine."
    )
    tracks["R16"]["next_experiment"] = (
        "Measure C22 advice-on, advice-off, exact fallback, and bounded shadow costs end to end."
    )
    tracks["R17"]["next_experiment"] = (
        "Add malformed, unsupported-source, and source-family OOD cases to fresh C22 confirmation."
    )
    data["milestones"]["F"] = (
        "C21/F2 verifies the first task-matched exact GF(2) table; C22 implements the frozen "
        "source-packed arm with advice-off, exact fallback, and shadow checks; fresh evaluation remains"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "implementation": "C22", "timing_claim": False,
                      "production_promotion": False}, sort_keys=True))


if __name__ == "__main__":
    main()
