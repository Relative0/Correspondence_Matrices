# Repository state inventory

Snapshot date: 2026-08-30. The two scoped CM checkpoints are staged but not
committed. Nothing was pushed, reverted, deployed, published, or deleted.

## CM_Computation

- Branch/HEAD: `main` / `7a18649e96ea4e9fd1994d0a4310947f60dee64a`.
- Exactly 170 files under `docs/video_factory` are staged. The checkpoint is
  approximately 9.3 MiB and contains factory code, strict contracts, tests,
  source/claim/catalog records, Level 1 proof media and QA, long-form resolved
  specs, the Level 2 release manifest, and review reports.
- No path outside `docs/video_factory` is staged by this task.
- The 19.6 MiB flagship MP4, chapter media, narration WAVs, audio master,
  contact sheet, raw frames, test workspaces, RunPod packages, and downloaded
  remote workspaces are local and ignored. Their authoritative hashes are
  retained in the checked-in manifests and reports.
- The repository contained many unrelated tracked changes before and during
  this task. They remain unstaged and were not modified, reverted, or included
  in the checkpoint.

Reviewed commands:

```powershell
git diff --cached --name-only -- docs/video_factory
git diff --cached --stat -- docs/video_factory
git diff --cached --check
git status --short --untracked-files=no -- docs/video_factory
```

## PoP/Tools shared repository

- HEAD at discovery was `81af0adec2e74bd0a0fa28a99cc0884dbb9b77ec`.
  During this task an unrelated concurrent commit advanced `main` to
  `56603bda089cc61ab00ea38c8c0099304534b66c` (`Add evidence-first social
  campaign factory`).
- Exactly 15 CM-owned renderer/portability files are staged: 11 modified IVC or
  POP files and four new `cm_science` POP files. No other Tools path is staged
  by this task.
- Focused verification passed: IVC 46 tests; POP 34 tests with two slow tests
  deselected. The long-form render also consumed the staged renderer bytes and
  bound their scoped source-set identity in `plan_manifest.json`.
- Other dirty Tools areas—including Artifact-To-Video, Book-Agents, model
  files, social-campaign work, and music experiments—were excluded and left
  untouched.

## Commit gate

The requested preservation checkpoint is fully staged and reviewed. A commit
attempt was refused by the repository safety gate because the user-level rule
requires the literal instruction to commit. No commit was created. The next
history-changing action is therefore gated on an explicit instruction such as
`commit the scoped CM checkpoints`. No push is planned or implied.
