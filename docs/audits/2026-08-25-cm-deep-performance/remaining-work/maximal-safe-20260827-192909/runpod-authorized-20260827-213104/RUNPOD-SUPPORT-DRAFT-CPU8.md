# Runpod support draft — CPU8 provisioning failures

Not sent. Prepared 2026-08-28 Bangkok; request timestamps below are UTC.

Subject: CPU3C pod creation fails on REST v1 and v2 despite availability and sufficient credit

Two authenticated CPU3C eight-vCPU creation requests failed with HTTP 500 and no pod ID:

| API | Request UTC | Request ID | Response |
|---|---|---|---|
| `POST https://api.runpod.io/v2/pods` | 2026-08-27 18:02:14.812944 | `req_4451fa8e-cc81-4e6f-9b96-1df429e3ff1c` | `Internal Server Error`, `failed to create pod` |
| `POST https://rest.runpod.io/v1/pods` | 2026-08-27 18:22:23.383459 | `req_9e3ea120-638d-42a7-ab63-5c7d6dc21cf2` | Error below |

The v1 response was:

```text
create pod: unmarshal to struct { Errors []struct { Message string }; Data json.RawMessage }: invalid character 'I' looking for beginning of value
```

Requested names were `cm-memory-smoke-76cade64b163` (v2) and `cm-memory-smoke-755542ee7031` (v1). Each used Secure CPU3C, eight vCPU, 10 GB container disk, zero persistent volume/mounts, and an empty port list. Neither request included SSH/Jupyter or global-networking options. No account credential was injected into the container.

Image:

```text
python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129
```

The v1 request used documented `computeType: CPU`, `cloudType: SECURE`, `cpuFlavorIds: [cpu3c]`, `cpuFlavorPriority: custom`, `vcpuCount: 8`, `containerDiskInGb: 10`, `volumeInGb: 0`, `ports: []`, `dockerEntrypoint: [python, -u, -c]`, and one bootstrap argument in `dockerStartCmd`. The approved source bundle was carried as base64 environment chunks: 163,940 compressed bytes, 16,000-byte maximum environment value, 234,082 total environment-value bytes, 11,622 total argument bytes, and 246,680 estimated JSON request bytes. The v2 request carried equivalent configuration through its schema.

Immediately preceding creation, `/v2/catalog/cpus/cpu3c?include=AVAILABILITY&product=POD&vcpuCount=8` reported HIGH availability at $0.03/vCPU/hour, or $0.24/hour for the request. Account credit and spend limit were sufficient for the one-hour quoted configuration. Earlier bulk and exact-flavor availability responses sometimes disagreed, so we do not treat a catalog quote as proof of successful placement.

Both requests were monitored through their full 20-minute horizons. The independent watchdogs ran on time and found no pod, with no recovery errors. Final independent v1 and v2 inventories at 18:42:24 UTC were empty. All temporary host idle-sleep guards were released. The 18:43 UTC pod-billing snapshot contained zero records and zero total amount; it is not a finalized invoice. No further CPU creation is being attempted, and no GPU fallback has been authorized or launched.

Runpod's status page reported CPU Cloud operational, last updated 2026-08-27 17:51 UTC. The public MCP client currently routes CPU creation to v1, while the newer v2 schema exposes CPU configuration. These observations do not establish the internal cause of this failure.

Please use the request IDs to identify the upstream error and clarify whether the CPU flavor, zero-volume/10-GB-disk configuration, pinned image reference, request size, account eligibility, or placement caused rejection. Please also confirm that neither request produced a chargeable resource. We do not authorize support to create a replacement pod, change account configuration, or incur charges.

This draft excludes API keys, account IDs/balances, private source contents, and the full environment payload. It has not been emailed, posted, or otherwise sent.
