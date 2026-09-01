# C16 second-machine timing package v2 protocol

Upload only the frozen 18-file package described by
`c16_linux_upload_manifest_v2.json`. This package differs from the first C16
package only in the workload entry point: it adds the uploaded package root to
`sys.path`, matching the import contract already used by the other Linux
confirmation entry points. Package-only validation must not inject `PYTHONPATH`.

The workload compares the C16 exact-screened GF(2) tail with the original
exhaustive materializer on the unchanged 40-case Yosys family. It reruns three
balanced rounds and requires identical artifact identity and complete semantic
reconstruction; it performs no training and no production write.

A future run requires explicit approval of this v2 manifest and protocol.
Create one Secure RunPod CPU pod and no replacement. Use the pinned Python
3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no pod or
network volume, one HTTPS port, a $0.25/hour rate ceiling, and a controller
$0.05 total ceiling within the user's $5 authorization. Retrieve at most 16
MiB, delete within ten minutes, and reconcile for twelve minutes.
