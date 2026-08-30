# C12 second-machine same-pod retry protocol

Reuse the unchanged frozen 14-file, 355,934-byte C12 package. Create one Secure
Runpod CPU pod and no replacement pod. Require two successful health observations
before upload. If `POST /payload` returns proxy HTTP 404, retry that idempotent
request at most five times on the same owned pod, rechecking health between
attempts. All other upload errors fail closed.

Use the pinned Python 3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral
disk, no pod or network volume, one HTTPS port, a $0.25/hour rate ceiling, and a
controller-enforced $0.05 total ceiling. Retrieve at most 16 MiB, delete the pod
within ten minutes, and reconcile for twelve minutes. No training or production
write is permitted.
