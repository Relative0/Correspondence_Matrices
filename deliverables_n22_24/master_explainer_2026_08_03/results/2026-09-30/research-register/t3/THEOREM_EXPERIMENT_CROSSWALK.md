# Frozen T3 to implementation and experiment

| Contract quantity | Implementation / raw evidence |
|---|---|
| Supplied U,W at named fixed cut | `inputs/NATURAL_FACTORS.json` and `TIMING_CASES.json`; canonical factor hash; `left`/`right` order is MSB-first within each side |
| n,p,q,r | n=p+q; r is supplied width; `actual_rank` recorded separately; inflation/cancellation controls retain supplied r |
| Total k and residual h | Capped/deduplicated {0,1,2,4,n}; h=k-depth at every prefix; repeated or excess updates rejected by T3 |
| Occurring support s | Initial nonzero profile count on anchor side; labels never silently dropped after updates |
| A and B | Independent superset-zeta construction of exact indicator and signed-character moments; no U/W fields in persistent object |
| Source disposal | T3 uses slots containing only moments, scope, labels and horizon; correctness tests poison source arrays; cold T3 consumer receives no factors |
| Update | Copy/subtract on affected family; unaffected arrays stay allocated and only horizon changes; `moment_counter_operations` records s D(d-1,h-1) |
| COUNT | Exact integer sign sum; no source lookup, histogram rebuild or transform online |
| Fixed counter widths | Anchor dimension+1 unsigned; other original dimension+2 signed two's-complement; retained after updates |
| Dense primary payload | Row anchored `(2**r-1)*((p+1)D(p,k)+(q+2)D(q,k))`; profile labels implicit |
| Sparse secondary payload | Observed s times r-bit label and fixed-width counters; row and column kept separate |
| Adaptive secondary choice | Scan support and choose smaller sparse formula, row on tie; scan charged in construction; never substitutes for primary inequality |
| Mathematical vs physical size | `persistent_payload_bits`, `serialized_bytes`, process RSS and serialized header/padding kept separate |
| Construction | Measured per-profile zeta algorithm O(s[p2^p+q2^q]) work, not a claim of executing the Theory Walsh schedule |
| Index work | Subset enumeration is performed inside measured construction/update/serialization; no uncharged external index; separate indexing phase is zero |
| Cumulative queries | Every tested prefix gets the full requested count batch; query_count=(k+1)*batch; horizon is not reset |
| Dense byte crossover | Test mathematical inequality unchanged, then separately check full serialized bytes against raw-factor payload and actual raw serialization |
| Full lifecycle | Source-artifact parse, construction, verification, serialization, optional loading, updates and queries; independent-oracle generation and parent/process overhead explicitly added/reported |

The fixed-width binary codec is compact; the live Python object uses dictionaries/lists and arbitrary-precision integers. The theorem payload formula is not asserted to equal Python heap bytes or process RSS. Inactive moments remain allocated; serialization compacts active cells and is charged. The native comparators cache repeated counts until an update; T3 does its stated O(s) count each time. Their cache construction/count work is measured.

`payloads.row_support` and `payloads.column_support` are observed occurring nonzero support sizes. In per-operation records, `s` is the number of allocated profile blocks: equal to observed support for sparse states, but equal to 2^r-1 for dense states. The dense update formula uses that latter worst-case block count. These fields must not be interchanged.

The bounded C++ implementation uses exact unsigned 64-bit counts and rejects n>62. This is exact throughout this campaign (n<=20); it is not a claim of arbitrary-width native support. CUDD compiles factor-bit BDDs, performs sifting, then the C++ kernel handles signed-edge DAG traversal and residual counts. Sifting and DAG export are charged to construction. This is a newly optimized compiled endpoint, not the historical Python ROBDD.

The corpus and timing panel were frozen before outcomes. All eligible cuts contribute incidence; timing uses one maximum-support case per independent eligible design with a hash tie-break. Outputs are never treated as independent designs. Supplied-factor times are the primary endpoint. Separately measured BLIF extraction/discovery records allow the larger input boundary to be assessed without pretending those are measured inside the same trial.
