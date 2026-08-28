# Verified research snapshot — August 28, 2026

[Research library](../README.md) · [Download ZIP](CM-Research-2026-08-28.zip?raw=true)

This offline package contains the CM research library, interactive HTML,
benchmark scripts, saved results, audit reports and their source snapshots.
It preserves the limitations and unsuccessful experiments alongside the
successful results. No credentials or installed dependencies are included.

## Snapshot identity

- Source commit: [`cc0e6f1721c8038573b210ced933ebbac6d68932`](https://github.com/Relative0/Correspondence_Matrices/tree/cc0e6f1721c8038573b210ced933ebbac6d68932).
- File: `CM-Research-2026-08-28.zip`.
- Size: **27,466,740 bytes** (about 26.2 MiB).
- Contents: **4,068 source files plus their manifest** (4,069 files total).
- ZIP SHA-256: `7e542350d13c25a81266fad8d581eb007b24367fc7f3c4b985195e02ed07369e`.
- Checksums: [SHA256SUMS](SHA256SUMS) and [per-file source manifest](../SOURCE-SHA256.json).

The source manifest hashes the bytes stored in Git, not a Windows checkout's
possibly converted line endings. It excludes itself and the export-ignored
download directory, dotenv files and profiling binaries. The source commit
pins the manifest. This package does not recursively contain its own ZIP or
this post-build receipt.

## Open locally

Extract the ZIP completely, preferably to a short path on Windows. Some
frozen source snapshots have long paths; use a long-path-capable extractor.
For example, with a recent Python installation:

```powershell
python -m zipfile -e CM-Research-2026-08-28.zip C:\CM
```

Then open:

```text
C:\CM\Correspondence-Matrices-research-2026-08-28\deliverables_n22_24\master_explainer_2026_08_03\index.html
```

The nearby `usecases.html` and `feature-model-evidence.html` show the use-case
research and evidence. The site displays saved results; it does not launch
tests or paid resources. GitHub-readable Markdown editions are under
`docs/research/readers`.

## Verification of this download

The final ZIP passed exact membership, byte-length and SHA-256 checks for
all 4,068 manifest entries, plus the publication path/credential scan,
including nested evidence archives. The six generated readers matched
their authored source. The ZIP was then extracted into a new directory
and these distinct suites were run from that extracted copy:

| Suite | Passing tests |
| --- | ---: |
| Website and pinned evidence (`*website.py`) | 21 |
| Website navigation | 6 |
| Publication, readers and exclusions | 16 |
| Runpod offline setup, transport and accounting (`test_cm_runpod_*.py`) | 61 |
| Bounded measurement verification | 17 |
| **Total** | **121** |

All passed using the project's Python 3.13.5 virtual environment, without
installing dependencies or contacting a cloud provider. These are focused
packaging/regression checks, not a full native-backend test suite or a new
performance experiment. The earlier 70 passing remote tests are historical
evidence and are not added to this local total. Pytest-only feature-model
suites and browser visual/interactive checks were not rerun for packaging.

The first candidate export exposed an omitted 54-byte checksum-pinned
parser fixture. This final snapshot includes that exact fixture; other
temporary test files remain excluded. Frozen evidence was not reformatted
to remove historical whitespace. See [validation notes](../PUBLICATION-VALIDATION-2026-08-28.md)
and [publication scope](../PUBLICATION-NOTES.md).

## Rebuild or verify

From a repository checkout containing the source commit, this creates the
same file-content snapshot at a new output location:

```powershell
git -c core.longpaths=true -c core.autocrlf=false -c core.eol=lf archive --format=zip --prefix=Correspondence-Matrices-research-2026-08-28/ --output=CM-Research-rebuilt.zip cc0e6f1721c8038573b210ced933ebbac6d68932
python -B scripts/cm_research_publication.py verify-archive --archive CM-Research-rebuilt.zip
Get-FileHash -Algorithm SHA256 -LiteralPath CM-Research-2026-08-28.zip
```

Use the verifier from this source snapshot and its accompanying manifest.
The explicit line-ending options prevent Windows archive conversion from
changing manifest-pinned bytes. Compression may vary across Git versions;
the SHA above identifies the supplied ZIP, while the manifest identifies its
file contents. A branch's latest source ZIP is a moving snapshot and should
not be substituted when citing this version.

Third-party material retains its upstream attribution and license terms.
Historical cloud controllers are included as evidence, not as authorization
to rerun consumed one-shot approvals.
