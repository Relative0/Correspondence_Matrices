# C12 second-machine package-v2 protocol

Upload only the corrected 16-file C12 package. Relative to the failed 14-file
package it adds `cmbench/output_budget.py` and `cmbench/recognition/features.py`,
the two missing transitive imports. The full workload must first pass from an
isolated directory containing only these 16 files.

Create one Secure Runpod CPU pod and no replacement. Require two successful
health checks and allow at most six idempotent `POST /payload` attempts on that
same pod when the proxy returns HTTP 404. Use the pinned Python 3.13.15 image,
2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no pod or network volume, one
HTTPS port, a $0.25/hour rate ceiling, and a controller-enforced $0.05 total
ceiling. Retrieve at most 16 MiB, delete within ten minutes, and reconcile for
twelve minutes. No training or production write is permitted.
