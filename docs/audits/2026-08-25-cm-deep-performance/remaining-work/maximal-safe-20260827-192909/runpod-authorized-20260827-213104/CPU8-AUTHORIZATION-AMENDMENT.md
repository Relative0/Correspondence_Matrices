# CPU8 smoke amendment — 2026-08-27

Brian explicitly authorized spending more if needed while asking whether pod availability caused the failure. This supplements the already explicit authorization for uploading the frozen 65-file bundle and running the approved smoke. No additional work, upload destinations, or dependencies are authorized here.

Read-only observations at 16:37–16:40 UTC showed no available two- or four-vCPU CPU3C/CPU3G configurations, while eight-vCPU CPU3C reported HIGH availability at $0.24/hour. The generic creation HTTP 500 does not prove that capacity alone caused the earlier failure.

The next single-pod attempt may therefore use Secure CPU3C with 8 vCPU and at least 16 GB RAM. Its explicit compute-rate ceiling is $0.25/hour; the existing $0.10 total cap, 20-minute maximum lifetime, 10 GB ephemeral disk limit, frozen image digest, exact 65-file upload, 13 pinned binary wheels, and exact smoke commands remain unchanged. The observed quote plus the conservative $0.002/hour storage reserve projects to about $0.080667 for 20 minutes. No GPU, persistent volume, extra workload, public port, SSH/Jupyter service, or source build is added.

Use `runpod_retry_cpu8_controller.py` in a fresh output directory. The prior two-vCPU controller and executed source snapshots are retained unchanged. BLAS/thread settings remain one; record actual CPU/RAM/affinity in any successful result and do not treat this host as interchangeable with previous measurements.

Before launch, verify that the previous ambiguous request has not left a pod, check its watchdog result, confirm fresh inventory and quote, and verify sufficient account credit for the selected one-hour configuration. Arm the new controller's independent network-tested watchdog before creation. Only one pod may be created; do not automatically replace an allocated pod. If creation again returns an uncertain result, reconcile it before any further creation.
