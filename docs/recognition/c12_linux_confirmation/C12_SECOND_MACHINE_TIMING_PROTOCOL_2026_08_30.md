# C12 second-machine timing protocol

Run the frozen robust 4,096-pair one-pass dispatcher and exact controls on the
unchanged 40-case C12 dataset. Use one Secure Runpod CPU pod, no replacement,
Python 3.13.15, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no pod or
network volume, one HTTPS port, a $0.25/hour rate ceiling, a controller-enforced
$0.05 total ceiling, ten-minute cleanup, and twelve-minute reconciliation.
Only the frozen 14-file package may be uploaded. Retrieve at most 16 MiB and
delete the owned pod. No training or production write is permitted.
