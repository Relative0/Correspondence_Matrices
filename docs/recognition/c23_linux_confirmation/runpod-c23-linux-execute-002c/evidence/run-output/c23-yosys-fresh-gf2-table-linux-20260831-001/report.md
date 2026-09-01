# C23 fresh Yosys-generator exact GF(2) method table

Status: **complete**  
Best fixed method: **cm_compiled_screened**

All methods used the unchanged C21 implementations and delivered the same
bounded exhaustive-best exact artifact from the same frozen expression input.

| Method | Aggregate vs exhaustive | Aggregate vs screened | Minimum vs exhaustive |
|---|---:|---:|---:|
| cm_exhaustive | 1.0000x | 0.2997x | 1.0000x |
| cm_screened | 3.3366x | 1.0000x | 1.1545x |
| cm_compiled_screened | 3.3467x | 1.0030x | 1.1380x |
| truth_anf_min_cut | 3.2889x | 0.9857x | 1.0563x |
| source_packed_anf | 3.3309x | 0.9983x | 1.3166x |
| bdd_level_cut | 1.5342x | 0.4598x | 0.0471x |
| source_interaction_cut | 3.3082x | 0.9915x | 1.0710x |

Per-case oracle headroom over the best fixed method: **1.0049x**.

The generator paths and truth identities were sealed before timing and did not
participate in C22 selection. Production promotion remains false.
