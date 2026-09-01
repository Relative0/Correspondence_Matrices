# C27 support-aware fresh confirmation

Status: **complete**  
Confirmation gate: **pass**  
Break-even query count: **8**

The policy was frozen before this corpus: n<=4 uses verified truth screening and n>=5
uses the packed fused path. Every arm retains exact CM completion and final artifact
reconstruction.

| Queries | Support-aware vs screened | Minimum width vs screened | Best fixed method |
|---:|---:|---:|---|
| 1 | 1.0027x | 0.8207x | resident_direct_source_packed |
| 2 | 0.9209x | 0.6771x | resident_direct_screened |
| 4 | 1.0130x | 0.8670x | resident_direct_source_packed |
| 8 | 1.0407x | 0.9974x | support_aware_c27_advice_on |
| 16 | 1.0626x | 0.9439x | support_aware_c27_advice_on |
| 32 | 1.0448x | 0.9851x | support_aware_c27_advice_on |

Production promotion remains false.
