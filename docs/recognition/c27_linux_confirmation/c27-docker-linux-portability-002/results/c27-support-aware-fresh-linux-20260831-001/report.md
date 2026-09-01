# C27 support-aware fresh confirmation

Status: **complete**  
Confirmation gate: **pass**  
Break-even query count: **8**

The policy was frozen before this corpus: n<=4 uses verified truth screening and n>=5
uses the packed fused path. Every arm retains exact CM completion and final artifact
reconstruction.

| Queries | Support-aware vs screened | Minimum width vs screened | Best fixed method |
|---:|---:|---:|---|
| 1 | 0.9876x | 0.5118x | resident_direct_source_packed |
| 2 | 1.0240x | 0.8347x | resident_direct_source_packed |
| 4 | 1.0676x | 0.8653x | support_aware_c27_advice_on |
| 8 | 1.0404x | 0.9573x | support_aware_c27_advice_on |
| 16 | 1.0759x | 0.8520x | support_aware_c27_advice_on |
| 32 | 0.9861x | 0.9693x | resident_direct_screened |

Production promotion remains false.
