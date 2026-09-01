# Circuit workloads: structure, truth, and exact controls

Video ID: `circuits`  
Episode content identity: `d034f7d278b31a7340fbc6cd5448d4823f249d0bb3c7cecc72809473bb98e1aa`  
Status: **complete narration draft; production candidate pending content approval**

## c01 — Question and definition: circuit cone

When a circuit has thousands of gates, what exact function is one output cone asking us to compute? This episode has one job: Circuit evaluation starts from gates and cones but must define semantic support, exact output, comparator structure, and task boundary before interpreting performance. We build on CM, CSE, BitSet, BDD, SAT, Espresso, and SymPy: different questions, Live support versus ambient variables, Plain CSE versus sharing-aware CSE-flat; their definitions stay fixed while this lesson adds a new layer. A cone is the gate region that can influence one output; its semantic support is the subset of inputs that can change that output.

Watch for the label logic circuit; it stays attached to the artifact this episode means. When we say cone, the highlight identifies its layer before we interpret it. The term fanout receives its own visual state so it cannot drift into a neighboring concept. We will keep semantic support visible whenever its definition controls the inference.

A persistent AND/INV label marks exactly where that object enters the example.

## c02 — Worked example: Small AND/INV cone

The next sequence uses Small AND/INV cone as a conceptual teaching example, not as measured benchmark evidence. Our stable example is Small AND/INV cone. A conceptual five-input AND/INV cone whose output has four-variable semantic support, paired later with separately labeled retained EPFL evidence. Teach cone support, fanout, lowering, exact digests, and the accepted EPFL mechanism.

We now construct the Small AND/INV cone and name every part before interpreting it. Now isolate circuit cone inside Small AND/INV cone. The example definition and output meaning stay fixed while only the state for circuit cone changes. That matched before-and-after view assigns the visible consequence to circuit cone, not to a substituted workload.

A full circuit fades while one output cone and its fan-in remain bright. The cone starts from five named inputs, but the displayed output has four-variable semantic support. Holding that element fixed lets this episode isolate circuit cone. Structural counts describe nodes, edges, and operations; they do not directly measure hardware memory traffic.

Any mechanism claim points to a visible change in the cone rather than to a benchmark ratio by itself. The starting state preserves the stable definition: A conceptual five-input AND/INV cone whose output has four-variable semantic support, paired later with separately labeled retained EPFL evidence.

## c03 — Mechanism: fanout and support; AND/INV workload shape; exact circuit controls

Zoom from a larger circuit into one output cone and trace which input variables can affect it. Lower the cone through CSE-flat and CM-IR, verify one truth digest, and connect its binary shape to the retained EPFL mechanism. Now isolate fanout and support inside Small AND/INV cone. The example definition and output meaning stay fixed while only the state for fanout and support changes.

That matched before-and-after view assigns the visible consequence to fanout and support, not to a substituted workload. Semantic-support testing removes an ambient input that cannot influence the cone output. Now isolate AND/INV workload shape inside Small AND/INV cone. The example definition and output meaning stay fixed while only the state for AND/INV workload shape changes.

That matched before-and-after view assigns the visible consequence to AND/INV workload shape, not to a substituted workload. Matched gate graph, lowered instructions, and exact digest remain synchronized. Now isolate exact circuit controls inside Small AND/INV cone. The example definition and output meaning stay fixed while only the state for exact circuit controls changes.

That matched before-and-after view assigns the visible consequence to exact circuit controls, not to a substituted workload. A circuit cone's semantic support and gate structure determine the exact function under study; nominal circuit size is not a substitute for cone support. Read that statement only within this scope: accepted EPFL AND/INV cone workload. Its declared measurement boundary is workload definition.

The uncertainty field says corpus and support range scoped. On the accepted EPFL AND/INV workload, CM/CSE-flat was 0.9998 with a circuit-clustered 95% interval [0.9747, 1.0249]. Read that statement only within this scope: EPFL AND/INV cones, semantic support 8–16, one Windows machine. Its declared measurement boundary is compiled evaluator kernel after compilation.

The uncertainty field says circuit-clustered bootstrap, 4000 draws. On the EPFL AND/INV workload, CM and CSE-flat had equal instruction and executed-operation counts, matching the parity mechanism prediction. Read that statement only within this scope: EPFL AND/INV cones. Its declared measurement boundary is compiled program structure and kernel.

The uncertainty field says exact count equality on accepted corpus. Corrected benchmark rows required frozen truth verification and equality across eligible timed arms before performance evidence was accepted. Read that statement only within this scope: corrected benchmark protocols. Its declared measurement boundary is correctness gate outside performance claim.

The uncertainty field says hash/equality gate. The nearest confusing lesson is Configuration and feature-model workloads; it owns feature constraints, while this episode owns circuit cone. AND and inversion nodes form a small exact dependency cone whose fanout remains visible throughout the lesson. Holding that element fixed lets this episode isolate fanout and support.

The inert input stays outlined so nominal width cannot be mistaken for active support. Holding that element fixed lets this episode isolate AND/INV workload shape. A topological trace orders the gates without changing their connectivity or the output function. Holding that element fixed lets this episode isolate exact circuit controls.

An exact output digest binds the conceptual cone to any separately labeled retained measurement panel. The conceptual mechanism and EPFL evidence use matched colors but retain distinct status badges and source footers. Lowering or packing may change the execution artifact while the cone's admitted Boolean result remains fixed. The comparison closes with the same inputs, output contract, and exactness gate on every path.

## c04 — Boundary, retrieval, and transfer

The accepted parity result belongs to selected EPFL AND/INV cones, not to all circuits or all tasks. Identify the gates and variables outside one selected cone and predict whether removing them changes its output function. Measure the function of the cone you actually selected, not the size of the circuit around it. A common mistake is this: Nominal circuit size directly determines the semantic support and strongest evaluation method for every cone.

Repair it by returning to the owned distinction: circuit cone.

*[Three-second retrieval pause.]*

Use the episode's central distinction to answer: Measure the function of the cone you actually selected, not the size of the circuit around it. Circuit structure becomes evidence only after the cone, support, output, and comparator are fixed.
