"""Provision a temporary high-memory pod for the n=28-32 full-output tail,
push the campaign3 worker, and launch. Writes big pod details to big_pod.json."""
import base64
import json
import secrets
import sys
import time
from pathlib import Path

import requests

REPO = Path(r"C:\Users\brian\Documents\CM_Computation")
SCRATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from cm_runpod_config import load_runpod_config  # noqa: E402
import cm_runpod_deploy as dep  # noqa: E402

cfg = load_runpod_config()
s = requests.Session()
s.headers.update({"Authorization": f"Bearer {cfg.api_key}"})
REST = "https://rest.runpod.io/v1"
token = secrets.token_urlsafe(24)

body = {
    "name": "cm-campaign-large-temp",
    "computeType": "CPU",
    "cloudType": "SECURE",
    "imageName": "python:3.10-slim",
    "containerDiskInGb": 20,
    "volumeInGb": 10,
    "volumeMountPath": "/workspace",
    "ports": ["8080/http", "8081/http"],
    "env": {"CM_BOOTSTRAP_TOKEN": token},
    "dockerEntrypoint": ["sh", "-c"],
    "dockerStartCmd": [dep.START_CMD],
}
pod = None
for flavor, vcpu in (("cpu3m", 16), ("cpu5m", 16), ("cpu3c", 16)):
    attempt = dict(body, cpuFlavorIds=[flavor], vcpuCount=vcpu)
    r = s.post(f"{REST}/pods", json=attempt, timeout=180)
    if r.status_code < 300:
        pod = r.json()
        print(f"created flavor={flavor} vcpu={vcpu} id={pod.get('id')} costPerHr={pod.get('costPerHr')}")
        break
    print(f"flavor {flavor} failed: HTTP {r.status_code} {r.text[:200]}")
if pod is None:
    raise SystemExit("no flavor worked")

pod_id = pod.get("id") or (pod.get("pod") or {}).get("id")
(SCRATCH / "big_pod.json").write_text(json.dumps({"pod_id": pod_id, "token": token}))

# NOTE: the pod was created with the standard START_CMD whose bootstrap reads
# CM_BOOTSTRAP_TOKEN from env — we passed our fresh token above.
boot = f"https://{pod_id}-8080.proxy.runpod.net"
work = f"https://{pod_id}-8081.proxy.runpod.net"
if not dep._wait_health(boot, "cm-bootstrap", 900, 10.0):
    raise SystemExit("bootstrap never healthy on big pod")
print("bootstrap up")
hdr = {"X-CM-Token": token}
pushes = [
    (REPO / "cm_exprlib.py", "cm_exprlib.py"),
    (REPO / "cm_expr_serde.py", "cm_expr_serde.py"),
    (REPO / "bitset_backend.py", "bitset_backend.py"),
    (REPO / "cm_ir.py", "cm_ir.py"),
    (REPO / "cm_runpod_protocol.py", "cm_runpod_protocol.py"),
    (SCRATCH / "cm_campaign3_worker.py", "cm_remote_worker.py"),
]
for path, remote_name in pushes:
    b64 = base64.b64encode(path.read_bytes()).decode()
    r = requests.post(f"{boot}/put", json={"name": remote_name, "b64": b64}, headers=hdr, timeout=120)
    assert r.ok and r.json().get("ok"), (remote_name, r.text[:200])
    print("pushed", remote_name)
r = requests.post(f"{boot}/deploy", json={}, headers=hdr, timeout=60)
assert r.ok and r.json().get("ok"), r.text[:200]
deadline = time.time() + 240
while time.time() < deadline:
    try:
        h = requests.get(f"{work}/health", timeout=10)
        if h.ok and h.json().get("mode") == "campaign2":
            print("campaign3 worker healthy")
            break
    except Exception:
        pass
    time.sleep(5)
else:
    raise SystemExit("worker never healthy")
print(requests.get(f"{work}/progress", timeout=20).json())
