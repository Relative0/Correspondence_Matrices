# C38 Linux/GCC native replication

**Date:** 2026-09-03  
**Scope:** unchanged C37 exact native payload on a second physical machine/compiler  
**Decision:** exact portability verified; aggregate benefit replicated; per-case performance gate not confirmed

## Outcome

C38 rebuilt the sealed C11 fused-slot executor with GCC 12 on a Secure Linux CPU Pod
and replayed the unchanged C37 schedule. Both independent verifiers passed after 954 raw
sessions, 44,928 single-root query checks, and 48,384 multi-root output-query checks.
The retrieved verification records were then regenerated locally from the frozen 44-file
package and were byte-identical to the on-Pod records.

The Linux result preserves an unfavorable observation. Native remained faster in the
aggregate, but the width-11 `addertree_sum` case
`c37-addertree_sum-c4f402c3a3a5c06d` measured `0.839984325x` versus Python R2. That is
below the predeclared `0.95x` individual-case floor, so the complete performance gate
failed and is not refit.

| Measure | Windows/MSVC | Linux/GCC | Cross-machine observed floor | Frozen requirement |
|---|---:|---:|---:|---:|
| Single-root aggregate speedup | 1.472005x | 1.366221x | 1.366221x | >=1.10x |
| Single-root minimum case | 0.988910x | 0.839984x | 0.839984x | >=0.95x |
| Single-root minimum width | 1.163807x | 1.028052x | 1.028052x | >=1.00x |
| Multi-root aggregate speedup | 1.285134x | 1.259519x | 1.259519x | >=1.10x |
| Multi-root minimum workload | 1.278433x | 1.223912x | 1.223912x | >=1.00x |

Exact behavior and aggregate benefit therefore transferred across both observed machines,
operating systems, and compiler families. Unqualified per-case performance did not.

## Guarded integration decision

The existing native restriction boundary remains development-only, disabled by default,
and opt-in only with an explicit library path and SHA-256. Exact Python R2 fallback remains
mandatory for disabled configuration, identity/ABI/load refusal, compilation refusal, and
runtime error. C38 supports retaining that guarded backend; it does not support making it
the production default or claiming that it wins every case on every supported machine.

No selector is justified by this result. The current task-identical C36 portfolio still
has a fixed native winner on all 18 exposed development cases and exactly `1.0000x`
per-case-oracle headroom. The Linux outlier is portability evidence for a fixed backend,
not a new source-closed selector-training table.

## Transport and resource boundary

The first authorized controller invocation stopped locally before a create request because
its `cm-c38-linux-*` ownership name did not match the inherited watchdog's historical
namespace. It uploaded nothing, created no Pod, incurred no compute charge, and reconciled
both inventories empty. The versioned transport-only retry used the already exercised
`cm-c7-linux-*` ownership namespace without changing the 44-file scientific payload.

The retry created exactly one Pod, made no replacement, accepted the payload on its second
bounded upload attempt after one transient proxy 404, retrieved 2,429,780 bytes, and deleted
the Pod. Both inventories were empty at cleanup. Estimated compute cost was
`$0.001562563`, below the `$0.05` controller cap.

Environment:

- Secure CPU Pod, 2 vCPU and 4 GB RAM;
- AMD EPYC 7713;
- pinned amd64 `python:3.13.15-bookworm` image;
- Python 3.13.15;
- GCC 12.2.0 at `/usr/bin/x86_64-linux-gnu-gcc-12`;
- native shared-library SHA-256
  `163095565ef8e9cd89c496dbc31e80662fbc2c660b2a3957fcb44ddd3efd5278`.

Evidence identities:

- Linux results SHA-256:
  `c47fcf976149d43442fa9f8859b23516ed2cf0b4c1b5b595d58bc71491d17cd5`;
- C37 verifier SHA-256:
  `0ad102f1b88f6cf17e5ecf13ef9a0a02b34dc2ccc8c9fe04762f714a971b7f4f`;
- C38 verifier SHA-256:
  `41967d6d4bfbbb593c3ab9c634a44857b6b509cb352f0408efc9b5d396c05d2b`;
- final retrieval verification SHA-256:
  `b55e58e9b754290ebe0b83817ee250cf159c922a8f22fe825b2a5165ffddef79`;
- cross-machine adjudication SHA-256:
  `c577c73cff20dc9bbeefd297e1cf0c0913c50ff974f8f0af32e603dcb56198fc`.

## Next controlled work

The next local step is the architecture-aware comparison harness described after C37:
complete-relation, repeated-restriction query-count ladder, related multi-root, and
smaller-query lanes, all with identical artifact contracts and complete-task cache
isolation. Development/regression cohorts can be used to validate that harness. A fresh
comparison corpus, timing campaign, public-site update, or production-default change
requires a separate freeze and authorization.

No neural training, policy refit, gate refit, website write, production promotion,
commit, or push occurred.
