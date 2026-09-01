# C30 immutable prepared-policy context

Status: **complete**  
Prepared no-regret diagnostic gate: **pass**  
Role: local development evidence; shadow and production promotion remain false

C30 validates and hash-binds the frozen C27/C22 policies once, then creates each
eight-query session from the immutable prepared snapshot. The one-time preparation
cost is conserved and allocated across all candidate batches.

| Width | C29 total | C30 charged total | C30 query-only | C30 paired range | prepared non-query share |
|---:|---:|---:|---:|---:|---:|
| 3 | 0.8459x | 1.0154x | 1.0244x | 0.9359-1.0700x | 1.92% |
| 4 | 0.9689x | 1.0660x | 1.0701x | 1.0427-1.1168x | 0.99% |
| 5 | 1.0088x | 1.0165x | 1.0179x | 1.0080-1.0386x | 0.38% |
| 6 | 1.0331x | 1.0435x | 1.0438x | 1.0241-1.0489x | 0.11% |

Lifecycle preparation: **0.0704 ms**.  
Median per-session prepared setup: **0.0216 ms**.  
Aggregate charged total speedup: **1.0385x**.  
Minimum-width charged total speedup: **1.0154x**.

All timed queries remain exact and the fail-closed controls pass. This local run
tests the concrete C29 overhead diagnosis; its paired dispersion is not a new
cross-machine uncertainty adjudication. Exact fallback remains mandatory.
