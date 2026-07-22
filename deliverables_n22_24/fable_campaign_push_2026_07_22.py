"""Push the extended campaign to the running pod and launch it."""
import base64
import sys
import time
from pathlib import Path

import requests

REPO = Path(r"C:\Users\brian\Documents\CM_Computation")
SCRATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from cm_runpod_config import load_runpod_config  # noqa: E402

cfg = load_runpod_config()
pod = cfg.pod_id
token = ""
for name in (".env.runpod", ".env.runpod.local"):
    p = REPO / name
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("CM_BOOTSTRAP_TOKEN="):
                token = line.split("=", 1)[1].strip()
boot = f"https://{pod}-8080.proxy.runpod.net"
work = f"https://{pod}-8081.proxy.runpod.net"
hdr = {"X-CM-Token": token} if token else {}

pushes = [
    (REPO / "cm_exprlib.py", "cm_exprlib.py"),
    (REPO / "cm_expr_serde.py", "cm_expr_serde.py"),
    (REPO / "bitset_backend.py", "bitset_backend.py"),
    (REPO / "cm_ir.py", "cm_ir.py"),
    (REPO / "cm_runpod_protocol.py", "cm_runpod_protocol.py"),
    (SCRATCH / "cm_campaign_worker.py", "cm_remote_worker.py"),  # campaign runner
]
for path, remote_name in pushes:
    b64 = base64.b64encode(path.read_bytes()).decode()
    r = requests.post(f"{boot}/put", json={"name": remote_name, "b64": b64},
                      headers=hdr, timeout=120)
    assert r.ok and r.json().get("ok"), (remote_name, r.text[:200])
    print("pushed", remote_name)

r = requests.post(f"{boot}/deploy", json={}, headers=hdr, timeout=60)
assert r.ok and r.json().get("ok"), r.text[:200]
print("deployed; waiting for worker health...")
deadline = time.time() + 180
while time.time() < deadline:
    try:
        h = requests.get(f"{work}/health", timeout=10)
        if h.ok and h.json().get("mode") == "campaign":
            print("campaign worker healthy:", h.json())
            break
    except Exception:
        pass
    time.sleep(4)
else:
    raise SystemExit("worker never became healthy")
print(requests.get(f"{work}/progress", timeout=15).json())
