"""The new research findings and downloads must agree with their measured evidence."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from unittest import mock
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'deliverables_n22_24/master_explainer_2026_08_03'
BASE = SITE / 'results/2026-09-16/exact-count-and-decomposition'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_all_published_bytes_rebuild_and_match_the_manifest():
    exporter = load('research_export_test', ROOT / 'scripts/cm_september16_research_export.py')
    expected = exporter.build_publication()
    assert set(expected) == {path.relative_to(BASE).as_posix() for path in BASE.rglob('*') if path.is_file()}
    for name, payload in expected.items():
        assert (BASE / name).read_bytes() == payload, name
    manifest = json.loads(expected['PUBLICATION-MANIFEST.json'])
    for row in manifest['artifacts']:
        assert hashlib.sha256(expected[row['path']]).hexdigest() == row['sha256']
        assert len(expected[row['path']]) == row['bytes']
    with zipfile.ZipFile(io.BytesIO(expected['research-source-and-evidence.zip'])) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(expected) - {'PUBLICATION-MANIFEST.json', 'research-source-and-evidence.zip'}
        for name in archive.namelist():
            assert archive.read(name) == expected[name]


def test_evidence_loader_rejects_modified_downloads():
    loader = load('research_evidence_test', SITE / 'cm_september16_research_evidence.py')
    evidence, files = loader.build_research_evidence()
    assert len(files) == 42
    assert evidence['cut_fusion']['decision'] == 'STOP'
    original = Path.read_bytes
    changed = BASE / 'sources/prototypes/cudd_apa/patch_dd.py'
    with mock.patch.object(Path, 'read_bytes', lambda path: original(path) + (b'corrupted' if path == changed else b'')):
        with pytest.raises(ValueError, match='Changed research artifact'):
            loader.build_research_evidence()


def test_exact_counts_and_negative_results_remain_visible():
    data = json.loads((BASE / 'PUBLIC-SUMMARY.json').read_text(encoding='utf-8'))
    cases = {row['case']: row for row in data['cudd']['benchmark']['cases']}
    assert all(row['methods']['apa_int']['exact'] for row in cases.values())
    assert cases['or_64_padded_128']['methods']['existing_double']['exact'] is False
    assert cases['literal_padded_1100']['methods']['existing_double']['status'] == 'error'
    runs = data['cudd']['memory']['runs']
    assert runs[1]['measured_calls'] == 40000
    assert runs[0]['combined_lost_bytes'] == runs[1]['combined_lost_bytes']
    assert data['cut_fusion']['confirmation']['speedup'] < 1
    for name in ('c39', 'c40'):
        study = data['decomposition'][name]['summary']
        times = study['primary_median_case_sum_ns']
        assert study['screened_over_exhaustive_speedup'] == times['c15_exhaustive'] / times['c16_screened']
    assert data['decomposition']['c41']['measurement_rows'] == 500


def test_routes_expose_source_links_without_redistributing_corpus_vectors():
    for name in ('index', 'layperson', 'investor', 'expert', 'usecases', 'feature-model-evidence',
                 'learning-neural-evidence', 'data-downloads', 'latest-results'):
        html = (SITE / (name + '.html')).read_text(encoding='utf-8')
        assert 'latest-results.html#exact-count-and-decomposition' in html
        assert 'data-downloads.html#september-16-research' in html
    assert 'app.append(september16ResearchUpdate());' in (SITE / 'latest-results.html').read_text(encoding='utf-8')
    assert 'september-16-research' in (SITE / 'data-downloads.html').read_text(encoding='utf-8')
    manifest = json.loads((BASE / 'PUBLICATION-MANIFEST.json').read_text())
    for row in manifest['artifacts']:
        assert 'FREEZE.json' not in row['path']
        assert not row['path'].endswith(('.exe', '.dll', '.so', '.pyd', '.env'))
        if row['path'].endswith('.json'):
            assert 'truth_bits_hex' not in (BASE / row['path']).read_text()
