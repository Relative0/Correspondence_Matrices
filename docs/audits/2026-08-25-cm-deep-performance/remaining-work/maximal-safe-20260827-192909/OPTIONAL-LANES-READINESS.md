# Optional-lane readiness

Research/access date: 2026-08-27. Public primary-source metadata only; no distributions, corpora or source archives downloaded. Exact wheel metadata, upload dates and hashes are retained in PRIMARY-PACKAGE-METADATA.json.

## Current facts

| Component | Verified current fact | Local state / readiness |
|---|---|---|
| Python | Stable 3.14.7 and maintenance 3.13.15 released August 5, 2026. [Official releases](https://www.python.org/downloads/) | Preserve venv 3.13.5 and test Python 3.10.11. Proposed disposable image uses 3.13.15; do not pool its timings with local runs. |
| NumPy | 2.5.2, August 9, 2026; Python >=3.12; CPython 3.13 Linux x86_64 and Windows wheels listed. [PyPI](https://pypi.org/project/numpy/2.5.2/) | Retain audited NumPy 2.3.2 for the proposed smoke; latest is not automatically an upgrade recommendation. |
| Numba | 0.67.0, August 11, 2026; Python >=3.10,<3.15, NumPy 2.x <2.6, llvmlite 0.49.x, LLVM 22.x. [Support table](https://numba.readthedocs.io/en/stable/user/installing.html) | Missing from venv; system has 0.64.0. No JIT executed. Current CPython 3.13 Linux/Windows wheel metadata verified. |
| llvmlite | 0.49.0, August 11, 2026; CPython 3.13 Linux x86_64/Windows wheels. [PyPI](https://pypi.org/project/llvmlite/0.49.0/) | Missing from venv; system 0.46.0. No LLVM/native experiment performed. |
| dd | 0.6.0; CPython 3.13 manylinux x86_64 wheel uploaded December 1, 2024; dependencies include astutils>=0.0.5 and ply>=3.4,<=3.10. [PyPI](https://pypi.org/project/dd/0.6.0/) | Installed venv metadata 0.6.0 is not evidence of native CUDD availability. No new backend import/performance claim. |
| PLY | 3.10 lists only source archive, January 31, 2017. [Exact release metadata](https://pypi.org/pypi/ply/3.10/json) | Still blocks a clean all-binary dd 0.6.0 resolution. PLY 3.11 does not satisfy dd's upper bound. |
| astutils | 0.0.6 lists source archive, April 15, 2024. [Exact metadata](https://pypi.org/pypi/astutils/0.0.6/json) | Prior Run 3 source build did not authorize a PLY build. |

PLY 3.10 SHA-256: 96e94af7dd7031d8d6dd6e2a8e0de593b511c211a86e28a9c9621c275ac8bacb.
Astutils 0.0.6 SHA-256: e9a6f31b243ecfc3c7c84dd2f145cf5de83e475b650d2a6b781cfa713ad15427.

The prior three RP-D0 authorizations remain consumed. Their negative result was standard installation under a restricted build contract, not Numba/CUDD correctness or performance. A no-deps exception leaves metadata unsatisfied and is not a clean installation. Neither that exception nor any source build is bundled into this safety smoke.

## Artifact and hardware gates

CUDD supports BDD managers, restriction/substitution and symbolic queries; these are not complete truth-vector extraction. Charge manager construction, ordering, restriction, query and exhaustive extraction separately for the same requested artifact. Upstream release notes describe the CUDD 3.0.0 source line; no new native binary identity was established here. [dd documentation](https://github.com/tulip-control/dd/blob/main/doc.md), [CUDD release notes](https://github.com/cuddorg/cudd/blob/main/RELEASE.NOTES).

NumPy dispatches CPU-specific kernels at runtime. That does not establish a CM speedup. Record actual CPU features, selected dispatch, scalar fallback, imports, JIT, plan conversion, copying and cold/warm costs. A Numba prototype must operate on uint64 arrays, not fixed-width approximations to arbitrary Python bigints. [NumPy SIMD documentation](https://numpy.org/doc/stable/reference/simd/index.html).

VTR's overall MIT license explicitly excludes some components, and benchmark circuits carry individual terms in their sources. A new selector corpus needs a pinned commit, per-design license/provenance review, hashes, extraction/synthesis recipe and whole-family split before outcomes. Do not infer every benchmark is MIT. i10 remains consumed held-out evidence and cannot tune a replacement. [Official VTR license](https://github.com/verilog-to-routing/vtr-verilog-to-routing/blob/master/LICENSE.md).

Runpod stopping can retain billed volume storage; termination deletes ephemeral data, so collect evidence first. Require an external deadline/watchdog, termination in finally, and postflight inventory. Preserve unrelated resources; never terminate another campaign's pods to manufacture an account-zero result. [Lifecycle documentation](https://docs.runpod.io/pods/manage-pods).

## Verdicts

| Lane | Verdict / entry condition |
|---|---|
| New selector corpus | NO-GO: no real k=13..15 traffic/opportunity gate or approved acquisition |
| Numba packed kernel | NO-GO: no observed repetition count beyond import/JIT/copy break-even |
| Native SIMD | NO-GO: no accepted Numba task-total win or remaining measured kernel bottleneck |
| CUDD context/query | NO-GO: no named symbolic/natural-context workload; source dependency gate remains |
| Cache/family/context prototype | NO-GO: no owner-approved ordered application evidence |
| Runpod safety validation | PREPARED, authorization pending: follows Brian's compute-location requirement; not a production remote-execution optimization |

Only the last row has an authorization package now. No broad pod matrix is proposed.
