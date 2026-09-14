# Comprehensive benchmark catalog

These 80 test families are recommendations. Source descriptions are cited facts; test designs, sizes and priorities are proposed experiments. None is an executed result. A family may have several task cells, and several families may share one upstream corpus.

Priority 1 is the initial campaign pool, priority 2 is the next pool, and priority 3 requires a larger adapter or a new capability. Selection into the first funded run is separately frozen in CAMPAIGN_PLAN.json.

All source links refer to upstream material consulted for this report. Dataset downloads, file hashes and per-file licensing remain acquisition work.

## Task contracts

- **T1:** Complete ordered packed truth vector over a declared basis; full consumption required.

- **T2:** Evaluation of specified concrete assignments/batches; return matching bits or output tuples.

- **T3:** Scalar status, witness, ordinary count or projected count; each output subtype is a distinct cell.

- **T4:** Session of explicitly typed queries; same ordered answers, preparation/cache lifetime and inputs.

- **T5:** Equivalence status, counterexample or exact semantic-difference count; separate output subtypes.

- **T6:** Complete ordered byte stream to a declared real sink, or explicitly declared cancellation prefix.

- **T7:** Exact GF(2) rank, consistency, solution count, basis or full decomposition; separate subtypes.

- **T8:** Simplified expression, synthesis artifact or historical boundary audit; quality guarantee explicit.

- **T9:** Weighted count/probability under specified arithmetic, projection and error guarantees.

- **T10:** Boolean set/bitmap query over arbitrary row IDs; distinct universe from complete assignments.


## Scale profiles

- **small:** 2,4,6,8; 10/12 only after timeout calibration; never force exponential minimization blindly to 32.

- **explicit:** 4,8,12,16,20,24,28,32 active/output variables when supported; bridge widths 18,22,26,30 optional.

- **explicit_large:** 20,24,28,30,32 with verified output/working-set admission and bounded complete streaming.

- **native_plus_explicit:** Whole source models at native size; explicit outputs only within admitted basis/byte limits; residuals separately labeled.

- **symbolic:** Whole input sizes including 32,64,128,256,1024+ variables where native algorithms and limits allow; no full expansion requirement.

- **projection:** Record total, visible and hidden widths independently; visible 8,12,16,20,24,28,32 plus whole-model scalar cases.

- **weighted:** Small audited encodings first; advance by encoded variables, factor width and arithmetic cost, not original node count.

- **affine:** 16,32,64,128,256,512,1024,4096 columns when limits allow; independently vary rows, rank and density.

- **query:** Q=1,2,4,8,16,64,256,1024; then observed trace Q. State width follows underlying input and resource limits.

- **batch_rows:** 8-128+ predicates; 1,32,1024,65536,1048576 actual rows/assignments where appropriate; rows are not 2^predicates.


## Comparator rules

- **T1:** CM full wrapper; optimized BitSet; sharing-aware CSE-flat; native/tiled words if verified; CUDD including full extraction; small SymPy table control.

- **T2:** Compiled direct/short-circuit evaluator; SymPy lambdify/NumPy; CSE-flat batch; admitted CM lookup/batch; relevant native application engine.

- **T3:** SAT: CaDiCaL/PySAT, Kissat one-shot, CryptoMiniSat for XOR. Counts: exact CUDD, d4, Ganak --prob 0, admitted CM scalar plans; projection capability checked.

- **T4:** Same task-specific controls with equivalent preparation, result caches, query assumptions, version invalidation and memory budgets.

- **T5:** SAT/ABC miter for status; packed XOR-popcount or exact projected counter for delta counts; CM matched output only.

- **T6:** CM and CSE-flat tiled stream plus complete-output delivery control; all methods include producer and final consumer costs.

- **T7:** Python packed Gaussian elimination; native M4RI; current CM-associated affine/decomposition path with all conversion charged.

- **T8:** SymPy simplify_logic explicit options; Espresso/ABC as suitable for declared quality; CM pipeline only if output guarantee is implemented.

- **T9:** Exact native counter/BDD weighted evaluation or native Bayesian/fault-tree engine; CM extension only after capability and precision validation.

- **T10:** CRoaring, dense words/bigint and sorted-list controls; CM/CSE batch adapter only after verifying arbitrary-row semantics.


## Hardware and logic design

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| H01 / P1 / application_derived | **EPFL arithmetic cones**. Select adder, multiplier, divider, square-root and other arithmetic roots by a fixed hash within width strata. [S02](https://github.com/lsils/benchmarks) | T1, T2, T5; explicit | Root/cone importer available in prior work; deduplicate designs and retain full-cone failures. A cut boundary is a derived abstraction. |

| H02 / P1 / application_derived | **EPFL control cones**. Sample arbiter, router, voter, decoder and other control functions independently of timings. [S02](https://github.com/lsils/benchmarks) | T1, T2, T5; explicit | Keep whole-design cluster identities; expose all tested roots, including constants and low-support roots. |

| H03 / P2 / legacy_benchmark | **ISCAS85 combinational logic**. Use the canonical combinational circuits and stratified output cones from an attributed distribution. [S05](https://iwls.org/iwls2005/benchmarks.html), [S08](https://github.com/zeroasiccorp/logikbench/blob/main/logikbench/benchmarks/koios/README.md) | T1, T2, T5; explicit | Verify original provenance and per-file terms through IWLS/LogikBench lineage; historical engineering benchmarks are not traffic traces. |

| H04 / P2 / legacy_benchmark | **ISCAS89 one-step logic**. Extract combinational next-state/output functions with current state explicitly declared as inputs. [S05](https://iwls.org/iwls2005/benchmarks.html), [S08](https://github.com/zeroasiccorp/logikbench/blob/main/logikbench/benchmarks/koios/README.md) | T1, T2, T3; native_plus_explicit | One step does not establish reachability or sequential equivalence; initial-state assumptions must be recorded. |

| H05 / P2 / application_derived | **IWLS2005 design suite**. Sample designs and combinational cones across gate count, depth and reconvergence. [S05](https://iwls.org/iwls2005/benchmarks.html) | T1, T2, T5; native_plus_explicit | Deduplicate shared ISCAS/ITC/OpenCores ancestry; do not count suite repackaging as new systems. |

| H06 / P2 / application_derived | **VTR and Koios designs**. Select independent accelerator/control designs, then freeze bit-level cones and output groups. [S06](https://docs.verilogtorouting.org/en/latest/vtr/benchmarks/), [S08](https://github.com/zeroasiccorp/logikbench/blob/main/logikbench/benchmarks/koios/README.md) | T1, T2, T5; native_plus_explicit | Elaboration, memories, signedness and sequential boundaries need verified import; neural accelerator hardware is not a neural inference benchmark. |

| H07 / P1 / application_derived | **Yosys large designs**. Use benchmarks_large designs unused in previous confirmation; retain synthesis and source identities. [S07](https://github.com/YosysHQ/yosys-bench) | T1, T2, T5; native_plus_explicit | Check elaboration against Yosys/ABC; preserving sharing is required in CM and CSE-flat alike. |

| H08 / P1 / synthetic_model | **Yosys small mechanisms**. Use benchmarks_small arithmetic, mux and gate tests to isolate depth and sharing effects. [S07](https://github.com/YosysHQ/yosys-bench) | T1, T2, T5; explicit | Upstream calls these mostly synthetic; retain that label and do not combine their weighting with real designs. |

| H09 / P1 / derived_transformation | **Original versus synthesized equivalence**. Compare original/ABC-rewritten circuits and controlled one-gate mutations; return equivalent status or exact difference count. [S02](https://github.com/lsils/benchmarks), [S35](https://github.com/berkeley-abc/abc) | T5, T8; native_plus_explicit | Equivalent pairs must be certified and mutations may be semantically masked; count only verified non-equivalent pairs as negatives. |

| H10 / P1 / application_derived | **Multi-output shared evaluation**. Request 1, 4, 16 and 64 outputs from one design, with one union basis and declared order. [S02](https://github.com/lsils/benchmarks), [S06](https://docs.verilogtorouting.org/en/latest/vtr/benchmarks/) | T1, T2, T4; explicit | All methods may share intermediates across roots; charge the sum of output bytes and multi-root preparation. |


## Configuration and feature models

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| F01 / P1 / application_derived | **Linux configuration formulas**. Select independent releases and whole models, plus separately labeled bounded residuals. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark) | T3, T4, T5; native_plus_explicit | Original features and auxiliaries must be mapped; arbitrary clause deletion is not a valid residual. |

| F02 / P1 / application_derived | **BusyBox version histories**. Use chronological versions and partial configurations; return feasibility, count and changed-product queries. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark), [S04](https://www.uvlhub.io/) | T3, T4, T5; native_plus_explicit | Split by system/history rather than rows; old consumed versions are regression evidence, not fresh confirmation. |

| F03 / P2 / application_derived | **uClibc and Fiasco configurations**. Sample both systems and preserve source feature mappings and previously found counterexamples. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark) | T3, T4, T5; native_plus_explicit | Full-CNF counts are separate from projected product counts; reject unsupported source semantics explicitly. |

| F04 / P2 / application_derived | **eCos/CDL configurations**. Use available attributed Boolean models and natural component boundaries. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark), [S04](https://www.uvlhub.io/) | T3, T4; native_plus_explicit | CDL attributes and non-Boolean constructs require a documented Boolean interpretation or refusal. |

| F05 / P1 / application_derived | **Automotive and financial product models**. Select one or more models per independent product family, including finance history where available. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark), [S04](https://www.uvlhub.io/) | T3, T4, T5; native_plus_explicit | A model's domain label does not prove deployed use; preserve obfuscation and conversion metadata. |

| F06 / P1 / mixed_repository | **Small SPLOT/UVL models**. Start with complete small models, stratified by hierarchy depth, constraints and valid-product density. [S04](https://www.uvlhub.io/) | T1, T3, T4; explicit | SPLOT contains community examples and synthetic models; classify origin individually and deduplicate other repositories. |

| F07 / P2 / application_derived | **Smartwatch product evolution**. Compare available Mi Band model versions and reduced/realized/planned configurations. [S04](https://www.uvlhub.io/) | T3, T4, T5; native_plus_explicit | These model kinds have different intended semantics; compare like kinds over time and preserve release ancestry. |

| F08 / P1 / modeled_queries_on_real_inputs | **Interactive configurator sessions**. Generate backtracking, contradictory selections and correlated partial assignments over real product models. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark), [S04](https://www.uvlhub.io/) | T4; query | Call modeled sessions synthetic unless an operator supplies real interactions; every method gets the same assumptions and reuse. |

| F09 / P1 / application_derived | **Dead, core and optional features**. Return complete status vectors from repeated SAT assumptions and count-based checks where admitted. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark), [S28](https://pysathq.github.io/docs/html/api/solvers.html) | T3, T4; native_plus_explicit | Incremental native SAT keeps learned clauses; cache query results and report total feature-analysis time. |

| F10 / P1 / application_derived | **Projected feature-product counts**. Count distinct concrete configurations after existential auxiliary elimination; include empty projection and unused features. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark), [S11](https://mccompetition.org/past_iterations.html) | T3, T4; projection | Projection-capable CM is reported in a separate checkout: locate and freeze it before admission; verify original conversion, not only DIMACS semantics. |


## SAT, counting and verification

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| C01 / P2 / mixed_repository | **Application SAT and UNSAT**. Use a family-balanced subset of the SAT competition with descriptions, both outcomes, and unmodified whole inputs. [S09](https://satcompetition.github.io/2025/benchmarks.html), [S28](https://pysathq.github.io/docs/html/api/solvers.html), [S29](https://github.com/arminbiere/cadical/releases), [S30](https://github.com/arminbiere/kissat/blob/master/README.md?plain=1) | T3; symbolic | Native CDCL is mandatory. CM explicit refusal is a result; whole industrial CNFs can greatly exceed 32 variables. |

| C02 / P2 / legacy_benchmark | **SATLIB planning**. Select bounded planning encodings and assumption queries across horizons. [S10](https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html) | T3, T4; symbolic | Solving one horizon is not an optimal planner; retain temporal semantics and decoder checks for returned plans. |

| C03 / P2 / synthetic_model | **SATLIB graph coloring**. Use flat/morphed graph-coloring CNFs across densities; separately generate small exactly checked graphs. [S10](https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html) | T3, T4; symbolic | Color bits and auxiliary counts differ from graph vertices; projected coloring counts must handle color symmetries explicitly. |

| C04 / P1 / mixed_repository | **Unweighted model counting competition**. Freeze a family-balanced selection from stable releases, retaining easy and hard application classes separately. [S11](https://mccompetition.org/past_iterations.html), [S12](https://mccompetition.org/2025/mc_description.html), [S33](https://github.com/crillab/d4v2), [S34](https://github.com/meelgroup/ganak) | T3, T4; symbolic | Exact arbitrary-precision answers, declared unused variables and independent counters required; hard competition selection is not typical traffic. |

| C05 / P2 / mixed_repository | **Projected model counting competition**. Use published projection sets and vary assumptions only in a separate modeled-query panel. [S11](https://mccompetition.org/past_iterations.html), [S12](https://mccompetition.org/2025/mc_description.html), [S34](https://github.com/meelgroup/ganak) | T3, T4; projection | Do not replace projected count with total CNF count; use deterministic exact mode and verify adapter support. |

| C06 / P3 / mixed_repository | **Weighted model counting**. Use rational-weight instances and defined evidence queries from archived weighted tracks. [S11](https://mccompetition.org/past_iterations.html), [S12](https://mccompetition.org/2025/mc_description.html), [S34](https://github.com/meelgroup/ganak) | T9; weighted | CM weight support is a new capability gate; exact, approximate and floating-tolerance results get different scoreboards. |

| C07 / P3 / application_derived | **Package dependency feasibility**. Import attributed CUDF examples or operator-provided package requests, checking installability and returned package sets. [S37](https://github.com/potassco/aspcud) | T3; symbolic | aspcud optimization includes preferences; benchmark feasibility alone unless every arm returns the same certified optimum. |

| C08 / P3 / application_derived | **SMT-LIB QF_BV circuits**. Choose bit-vector cases; evaluate original SMT with Z3 and a checked Boolean translation with SAT/CM. [S36](https://smt-lib.org/benchmarks.shtml), [S38](https://github.com/Z3Prover/z3) | T3, T5; symbolic | Charge bit-blasting; word width is not total Boolean width; signedness, overflow, shifts and zero-division semantics must match. |


## Biology, reliability and probability

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| B01 / P1 / application_derived | **Biological update-function tables**. Extract each model's regulator update functions and request complete local truth vectors. [S13](https://github.com/sybila/biodivine-boolean-models), [S14](https://zenodo.org/records/8020309) | T1, T2; explicit | Network size and local in-degree differ; preserve source/free-input conventions and Booleanization metadata. |

| B02 / P2 / application_derived | **Synchronous Boolean-network simulation**. Evaluate all node updates for the same batches of initial states and fixed step counts. [S13](https://github.com/sybila/biodivine-boolean-models), [S15](https://github.com/sybila/biodivine-aeon-py) | T2; batch_rows | All nodes read the old state; full transition relations contain current and next-state variables and are a different task. |

| B03 / P2 / application_derived | **Biological fixed points**. Solve conjunctions of each state variable equal to its update function; return count/status/witness in separate cells. [S13](https://github.com/sybila/biodivine-boolean-models), [S15](https://github.com/sybila/biodivine-aeon-py) | T3; native_plus_explicit | Compare with AEON/native SAT; fixed points are not all attractors, and asynchronous dynamics require a separate implementation. |

| B04 / P1 / modeled_queries_on_real_inputs | **Perturbation and knockout contexts**. Apply fixed-variable knockout/overexpression contexts and evaluate or count the same residual functions. [S13](https://github.com/sybila/biodivine-boolean-models), [S15](https://github.com/sybila/biodivine-aeon-py) | T4; query | Retain source biological provenance without claiming clinical utility; generated perturbation order is modeled reuse. |

| B05 / P2 / application_derived | **Static fault-tree top event**. Use OpenPSA static AND/OR/NOT/k-of-n trees; compute event truth vectors, existence or counts. [S16](https://docs-dev.openpra.org/guides/benchmarking.html), [S17](https://github.com/rakhimov/scram) | T1, T3, T4; native_plus_explicit | Repeated basic events are the same variable; dynamic gates and common-cause semantics need separate modeling. |

| B06 / P3 / application_derived | **Fault-tree reliability probabilities**. Use exact top-event probability under a declared independence model and evidence updates. [S16](https://docs-dev.openpra.org/guides/benchmarking.html), [S17](https://github.com/rakhimov/scram) | T9; weighted | SCRAM exact BDD probability is the comparator; rare-event approximations and truncated cut sets are not exact answers. |

| B07 / P3 / reference_model | **Small Bayesian-network inference**. Start with ASIA, CANCER and EARTHQUAKE; compare evidence likelihood/marginal queries under an audited encoding. [S18](https://www.bnlearn.com/bnrepository/) | T9; weighted | CPTs are conditional probabilities; arbitrary Boolean counts do not implement Bayesian inference. Native elimination is mandatory. |

| B08 / P3 / reference_model | **Medium Bayesian-network inference**. Use CHILD, ALARM, INSURANCE and WATER after small-model conversion tests succeed. [S18](https://www.bnlearn.com/bnrepository/) | T9; weighted | Categorical node count is not Boolean width; preserve one-hot constraints and exact/tolerance contract, including zero-probability evidence. |


## Policies and data filtering

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| P01 / P2 / application_fixture | **Cedar authorization examples**. Use handwritten policies with expected decisions and request contexts; retain an admitted finite Boolean subset. [S19](https://github.com/cedar-policy/cedar-integration-tests), [S20](https://github.com/cedar-policy/cedar) | T2, T4; query | Preserve forbid precedence, entity membership, missing fields and errors; compare native prepared Cedar as well as cold parsing. |

| P02 / P3 / synthetic_fuzz | **Cedar fuzz corpus**. Use a fixed sample of upstream generated cases for adapter differential correctness and repeated-request tests. [S19](https://github.com/cedar-policy/cedar-integration-tests) | T2, T4; query | Corpus generation targets code coverage, not production frequencies; unsupported/error cases cannot silently become deny. |

| P03 / P3 / application_fixture | **OPA policy evaluation**. Select documented Boolean policy fragments and benchmark raw, prepared and compiled incumbent paths. [S21](https://www.openpolicyagent.org/docs/policy-performance) | T2, T4; query | Rego collections, undefined values and external lookups are not free Boolean atoms; charge extraction and preserve result semantics. |

| P04 / P3 / synthetic_model | **Packet-classification rules**. Generate fixed ClassBench seeds and packet batches; return the first matching action or permitted-set artifact. [S22](https://github.com/classbench-ng/classbench-ng) | T2, T4; batch_rows | Preserve rule order and default action; full packet bit widths generally exceed explicit-table limits. |

| P05 / P3 / application_derived | **Roaring bitmap query expressions**. Run intersections, unions, differences and shared multi-output expressions on real bitmap datasets. [S23](https://github.com/RoaringBitmap/real-roaring-datasets), [S24](https://github.com/RoaringBitmap/CRoaring) | T10; batch_rows | Rows are arbitrary records, not all truth assignments; CM needs a verified batch evaluator. Compare CRoaring, dense words and sorted-set intersection. |

| P06 / P2 / synthetic_model | **Feature flags and eligibility rule models**. Generate tenant/rule hierarchies, allow/deny conflicts and correlated request attributes with declared distributions. [S19](https://github.com/cedar-policy/cedar-integration-tests), [S21](https://www.openpolicyagent.org/docs/policy-performance) | T2, T4; query | Distinguish primitive predicate extraction from Boolean combination and include a compiled native/short-circuit evaluator. |


## Affine logic and coding

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| A01 / P1 / application_derived | **LDPC parity-check feasibility and count**. Use verified parity-check matrices; vary syndrome and erasure/fixed-bit contexts. [S25](https://github.com/aff3ct/configuration_files), [S26](https://github.com/malb/m4ri) | T7, T3; affine | H matrices differ from generators; compare packed elimination and M4RI. Counting solutions is not error-correction decoding performance. |

| A02 / P1 / synthetic_model | **CRC/LFSR linear constraints**. Generate pinned polynomials, bit ordering and observed-output constraints; return rank, consistency and exact count. [S26](https://github.com/malb/m4ri), [S27](https://github.com/msoos/cryptominisat) | T7, T3; affine | Pure affine formulas favor algebraic solvers; identify generic GF(2) benefits separately from CM representation benefits. |

| A03 / P2 / synthetic_model | **Structured dense/sparse GF(2)**. Sweep dimensions, density, rank deficiency, duplicate rows and contradictions with planted exact ranks. [S26](https://github.com/malb/m4ri) | T7, T3; affine | Dense M4RI and Python packed elimination get the same native rows; AST-to-row conversion is separately charged. |

| A04 / P2 / synthetic_model | **Mixed XOR/CNF cryptographic models**. Combine parity layers with nonlinear gates; sweep XOR density and nonlinear count using published generator specifications. [S27](https://github.com/msoos/cryptominisat) | T1, T3; native_plus_explicit | These are cryptography-inspired models, not a claim to break real ciphers; include CryptoMiniSat native XOR support. |

| A05 / P2 / synthetic_model | **Complete ANF versus rank-only queries**. Request full ANF coefficients or a declared rank/decomposition artifact from the same truth functions in distinct lanes. [S01](https://docs.sympy.org/latest/modules/logic.html), [S26](https://github.com/malb/m4ri) | T7; explicit | ANF transform, rank and full decomposition have different outputs; include every transform/conversion and exact artifact verification. |

| A06 / P2 / application_derived | **Repeated syndrome sessions**. Keep a parity-check system fixed while processing distinct RHS values, fixed bits and selected revisions. [S25](https://github.com/aff3ct/configuration_files), [S26](https://github.com/malb/m4ri) | T4, T7; affine | Incumbents may reuse factorization; identical-result memoization and changed matrix versions must be represented fairly. |


## Synthetic mechanism and boundary tests

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| S01 / P1 / synthetic_control | **Constants, literals and absent variables**. Cover true/false, literals, tautologies and unused ambient variables with analytic counts. [S01](https://docs.sympy.org/latest/modules/logic.html) | T1, T2, T3; explicit | Unused basis variables multiply counts; a large declared basis with tiny support is its own stratum. |

| S02 / P1 / synthetic_model | **Balanced versus deep expression trees**. Match operator counts and effective support while varying depth, fan-in and recursion exposure. [S07](https://github.com/YosysHQ/yosys-bench) | T1, T2; explicit | Match nodes rather than nominal generator depth; use independently proved live-variable controls. |

| S03 / P1 / synthetic_model | **Shared DAG versus duplicated tree**. Generate controlled sharing factors with identical semantics and expose repeated subgraphs. [S02](https://github.com/lsils/benchmarks) | T1, T2; explicit | Include raw recursion, memoization and CSE-flat ladder; a sharing win alone is not CM-specific. |

| S04 / P1 / synthetic_control | **Parity and equivalence chains**. Generate all-live parity/equivalence functions at each explicit width with known counts. [S27](https://github.com/msoos/cryptominisat) | T1, T3; explicit | Native XOR/CDCL and GF(2) are strong scalar baselines; constants from accidental cancellation must be detected. |

| S05 / P1 / synthetic_model | **Cardinality and voting rules**. Generate at-most, exactly and at-least thresholds, including boundary thresholds. [S07](https://github.com/YosysHQ/yosys-bench), [S28](https://pysathq.github.io/docs/html/api/solvers.html) | T1, T2, T3; explicit | Use combinatorial binomial counts as an oracle; retain encoding size and auxiliaries for sequential/totalizer controls. |

| S06 / P1 / synthetic_model | **Multiplexers and selectors**. Vary address bits, data bits, sharing and variable order with a stable selection definition. [S07](https://github.com/YosysHQ/yosys-bench) | T1, T2; explicit | Total input width includes address and data; compare BDD natural, interleaved and dynamic orders with ordering costs. |

| S07 / P1 / synthetic_model | **Arithmetic Boolean functions**. Use adders, comparators and selected multiplier bits; record operand widths and output choice. [S02](https://github.com/lsils/benchmarks), [S07](https://github.com/YosysHQ/yosys-bench) | T1, T3, T5; explicit | Two b-bit operands require up to 2b inputs; include native arithmetic for concrete-assignment tasks. |

| S08 / P1 / synthetic_model | **Random 3-CNF density sweep**. Generate unique seeded cases across clause/variable ratios 1, 3, 4, 4.3, 5 and 8. [S10](https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html) | T1, T3; explicit | Balance outcomes after recording all draws; ratio 4.3 is a parameter, not a proved threshold for every small n. |

| S09 / P1 / synthetic_model | **Horn and 2-CNF controls**. Sweep implication graphs, satisfiable/unsatisfiable cases and partial contexts. [S10](https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html), [S28](https://pysathq.github.io/docs/html/api/solvers.html) | T3, T4; native_plus_explicit | Include specialized linear-time SAT controls; easy status does not imply easy model counting. |

| S10 / P1 / synthetic_model | **Independent components**. Compose disjoint small factors while increasing total variables to 64, 128, 256 and beyond. [S11](https://mccompetition.org/past_iterations.html) | T3, T4; symbolic | Compare factorized counts with native counters and product-of-counts control; never expand the full state space unnecessarily. |

| S11 / P1 / synthetic_model | **Overlap and elimination-width ladder**. Generate chains, cycles, grids and hub/star CNFs with matched counts of variables/clauses where possible. [S11](https://mccompetition.org/past_iterations.html), [S33](https://github.com/crillab/d4v2) | T3, T4; symbolic | Record measured induced width and ordering cost; include deliberately hostile elimination orders and refusals. |

| S12 / P1 / synthetic_control | **Auxiliary/projection correctness traps**. Create unique-extension gates, nonunique auxiliaries, empty projections and unused selected variables. [S11](https://mccompetition.org/past_iterations.html), [S12](https://mccompetition.org/2025/mc_description.html) | T3, T4; projection | E.g. a true visible variable plus a free hidden variable has total count 2 but projected count 1; this must not be conflated. |

| S13 / P1 / synthetic_control | **Rewrite and equivalence adversaries**. Use absorption, De Morgan, double negation, XOR cancellation and masked mutations with certified outcomes. [S01](https://docs.sympy.org/latest/modules/logic.html) | T1, T3, T5; explicit | All exact methods may exploit simplification; include unchanged negative controls and failed mutation attempts. |

| S14 / P2 / synthetic_model | **BDD variable-order sensitivity**. Construct paired equality and multiplexer families in grouped/interleaved/random orders. [S31](https://github.com/cuddorg/cudd) | T1, T3; explicit | Charge reorder/search cost; do not report the worst BDD order as its sole comparator or oracle-best order as a deployable selector. |

| S15 / P2 / synthetic_model | **Output density and runs**. Sweep sparse, dense, clustered and alternating outputs on declared finite universes. [S24](https://github.com/RoaringBitmap/CRoaring) | T1, T10; explicit | Dense versus compressed artifacts must be normalized or scored by a downstream task; complements mask unused high bits. |

| S16 / P1 / synthetic_control | **True 24-32-variable frontier**. Construct certified all-live instances at 20, 24, 28, 30 and 32; add a separate low-support ambient ladder. [S02](https://github.com/lsils/benchmarks) | T1, T3, T6; explicit_large | Use resource preflight, complete packed/stream verification and independent variable-influence checks; sampled equality alone is provisional. |


## Lifetime and delivery tests

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| L01 / P1 / modeled_lifecycle | **Cold versus resident amortization**. Measure Q=1,2,4,8,16,64,256,1024 distinct queries with setup charged once per session. [S28](https://pysathq.github.io/docs/html/api/solvers.html), [S31](https://github.com/cuddorg/cudd) | T4; query | Include cached-result lookup for identical queries and native incumbent preparation reuse; model Q is not observed production Q. |

| L02 / P1 / modeled_lifecycle | **Cache pressure and eviction**. Use uniform and Zipf-like accesses, working sets below/above capacity, renaming and basis changes. [S21](https://www.openpolicyagent.org/docs/policy-performance), [S24](https://github.com/RoaringBitmap/CRoaring) | T4; query | Hold byte budgets equal, account for caller-held references, and label synthetic traffic explicitly. |

| L03 / P2 / modeled_lifecycle | **Version invalidation**. Replay genuine source versions with separately modeled query arrivals and occasional no-op edits. [S03](https://github.com/SoftVarE-Group/feature-model-benchmark), [S07](https://github.com/YosysHQ/yosys-bench) | T4, T5; query | Version history does not reveal query frequency; frozen chronological holdout and independent result checks required. |

| L04 / P1 / modeled_lifecycle | **Fresh process and structural reload**. Compare resident plans, new engines, fresh processes and checked artifact reloads for identical sessions. [S39](https://docs.runpod.io/pods/pricing), [S40](https://docs.runpod.io/pods/storage/types) | T4; query | Include imports, dynamic library load, preparation, deserialization and first query; native persistence gets equal opportunity. |

| L05 / P1 / modeled_delivery | **Complete streaming to real sinks**. Deliver ordered packed bytes to file, pipe and slow-reader sinks; sweep 8KiB,64KiB,1MiB,8MiB chunks. [S40](https://docs.runpod.io/pods/storage/types) | T6; explicit_large | Measure final consumer completion, cancellation and backpressure; lazy iterator creation is not complete evaluation. |

| L06 / P2 / modeled_load | **Concurrency and workspace isolation**. Use 1,2,4,8 workers on independent/shared plans with memory pressure and deterministic results. [S32](https://github.com/trolando/sylvan) | T2, T4; query | Verify private mutable scratch, matched CPU quotas, no GIL asymmetry hidden in claims, and no oversubscribed timing lane. |

| L07 / P2 / modeled_load | **Long soak, recovery and refusal**. Run bounded sessions with cancellations, refused widths, resource exhaustion and process restarts. [S40](https://docs.runpod.io/pods/storage/types) | T4, T6; query | Record leak trends, successful-work throughput and every lost request; a soak is engineering evidence rather than an algorithm speedup. |

| L08 / P2 / production_trace_pending | **Independent consumer trace**. Capture an already-used caller's natural queries, lifetimes, revisions and consumed outputs. [S19](https://github.com/cedar-policy/cedar-integration-tests), [S21](https://www.openpolicyagent.org/docs/policy-performance) | T2, T4, T6; query | Owner and trace admission required; local metadata-only sampling precedes authorized exact replay. This is the production-savings claim lane. |


## SymPy and representation controls

| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |
| --- | --- | --- | --- |

| Y01 / P1 / historical_replay | **Reconstruct archived SymPy comparison**. Replay the historical formulas and pinned source when recoverable; report old timer boundaries and current equivalents. [S01](https://docs.sympy.org/latest/modules/logic.html) | T8; small | Historical labels are not trusted as task parity; unrecoverable source/formulas remain unverified and are not regenerated as exact replays. |

| Y02 / P1 / api_baseline | **SymPy truth_table API**. Fully consume truth_table(..., input=False) into the agreed packed result on small widths. [S01](https://docs.sympy.org/latest/modules/logic.html) | T1; small | Include SymPy conversion and generator consumption; narrow per-cell timeouts prevent tiny controls dominating the campaign. |

| Y03 / P1 / api_baseline | **SymPy lambdify evaluation**. Compile Boolean expressions to NumPy callable and evaluate identical assignment batches; compare cse on/off. [S01](https://docs.sympy.org/latest/modules/logic.html) | T2; batch_rows | Charge callable compilation/JIT where relevant and normalize constants/scalars; do not include simplification unless requested. |

| Y04 / P1 / api_baseline | **SymPy SAT and equivalence**. Use satisfiable(F) and satisfiable(XOR(F,G)); compare status or witness against native SAT and CM. [S01](https://docs.sympy.org/latest/modules/logic.html), [S28](https://pysathq.github.io/docs/html/api/solvers.html) | T3, T5; small | An unevaluated simplify_logic result is unknown for proof purposes; failure to simplify to false does not establish non-equivalence. |

| Y05 / P2 / api_baseline | **SymPy simplified SOP/POS**. Request simplified SOP/POS from fixed small formulas; compare alternative simplification pipelines under equivalence checks. [S01](https://docs.sympy.org/latest/modules/logic.html) | T8; small | CM alone has no matched minimizer here; CM plus the same minimizer is a pipeline arm. Report quality/runtime, not a full-table speed ranking. |

| Y06 / P2 / api_baseline | **Espresso and synthesis quality**. Use Boolean cover/logic synthesis tasks with equivalent output, literal/gate count, and runtime. [S01](https://docs.sympy.org/latest/modules/logic.html), [S35](https://github.com/berkeley-abc/abc) | T8; small | Heuristic and exact minimization are separate guarantees; input preparation and truth-table conversion are charged symmetrically. |

| Y07 / P2 / artifact_fixture | **IWLS2026 published truth tables**. Use already-materialized tables for representation loading, queries and a separate logic-synthesis study. [S42](https://github.com/alanminko/iwls2026-ls-contest/) | T8, T4; explicit | There is no AST-to-table construction to time; undisclosed function origins do not establish application provenance. |

| Y08 / P1 / mechanism_ablation | **CM contribution ladder**. Compare raw AST, memoized AST, CSE-flat, CM IR, optimized packed masks and the same scalar algorithm from raw versus CM ingress. [S02](https://github.com/lsils/benchmarks), [S31](https://github.com/cuddorg/cudd) | T1, T2, T3; explicit | Give shared optimizations to every eligible arm. Attribute a gain to the smallest changed mechanism that explains it. |
