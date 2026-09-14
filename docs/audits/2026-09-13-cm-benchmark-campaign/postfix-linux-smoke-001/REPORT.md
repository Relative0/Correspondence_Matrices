# CM post-fix native Linux smoke

Status: passed locally in a dedicated Ubuntu 24.04 WSL distribution.

The pinned d4 source built successfully. Under the same 4 GiB address-space limit used by the frozen campaign worker, the successor adapter returned exact counts 4 and 0 for the satisfiable and unsatisfiable fixtures while explicitly passing 256 MiB and 64 MiB cache-page bounds.

Ganak exact and projected counting, CryptoMiniSat native XOR-CNF solving, Kissat SAT/UNSAT status, and Biodivine AEON fixed-point counting all passed their pinned fixtures. AEON and the scalar oracle both returned two fixed points.

The bounded d4 corpus replay covered all 8 exact-count cases selected by the frozen plan: 7 completed, 1 reached the 30-second local bound, and 0 aborted or otherwise errored. Every completed d4 count agrees with the frozen Ganak count where one is available.

No cloud resource was created, no secret was accessed, and the native build and execution used no network after the Ubuntu prerequisites were installed.
