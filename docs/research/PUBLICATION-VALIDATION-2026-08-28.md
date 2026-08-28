# Research-library integration checks

The publication adds GitHub-readable Markdown editions and an offline
repository snapshot without rerunning scientific timing experiments.

## Checks before the source commit

- Existing website builder regenerated all six HTML pages successfully.
- 21 website/evidence tests passed, including pinned historical evidence
  checks and exact template/data expansion.
- 61 Runpod setup, fake-client transport and accounting tests passed.
- 17 bounded measurement-verification tests passed.
- Six static website-navigation tests passed.
- 16 new publication tests passed: path exclusions, credential-signature
  redaction, sensitive JSON fields, nested archive checks, link conversion,
  numerical units/provenance, superscripts and reader coverage.
- Total: **121 local tests passed**, across the above distinct suites.
- All six generated Markdown editions passed the reproducibility check;
  their local links and the research index resolved.
- The selected publication files passed the credential/path scan, including
  existing nested evidence archives. Credential files were not opened.

The 70 previously passed remote output-budget tests remain separately
recorded in the successful Runpod smoke; they are not 70 new local tests.
No full pytest/native-backend suite, new cloud workload, dependency install,
or browser visual/interactive check was performed for this packaging task.
Pytest-only feature-model tests were retained with their historical results,
not claimed as rerun by unittest discovery.

## Preservation

The frozen scientific records and their checksum manifests are retained.
New evidence attributes preserve exact bytes across checkouts. The only
new scientific prose correction in the website source acknowledges that
bounded real feature-model tests have run, while retaining their measurement
gaps; it does not change a timing result or add a performance claim.

Staging required Git's per-command `core.longpaths=true` for the nested
source snapshots. Frozen CRLF records are marked `cr-at-eol` for whitespace
checking, not converted to LF. Historical trailing spaces/blank lines are
retained where they belong to hashed evidence; they are not reformatted.

The first extracted-copy test exposed one omitted 54-byte parser fixture
inside a historically named `pytest-tmp` directory. Unlike live scratch,
this file is required by the frozen audit's checksum manifest. It is now an
explicit hash-pinned publication exception; the historical manifest and
fixture bytes were not changed. The download receipt records the repeated
extracted-copy verification after this correction.

The companion source manifest hashes Git-index bytes, not assumptions about
Windows line-ending conversion. The downloadable archive is built from the
source commit and checked against that manifest. The download receipt
records the exact commit, archive hash, size, and post-extraction checks.

No push is implied by a successful local commit. At preparation time,
`origin/main` was `1f51e651cb08ccda3284bd8476e4a9dbaedacf37`, while the local
branch already contained `21635b8` and `6ce1f3f` (CRSE proposal commits).
Publishing this branch therefore also publishes those existing commits
and requires confirmation of that full scope.
