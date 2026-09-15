"""Fail-closed pytest selection for the maintained Windows test profile."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

import pytest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests/cm_windows_pytest_profile.json"
PROFILE = "windows-supported"


@dataclass(frozen=True)
class WindowsProfile:
    historical: dict[tuple[str, str], str]
    optional: dict[str, dict[str, str]]
    collection_refusal_count: int
    all_skipped_count: int
    evidence: dict[str, dict[str, Any]]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bound_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"profile evidence escapes repository: {relative}") from error
    if not path.is_file():
        raise ValueError(f"profile evidence is missing: {relative}")
    return path


def _require_hash(path: Path, expected: str, *, newline_canonical: bool = False) -> None:
    actual = sha256_lf(path) if newline_canonical else sha256(path)
    if actual != expected:
        kind = "newline-canonical " if newline_canonical else ""
        raise ValueError(
            f"profile evidence {kind}hash mismatch: {path.as_posix()} "
            f"expected {expected}, got {actual}"
        )


def validate_profile(
    *, root: Path = ROOT, manifest_path: Path | None = None
) -> WindowsProfile:
    manifest_path = MANIFEST if manifest_path is None else manifest_path
    manifest = load_json(manifest_path)
    if manifest.get("schema") != "cm-windows-pytest-profile/v1":
        raise ValueError("Windows pytest profile schema")
    if manifest.get("profile") != PROFILE:
        raise ValueError("Windows pytest profile name")

    evidence = manifest.get("evidence", {})
    historical_record = evidence.get("historical_replay", {})
    historical_path = _bound_path(root, historical_record["path"])
    _require_hash(
        historical_path,
        historical_record["sha256_lf"],
        newline_canonical=True,
    )
    baseline = load_json(historical_path)
    field = historical_record.get("json_field")
    historical_rows = baseline.get(field, [])
    if len(historical_rows) != historical_record.get("expected_records"):
        raise ValueError("historical replay record count")
    historical: dict[tuple[str, str], str] = {}
    for row in historical_rows:
        if not isinstance(row, list) or len(row) != 3:
            raise ValueError("historical replay record shape")
        classname, name, outcome = row
        key = (classname, name)
        if key in historical:
            raise ValueError(f"duplicate historical replay selector: {key!r}")
        if outcome not in {"failure", "error"}:
            raise ValueError(f"unsupported historical outcome: {outcome!r}")
        historical[key] = outcome
        module_name = classname.split(".", 2)
        if len(module_name) < 2 or module_name[0] != "tests":
            raise ValueError(f"historical selector is outside tests/: {classname}")
        if not (root / "tests" / f"{module_name[1]}.py").is_file():
            raise ValueError(f"historical selector module is missing: {classname}")

    optional_record = evidence.get("optional_refusals", {})
    optional_path = _bound_path(root, optional_record["path"])
    _require_hash(optional_path, optional_record["sha256"])
    overnight = load_json(optional_path)
    comparison = overnight.get("baseline_comparison", {})
    if not comparison.get("same_nonpassing_test_ids_and_kinds"):
        raise ValueError("overnight audit does not preserve baseline parity")
    if comparison.get("new_nonpassing") or comparison.get("resolved_nonpassing"):
        raise ValueError("overnight audit records baseline drift")
    if comparison.get("current_supported_nonpassing") != len(historical):
        raise ValueError("overnight supported count differs from historical inventory")

    collection = comparison.get("expected_collection_refusals", [])
    all_skipped = comparison.get("expected_all_skipped", [])
    if len(collection) != optional_record.get("expected_collection_refusal_modules"):
        raise ValueError("optional collection-refusal count")
    if len(all_skipped) != optional_record.get("expected_all_skipped_modules"):
        raise ValueError("optional all-skipped count")
    optional: dict[str, dict[str, str]] = {}
    for kind, rows in (
        ("collection_refusal", collection),
        ("all_skipped", all_skipped),
    ):
        for row in rows:
            relative = row.get("path")
            if not isinstance(relative, str) or not relative.startswith("tests/"):
                raise ValueError("optional refusal path")
            if relative in optional:
                raise ValueError(f"duplicate optional refusal module: {relative}")
            if not (root / relative).is_file():
                raise ValueError(f"optional refusal module is missing: {relative}")
            optional[relative] = {"kind": kind, "reason": row.get("reason", "")}

    historical_modules = {
        "tests/" + classname.split(".", 2)[1] + ".py"
        for classname, _ in historical
    }
    overlap = historical_modules.intersection(optional)
    if overlap:
        raise ValueError(f"profile categories overlap: {sorted(overlap)!r}")
    return WindowsProfile(
        historical=historical,
        optional=optional,
        collection_refusal_count=len(collection),
        all_skipped_count=len(all_skipped),
        evidence=evidence,
    )


def profile_summary(profile: WindowsProfile) -> dict[str, Any]:
    return {
        "schema": "cm-windows-pytest-profile-summary/v1",
        "profile": PROFILE,
        "historical_replay_tests": len(profile.historical),
        "optional_modules": len(profile.optional),
        "collection_refusal_modules": profile.collection_refusal_count,
        "all_skipped_modules": profile.all_skipped_count,
        "optional": [
            {"path": path, **record}
            for path, record in sorted(profile.optional.items())
        ],
    }


def item_key(item: Any) -> tuple[str, str]:
    module_path = item.nodeid.split("::", 1)[0]
    if module_path.endswith(".py"):
        module_path = module_path[:-3]
    classname = module_path.lstrip("./\\").replace("\\", ".").replace("/", ".")
    if item.cls is not None:
        classname += "." + item.cls.__name__
    return classname, item.name


def missing_historical_keys(
    found: Iterable[tuple[str, str]], expected: Iterable[tuple[str, str]]
) -> set[tuple[str, str]]:
    return set(expected).difference(found)


def _selected(config: pytest.Config) -> bool:
    return config.getoption("cm_profile", default=None) == PROFILE


def _profile(config: pytest.Config) -> WindowsProfile:
    profile = getattr(config, "_cm_windows_profile", None)
    if profile is None:
        profile = validate_profile()
        setattr(config, "_cm_windows_profile", profile)
    return profile


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("cm test profiles")
    group.addoption(
        "--cm-profile",
        dest="cm_profile",
        choices=(PROFILE,),
        help="Select the fail-closed maintained CM test profile.",
    )


def pytest_configure(config: pytest.Config) -> None:
    if _selected(config):
        if os.name != "nt":
            raise pytest.UsageError(f"{PROFILE} is defined only for Windows")
        _profile(config)


def pytest_ignore_collect(
    collection_path: Path, config: pytest.Config
) -> bool | None:
    if not _selected(config):
        return None
    try:
        relative = Path(collection_path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return None
    return True if relative in _profile(config).optional else None


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not _selected(config):
        return
    profile = _profile(config)
    selected = []
    deselected = []
    found: set[tuple[str, str]] = set()
    for item in items:
        key = item_key(item)
        if key in profile.historical:
            item.add_marker(pytest.mark.cm_historical_replay)
            deselected.append(item)
            found.add(key)
        else:
            item.add_marker(pytest.mark.cm_active_supported)
            selected.append(item)
    missing = missing_historical_keys(found, profile.historical)
    if missing:
        preview = ", ".join(f"{key[0]}::{key[1]}" for key in sorted(missing)[:5])
        raise pytest.UsageError(
            f"{PROFILE} historical inventory drift: {len(missing)} selectors missing; "
            + preview
        )
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected
    setattr(
        config,
        "_cm_windows_profile_counts",
        {
            "active_supported": len(selected),
            "historical_replay": len(deselected),
            "optional_modules": len(profile.optional),
        },
    )


def pytest_report_header(config: pytest.Config) -> str | None:
    if not _selected(config):
        return None
    profile = _profile(config)
    return (
        f"CM profile: {PROFILE}; {len(profile.historical)} historical tests and "
        f"{len(profile.optional)} optional/refusal modules excluded fail-closed"
    )


def pytest_terminal_summary(
    terminalreporter: Any, exitstatus: int, config: pytest.Config
) -> None:
    if not _selected(config):
        return
    counts = getattr(config, "_cm_windows_profile_counts", None)
    if counts is None:
        return
    terminalreporter.section("CM Windows supported profile")
    terminalreporter.write_line(
        f"active supported: {counts['active_supported']}; "
        f"historical replay deselected: {counts['historical_replay']}; "
        f"optional/refusal modules ignored: {counts['optional_modules']}"
    )
