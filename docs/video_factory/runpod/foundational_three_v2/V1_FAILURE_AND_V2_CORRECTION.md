# Foundational-three v1 postflight and v2 correction

The one create authorized by `cm-video-foundational-three-production-remote-v1` was consumed. The run produced no downloaded or verified video. Estimated compute cost was **$0.1117**, and the exact owned pod was subsequently verified absent.

The v2 bundle corrects the two issues exposed by v1:

1. It includes all six contact-sheet and silent-animatic files referenced by the remote validation report. A clean staged extraction passes all **15/15** validation checks.
2. It launches rendering as a detached in-pod job. The controller polls a durable exit record, reconnects after a transient SSH-monitor interruption, preserves the remote log when possible, and retries exact owned-pod cleanup before relying on the independent watchdog.

The v2 ZIP uses fixed metadata and produced the same SHA-256 on consecutive rebuilds. The exact controller core is also hash-bound in the v2 proposal.

No v2 RunPod resource has been created, and v2 is not authorized until its exact proposal identity is approved.
