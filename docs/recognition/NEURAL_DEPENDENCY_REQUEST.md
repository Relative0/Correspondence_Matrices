# Grouped optional dependency request: next CNN/GNN smoke batch

Status: **approved by the owner and executed on 2026-08-29**. The isolated
installation and retained experiment stayed inside every requested limit; see
[`pytorch_cpu_2_10_0_manifest.json`](pytorch_cpu_2_10_0_manifest.json) and the
[`Milestone C report`](LEARNING_MILESTONE_C_2026_08_29.md). Existing NumPy
research remains runnable in the unchanged project `.venv`.
This request is only for the next matrix/CNN/GNN comparison, not a live LLM,
external dataset, deployment, GPU job, service, or automatic retraining.

## Proposed effect and limits

Create an isolated Python 3.13 environment at
`C:/Users/brian/Documents/CM_Computation/.venv-crse-neural` and install the pinned
binary wheels below. Keep the project's existing `.venv` unchanged. Download
only from the official PyTorch CPU index and PyPI; retain package hashes,
metadata and bundled license notices. Do not compile from source or install
system components. If dependencies conflict or require additional packages,
stop before installation instead of expanding this request.

Expected download: roughly **150 MiB**, with a **250 MiB maximum** for all wheels
and metadata; maximum environment/download disk allowance **1.5 GiB**.
The exact CPU-wheel total has not been resolved/downloaded: the published PyPI
Windows CPython 3.13 torch wheel is 113.8 MB, and the CPU index separately lists
the pinned `+cpu` wheel. The cap, not that estimate, governs the request.
Sources: [torch release files](https://pypi.org/project/torch/2.10.0/),
[official CPU wheel index](https://download.pytorch.org/whl/cpu/torch/).

After an import/CPU smoke check, permit at most **three manually invoked local
experiments**, each at most **120 cooperative seconds**, with **two shared
training seeds**, **two CPU threads**, **eight variables**, **250,000 parameters**,
and **1 GiB estimated working memory**. CPU only, no JIT/native compilation,
no background jobs, no uploads, no model downloads, no paid calls: **$0 external
compute**. Record manifests before execution; memory/time estimates do not claim
OS containment. Generated data and exact checks use the existing CRSE contracts.

Outputs: new ignored directories under
`C:/Users/brian/Documents/CM_Computation/docs/recognition/runs/`.
This permits bounded representation experiments, not a larger training sweep or
an assertion that CNN/GNN models will outperform the negative MLP baseline.

## Pinned package proposal

These were the explicitly approved pins. All eleven compatible binary wheels
were hash-recorded, installed offline from the local wheelhouse, and tested on
this machine. The wheel total was 136,938,562 bytes; combined wheelhouse and
environment size was 774,856,573 bytes.

| Package | Version | Declared license / source |
| --- | --- | --- |
| torch | 2.10.0+cpu, cp313 win_amd64 | [BSD-3-Clause and bundled third-party notices](https://github.com/pytorch/pytorch/blob/v2.10.0/LICENSE) |
| numpy | 2.3.2 | [BSD-3-Clause and bundled notices](https://pypi.org/project/numpy/2.3.2/) |
| sympy | 1.14.0 | [BSD-3-Clause](https://pypi.org/project/sympy/1.14.0/) |
| mpmath | 1.3.0 | [BSD](https://pypi.org/project/mpmath/1.3.0/) |
| networkx | 3.5 | [BSD-3-Clause](https://pypi.org/project/networkx/3.5/) |
| Jinja2 | 3.1.6 | [BSD-3-Clause](https://pypi.org/project/Jinja2/3.1.6/) |
| MarkupSafe | 3.0.3 | [BSD-3-Clause](https://pypi.org/project/MarkupSafe/3.0.3/) |
| filelock | 3.20.3 | [Unlicense](https://pypi.org/project/filelock/3.20.3/) |
| fsspec | 2026.2.0 | [BSD-3-Clause](https://pypi.org/project/fsspec/2026.2.0/) |
| typing-extensions | 4.15.0 | [PSF-2.0](https://pypi.org/project/typing-extensions/4.15.0/) |
| setuptools | 80.9.0 | [MIT](https://pypi.org/project/setuptools/80.9.0/) |

The official CPU index lists a Windows CPython 3.13 wheel for this torch pin.
Package licenses here are distribution metadata, not legal advice or an
acceptance of separate terms. No downloaded model or external dataset was used.
Milestones A/B remain NumPy-only; the approved packages are used only by the
optional Milestone C path.
