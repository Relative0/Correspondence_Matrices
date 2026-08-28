# Website integration of the saved feature-model evidence

The local site now exposes [Results & audit](feature-model-evidence.html) from
the navigation on every generated page, a focused-view card on the main page,
and visible summaries on the existing audience and use-case pages. The
configuration card links directly to the results. Stale wording that no
configuration workload had been measured was replaced with the bounded scope.

The new page contains correctness coverage, qualified warm-output ratios,
workload density/change limits, serialization components, all 13 measurement
gaps, independence qualifications, exact run identities, checksums, reports,
raw results and reusable audit/data links. It displays saved evidence; it does
not launch experiments in the browser. Earlier battery and EPFL materials
remain separately labeled and linked.

## Evidence selection and concurrent work

`cm_feature_model_evidence.py` reads only eight explicitly named runs with
pinned checksum-manifest hashes. It verifies 1,113 listed files, checks the
exact bytes consumed by the builder, and refuses changed identities or files.
It does not discover the newest run, import the producer, modify historical
evidence or infer that another task's trials passed this audit.

Feature-model correctness passes do not certify performance. The historical
dirty compiler state and actual sifted graphs remain missing; cold/warm,
fresh/shared, memory and serialization comparisons still need repair.
Legacy chart data and campaign metadata retain their separate identity.

## Validation

- Existing static-site builder: passed; six pages regenerated.
- Existing website suite: 9 tests passed.
- New feature-model website suite: 12 tests passed, including inline JavaScript
  syntax, exact template/data expansion, links, scope labels, checksum mutation,
  duplicate-entry and path-traversal refusal controls.
- All prior evidence arrays, campaign metadata and number tokens compare equal
  to the previously committed generated data; the new section and `fm.*` tokens
  are additive. Authored scope wording was deliberately updated.
- Scoped `git diff --check`: passed.

Commands (from the project root):

```powershell
.venv/Scripts/python.exe -B deliverables_n22_24/master_explainer_2026_08_03/cm_master_build_2026_08_03.py
.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_cm_master_website.py -v
.venv/Scripts/python.exe -B -m unittest discover -s tests -p test_cm_feature_model_website.py -v
```

This was a local website integration. No benchmark timings, full repository
suite or browser visual/interaction tests were run. No dependency installation,
shared compiler/backend edits, commit, push or publication was performed.
