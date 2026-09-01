# C27 support-aware fresh confirmation

Status: **complete**  
Confirmation gate: **pass**  
Break-even query count: **8**

The policy was frozen before this corpus: n<=4 uses verified truth screening and n>=5
uses the packed fused path. Every arm retains exact CM completion and final artifact
reconstruction.

| Queries | Support-aware vs screened | Minimum width vs screened | Best fixed method |
|---:|---:|---:|---|
| 1 | 0.9609x | 0.5600x | resident_direct_source_packed |
| 2 | 0.9829x | 0.7875x | resident_direct_screened |
| 4 | 1.0326x | 0.8949x | support_aware_c27_advice_on |
| 8 | 1.0216x | 0.9622x | support_aware_c27_advice_on |
| 16 | 1.0206x | 0.9706x | support_aware_c27_advice_on |
| 32 | 1.0403x | 0.9711x | support_aware_c27_advice_on |

Production promotion remains false.
