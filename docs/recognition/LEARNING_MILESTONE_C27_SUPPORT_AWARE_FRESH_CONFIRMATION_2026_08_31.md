# Learning milestone C27: support-aware fresh confirmation

Date: 2026-08-31  
Status: **locally complete and independently verified; frozen confirmation gate passed**

## Question

C26 isolated a fixed packed-context cost at small supports. C27 asks whether a
transparent rule fixed before new evidence can remove that loss without training a
router or weakening exact CM/GF(2) completion:

- `n <= 4`: build a truth-only verified context and run screened exact CM;
- `n >= 5`: build the source-packed verified context and run screened exact CM; and
- advice off or selected-path refusal: run exhaustive exact CM.

The rule, its `n=4` boundary, both arms, and the promotion thresholds were sealed from
C26 development evidence before the C27 corpus was constructed or timed. No model was
trained and the rule was not refit after observing C27.

## Fresh corpus

C27 uses the pinned Yosys-bench commit
`52ff6fa991f2ab509618d8aaad02f307aac78848`. It draws restricted semantics from four
generator groups unused by the earlier C7, C16, C18, C19, and C23 evidence:

- DSP multiply/accumulate;
- enabled multiply/accumulate;
- priority decoding; and
- transparent, synchronous, and dual-port RAM behavior.

The builder generated restricted Boolean functions at `n=3..6`, evaluated every
expression against a separately implemented scalar oracle, required full semantic
support, rejected all prior truth identities, and then selected 12 cases per width by a
stable family round robin. The frozen set has **48 cases across six semantic families**.

Corpus filtering recorded **zero scalar-oracle mismatches**, rejected 137 prior-truth
overlaps, 796 within-pool duplicate truths, and 3,210 restrictions that lost full
support or failed admission. The independent corpus verifier rebuilt the 811-case
post-exclusion pool, all ten pinned source blobs, and the exact selected dataset with
zero mismatches.

## Implementation

`SupportAwareGF2Session` validates both the frozen C27 support policy and unchanged C22
packed-source policy once at setup. Each query:

1. selects the arm only from support width and the advice switch;
2. parses and evaluates the expression exactly once into a hash-bound verified context;
3. caches one immutable execution plan per width;
4. performs exact screened or exhaustive CM/GF(2) completion; and
5. reconstructs the final artifact before delivery.

Tiny-support queries contain no packed polynomial. Large-support queries independently
check that the packed polynomial reconstructs the same verified truth. A forced refusal
of either selected path uses the exact exhaustive fallback.

## Experiment

The experiment kept the C25/C26 schedule: **1, 2, 4, 8, 16, and 32 queries per
session**, four widths, six methods, and five balanced randomized rounds. The four
direct methods use the unchanged C25 adapter:

1. resident direct exhaustive CM;
2. resident direct screened CM;
3. resident direct compiled-screened CM;
4. resident direct source-packed ANF;
5. C27 support-aware advice on; and
6. C27 support-aware advice off.

The run contains **720 measured batches, 7,560 timed exact queries, and 24 bounded
memory batches**.

## Exactness and controls

All 48 cases passed forced selected-path fallback to exhaustive CM. Another 48 controls
proved the frozen arm identity: 24 tiny truth-screened cases and 24 large packed-screened
cases. Ten fail-closed controls covered truth mismatch, unsupported width, closed
session, query limit, tampered C22 policy, tampered C27 policy, and four context changes
to expression digest, truth, width, or context digest.

The independent verifier replayed all 48 exhaustive oracles and fallbacks, checked 48
contracts, all 720 batches and 7,560 query records, semantically rebuilt all **2,520
support-aware contexts**, checked 2,520 plan-cache records, validated 24 memory batches,
recomputed the complete summary, and found zero semantic or artifact mismatches.

## Results

The frozen confirmation contract requires support-aware advice on to reach at least
1.00x direct screened in aggregate and at least 0.90x at every width for one declared
query count.

| Queries/session | Support-aware vs direct screened | Minimum width vs screened | Best fixed method |
|---:|---:|---:|---|
| 1 | 0.7940x | 0.5901x | direct screened |
| 2 | 0.9415x | 0.6957x | direct source packed |
| 4 | 0.9407x | 0.8391x | direct compiled screened |
| 8 | **1.0240x** | **0.9798x** | **C27 support-aware** |
| 16 | **1.0046x** | **0.9216x** | direct source packed |
| 32 | 0.9700x | 0.9163x | direct compiled screened |

The first qualifying session size is **8 queries**. Sixteen queries also satisfy both
thresholds. At 32 queries the width floor remains above 0.90x but aggregate timing falls
to 0.9700x, so the result is not monotonic and does not establish universal
profitability.

## Width-level result

| Queries | n=3 | n=4 | n=5 | n=6 |
|---:|---:|---:|---:|---:|
| 1 | 0.5901x | 0.6405x | 0.7766x | 0.8331x |
| 2 | 0.6957x | 0.9726x | 0.7835x | 1.0149x |
| 4 | 0.8391x | 0.9306x | 0.9500x | 0.9447x |
| 8 | 1.0024x | 0.9798x | 1.0728x | 1.0155x |
| 16 | 0.9923x | 0.9216x | 1.0234x | 1.0102x |
| 32 | 1.0202x | 0.9163x | 1.0200x | 0.9592x |

The frozen support rule removes C26's most severe tiny-support packed-context penalty at
the profitable repeated-query points. It does not make every session length faster,
and the direct fixed winner still changes across query counts.

## Package validation and decision

The primary local fresh-confirmation gate passes, so an **unchanged second-machine
replication** is scientifically informative. A 63-file, 1,078,671-byte Linux package is
now frozen and has passed isolated local validation with no `PYTHONPATH` injection. The
isolated run reproduced all exact outputs, counts, controls, and independent
verification within a 3.91 MiB result bundle.

The isolated timing rerun did **not** preserve the profitability gate. The package
protocol defines timing-gate failure as valid evidence rather than a package failure;
the validator therefore records the false gate while requiring all scientific
invariants. This same-machine disagreement shows that the 1.0240x primary win is narrow
and timing-sensitive. Second-machine execution would adjudicate portability, but it
cannot turn the current evidence into a robust production claim by itself.

Production promotion remains false. At package freeze, no upload or paid RunPod action
had occurred and the manifest recorded that exact upload authorization was pending.

## RunPod transport outcome

The exact 63-file upload was subsequently authorized for one create with no replacement.
Three controller invocations and two bounded read-only waits first ended before create
because no eligible Secure CPU offer was available. Those **39 zero-write availability
checks** were independently sealed with the authorization still unused. A fourth
controller then found an approved `cpu3c` offer on preflight sample 16 and made the one
authorized create request.

RunPod returned HTTP 201 for pod `z1wpaiw3u278mx`. The resource check verified Secure
Cloud, 2 vCPU, 4 GiB RAM, a 12 GiB container disk, zero pod volume, the pinned Python
3.13.15 image, and a $0.06/hour rate. The bootstrap passed two consecutive health checks,
but the HTTPS proxy returned HTTP 404 before payload acceptance. The controller deleted
the owned pod 33.07 seconds after create; an independent inventory reconciliation found
the owned pod absent and the unrelated video-production pod unchanged.

The reconciled outcome is:

- C27 create requests: **1** (authorization consumed);
- compliant C27 pods created: **1**;
- source files uploaded: **0**;
- automatic replacements: **0**;
- estimated C27 compute cost: **$0.000551**;
- owned pod cleanup: **verified**; and
- unrelated video pod: **not modified**.

The early abort exposed a controller defect: a payload-POST 404 entered the authorized
six-attempt same-pod retry loop, but a 404 from the immediate health recheck escaped that
loop. The health recheck now treats transient proxy 404 and request failures as retryable
on the same pod; a simulated 404-then-success transport test passes.

## RunPod retry-002 outcome

The unchanged frozen package was authorized for exactly one additional create with no
replacement. After five capacity-only preflight samples, sample six selected approved
Secure `cpu3c` capacity at $0.06/hour. The single create request returned HTTP 500 with
no pod identifier. The response was therefore treated as uncertain and the authorization
as consumed. The ownership-scoped watchdog continued for the full twelve-minute horizon.
Across **35 inventory checks**, including an explicit post-horizon check, the uniquely
named retry pod never appeared. Final v1 and v2 inventories contained only the sealed
unrelated video-production pod.

Retry-002 is independently reconciled as:

- create requests: **1**;
- create HTTP status: **500**;
- retry pods ever observed: **0**;
- source files uploaded: **0**;
- automatic replacements: **0**;
- estimated retry compute cost: **$0.00** (billing may lag);
- post-horizon owned-pod absence: **verified**; and
- unrelated video pod: **not modified**.

Across both C27 create authorizations, one compliant pod was created and cleaned, the
second create returned HTTP 500 without an observed pod, and zero source files were
uploaded. No Linux scientific or timing result was produced. Retry-002 permits no further
create, so another RunPod attempt would require a new exact authorization.

## Same-host Linux Docker portability

To separate RunPod transport failures from Linux runtime compatibility, the unchanged
63-file package was executed in the exact pinned Python 3.13.15 `linux/amd64` image on
the local Docker Desktop Linux engine. NumPy 2.3.2 was installed from the single wheel
hash frozen in the manifest. Both scientific commands ran with networking disabled, a
read-only container root, read-only frozen sources, a 2-vCPU limit, and a 4 GiB memory
limit. Only the bounded result directory was writable.

The independent verification passed with zero mismatches across 720 measurement batches,
7,560 timed queries, and 24 memory batches. All fallback, selected-path, refusal, and
artifact controls remained exact. The result contained 13 files totaling 3,913,442 bytes,
below the 16 MiB cap.

| Queries | aggregate speedup over screened direct | minimum-width speedup |
|---:|---:|---:|
| 1 | 0.9525x | 0.6803x |
| 2 | 0.9433x | 0.7647x |
| 4 | 1.0622x | 0.8933x |
| 8 | **1.0575x** | **0.9498x** |
| 16 | 0.9854x | 0.9636x |
| 32 | **1.0349x** | **1.0185x** |

Two additional unchanged Docker Linux repetitions were then run under the same resource,
network, and filesystem restrictions. All three independent verifiers passed, covering
2,160 measurement batches and 22,680 timed exact queries with zero mismatches. The timing
gate passed **3/3**, and every repetition selected the same eight-query break-even point.
At eight queries, aggregate speedup ranged from **1.0404x to 1.0575x** (median 1.0407x),
while minimum-width speedup ranged from **0.9498x to 0.9974x** (median 0.9573x).

The repeatability result strengthens OS/container portability and confirms that the frozen
code runs exactly on Linux. It does not supply independent-machine evidence because all
Docker repetitions used the same physical computer. The isolated Windows package timing
failure and variability away from eight queries keep the broader profitability claim
timing-sensitive. Production promotion remains false.

## Independent-machine Docker package

A transport-neutral package is now frozen for a physically distinct Docker host. It
contains the 63 unchanged scientific sources plus the exact Dockerfile, POSIX launcher,
hash inventory, bounded result verifier, package manifest, and protocol: **70 files** in
a **211,551-byte** archive. It contains no credentials or production data.

The exact archive was extracted into a new directory and executed through its own
`run_c27.sh same-host` path. The package rechecked all frozen hashes, used the pinned
runtime cache, disabled networking during both scientific commands, independently
verified zero mismatches, and produced a 474,636-byte result archive. The local package
validation timing gate passed at eight queries, but its declared scope is correctly
`same-host`; the same archive must be run as `independent-machine` on distinct hardware
to become second-machine evidence.

A subsequent read-only RunPod check found `cpu3c`, `cpu3m`, and `cpu5c` at HIGH
availability with the account and sealed unrelated-pod baseline ready. Retry-003 was
then authorized for exactly one `cpu5c` create at no more than $0.07/hour, providing
hardware diversification from the prior `cpu3c` attempts.

## RunPod retry-003 second-machine confirmation

The controller selected only the authorized Secure `cpu5c` flavor and RunPod returned
HTTP 201 for pod `gukzs8ixi5gpdi`. The assigned pod had 2 vCPU, 4 GiB RAM, a 12 GiB
container disk, zero pod or network volume, the pinned Python 3.13.15 image, and a
$0.07/hour rate. The frozen 63-file payload was accepted on the first same-pod attempt.
Both scientific commands completed with return code zero.

The Linux host was an AMD EPYC 4564P. Its independent verifier checked all 720 timing
batches, 7,560 timed queries, 24 memory batches, 48 fallback controls, 48 selected-path
controls, ten refusal controls, 2,520 hash-bound semantic contexts, and 2,520 cache
records. Every exact and artifact check passed. A separate post-retrieval replay of the
frozen verifier produced byte-identical verification evidence.

| Queries | aggregate speedup over screened direct | minimum-width speedup |
|---:|---:|---:|
| 1 | 0.9616x | 0.6113x |
| 2 | 0.9883x | 0.7746x |
| 4 | 1.0178x | 0.8858x |
| 8 | **1.0352x** | **0.9608x** |
| 16 | **1.0290x** | **0.9609x** |
| 32 | **1.0363x** | **0.9893x** |

The frozen timing gate passes first at **8 queries**, matching all three same-host Docker
repetitions. It also passes at 16 and 32 queries on this second machine. This completes
the unchanged physical second-machine scientific confirmation, with zero semantic or
artifact mismatches.

The controller initially labeled the retrieved run failed because its metadata gate
expected vendored `dd 0.6.0` in `DEPENDENCIES.json`, which intentionally inventories
installed distributions only. The workload recorded and imported vendored `dd 0.6.0`,
the manifest binds its files and distribution metadata, and both independent verifiers
passed. The final adjudicator therefore records a controller metadata false negative
while preserving the original `RUN.json`. The controller gate is corrected for future
packages.

The pod was deleted and its absence verified 79.86 seconds after create. Estimated cost
was **$0.001553**, the 16 MiB retrieval bound was respected, and no replacement was
created. Across all three C27 create authorizations, three create requests produced two
pods, 63 source files were uploaded once, total estimated compute cost was approximately
**$0.002104**, and every owned pod is reconciled absent. Production promotion remains
false because the profitability margins are narrow and timing remains machine-specific.

## C28 follow-up

The no-refit C28 adjudicator now combines the primary Windows run, three same-host Docker
repetitions, and this RunPod execution while preserving their two-physical-machine scope.
Only q8 passes the point gate on every execution. Its cross-execution point floor is
1.0240x aggregate / 0.9498x minimum width, but the conservative paired-round lower floor
is 0.9279x / 0.5972x. No query count passes the uncertainty gate, so C28 refuses a general
shadow rule and retains exact fallback.

## Evidence

- Policy: `docs/recognition/c27_support_aware_policy.json`
- Corpus: `docs/recognition/c27_yosys_fresh_gf2_dataset.json`
- Corpus verification: `docs/recognition/c27_yosys_fresh_gf2_dataset_verification.json`
- Run: `docs/recognition/runs/c27-support-aware-fresh-windows-20260831-001`
- Run verification: `docs/recognition/runs/c27-support-aware-fresh-windows-20260831-001/independent_verification.json`
- Linux manifest: `docs/recognition/c27_linux_confirmation/c27_linux_upload_manifest.json`
- Linux protocol: `docs/recognition/c27_linux_confirmation/C27_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md`
- Isolated package validation: `docs/recognition/c27_linux_confirmation/C27_PACKAGE_LOCAL_VALIDATION_20260831.json`
- RunPod zero-create availability verification: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_AVAILABILITY_BLOCKED_VERIFICATION_V2_20260901.json`
- RunPod proxy-404 reconciliation: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_PROXY_404_RECONCILIATION_20260901.json`
- RunPod controller evidence: `docs/recognition/c27_linux_confirmation/runpod-c27-linux-execute-001d`
- Retry-002 authorization request: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_RETRY_002_AUTHORIZATION_REQUEST_20260901.json`
- Retry-002 authorization: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json`
- Retry-002 reconciliation: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_RETRY_002_HTTP500_RECONCILIATION_20260901.json`
- Retry-002 controller evidence: `docs/recognition/c27_linux_confirmation/runpod-c27-linux-execute-001e`
- Docker Linux execution: `docs/recognition/c27_linux_confirmation/c27-docker-linux-portability-001/EXECUTION.json`
- Docker Linux verification: `docs/recognition/c27_linux_confirmation/C27_DOCKER_LINUX_PORTABILITY_VERIFICATION_20260901.json`
- Docker Linux repeatability: `docs/recognition/c27_linux_confirmation/C27_DOCKER_LINUX_REPEATABILITY_20260901.json`
- Docker Linux repeatability verification: `docs/recognition/c27_linux_confirmation/C27_DOCKER_LINUX_REPEATABILITY_VERIFICATION_20260901.json`
- Independent Docker protocol: `docs/recognition/c27_independent_docker_confirmation/C27_INDEPENDENT_DOCKER_SECOND_MACHINE_PROTOCOL_2026_09_01.md`
- Independent Docker archive manifest: `docs/recognition/c27_independent_docker_confirmation/c27_independent_docker_package_manifest.json`
- Independent Docker local validation: `docs/recognition/c27_independent_docker_confirmation/C27_INDEPENDENT_DOCKER_PACKAGE_LOCAL_VALIDATION_20260901.json`
- Retry-003 readiness: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_RETRY_003_READINESS_20260901.json`
- Retry-003 authorization request: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_RETRY_003_AUTHORIZATION_REQUEST_20260901.json`
- Retry-003 authorization: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_RETRY_003_EXACT_PAYLOAD_AUTHORIZED_2026_09_01.json`
- Retry-003 controller evidence: `docs/recognition/c27_linux_confirmation/runpod-c27-linux-execute-001f`
- Retry-003 final verification: `docs/recognition/c27_linux_confirmation/RUNPOD_C27_RETRY_003_FINAL_VERIFICATION_20260901.json`
- Retry-003 verification script: `docs/recognition/c27_linux_confirmation/verify_runpod_c27_retry_003.py`
- C28 adjudication: `docs/recognition/runs/c28-cross-machine-profitability-adjudication-20260901-001`
- Proxy retry test: `tests/test_c27_runpod_transport.py`
- Session: `cmbench/recognition/gf2_support_aware_session.py`
- Experiment: `cmbench/comparative/gf2_support_aware_experiment.py`
