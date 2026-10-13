"""Acquire pinned public CM campaign archives with strict byte/hash guards.

This script performs public HTTP GETs and bounded data-only extraction. It does
not access credentials, execute payloads, contact RunPod, or overwrite output.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
import time
from urllib.parse import quote
import zipfile

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/input-freeze-001"
MAX_RESPONSE_BYTES = 200_000_000
MAX_INPUT_BYTES = 16 << 20
COUNTING_REPOSITORY = "dfremont/counting-benchmarks"
COUNTING_REVISION = "daff1084d7487cd85f5a49f6588966275332e73f"
PINNED_BIOLOGY_METADATA = {
    "record": 8020309,
    "doi": "10.5281/zenodo.8020309",
    "title": "Biodivine Boolean Models; Edition 2022",
    "license": "cc-by-4.0",
    "created": None,
    "updated": None,
    "files": [{
        "key": "edition-2022-bnet.zip", "bytes": 261759,
        "checksum": "md5:fca5be7d6a621b78541f2846c388ebcd",
        "content_url": "https://zenodo.org/api/records/8020309/files/edition-2022-bnet.zip/content",
    }],
    "metadata_status": "pinned fallback; live endpoint unavailable",
}
SOURCES = (
    {
        "id": "biodivine-2022-bnet",
        "record": 8020309,
        "filename": "edition-2022-bnet.zip",
        "bytes": 261759,
        "md5": "fca5be7d6a621b78541f2846c388ebcd",
        "kind": "zip",
        "track": "biology",
    },
    {
        "id": "mc2024-track1",
        "record": 14249068,
        "filename": "mc2024-track1-mc_competition.tar",
        "bytes": 76199936,
        "md5": "2818d425fab0d89e666237241ca610bc",
        "kind": "tar",
        "track": "exact_count",
    },
    {
        "id": "mc2024-track3",
        "record": 14249068,
        "filename": "mc2024-track3-pmc_competition.tar",
        "bytes": 153438720,
        "md5": "e0421242445608d9de5961f1e8f544e8",
        "kind": "tar",
        "track": "projected_count",
    },
)


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        while block := stream.read(1 << 20):
            value.update(block)
    return value.hexdigest()


def download(session: requests.Session, url: str, destination: Path, expected_bytes: int,
             expected_md5: str) -> dict:
    if expected_bytes <= 0 or expected_bytes > MAX_RESPONSE_BYTES:
        raise ValueError("declared response outside acquisition bound")
    temporary = destination.with_suffix(destination.suffix + ".part")
    if destination.exists() or temporary.exists():
        raise FileExistsError(destination)
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    written = 0
    range_bytes = 1 << 20
    ranges = [(start, min(expected_bytes, start + range_bytes) - 1)
              for start in range(0, expected_bytes, range_bytes)]

    def fetch_range(bounds: tuple[int, int]) -> tuple[int, int, bytes]:
        start, end = bounds
        with requests.get(url, headers={"Range": f"bytes={start}-{end}"},
                          timeout=(15, 60)) as response:
            response.raise_for_status()
            block = response.content
            if response.status_code == 206:
                expected_range = f"bytes {start}-{end}/{expected_bytes}"
                if response.headers.get("content-range") != expected_range:
                    raise ValueError("HTTP content range differs from request")
            elif response.status_code != 200 or start != 0 or len(block) != expected_bytes:
                raise ValueError("server ignored a noninitial bounded range")
            if len(block) != end - start + 1:
                raise ValueError("HTTP range length differs from request")
            return start, end, block

    with temporary.open("xb") as output:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for start, end, block in pool.map(fetch_range, ranges):
                if start != written:
                    raise ValueError("range assembly order mismatch")
                written = end + 1
                md5.update(block)
                sha256.update(block)
                output.write(block)
    if written != expected_bytes or md5.hexdigest() != expected_md5:
        raise ValueError("download size or MD5 differs from Zenodo record")
    os.replace(temporary, destination)
    return {"bytes": written, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def archive_inventory(path: Path, kind: str) -> dict:
    rows = []
    if kind == "zip":
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                rows.append({"name": item.filename, "bytes": item.file_size,
                             "compressed_bytes": item.compress_size, "directory": item.is_dir()})
    elif kind == "tar":
        with tarfile.open(path, "r:") as archive:
            for item in archive:
                rows.append({"name": item.name, "bytes": item.size, "type": item.type.decode("ascii", "replace"),
                             "regular_file": item.isfile()})
    else:
        raise ValueError("unknown archive type")
    return {"members": rows, "member_count": len(rows),
            "regular_file_count": sum(not row.get("directory", False) and row.get("regular_file", True) for row in rows),
            "declared_expanded_bytes": sum(row["bytes"] for row in rows)}


def fetch_metadata(session: requests.Session, record: int) -> dict:
    response = None
    last_error = None
    for attempt in range(4):
        try:
            response = session.get(f"https://zenodo.org/api/records/{record}", timeout=(15, 90))
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            last_error = exc
            if attempt != 3:
                time.sleep(2 ** attempt)
    if response is None or not response.ok:
        raise RuntimeError("Zenodo metadata request exhausted four attempts") from last_error
    value = response.json()
    files = [{"key": item["key"], "bytes": item["size"], "checksum": item["checksum"],
              "content_url": item["links"]["self"]} for item in value["files"]]
    return {"record": value["id"], "doi": value["metadata"].get("doi"),
            "title": value["metadata"]["title"], "license": value["metadata"]["license"]["id"],
            "created": value["created"], "updated": value["updated"], "files": files}


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data, usedforsecurity=False).hexdigest()


def _select_balanced(rows: list[dict], count: int, prefixes: tuple[str, ...]) -> list[dict]:
    candidates = [row for row in rows if row["type"] == "blob" and row["path"].startswith(prefixes)
                  and row["path"].endswith(".cnf.gz") and 0 < row.get("size", 0) <= (2 << 20)]
    groups: dict[str, list[dict]] = {}
    for row in candidates:
        matched = next(prefix for prefix in prefixes if row["path"].startswith(prefix))
        remainder = row["path"][len(matched):]
        family = matched.rstrip("/").rsplit("/", 1)[-1] + "/" + remainder.split("/", 1)[0]
        groups.setdefault(family, []).append(row)
    for family_rows in groups.values():
        family_rows.sort(key=lambda row: hashlib.sha256(row["path"].encode("utf-8")).hexdigest())
    selected = []
    while len(selected) < count and any(groups.values()):
        for family in sorted(groups):
            if groups[family] and len(selected) < count:
                selected.append(groups[family].pop(0))
    if len(selected) != count:
        raise ValueError(f"insufficient bounded application files under {prefixes}")
    return selected


def _gunzip_bounded(data: bytes) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as source:
        while block := source.read(1 << 20):
            if output.tell() + len(block) > MAX_INPUT_BYTES:
                raise ValueError("expanded CNF exceeds input limit")
            output.write(block)
    return output.getvalue()


def acquire_bounded(output: Path) -> dict:
    """Freeze small stable biology plus exact/projected application CNFs."""
    target = output.resolve()
    if target.exists() or not target.parent.exists() or not target.is_relative_to(ROOT.resolve()):
        raise ValueError("new output below an existing workspace directory required")
    target.mkdir()
    raw = target / "raw"
    biology_dir = target / "admitted" / "biology"
    exact_dir = target / "admitted" / "counting" / "exact"
    projected_dir = target / "admitted" / "counting" / "projected"
    for path in (raw, biology_dir, exact_dir, projected_dir):
        path.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    biology_source = SOURCES[0]
    biology_archive = raw / biology_source["filename"]
    cached = next((path for path in sorted((target.parent).glob("input-freeze-*/raw/edition-2022-bnet.zip"))
                   if path.resolve() != biology_archive.resolve() and path.stat().st_size == biology_source["bytes"]
                   and digest(path, "md5") == biology_source["md5"]), None)
    if cached is not None:
        biology_metadata = dict(PINNED_BIOLOGY_METADATA)
    else:
        try:
            biology_metadata = fetch_metadata(session, 8020309)
            biology_metadata["metadata_status"] = "live verified"
        except RuntimeError:
            biology_metadata = dict(PINNED_BIOLOGY_METADATA)
    if biology_metadata["license"] != "cc-by-4.0":
        raise ValueError("unexpected biology license")
    biology_live = next(row for row in biology_metadata["files"] if row["key"] == biology_source["filename"])
    if cached is None:
        biology_receipt = download(session, biology_live["content_url"], biology_archive,
                                   biology_source["bytes"], biology_source["md5"])
        biology_receipt["transport"] = "public_https"
    else:
        shutil.copyfile(cached, biology_archive)
        biology_receipt = {"bytes": biology_archive.stat().st_size, "md5": digest(biology_archive, "md5"),
                           "sha256": digest(biology_archive, "sha256"),
                           "transport": "hash-verified local cache", "cache_source": cached.relative_to(ROOT).as_posix()}
    biology_rows = []
    with zipfile.ZipFile(biology_archive) as archive:
        for member in sorted(archive.infolist(), key=lambda item: item.filename):
            path = Path(member.filename)
            if member.is_dir() or path.suffix.lower() != ".bnet":
                continue
            if path.is_absolute() or ".." in path.parts or not 0 < member.file_size <= MAX_INPUT_BYTES:
                raise ValueError("unsafe biology archive member")
            data = archive.read(member)
            destination_name = f"{len(biology_rows):03d}-{hashlib.sha256(member.filename.encode()).hexdigest()[:12]}.bnet"
            destination = biology_dir / destination_name
            destination.write_bytes(data)
            biology_rows.append({"case_source": member.filename, "path": destination.relative_to(ROOT).as_posix(),
                                 "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    if not biology_rows:
        raise ValueError("biology archive has no BNet inputs")

    tree_url = f"https://api.github.com/repos/{COUNTING_REPOSITORY}/git/trees/{COUNTING_REVISION}?recursive=1"
    tree_response = session.get(tree_url, timeout=(15, 90))
    tree_response.raise_for_status()
    tree = tree_response.json()
    if tree.get("truncated"):
        raise ValueError("Git tree response was truncated")
    selected = {
        "exact": _select_balanced(tree["tree"], 92, (
            "benchmarks/basic/application/", "benchmarks/basic/quasi-application/",
        )),
        "projected": _select_balanced(tree["tree"], 196, ("benchmarks/projection/application/",)),
    }
    license_row = next(row for row in tree["tree"] if row["path"] == "LICENSE" and row["type"] == "blob")

    def fetch_blob(row: dict) -> tuple[dict, bytes]:
        url = f"https://raw.githubusercontent.com/{COUNTING_REPOSITORY}/{COUNTING_REVISION}/{quote(row['path'], safe='/')}"
        last_error = None
        for attempt in range(4):
            try:
                response = requests.get(url, timeout=(15, 180))
                response.raise_for_status()
                data = response.content
                if len(data) != row["size"] or git_blob_sha1(data) != row["sha"]:
                    raise ValueError("GitHub blob identity mismatch")
                return row, data
            except requests.RequestException as exc:
                last_error = exc
                if attempt != 3:
                    time.sleep(2 ** attempt)
        raise RuntimeError("GitHub blob download exhausted four attempts") from last_error

    _, license_data = fetch_blob(license_row)
    (target / "COUNTING-LICENSE.txt").write_bytes(license_data)
    counting_rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for track in ("exact", "projected"):
            destination_dir = exact_dir if track == "exact" else projected_dir
            for index, (row, compressed) in enumerate(pool.map(fetch_blob, selected[track])):
                data = _gunzip_bounded(compressed)
                destination_name = f"{index:03d}-{row['sha'][:12]}.cnf"
                destination = destination_dir / destination_name
                destination.write_bytes(data)
                counting_rows.append({
                    "track": track, "source_path": row["path"], "source_git_blob": row["sha"],
                    "source_bytes": row["size"], "source_sha256": hashlib.sha256(compressed).hexdigest(),
                    "path": destination.relative_to(ROOT).as_posix(), "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(), "transformation": "gzip decompression only",
                })

    record = {
        "schema": "cm-benchmark-bounded-input-freeze/v1",
        "selection": "family round-robin, SHA-256(path) order, independent of timings",
        "limits": {"input_bytes": MAX_INPUT_BYTES, "compressed_source_bytes": 2 << 20},
        "biology": {"record": biology_metadata, "archive": {**biology_source, **biology_receipt},
                    "license": "CC-BY-4.0", "rows": biology_rows},
        "counting": {"repository": f"https://github.com/{COUNTING_REPOSITORY}",
                     "revision": COUNTING_REVISION, "license": "CC0-1.0",
                     "license_git_blob": license_row["sha"], "rows": counting_rows},
        "deferred": [
            {"record": 14249068, "reason": "official MC2024 archives retained as preferred extension; local transfer did not complete within bounded preparation time"},
        ],
        "secret_access": False,
        "cloud_resource_writes": 0,
    }
    (target / "INPUT_FREEZE.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "passed", "output": str(target), "biology_files": len(biology_rows),
            "exact_count_files": len(selected["exact"]), "projected_count_files": len(selected["projected"])}


def verify_bounded(output: Path) -> dict:
    record = json.loads((output / "INPUT_FREEZE.json").read_text(encoding="utf-8"))
    archive = record["biology"]["archive"]
    archive_path = output / "raw" / archive["filename"]
    if archive_path.stat().st_size != archive["bytes"] or digest(archive_path, "md5") != archive["md5"] \
            or digest(archive_path, "sha256") != archive["sha256"]:
        raise ValueError("biology archive identity mismatch")
    paths = []
    for row in [*record["biology"]["rows"], *record["counting"]["rows"]]:
        path = ROOT / row["path"]
        if path.is_symlink() or not path.is_file() or path.stat().st_size != row["bytes"] \
                or digest(path, "sha256") != row["sha256"]:
            raise ValueError("frozen input identity mismatch")
        paths.append(path.resolve())
    actual = sorted(path.resolve() for path in (output / "admitted").rglob("*") if path.is_file())
    if sorted(paths) != actual or len(paths) != len(set(paths)):
        raise ValueError("frozen input membership mismatch")
    license_path = output / "COUNTING-LICENSE.txt"
    if git_blob_sha1(license_path.read_bytes()) != record["counting"]["license_git_blob"]:
        raise ValueError("counting license identity mismatch")
    tracks = {name: sum(row["track"] == name for row in record["counting"]["rows"])
              for name in ("exact", "projected")}
    return {"status": "passed", "biology_files": len(record["biology"]["rows"]),
            "counting_files": tracks, "secret_access": False}


def acquire(output: Path) -> dict:
    target = output.resolve()
    if target.exists() or not target.parent.exists() or not target.is_relative_to(ROOT.resolve()):
        raise ValueError("new output below an existing workspace directory required")
    target.mkdir()
    raw = target / "raw"
    raw.mkdir()
    session = requests.Session()
    metadata = {str(record): fetch_metadata(session, record) for record in sorted({row["record"] for row in SOURCES})}
    if any(row["license"] != "cc-by-4.0" for row in metadata.values()):
        raise ValueError("unexpected Zenodo license")
    acquired = []
    for source in SOURCES:
        file_meta = next(row for row in metadata[str(source["record"])]["files"] if row["key"] == source["filename"])
        if file_meta["bytes"] != source["bytes"] or file_meta["checksum"] != "md5:" + source["md5"]:
            raise ValueError("live Zenodo metadata differs from pinned source")
        destination = raw / source["filename"]
        receipt = download(session, file_meta["content_url"], destination, source["bytes"], source["md5"])
        inventory = archive_inventory(destination, source["kind"])
        acquired.append({**source, "url": file_meta["content_url"], **receipt, "inventory": inventory})
    record = {
        "schema": "cm-benchmark-public-acquisition/v1",
        "network": "public HTTPS GET only",
        "secret_access": False,
        "cloud_resource_writes": 0,
        "metadata": metadata,
        "archives": acquired,
    }
    (target / "ACQUISITION.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"status": "passed", "output": str(target), "archives": len(acquired),
            "downloaded_bytes": sum(row["bytes"] for row in acquired)}


def verify(output: Path) -> dict:
    record = json.loads((output / "ACQUISITION.json").read_text(encoding="utf-8"))
    for row in record["archives"]:
        path = output / "raw" / row["filename"]
        if path.stat().st_size != row["bytes"] or digest(path, "md5") != row["md5"] or digest(path, "sha256") != row["sha256"]:
            raise ValueError("archive identity mismatch")
        current = archive_inventory(path, row["kind"])
        if current != row["inventory"]:
            raise ValueError("archive inventory changed")
    return {"status": "passed", "archives": len(record["archives"]), "secret_access": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("acquire", "acquire-bounded", "verify"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = acquire(args.output) if args.action == "acquire" else (
        acquire_bounded(args.output) if args.action == "acquire-bounded" else (
            verify_bounded(args.output) if (args.output / "INPUT_FREEZE.json").is_file() else verify(args.output)
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
