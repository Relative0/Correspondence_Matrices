# Bounded corpus/oracle/RSS validation — proposed only

**Not authorized and not launched.** No source has been uploaded for this
phase, no pod has been created, and no existing controller will be reused.
The upload manifest remains marked `pending` until Brian approves the exact
scope below.

## Scientific question

Test the unchanged `cm-memory-structure-v1-candidate` on frozen BX1, B2, and
EPFL benchmark corpora, verify every result against an evaluator independent
of CM compilation and bitset execution, and collect whole-child RSS evidence
separately from the guarded-call `tracemalloc` peak.

The deterministic selection contains 35 cases:

- BX1: first and last eligible records at k=6,8,12,16 (8 cases).
- B2: first and last eligible records at k=6,8,12,16 (8 cases).
- EPFL: first and last eligible records at each k=8..16, plus the one eligible
  record with syntactic support larger than semantic support (19 cases).

Selection uses immutable corpus order and support metadata, never timing or
memory results. The split is frozen as 17 `calibration-corpus` cases and 18
`heldout-corpus` cases. This phase does **not** fit the candidate; the held-out
rows stay untouched for a later acceptance decision.

For each case, run dense, bigint, and words representations with three cold
process repetitions and three recorded warm calls. The exact grid is 420
isolated child jobs and 630 measured representation calls.

## Correctness and memory definitions

The parent computes truth directly from each serialized v2 DAG with a scalar
topological evaluator. It imports no CM compiler, normalizer, or bitset
evaluator. It verifies all 35 frozen truth hashes, including the EPFL dead-axis
case, then gives each child only the expected output hash.

Each measured call records `tracemalloc` for the evaluator window. The parent
also polls `/proc/<pid>/status` every 5 ms for `VmRSS` and `VmHWM` across the
whole isolated child lifetime. That RSS value includes interpreter imports,
compilation, evaluation, output hashing, and allocator lifetime. It is not a
per-call RSS peak, a process-tree measurement, or proof that a cgroup memory
limit was enforced. These definitions remain separate in the output.

BX1/B2/EPFL are accepted frozen benchmark corpora, not genuine application
traffic. This study cannot close the separately documented real-workload gap.

## Frozen command and package

After the existing 13 hash-locked binary wheels are installed and `pip check`
passes, run 79 focused tests and exactly:

```sh
python scripts/cm_corpus_memory_validation.py \
  --execution runpod \
  --selection-manifest study/CORPUS-MEMORY-SELECTION.json \
  --output-dir /workspace/cm-memory-smoke/run-output/corpus-memory
```

The 71-file upload is exactly 1,680,864 uncompressed source bytes. It is the
previous hash-verified 65-file package plus the new corpus driver, its tests,
the three named frozen corpus JSONL files, and the frozen selection manifest.
It excludes `.env*`, credentials, all other deliverables, genuine workload
traces, unrelated tests, and concurrent work.

- Upload manifest: `RUNPOD-CORPUS-UPLOAD-MANIFEST-V2.json`
- Upload-manifest SHA-256:
  `9149a41912e8b909fb8ae8871a9b72356a5f35a5cb3938a8034e2cbe51aa1e11`
- Selection manifest: `CORPUS-MEMORY-SELECTION-V2.json`
- Selection SHA-256:
  `e5d474983049074847552a55ec5bffc5fb00a66d1b1c04765e5a88ace71d66cd`
- Compressed source bundle: 313,841 bytes, SHA-256
  `cb1aa9ce90daa2a38258a985c03740cf2718a51c0df3afdcf65aa5a18879525f`
- Frozen remote program SHA-256:
  `cfbe183128253ee06c8fbb274d3a6d422343a210e652d487ef4359de3859b528`
- Complete authenticated transport payload: 448,148 bytes under the 1 MiB
  cap. Its hash is recomputed immediately before any authorized create.

## Resource, cost, and teardown bounds

Use one new Secure CPU pod with the same pinned Python 3.13.15 image digest,
`cpu3c`, exactly 2 vCPU, at least 4 GB RAM, at most $0.25/hour, 12 GB container
storage, zero pod volume, no network volume, and only the two authenticated
HTTP bootstrap ports. No GPU, SSH, Jupyter, source build, download, extra
dependency, publication, support message, or automatic replacement.

Cap this phase at $0.10 and the attributable HTTP campaign at $0.20, including
storage and all three earlier HTTP pods. Reserve at least $0.03 for delayed
prior billing, increasing the reserve if the live attributable bill is higher.
At the expected $0.06/hour CPU quote, the conservative 20-minute compute plus
storage bound is $0.02334 before the prior reserve.

Keep the hard lifetime at 20 minutes from the sole create request, independent
owned-pod cleanup at 18 minutes, the study at 10 minutes, and evidence under
16 MiB. Require a zero-pod baseline, validate returned identity/resources and
price before upload, retrieve evidence, delete only the pod ID/name created by
this controller, and reconcile v1/v2 inventory and attributable billing. Any
failure ends the attempt; no replacement is authorized.

No production estimator, coefficient, budget default, backend selection,
workload tracing, dependency, publication, commit, or push is part of this
proposal.

## Exact approval text

> I authorize one Runpod corpus/oracle/RSS validation pod exactly as specified
> in `RUNPOD-CORPUS-MEMORY-VALIDATION-PROPOSAL-20260829.md`: upload the exact
> 71-file manifest, install the existing 13 locked binary wheels, run the 79
> focused tests and frozen 35-case/420-job/630-call command, using one Secure
> 2-vCPU CPU pod with 12 GB container storage and zero pod/network volume, a
> 20-minute lifetime, $0.10 phase and $0.20 attributable-campaign caps, owned
> cleanup and no replacement.
