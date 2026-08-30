# RunPod preflight — proof-only CPU proposal

Status: exactly approved v4 execution passed; results downloaded and pod deleted.

The workload is Chromium/SVG/FFmpeg rendering and does not use a GPU. The
proposal therefore requests one Secure Cloud CPU pod in the `cpu5c` family,
requires the returned shape to be exactly 4 vCPU / 8 GB RAM, and fails without
a replacement create if the shape differs. It uses 30 GB ephemeral container
disk, no persistent/network volume, and only `22/tcp` for hash-bound SFTP/SSH
bootstrap. The exact public base image is
`python:3.10.15-slim-bookworm@sha256:97ff6fda70178dee6c144d41030fb88b6ec86d75e1c517fe96b8f62094ea7ac2`.

The deterministic v4 bundle was rebuilt twice with identical bytes. It contains
156 allowlisted files and no Windows absolute path, `.env*`, credential,
database, cache, `node_modules`, proof MP4, historical run, or unrelated CM
corpus. The extracted manifest verified locally. A full container smoke was
not run because the Docker engine is unavailable. The exact Debian bootstrap
and all three worker jobs subsequently passed on RunPod.

RunPod publicly documents CPU pods and the `cpu5c` family but does not publish
CPU Pod rates on its public pricing page. The controller therefore has a
mandatory authenticated pre-create quote gate: no create if the exact quote is
unavailable or above $0.27/hour. The $0.27/hour limit is the current official
public Secure Cloud A5000 Pod price used as a conservative budget anchor, not a
claim that CPU and A5000 pricing are equal. At a 30-minute watchdog this yields
a conservative $0.14 estimate; the hard authorization ceiling is $0.25 total.

The authenticated v4 quote was $0.14/hour. Pod `q7ty5inrxx7w9r` matched the
authorized shape, rendered all three proof jobs, returned a 13,259,511-byte
results archive, and was deleted with final absence verified. Estimated v4
compute cost is $0.013772; pod billing had not posted a matching record at the
first postflight and may lag.

On any success, failure, shape mismatch, or timeout, the controller deletes
only the pod it created and performs final owned-pod inventory reconciliation.
Successful cleanup occurs after result download and hash verification. No paid
non-RunPod service was involved. The v4 one-create authorization is consumed;
no retry or additional pod is queued.
