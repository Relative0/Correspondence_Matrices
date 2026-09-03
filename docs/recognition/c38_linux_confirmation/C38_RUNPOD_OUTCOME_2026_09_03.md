# C38 RunPod Linux/GCC outcome

Date: 2026-09-03  
Scope: unchanged C37 non-neural native fused-slot and multi-root schedule  
Decision: exact replication complete; cross-machine performance only partly confirmed

## Execution and cleanup

Exactly one Secure CPU Pod was created: 2 vCPU, 4 GB RAM, 12 GB ephemeral container
disk, no Pod or network volume, and one `8080/http` port. The pinned Python 3.13.15
Bookworm image resolved to GCC 12.2.0. The quoted rate was $0.06/hour, the Pod lifetime
was 93.754 seconds, and estimated compute cost was $0.001563 against the authorized
$0.05 ceiling. No replacement was attempted.

The controller deleted the Pod with HTTP 204. Its v1/v2 inventories were empty, the
independent watchdog acknowledged cleanup, and a separate post-run inventory query was
also empty.

## Exactness and provenance

The retrieved evidence contains 33 files (2,429,780 compressed bytes). Both independent
verifiers passed. The post-retrieval local replay reproduced the stored verifier
objects and reported zero mismatches in every checked category.

| Check | Result |
|---|---:|
| Raw sessions | 954 |
| Single-root exact query checks | 44,928 |
| Multi-root exact output-query checks | 48,384 |
| Canonical delivery mismatches | 0 |
| C37 verifier mismatch categories | all 0 |
| C38 binding/compiler mismatch categories | all 0 |
| Native library SHA-256 | `163095565ef8e9cd89c496dbc31e80662fbc2c660b2a3957fcb44ddd3efd5278` |
| Results SHA-256 | `c47fcf976149d43442fa9f8859b23516ed2cf0b4c1b5b595d58bc71491d17cd5` |

## Performance outcome

| Lane | Windows/MSVC | Linux/GCC | Linux frozen gate |
|---|---:|---:|---|
| Single-root native fused vs Python R2 | 1.472x | 1.366x | Failed overall |
| Slowest single-root case | passed 0.95x floor | 0.840x | Failed |
| Slowest width aggregate | passed 1.00x floor | 1.028x | Passed |
| Single-root p95 session speedup | passed 0.95x floor | 1.714x | Passed |
| Multi-root union vs separate roots | 1.285x | 1.260x | Passed |
| Slowest multi-root workload | passed 1.00x floor | 1.224x | Passed |

The Linux single-root aggregate, width, tail, memory, and correctness gates passed, but
one of 18 individual cases regressed enough to fail the frozen minimum-case gate. All
six multi-root workloads improved and all multi-root gates passed.

The failing case is the 11-variable low-bit `addertree_sum`, structurally a short XOR
chain. Across its 12 frozen blocks, median native evaluation was 3.341 ms versus
0.886 ms for Python R2. Native restriction setup was lower (1.166 ms versus 2.776 ms),
but not by enough to recover the evaluation overhead. That makes small, cheap parity-like
graphs the first concrete exclusion cohort for any later native dispatch guard; it is
not evidence against the larger-width or multi-root gains.

## Consequence

C38 supports three scoped claims: the native C11 implementation is exact on both tested
OS/compiler families; aggregate repeated-restriction performance improved on both; and
the related-output multi-root optimization improved every frozen workload on both.
It does not support claiming that native fused single-root execution is uniformly
faster. No thresholds were refit, and no production, training, website, commit, or push
operation occurred.

The next comparison campaign should keep the Windows 1.472x and Linux 1.366x results
separately labeled, expose the 0.840x case, and compare all current CM-family, BitSet,
CSE-flat, and applicable symbolic arms under matched output contracts. Native
single-root selection remains guarded/opt-in; native multi-root is the stronger
portable candidate for the next frozen comparison.
