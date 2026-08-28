# CPU8 REST v1 retry — 2026-08-28 Bangkok

This continues Brian's explicit source-upload and smoke authorization, including the CPU8 amendment. It does not authorize another workload, service, destination, or dependency.

## Evidence and reason for changing the request

At 2026-08-27 18:02:14 UTC, the eight-vCPU REST v2 request returned HTTP 500 despite a fresh CPU3C HIGH availability quote at $0.24/hour. Request ID: `req_4451fa8e-cc81-4e6f-9b96-1df429e3ff1c`. No pod ID was returned. Independent v1 and v2 inventories at 18:06 and 18:10 UTC were empty. The authenticated pod-billing snapshot at 18:10 UTC contained zero records and zero total amount; it is not a finalized invoice.

Current primary-source research found that Runpod's own MCP client explicitly routes CPU creation to REST v1 because its v2 CPU creation path is unsupported (code comment AE-2991):

- [Runpod MCP configuration](https://github.com/runpod/runpod-mcp/blob/main/docs/configuration.md)
- [Runpod MCP CPU creation implementation](https://github.com/runpod/runpod-mcp/blob/main/src/tools/pods.ts)
- [Runpod REST v1 creation schema](https://docs.runpod.io/api-reference/pods/POST/pods)
- [Runpod CLI CPU creation implementation](https://github.com/runpod/runpodctl/blob/main/cmd/pod/create.go)

This is a concrete reason to change API paths, not proof of the internal cause of every HTTP 500. The earliest v1 attempt also failed, but used two vCPU and included `globalNetworking: false`; the new request omits that GPU-only option. Additional spending alone is not an established remedy.

## Exact next attempt

Use `runpod_retry_cpu8_v1_controller.py`, initially checked at SHA-256 `40adb66b61ba59dda9282bf264b6767c738d168ed31abc84c790e1c6c2b3ccac`, in a fresh `cpu8-v1-execute-001` directory.

Creation uses `POST https://rest.runpod.io/v1/pods` with `computeType: CPU`, `cloudType: SECURE`, `cpuFlavorIds: [cpu3c]`, `cpuFlavorPriority: custom`, `vcpuCount: 8`, container disk 10 GB, persistent volume 0, and no ports. The pinned image is unchanged. The unchanged bootstrap is encoded as the argument to explicit `python -u -c` entrypoint arrays. No SSH/Jupyter, global networking, GPU, template, registry credential, or external storage is added. Termination prefers REST v1, with v2 as fallback.

The rate ceiling remains $0.25/hour, total $0.10, and maximum pod lifetime 20 minutes; the independent watchdog starts cleanup at 18 minutes. The approved 65 file hashes, 13 binary wheels, commands, thread settings, evidence limit, and stage timeouts remain unchanged. Account credit and spend limit were sufficient at 18:10 UTC. Recheck inventory and live capacity before creation. No account key is uploaded to the worker.

Do not start while the earlier ambiguous CPU8 request is unresolved. Its independent watchdog is armed for 18:20:11 UTC and its original 20-minute horizon ends at 18:22:11 UTC (01:22:11 Bangkok). Require its result plus fresh empty inventories before retrying. Preserve the temporary idle-sleep request while a cleanup process is active; no persistent power configuration is changed. Lid closure, explicit sleep, power failure, and network failure remain limitations.

## Offline validation

`check_cpu8_v1_controller.py` passed syntax, unchanged-bootstrap, exact 65-file hash, and fake-client HTTP 400/500/201 control-flow checks in under one second. HTTP 500 retains the watchdog; success terminates using v1 and exits cleanly. The checks found and fixed an `int([])` success-exit bug in the newly prepared controller only. All prior executed controllers remain unchanged. These checks read no credential and created no real pod; fake fixtures are not workload evidence.

After any actual allocation, do not automatically create a replacement. Collect and independently validate real evidence, then verify termination and query billing. If provisioning still fails, retain the request diagnostics and report the limitation without inventing a benchmark result or a definitive provider root cause.
