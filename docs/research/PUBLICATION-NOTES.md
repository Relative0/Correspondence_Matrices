# Publication scope and preservation rules

The GitHub research library includes the CM website, eight-use-case dataset
research, feature-model benchmark scripts and saved runs, independent audits,
measurement-verification pilot, memory-budget fixes and tests, and the
successful bounded Runpod memory smoke with its failed-attempt history.

The snapshot also contains the repository's previously committed source and
historical research so that relative evidence links remain usable. Dates,
machine paths, branch identities and old status statements inside frozen
records are provenance, not current operational instructions. The research
index and latest result audit take precedence when identifying current status.

## Deliberate exclusions

No dotenv files, credentials, private keys, token caches, local databases,
virtualenvs, external repository clones, temporary pytest directories,
fake-client fixture directories, local application state, unrelated personal
HTML/ZIP files, or unsubmitted support drafts are added by this publication.
Downloaded copies of provider documentation are not republished; official
sources remain linked. New unrelated CRSE proposal files are left unstaged.

Existing tests and evidence use some preserved historical controller source.
Those scripts are included for inspection and fake-client verification, not
as permission to create another pod. Local credential paths may be documented;
credential file contents are neither read nor published by the packaging flow.

The publication scanner checks selected text and nested archive members for
known credential signatures and sensitive JSON fields, without opening
credential files. This is defense in depth, not a guarantee that every
possible secret format can be recognized. Candidate paths are explicitly
reviewed before staging; a repository-wide `git add .` is not used.

## Evidence integrity and reuse

Content-addressed source snapshots, JSON/CSV/XML records and checksum files
are preserved byte-for-byte. Git attributes disable line-ending conversion
for the new frozen-evidence tree. Friendly Markdown readers are derived
separately and do not rewrite historical measurements or their hashes.

The readers resolve named numeric tokens from the site's existing evidence
data and retain a provenance appendix. Read the correction and independence
audits before quoting results. Correctness passes, a working remote
transport, and synthetic memory coverage do not imply general CM dominance.

Third-party datasets, extracted instances, test corpora and dependencies
retain their upstream attribution and licensing conditions. The dataset
catalog supplies source URLs and acquisition/license notes. No new project
license or relicensing of upstream material is introduced here. No new
datasets are downloaded or scientific experiments run as part of packaging.

The downloadable snapshot is built from an exact local Git commit using
`git archive`, after staged-file inspection. Its own download directory is
export-ignored to prevent recursive archive growth. The supplied SHA-256
manifest identifies the bytes stored in Git; the download page identifies
the source commit and ZIP hash. GitHub publication requires the separately
confirmed push to `Relative0/Correspondence_Matrices` on `main`.
