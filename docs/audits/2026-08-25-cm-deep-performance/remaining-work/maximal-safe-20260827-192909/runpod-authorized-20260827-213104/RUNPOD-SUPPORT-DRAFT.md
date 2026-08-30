# Runpod support draft — not sent

Subject: CPU pod provisioning returns HTTP 500 with no pod ID

At approximately 2026-08-27 16:28:29 UTC, an authenticated `POST https://api.runpod.io/v2/pods` returned HTTP 500 with `title: Internal Server Error` and `detail: failed to create pod`. No pod ID was returned. Independent v1 and v2 list-pod requests subsequently returned empty inventories. We are preserving a separate owned-name cleanup watchdog and have stopped creation retries.

The request specified:

- Secure CPU3C, 2 vCPU, 10 GB container disk, no mounts, no ports.
- Official image `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`.
- `startSsh: false`, `startJupyter: false`; no `globalNetworking` field.
- A Python bootstrap command and an approved small source bundle carried in environment variables (163,940 compressed source bytes, base64 encoded). No account credential was passed to the container.
- Unique requested pod name: `cm-memory-smoke-5662bdbfc0de`.

The preceding request at approximately 16:27:35 UTC returned HTTP 400 because `globalNetworking: false` was rejected for a CPU pod. That field was removed before the HTTP 500 attempt.

Additionally, paired catalog requests with identical `include=AVAILABILITY&product=POD&vcpuCount=2` filters returned inconsistent availability:

- 16:24:24 and 16:24:47 UTC: `/v2/catalog/cpus` reported all CPU flavors NONE; `/v2/catalog/cpus/cpu3c` reported HIGH, with US-CA-2 available.
- 16:25:08 UTC: both reported CPU3C HIGH.

Please identify the underlying provisioning error and whether the requested CPU configuration or payload is unsupported. We do not authorize support to create a replacement pod, change account settings, or incur charges from this draft.

This draft deliberately excludes the API key, account identifiers, private source contents, and full environment payload. It has not been emailed, posted, or otherwise sent.
