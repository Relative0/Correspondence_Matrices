import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'deliverables_n22_24/master_explainer_2026_08_03'
FOLDER=SITE/'results/2026-10-14/cpu-pilots'


def test_published_pilot_downloads_and_phase_medians_are_complete():
    spec=importlib.util.spec_from_file_location('october_verifier',ROOT/'scripts/cm_october_pilot_publication_verify.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.verify(SITE)
    assert result['trial_records']==224 and result['matching_pairs']==112
    assert result['phase_rows']==56 and result['source_subset_files']==288


def test_pilots_preserve_scope_and_remove_operational_metadata():
    summary=json.loads((FOLDER/'summary.json').read_text(encoding='utf-8'))
    assert 'four active source variables' in summary['interpretation']['support_limit']
    assert 'do not pool platforms' in summary['interpretation']['cross_platform']
    assert 'no new crossover timings' in summary['interpretation']['next']
    for pilot in summary['pilots']:
        payload=(FOLDER/pilot['trial_download']).read_text(encoding='utf-8')
        assert 'C:\\\\Users' not in payload and '/sys/fs/cgroup/' not in payload
        for line in payload.splitlines():
            row=json.loads(line)
            assert set(row['resource_summary'])<={'cleanup_verified','peak_job_committed_bytes','memory_metric'}
            assert 'stdout' not in row and 'stderr' not in row and 'pid' not in row
