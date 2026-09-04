"""Frozen source-only audit for behavior-changing hardware revision histories."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping


SCHEMA = "cm-hardware-behavior-corpus/v1"
CUTOFF = "2026-09-04T00:00:00Z"
MAX_SCANNED_COMMITS = 160
MAX_SELECTED_TRANSITIONS = 12
HDL_SUFFIXES = (".v", ".sv", ".vh", ".svh")
CANDIDATES = (
    {
        "slug": "alexforencich/verilog-axi",
        "directory": "verilog-axi",
        "url": "https://github.com/alexforencich/verilog-axi.git",
        "branch": "master",
        "role": "development",
        "license_spdx": "MIT",
        "path_prefixes": ("rtl/",),
    },
    {
        "slug": "lowRISC/ibex",
        "directory": "ibex",
        "url": "https://github.com/lowRISC/ibex.git",
        "branch": "master",
        "role": "development",
        "license_spdx": "Apache-2.0",
        "path_prefixes": ("rtl/",),
    },
    {
        "slug": "black-parrot/black-parrot",
        "directory": "black-parrot",
        "url": "https://github.com/black-parrot/black-parrot.git",
        "branch": "master",
        "role": "confirmation",
        "license_spdx": "BSD-3-Clause",
        "path_prefixes": (
            "bp_be/src/", "bp_common/src/", "bp_fe/src/", "bp_me/src/", "bp_top/src/",
        ),
    },
    {
        "slug": "ultraembedded/riscv",
        "directory": "ultraembedded-riscv",
        "url": "https://github.com/ultraembedded/riscv.git",
        "branch": "master",
        "role": "confirmation",
        "license_spdx": "BSD-3-Clause",
        "path_prefixes": ("core/riscv/",),
    },
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _git(
    repository: Path,
    *arguments: str,
    text: bool = True,
    offline: bool = False,
) -> str | bytes:
    environment = os.environ.copy()
    environment.update({
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "core.autocrlf",
        "GIT_CONFIG_VALUE_0": "false",
        "GIT_CONFIG_KEY_1": "safe.directory",
        "GIT_CONFIG_VALUE_1": repository.resolve().as_posix(),
    })
    if offline:
        environment["GIT_NO_LAZY_FETCH"] = "1"
    process = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        check=False,
        text=text,
        encoding="utf-8" if text else None,
        errors="strict" if text else None,
        env=environment,
    )
    if process.returncode:
        diagnostic = process.stderr if text else process.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"git {' '.join(arguments[:2])} failed: {diagnostic[-600:]}")
    return process.stdout


def strip_comments(source: str) -> str:
    """Remove Verilog comments while preserving strings and line positions."""
    result: list[str] = []
    index = 0
    state = "normal"
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if state == "normal":
            if char == '"':
                result.append(char)
                state = "string"
            elif char == "/" and following == "/":
                result.extend((" ", " "))
                index += 1
                state = "line"
            elif char == "/" and following == "*":
                result.extend((" ", " "))
                index += 1
                state = "block"
            else:
                result.append(char)
        elif state == "string":
            result.append(char)
            if char == "\\" and following:
                result.append(following)
                index += 1
            elif char == '"':
                state = "normal"
        elif state == "line":
            result.append("\n" if char == "\n" else " ")
            if char == "\n":
                state = "normal"
        else:
            if char == "*" and following == "/":
                result.extend((" ", " "))
                index += 1
                state = "normal"
            else:
                result.append("\n" if char == "\n" else " ")
        index += 1
    return "".join(result)


def normalize_region(source: str) -> str:
    return re.sub(r"\s+", "", source)


_MODULE = re.compile(
    r"\bmodule\s+(?:automatic\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_$]*)\b(?P<body>.*?)\bendmodule\b",
    re.DOTALL,
)
_CONTINUOUS = re.compile(r"\bassign\b(?P<body>.*?);", re.DOTALL)
_ALWAYS_START = re.compile(r"\b(?:always_comb|always_ff|always_latch)\b|\balways\b")
_ASSIGNMENT = re.compile(
    r"(?<![A-Za-z0-9_$])(?P<lhs>[A-Za-z_][A-Za-z0-9_$]*)"
    r"(?:\s*\[[^\]]+\])?\s*(?P<op><=|(?<![=!<>])=(?!=))",
)
_SIMPLE_LHS = re.compile(r"\s*(?P<lhs>[A-Za-z_][A-Za-z0-9_$]*)(?:\s*\[[^\]]+\])?\s*")
_BLOCK_TOKEN = re.compile(r"\b(?:begin|end)\b")


def _inside(position: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)


def _skip_space(source: str, position: int) -> int:
    while position < len(source) and source[position].isspace():
        position += 1
    return position


def _matching_parenthesis(source: str, start: int) -> int | None:
    if start >= len(source) or source[start] != "(":
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def _statement_end(source: str, start: int) -> int | None:
    parentheses = brackets = braces = 0
    in_string = False
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            parentheses += 1
        elif char == ")":
            parentheses = max(0, parentheses - 1)
        elif char == "[":
            brackets += 1
        elif char == "]":
            brackets = max(0, brackets - 1)
        elif char == "{":
            braces += 1
        elif char == "}":
            braces = max(0, braces - 1)
        elif char == ";" and not (parentheses or brackets or braces):
            return index + 1
    return None


def _always_region(source: str, match: re.Match[str]) -> tuple[int, int] | None:
    position = _skip_space(source, match.end())
    if position < len(source) and source[position] == "@":
        position = _skip_space(source, position + 1)
        if position < len(source) and source[position] == "*":
            position += 1
        else:
            position = _matching_parenthesis(source, position) or -1
            if position < 0:
                return None
    elif match.group() == "always":
        return None
    position = _skip_space(source, position)
    if not re.match(r"begin\b", source[position:]):
        end = _statement_end(source, position)
        return None if end is None else (match.start(), end)
    depth = 0
    for token in _BLOCK_TOKEN.finditer(source, position):
        depth += 1 if token.group() == "begin" else -1
        if depth == 0:
            return match.start(), token.end()
    return None


def _parenthesis_depth(source: str, position: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    for char in source[:position]:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
    return depth


def parse_driver_regions(payload: bytes) -> dict[str, Any]:
    try:
        source = payload.decode("utf-8")
    except UnicodeDecodeError:
        return {"status": "refused_non_utf8", "modules": 0, "discovered": 1,
                "admitted": 0, "refused": 1, "ambiguous_identities": [], "drivers": {}}
    clean = strip_comments(source)
    candidates: list[dict[str, str]] = []
    refused = 0
    modules = list(_MODULE.finditer(clean))
    refused += max(0, len(re.findall(r"\bmodule\b", clean)) - len(modules))
    for module_match in modules:
        module = module_match.group("name")
        body = module_match.group("body")
        generate_spans = [(match.start(), match.end()) for match in
                          re.finditer(r"\bgenerate\b.*?\bendgenerate\b", body, re.DOTALL)]
        continuous = list(_CONTINUOUS.finditer(body))
        refused += max(0, len(re.findall(r"\bassign\b", body)) - len(continuous))
        for match in continuous:
            statement = match.group("body")
            if _inside(match.start(), generate_spans) or "`" in statement:
                refused += 1
                continue
            parts = statement.split("=", 1)
            lhs = _SIMPLE_LHS.fullmatch(parts[0]) if len(parts) == 2 else None
            if lhs is None:
                refused += 1
                continue
            candidates.append({"identity": f"{module}::{lhs.group('lhs')}",
                               "kind": "continuous", "normalized": normalize_region(statement)})
        consumed_until = -1
        for always in _ALWAYS_START.finditer(body):
            if always.start() < consumed_until:
                continue
            span = _always_region(body, always)
            if span is None:
                refused += 1
                continue
            consumed_until = span[1]
            block = body[span[0]:span[1]]
            assignments = sorted({match.group("lhs") for match in _ASSIGNMENT.finditer(block)
                                  if _parenthesis_depth(block, match.start()) == 0})
            if not assignments:
                refused += 1
                continue
            if "`" in block or _inside(always.start(), generate_spans):
                refused += len(assignments)
                continue
            normalized = normalize_region(block)
            for lhs in assignments:
                candidates.append({"identity": f"{module}::{lhs}", "kind": "procedural",
                                   "normalized": normalized})
    outside_assigns = len(_CONTINUOUS.findall(clean)) - sum(
        len(_CONTINUOUS.findall(match.group("body"))) for match in modules
    )
    refused += max(0, outside_assigns)
    base_refused = refused
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in candidates:
        grouped.setdefault(row["identity"], []).append(row)
    ambiguous = sorted(identity for identity, rows in grouped.items() if len(rows) != 1)
    refused += sum(len(grouped[identity]) for identity in ambiguous)
    drivers = {
        identity: {"kind": rows[0]["kind"],
                   "sha256": sha256_bytes(rows[0]["normalized"].encode("utf-8"))}
        for identity, rows in sorted(grouped.items()) if len(rows) == 1
    }
    return {
        "status": "parsed" if modules else "refused_no_module",
        "modules": len(modules),
        "discovered": len(candidates) + base_refused,
        "admitted": len(drivers),
        "refused": refused,
        "ambiguous_identities": ambiguous,
        "drivers": drivers,
    }


def compare_driver_regions(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    old = before.get("drivers", {})
    new = after.get("drivers", {})
    common = set(old) & set(new)
    changed = sorted(identity for identity in common if old[identity]["sha256"] != new[identity]["sha256"])
    unchanged = sorted(common - set(changed))
    return {
        "comparable": len(common),
        "changed": len(changed),
        "unchanged": len(unchanged),
        "added": len(set(new) - set(old)),
        "removed": len(set(old) - set(new)),
        "changed_identities": changed,
        "unchanged_identities": unchanged,
    }


def _name_status(repository: Path, parent: str, commit: str, *, offline: bool) -> list[dict[str, str | None]]:
    raw = _git(repository, "diff", "--name-status", "-z", "-M", parent, commit,
               text=False, offline=offline)
    fields = raw.decode("utf-8").split("\0")
    rows: list[dict[str, str | None]] = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index]
        index += 1
        if status.startswith(("R", "C")):
            old_path, new_path = fields[index], fields[index + 1]
            index += 2
        else:
            path = fields[index]
            index += 1
            old_path = None if status == "A" else path
            new_path = None if status == "D" else path
        rows.append({"status": status, "old_path": old_path, "new_path": new_path})
    return rows


def _eligible_path(path: str | None, candidate: Mapping[str, Any]) -> bool:
    return bool(path and path.lower().endswith(HDL_SUFFIXES)
                and any(path.startswith(prefix) for prefix in candidate["path_prefixes"]))


def _eligible_change(row: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    return any(_eligible_path(path, candidate) for path in (row.get("old_path"), row.get("new_path")))


def _blob(repository: Path, revision: str, path: str | None, *, offline: bool) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        payload = _git(repository, "show", f"{revision}:{path}", text=False, offline=offline)
        oid = str(_git(repository, "rev-parse", f"{revision}:{path}", offline=offline)).strip()
    except RuntimeError:
        return None
    return {"path": path, "bytes": len(payload), "sha256": sha256_bytes(payload),
            "git_oid": oid, "parse": parse_driver_regions(payload)}


def _line_counts(repository: Path, parent: str, commit: str, paths: Iterable[str],
                 *, offline: bool) -> dict[str, int | None]:
    unique = sorted(set(paths))
    raw = str(_git(repository, "diff", "--numstat", "--no-renames", parent, commit, "--", *unique,
                   offline=offline))
    added = deleted = 0
    binary = False
    for line in raw.splitlines():
        fields = line.split("\t", 2)
        if len(fields) < 2 or "-" in fields[:2]:
            binary = True
            continue
        added += int(fields[0])
        deleted += int(fields[1])
    return {"added": None if binary else added, "deleted": None if binary else deleted}


def _license(repository: Path, head: str, expected: str, *, offline: bool) -> dict[str, Any]:
    names = str(_git(repository, "ls-tree", "-r", "--name-only", head, offline=offline)).splitlines()
    choices = sorted(
        (name for name in names if Path(name).name.lower().startswith(("license", "copying"))),
        key=lambda value: (value.count("/"), value.casefold()),
    )
    if not choices:
        return {"verified": False, "reason": "license_file_missing"}
    path = choices[0]
    payload = _git(repository, "show", f"{head}:{path}", text=False, offline=offline)
    text = payload.decode("utf-8", errors="replace").lower()
    markers = {
        "MIT": ("permission is hereby granted, free of charge",),
        "ISC": ("permission to use, copy, modify, and/or distribute",),
        "Apache-2.0": ("apache license", "version 2.0"),
        "BSD-3-Clause": ("redistribution and use in source and binary forms", "neither the name"),
    }[expected]
    verified = all(marker in text for marker in markers)
    return {"verified": verified, "expected_spdx": expected, "path": path,
            "bytes": len(payload), "sha256": sha256_bytes(payload),
            "reason": None if verified else "license_text_mismatch"}


def _normalized_origin(value: str) -> str:
    return value.rstrip("/").removesuffix(".git")


def selection_reason(counts: Mapping[str, int]) -> str | None:
    if counts["changed"] < 1:
        return "no_changed_stable_driver"
    if counts["unchanged"] < 1:
        return "no_reusable_stable_driver"
    if counts["changed"] / counts["comparable"] > 0.90:
        return "near_total_stable_driver_rebuild"
    return None


def audit_repository(candidate: Mapping[str, Any], repositories_root: Path,
                     *, offline: bool = False) -> dict[str, Any]:
    repository = (repositories_root / candidate["directory"]).resolve()
    base = {key: candidate[key] for key in
            ("slug", "directory", "url", "branch", "role", "license_spdx", "path_prefixes")}
    if not (repository / ".git").is_dir():
        return {**base, "status": "refused", "refusal": "repository_missing"}
    try:
        remote = str(_git(repository, "remote", "get-url", "origin", offline=offline)).strip()
        if _normalized_origin(remote) != _normalized_origin(candidate["url"]):
            return {**base, "status": "refused", "refusal": "origin_url_mismatch"}
        head = str(_git(repository, "rev-list", "-1", "--first-parent", f"--before={CUTOFF}",
                        f"origin/{candidate['branch']}", offline=offline)).strip()
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise RuntimeError("sample head missing")
        license_record = _license(repository, head, candidate["license_spdx"], offline=offline)
        commits = str(_git(repository, "rev-list", "--first-parent", "--no-merges", head,
                           offline=offline)).splitlines()
        scans: list[dict[str, Any]] = []
        selected = 0
        for commit in commits:
            parents = str(_git(repository, "rev-list", "--parents", "-n", "1", commit,
                               offline=offline)).strip().split()
            if len(parents) != 2:
                continue
            if len(scans) == MAX_SCANNED_COMMITS or selected == MAX_SELECTED_TRANSITIONS:
                break
            parent = parents[1]
            changes = _name_status(repository, parent, commit, offline=offline)
            eligible = [row for row in changes if _eligible_change(row, candidate)]
            metadata = str(_git(repository, "show", "-s", "--format=%aI%x00%cI%x00%s", commit,
                                offline=offline)).rstrip("\n").split("\0", 2)
            record: dict[str, Any] = {
                "scan_index": len(scans),
                "parent_sha": parent,
                "commit_sha": commit,
                "author_time": metadata[0],
                "commit_time": metadata[1],
                "subject": metadata[2],
                "changed_path_count": len(changes),
                "noneligible_path_count": len(changes) - len(eligible),
                "eligible_path_count": len(eligible),
                "paths": [],
                "selected_index": None,
            }
            if not eligible:
                record.update({"selection": "refused", "reason": "no_production_hdl",
                               "driver_counts": {key: 0 for key in
                                                 ("comparable", "changed", "unchanged", "added", "removed")}})
                scans.append(record)
                continue
            changed_driver_keys: list[str] = []
            unchanged_driver_keys: list[str] = []
            for change in eligible:
                paths = [path for path in (change["old_path"], change["new_path"]) if path]
                before = _blob(repository, parent, change["old_path"], offline=offline)
                after = _blob(repository, commit, change["new_path"], offline=offline)
                stable_path = change["old_path"] is not None and change["old_path"] == change["new_path"]
                comparison = compare_driver_regions(before["parse"], after["parse"]) if (
                    stable_path and before is not None and after is not None
                ) else {
                    "comparable": 0, "changed": 0, "unchanged": 0,
                    "added": 0 if after is None else after["parse"]["admitted"],
                    "removed": 0 if before is None else before["parse"]["admitted"],
                    "changed_identities": [],
                    "unchanged_identities": [],
                }
                stable_name = change["new_path"] or change["old_path"] or ""
                changed_driver_keys.extend(f"{stable_name}::{identity}"
                                           for identity in comparison["changed_identities"])
                unchanged_driver_keys.extend(f"{stable_name}::{identity}"
                                             for identity in comparison["unchanged_identities"])
                record["paths"].append({
                    **change,
                    "stable_path": stable_path,
                    "line_counts": _line_counts(repository, parent, commit, paths, offline=offline),
                    "before": before,
                    "after": after,
                    "comparison": comparison,
                })
            count_names = ("comparable", "changed", "unchanged", "added", "removed")
            counts = {key: sum(row["comparison"][key] for row in record["paths"])
                      for key in count_names}
            reason = selection_reason(counts)
            record.update({
                "selection": "selected" if reason is None else "refused",
                "reason": reason,
                "driver_counts": counts,
                "changed_driver_keys": sorted(changed_driver_keys),
                "unchanged_driver_keys": sorted(unchanged_driver_keys),
            })
            if reason is None:
                record["selected_index"] = selected
                selected += 1
            scans.append(record)
        status = "admitted" if license_record["verified"] else "refused"
        return {
            **base,
            "status": status,
            "refusal": None if status == "admitted" else license_record.get("reason"),
            "sampled_head_sha": head,
            "license": license_record,
            "scanned_commit_count": len(scans),
            "selected_transition_count": selected,
            "scans": scans,
        }
    except (OSError, RuntimeError, UnicodeError, ValueError) as error:
        return {**base, "status": "refused", "refusal": type(error).__name__ + ":" + str(error)[:300]}


def _identity_parts(key: str) -> tuple[str, str]:
    path, module, _driver = key.rsplit("::", 2)
    return path, module


def summarize(audit: Mapping[str, Any]) -> dict[str, Any]:
    repositories = []
    total_discovered = total_admitted = 0
    for repository in audit["repositories"]:
        selected = [row for row in repository.get("scans", []) if row["selection"] == "selected"]
        count_names = ("comparable", "changed", "unchanged", "added", "removed")
        counts = {key: sum(row["driver_counts"][key] for row in selected) for key in count_names}
        discovered = admitted = 0
        for transition in selected:
            for path in transition["paths"]:
                for side in (path.get("before"), path.get("after")):
                    if side:
                        discovered += side["parse"]["discovered"]
                        admitted += side["parse"]["admitted"]
        total_discovered += discovered
        total_admitted += admitted
        changed_keys = sorted({key for row in selected for key in row["changed_driver_keys"]})
        unchanged_keys = sorted({key for row in selected for key in row["unchanged_driver_keys"]})
        changed_parts = [_identity_parts(key) for key in changed_keys]
        reason_counts = {
            reason: sum(row.get("reason") == reason for row in repository.get("scans", []))
            for reason in sorted({row.get("reason") or "selected"
                                  for row in repository.get("scans", [])})
        }
        if "selected" in reason_counts:
            reason_counts["selected"] = len(selected)
        repositories.append({
            "slug": repository["slug"],
            "role": repository["role"],
            "status": repository["status"],
            "refusal": repository.get("refusal"),
            "scanned_commits": repository.get("scanned_commit_count", 0),
            "selected_transitions": len(selected),
            "selection_reason_counts": reason_counts,
            "driver_counts": counts,
            "distinct_changed_drivers": len(changed_keys),
            "distinct_unchanged_drivers": len(unchanged_keys),
            "distinct_changed_paths": len({path for path, _module in changed_parts}),
            "distinct_changed_modules": len({(path, module) for path, module in changed_parts}),
            "changed_fraction": counts["changed"] / counts["comparable"] if counts["comparable"] else None,
            "driver_regions_discovered": discovered,
            "driver_regions_admitted": admitted,
            "parse_coverage": admitted / discovered if discovered else None,
            "selector_invariant": all(
                row["driver_counts"]["changed"] >= 1
                and row["driver_counts"]["unchanged"] >= 1
                and row["driver_counts"]["changed"] / row["driver_counts"]["comparable"] <= 0.90
                for row in selected
            ),
        })
    confirmation = [row for row in repositories if row["role"] == "confirmation"]
    confirmation_changed = sum(row["driver_counts"]["changed"] for row in confirmation)
    confirmation_comparable = sum(row["driver_counts"]["comparable"] for row in confirmation)
    conditions = {
        "all_four_repositories_provenance_admitted": (
            len(repositories) == 4 and all(row["status"] == "admitted" for row in repositories)
        ),
        "both_confirmation_repositories_admitted": (
            len(confirmation) == 2 and all(row["status"] == "admitted" for row in confirmation)
        ),
        "confirmation_each_has_eight_selected_transitions": (
            len(confirmation) == 2 and all(row["selected_transitions"] >= 8 for row in confirmation)
        ),
        "confirmation_selector_invariant": (
            len(confirmation) == 2 and all(row["selector_invariant"] for row in confirmation)
        ),
        "confirmation_each_has_eight_changed_and_unchanged_identities": (
            len(confirmation) == 2
            and all(row["distinct_changed_drivers"] >= 8
                    and row["distinct_unchanged_drivers"] >= 8 for row in confirmation)
        ),
        "confirmation_each_spans_four_paths_and_modules": (
            len(confirmation) == 2
            and all(row["distinct_changed_paths"] >= 4
                    and row["distinct_changed_modules"] >= 4 for row in confirmation)
        ),
        "confirmation_change_fraction_in_range": (
            confirmation_comparable > 0
            and 0.01 <= confirmation_changed / confirmation_comparable <= 0.80
        ),
        "confirmation_parse_coverage_at_least_0_60": (
            len(confirmation) == 2
            and all(row["parse_coverage"] is not None and row["parse_coverage"] >= 0.60
                    for row in confirmation)
        ),
        "overall_parse_coverage_at_least_0_65": (
            total_discovered > 0 and total_admitted / total_discovered >= 0.65
        ),
    }
    return {
        "schema": "cm-hardware-behavior-corpus-summary/v1",
        "repositories": repositories,
        "overall": {
            "driver_regions_discovered": total_discovered,
            "driver_regions_admitted": total_admitted,
            "parse_coverage": total_admitted / total_discovered if total_discovered else None,
            "confirmation_changed_stable_drivers": confirmation_changed,
            "confirmation_comparable_stable_drivers": confirmation_comparable,
            "confirmation_change_fraction": (
                confirmation_changed / confirmation_comparable if confirmation_comparable else None
            ),
        },
        "conditions": conditions,
        "independent_replay_required": True,
        "status_without_replay": (
            "admissible_pending_replay" if all(conditions.values())
            else "insufficient_behavior_change_or_provenance"
        ),
    }


def run_audit(repositories_root: Path, *, offline: bool = False) -> dict[str, Any]:
    repositories = [audit_repository(candidate, repositories_root, offline=offline)
                    for candidate in CANDIDATES]
    return {
        "schema": SCHEMA,
        "cutoff": CUTOFF,
        "max_scanned_commits": MAX_SCANNED_COMMITS,
        "max_selected_transitions": MAX_SELECTED_TRANSITIONS,
        "hdl_suffixes": list(HDL_SUFFIXES),
        "repositories": repositories,
    }
