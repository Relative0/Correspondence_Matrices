# Biology corpus audit

The retained Biodivine 2022 BNet archive has **212 valid models: 22 closed and 190 open**. Every admitted file is byte-identical to its ZIP member and frozen SHA256. The archive's `metadata.json` explicitly declares `input_representation: "free"`. Thus missing update equations are consistent with the chosen free-input export, and **the 190 open models must not be called broken solely because they contain undeclared regulators**.

The archive is bound by SHA256 `76f9eb1bcf4f758d06968647ade2232fccec02f92f80bf2b003043b57e97e04a` and the frozen record identifies Zenodo DOI `10.5281/zenodo.8020309`, CC-BY-4.0. The local evidence is sufficient for export-level attribution; this audit made no network calls and did not independently validate the original publications or original translation pipelines. The freeze's metadata record itself says it used a pinned fallback when the live endpoint was unavailable.

`BIOLOGY_CORPUS_AUDIT.json` records all 212 model names, source archive members/URLs, input hashes, source metadata hashes, parser/generator hashes, external regulator lists, widths, syntax checks, flags, ancestry evidence, clusters, and proposed partitions. Archive numbers start at 001; the admitted filename index starts at 000. Use the manifest mapping rather than equating those indexes.

## What the open models establish

All 190 open models parse successfully. Across models, 2,132 external regulator name occurrences have no exported update equation. Export metadata establishes their intended treatment as free inputs at this representation level. The archive does not supply original per-regulator annotations, publications, physiological domains, or perturbation protocols. Whether each name is a biological environment input, intervention parameter, an omitted original input, or a translation defect therefore remains unresolved. This is a substantive distinction between demonstrated export semantics and unvalidated biological meaning.

The source summary has four column labels but five values per row. The audit retains the original numeric fields and compares them empirically to target count, referenced external count, and distinct target-regulator edge count. All 212 target counts agree. All three counts agree for 194 models. Eighteen models have fewer syntactically referenced edges than the summary; two also have fewer referenced inputs:

| Model | Summary fourth field | Referenced external names | Interpretation |
|---|---:|---:|---|
| 039 HIV-1-INTERACTIONS-WITH-T-CELL-SIGNALING | 14 | 12 | Original unused inputs, simplified edges, or translation loss remain possible. |
| 094 MACROPHAGE-POLARIZATION-STATES | 8 | 7 | The missing original names cannot be recovered from this BNet alone. |

There are two case-sensitive naming flags: model 098 references external `v_TNFA` while declaring `v_TNFa`; model 173 references external `v_Gal4` while declaring `v_GAL4`. These are review candidates, not proven typos. No names or equations were corrected. The JSON names every discrepancy and external regulator, so unresolved cases are individually actionable without a blanket rejection.

For an open network, a fixed external assignment gives one closed internal-state fixed-point query. Counting all `(internal state, external input)` pairs and counting distinct internal states projected across inputs are different contracts. An omitted input that no longer appears in the export can change the former count without changing the latter. Do not infer the original full input space, add self-loops, pin defaults, or merge case variants silently. Require an explicit input-role/assignment contract and hash it with each future query; original-source recovery is required to settle the flagged provenance questions.

## Duplicates and independence

There are no byte-identical models and no duplicates after sorting equations and canonicalizing associative/commutative operators. Exact local truth tables were also computed for the 192 models whose every function has at most 12 regulators; they reveal no additional duplicates. These fingerprints preserve regulator names and syntactic regulator sets. Arbitrary variable-renaming equivalence and equivalence after eliminating redundant regulators were not exhaustively checked.

Two pairs have strong shared-equation evidence: 002/004 share 109 equations, 83.85% of the smaller model; 014/025 share 51 equations, 94.44% of the smaller. The generator also enumerates 26 conservative named-family/variant groups, including explicitly reduced, extended, multicell, time-scale, and A/B/C/D variants. These are leakage-prevention hypotheses grounded in names and syntax, not verified publication genealogy. Taking their transitive union yields 168 conservative clusters, of which 20 contain the 22 closed models. A singleton cluster is not proof of biological independence; publication-level provenance can still merge clusters.

The ten successor biology models occupy nine conservative clusters: models 109 and 110 are the A/B asymmetric-cell-division variants. Repetitions, queries, and variants must not be counted as independent biological datasets. Every successor case ID is mapped back to its input hash and cluster in the JSON.

## Partitions and closed-model coverage

The proposed split deterministically orders cluster hashes using seed `cm-biology-prospective-family-split-v1-20260914`, applies Hamilton allocation to 60/20/20 train/development/heldout-candidate ratios within size/support strata, and forces successor-timing-exposed clusters to development. Cluster strata use maximum target count and maximum support width across their members. Small strata can have empty partitions; no artificial replication is introduced to balance them.

This gives 116 train, 62 development, and 34 heldout-candidate models. Among the 22 closed models, the counts are 7, 12, and 3. The candidate heldout closed models are 074, 210, and 211. These partitions are **prospective recommendations, not pristine heldout evidence**: the corpus was already accessible and screened, and its past selection criteria are known. Freeze the implementation and query generator before additional performance measurements. Use independently sourced, provenance-validated families for a strong confirmatory generalization gate; the current split can support carefully labeled internal validation.

All 22 closed models belong in the experiment matrix, with explicit per-arm resource limits and failures. They span 5–183 targets and maximum support widths 2–20. A scalar oracle limit must produce an explicit unsupported/limit result for larger models; it cannot justify omitting them from the other exact controls. The frozen campaign's selected-function local width is not the maximum width of its whole BNet; use this audit's `maximum_support_width` for whole-network stratification.

## Reproduction and checks

Run from the clean consolidation worktree, retaining the original checkout only as a read-only evidence root:

```powershell
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' docs/audits/2026-09-14-cm-benchmark-attribution/corpus_audit.py --evidence-root 'C:/Users/brian/Documents/CM_Computation' --self-test
```

The evidence root is an explicit argument and is recorded in the JSON; no input is copied, normalized in place, or downloaded. The generator verifies archive and per-model manifest hashes and checks every admitted model against the raw ZIP member before analysis. It asserts the reproduced 22/190 classification. The optional self-test passed: 200 seeded random expressions, 786 exhaustive scalar/table comparisons, positive and negative canonicalization controls, and a depth-4000 expression. Two complete generator runs produced byte-identical JSON after the source was finalized. No dependencies were installed or solver substitutions made.

The next provenance work is to retrieve original annotations/publication identifiers for the 190 free-input exports, prioritizing 039/094 count discrepancies and 098/173 casefold flags. That work belongs with this audit's follow-up because it reuses the hash-bound mapping; it must remain read-only unless a separately reviewed successor corpus is authorized. Until then, closed-model local control and attribution experiments can proceed under the experiment specification.
