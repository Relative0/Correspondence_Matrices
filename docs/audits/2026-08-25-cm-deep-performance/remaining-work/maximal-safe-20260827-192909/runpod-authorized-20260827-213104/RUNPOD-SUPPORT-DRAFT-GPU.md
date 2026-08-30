# Draft for Runpod support — not sent

Please investigate pod creation failures across CPU/GPU and REST API versions. We need the underlying placement, validation, image, payload, or account error, and confirmation that the failed requests did not allocate resources. No API key, account balance, source bundle, environment values, or other credentials are included in this draft.

## Requests on 2026-08-27 UTC

| Request | Hardware | Time | Response | Request ID |
|---|---|---|---|---|
| POST `https://api.runpod.io/v2/pods` | CPU3C, 8 vCPU, 16 GB | 18:02:14.812944 | 500, failed to create pod | `req_4451fa8e-cc81-4e6f-9b96-1df429e3ff1c` |
| POST `https://rest.runpod.io/v1/pods` | CPU3C, 8 vCPU, 16 GB | 18:22:23.383459 | 500, upstream response parsing error | `req_9e3ea120-638d-42a7-ab63-5c7d6dc21cf2` |
| POST `https://api.runpod.io/v2/pods` | 1 Secure NVIDIA RTX PRO 4000 Blackwell | 19:19:41.497195 | 500, failed to create pod | `req_5353d7a7-aeaf-40ac-9a1d-5a6e3f3cd636` |

The CPU v1 detail was:

```text
create pod: unmarshal to struct { Errors []struct { Message string }; Data json.RawMessage }: invalid character 'I' looking for beginning of value
```

The GPU response had `Date: Thu, 27 Aug 2026 19:19:42 GMT`, `CF-Ray: a31d6de6bbe40960-HKG`, and JSON `title: Internal Server Error`, `detail: failed to create pod`. No request returned a pod ID.

## GPU preflight and sanitized request shape

At 19:19:41.430 UTC, the exact GPU catalog query returned `secure: true`, `availability: LOW`, `price.secure: 0.57`, and LOW availability in EU-RO-1. Query: `/v2/catalog/gpus/NVIDIA%20RTX%20PRO%204000%20Blackwell?include=AVAILABILITY&product=POD&cloud=SECURE&count=1`. Both inventories were empty, available credit and hourly spend limit passed, and the pod-billing snapshot contained zero records and zero charges. The earlier CPU requests had HIGH availability at $0.24/hour. We understand these are snapshots, not allocation guarantees or final invoices.

GPU request fields were `name`, `cloud`, `image`, `disk`, `mounts`, `gpu`, `ports`, `env`, and `args`:

- Secure cloud; exact GPU ID above, count 1; no CPU field or alternate hardware list.
- Image `python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129`.
- Disk 10 GB; mounts `{}`; ports `[]`; no template, registry credentials, SSH/Jupyter, or global-networking request.
- An inline Python bootstrap and a base64 source ZIP in chunked environment variables. No Runpod API key in the worker environment.
- Serialized JSON body approximately 246,550 bytes, argument string 11,635 bytes, environment values 234,082 bytes total, largest value 16,000 bytes. The archive is 163,940 bytes for 65 approved source/test/lock files.

Please check whether the backend accepts this image digest syntax, command length, environment-value size and aggregate payload, empty mounts with no persistent volume, and this exact GPU type. The public schema does not establish the actual upstream limits for this combination. We have not established that request size, image handling, account eligibility, or capacity caused the 500 responses. Raising the hardware price did not resolve this attempt.

## Cleanup evidence

Both CPU requests were reconciled after their full 20-minute horizons with empty v1/v2 inventories and no watchdog errors. The GPU watchdog activated at 19:37:36.755 UTC, found no pod, and reported no recovery errors. All 26 independent inventory snapshots succeeded with zero pods; the final horizon check completed at 19:39:43 UTC. A further inventory/billing check at 19:40 UTC found both inventories empty and zero pod-billing records/charges. Billing may lag. All temporary host sleep guards were released. Final proof is in `GPU-FINAL-RECONCILIATION.json` and `GPU-FINAL-OUTCOME.json`.

No installation, focused tests, or memory study has been observed on a worker. No automatic replacement is queued. Please advise on the supported correction before another paid attempt.

Local preparation only: contacting support or sharing this draft needs Brian's explicit confirmation of the target and effect.
