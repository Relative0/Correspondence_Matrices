# Sources

Sources consulted 2026-09-13. Editions below describe the page or release inspected. Moving repository URLs must be pinned before execution; availability here does not establish each payload's license.

1. **S01**. SymPy development team. [Logic documentation](https://docs.sympy.org/latest/modules/logic.html). 1.14.0 documentation. Used for: Simplification limit, truth-table and SAT APIs.

2. **S02**. EPFL / LSILS. [Combinational benchmark suite](https://github.com/lsils/benchmarks). 2015 suite; repository consulted. Used for: Arithmetic and control circuits; preserve upstream design and revision identities.

3. **S03**. SoftVarE Group. [Feature-Model Benchmark](https://github.com/SoftVarE-Group/feature-model-benchmark). SPLC 2024 dataset; repository consulted. Used for: Real feature-model collection, formats, domains and histories.

4. **S04**. DiversoLab and collaborators. [UVLHub](https://www.uvlhub.io/). 2024 repository paper; current portal consulted. Used for: SPLOT, BusyBox, finance and smartwatch model datasets; provenance varies by model.

5. **S05**. IWLS organizers. [IWLS 2005 Benchmarks](https://iwls.org/iwls2005/benchmarks.html). 2005. Used for: Public sequential/combinational synthesis benchmark acquisition source.

6. **S06**. Verilog-to-Routing project. [Benchmarks documentation](https://docs.verilogtorouting.org/en/latest/vtr/benchmarks/). 9.0.0-dev documentation. Used for: VTR benchmark suites; select at design level, preserve upstream origin.

7. **S07**. YosysHQ. [yosys-bench](https://github.com/YosysHQ/yosys-bench). repository consulted. Used for: Explicit distinction between mostly synthetic small and real-design large suites.

8. **S08**. Zero ASIC. [LogikBench Koios benchmark provenance](https://github.com/zeroasiccorp/logikbench/blob/main/logikbench/benchmarks/koios/README.md). repository consulted. Used for: Vendored suite provenance and VTR origin; overlapping copies are not independent data.

9. **S09**. SAT Competition organizers. [SAT Competition 2025 benchmarks](https://satcompetition.github.io/2025/benchmarks.html). 2025. Used for: SAT competition acquisition entry; freeze actual file list and descriptions.

10. **S10**. Holger Hoos and Thomas Stutzle / SATLIB. [SATLIB Benchmark Problems](https://www.cs.ubc.ca/~hoos/SATLIB/benchm.html). historical archive. Used for: Planning, graph coloring, parity and random CNF test families.

11. **S11**. Model Counting Competition organizers. [Public Resources](https://mccompetition.org/past_iterations.html). 2020-2025 archive consulted. Used for: Counting dataset releases; 2025 links are explicitly labeled draft.

12. **S12**. Model Counting Competition organizers. [2025 competition description](https://mccompetition.org/2025/mc_description.html). 2025. Used for: Separate counting/projection/weight tracks, precision categories, limits and hard-instance selection.

13. **S13**. Pastva and Biodivine collaborators. [Biodivine Boolean Models](https://github.com/sybila/biodivine-boolean-models). repository consulted. Used for: Biological model sources, free input convention and Booleanized multivalued models.

14. **S14**. Samuel Pastva. [Biodivine Boolean Models; Edition 2022](https://zenodo.org/records/8020309). Zenodo record created 2023-06-09. Used for: Stable release with 212 published models; bnet archive is small enough for a first import.

15. **S15**. Biodivine project. [AEON.py](https://github.com/sybila/biodivine-aeon-py). repository consulted. Used for: Native symbolic Boolean-network comparator and formats.

16. **S16**. OpenPRA project. [Benchmarking Tool](https://docs-dev.openpra.org/guides/benchmarking.html). documentation consulted. Used for: Fault-tree OpenPSA models, exact probability and approximate/minimal-cut-set distinctions.

17. **S17**. SCRAM project. [SCRAM](https://github.com/rakhimov/scram). repository consulted. Used for: Fault-tree analysis implementation; use supported static Boolean subset and audited fixtures.

18. **S18**. Marco Scutari. [bnlearn Bayesian Network Repository](https://www.bnlearn.com/bnrepository/). page updated 2022-11-29. Used for: Discrete reference networks and formats; nodes are not all Boolean variables.

19. **S19**. Cedar policy project. [Cedar Integration Tests](https://github.com/cedar-policy/cedar-integration-tests). repository consulted. Used for: Handwritten and fuzz-generated fixtures with expected decisions, reasons and errors.

20. **S20**. Cedar policy project. [Cedar implementation](https://github.com/cedar-policy/cedar). repository consulted. Used for: Native authorization engine and symbolic compiler; finite propositional extraction is a new adapter.

21. **S21**. Open Policy Agent. [Policy Performance](https://www.openpolicyagent.org/docs/policy-performance). documentation consulted. Used for: Compiled/prepared evaluation and benchmark practices for the native incumbent.

22. **S22**. ClassBench-ng maintainers. [ClassBench-ng](https://github.com/classbench-ng/classbench-ng). repository consulted. Used for: Synthetic packet-classification rule generation; generated traffic is not production traffic.

23. **S23**. RoaringBitmap project. [Real Roaring datasets](https://github.com/RoaringBitmap/real-roaring-datasets). repository consulted. Used for: Application-derived bitmap inputs; arbitrary row universes differ from assignment spaces.

24. **S24**. RoaringBitmap project. [CRoaring](https://github.com/RoaringBitmap/CRoaring). repository consulted. Used for: Native compressed and conventional bitmap comparator.

25. **S25**. AFF3CT project. [Configuration files](https://github.com/aff3ct/configuration_files). repository consulted. Used for: LDPC parity-check configuration source; verify each file's H/G identity and terms.

26. **S26**. Albrecht, Bard and M4RI contributors. [M4RI](https://github.com/malb/m4ri). repository consulted. Used for: Dense exact GF(2) arithmetic comparator.

27. **S27**. Soos and CryptoMiniSat contributors. [CryptoMiniSat](https://github.com/msoos/cryptominisat). repository consulted. Used for: CNF/XOR SAT and Gaussian elimination support.

28. **S28**. PySAT project. [SAT solvers API](https://pysathq.github.io/docs/html/api/solvers.html). 1.9.dev15 documentation. Used for: Incremental assumptions and native solver bindings; exact availability must be probed.

29. **S29**. Biere and CaDiCaL contributors. [CaDiCaL releases](https://github.com/arminbiere/cadical/releases). releases consulted. Used for: Native CDCL SAT comparator; freeze tested version.

30. **S30**. Biere and Kissat contributors. [Kissat](https://github.com/arminbiere/kissat/blob/master/README.md?plain=1). repository documentation consulted. Used for: Native SAT comparator; one-shot and incremental capabilities must not be conflated.

31. **S31**. CUDD maintainers. [CUDD](https://github.com/cuddorg/cudd). repository consulted. Used for: Native BDD/ADD/ZDD implementation; verify counting API precision.

32. **S32**. Sylvan maintainers. [Sylvan](https://github.com/trolando/sylvan). repository consulted. Used for: Multicore decision diagrams; separate thread-count lanes.

33. **S33**. CRIL. [d4v2](https://github.com/crillab/d4v2). repository consulted. Used for: Counting library with CNF and circuit input; CLI differs from other d4 releases.

34. **S34**. Meel Group and Ganak contributors. [Ganak](https://github.com/meelgroup/ganak). repository consulted. Used for: Default probabilistic mode versus --prob 0; verify pinned binary and disable approximation fallback for exact lane.

35. **S35**. Berkeley ABC project. [ABC](https://github.com/berkeley-abc/abc). repository consulted. Used for: Native synthesis and equivalence comparator; transformations need verified semantics.

36. **S36**. SMT-LIB initiative. [SMT-LIB Benchmarks](https://smt-lib.org/benchmarks.shtml). current index consulted. Used for: QF_BV application inputs; encoding/solver semantics require separate admission.

37. **S37**. Potassco. [aspcud](https://github.com/potassco/aspcud). repository consulted. Used for: Package dependency solving; feasibility differs from optimized upgrade selection.

38. **S38**. Z3 contributors. [Z3](https://github.com/Z3Prover/z3). repository consulted. Used for: SMT comparator for original bit-vector contracts.

39. **S39**. Runpod. [Pod pricing](https://docs.runpod.io/pods/pricing). current documentation consulted. Used for: Live quote required; compute and continuing storage charges.

40. **S40**. Runpod. [Storage options](https://docs.runpod.io/pods/storage/types). current documentation consulted. Used for: Container/volume/network persistence and retrieval before termination.

41. **S41**. Runpod. [CPU types](https://docs.runpod.io/references/cpu-types). current documentation consulted. Used for: Host CPU diversity; inventory is not a reservation or a CPU-only SKU guarantee.

42. **S42**. IWLS 2026 contest maintainers. [Logic synthesis contest](https://github.com/alanminko/iwls2026-ls-contest/). 2026. Used for: Already-materialized truth tables; synthesis and query tests only, not AST-to-table timing.


Sources that could not be read sufficiently for admission: the original MacKay code-data page returned HTTP 403; speculative fault-tree/BEEM URLs were not verified; the supplied GitHub Pages homepage did not load in the web reader. The catalog uses independently accessible primary sources and local CM evidence instead.
