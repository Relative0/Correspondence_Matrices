> ## Documentation Index
> Fetch the complete documentation index at: https://docs.runpod.io/llms.txt
> Use this file to discover all available pages before exploring further.

# Create a pod

> Creates a new pod. `name` is always required; supply exactly one of
`gpu` or `cpu` to select compute (a GPU or a CPU pod). Container
settings come from the body, from a template referenced by
`templateId` (body fields override the template's), or both; `image`
is required unless `templateId` is set. See `CreatePodRequest` for
the full body.

Returns `201` with the created pod. Provisioning is asynchronous: the
pod starts in `PROVISIONING`, transitions through `STARTING`, and
reaches `RUNNING` once its container is healthy. Poll `getPod` (or
watch the pod's `status`) to observe readiness rather than assuming
the pod is running when this call returns.

## Checking what you can deploy

This endpoint places one specific GPU type. It does not search for
capacity, and it does not fall back to a different GPU. To find out
what is deployable before you call it, read the catalog:

- [List GPU types](https://docs.runpod.io/api-reference-v2/catalog/list-gpu-types)
  — GPU types with pricing, per-cloud ceilings, and, with
  `include=AVAILABILITY&product=POD`, current pod stock.
- [List data centers](https://docs.runpod.io/api-reference-v2/catalog/list-data-centers)
  — locations, with `include=GPU_AVAILABILITY` for stock per data
  center.

Both accept filters that combine, so you can narrow by location and by
compute in one request — for example
`GET /v2/catalog/datacenters?regions=EUROPE&include=GPU_AVAILABILITY`
returns only European data centers, each carrying the GPU types
currently available there.

## Deploying under region and GPU constraints

If you need a particular GPU in a particular geography, the working
pattern is read-then-create: narrow the catalog to an acceptable
(data center, GPU) set, then call this endpoint once per candidate in
your order of preference until one returns `201`. The runnable sample
alongside this operation does exactly that.

Availability can change between the catalog read and the create call,
so treat the catalog as a way to order your candidates, not as a
reservation — a create can still fail for capacity on a GPU the
catalog just reported as available.

Which failures are worth retrying:

| Status | Meaning | Do |
| --- | --- | --- |
| `422` | The body does not match the contract. `errors` lists each violation. | Fix the request. Never retry. |
| `400` | The body matches the contract but was rejected — either it breaks a cross-field rule, or this GPU and data center combination could not be placed. | Try your next candidate. |
| `402` | Insufficient balance. | Stop; no candidate will succeed. |
| `403` | Your account cannot access the requested pool. | Skip this candidate, keep going. |
| `429` | Rate limited. | Back off using `Retry-After`, then resume. |
| `5xx` | Transient upstream failure. | Retry the same candidate with backoff. |

`400` covers both "your request breaks a rule" and "no capacity",
because capacity exhaustion currently carries no machine-readable code
of its own — only a human-readable `detail`. A rule violation is
deterministic, so it fails identically on every candidate: if *every*
candidate returns `400`, read the last `detail` as a problem with the
request rather than as absent capacity.




## OpenAPI

````yaml post /v2/pods
openapi: 3.1.0
info:
  title: Runpod REST API
  version: 2.0.0
  description: Runpod public REST API — v2
servers:
  - url: https://api.runpod.io
    description: Runpod API v2 production server
security:
  - bearerAuth: []
tags:
  - name: Account
    description: Account-scoped settings and primitives (SSH public keys).
  - name: Pods
    description: GPU and CPU pod lifecycle, configuration, actions, and log streaming.
  - name: Serverless
    description: >-
      Serverless endpoint lifecycle, worker visibility, releases, and worker log
      streaming.
  - name: Templates
    description: Reusable pod and endpoint configuration templates.
  - name: Network Volumes
    description: Persistent network storage volumes for workloads.
  - name: Registries
    description: Container registry credentials used to pull private images.
  - name: Catalog
    description: Available GPU, CPU, data center, and public template catalog metadata.
  - name: Billing
    description: Billing history and usage cost records across resource types.
paths:
  /v2/pods:
    post:
      tags:
        - Pods
      summary: Create a pod
      description: >
        Creates a new pod. `name` is always required; supply exactly one of

        `gpu` or `cpu` to select compute (a GPU or a CPU pod). Container

        settings come from the body, from a template referenced by

        `templateId` (body fields override the template's), or both; `image`

        is required unless `templateId` is set. See `CreatePodRequest` for

        the full body.


        Returns `201` with the created pod. Provisioning is asynchronous: the

        pod starts in `PROVISIONING`, transitions through `STARTING`, and

        reaches `RUNNING` once its container is healthy. Poll `getPod` (or

        watch the pod's `status`) to observe readiness rather than assuming

        the pod is running when this call returns.


        ## Checking what you can deploy


        This endpoint places one specific GPU type. It does not search for

        capacity, and it does not fall back to a different GPU. To find out

        what is deployable before you call it, read the catalog:


        - [List GPU
        types](https://docs.runpod.io/api-reference-v2/catalog/list-gpu-types)
          — GPU types with pricing, per-cloud ceilings, and, with
          `include=AVAILABILITY&product=POD`, current pod stock.
        - [List data
        centers](https://docs.runpod.io/api-reference-v2/catalog/list-data-centers)
          — locations, with `include=GPU_AVAILABILITY` for stock per data
          center.

        Both accept filters that combine, so you can narrow by location and by

        compute in one request — for example

        `GET /v2/catalog/datacenters?regions=EUROPE&include=GPU_AVAILABILITY`

        returns only European data centers, each carrying the GPU types

        currently available there.


        ## Deploying under region and GPU constraints


        If you need a particular GPU in a particular geography, the working

        pattern is read-then-create: narrow the catalog to an acceptable

        (data center, GPU) set, then call this endpoint once per candidate in

        your order of preference until one returns `201`. The runnable sample

        alongside this operation does exactly that.


        Availability can change between the catalog read and the create call,

        so treat the catalog as a way to order your candidates, not as a

        reservation — a create can still fail for capacity on a GPU the

        catalog just reported as available.


        Which failures are worth retrying:


        | Status | Meaning | Do |

        | --- | --- | --- |

        | `422` | The body does not match the contract. `errors` lists each
        violation. | Fix the request. Never retry. |

        | `400` | The body matches the contract but was rejected — either it
        breaks a cross-field rule, or this GPU and data center combination could
        not be placed. | Try your next candidate. |

        | `402` | Insufficient balance. | Stop; no candidate will succeed. |

        | `403` | Your account cannot access the requested pool. | Skip this
        candidate, keep going. |

        | `429` | Rate limited. | Back off using `Retry-After`, then resume. |

        | `5xx` | Transient upstream failure. | Retry the same candidate with
        backoff. |


        `400` covers both "your request breaks a rule" and "no capacity",

        because capacity exhaustion currently carries no machine-readable code

        of its own — only a human-readable `detail`. A rule violation is

        deterministic, so it fails identically on every candidate: if *every*

        candidate returns `400`, read the last `detail` as a problem with the

        request rather than as absent capacity.
      operationId: createPod
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreatePodRequest'
            examples:
              gpuPod:
                summary: GPU pod
                value:
                  name: pytorch-training
                  image: runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404
                  gpu:
                    id: NVIDIA GeForce RTX 4090
                    count: 1
                  disk: 50
      responses:
        '201':
          headers:
            RateLimit:
              $ref: '#/components/headers/RateLimit'
            RateLimit-Policy:
              $ref: '#/components/headers/RateLimit-Policy'
          description: Created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Pod'
              examples:
                pod:
                  summary: Successful response
                  value:
                    id: 7h9k2m4n6p
                    name: pytorch-training
                    image: runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404
                    args: ''
                    disk: 50
                    ports:
                      - 8888/http
                      - 22/tcp
                    env:
                      MODEL_NAME: llama-3
                    registry: null
                    status: PROVISIONING
                    actions:
                      - start
                      - terminate
                    mounts:
                      persistent:
                        size: 20
                        path: /workspace
                    gpu:
                      id: NVIDIA GeForce RTX 4090
                      count: 1
                    cloud: SECURE
                    dataCenterId: US-KS-2
                    cudaVersion: '12.8'
                    ssh:
                      proxy:
                        host: ssh.runpod.io
                        port: 22
                        username: 7h9k2m4n6p-64411eb2
                        command: ssh 7h9k2m4n6p-64411eb2@ssh.runpod.io
                      direct: null
                    template: 9x4m2p7v
                    cost: 0.44
                    locked: false
                    globalNetworking:
                      enabled: false
                    runtime: {}
                    createdAt: '2026-06-01T12:00:00Z'
                    startedAt: null
        '400':
          $ref: '#/components/responses/BadRequestError'
        '401':
          $ref: '#/components/responses/UnauthorizedError'
        '403':
          $ref: '#/components/responses/ForbiddenError'
        '404':
          $ref: '#/components/responses/NotFoundError'
        '422':
          $ref: '#/components/responses/UnprocessableEntityError'
        '429':
          $ref: '#/components/responses/TooManyRequestsError'
        default:
          headers:
            RateLimit:
              $ref: '#/components/headers/RateLimit'
            RateLimit-Policy:
              $ref: '#/components/headers/RateLimit-Policy'
          description: Error
          content:
            application/problem+json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
      x-codeSamples:
        - lang: Python
          label: Region-constrained deploy loop
          source: >
            import os

            import time


            import requests


            API = "https://api.runpod.io"

            SESSION = requests.Session()

            SESSION.headers["Authorization"] = f"Bearer
            {os.environ['RUNPOD_API_KEY']}"


            # Most preferred GPU first. The loop stops at the first one that
            places.

            GPU_PREFERENCE = [
                "NVIDIA GeForce RTX 4090",
                "NVIDIA GeForce RTX 5090",
                "NVIDIA H100 PCIe",
            ]

            USABLE = {"LOW", "MEDIUM", "HIGH"}  # anything but NONE



            def candidates(region):
                """(gpu_id, datacenter_id) pairs that the catalog reports as deployable,
                ordered by GPU_PREFERENCE then by descending stock."""
                response = SESSION.get(
                    f"{API}/v2/catalog/datacenters",
                    params={"regions": region, "include": "GPU_AVAILABILITY"},
                    timeout=30,
                )
                response.raise_for_status()

                rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
                found = []
                for datacenter in response.json()["dataCenters"]:
                    for gpu in datacenter.get("gpuAvailability", []):
                        if gpu["id"] in GPU_PREFERENCE and gpu["availability"] in USABLE:
                            found.append((gpu["id"], datacenter["id"], gpu["availability"]))

                found.sort(key=lambda c: (GPU_PREFERENCE.index(c[0]), rank[c[2]]))
                return [(gpu_id, dc_id) for gpu_id, dc_id, _ in found]


            def create(gpu_id, datacenter_id):
                return SESSION.post(
                    f"{API}/v2/pods",
                    json={
                        "name": "inference-worker",
                        "image": "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404",
                        "gpu": {"id": gpu_id, "count": 1},
                        "dataCenterIds": [datacenter_id],
                        "disk": 50,
                    },
                    timeout=60,
                )


            def create_with_backoff(gpu_id, datacenter_id, attempts=5):
                """Rate limits and 5xx are not the candidate's fault, so they are
                retried in place rather than moving to the next GPU."""
                for attempt in range(attempts):
                    response = create(gpu_id, datacenter_id)
                    if response.status_code == 429:
                        # Retry-After is integer seconds on this API.
                        time.sleep(int(response.headers.get("Retry-After", 5)))
                        continue
                    if response.status_code >= 500:
                        time.sleep(2**attempt)
                        continue
                    return response
                raise RuntimeError(f"{attempts} transient failures for {gpu_id}; upstream unhealthy")


            def deploy(region="EUROPE"):
                last_detail = None

                for gpu_id, datacenter_id in candidates(region):
                    response = create_with_backoff(gpu_id, datacenter_id)

                    if response.status_code == 201:
                        return response.json()

                    problem = response.json()
                    last_detail = problem.get("detail")

                    if response.status_code == 422:
                        # Contract violation — identical on every candidate.
                        raise SystemExit(f"Bad request: {problem.get('errors', last_detail)}")
                    if response.status_code == 402:
                        raise SystemExit(f"Cannot deploy: {last_detail}")
                    if response.status_code in (400, 403):
                        # 403: no access to this pool. 400: rule violation, or this
                        # GPU/data center could not be placed. Either way, move on.
                        continue

                    response.raise_for_status()

                # Every candidate was refused. A rule violation fails the same way on
                # all of them, so the last detail is the useful signal here.
                raise SystemExit(f"No candidate placed in {region}. Last error: {last_detail}")


            if __name__ == "__main__":
                pod = deploy()
                print(f"{pod['id']} placed in {pod['dataCenterId']} on {pod['gpu']['id']}")
components:
  schemas:
    CreatePodRequest:
      allOf:
        - $ref: '#/components/schemas/ContainerConfig'
        - type: object
          required:
            - name
          description: |
            Request body for creating a pod. Exactly one of `gpu` or `cpu`
            must be set — enforced at the handler layer. For CPU pods, memory
            is derived by the API from the selected flavor's RAM multiplier;
            clients provide only CPU flavor and vCPU count. CPU pods support
            container disk and network volumes only; `mounts.persistent` is
            invalid when `cpu` is set.

            `image` is required unless `templateId` is set.
          properties:
            name:
              type: string
              minLength: 1
              examples:
                - my-training-pod
            cloud:
              allOf:
                - $ref: '#/components/schemas/Cloud'
              default: SECURE
              description: Cloud tier. Defaults to `SECURE` when omitted.
            cpu:
              $ref: '#/components/schemas/CreateCpuConfig'
            dataCenterIds:
              type: array
              items:
                type: string
              description: |
                Preferred data centers for placement. Omit or pass an empty
                array to let the scheduler choose.
              examples:
                - - US-TX-3
            globalNetworking:
              type: boolean
              default: false
              description: >-
                Enable global networking, giving the pod a private IP reachable
                across data centers. Requires an NVIDIA GPU and a
                global-networking-enabled data center (both enforced upstream).
                See `GET /v2/catalog/datacenters` (`globalNetwork`) for eligible
                data centers.
              examples:
                - false
            gpu:
              $ref: '#/components/schemas/CreateGpuConfig'
            mounts:
              $ref: '#/components/schemas/Mounts'
            startJupyter:
              type: boolean
              default: false
              description: |
                Create-time flag telling the provisioner to start JupyterLab:
                injects a generated `JUPYTER_PASSWORD` environment variable,
                unless the request already sets one. Only images that honor
                the convention start Jupyter from it (RunPod official images
                do); expose `8888/http` in `ports` to reach it.

                Not part of the pod's readable config — never returned by
                GET and not changeable by PATCH.
              examples:
                - true
            startSsh:
              type: boolean
              default: false
              description: |
                Create-time flag telling the provisioner to set up SSH
                access: injects a `PUBLIC_KEY` environment variable carrying
                your account's registered SSH public keys, unless the request
                already sets one. **Requires registered keys** (`PUT
                /v2/account/ssh-keys`) — with none registered the flag does
                nothing and the pod has no SSH access. Only images that honor
                the convention start sshd from it (all RunPod official images
                do). Connect using the pod's `ssh` block; the `ssh.direct`
                variant additionally needs a `22/tcp` entry in `ports`.

                Not part of the pod's readable config — never returned by
                GET and not changeable by PATCH.
              examples:
                - true
            templateId:
              type: string
              minLength: 1
              description: |
                ID of a pod template to base this pod on. The template is
                resolved at create time into the same container settings you
                could otherwise spread into this body (image, args, disk,
                ports, env, registry, persistent mount, startSsh,
                startJupyter, allowedCudaVersions); explicit body fields
                override the template's, except `env`, which is merged per
                key with body values winning. Sending either CUDA field
                (`gpu.allowedCudaVersions` or `gpu.minCudaVersion`) replaces
                the template's CUDA constraint entirely, and CPU pods ignore
                it (like the persistent mount). The template is a one-time
                source of settings: later template edits do not affect the
                pod, and the created pod does not retain a link to the
                template (`template` stays null). The template may be one
                of your own or a public catalog template — see
                `GET /v2/catalog/templates` (unknown or inaccessible ID →
                404) — and must not be a serverless template (→ 422). CPU
                pods do not inherit a template's persistent mount.
              examples:
                - 30zmvf89kd
      unevaluatedProperties: false
      if:
        not:
          required:
            - templateId
      then:
        required:
          - image
    Pod:
      allOf:
        - $ref: '#/components/schemas/ContainerConfig'
        - type: object
          required:
            - id
            - name
            - status
            - actions
            - image
            - args
            - disk
            - mounts
            - ports
            - env
            - registry
            - cloud
            - dataCenterId
            - cudaVersion
            - ssh
            - template
            - cost
            - locked
            - runtime
            - createdAt
            - startedAt
            - globalNetworking
          properties:
            id:
              type: string
              examples:
                - pod_abc123
            name:
              type: string
              examples:
                - my-training-pod
            status:
              $ref: '#/components/schemas/PodStatus'
            actions:
              type: array
              description: Valid state transitions for the current status.
              items:
                $ref: '#/components/schemas/PodAction'
            mounts:
              $ref: '#/components/schemas/Mounts'
            gpu:
              description: Present for GPU pods; omitted from CPU pods.
              allOf:
                - $ref: '#/components/schemas/GpuConfig'
            cpu:
              description: Present for CPU pods; omitted from GPU pods.
              allOf:
                - $ref: '#/components/schemas/CpuConfig'
            cloud:
              $ref: '#/components/schemas/Cloud'
            dataCenterId:
              type:
                - string
                - 'null'
              description: Data center where the pod is running (assigned by scheduler)
              examples:
                - US-TX-3
            cudaVersion:
              type:
                - string
                - 'null'
              description: >-
                CUDA version reported by the host machine. Retained while the
                pod is stopped — a stopped pod keeps its machine assignment and
                resumes onto the same host. Null means unknown or not applicable
                (CPU pods, or a host that has not reported one), not that CUDA
                is absent.
              examples:
                - '12.8'
            ssh:
              allOf:
                - $ref: '#/components/schemas/PodSsh'
              description: >-
                SSH connection details, via the Runpod proxy or directly to the
                pod's published `22/tcp` port.
            cluster:
              description: >-
                Cluster membership; omitted from a standalone pod. Member pods
                are managed through `/v2/clusters/{id}` — they are excluded from
                `GET /v2/pods` by default (pass `includeClusterPods=true` to
                include them) and cannot be modified or deleted via the pod
                endpoints.
              allOf:
                - $ref: '#/components/schemas/PodCluster'
            template:
              type:
                - string
                - 'null'
              description: ID of the template this pod was created from
              examples:
                - null
            cost:
              type: number
              format: float
              description: Current cost in USD per hour (0.0 when EXITED or TERMINATED)
              examples:
                - 0.35
            locked:
              type: boolean
              description: Whether the pod is locked (prevents stopping or resetting)
              examples:
                - false
            globalNetworking:
              $ref: '#/components/schemas/PodGlobalNetworking'
            runtime:
              description: Live utilization metrics. Null when the pod is not RUNNING.
              anyOf:
                - $ref: '#/components/schemas/PodRuntime'
                - type: 'null'
            createdAt:
              type: string
              format: date-time
              examples:
                - '2026-03-13T20:00:00Z'
            startedAt:
              type:
                - string
                - 'null'
              format: date-time
              examples:
                - '2026-03-13T20:00:00Z'
    ErrorResponse:
      type: object
      required:
        - title
        - status
        - detail
      properties:
        title:
          type: string
          description: Short human-readable summary
          examples:
            - Not Found
        status:
          type: integer
          description: HTTP status code
          examples:
            - 404
        detail:
          type: string
          description: Human-readable explanation
          examples:
            - pod not found
        errors:
          type: array
          description: Individual request-validation failures.
          items:
            type: string
          examples:
            - - '$: additional properties ''bogus'' not allowed'
    ContainerConfig:
      description: >
        Reusable container configuration shared across templates, pods, and
        serverless endpoints. Adding a field here automatically propagates to
        all three resources.
      allOf:
        - $ref: '#/components/schemas/BaseContainerConfig'
        - type: object
          properties:
            registry:
              type:
                - string
                - 'null'
              description: Container registry credential ID (for private images)
              examples:
                - null
    Cloud:
      type: string
      description: |
        Cloud tier.
        - `SECURE`    — Runpod-owned datacenter hardware
        - `COMMUNITY` — community-hosted hardware
      enum:
        - SECURE
        - COMMUNITY
    CreateCpuConfig:
      allOf:
        - $ref: '#/components/schemas/BaseCpuConfig'
      unevaluatedProperties: false
    CreateGpuConfig:
      description: |
        GPU request for a pod create. Carries the CUDA host constraints, which
        live here rather than at the body's top level so they are
        unrepresentable on a CPU pod.
      allOf:
        - $ref: '#/components/schemas/GpuConfig'
        - type: object
          properties:
            allowedCudaVersions:
              type: array
              items:
                type: string
                pattern: ^\d+\.\d+$
              description: |
                Acceptable CUDA versions for the host machine, as `major.minor`.
                Omit to accept any version. Matching is exact, so a version no
                machine reports yields a capacity error rather than a fallback —
                discover valid values per GPU type via
                `GET /v2/catalog/gpus?include=AVAILABILITY&product=POD`
                (`cudaVersions`).

                A non-empty set is mutually exclusive with minCudaVersion (400
                if both are sent). An explicit `[]` states no constraint, so it
                may accompany a floor.
              examples:
                - - '12.8'
                  - '12.6'
            minCudaVersion:
              type: string
              pattern: ^\d+\.\d+$
              description: |
                Lowest acceptable CUDA version for the host machine, as
                `major.minor`, compared numerically rather than as a decimal —
                so 12.11 is above 12.2. Use this for an open-ended floor and
                allowedCudaVersions for an exact set.

                Mutually exclusive with a non-empty allowedCudaVersions (400 if
                both are sent); an explicit `[]` there states no constraint and
                may accompany this floor.
              examples:
                - '12.1'
      unevaluatedProperties: false
    Mounts:
      type: object
      additionalProperties: false
      description: |
        Storage mounts attached to a pod. At-most-one of `persistent` or
        `network` may be set today (mutually exclusive, enforced at the
        handler with 400 if both are present). The `network` field is an
        array for forward compatibility with eventual multi-network-volume
        support, but `maxItems` is 1 today.

        PATCH semantics:
        - Omitting `mounts` or sending `{}` leaves the existing mount
          unchanged.
        - An explicit `network: []` is rejected with 400 (clearing mounts
          is not supported).
        - Mount kind is fixed at create — a PATCH that introduces a kind
          not present at create (persistent on a network pod, network on
          a persistent pod, or any mount on a previously-mountless pod)
          is rejected with 400.
        - The `volumeId` of a network mount is immutable; a PATCH that
          names a different `volumeId` is rejected with 400.
        - Partial mounts are not supported — every mount entry must
          include the full schema (`size` + `path` for persistent,
          `volumeId` + `path` for network). Missing required fields → 422.
      properties:
        persistent:
          $ref: '#/components/schemas/PersistentMount'
        network:
          type: array
          maxItems: 1
          items:
            $ref: '#/components/schemas/NetworkMount'
    RateLimitHeader:
      type: string
      description: |
        Live per-window quota state. Optional — omitted for rate-limit-exempt
        callers.

        A structured-field list with one member per window (`minute`, `hour`,
        `day`), each carrying the remaining request count `r` and seconds until
        the window resets `t`. Returned on responses to authenticated requests,
        not only on 429s.
      examples:
        - '"minute";r=0;t=12, "hour";r=2800;t=1812, "day";r=49500;t=45012'
    RateLimitPolicyHeader:
      type: string
      description: >
        Static per-window quota policy. Optional — omitted for rate-limit-exempt

        callers.


        A structured-field list with one member per window (`minute`, `hour`,

        `day`), each carrying the quota `q` and the window length in seconds
        `w`.

        Returned on responses to authenticated requests, not only on 429s.
      examples:
        - '"minute";q=60;w=60, "hour";q=3000;w=3600, "day";q=50000;w=86400'
    PodStatus:
      type: string
      description: |
        Lifecycle status of a pod.
        - `PROVISIONING` — pod is being allocated
        - `STARTING`     — container is starting
        - `RUNNING`      — container is healthy
        - `EXITED`       — container exited (stopped)
        - `ERROR`        — container is in an unrecoverable error state
        - `TERMINATED`   — pod has been permanently deleted
      enum:
        - PROVISIONING
        - STARTING
        - RUNNING
        - EXITED
        - ERROR
        - TERMINATED
    PodAction:
      type: string
      description: State transition to trigger on a pod.
      enum:
        - start
        - stop
        - restart
        - terminate
    GpuConfig:
      type: object
      required:
        - id
      properties:
        id:
          type: string
          description: GPU type identifier
          examples:
            - NVIDIA GeForce RTX 4090
        count:
          type: integer
          minimum: 1
          default: 1
          description: Number of GPUs
          examples:
            - 1
    CpuConfig:
      allOf:
        - $ref: '#/components/schemas/BaseCpuConfig'
        - type: object
          required:
            - memory
          properties:
            memory:
              type: integer
              minimum: 1
              description: Memory allocated to the pod in GB.
              examples:
                - 16
    PodSsh:
      type: object
      required:
        - proxy
        - direct
      description: >-
        How to connect to this pod over SSH. Both variants authenticate with the
        account's registered SSH public keys (`PUT /v2/account/ssh-keys`), which
        reach the pod only if it was created with `startSsh` — a pod created
        without it has no SSH access regardless of what this block reports.
      properties:
        proxy:
          description: >-
            Connection through Runpod's SSH proxy. Works without exposing a port
            and without a public IP, but carries an interactive shell only —
            SCP, SFTP, rsync, and port forwarding need `direct`. Null until the
            pod has a machine assignment.
          anyOf:
            - $ref: '#/components/schemas/PodSshEndpoint'
            - type: 'null'
        direct:
          description: >-
            Connection straight to the pod's sshd over its published `22/tcp`
            mapping. Supports the full SSH feature set. Null unless `22/tcp` is
            in `ports` and the running pod has been assigned a public port for
            it — so it is absent while the pod is provisioning or stopped.
          anyOf:
            - $ref: '#/components/schemas/PodSshEndpoint'
            - type: 'null'
    PodCluster:
      type: object
      additionalProperties: false
      description: A pod's membership in a cluster.
      required:
        - id
        - rank
      properties:
        id:
          type: string
          description: ID of the cluster this pod belongs to.
          examples:
            - cluster_abc123
        rank:
          type:
            - integer
            - 'null'
          description: >-
            The pod's node rank within the cluster (NODE_RANK), or null until
            the index is assigned during provisioning. Rank 0 is the cluster's
            entry node (`Cluster.primary`); for SLURM it is the controller.
          examples:
            - 0
        role:
          description: >-
            SLURM or RAY role; omitted for TRAINING/APPLICATION clusters, which
            do not assign roles.
          allOf:
            - $ref: '#/components/schemas/PodClusterRole'
        ip:
          type: string
          description: >-
            The pod's address on the cluster's private overlay network; omitted
            until the address is assigned.
          examples:
            - 10.65.0.2
    PodGlobalNetworking:
      type: object
      required:
        - enabled
      properties:
        enabled:
          type: boolean
          description: >-
            Whether global networking is enabled, giving the pod a private IP
            reachable across data centers. Derived from whether the pod has an
            assigned global-network address.
          examples:
            - true
        ip:
          type: string
          description: The pod's assigned global-networking IP. Present only when enabled.
          examples:
            - 10.65.1.42
        internalDns:
          type: string
          description: >-
            Internal DNS name (`<podId>.runpod.internal`), reachable from other
            globally-networked pods in the same account. Present only when
            enabled.
          examples:
            - gfj8b292vyg08g.runpod.internal
    PodRuntime:
      type: object
      description: Live utilization metrics for a running pod.
      properties:
        uptime:
          type: integer
          description: Seconds since the container started
          examples:
            - 3600
        gpus:
          type: array
          items:
            $ref: '#/components/schemas/PodGpuUtilization'
        cpu:
          $ref: '#/components/schemas/Utilization'
        memory:
          $ref: '#/components/schemas/Utilization'
        ports:
          type: array
          items:
            $ref: '#/components/schemas/PodRuntimePort'
    BaseContainerConfig:
      type: object
      description: >
        Container configuration universal to every containerized resource.
        Compose ContainerConfig instead unless the resource cannot support
        private registries (clusters, until the upstream input accepts a
        registry credential).
      properties:
        args:
          type: string
          description: Arguments passed to the container entrypoint
          examples:
            - ''
        disk:
          type: integer
          minimum: 1
          description: Container disk in GB (ephemeral, wiped on restart)
          examples:
            - 50
        env:
          type: object
          additionalProperties:
            type: string
          description: Environment variables as key-value pairs
          examples:
            - JUPYTER_PASSWORD: hunter2
        image:
          type: string
          description: Docker image reference
          examples:
            - runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404
        ports:
          type: array
          description: Exposed ports, formatted as port/protocol
          items:
            type: string
          examples:
            - - 8888/http
              - 22/tcp
    BaseCpuConfig:
      type: object
      required:
        - id
        - vcpuCount
      properties:
        id:
          type: string
          description: CPU flavor identifier, as returned by GET /v2/catalog/cpus.
          examples:
            - cpu5c
          minLength: 1
        vcpuCount:
          type: integer
          minimum: 2
          description: >-
            Number of vCPUs. Must be valid for the selected CPU flavor and must
            be a power of two.
          examples:
            - 4
    PersistentMount:
      type: object
      required:
        - size
        - path
      additionalProperties: false
      description: |
        Host-local persistent storage. Pinned to the pod's host machine — data
        does not survive a host failure. Disallowed on CPU pods. Mutually
        exclusive with NetworkMount. Deprecated: prefer NetworkMount for any
        data you cannot recreate.
      properties:
        size:
          type: integer
          minimum: 10
          description: >-
            Host-local persistent storage in GB. Upstream enforces a 10 GB
            floor.
          examples:
            - 20
        path:
          type: string
          description: Mount path inside the container. May be changed via PATCH.
          examples:
            - /workspace
    NetworkMount:
      type: object
      required:
        - volumeId
        - path
      additionalProperties: false
      description: |
        Reference to a NetworkVolume. Custom paths are honored at runtime on
        both GPU and CPU pods. The underlying `volumeId` is immutable
        post-create; the mount `path` may be changed via PATCH.
      properties:
        volumeId:
          type: string
          description: ID of an existing NetworkVolume in the same data center as the pod.
          examples:
            - vol_xyz
        path:
          type: string
          description: >-
            Mount path inside the container. No default — must be specified
            explicitly.
          examples:
            - /runpod-volume
    PodSshEndpoint:
      type: object
      required:
        - host
        - port
        - username
        - command
      description: >-
        One way to reach the pod over SSH, as both its parts and a ready-to-run
        invocation.
      properties:
        host:
          type: string
          description: Hostname or IP to connect to.
          examples:
            - ssh.runpod.io
        port:
          type: integer
          description: TCP port to connect to.
          examples:
            - 22
        username:
          type: string
          description: >-
            SSH username. For the proxy this is an opaque routing token, not a
            user account on the pod.
          examples:
            - 7h9k2m4n6p-64411eb2
        command:
          type: string
          description: >-
            The equivalent `ssh` invocation, ready to run. Add `-i <path>` if
            the matching private key is not one of your default identities, and
            `-o StrictHostKeyChecking=no` to skip the host-key prompt on
            short-lived pods.
          examples:
            - ssh 7h9k2m4n6p-64411eb2@ssh.runpod.io
    PodClusterRole:
      type: string
      description: >-
        A cluster member's role. Assigned for SLURM and RAY clusters; omitted
        for TRAINING/APPLICATION members.
      enum:
        - SLURM_CONTROLLER
        - SLURM_COMPUTE
        - RAY_HEAD
        - RAY_WORKER
    PodGpuUtilization:
      type: object
      description: Per-GPU utilization metrics.
      properties:
        util:
          type: integer
          examples:
            - 94
        memoryUtil:
          type: integer
          examples:
            - 78
    Utilization:
      type: object
      description: >-
        Single-value utilization percentage (0–100). Shared by `cpu` and
        `memory`.
      properties:
        util:
          type: integer
          examples:
            - 45
    PodRuntimePort:
      type: object
      description: Live port mapping for a running pod.
      properties:
        private:
          type: integer
          examples:
            - 8888
        public:
          type:
            - integer
            - 'null'
          examples:
            - 43210
        type:
          type: string
          examples:
            - http
        ip:
          type:
            - string
            - 'null'
          examples:
            - 45.23.12.1
  headers:
    RateLimit:
      schema:
        $ref: '#/components/schemas/RateLimitHeader'
    RateLimit-Policy:
      schema:
        $ref: '#/components/schemas/RateLimitPolicyHeader'
  responses:
    BadRequestError:
      headers:
        RateLimit:
          $ref: '#/components/headers/RateLimit'
        RateLimit-Policy:
          $ref: '#/components/headers/RateLimit-Policy'
      description: >-
        The request could not be processed because it is malformed or conflicts
        with request rules.
      content:
        application/problem+json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          examples:
            badRequest:
              summary: Bad request
              value:
                title: Bad Request
                status: 400
                detail: request could not be processed
    UnauthorizedError:
      description: >-
        Authentication failed because the bearer token is missing, malformed,
        expired, or invalid.
      content:
        application/problem+json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          examples:
            missingBearerToken:
              summary: Missing bearer token
              value:
                title: Unauthorized
                status: 401
                detail: missing bearer token
    ForbiddenError:
      headers:
        RateLimit:
          $ref: '#/components/headers/RateLimit'
        RateLimit-Policy:
          $ref: '#/components/headers/RateLimit-Policy'
      description: >-
        The bearer token is valid, but it does not grant access to the requested
        resource or action.
      content:
        application/problem+json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          examples:
            insufficientAccess:
              summary: Insufficient access
              value:
                title: Forbidden
                status: 403
                detail: access denied
    NotFoundError:
      headers:
        RateLimit:
          $ref: '#/components/headers/RateLimit'
        RateLimit-Policy:
          $ref: '#/components/headers/RateLimit-Policy'
      description: The requested resource was not found or is not accessible to the caller.
      content:
        application/problem+json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          examples:
            notFound:
              summary: Resource not found
              value:
                title: Not Found
                status: 404
                detail: resource not found
    UnprocessableEntityError:
      headers:
        RateLimit:
          $ref: '#/components/headers/RateLimit'
        RateLimit-Policy:
          $ref: '#/components/headers/RateLimit-Policy'
      description: >-
        The request body or parameters were syntactically valid but failed
        validation.
      content:
        application/problem+json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          examples:
            validationFailed:
              summary: Validation failed
              value:
                title: Unprocessable Entity
                status: 422
                detail: Request validation failed.
    TooManyRequestsError:
      description: >
        The caller exceeded its per-user rate limit. The response identifies the
        window that was exceeded and how long to wait. The `RateLimit` and
        `RateLimit-Policy` headers (per the IETF ratelimit-headers draft) also
        accompany successful responses, so clients can track quota before a 429.
      headers:
        Retry-After:
          description: Seconds to wait before retrying, per the exceeded window.
          schema:
            type: integer
          example: 12
        RateLimit:
          $ref: '#/components/headers/RateLimit'
        RateLimit-Policy:
          $ref: '#/components/headers/RateLimit-Policy'
      content:
        application/problem+json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          examples:
            rateLimited:
              summary: Rate limit exceeded
              value:
                title: Too Many Requests
                status: 429
                detail: rate limit exceeded for the minute window
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: Runpod API Key
      description: >
        Runpod API key authentication. Generate an API key in the Runpod console
        and send it in the `Authorization` header as `Bearer <api_key>`. Keys
        are scoped to the permissions granted when created; requests may return
        `403` when a valid key lacks access to the requested resource or action.

````