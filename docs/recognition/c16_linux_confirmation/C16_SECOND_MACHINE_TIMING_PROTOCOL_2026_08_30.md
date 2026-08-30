# C16 second-machine timing protocol

Upload only the frozen 18-file package described by `c16_linux_upload_manifest.json`.
The workload compares the C16 exact-screened GF(2) tail with the original
exhaustive materializer on the unchanged 40-case Yosys family. It reruns three
balanced rounds and requires identical artifact identity and complete semantic
reconstruction; it performs no training and no production write.

Create one Secure Runpod CPU pod and no replacement. Use the pinned Python
3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no pod or
network volume, one HTTPS port, a $0.25/hour rate ceiling, and a controller
$0.05 total ceiling within the user's $5 authorization. Retrieve at most 16
MiB, delete within ten minutes, and reconcile for twelve minutes.
