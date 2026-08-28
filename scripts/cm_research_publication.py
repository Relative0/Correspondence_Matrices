"""GitHub reading editions and explicit, credential-excluding publication checks.

Never authenticates, creates cloud resources, stages, commits, or pushes.
Reader files are derived artifacts; frozen scientific evidence is never edited.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import quote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SITE = Path("deliverables_n22_24/master_explainer_2026_08_03")
CAMPAIGN = Path("docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909")
READERS = Path("docs/research/readers")
MANIFEST = Path("docs/research/SOURCE-SHA256.json")
PINNED_FIXTURE = (SITE / "use_case_benchmarks_2026-08-27/runs/configuration-fm-frozen-audit-regression-2026-08-27/pytest-tmp/test_dimacs_parser_preserves_f0/fixture.dimacs").as_posix()
PINNED_FIXTURE_SHA256 = "ed6657f83632435d5877551ec442560247aba5ee8944a3fff94669147ae85e9b"
EXTRA_FILES = (
    "scripts/cm_measurement_verify.py", "scripts/cm_memory_estimator_study.py",
    "scripts/cm_runpod_readiness.py", "scripts/cm_research_publication.py",
    "docs/audits/CM-VERIFICATION-CONTINUATION-2026-08-28.md",
    "docs/audits/2026-08-25-cm-deep-performance/CM-MAXIMAL-SAFE-REMAINING-WORK-CAMPAIGN-PROMPT-2026-08-27.md",
)
MAX_FILE = 48 << 20
MAX_ARCHIVE_EXPANSION = 128 << 20


def git(*args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root)


def excluded(name):
    path = PurePosixPath(name.replace("\\", "/"))
    # This 54-byte fixture is part of a pinned scientific checksum manifest,
    # despite its historical directory name. No other scratch is admitted.
    if path.as_posix() == PINNED_FIXTURE:
        return False
    parts = [part.lower() for part in path.parts]
    return (
        path.is_absolute() or ".." in parts or not parts or ":" in parts[0]
        or "\n" in name or "\r" in name
        or any(part.startswith((".env", ".pytest")) for part in parts)
        or any(part in (".git", ".venv", "__pycache__", ".claude", "external", "tmp", "node_modules", "pytest-tmp", "pytest-temp") for part in parts)
        or any("fake-checks" in part or "fake-client" in part or "unit-fixtures" in part
               or part == "gpu-official-schema-20260828" for part in parts)
        or any("support-draft" in part or "the broken silence" in part for part in parts)
        or path.suffix.lower() in (".pyc", ".pyd", ".pem", ".key", ".sqlite", ".sqlite3", ".db", ".prof")
        or parts[-1] in ("id_rsa", "id_ed25519", "credentials", "credentials.json", "auth.json")
        or "/downloads/" in "/" + path.as_posix()
    )


SECRET_PATTERNS = (
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"\b(?:ghp_|gho_|github_pat_|rpa_)[A-Za-z0-9_]{24,}\b",
    rb"\bAKIA[0-9A-Z]{16}\b",
    rb"https?://[^\s/:]+:[^\s/@]+@",
)
SENSITIVE_FIELDS = {"authorization", "api_key", "apikey", "runpod_api_key", "rp_token",
                    "cm_bootstrap_token", "access_token", "refresh_token", "private_key"}


def scan_bytes(name, data, depth=0):
    """Refuse suspected secret values without including them in error messages."""
    if excluded(name):
        raise ValueError("excluded publication path: " + name)
    if name.replace("\\", "/") == PINNED_FIXTURE and hashlib.sha256(data).hexdigest() != PINNED_FIXTURE_SHA256:
        raise ValueError("pinned parser fixture changed")
    if len(data) > MAX_FILE:
        raise ValueError("publication file too large: " + name)
    if name.lower().endswith(".zip"):
        if depth >= 3:
            raise ValueError("nested archive depth exceeded: " + name)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if sum(member.file_size for member in members) > MAX_ARCHIVE_EXPANSION:
                raise ValueError("archive expansion exceeded: " + name)
            if len({member.filename for member in members}) != len(members):
                raise ValueError("duplicate archive member: " + name)
            for member in members:
                if member.is_dir():
                    continue
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("archive symlink: " + name)
                scan_bytes(member.filename, archive.read(member), depth + 1)
        return
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, data):
            raise ValueError("potential credential signature: " + name)
    if not name.lower().endswith(('.json', '.jsonl')):
        return
    def inspect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in SENSITIVE_FIELDS and isinstance(item, str) and item.strip():
                    if not item.startswith(("OFFLINE", "FAKE", "<", "PRIVATE_SENTINEL")):
                        raise ValueError("nonempty sensitive JSON field: " + name)
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    try:
        text = data.decode("utf-8-sig")
        if name.lower().endswith('.jsonl'):
            for line in text.splitlines():
                if line.strip():
                    inspect(json.loads(line))
        else:
            inspect(json.loads(text))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid publication JSON: " + name) from exc


def selected_paths(root=ROOT):
    tracked = git("ls-files", "-z", root=root).decode("utf-8").split("\0")
    additions = []
    for directory in (SITE, CAMPAIGN, Path("docs/runpod"), Path("docs/research")):
        additions.extend(str(p.relative_to(root)).replace("\\", "/") for p in (root / directory).rglob("*") if p.is_file())
    additions.extend(EXTRA_FILES)
    additions.extend(str(p.relative_to(root)).replace("\\", "/")
                     for p in (root / "tests").glob("test_cm_*.py"))
    return sorted({p for p in tracked + additions if p and not excluded(p) and p != MANIFEST.as_posix()})


def local_link(target, source, destination, root=ROOT):
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return target
    target = target.removeprefix("file:///").replace("\\", "/")
    local_prefix = "C:/Users/brian/Documents/CM_Computation/"
    if target.lower().startswith(local_prefix.lower()):
        path = root / target[len(local_prefix):]
    elif re.match(r"^[A-Za-z]:", target):
        return target
    else:
        path = (root / source).parent / target
    return quote(os.path.relpath(path, (root / destination).parent).replace("\\", "/"), safe="/#?=&:%+")


class InlineMarkdown(HTMLParser):
    def __init__(self, source, destination):
        super().__init__(convert_charrefs=True)
        self.parts, self.links = [], []
        self.source, self.destination = source, destination

    def handle_starttag(self, tag, attrs):
        if tag in ("em", "i"):
            self.parts.append("*")
        elif tag in ("b", "strong"):
            self.parts.append("**")
        elif tag == "code":
            self.parts.append("`")
        elif tag in ("sup", "sub"):
            self.parts.append("<" + tag + ">")
        elif tag == "a":
            self.links.append(dict(attrs).get("href", ""))
            self.parts.append("[")
        elif tag in ("p", "div", "br"):
            self.parts.append("\n\n")
        elif tag == "li":
            self.parts.append("\n- ")

    def handle_endtag(self, tag):
        if tag in ("em", "i", "b", "strong", "code"):
            self.parts.append({"em": "*", "i": "*", "b": "**", "strong": "**", "code": "`"}[tag])
        elif tag == "a" and self.links:
            self.parts.append("](" + local_link(self.links.pop(), self.source, self.destination) + ")")
        elif tag in ("sup", "sub"):
            self.parts.append("</" + tag + ">")
        elif tag in ("p", "div", "ul", "ol"):
            self.parts.append("\n\n")

    def handle_data(self, data):
        self.parts.append(data)


def format_number(record):
    value, fmt = record["value"], record["fmt"]
    if value is None:
        return "—"
    if fmt == "text":
        return str(value)
    if fmt in ("int", "big", "x0", "xcomma", "pct0"):
        number = math.floor(float(value) + 0.5)
        return (f"{number:,}" if fmt != "pct0" else str(number)) + ("×" if fmt in ("x0", "xcomma") else "%" if fmt == "pct0" else "")
    digits = {"ratio2": 2, "ratio3": 3, "ratio4": 4, "num1": 1, "num1s": 1,
              "x1": 1, "x2": 2, "pct1": 1, "pct2": 2, "pctsign2": 2, "usd": 4}
    if fmt in digits:
        output = f"{float(value):.{digits[fmt]}f}"
        if fmt == "num1s":
            output = output.removesuffix(".0")
        if fmt == "pctsign2" and value >= 0:
            output = "+" + output
        return ("$" if fmt == "usd" else "") + output + ("×" if fmt in ("x1", "x2") else "%" if fmt.startswith("pct") else "")
    if fmt == "ms0":
        return f"{value:.1f} ms" if value < 10 else f"{value:.0f} ms"
    if fmt == "us0":
        if value >= 100000:
            return f"{value / 1000:.0f} ms"
        if value >= 1000:
            return f"{value / 1000:.{1 if value >= 10000 else 2}f} ms"
        return f"{value:.{2 if value < 10 else 1}f} µs"
    raise ValueError("unsupported number format: " + fmt)


def reader(title, content, numbers, destination):
    used = set()
    source = SITE / "cm_master_data_2026_08_03.json"
    def prose(value):
        def token(match):
            key = match.group(1)
            used.add(key)
            return format_number(numbers[key])
        text = re.sub(r"\{\{([\w.]+)\}\}", token, str(value))
        parser = InlineMarkdown(source, destination)
        parser.feed(text)
        result = "".join(parser.parts).strip()
        return re.sub(r"\n{3,}", "\n\n", result)
    def label(key):
        names = {"lay": "Plain-language explanation", "technical": "Technical detail",
                 "cm_fit": "How CMs could help", "cm_role": "Proposed CM role",
                 "information": "Information retained", "incumbents": "Incumbents and alternatives",
                 "proof": "Evidence still needed", "fit": "When to consider CMs",
                 "good": "Good fit", "poor": "Poor fit", "boundary": "Evidence boundary",
                 "what a CM retains": "What a CM retains", "real_datasets": "Real datasets",
                 "dominance_gate": "What would establish a useful advantage"}
        return names.get(key, re.sub(r"(?<=[a-z])(?=[A-Z])", " ", key).replace("_", " ").capitalize())
    def render(value, depth=2):
        if isinstance(value, dict):
            chunks = []
            for key, item in value.items():
                if key in ("id", "kind", "_readme"):
                    continue
                if key in ("lede", "text", "title", "items"):
                    chunks.append(render(item, depth))
                    continue
                heading = label(key)
                chunks.append(("#" * min(depth, 6) + " " + heading + "\n\n") + render(item, depth + 1))
            return "\n\n".join(chunks)
        if isinstance(value, list):
            chunks = []
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    name = next((item[k] for k in ("name", "title", "field", "term", "question", "stage") if k in item), f"Item {index + 1}")
                    rest = {k: v for k, v in item.items() if v != name}
                    chunks.append("#" * min(depth, 6) + " " + prose(name) + "\n\n" + render(rest, depth + 1))
                else:
                    chunks.append(prose(item))
            return "\n\n".join(chunks)
        return prose(value)
    body = render(content)
    header = f"# {title}\n\n[Research library](../README.md) · Generated reading edition, 2026-08-28.\n\n"
    header += "Derived from the authored explainer and its saved evidence. Charts and interactive controls remain in the downloaded HTML.\n\n"
    header += "Latest follow-up: [verified Runpod memory smoke](RUNPOD-MEMORY-SMOKE.md). This does not establish general CM dominance or production estimator acceptance.\n\n"
    appendix = ""
    if used:
        appendix = "\n\n## Named-number provenance\n\nValues below retain the source field and any qualification used by the website.\n\n"
        for key in sorted(used):
            record = numbers[key]
            appendix += f"- `{key}` = {format_number(record)}. Source: `{record['prov']}`. {record.get('note', '')}".rstrip() + "\n"
    return header + body + appendix.rstrip() + "\n"


def reading_editions(root=ROOT):
    data = json.loads((root / SITE / "cm_master_data_2026_08_03.json").read_text(encoding="utf-8"))
    c, numbers = data["_content"], data["_numbers"]
    selections = {
        "MASTER-EXPLAINER.md": ("Correspondence Matrices — master explainer", c),
        "CM-USE-CASES.md": ("CM use cases and benchmark opportunities", {"application hypotheses": c["use_cases"], "datasets and benchmark design": c["use_case_benchmark_catalog"]}),
        "SIMPLE-ONE-PAGER.md": ("Correspondence Matrices — simple one-pager", {
            "the problem": c["domains"]["lay"], "what a CM retains": c["whatIsCM"]["truthTable"]["lay"],
            "the size that matters": c["whatIsCM"]["liveK"]["lay"], "choose the right tool": c["toolbox"]["lay"],
            "where reuse might help": c["use_cases"]["fit"], "what is measured": c["use_cases"]["boundary"]}),
        "TECHNICAL-SUMMARY.md": ("Correspondence Matrices — technical summary", {
            "representation": c["whatIsCM"], "comparison contracts": c["toolbox"]["technical"],
            "current frontier": c["frontier"]["technical"], "measurement discipline": c["discipline"],
            "current evidence update": c["current_update"]}),
    }
    outputs = {READERS / name: reader(title, value, numbers, READERS / name)
               for name, (title, value) in selections.items()}
    for filename, original in (("RUNPOD-MEMORY-SMOKE.md", "RUNPOD-ZERO-VOLUME-RESULT-AUDIT-2026-08-28.md"),
                               ("RUNPOD-SETUP.md", "RUNPOD-SETUP-HANDOFF-2026-08-28.md")):
        source, destination = Path("docs/runpod") / original, READERS / filename
        text = (root / source).read_text(encoding="utf-8")
        text = re.sub(r"\]\(([^)]+)\)", lambda match: "](" + local_link(match.group(1), source, destination, root) + ")", text)
        outputs[destination] = "[Research library](../README.md) · GitHub reading edition; local paths inside historical commands are provenance.\n\n" + text.rstrip() + "\n"
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("readers", "inventory", "manifest", "verify-archive"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--stage-list", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args(argv)
    if args.action == "readers":
        outputs = reading_editions()
        for path, text in outputs.items():
            if args.check:
                if (ROOT / path).read_text(encoding="utf-8") != text:
                    raise ValueError("stale reader: " + str(path))
            else:
                (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
                (ROOT / path).write_text(text, encoding="utf-8", newline="\n")
        print(json.dumps({"readers": len(outputs), "checked": args.check}))
    elif args.action == "inventory":
        paths = selected_paths()
        total = 0
        for name in paths:
            path = ROOT / name
            if (any(part.is_symlink() or part.is_junction() for part in (path, *path.parents) if part != ROOT)
                or not path.resolve().is_relative_to(ROOT)
                or excluded(path.resolve().relative_to(ROOT).as_posix())):
                raise ValueError("linked publication source: " + name)
            data = path.read_bytes()
            scan_bytes(name, data)
            total += len(data)
        if args.stage_list:
            output = args.stage_list.resolve()
            if not output.is_relative_to(ROOT / "tmp"):
                raise ValueError("stage list must be a new file under project tmp")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(b"\0".join(name.encode() for name in paths) + b"\0")
        print(json.dumps({"selected_files": len(paths), "bytes": total, "secret_scan": "passed", "stage_list_written": bool(args.stage_list)}))
    elif args.action == "manifest":
        paths = [name for name in git("ls-files", "-z").decode().split("\0") if name and not excluded(name) and name != MANIFEST.as_posix()]
        batch = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT,
                               input="".join(":" + name + "\n" for name in paths).encode(), capture_output=True, check=True)
        stream, rows = io.BytesIO(batch.stdout), []
        for name in paths:
            header = stream.readline().decode().split()
            if len(header) != 3 or header[1] != "blob":
                raise ValueError("unexpected staged object: " + name)
            data = stream.read(int(header[2]))
            if stream.read(1) != b"\n":
                raise ValueError("invalid Git batch boundary")
            scan_bytes(name, data)
            rows.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        result = {"schema": "cm-research-source/v1", "scope": "Git index bytes; manifest itself and export-ignored downloads/env/profiles excluded", "files": rows}
        (ROOT / MANIFEST).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"manifest_files": len(rows), "manifest": MANIFEST.as_posix()}))
    else:
        if not args.archive:
            parser.error("--archive is required")
        manifest = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
        with zipfile.ZipFile(args.archive) as archive:
            root = archive.namelist()[0].split("/")[0] + "/"
            actual = {item.filename[len(root):] for item in archive.infolist() if not item.is_dir()}
            expected = {row["path"] for row in manifest["files"]} | {MANIFEST.as_posix()}
            if actual != expected:
                raise ValueError("archive membership differs from source manifest")
            for row in manifest["files"]:
                data = archive.read(root + row["path"])
                if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                    raise ValueError("archive content differs: " + row["path"])
            for item in archive.infolist():
                if not item.is_dir():
                    scan_bytes(item.filename[len(root):], archive.read(item))
        print(json.dumps({"verified_files": len(manifest["files"]), "archive_bytes": args.archive.stat().st_size,
                          "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
