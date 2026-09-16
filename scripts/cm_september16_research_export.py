"""Build the explicit September 16 research/source publication allowlist."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'deliverables_n22_24/master_explainer_2026_08_03'
RELATIVE = Path('results/2026-09-16/exact-count-and-decomposition')
EVIDENCE = ROOT / 'docs/research/2026-09-16-exact-count-and-decomposition/evidence'
SOURCE_FILES = (
    'cmbench/comparative/exact_cudd_count.py',
    'cmbench/comparative/sympy_cm_claim_cleanup.py',
    'scripts/cm_sympy_claim_cleanup.py',
    'cmbench/recognition/gf2_decomposition.py',
    'cmbench/recognition/gf2_screening_experiment.py',
    'cmbench/recognition/gf2_phase_benchmark.py',
    'cmbench/recognition/gf2_c40_confirmation_benchmark.py',
    'cmbench/recognition/gf2_c41_ablation_benchmark.py',
    'cmbench/recognition/abc_acd_external_baseline.py',
    'cmbench/recognition/abc_acd_truth_runner.cpp',
    'cmbench/recognition/c40_abc_contract_probe.py',
    'cmbench/recognition/external_gf2_artifact_adapter.py',
    'cmbench/recognition/cut_fusion.py',
    'tests/test_gf2_decomposition.py',
    'tests/test_external_gf2_artifact_adapter.py',
    'tests/test_gf2_c41_ablation_benchmark.py',
    'tests/test_cut_fusion.py',
) + tuple('prototypes/cudd_apa/' + name for name in (
    'README.md', 'DD-LICENSE', 'patch_dd.py', 'dd-0.6.0-apa.patch', 'bootstrap.sh',
    'build_native.py', 'fetch_cudd.py', 'reference.py', 'test_count.py',
    'benchmark.py', 'memory_probe.py', 'validate.py',
    'results/python-dependencies.txt', 'results/prototype-tests.log',
    'results/dd-count-support-reorder-tests.log',
))


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def build_publication():
    benchmark = json.loads((ROOT / 'prototypes/cudd_apa/results/benchmark.json').read_text())
    memory = json.loads((ROOT / 'prototypes/cudd_apa/results/memory-summary.json').read_text())
    studies = {name: json.loads((EVIDENCE / (name + '.json')).read_text()) for name in ('c39', 'c40', 'c41')}
    cut = json.loads((ROOT / 'docs/audits/2026-09-16-cm-cut-fusion-phase2/phase2-verification.json').read_text())
    assert cut['decision'] == 'STOP'
    assert all(study['status'] == 'complete' for study in studies.values())
    assert all(all(studies[key]['summary']['functional'].values()) for key in ('c39', 'c40'))
    assert studies['c41']['summary']['all_ablations_valid']
    assert memory['status'] == 'passed_differential_check'
    assert all(row['methods']['apa_int']['exact'] and row['methods']['python_exact']['exact'] for row in benchmark['cases'])
    summary = {
        'schema': 'cm-september16-research-publication/v1', 'reviewed': '2026-09-16',
        'title': 'Exact counting, decomposition studies and a stopped optimization',
        'cudd': {'benchmark': benchmark, 'memory': memory, 'prototype_tests': 57, 'regression_tests': 23,
                 'scope': 'Local Linux/WSL synthetic resident-root counting; build and extraction excluded. This is a dd/CUDD binding prototype, not a CM-versus-CUDD performance claim or an upstream release.'},
        'decomposition': studies,
        'cut_fusion': {'decision': cut['decision'], 'stop_reason': cut['stop_reason'],
                       'confirmation': cut['locked_f1_f2_q64'], 'timing_integrity': cut['timing_integrity']},
        'boundaries': [
            'C39 and C40 compare C16 with this repository’s C15 control on one Windows host; they do not establish superiority over external decomposition tools.',
            'C40 used a separately acquired source family not used to develop C15/C16. This bounded development-blind selection is not an independent implementation.',
            'ABC’s fixed 4-LUT output does not meet the C16 artifact contract; no C16-versus-ABC speed or quality claim is made.',
            'C41 reuses C40’s vectors on Windows. Ablation ratios are descriptive and non-additive; strict reconstruction remains required.',
            'C40/C41 corpus redistribution remains unresolved. Downloads contain project source and aggregate measurements, not frozen corpus vectors or third-party source trees.',
            'Cut fusion failed its frozen whole-session latency gate and remains opt-in research code; it is not a recommended default.',
        ],
    }
    payloads = {'PUBLIC-SUMMARY.json': json_bytes(summary),
                'cudd-benchmark.json': json_bytes(benchmark), 'cudd-memory-summary.json': json_bytes(memory)}
    payloads.update({name + '-aggregate.json': json_bytes(study) for name, study in studies.items()})
    payloads['cut-fusion-verification.json'] = json_bytes(cut)
    for relative in SOURCE_FILES:
        payloads['sources/' + relative] = (ROOT / relative).read_text(encoding='utf-8').encode('utf-8')
    c39 = studies['c39']['summary']['screened_over_exhaustive_speedup']
    c40 = studies['c40']['summary']['screened_over_exhaustive_speedup']
    report = f'''# September 16 research and source update

## Exact integer CUDD counting

The dd 0.6.0 prototype calls `Cudd_ApaCountMinterm`, folds binary APA digits into
a Python integer, and frees the returned buffer using `Cudd_FreeApaNumber` in
`finally`. Default support-sized counting is preserved. There were 57 prototype
and 23 relevant dd regression passes. A 40,000-call Valgrind comparison showed
unchanged combined lost bytes against the interpreter baseline, not a globally
leak-free interpreter. Allocation failures were not fault-injected.

Nine rounds of 200 calls per method measured already-resident roots on Linux/WSL.
Construction is excluded. On the three larger synthetic diagrams APA was about
9–10 times faster than the existing Python exact traversal, with about 1.1–3.4
times the latency of the double API. Trivial roots favor Python. The OR count
rounded in the double control; the 1,100-variable padded literal overflowed it.
See `cudd-benchmark.json` for all samples, exactness flags, environment and hashes.

## C39–C41 decomposition studies

C39 measured {c39:.4f} times C16-over-C15 speed across 19 public cases; C40
measured {c40:.4f} times across 20 cases on a separately acquired public family.
Both use sums of per-case medians of analysis-only time, not end-to-end time.
Selected artifacts were identical and reconstructed the input truth vectors.
C40's sum of median peak-working-set deltas was 33,587,200 bytes for C15 and
19,165,184 bytes for C16. This is a Windows observation, not a general memory bound.

C41 retained 500 timing rows and zero invalid ablation lanes. Repeating layouts
cost 1.7329 times the reference; eager admission cost 3.5491 times. A linear
minimum used 0.9324 times the reference time. Omitting strict checks is a
diagnostic lane, not a safe production optimization. These effects are not
additive causal shares of the historical C15-to-C16 difference.

The ABC ACD output contract is different: no external speed or quality claim is
supported. The published code exposes that incompatibility explicitly.

## Bounded cut fusion: STOP

The locked F1/F2 q64 whole-session speed was {cut['locked_f1_f2_q64']['speedup']:.4f}
times the CSE control, below the frozen 1.10-times threshold. Execution improved
but recognition/compilation did not repay at measured reuse. All 21,840 timing
rows were exact across arms, but natural-panel timing and the relative-memory
promotion sweep were not run after the stop. No default dispatch change is made.

## Source and reuse

Individual Python files and the APA patch are under `sources/`; the ZIP contains
the same explicit allowlist plus these summaries. The source ZIP is an overlay
for the repository, not a standalone Python installation. Prototype build and
validation instructions are in `sources/prototypes/cudd_apa/README.md`.
The repository includes the reviewed recent compiler/research/Python work; the
SymPy cleanup source is included as well, without assigning it a new benchmark.

Source text is normalized only for line endings before hashing. The manifest
records every published file's bytes and SHA-256. Original C39–C41 result hashes
are retained in the aggregate documents. They are aggregate extracts, not a
redistribution of the original corpus or a complete benchmark replay bundle.
Raw corpus vectors, unresolved-licensing data, executable binaries, local paths,
credentials and cloud-operation receipts are outside this publication allowlist.
The dd-derived patch carries `DD-LICENSE`; publication grants no new license to
the remaining project source. Third-party tools must be obtained separately.
'''
    payloads['REPORT.md'] = report.encode('utf-8')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for name, payload in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 16, 0, 0, 0))
            # Preserve the published ZIP's origin byte on every build host.
            info.create_system = 0
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            output.writestr(info, payload)
    payloads['research-source-and-evidence.zip'] = archive.getvalue()
    manifest = {'schema': 'cm-research-download-manifest/v1', 'reviewed': '2026-09-16',
                'source_text_hash_mode': 'UTF-8 with LF line endings',
                'artifacts': [{'path': name, 'bytes': len(payload), 'sha256': digest(payload),
                               'role': 'source' if name.startswith('sources/') else 'evidence'}
                              for name, payload in sorted(payloads.items())]}
    payloads['PUBLICATION-MANIFEST.json'] = json_bytes(manifest)
    return payloads


def main():
    payloads = build_publication()
    base = SITE / RELATIVE
    for name, payload in payloads.items():
        target = base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != payload:
            target.write_bytes(payload)
    print(f'Exported {len(payloads)} allowlisted files; manifest SHA-256 {digest(payloads["PUBLICATION-MANIFEST.json"])}')


if __name__ == '__main__':
    main()
