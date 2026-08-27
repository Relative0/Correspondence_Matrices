# EPFL real-cone/generated-context pilot results

**Date:** 2026-08-27

**Protocols:** V1 void during fail-closed preflight; V2 completed twice.
**Verdict:** exact, reproducible neutral evidence; the preregistered CM advantage gate did not pass.

## Outcome

Both completed V2 runs used all 129 admitted expressions from 19 EPFL circuits and evaluated 13 contexts per expression: 1,677 artifact-equivalent rows per run. Each run produced:

- 1,677/1,677 exact CM/CSE-flat packed matches;
- 129/129 all-free outputs matching the frozen corpus truth digest;
- zero exclusions, timeouts, or refusals; and
- successful independent checksum and raw-result reaggregation.

| Measure | Run 1 | Run 2 |
|---|---:|---:|
| Circuit-weighted CM/CSE-flat geomean | 0.9977 | 1.0035 |
| Circuit-bootstrap 95% CI | [0.9942, 1.0012] | [0.9994, 1.0077] |
| Row-weighted geomean | 0.9973 | 1.0035 |
| Follow-up advantage gate | Fail | Fail |
| Persistent-cache hits / misses | 500 / 830 | 500 / 830 |
| Persistent-cache hit fraction | 37.6% | 37.6% |
| Family-CM compile geomean | 1.216 ms | 1.162 ms |
| Fresh-CM compile geomean | 1.416 ms | 0.964 ms |
| CSE-flat compile geomean | 0.404 ms | 0.277 ms |

Construction timings are descriptive single-pass measurements. Their direction within CM was not stable between runs, but both runs put family-CM construction well above CSE-flat construction. Run 2 retains every per-expression construction timing and independently reaggregates them; Run 1 retains only family-CM per-expression timings and the other construction aggregates.

## Mechanism finding

For all 129 formulas, CM and structural-CSE-flat lowered to exactly the same flat-instruction count and exactly the same executed-word-operation count. The warm timing parity is therefore mechanistically expected: once both representations are lowered to the same execution artifact, repeated contexts do not give the CM kernel distinct work to avoid.

The CM persistent cache found genuine cross-expression structural reuse—500 hits—but this did not produce a stable construction advantage and did not overcome the substantially lower CSE-flat construction cost.

## Protocol correction

The initial V1 full attempt aborted before writing an output directory. V1 generated the evaluator axis from semantic-support width, while two corpus records retain one syntactically present but semantically dead axis in the frozen truth artifact. V2 preserves every syntactic axis and fixes only semantically active variables. This correction was made after the missing-axis exception and before any full-run timing was available. The void V1 protocol remains in the repository rather than being silently rewritten.

## Interpretation

This pilot rejects the specific hypothesis that repeated partial-context evaluation alone creates a CM performance advantage over the strongest structural-CSE-flat program on these real circuit cones. It does not reject other CM roles:

- structural change attribution between real design revisions;
- durable serialization and reload;
- provenance/explanation attached to an exact artifact; or
- workflows whose incumbent discards shared structure between operations.

The next hardware experiment should therefore use a natural design revision history and score change localization or artifact reuse, not repeat another flat-kernel context comparison. The highest-priority cross-domain next experiment remains a versioned configuration/product-family corpus, where partial assignments and adjacent model revisions are native workload objects.

## Artifacts

- [V1 void protocol](HARDWARE-EPFL-CONTEXT-PILOT-PROTOCOL.md)
- [V2 protocol](HARDWARE-EPFL-CONTEXT-PILOT-PROTOCOL-V2.md)
- [Run 1 summary](runs/hardware-epfl-context-pilot-2026-08-27/summary.json)
- [Run 1 checksums](runs/hardware-epfl-context-pilot-2026-08-27/CHECKSUMS.sha256)
- [Run 2 summary](runs/hardware-epfl-context-pilot-2026-08-27-run2/summary.json)
- [Run 2 checksums](runs/hardware-epfl-context-pilot-2026-08-27-run2/CHECKSUMS.sha256)
- Runner: `cm_epfl_context_pilot.py`
- Independent audit: `cm_epfl_context_pilot_audit.py`
