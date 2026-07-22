"""Poll the pod campaign until done, then download result CSVs."""
import base64
import sys
import time
from pathlib import Path

import requests

REPO = Path(r"C:\Users\brian\Documents\CM_Computation")
sys.path.insert(0, str(REPO))
from cm_runpod_config import load_runpod_config  # noqa: E402

cfg = load_runpod_config()
work = f"https://{cfg.pod_id}-8081.proxy.runpod.net"
out = REPO / "deliverables_n22_24"

while True:
    try:
        p = requests.get(f"{work}/progress", timeout=20).json()
    except Exception as exc:
        print("poll error:", exc, flush=True)
        time.sleep(60)
        continue
    print(f"[{time.strftime('%H:%M:%S')}] cells {p['cells_done']}/{p['cells_total']} "
          f"trials={p['trials_done']} declined={p['declined_total']} "
          f"current={p['current']} elapsed={p['elapsed_s']}s err={bool(p['error'])}", flush=True)
    if p.get("error"):
        print(p["error"])
        raise SystemExit(1)
    if p.get("done"):
        break
    time.sleep(120)

res = requests.get(f"{work}/results", timeout=60).json()
for name in ("raw", "summary"):
    data = base64.b64decode(res[name])
    path = out / f"CM_FABLE_extended_n32_{name}.csv"
    path.write_bytes(data)
    print("saved", path, len(data), "bytes")
print("DONE")
