"""Build this research package's derived catalog and audit; never run a benchmark or use the network."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATE = "2026-09-13"

# Source descriptions identify material actually consulted, not a frozen dataset download.
SOURCE_ROWS = [
    ("S01", "SymPy development team", "Logic documentation", "1.14.0 documentation", "https://docs.sympy.org/latest/modules/logic.html", "Simplification limit, truth-table and SAT APIs."),
    ("S02", "EPFL / LSILS", "Combinational benchmark suite", "2015 suite; repository consulted", "https://github.com/lsils/benchmarks", "Arithmetic and control circuits; preserve upstream design and revision identities."),
    ("S03", "SoftVarE Group", "Feature-Model Benchmark", "SPLC 2024 dataset; repository consulted", "https://github.com/SoftVarE-Group/feature-model-benchmark", "Real feature-model collection, formats, domains and histories."),
    ("S04", "DiversoLab and collaborators", "UVLHub", "2024 repository paper; current portal consulted", "https://www.uvlhub.io/", "SPLOT, BusyBox, finance and smartwatch model datasets; provenance varies by model."),
    ("S05", "IWLS organizers", "IWLS 2005 Benchmarks", "2005", "https://iwls.org/iwls2005/benchmarks.html", "Public sequential/combinational synthesis benchmark acquisition source."),
    ("S06", "Verilog-to-Routing project", "Benchmarks documentation", "9.0.0-dev documentation", "https://docs.verilogtorouting.org/en/latest/vtr/benchmarks/", "VTR benchmark suites; select at design level, preserve upstream origin."),
    ("S07", "YosysHQ", "yosys-bench", "repository consulted", "https://github.com/YosysHQ/yosys-bench", "Explicit distinction between mostly synthetic small and real-design large suites."),
    ("S08", "Zero ASIC", "LogikBench Koios benchmark provenance", "repository consulted", "https://github.com/zeroasiccorp/logikbench/blob/main/logikbench/benchmarks/koios/README.md", "Vendored suite provenance and VTR origin; overlapping copies are not independent data."),
    ("S09", "SAT Competition organizers", "SAT Competition 2025 benchmarks", "2025", "https://satcompetition.github.io/2025/benchmarks.html", "SAT competition acquisition entry; freeze actual file list and descriptions."),
    ("S10", "Holger Hoos and Thomas Stutzle / SATLIB", "SATLIB Benchmark Problems", "historical archive", "https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html", "Planning, graph coloring, parity and random CNF test families."),
    ("S11", "Model Counting Competition organizers", "Public Resources", "2020-2025 archive consulted", "https://mccompetition.org/past_iterations.html", "Counting dataset releases; 2025 links are explicitly labeled draft."),
    ("S12", "Model Counting Competition organizers", "2025 competition description", "2025", "https://mccompetition.org/2025/mc_description.html", "Separate counting/projection/weight tracks, precision categories, limits and hard-instance selection."),
    ("S13", "Pastva and Biodivine collaborators", "Biodivine Boolean Models", "repository consulted", "https://github.com/sybila/biodivine-boolean-models", "Biological model sources, free input convention and Booleanized multivalued models."),
    ("S14", "Samuel Pastva", "Biodivine Boolean Models; Edition 2022", "Zenodo record created 2023-06-09", "https://zenodo.org/records/8020309", "Stable release with 212 published models; bnet archive is small enough for a first import."),
    ("S15", "Biodivine project", "AEON.py", "repository consulted", "https://github.com/sybila/biodivine-aeon-py", "Native symbolic Boolean-network comparator and formats."),
    ("S16", "OpenPRA project", "Benchmarking Tool", "documentation consulted", "https://docs-dev.openpra.org/guides/benchmarking.html", "Fault-tree OpenPSA models, exact probability and approximate/minimal-cut-set distinctions."),
    ("S17", "SCRAM project", "SCRAM", "repository consulted", "https://github.com/rakhimov/scram", "Fault-tree analysis implementation; use supported static Boolean subset and audited fixtures."),
    ("S18", "Marco Scutari", "bnlearn Bayesian Network Repository", "page updated 2022-11-29", "https://www.bnlearn.com/bnrepository/", "Discrete reference networks and formats; nodes are not all Boolean variables."),
    ("S19", "Cedar policy project", "Cedar Integration Tests", "repository consulted", "https://github.com/cedar-policy/cedar-integration-tests", "Handwritten and fuzz-generated fixtures with expected decisions, reasons and errors."),
    ("S20", "Cedar policy project", "Cedar implementation", "repository consulted", "https://github.com/cedar-policy/cedar", "Native authorization engine and symbolic compiler; finite propositional extraction is a new adapter."),
    ("S21", "Open Policy Agent", "Policy Performance", "documentation consulted", "https://www.openpolicyagent.org/docs/policy-performance", "Compiled/prepared evaluation and benchmark practices for the native incumbent."),
    ("S22", "ClassBench-ng maintainers", "ClassBench-ng", "repository consulted", "https://github.com/classbench-ng/classbench-ng", "Synthetic packet-classification rule generation; generated traffic is not production traffic."),
    ("S23", "RoaringBitmap project", "Real Roaring datasets", "repository consulted", "https://github.com/RoaringBitmap/real-roaring-datasets", "Application-derived bitmap inputs; arbitrary row universes differ from assignment spaces."),
    ("S24", "RoaringBitmap project", "CRoaring", "repository consulted", "https://github.com/RoaringBitmap/CRoaring", "Native compressed and conventional bitmap comparator."),
    ("S25", "AFF3CT project", "Configuration files", "repository consulted", "https://github.com/aff3ct/configuration_files", "LDPC parity-check configuration source; verify each file's H/G identity and terms."),
    ("S26", "Albrecht, Bard and M4RI contributors", "M4RI", "repository consulted", "https://github.com/malb/m4ri", "Dense exact GF(2) arithmetic comparator."),
    ("S27", "Soos and CryptoMiniSat contributors", "CryptoMiniSat", "repository consulted", "https://github.com/msoos/cryptominisat", "CNF/XOR SAT and Gaussian elimination support."),
    ("S28", "PySAT project", "SAT solvers API", "1.9.dev15 documentation", "https://pysathq.github.io/docs/html/api/solvers.html", "Incremental assumptions and native solver bindings; exact availability must be probed."),
    ("S29", "Biere and CaDiCaL contributors", "CaDiCaL releases", "releases consulted", "https://github.com/arminbiere/cadical/releases", "Native CDCL SAT comparator; freeze tested version."),
    ("S30", "Biere and Kissat contributors", "Kissat", "repository documentation consulted", "https://github.com/arminbiere/kissat/blob/master/README.md?plain=1", "Native SAT comparator; one-shot and incremental capabilities must not be conflated."),
    ("S31", "CUDD maintainers", "CUDD", "repository consulted", "https://github.com/cuddorg/cudd", "Native BDD/ADD/ZDD implementation; verify counting API precision."),
    ("S32", "Sylvan maintainers", "Sylvan", "repository consulted", "https://github.com/trolando/sylvan", "Multicore decision diagrams; separate thread-count lanes."),
    ("S33", "CRIL", "d4v2", "repository consulted", "https://github.com/crillab/d4v2", "Counting library with CNF and circuit input; CLI differs from other d4 releases."),
    ("S34", "Meel Group and Ganak contributors", "Ganak", "repository consulted", "https://github.com/meelgroup/ganak", "Default probabilistic mode versus --prob 0; verify pinned binary and disable approximation fallback for exact lane."),
    ("S35", "Berkeley ABC project", "ABC", "repository consulted", "https://github.com/berkeley-abc/abc", "Native synthesis and equivalence comparator; transformations need verified semantics."),
    ("S36", "SMT-LIB initiative", "SMT-LIB Benchmarks", "current index consulted", "https://smt-lib.org/benchmarks.shtml", "QF_BV application inputs; encoding/solver semantics require separate admission."),
    ("S37", "Potassco", "aspcud", "repository consulted", "https://github.com/potassco/aspcud", "Package dependency solving; feasibility differs from optimized upgrade selection."),
    ("S38", "Z3 contributors", "Z3", "repository consulted", "https://github.com/Z3Prover/z3", "SMT comparator for original bit-vector contracts."),
    ("S39", "Runpod", "Pod pricing", "current documentation consulted", "https://docs.runpod.io/pods/pricing", "Live quote required; compute and continuing storage charges."),
    ("S40", "Runpod", "Storage options", "current documentation consulted", "https://docs.runpod.io/pods/storage/types", "Container/volume/network persistence and retrieval before termination."),
    ("S41", "Runpod", "CPU types", "current documentation consulted", "https://docs.runpod.io/references/cpu-types", "Host CPU diversity; inventory is not a reservation or a CPU-only SKU guarantee."),
    ("S42", "IWLS 2026 contest maintainers", "Logic synthesis contest", "2026", "https://github.com/alanminko/iwls2026-ls-contest/", "Already-materialized truth tables; synthesis and query tests only, not AST-to-table timing."),
]

GROUPS = {
    "H": "Hardware and logic design", "F": "Configuration and feature models",
    "C": "SAT, counting and verification", "B": "Biology, reliability and probability",
    "P": "Policies and data filtering", "A": "Affine logic and coding",
    "S": "Synthetic mechanism and boundary tests", "L": "Lifetime and delivery tests",
    "Y": "SymPy and representation controls",
}

# id, priority (1=first campaign, 2=next, 3=exploratory), provenance,
# tasks, scale profile, source ids, name, concrete test, fairness/admission requirement.
ROWS = [
("H01",1,"application_derived","T1,T2,T5","explicit","S02","EPFL arithmetic cones","Select adder, multiplier, divider, square-root and other arithmetic roots by a fixed hash within width strata.","Root/cone importer available in prior work; deduplicate designs and retain full-cone failures. A cut boundary is a derived abstraction."),
("H02",1,"application_derived","T1,T2,T5","explicit","S02","EPFL control cones","Sample arbiter, router, voter, decoder and other control functions independently of timings.","Keep whole-design cluster identities; expose all tested roots, including constants and low-support roots."),
("H03",2,"legacy_benchmark","T1,T2,T5","explicit","S05,S08","ISCAS85 combinational logic","Use the canonical combinational circuits and stratified output cones from an attributed distribution.","Verify original provenance and per-file terms through IWLS/LogikBench lineage; historical engineering benchmarks are not traffic traces."),
("H04",2,"legacy_benchmark","T1,T2,T3","native_plus_explicit","S05,S08","ISCAS89 one-step logic","Extract combinational next-state/output functions with current state explicitly declared as inputs.","One step does not establish reachability or sequential equivalence; initial-state assumptions must be recorded."),
("H05",2,"application_derived","T1,T2,T5","native_plus_explicit","S05","IWLS2005 design suite","Sample designs and combinational cones across gate count, depth and reconvergence.","Deduplicate shared ISCAS/ITC/OpenCores ancestry; do not count suite repackaging as new systems."),
("H06",2,"application_derived","T1,T2,T5","native_plus_explicit","S06,S08","VTR and Koios designs","Select independent accelerator/control designs, then freeze bit-level cones and output groups.","Elaboration, memories, signedness and sequential boundaries need verified import; neural accelerator hardware is not a neural inference benchmark."),
("H07",1,"application_derived","T1,T2,T5","native_plus_explicit","S07","Yosys large designs","Use benchmarks_large designs unused in previous confirmation; retain synthesis and source identities.","Check elaboration against Yosys/ABC; preserving sharing is required in CM and CSE-flat alike."),
("H08",1,"synthetic_model","T1,T2,T5","explicit","S07","Yosys small mechanisms","Use benchmarks_small arithmetic, mux and gate tests to isolate depth and sharing effects.","Upstream calls these mostly synthetic; retain that label and do not combine their weighting with real designs."),
("H09",1,"derived_transformation","T5,T8","native_plus_explicit","S02,S35","Original versus synthesized equivalence","Compare original/ABC-rewritten circuits and controlled one-gate mutations; return equivalent status or exact difference count.","Equivalent pairs must be certified and mutations may be semantically masked; count only verified non-equivalent pairs as negatives."),
("H10",1,"application_derived","T1,T2,T4","explicit","S02,S06","Multi-output shared evaluation","Request 1, 4, 16 and 64 outputs from one design, with one union basis and declared order.","All methods may share intermediates across roots; charge the sum of output bytes and multi-root preparation."),
("F01",1,"application_derived","T3,T4,T5","native_plus_explicit","S03","Linux configuration formulas","Select independent releases and whole models, plus separately labeled bounded residuals.","Original features and auxiliaries must be mapped; arbitrary clause deletion is not a valid residual."),
("F02",1,"application_derived","T3,T4,T5","native_plus_explicit","S03,S04","BusyBox version histories","Use chronological versions and partial configurations; return feasibility, count and changed-product queries.","Split by system/history rather than rows; old consumed versions are regression evidence, not fresh confirmation."),
("F03",2,"application_derived","T3,T4,T5","native_plus_explicit","S03","uClibc and Fiasco configurations","Sample both systems and preserve source feature mappings and previously found counterexamples.","Full-CNF counts are separate from projected product counts; reject unsupported source semantics explicitly."),
("F04",2,"application_derived","T3,T4","native_plus_explicit","S03,S04","eCos/CDL configurations","Use available attributed Boolean models and natural component boundaries.","CDL attributes and non-Boolean constructs require a documented Boolean interpretation or refusal."),
("F05",1,"application_derived","T3,T4,T5","native_plus_explicit","S03,S04","Automotive and financial product models","Select one or more models per independent product family, including finance history where available.","A model's domain label does not prove deployed use; preserve obfuscation and conversion metadata."),
("F06",1,"mixed_repository","T1,T3,T4","explicit","S04","Small SPLOT/UVL models","Start with complete small models, stratified by hierarchy depth, constraints and valid-product density.","SPLOT contains community examples and synthetic models; classify origin individually and deduplicate other repositories."),
("F07",2,"application_derived","T3,T4,T5","native_plus_explicit","S04","Smartwatch product evolution","Compare available Mi Band model versions and reduced/realized/planned configurations.","These model kinds have different intended semantics; compare like kinds over time and preserve release ancestry."),
("F08",1,"modeled_queries_on_real_inputs","T4","query","S03,S04","Interactive configurator sessions","Generate backtracking, contradictory selections and correlated partial assignments over real product models.","Call modeled sessions synthetic unless an operator supplies real interactions; every method gets the same assumptions and reuse."),
("F09",1,"application_derived","T3,T4","native_plus_explicit","S03,S28","Dead, core and optional features","Return complete status vectors from repeated SAT assumptions and count-based checks where admitted.","Incremental native SAT keeps learned clauses; cache query results and report total feature-analysis time."),
("F10",1,"application_derived","T3,T4","projection","S03,S11","Projected feature-product counts","Count distinct concrete configurations after existential auxiliary elimination; include empty projection and unused features.","Projection-capable CM is reported in a separate checkout: locate and freeze it before admission; verify original conversion, not only DIMACS semantics."),
("C01",2,"mixed_repository","T3","symbolic","S09,S28,S29,S30","Application SAT and UNSAT","Use a family-balanced subset of the SAT competition with descriptions, both outcomes, and unmodified whole inputs.","Native CDCL is mandatory. CM explicit refusal is a result; whole industrial CNFs can greatly exceed 32 variables."),
("C02",2,"legacy_benchmark","T3,T4","symbolic","S10","SATLIB planning","Select bounded planning encodings and assumption queries across horizons.","Solving one horizon is not an optimal planner; retain temporal semantics and decoder checks for returned plans."),
("C03",2,"synthetic_model","T3,T4","symbolic","S10","SATLIB graph coloring","Use flat/morphed graph-coloring CNFs across densities; separately generate small exactly checked graphs.","Color bits and auxiliary counts differ from graph vertices; projected coloring counts must handle color symmetries explicitly."),
("C04",1,"mixed_repository","T3,T4","symbolic","S11,S12,S33,S34","Unweighted model counting competition","Freeze a family-balanced selection from stable releases, retaining easy and hard application classes separately.","Exact arbitrary-precision answers, declared unused variables and independent counters required; hard competition selection is not typical traffic."),
("C05",2,"mixed_repository","T3,T4","projection","S11,S12,S34","Projected model counting competition","Use published projection sets and vary assumptions only in a separate modeled-query panel.","Do not replace projected count with total CNF count; use deterministic exact mode and verify adapter support."),
("C06",3,"mixed_repository","T9","weighted","S11,S12,S34","Weighted model counting","Use rational-weight instances and defined evidence queries from archived weighted tracks.","CM weight support is a new capability gate; exact, approximate and floating-tolerance results get different scoreboards."),
("C07",3,"application_derived","T3","symbolic","S37","Package dependency feasibility","Import attributed CUDF examples or operator-provided package requests, checking installability and returned package sets.","aspcud optimization includes preferences; benchmark feasibility alone unless every arm returns the same certified optimum."),
("C08",3,"application_derived","T3,T5","symbolic","S36,S38","SMT-LIB QF_BV circuits","Choose bit-vector cases; evaluate original SMT with Z3 and a checked Boolean translation with SAT/CM.","Charge bit-blasting; word width is not total Boolean width; signedness, overflow, shifts and zero-division semantics must match."),
("B01",1,"application_derived","T1,T2","explicit","S13,S14","Biological update-function tables","Extract each model's regulator update functions and request complete local truth vectors.","Network size and local in-degree differ; preserve source/free-input conventions and Booleanization metadata."),
("B02",2,"application_derived","T2","batch_rows","S13,S15","Synchronous Boolean-network simulation","Evaluate all node updates for the same batches of initial states and fixed step counts.","All nodes read the old state; full transition relations contain current and next-state variables and are a different task."),
("B03",2,"application_derived","T3","native_plus_explicit","S13,S15","Biological fixed points","Solve conjunctions of each state variable equal to its update function; return count/status/witness in separate cells.","Compare with AEON/native SAT; fixed points are not all attractors, and asynchronous dynamics require a separate implementation."),
("B04",1,"modeled_queries_on_real_inputs","T4","query","S13,S15","Perturbation and knockout contexts","Apply fixed-variable knockout/overexpression contexts and evaluate or count the same residual functions.","Retain source biological provenance without claiming clinical utility; generated perturbation order is modeled reuse."),
("B05",2,"application_derived","T1,T3,T4","native_plus_explicit","S16,S17","Static fault-tree top event","Use OpenPSA static AND/OR/NOT/k-of-n trees; compute event truth vectors, existence or counts.","Repeated basic events are the same variable; dynamic gates and common-cause semantics need separate modeling."),
("B06",3,"application_derived","T9","weighted","S16,S17","Fault-tree reliability probabilities","Use exact top-event probability under a declared independence model and evidence updates.","SCRAM exact BDD probability is the comparator; rare-event approximations and truncated cut sets are not exact answers."),
("B07",3,"reference_model","T9","weighted","S18","Small Bayesian-network inference","Start with ASIA, CANCER and EARTHQUAKE; compare evidence likelihood/marginal queries under an audited encoding.","CPTs are conditional probabilities; arbitrary Boolean counts do not implement Bayesian inference. Native elimination is mandatory."),
("B08",3,"reference_model","T9","weighted","S18","Medium Bayesian-network inference","Use CHILD, ALARM, INSURANCE and WATER after small-model conversion tests succeed.","Categorical node count is not Boolean width; preserve one-hot constraints and exact/tolerance contract, including zero-probability evidence."),
("P01",2,"application_fixture","T2,T4","query","S19,S20","Cedar authorization examples","Use handwritten policies with expected decisions and request contexts; retain an admitted finite Boolean subset.","Preserve forbid precedence, entity membership, missing fields and errors; compare native prepared Cedar as well as cold parsing."),
("P02",3,"synthetic_fuzz","T2,T4","query","S19","Cedar fuzz corpus","Use a fixed sample of upstream generated cases for adapter differential correctness and repeated-request tests.","Corpus generation targets code coverage, not production frequencies; unsupported/error cases cannot silently become deny."),
("P03",3,"application_fixture","T2,T4","query","S21","OPA policy evaluation","Select documented Boolean policy fragments and benchmark raw, prepared and compiled incumbent paths.","Rego collections, undefined values and external lookups are not free Boolean atoms; charge extraction and preserve result semantics."),
("P04",3,"synthetic_model","T2,T4","batch_rows","S22","Packet-classification rules","Generate fixed ClassBench seeds and packet batches; return the first matching action or permitted-set artifact.","Preserve rule order and default action; full packet bit widths generally exceed explicit-table limits."),
("P05",3,"application_derived","T10","batch_rows","S23,S24","Roaring bitmap query expressions","Run intersections, unions, differences and shared multi-output expressions on real bitmap datasets.","Rows are arbitrary records, not all truth assignments; CM needs a verified batch evaluator. Compare CRoaring, dense words and sorted-set intersection."),
("P06",2,"synthetic_model","T2,T4","query","S19,S21","Feature flags and eligibility rule models","Generate tenant/rule hierarchies, allow/deny conflicts and correlated request attributes with declared distributions.","Distinguish primitive predicate extraction from Boolean combination and include a compiled native/short-circuit evaluator."),
("A01",1,"application_derived","T7,T3","affine","S25,S26","LDPC parity-check feasibility and count","Use verified parity-check matrices; vary syndrome and erasure/fixed-bit contexts.","H matrices differ from generators; compare packed elimination and M4RI. Counting solutions is not error-correction decoding performance."),
("A02",1,"synthetic_model","T7,T3","affine","S26,S27","CRC/LFSR linear constraints","Generate pinned polynomials, bit ordering and observed-output constraints; return rank, consistency and exact count.","Pure affine formulas favor algebraic solvers; identify generic GF(2) benefits separately from CM representation benefits."),
("A03",2,"synthetic_model","T7,T3","affine","S26","Structured dense/sparse GF(2)","Sweep dimensions, density, rank deficiency, duplicate rows and contradictions with planted exact ranks.","Dense M4RI and Python packed elimination get the same native rows; AST-to-row conversion is separately charged."),
("A04",2,"synthetic_model","T1,T3","native_plus_explicit","S27","Mixed XOR/CNF cryptographic models","Combine parity layers with nonlinear gates; sweep XOR density and nonlinear count using published generator specifications.","These are cryptography-inspired models, not a claim to break real ciphers; include CryptoMiniSat native XOR support."),
("A05",2,"synthetic_model","T7","explicit","S01,S26","Complete ANF versus rank-only queries","Request full ANF coefficients or a declared rank/decomposition artifact from the same truth functions in distinct lanes.","ANF transform, rank and full decomposition have different outputs; include every transform/conversion and exact artifact verification."),
("A06",2,"application_derived","T4,T7","affine","S25,S26","Repeated syndrome sessions","Keep a parity-check system fixed while processing distinct RHS values, fixed bits and selected revisions.","Incumbents may reuse factorization; identical-result memoization and changed matrix versions must be represented fairly."),
("S01",1,"synthetic_control","T1,T2,T3","explicit","S01","Constants, literals and absent variables","Cover true/false, literals, tautologies and unused ambient variables with analytic counts.","Unused basis variables multiply counts; a large declared basis with tiny support is its own stratum."),
("S02",1,"synthetic_model","T1,T2","explicit","S07","Balanced versus deep expression trees","Match operator counts and effective support while varying depth, fan-in and recursion exposure.","Match nodes rather than nominal generator depth; use independently proved live-variable controls."),
("S03",1,"synthetic_model","T1,T2","explicit","S02","Shared DAG versus duplicated tree","Generate controlled sharing factors with identical semantics and expose repeated subgraphs.","Include raw recursion, memoization and CSE-flat ladder; a sharing win alone is not CM-specific."),
("S04",1,"synthetic_control","T1,T3","explicit","S27","Parity and equivalence chains","Generate all-live parity/equivalence functions at each explicit width with known counts.","Native XOR/CDCL and GF(2) are strong scalar baselines; constants from accidental cancellation must be detected."),
("S05",1,"synthetic_model","T1,T2,T3","explicit","S07,S28","Cardinality and voting rules","Generate at-most, exactly and at-least thresholds, including boundary thresholds.","Use combinatorial binomial counts as an oracle; retain encoding size and auxiliaries for sequential/totalizer controls."),
("S06",1,"synthetic_model","T1,T2","explicit","S07","Multiplexers and selectors","Vary address bits, data bits, sharing and variable order with a stable selection definition.","Total input width includes address and data; compare BDD natural, interleaved and dynamic orders with ordering costs."),
("S07",1,"synthetic_model","T1,T3,T5","explicit","S02,S07","Arithmetic Boolean functions","Use adders, comparators and selected multiplier bits; record operand widths and output choice.","Two b-bit operands require up to 2b inputs; include native arithmetic for concrete-assignment tasks."),
("S08",1,"synthetic_model","T1,T3","explicit","S10","Random 3-CNF density sweep","Generate unique seeded cases across clause/variable ratios 1, 3, 4, 4.3, 5 and 8.","Balance outcomes after recording all draws; ratio 4.3 is a parameter, not a proved threshold for every small n."),
("S09",1,"synthetic_model","T3,T4","native_plus_explicit","S10,S28","Horn and 2-CNF controls","Sweep implication graphs, satisfiable/unsatisfiable cases and partial contexts.","Include specialized linear-time SAT controls; easy status does not imply easy model counting."),
("S10",1,"synthetic_model","T3,T4","symbolic","S11","Independent components","Compose disjoint small factors while increasing total variables to 64, 128, 256 and beyond.","Compare factorized counts with native counters and product-of-counts control; never expand the full state space unnecessarily."),
("S11",1,"synthetic_model","T3,T4","symbolic","S11,S33","Overlap and elimination-width ladder","Generate chains, cycles, grids and hub/star CNFs with matched counts of variables/clauses where possible.","Record measured induced width and ordering cost; include deliberately hostile elimination orders and refusals."),
("S12",1,"synthetic_control","T3,T4","projection","S11,S12","Auxiliary/projection correctness traps","Create unique-extension gates, nonunique auxiliaries, empty projections and unused selected variables.","E.g. a true visible variable plus a free hidden variable has total count 2 but projected count 1; this must not be conflated."),
("S13",1,"synthetic_control","T1,T3,T5","explicit","S01","Rewrite and equivalence adversaries","Use absorption, De Morgan, double negation, XOR cancellation and masked mutations with certified outcomes.","All exact methods may exploit simplification; include unchanged negative controls and failed mutation attempts."),
("S14",2,"synthetic_model","T1,T3","explicit","S31","BDD variable-order sensitivity","Construct paired equality and multiplexer families in grouped/interleaved/random orders.","Charge reorder/search cost; do not report the worst BDD order as its sole comparator or oracle-best order as a deployable selector."),
("S15",2,"synthetic_model","T1,T10","explicit","S24","Output density and runs","Sweep sparse, dense, clustered and alternating outputs on declared finite universes.","Dense versus compressed artifacts must be normalized or scored by a downstream task; complements mask unused high bits."),
("S16",1,"synthetic_control","T1,T3,T6","explicit_large","S02","True 24-32-variable frontier","Construct certified all-live instances at 20, 24, 28, 30 and 32; add a separate low-support ambient ladder.","Use resource preflight, complete packed/stream verification and independent variable-influence checks; sampled equality alone is provisional."),
("L01",1,"modeled_lifecycle","T4","query","S28,S31","Cold versus resident amortization","Measure Q=1,2,4,8,16,64,256,1024 distinct queries with setup charged once per session.","Include cached-result lookup for identical queries and native incumbent preparation reuse; model Q is not observed production Q."),
("L02",1,"modeled_lifecycle","T4","query","S21,S24","Cache pressure and eviction","Use uniform and Zipf-like accesses, working sets below/above capacity, renaming and basis changes.","Hold byte budgets equal, account for caller-held references, and label synthetic traffic explicitly."),
("L03",2,"modeled_lifecycle","T4,T5","query","S03,S07","Version invalidation","Replay genuine source versions with separately modeled query arrivals and occasional no-op edits.","Version history does not reveal query frequency; frozen chronological holdout and independent result checks required."),
("L04",1,"modeled_lifecycle","T4","query","S39,S40","Fresh process and structural reload","Compare resident plans, new engines, fresh processes and checked artifact reloads for identical sessions.","Include imports, dynamic library load, preparation, deserialization and first query; native persistence gets equal opportunity."),
("L05",1,"modeled_delivery","T6","explicit_large","S40","Complete streaming to real sinks","Deliver ordered packed bytes to file, pipe and slow-reader sinks; sweep 8KiB,64KiB,1MiB,8MiB chunks.","Measure final consumer completion, cancellation and backpressure; lazy iterator creation is not complete evaluation."),
("L06",2,"modeled_load","T2,T4","query","S32","Concurrency and workspace isolation","Use 1,2,4,8 workers on independent/shared plans with memory pressure and deterministic results.","Verify private mutable scratch, matched CPU quotas, no GIL asymmetry hidden in claims, and no oversubscribed timing lane."),
("L07",2,"modeled_load","T4,T6","query","S40","Long soak, recovery and refusal","Run bounded sessions with cancellations, refused widths, resource exhaustion and process restarts.","Record leak trends, successful-work throughput and every lost request; a soak is engineering evidence rather than an algorithm speedup."),
("L08",2,"production_trace_pending","T2,T4,T6","query","S19,S21","Independent consumer trace","Capture an already-used caller's natural queries, lifetimes, revisions and consumed outputs.","Owner and trace admission required; local metadata-only sampling precedes authorized exact replay. This is the production-savings claim lane."),
("Y01",1,"historical_replay","T8","small","S01","Reconstruct archived SymPy comparison","Replay the historical formulas and pinned source when recoverable; report old timer boundaries and current equivalents.","Historical labels are not trusted as task parity; unrecoverable source/formulas remain unverified and are not regenerated as exact replays."),
("Y02",1,"api_baseline","T1","small","S01","SymPy truth_table API","Fully consume truth_table(..., input=False) into the agreed packed result on small widths.","Include SymPy conversion and generator consumption; narrow per-cell timeouts prevent tiny controls dominating the campaign."),
("Y03",1,"api_baseline","T2","batch_rows","S01","SymPy lambdify evaluation","Compile Boolean expressions to NumPy callable and evaluate identical assignment batches; compare cse on/off.","Charge callable compilation/JIT where relevant and normalize constants/scalars; do not include simplification unless requested."),
("Y04",1,"api_baseline","T3,T5","small","S01,S28","SymPy SAT and equivalence","Use satisfiable(F) and satisfiable(XOR(F,G)); compare status or witness against native SAT and CM.","An unevaluated simplify_logic result is unknown for proof purposes; failure to simplify to false does not establish non-equivalence."),
("Y05",2,"api_baseline","T8","small","S01","SymPy simplified SOP/POS","Request simplified SOP/POS from fixed small formulas; compare alternative simplification pipelines under equivalence checks.","CM alone has no matched minimizer here; CM plus the same minimizer is a pipeline arm. Report quality/runtime, not a full-table speed ranking."),
("Y06",2,"api_baseline","T8","small","S01,S35","Espresso and synthesis quality","Use Boolean cover/logic synthesis tasks with equivalent output, literal/gate count, and runtime.","Heuristic and exact minimization are separate guarantees; input preparation and truth-table conversion are charged symmetrically."),
("Y07",2,"artifact_fixture","T8,T4","explicit","S42","IWLS2026 published truth tables","Use already-materialized tables for representation loading, queries and a separate logic-synthesis study.","There is no AST-to-table construction to time; undisclosed function origins do not establish application provenance."),
("Y08",1,"mechanism_ablation","T1,T2,T3","explicit","S02,S31","CM contribution ladder","Compare raw AST, memoized AST, CSE-flat, CM IR, optimized packed masks and the same scalar algorithm from raw versus CM ingress.","Give shared optimizations to every eligible arm. Attribute a gain to the smallest changed mechanism that explains it."),
]

TASKS = {
 "T1": "Complete ordered packed truth vector over a declared basis; full consumption required.",
 "T2": "Evaluation of specified concrete assignments/batches; return matching bits or output tuples.",
 "T3": "Scalar status, witness, ordinary count or projected count; each output subtype is a distinct cell.",
 "T4": "Session of explicitly typed queries; same ordered answers, preparation/cache lifetime and inputs.",
 "T5": "Equivalence status, counterexample or exact semantic-difference count; separate output subtypes.",
 "T6": "Complete ordered byte stream to a declared real sink, or explicitly declared cancellation prefix.",
 "T7": "Exact GF(2) rank, consistency, solution count, basis or full decomposition; separate subtypes.",
 "T8": "Simplified expression, synthesis artifact or historical boundary audit; quality guarantee explicit.",
 "T9": "Weighted count/probability under specified arithmetic, projection and error guarantees.",
 "T10": "Boolean set/bitmap query over arbitrary row IDs; distinct universe from complete assignments.",
}
SCALES = {
 "small": "2,4,6,8; 10/12 only after timeout calibration; never force exponential minimization blindly to 32.",
 "explicit": "4,8,12,16,20,24,28,32 active/output variables when supported; bridge widths 18,22,26,30 optional.",
 "explicit_large": "20,24,28,30,32 with verified output/working-set admission and bounded complete streaming.",
 "native_plus_explicit": "Whole source models at native size; explicit outputs only within admitted basis/byte limits; residuals separately labeled.",
 "symbolic": "Whole input sizes including 32,64,128,256,1024+ variables where native algorithms and limits allow; no full expansion requirement.",
 "projection": "Record total, visible and hidden widths independently; visible 8,12,16,20,24,28,32 plus whole-model scalar cases.",
 "weighted": "Small audited encodings first; advance by encoded variables, factor width and arithmetic cost, not original node count.",
 "affine": "16,32,64,128,256,512,1024,4096 columns when limits allow; independently vary rows, rank and density.",
 "query": "Q=1,2,4,8,16,64,256,1024; then observed trace Q. State width follows underlying input and resource limits.",
 "batch_rows": "8-128+ predicates; 1,32,1024,65536,1048576 actual rows/assignments where appropriate; rows are not 2^predicates.",
}
CONTROLS = {
 "T1": "CM full wrapper; optimized BitSet; sharing-aware CSE-flat; native/tiled words if verified; CUDD including full extraction; small SymPy table control.",
 "T2": "Compiled direct/short-circuit evaluator; SymPy lambdify/NumPy; CSE-flat batch; admitted CM lookup/batch; relevant native application engine.",
 "T3": "SAT: CaDiCaL/PySAT, Kissat one-shot, CryptoMiniSat for XOR. Counts: exact CUDD, d4, Ganak --prob 0, admitted CM scalar plans; projection capability checked.",
 "T4": "Same task-specific controls with equivalent preparation, result caches, query assumptions, version invalidation and memory budgets.",
 "T5": "SAT/ABC miter for status; packed XOR-popcount or exact projected counter for delta counts; CM matched output only.",
 "T6": "CM and CSE-flat tiled stream plus complete-output delivery control; all methods include producer and final consumer costs.",
 "T7": "Python packed Gaussian elimination; native M4RI; current CM-associated affine/decomposition path with all conversion charged.",
 "T8": "SymPy simplify_logic explicit options; Espresso/ABC as suitable for declared quality; CM pipeline only if output guarantee is implemented.",
 "T9": "Exact native counter/BDD weighted evaluation or native Bayesian/fault-tree engine; CM extension only after capability and precision validation.",
 "T10": "CRoaring, dense words/bigint and sorted-list controls; CM/CSE batch adapter only after verifying arbitrary-row semantics.",
}

def emit(name: str, value: object) -> None:
    # Only this builder's known derived output files are overwritten on a rerun.
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    (HERE / name).write_text(text, encoding="utf-8")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    sources = [dict(id=r[0], publisher=r[1], title=r[2], edition_or_date=r[3], url=r[4], use=r[5],
                    accessed=DATE, verification="primary_page_consulted", dataset_downloaded_by_this_package=False,
                    frozen_revision=None, file_license_verified=False) for r in SOURCE_ROWS]
    source_ids = {s["id"] for s in sources}
    tests = []
    for rid, priority, provenance, tasks, scale, src, name, test, caveat in ROWS:
        ids = src.split(",")
        ts = tasks.split(",")
        assert set(ids) <= source_ids and set(ts) <= TASKS.keys() and scale in SCALES
        tests.append(dict(id=rid, group=GROUPS[rid[0]], priority=priority, provenance=provenance,
                          tasks=ts, scale_profile=scale, sources=ids, name=name, proposed_test=test,
                          fairness_and_admission=caveat, status="recommended_not_executed",
                          frozen_input_count=0, performance_claim=None))
    assert len(tests) == 80 and len({t["id"] for t in tests}) == 80
    catalog = dict(schema="cm-comprehensive-benchmark-catalog/v1", research_date=DATE,
                   interpretation="80 proposed test families, not 80 independent corpora or executed benchmarks",
                   tasks=TASKS, scale_profiles=SCALES, required_controls=CONTROLS, tests=tests)
    emit("CATALOG.json", catalog)
    emit("SOURCES.json", sources)
    base = HERE.as_posix()
    docs = ["# Comprehensive benchmark catalog\n",
            "These 80 test families are recommendations. Source descriptions are cited facts; test designs, sizes and priorities are proposed experiments. None is an executed result. A family may have several task cells, and several families may share one upstream corpus.\n",
            "Priority 1 is the initial campaign pool, priority 2 is the next pool, and priority 3 requires a larger adapter or a new capability. Selection into the first funded run is separately frozen in CAMPAIGN_PLAN.json.\n",
            "All source links refer to upstream material consulted for this report. Dataset downloads, file hashes and per-file licensing remain acquisition work.\n",
            "## Task contracts\n"]
    docs.extend(f"- **{k}:** {v}\n" for k,v in TASKS.items())
    docs.append("\n## Scale profiles\n")
    docs.extend(f"- **{k}:** {v}\n" for k,v in SCALES.items())
    docs.append("\n## Comparator rules\n")
    docs.extend(f"- **{k}:** {v}\n" for k,v in CONTROLS.items())
    lookup = {s["id"]:s for s in sources}
    for letter, group in GROUPS.items():
        docs.append(f"\n## {group}\n\n| ID / priority / origin | Test and selection | Task / scale | Fairness and work needed |\n| --- | --- | --- | --- |\n")
        for t in tests:
            if not t["id"].startswith(letter):
                continue
            links = ", ".join(f"[{sid}]({lookup[sid]['url']})" for sid in t["sources"])
            docs.append(f"| {t['id']} / P{t['priority']} / {t['provenance']} | **{t['name']}**. {t['proposed_test']} {links} | {', '.join(t['tasks'])}; {t['scale_profile']} | {t['fairness_and_admission']} |\n")
    emit("CATALOG.md", "\n".join(docs))
    source_md = ["# Sources\n", f"Sources consulted {DATE}. Editions below describe the page or release inspected. Moving repository URLs must be pinned before execution; availability here does not establish each payload's license.\n"]
    source_md.extend(f"{i}. **{s['id']}**. {s['publisher']}. [{s['title']}]({s['url']}). {s['edition_or_date']}. Used for: {s['use']}\n" for i,s in enumerate(sources,1))
    source_md.append("\nSources that could not be read sufficiently for admission: the original MacKay code-data page returned HTTP 403; speculative fault-tree/BEEM URLs were not verified; the supplied GitHub Pages homepage did not load in the web reader. The catalog uses independently accessible primary sources and local CM evidence instead.\n")
    emit("SOURCES.md", "\n".join(source_md))

    # Reaggregate an actual local historical file without importing project code.
    path = ROOT / "bench_robdd_cm_balanced_all_vars_raw.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    groups = []
    for n in sorted({int(row["n_vars"]) for row in rows}):
        paired = [r for r in rows if int(r["n_vars"]) == n and r["sympy_time_s"] and r["cm_time_s"]]
        ratios = [float(r["sympy_time_s"])/float(r["cm_time_s"]) for r in paired]
        groups.append(dict(n_vars=n, pairs=len(paired), median_of_paired_recorded_sympy_over_cm=median(ratios),
                           minimum=min(ratios), maximum=max(ratios),
                           recorded_all_correct=all(r["cm_ok"] == r["sympy_ok"] == "True" for r in paired)))
    audit_paths = ["expr_simplify.py", "cm_bench.py", "CM_AUDIT_V3_2026-07-23.md",
                   "CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md",
                   "cmbench/comparative/contracts.py", "cmbench/tracing/workload_manifest.py",
                   "docs/research/CM_SCALAR_QUERY_APIS_2026_09_11.md",
                   "docs/audits/2026-09-11-cm-next-research/REPORT.md",
                   "deliverables_n22_24/master_explainer_2026_08_03/results/2026-09-12/frontier-research-summary.json",
                   "docs/audits/2026-09-13-cm-fair-feature-model/PREPARATION.json"]
    historical = dict(schema="cm-historical-sympy-audit/v1", raw_file=path.relative_to(ROOT).as_posix(),
                      raw_sha256=sha(path), groups=groups,
                      interpretation="Recorded historical unlike-task timer ratios; not fair speedups, not rerun or reproduced performance.",
                      source_version_binding="Current inspected code explains the timer design but exact historical source/environment not independently recovered.",
                      inspected_files=[dict(path=p, sha256=sha(ROOT/p)) for p in audit_paths])
    emit("HISTORICAL_AUDIT.json", historical)
    hist = ["# Historical SymPy audit\n", "An archived file contains substantial differences in the recorded timers. These are historical observations with unlike output contracts, not a contemporary matched-task speed comparison.\n",
            f"Input: [bench_robdd_cm_balanced_all_vars_raw.csv]({path.as_posix()}); SHA-256 `{sha(path)}`.\n",
            "| Nominal variables | Paired rows | Median recorded SymPy time / CM time | Range | Recorded correctness flags |\n| ---: | ---: | ---: | ---: | --- |\n"]
    for g in groups:
        hist.append(f"| {g['n_vars']} | {g['pairs']} | {g['median_of_paired_recorded_sympy_over_cm']:.3f} | {g['minimum']:.3f}–{g['maximum']:.3f} | both true |\n")
    hist.append(f"\nThe inspected [adapter]({ROOT.as_posix()}/expr_simplify.py:39) calls `simplify_logic(..., form='dnf')` with default `force=False`. The [timer]({ROOT.as_posix()}/cm_bench.py:2239) ends before lambdify, assignment-grid evaluation and truth-vector validation. CM construction and symbolic simplification are different requested outputs. [SymPy's documentation](https://docs.sympy.org/latest/modules/logic.html#sympy.logic.boolalg.simplify_logic) describes the eight-variable default restriction; above it the same call does not perform the same exhaustive simplification. The archive's sharp n8/n12 change is consistent with that mechanism, but historical version binding has not been independently reconstructed.\n")
    hist.append(f"\nThe [August gap audit]({ROOT.as_posix()}/CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md:639) criticized these comparator choices. That document is evidence about past interpretation, not an instruction to exclude fair SymPy experiments now. Y02–Y06 propose new task-matched comparisons. No claim that SymPy cannot be used in production is supported here.\n")
    hist.append(f"\nThe [July V3 audit]({ROOT.as_posix()}/CM_AUDIT_V3_2026-07-23.md:183) also found an n32 example with semantic support 16. Its ambient-output timing survived, but its all-live interpretation did not. The new scale protocol separately records ambient variables, syntactic support, proved semantic support and output width.\n")
    emit("HISTORICAL_AUDIT.md", "\n".join(hist))

    plan = dict(schema="cm-benchmark-campaign-proposal/v1", status="research_proposal_not_launch_authorization",
                approved_budget_usd=None, approved_pod_ids=[], cloud_execution_started=False,
                proposed_dollar_cap_usd=50, proposed_pod_hour_cap=16, max_concurrent_pods=1,
                core_case_count_target=2400, explicit_widths=[4,8,12,16,20,24,28,32],
                optional_bridge_widths=[18,22,26,30], query_counts=[1,2,4,8,16,64,256,1024],
                allocations={"hardware":600,"feature_models":400,"biological_functions":300,
                             "sat_and_counting":300,"affine":200,"synthetic_mechanisms":600},
                first_pool_ids=["H01","H02","H07","H08","H09","H10","F01","F02","F05","F06","F08","F09","F10",
                                "B01","B04","C04","A01","A02"] + [f"S{i:02}" for i in range(1,17)] + ["Y01","Y02","Y03","Y04","Y08","L01","L02","L04","L05"],
                phased_pod_hours={"environment_and_probe":2,"broad_screen":4,"confirmation_and_large_width":6,
                                  "second_host_replication":3,"retrieval_and_cleanup_reserve":1},
                default_limits={"input_bytes":16<<20,"worker_memory_bytes":4<<30,"worker_wall_seconds":60,
                                "large_worker_memory_bytes":48<<30,"large_worker_wall_seconds":300,
                                "exploratory_hard_cell_wall_seconds":900,"normal_output_bytes":64<<20,
                                "frontier_output_bytes":512<<20,"explicit_masks_fraction_of_cgroup_memory":0.60},
                primary_effect="paired session total time ratio CM / preselected strong comparator, within task/corpus/lifecycle/host",
                proposed_practical_gate={"ratio_at_most":0.95,"ci95_upper_below":1.0,"confirmation":"fresh held-out source groups and second host for generalized claims"},
                stop_policy="Stop admission when time/dollar reserve insufficient; retain planned/not-run cells, refusals, timeouts, errors and mismatches.",
                run_mode="Core and admitted extensions only. This is not an all-80-family full Cartesian product.",
                required_before_paid_launch=["verified source/input freeze and exact adapter contracts","successful bounded local capability checks",
                                             "live hardware/rate quote","explicit campaign budget and upload scope authorization"])
    assert sum(plan["allocations"].values()) == 2400
    assert set(plan["first_pool_ids"]) <= {t["id"] for t in tests}
    emit("CAMPAIGN_PLAN.json", plan)
    validation = dict(schema="cm-research-package-validation/v1", status="pass", test_families=len(tests),
                      groups=dict(Counter(t["group"] for t in tests)), sources=len(sources),
                      duplicate_ids=0, broken_source_references=0, invalid_task_references=0,
                      historical_pairs=sum(g["pairs"] for g in groups), proposed_base_cases=2400,
                      note="Static package and historical arithmetic validation only; no new performance tests or cloud operations.")
    emit("VALIDATION.json", validation)
    print(json.dumps(validation, indent=2))

if __name__ == "__main__":
    main()
