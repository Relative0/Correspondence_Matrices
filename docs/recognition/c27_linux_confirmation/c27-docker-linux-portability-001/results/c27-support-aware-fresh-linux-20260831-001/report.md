# C27 support-aware fresh confirmation

Status: **complete**  
Confirmation gate: **pass**  
Break-even query count: **8**

The policy was frozen before this corpus: n<=4 uses verified truth screening and n>=5
uses the packed fused path. Every arm retains exact CM completion and final artifact
reconstruction.

| Queries | Support-aware vs screened | Minimum width vs screened | Best fixed method |
|---:|---:|---:|---|
| 1 | 0.9525x | 0.6803x | resident_direct_screened |
| 2 | 0.9433x | 0.7647x | resident_direct_screened |
| 4 | 1.0622x | 0.8933x | support_aware_c27_advice_on |
| 8 | 1.0575x | 0.9498x | resident_direct_source_packed |
| 16 | 0.9854x | 0.9636x | resident_direct_source_packed |
| 32 | 1.0349x | 1.0185x | support_aware_c27_advice_on |

Production promotion remains false.
