# C27 support-aware fresh confirmation

Status: **complete**  
Confirmation gate: **pass**  
Break-even query count: **8**

The policy was frozen before this corpus: n<=4 uses verified truth screening and n>=5
uses the packed fused path. Every arm retains exact CM completion and final artifact
reconstruction.

| Queries | Support-aware vs screened | Minimum width vs screened | Best fixed method |
|---:|---:|---:|---|
| 1 | 0.9616x | 0.6113x | resident_direct_source_packed |
| 2 | 0.9883x | 0.7746x | resident_direct_source_packed |
| 4 | 1.0178x | 0.8858x | support_aware_c27_advice_on |
| 8 | 1.0352x | 0.9608x | support_aware_c27_advice_on |
| 16 | 1.0290x | 0.9609x | support_aware_c27_advice_on |
| 32 | 1.0363x | 0.9893x | support_aware_c27_advice_on |

Production promotion remains false.
