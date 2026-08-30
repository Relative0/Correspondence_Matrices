> ## Documentation Index
> Fetch the complete documentation index at: https://docs.runpod.io/llms.txt
> Use this file to discover all available pages before exploring further.

# Get a pod

> Returns a single pod by ID.



## OpenAPI

````yaml get /v2/pods/{id}
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
  /v2/pods/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
        description: Pod identifier
        example: pod_abc123
    get:
      tags:
        - Pods
      summary: Get a pod
      description: Returns a single pod by ID.
      operationId: getPod
      responses:
        '200':
          headers:
            RateLimit:
              $ref: '#/components/headers/RateLimit'
            RateLimit-Policy:
              $ref: '#/components/headers/RateLimit-Policy'
          description: OK
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
                    status: RUNNING
                    actions:
                      - stop
                      - restart
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
                      direct:
                        host: 195.26.233.3
                        port: 34446
                        username: root
                        command: ssh root@195.26.233.3 -p 34446
                    template: 9x4m2p7v
                    cost: 0.44
                    locked: false
                    globalNetworking:
                      enabled: false
                    runtime:
                      uptime: 3600
                      ports:
                        - private: 22
                          public: 34446
                          type: tcp
                          ip: 195.26.233.3
                    createdAt: '2026-06-01T12:00:00Z'
                    startedAt: '2026-06-01T12:02:00Z'
        '401':
          $ref: '#/components/responses/UnauthorizedError'
        '403':
          $ref: '#/components/responses/ForbiddenError'
        '404':
          $ref: '#/components/responses/NotFoundError'
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
components:
  headers:
    RateLimit:
      schema:
        $ref: '#/components/schemas/RateLimitHeader'
    RateLimit-Policy:
      schema:
        $ref: '#/components/schemas/RateLimitPolicyHeader'
  schemas:
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
    Cloud:
      type: string
      description: |
        Cloud tier.
        - `SECURE`    — Runpod-owned datacenter hardware
        - `COMMUNITY` — community-hosted hardware
      enum:
        - SECURE
        - COMMUNITY
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
  responses:
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