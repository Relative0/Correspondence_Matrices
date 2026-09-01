# C27 unchanged second-machine replication protocol

Upload only the frozen 63-file, 1,078,671-byte package in
`c27_linux_upload_manifest.json`. It contains the sealed C27 support policy,
fresh dataset and verification, the unchanged C25 direct controls, the C27
session, harness and independent run verifier, and bounded pure-Python runtime
dependencies. It excludes credentials, local timing results, source checkouts,
compiled BDD backends, and unrelated worktree files.

Run the same 48 cases, six methods, five balanced rounds, 1/2/4/8/16/32-query
session schedule, 64-partition bound, four-artifact materialization budget,
single-evaluation verified contexts, and charged final reconstruction used by
the verified Windows run. Then run the independent verifier on the same pod.
No training, policy refit, production write, method substitution, or production
promotion is permitted. A Linux timing-gate failure is a valid result and must
be retrieved rather than retried with changed code or data.

No upload or paid RunPod action is authorized by this freeze. A later exact
authorization should be limited to one Secure CPU pod with no replacement,
the pinned Python 3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral
disk, zero persistent volumes, one HTTPS port, $0.25/hour rate ceiling, and
$0.05 controller cost ceiling. Retrieve at most 16 MiB, delete the owned pod
within ten minutes, and reconcile inventories for twelve minutes.
