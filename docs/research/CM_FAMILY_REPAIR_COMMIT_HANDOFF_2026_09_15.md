# CM-family repair commit and audit handoff

The repair implementation and sealed development diagnostics are committed as
`4f979d141d8a73591a83d48f7273f516b7205823` on
`codex/cm-family-repair-20260915`, parent
`4d9b869fb7b22eb6263ef613b5a9d41fcbbb78dd`.
The original implementation baseline remains
`e334de594262059cc18cf37eaab56b0f79e94843`.

This additive handoff follows the user's explicit request to commit and push.
It does not replace the sealed audit. Statements such as "uncommitted" and
"unpushed" in that audit describe its historical sealing checkpoint. The later
documentation commit contains this handoff and the successor audit prompt.
Remote push completion is checked separately against the remote branch tip.

## Evidence and source identity after committing

All 69 artifacts, the manifest and detached seal were checked against the staged
Git blobs byte for byte before the repair commit. A narrow `.gitattributes` rule
preserves those bytes on subsequent checkouts, including captured test logs.

Git normalizes four modified Python files from their working CRLF/mixed endings
to LF. Before committing, each staged source was compared against the measured
working source after CRLF-to-LF normalization. No other byte difference occurred.
The two new Python files already matched their committed bytes.
[CM_FAMILY_REPAIR_PUBLICATION_2026_09_15.json](CM_FAMILY_REPAIR_PUBLICATION_2026_09_15.json)
binds the measurement hashes, exact committed source hashes and normalized hashes.
This is a line-ending provenance bridge, not a rewrite of the measurement hashes
or a claim that every checkout has the original raw bytes.

Use the read-only verifier from this documentation commit:

```powershell
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' -B `
  docs/research/verify_cm_family_repair_publication.py --check-local-predecessors
```

It checks the exact repair commit, all sealed artifacts, source bindings and
current source equivalence. The optional local check also reads the predecessor
paths and evidence-directory hashes recorded on this machine. Without that flag,
it explicitly reports local predecessors as unchecked. In a new audit worktree,
pass `--repo` naming that unchanged implementation checkout or the original repair
worktree; the verifier itself lives in the later documentation commit.

The original `seal.py --verify` additionally asserts the original HEAD, unstaged
status and exact pre-commit diff. It is intentionally unsuitable as a current Git
state check after committing. Preserve it and its successful historical receipt.
The new verifier does not attest current protected-worktree status; use the
read-only `preservation.py --verify` in the original repair worktree for that.

## Validation checkpoint

The unchanged final implementation passed another pre-commit run:

```powershell
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' -B -m pytest -q `
  -p no:cacheprovider --basetemp=tmp/commit-check-pytest `
  tests/test_cm_family_repairs.py tests/test_persistent_path_consistency.py `
  tests/test_cm_runpod_p7_functional_scout_v2.py
```

Result: **63 passed, four subtests passed**. The broader prior results and
pre-existing failures remain in the sealed `CHECKS.md`. The chart-data failure
reproduces on the baseline. Two historical source-identity verifiers fail because
the baseline and candidate working bytes differ from their expected LF hashes;
`SOURCE_IDENTITY_DIAGNOSTIC.json` records that LF normalization matches both
expected hashes. These historical checks are not relabeled as passing.

The additive publication verifier also passed five controlled checks: it rejects
a changed manifest binding, committed-source binding, working source content and
sealed report content, while accepting a checkout whose only difference is LF
line endings. These checks used in-memory substitutions and changed no evidence
files. Its full local check verified all 69 artifacts and 81 predecessor-file
bindings (including repeated manifest bindings).

Protected tracked statuses/dirty-file hashes and both predecessor audit directories
were verified unchanged. Staged diff checks passed. No new timing run, held-out
input, dependency installation or scientific-disposition change accompanied this
commit preparation.

## Successor task

Use [the complete missed-speedups audit prompt](CM_MISSED_SPEEDUPS_DEEP_DIVE_PROMPT_2026_09_15.md).
It targets the exact repair commit and identifies the current records, old
measurement caveats, untracked local evidence and bounded audit permissions.
The successor audit has been prepared, not executed.

Recommend a **new task using GPT-6 Astra with high reasoning**. This is an
independent assessment of remaining mechanisms and possible blind spots; the
handoff preserves the decisions and evidence needed to avoid repeating discovery.
High is the initial setting I judge sufficient; reserve xhigh for a concrete
unresolved cache-correctness or causal-attribution problem. This is a qualitative
reliability/cost judgment, not a measured model comparison or a promise of cache
savings. Astra supports this reasoning setting and complex coding/research work.
See the [official model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra).

No further repair work is required by this commit request. Running the prepared
audit is the useful optional next task; implementation decisions follow its evidence.
