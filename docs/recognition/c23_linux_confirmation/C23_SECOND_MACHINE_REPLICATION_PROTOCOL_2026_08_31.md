# C23 unchanged second-machine replication protocol

Upload only the frozen 52-file, 903,745-byte package in
`c23_linux_upload_manifest.json`. The package contains the sealed C23 v2
dataset, its independent verification, the unchanged seven C21 method adapters,
the C23 harness and verifier, the frozen screened-policy control, and bounded
pure-Python BDD dependencies. It excludes credentials, local timing results,
source checkouts, compiled BDD backends, and unrelated worktree files.

Run the same 48 cases, seven methods, five balanced rounds, 64-partition bound,
four-artifact materialization budget, fresh-engine single-query lifecycle, and
outside-timing correctness oracle used by the verified Windows run. Then run the
independent verifier on the same pod. No training, policy refit, production
write, or fallback to a changed method is permitted.

The current user request authorizes the following bounded RunPod action within
the standing $5 ceiling: one Secure CPU pod, no replacement, pinned Python
3.13.15 image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, zero persistent
volumes, one HTTPS port, $0.25/hour rate ceiling, and $0.05 controller cost
ceiling. Upload only this manifest, retrieve at most 16 MiB, delete the owned pod
within ten minutes, and reconcile inventories for twelve minutes.
