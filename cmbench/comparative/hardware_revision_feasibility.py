"""Deterministic, non-timed feasibility audit for natural hardware revisions."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping


SCHEMA = "cm-hardware-revision-feasibility/v1"
CUTOFF = "2026-09-04T00:00:00Z"
MAX_TRANSITIONS = 12
HDL_SUFFIXES = (".v", ".sv", ".vh", ".svh")
CANDIDATES = (
    {
        "slug": "alexforencich/verilog-axi",
        "directory": "verilog-axi",
        "url": "https://github.com/alexforencich/verilog-axi.git",
        "branch": "master",
        "role": "development",
        "license_spdx": "MIT",
    },
    {
        "slug": "lowRISC/ibex",
        "directory": "ibex",
        "url": "https://github.com/lowRISC/ibex.git",
        "branch": "master",
        "role": "development",
        "license_spdx": "Apache-2.0",
    },
    {
        "slug": "olofk/serv",
        "directory": "serv",
        "url": "https://github.com/olofk/serv.git",
        "branch": "main",
        "role": "confirmation",
        "license_spdx": "ISC",
    },
    {
        "slug": "YosysHQ/picorv32",
        "directory": "picorv32",
        "url": "https://github.com/YosysHQ/picorv32.git",
        "branch": "main",
        "role": "confirmation",
        "license_spdx": "ISC",
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
    environment.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.autocrlf",
                        "GIT_CONFIG_VALUE_0": "false"})
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
    """Remove Verilog comments while preserving strings and source positions."""
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
_ALWAYS = re.compile(
    r"\b(?:always_comb|always\s*@\s*(?:\*|\(\s*\*\s*\)))(?![A-Za-z0-9_$])"
)
_ASSIGNMENT = re.compile(
    r"(?<![A-Za-z0-9_$])(?P<lhs>[A-Za-z_][A-Za-z0-9_$]*)"
    r"(?:\s*\[[^\]]+\])?\s*(?P<op><=|(?<![=!<>])=(?!=))",
)
_SIMPLE_LHS = re.compile(r"\s*(?P<lhs>[A-Za-z_][A-Za-z0-9_$]*)(?:\s*\[[^\]]+\])?\s*")


def _inside(position: int, spans: Iterable[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)


def _block_end(source: str, start: int) -> int:
    remainder = source[start:]
    begin = re.search(r"\bbegin\b", remainder)
    semicolon = remainder.find(";")
    if begin is None or (semicolon >= 0 and semicolon < begin.start()):
        return len(source) if semicolon < 0 else start + semicolon + 1
    depth = 0
    for token in re.finditer(r"\b(?:begin|end)\b", source[start + begin.start():]):
        depth += 1 if token.group() == "begin" else -1
        if depth == 0:
            return start + begin.start() + token.end()
    return len(source)


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
    for module_match in modules:
        module = module_match.group("name")
        body = module_match.group("body")
        generate_spans = [(match.start(), match.end()) for match in
                          re.finditer(r"\bgenerate\b.*?\bendgenerate\b", body, re.DOTALL)]
        for match in _CONTINUOUS.finditer(body):
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
        for always in _ALWAYS.finditer(body):
            end = _block_end(body, always.end())
            block = body[always.start():end]
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
    outside_module_assigns = len(_CONTINUOUS.findall(clean)) - sum(
        len(_CONTINUOUS.findall(match.group("body"))) for match in modules
    )
    refused += max(0, outside_module_assigns)
    base_refused = refused
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in candidates:
        grouped.setdefault(row["identity"], []).append(row)
    ambiguous = sorted(identity for identity, rows in grouped.items() if len(rows) != 1)
    refused += sum(len(grouped[identity]) for identity in ambiguous)
    drivers = {
        identity: {"kind": rows[0]["kind"], "sha256": sha256_bytes(rows[0]["normalized"].encode("utf-8"))}
        for identity, rows in sorted(grouped.items()) if len(rows) == 1
    }
    discovered = len(candidates) + base_refused
    return {
        "status": "parsed" if modules else "refused_no_module",
        "modules": len(modules),
        "discovered": discovered,
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


def _is_hdl(row: Mapping[str, Any]) -> bool:
    return any(path and str(path).lower().endswith(HDL_SUFFIXES)
               for path in (row.get("old_path"), row.get("new_path")))


def select_transitions(repository: Path, head: str, maximum: int = MAX_TRANSITIONS,
                       *, offline: bool = False) -> list[dict[str, Any]]:
    commits = str(_git(repository, "rev-list", "--first-parent", "--no-merges", head,
                       offline=offline)).splitlines()
    selected = []
    for commit in commits:
        parents = str(_git(repository, "rev-list", "--parents", "-n", "1", commit,
                           offline=offline)).strip().split()
        if len(parents) != 2:
            continue
        parent = parents[1]
        changes = _name_status(repository, parent, commit, offline=offline)
        hdl = [row for row in changes if _is_hdl(row)]
        if not hdl:
            continue
        metadata = str(_git(repository, "show", "-s", "--format=%aI%x00%cI%x00%s", commit,
                            offline=offline)).rstrip("\n").split("\0", 2)
        selected.append({
            "index": len(selected),
            "parent_sha": parent,
            "commit_sha": commit,
            "author_time": metadata[0],
            "commit_time": metadata[1],
            "subject": metadata[2],
            "changed_path_count": len(changes),
            "non_hdl_path_count": len(changes) - len(hdl),
            "hdl_changes": hdl,
        })
        if len(selected) == maximum:
            break
    return selected


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
    verified = {
        "MIT": "permission is hereby granted, free of charge" in text,
        "ISC": "permission to use, copy, modify, and/or distribute" in text,
        "Apache-2.0": "apache license" in text and "version 2.0" in text,
    }[expected]
    return {"verified": verified, "expected_spdx": expected, "path": path,
            "bytes": len(payload), "sha256": sha256_bytes(payload),
            "reason": None if verified else "license_text_mismatch"}


def audit_repository(candidate: Mapping[str, str], repositories_root: Path,
                     *, offline: bool = False) -> dict[str, Any]:
    repository = (repositories_root / candidate["directory"]).resolve()
    base = {key: candidate[key] for key in
            ("slug", "directory", "url", "branch", "role", "license_spdx")}
    if not (repository / ".git").is_dir():
        return {**base, "status": "refused", "refusal": "repository_missing"}
    try:
        remote = str(_git(repository, "remote", "get-url", "origin", offline=offline)).strip()
        if remote.rstrip("/").removesuffix(".git") != candidate["url"].rstrip("/").removesuffix(".git"):
            return {**base, "status": "refused", "refusal": "origin_url_mismatch"}
        head = str(_git(repository, "rev-list", "-1", "--first-parent", f"--before={CUTOFF}",
                        f"origin/{candidate['branch']}", offline=offline)).strip()
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise RuntimeError("sample head missing")
        license_record = _license(repository, head, candidate["license_spdx"], offline=offline)
        transitions = select_transitions(repository, head, offline=offline)
        for transition in transitions:
            path_rows = []
            for change in transition.pop("hdl_changes"):
                paths = [path for path in (change["old_path"], change["new_path"]) if path]
                before = _blob(repository, transition["parent_sha"], change["old_path"], offline=offline)
                after = _blob(repository, transition["commit_sha"], change["new_path"], offline=offline)
                stable_path = change["old_path"] is not None and change["old_path"] == change["new_path"]
                comparison = compare_driver_regions(before["parse"], after["parse"]) if (
                    stable_path and before is not None and after is not None
                ) else {
                    "comparable": 0,
                    "changed": 0,
                    "unchanged": 0,
                    "added": 0 if after is None else after["parse"]["admitted"],
                    "removed": 0 if before is None else before["parse"]["admitted"],
                    "changed_identities": [],
                }
                path_rows.append({**change, "stable_path": stable_path,
                                  "line_counts": _line_counts(repository, transition["parent_sha"],
                                                               transition["commit_sha"], paths,
                                                               offline=offline),
                                  "before": before, "after": after, "comparison": comparison})
            transition["paths"] = path_rows
            counts = ("comparable", "changed", "unchanged", "added", "removed")
            transition["seed_counts"] = {
                key: sum(row["comparison"][key] for row in path_rows) for key in counts
            }
            transition["has_changed_stable_seeds"] = transition["seed_counts"]["changed"] > 0
        status = "admitted" if license_record["verified"] and transitions else "refused"
        refusal = None if status == "admitted" else (
            license_record.get("reason") or "no_selected_hdl_transitions"
        )
        return {**base, "status": status, "refusal": refusal, "sampled_head_sha": head,
                "license": license_record, "selected_transition_count": len(transitions),
                "transitions": transitions}
    except (OSError, RuntimeError, UnicodeError, ValueError) as error:
        return {**base, "status": "refused", "refusal": type(error).__name__ + ":" + str(error)[:300]}


def summarize(audit: Mapping[str, Any]) -> dict[str, Any]:
    repository_rows = []
    discovered = admitted = 0
    for repository in audit["repositories"]:
        changed = comparable = transitions_changed = 0
        repo_discovered = repo_admitted = 0
        for transition in repository.get("transitions", []):
            changed += transition["seed_counts"]["changed"]
            comparable += transition["seed_counts"]["comparable"]
            transitions_changed += int(transition["has_changed_stable_seeds"])
            for path in transition["paths"]:
                for side in (path.get("before"), path.get("after")):
                    if side:
                        repo_discovered += side["parse"]["discovered"]
                        repo_admitted += side["parse"]["admitted"]
        discovered += repo_discovered
        admitted += repo_admitted
        repository_rows.append({
            "slug": repository["slug"],
            "role": repository["role"],
            "status": repository["status"],
            "selected_transitions": repository.get("selected_transition_count", 0),
            "transitions_with_changed_stable_seeds": transitions_changed,
            "changed_stable_seeds": changed,
            "comparable_stable_seeds": comparable,
            "changed_fraction": changed / comparable if comparable else None,
            "driver_regions_discovered": repo_discovered,
            "driver_regions_admitted": repo_admitted,
            "parse_coverage": repo_admitted / repo_discovered if repo_discovered else None,
            "refusal": repository.get("refusal"),
        })
    confirmation = [row for row in repository_rows if row["role"] == "confirmation"]
    confirmation_changed = sum(row["changed_stable_seeds"] for row in confirmation)
    confirmation_comparable = sum(row["comparable_stable_seeds"] for row in confirmation)
    conditions = {
        "three_repositories_provenance_admitted": sum(row["status"] == "admitted" for row in repository_rows) >= 3,
        "both_confirmation_repositories_admitted": len(confirmation) == 2 and all(row["status"] == "admitted" for row in confirmation),
        "confirmation_each_has_six_transitions": len(confirmation) == 2 and all(row["selected_transitions"] >= 6 for row in confirmation),
        "confirmation_each_has_four_changed_transitions": len(confirmation) == 2 and all(row["transitions_with_changed_stable_seeds"] >= 4 for row in confirmation),
        "confirmation_each_has_sixteen_changed_seeds": len(confirmation) == 2 and all(row["changed_stable_seeds"] >= 16 for row in confirmation),
        "confirmation_change_fraction_in_range": confirmation_comparable > 0 and 0.20 <= confirmation_changed / confirmation_comparable <= 0.90,
        "parse_coverage_at_least_0_70": discovered > 0 and admitted / discovered >= 0.70,
    }
    return {
        "schema": "cm-hardware-revision-feasibility-summary/v1",
        "repositories": repository_rows,
        "overall": {
            "driver_regions_discovered": discovered,
            "driver_regions_admitted": admitted,
            "parse_coverage": admitted / discovered if discovered else None,
            "confirmation_changed_stable_seeds": confirmation_changed,
            "confirmation_comparable_stable_seeds": confirmation_comparable,
            "confirmation_change_fraction": confirmation_changed / confirmation_comparable if confirmation_comparable else None,
        },
        "conditions": conditions,
        "independent_replay_required": True,
        "status_without_replay": "admissible_pending_replay" if all(conditions.values()) else "insufficient_activation_or_provenance",
    }


def run_audit(repositories_root: Path, *, offline: bool = False) -> dict[str, Any]:
    repositories = [audit_repository(candidate, repositories_root, offline=offline)
                    for candidate in CANDIDATES]
    return {"schema": SCHEMA, "cutoff": CUTOFF, "max_transitions_per_repository": MAX_TRANSITIONS,
            "hdl_suffixes": list(HDL_SUFFIXES), "repositories": repositories}
