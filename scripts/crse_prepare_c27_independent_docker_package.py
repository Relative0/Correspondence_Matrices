"""Freeze a transport-neutral C27 Docker package for an independent machine."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/recognition/c27_linux_confirmation"
HERE = ROOT / "docs/recognition/c27_independent_docker_confirmation"
MANIFEST = SOURCE / "c27_linux_upload_manifest.json"
PROTOCOL = HERE / "C27_INDEPENDENT_DOCKER_SECOND_MACHINE_PROTOCOL_2026_09_01.md"
PACKAGE = HERE / "c27-independent-docker-package"
ARCHIVE = HERE / "c27-independent-docker-package.tar.gz"
PACKAGE_MANIFEST = HERE / "c27_independent_docker_package_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def verifier_source() -> str:
    return '''"""Verify bounded exact C27 outputs inside the pinned Linux runtime."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys

run = Path(sys.argv[1])
output = Path(sys.argv[2])
scope = os.environ.get("CRSE_EVIDENCE_SCOPE")
if scope not in {"same-host", "independent-machine"}:
    raise SystemExit("invalid CRSE_EVIDENCE_SCOPE")
result = json.loads((run / "results.json").read_text(encoding="utf-8"))
verification = json.loads((run / "independent_verification.json").read_text(encoding="utf-8"))
checks = {
    "result_complete": result.get("status") == "complete",
    "measurement_batches": result.get("measurement_batches") == 720,
    "timed_queries": result.get("timed_queries") == 7560,
    "memory_batches": result.get("memory_measurement_batches") == 24,
    "fallback_controls": result.get("fallback_controls") == 48,
    "selected_path_controls": result.get("selected_path_controls") == 48,
    "refusal_controls": result.get("refusal_controls") == 10,
    "result_exactness": result.get("semantic_or_artifact_mismatches") == 0,
    "verification_status": verification.get("status") == "verified",
    "verified_batches": verification.get("measurement_batches_checked") == 720,
    "verified_queries": verification.get("timed_query_records_checked") == 7560,
    "summary_recomputed": verification.get("summary_recomputed") is True,
    "verified_exactness": verification.get("semantic_or_artifact_mismatches") == 0,
}
if not all(checks.values()):
    raise SystemExit("C27 output invariant failed: " + json.dumps(checks, sort_keys=True))
gate = result.get("summary", {}).get("support_aware_confirmation_gate")
if type(gate) is not bool:
    raise SystemExit("C27 timing gate is missing")
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
record = {
    "schema": "crse-c27-independent-docker-result/v1",
    "status": "verified",
    "evidence_scope": scope,
    "second_machine_replication": scope == "independent-machine",
    "measurement_batches": 720,
    "timed_queries": 7560,
    "memory_batches": 24,
    "semantic_or_artifact_mismatches": 0,
    "independent_verification": "verified",
    "support_aware_confirmation_gate": gate,
    "support_aware_break_even_query_count": result["summary"].get(
        "support_aware_break_even_query_count"),
    "results_sha256": digest(run / "results.json"),
    "independent_verification_sha256": digest(run / "independent_verification.json"),
    "network_during_workload": False,
    "production_promotion": False,
    "training": False,
    "production_write": False,
}
output.write_bytes(json.dumps(record, indent=2, sort_keys=True, allow_nan=False).encode() + b"\\n")
print(json.dumps(record, sort_keys=True))
'''


def runner_source(image: str, run_name: str) -> str:
    return f'''#!/usr/bin/env bash
set -euo pipefail

scope="${{1:-}}"
if [[ "$scope" != "same-host" && "$scope" != "independent-machine" ]]; then
  echo "usage: ./run_c27.sh same-host|independent-machine" >&2
  exit 2
fi
case "$(uname -s)" in
  MINGW*|MSYS*) export MSYS_NO_PATHCONV=1; root="$(pwd -W)" ;;
  *) root="$(pwd -P)" ;;
esac
if [[ -e results || -e c27-results.tar.gz ]]; then
  echo "refusing to overwrite existing results" >&2
  exit 3
fi
sha256sum -c frozen.sha256
mkdir results

image='{image}'
docker build --pull=false --tag "$image" .
docker image inspect "$image" --format '{{{{printf "{{\\\"id\\\":%q,\\\"os\\\":%q,\\\"architecture\\\":%q}}" .Id .Os .Architecture}}}}' > results/docker-image.txt
docker version --format 'Client={{{{.Client.Version}}}} Server={{{{.Server.Version}}}} OS={{{{.Server.Os}}}} Arch={{{{.Server.Arch}}}}' > results/docker-version.txt
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges \\
  "$image" python -B -c 'import json,numpy,platform; print(json.dumps({{"python":platform.python_version(),"numpy":numpy.__version__,"system":platform.system(),"machine":platform.machine()}}))' \\
  > results/runtime.json

common=(docker run --rm --network none --cpus 2 --memory 4g --pids-limit 256
  --read-only --cap-drop ALL --security-opt no-new-privileges
  --env PYTHONDONTWRITEBYTECODE=1 --env OPENBLAS_NUM_THREADS=1
  --env OMP_NUM_THREADS=1 --env MKL_NUM_THREADS=1 --env NUMEXPR_NUM_THREADS=1
  --mount "type=bind,source=$root/frozen,target=/frozen,readonly"
  --mount "type=bind,source=$root/results,target=/output"
  --mount "type=bind,source=$root,target=/package,readonly"
  --tmpfs /work:rw,exec,nosuid,size=268435456
  --tmpfs /tmp:rw,noexec,nosuid,size=67108864)

"${{common[@]}}" "$image" sh -ec \
  "cp -a /frozen/. /work/; ln -s /output /work/run-output; cd /work; exec python -B scripts/cm_comparative_c27_support_aware.py --output run-output/{run_name} --rounds 5 --max-seconds 1200"
"${{common[@]}}" "$image" sh -ec \
  "cp -a /frozen/. /work/; ln -s /output /work/run-output; cd /work; exec python -B scripts/crse_gf2_support_aware_verify.py run-output/{run_name}"
"${{common[@]}}" --env "CRSE_EVIDENCE_SCOPE=$scope" "$image" \
  python -B /package/verify_c27_outputs.py \
  /output/{run_name} /output/PORTABILITY-SUMMARY.json

tar -czf c27-results.tar.gz -C results .
bytes="$(wc -c < c27-results.tar.gz)"
if (( bytes > 16777216 )); then
  echo "result archive exceeds 16 MiB" >&2
  exit 4
fi
printf '{{"status":"complete","scope":"%s","archive_bytes":%s}}\\n' "$scope" "$bytes"
'''


def add_bytes(archive: tarfile.TarFile, name: str, data: bytes, mode: int) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    archive.addfile(info, io.BytesIO(data))


def main() -> int:
    if PACKAGE.exists() or ARCHIVE.exists() or PACKAGE_MANIFEST.exists():
        raise SystemExit("refusing to overwrite C27 independent Docker package")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("file_count") != 63
        or manifest.get("bytes") != 1078671
        or manifest.get("runtime", {}).get("python") != "3.13.15"
        or manifest.get("runtime", {}).get("numpy") != "2.3.2"
    ):
        raise ValueError("C27 independent Docker source manifest mismatch")
    frozen = PACKAGE / "frozen"
    frozen.mkdir(parents=True)
    frozen_lines = []
    for row in manifest["files"]:
        source = ROOT / row["source"]
        target = frozen / row["target"]
        if source.stat().st_size != row["bytes"] or sha256(source) != row["sha256"]:
            raise ValueError(f"C27 frozen source changed: {row['source']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        frozen_lines.append(f"{row['sha256']}  frozen/{row['target']}")
    runtime = manifest["runtime"]
    dockerfile = (
        f"FROM {runtime['image']}\n"
        f"RUN printf '%s\\n' '{runtime['numpy_requirement']}' > /tmp/requirements.txt \\\n"
        " && python -m pip install --disable-pip-version-check --no-cache-dir "
        "--require-hashes -r /tmp/requirements.txt \\\n"
        " && rm /tmp/requirements.txt\n"
    )
    write(PACKAGE / "Dockerfile", dockerfile)
    write(PACKAGE / ".dockerignore", "frozen\nresults\nc27-results.tar.gz\n")
    write(PACKAGE / "frozen.sha256", "\n".join(frozen_lines) + "\n")
    write(PACKAGE / "verify_c27_outputs.py", verifier_source())
    write(PACKAGE / "run_c27.sh", runner_source(
        "crse-c27-independent:python3.13.15-numpy2.3.2", manifest["run_name"]))
    shutil.copyfile(PROTOCOL, PACKAGE / PROTOCOL.name)
    package_files = sorted(
        path for path in PACKAGE.rglob("*") if path.is_file())
    records = [{
        "path": str(path.relative_to(PACKAGE)).replace("\\", "/"),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    } for path in package_files]
    package_manifest = {
        "schema": "crse-c27-independent-docker-package-manifest/v1",
        "status": "frozen",
        "scientific_scope": "independent-machine only when declared and physically distinct",
        "source_manifest_sha256": sha256(MANIFEST),
        "source_files": 63,
        "source_bytes": 1078671,
        "package_files": len(records),
        "package_bytes": sum(row["bytes"] for row in records),
        "files": records,
        "base_image": runtime["image"],
        "numpy_requirement": runtime["numpy_requirement"],
        "network_during_workload": False,
        "result_cap_bytes": manifest["result_cap_bytes"],
        "training": False,
        "production_write": False,
        "credentials_included": False,
    }
    write(PACKAGE / "PACKAGE-MANIFEST.json", json.dumps(
        package_manifest, indent=2, sort_keys=True, allow_nan=False) + "\n")
    package_files.append(PACKAGE / "PACKAGE-MANIFEST.json")
    with tarfile.open(ARCHIVE, "w:gz", compresslevel=9) as archive:
        for path in sorted(package_files):
            relative = str(path.relative_to(PACKAGE)).replace("\\", "/")
            add_bytes(archive, "c27-independent-docker-package/" + relative,
                      path.read_bytes(), 0o755 if relative == "run_c27.sh" else 0o644)
    outer = {
        **package_manifest,
        "package_files": len(package_files),
        "archive_path": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
        "archive_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "embedded_manifest_sha256": sha256(PACKAGE / "PACKAGE-MANIFEST.json"),
    }
    PACKAGE_MANIFEST.write_bytes(json.dumps(
        outer, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "status": "frozen", "source_files": 63, "source_bytes": 1078671,
        "package_files": outer["package_files"],
        "archive_bytes": outer["archive_bytes"],
        "archive_sha256": outer["archive_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
