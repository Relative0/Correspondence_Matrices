"""Current evidence selection, graph identity and publication-path regressions."""
import ast
import hashlib
import os
import time
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT/'deliverables_n22_24/master_explainer_2026_08_03'


class LatestResultsWebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('cm_latest_results_test', SITE/'cm_latest_results_evidence.py')
        cls.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.module)
        cls.evidence, cls.numbers, cls.files = cls.module.build_latest_results()
        cls.data = json.loads((SITE/'cm_master_data_2026_08_03.json').read_text(encoding='utf-8'))

    def test_current_payload_equals_sealed_sources(self):
        self.assertEqual(self.data['e25_latest_results'], self.evidence)
        for key, record in self.numbers.items():
            self.assertEqual(self.data['_numbers'][key]['value'], record['value'], key)
            self.assertEqual(self.data['_numbers'][key]['prov'], record['prov'], key)

    def test_every_current_source_download_has_exact_bytes_and_hash(self):
        for name, payload in self.files.items():
            self.assertEqual((SITE/name).read_bytes(), payload, name)
        for source in self.evidence['sources'].values():
            payload = (SITE/source['href']).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), source['sha256'])
            self.assertEqual(len(payload), source['bytes'])
            self.assertIn(source['audit_seal'], self.evidence['audit_seals'].values())

    def test_full_site_snapshot_covers_the_same_data_as_every_page(self):
        for name, expected in self.module.site_snapshots(self.data).items():
            self.assertEqual((SITE/name).read_bytes(), expected, name)
        self.assertEqual(json.loads((SITE/'results/2026-09-11/full-site-data.json').read_text(encoding='utf-8')), self.data)

    def test_final_indexed_affine_attempt_controls_current_values(self):
        source = self.evidence['sources']['affine-final-indexed']
        self.assertIn('attempt-003/evidence/binding/', source['path'])
        panel = next(p for p in self.evidence['panels'] if p['id'] == 'affine-count')
        rows = [r for r in panel['rows'] if r['case'] == 'n_1800_k_0902_gap_28' and r['q'] == 8]
        current = next(r for r in rows if r['method'] == 'rows_indexed')
        original = next(r for r in rows if r['method'] == 'rows_legacy')
        self.assertLess(current['cold_ms'], 40)
        self.assertGreater(original['cold_ms'], 90)
        self.assertIn('ablation', original['label'])

    def test_corrected_process_memory_and_all_bucket_refusals_are_retained(self):
        self.assertIn('attempt-005/evidence/memory/', self.evidence['sources']['file-memory-corrected']['path'])
        bucket = next(p for p in self.evidence['panels'] if p['id'] == 'bucket-count')
        self.assertEqual(len(bucket['rows']), 420)
        self.assertEqual(len({r['case'] for r in bucket['rows']}), 35)
        for row in bucket['rows']:
            if row['status'] == 'refused':
                self.assertTrue(row['reason'])
                self.assertNotIn('cold_ms', row)
                self.assertNotIn('warm_ms', row)
        public = [r for r in bucket['rows'] if r['case'].startswith('model-') and r['method'] == 'numpy_min_fill' and r['q'] == 1]
        self.assertEqual(len(public), 11)
        self.assertEqual(sum(r['status'] == 'complete' for r in public), 10)

    def test_completed_native_batch_gate_is_not_a_future_or_positive_claim(self):
        panel = next(p for p in self.evidence['panels'] if p['id'] == 'native-batch')
        self.assertIn('completed no-go', panel['note'])
        self.assertLess(self.numbers['latest.batch.speedup']['value'], 1.10)

    def test_all_shared_figures_have_current_review_and_correct_data_identity(self):
        inventory = self.data['_freshness']['figures']
        self.assertGreaterEqual(len(inventory), 22)
        for figure, record in inventory.items():
            expected = hashlib.sha256(json.dumps({k:self.data[k] for k in record['datasets']}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            self.assertEqual(record['data_sha256'], expected, figure)
            self.assertEqual(record['reviewed'], '2026-09-11')
            if record['status'] == 'latest_accepted_for_this_contract': self.assertTrue(record['sources'])
        repeats = [r for r in self.data['e2_kernel_vs_cse_flat']['rows'] if r['group'] == 'repeat']
        self.assertEqual(len(repeats), 3)

    def test_all_nine_routes_include_current_results(self):
        for page in ('index','layperson','investor','expert','usecases','feature-model-evidence','learning-neural-evidence','data-downloads','latest-results'):
            text = (SITE/(page+'.html')).read_text(encoding='utf-8')
            self.assertIn('app.append(latestResultsUpdate());', text, page)
            self.assertIn('"reviewed":"2026-09-11"', text, page)
            self.assertIn('["latest-results.html", "Latest results"]', text, page)

    def test_new_pages_are_exact_template_expansions(self):
        css = (SITE/'cm_master_shared.css').read_text(encoding='utf-8')
        library = (SITE/'cm_master_shared.js').read_text(encoding='utf-8')
        data = json.dumps(self.data, separators=(',', ':'), ensure_ascii=False)
        for template, page in (('cm_downloads_template.html','data-downloads.html'), ('cm_latest_results_template.html','latest-results.html')):
            expected = (SITE/template).read_text(encoding='utf-8').replace('/*__CM_CSS__*/', css).replace('/*__CM_LIB__*/', library).replace('/*__CM_DATA__*/null', data)
            actual = (SITE/page).read_text(encoding='utf-8')
            self.assertEqual(hashlib.sha256(actual.encode()).hexdigest(), hashlib.sha256(expected.encode()).hexdigest(), page)

    def test_latest_repeat_headline_and_each_interval_equal_their_actual_audits(self):
        rows = [r for r in self.data['e2_kernel_vs_cse_flat']['rows'] if r['group'] == 'repeat']
        sources = [p for p in self.data['e2_kernel_vs_cse_flat']['provenance'] if 'statistical_inference.headline' in p]
        self.assertEqual(len(sources), 3)
        for row, source in zip(rows, sources):
            record = json.loads((ROOT/source.split(' :: ')[0]).read_text(encoding='utf-8'))['statistical_inference']['headline']
            self.assertEqual(row['value'], record['paired_formula_cluster_geomean'])
            self.assertEqual(row['lo'], record['paired_formula_cluster_bootstrap_ci95_low'])
            self.assertEqual(row['hi'], record['paired_formula_cluster_bootstrap_ci95_high'])
        for suffix, field in (('latest','value'),('latest.lo','lo'),('latest.hi','hi')):
            self.assertEqual(self.data['_numbers']['symv3.repeat.'+suffix]['value'], rows[-1][field])

    def test_release_gate_verifies_current_site_and_rejects_a_stale_page(self):
        spec = importlib.util.spec_from_file_location('cm_release_test', ROOT/'scripts/cm_website_release_verify.py')
        release = importlib.util.module_from_spec(spec); spec.loader.exec_module(release)
        self.assertEqual(release.verify(SITE)['status'], 'verified_for_publication')
        with tempfile.TemporaryDirectory(prefix='stale-site-test-', dir=ROOT/'build') as temporary:
            path = Path(temporary)
            (path/'index.html').write_bytes(b'old cached website')
            with self.assertRaisesRegex(ValueError, 'Stale generated page: index.html'):
                release.verify(path)
        workflow = (ROOT/'.github/workflows/publish-results-site.yml').read_text(encoding='utf-8')
        self.assertLess(workflow.index('cm_website_release_verify.py'), workflow.index('actions/upload-pages-artifact'))

    def test_generated_output_is_atomic_and_identical_output_does_not_touch_disk(self):
        tree = ast.parse((SITE/'cm_master_build_2026_08_03.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'write_generated')
        with tempfile.TemporaryDirectory(prefix='generated-output-test-', dir=ROOT/'build') as temporary:
            directory = Path(temporary)
            context = dict(Path=Path, tempfile=tempfile, os=os, time=time, HERE=directory)
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<write_generated>', 'exec'), context)
            target = directory/'page.html'
            context['write_generated'](target, b'current')
            with mock.patch.object(os, 'replace', side_effect=AssertionError('Unchanged file was replaced')):
                context['write_generated'](target, b'current')
            real_replace = os.replace
            attempts = []
            def temporarily_locked(source, destination):
                attempts.append(1)
                if len(attempts) < 3:
                    self.assertEqual(target.read_bytes(), b'current')
                    raise PermissionError('Transient Windows reader')
                return real_replace(source, destination)
            with mock.patch.object(os, 'replace', side_effect=temporarily_locked), mock.patch.object(time, 'sleep'):
                context['write_generated'](target, b'updated')
            self.assertEqual(target.read_bytes(), b'updated')
            self.assertEqual(len(attempts), 3)
            self.assertEqual(list(directory.glob('*.tmp')), [])
            with self.assertRaisesRegex(ValueError, 'escapes'):
                context['write_generated'](directory.parent/'outside.html', b'not written')

    def test_published_current_downloads_are_not_rewritten_to_an_old_commit(self):
        library = (SITE/'cm_master_shared.js').read_text(encoding='utf-8')
        code = library[library.index('const REVIEWED_EVIDENCE_REVISION'):library.index('const el =')]
        script = "const location={hostname:'relative0.github.io',pathname:'/Correspondence_Matrices/'};"+code+"\nif(hostedEvidenceHref('results/2026-09-11/current-results.json')!=='results/2026-09-11/current-results.json')throw Error('stale commit rewrite');"
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        workflow = (ROOT/'.github/workflows/publish-results-site.yml').read_text(encoding='utf-8')
        self.assertIn('latest-results.html', workflow)
        self.assertIn('cp -R "$site_dir/results" _site/results', workflow)


if __name__ == '__main__': unittest.main()
