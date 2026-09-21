"""Current evidence selection, graph identity and publication-path regressions."""
import ast
import hashlib
import os
import time
import importlib.util
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
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
        self.assertEqual(self.evidence['reviewed'], '2026-09-16')
        for key, record in self.numbers.items():
            self.assertEqual(self.data['_numbers'][key]['value'], record['value'], key)
            self.assertEqual(self.data['_numbers'][key]['prov'], record['prov'], key)

    def test_fair_feature_model_successor_is_published_with_exact_identity(self):
        fair = self.evidence['fair_feature_model']
        payload = (SITE/fair['href']).read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), fair['sha256'])
        self.assertEqual(fair['coverage']['completed_cells'], fair['coverage']['scheduled_cells'])
        self.assertEqual(fair['coverage']['independently_replayed_distinct_structures'], 166)
        self.assertEqual([row['baseline'] for row in fair['equal_history_geomeans']],
                         ['cse', 'cnf', 'cudd_fixed', 'cudd_sift'])
        page = (SITE/'latest-results.html').read_text(encoding='utf-8')
        self.assertIn('section("fair-feature-model"', page)
        self.assertIn('feature-model-evidence.html#fair-lifecycle', page)

    def test_new_continuation_keeps_incomplete_values_unplotted_and_rejects_source_drift(self):
        panels = {p['id']:p for p in self.evidence['panels']}
        for key in ('projected-count-new','additional-public-count','pipe-consumer-new','preparation-reuse-new',
                    'application-feature','application-independent','component-feature','component-independent'):
            self.assertIn(key, panels)
            for row in panels[key]['rows']:
                if row['status'] != 'complete':
                    self.assertTrue(row['reason'])
                    for metric in panels[key]['metrics']: self.assertNotIn(metric, row)
        source = ROOT/self.evidence['sources']['next-research-summary']['path']
        real_read_bytes = Path.read_bytes
        with mock.patch.object(Path,'read_bytes',lambda path: real_read_bytes(path)+(b' ' if path==source else b'')):
            with self.assertRaisesRegex(ValueError,'Unsealed or changed website source'):
                self.module.build_latest_results()

    def test_every_current_source_download_has_exact_bytes_and_hash(self):
        for name, payload in self.files.items():
            self.assertEqual((SITE/name).read_bytes(), payload, name)
        for source in self.evidence['sources'].values():
            payload = (SITE/source['href']).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), source['sha256'])
            self.assertEqual(len(payload), source['bytes'])
            self.assertIn(source['audit_seal'], self.evidence['audit_seals'].values())

    def test_post_integration_confirmation_is_exact_manifest_driven_and_privacy_reviewed(self):
        confirmation = self.evidence['post_integration_confirmation']
        self.assertEqual(confirmation['status'], 'verified_multi_host_confirmation')
        self.assertEqual(confirmation['source_commit'], '63285d2bd16e16ca48d8a0328b6f6328ea038b35')
        self.assertEqual(confirmation['manifest']['artifact_count'], 24)
        self.assertTrue(confirmation['symmetric_wrapper']['windows']['all_exact'])
        self.assertTrue(confirmation['symmetric_wrapper']['linux']['all_exact'])
        self.assertAlmostEqual(confirmation['symmetric_wrapper']['windows']['bare_cm_over_cse_flat']['geomean'], 0.907508424013887)
        self.assertAlmostEqual(confirmation['symmetric_wrapper']['linux']['bare_cm_over_cse_flat']['geomean'], 0.9098481144011911)
        self.assertGreater(confirmation['symmetric_wrapper']['windows']['wrapper_cm_over_cse_flat']['geomean'],
                           confirmation['symmetric_wrapper']['historical_accepted_v3']['cm_wrapper_over_cse_flat_current']['geomean'])
        forbidden = ('C:\\\\', '/root/', 'runpod_pod_id', 'g8y75vqj83fcvt')
        for record in confirmation['manifest']['artifacts']:
            payload = (SITE/record['href']).read_bytes()
            self.assertEqual(len(payload), record['bytes'], record['name'])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), record['sha256'], record['name'])
            text = payload.decode('utf-8', errors='ignore')
            self.assertFalse(any(value in text for value in forbidden), record['name'])
        latest = (SITE/'latest-results.html').read_text(encoding='utf-8')
        downloads = (SITE/'data-downloads.html').read_text(encoding='utf-8')
        self.assertIn('app.append(postIntegrationConfirmationUpdate());', latest)
        self.assertIn('section("september-16-confirmation"', downloads)

    def test_full_site_snapshot_covers_the_same_data_as_every_page(self):
        for name, expected in self.module.site_snapshots(self.data).items():
            self.assertEqual((SITE/name).read_bytes(), expected, name)
        self.assertEqual(json.loads((SITE/f'results/{self.module.REVIEWED}/full-site-data.json').read_text(encoding='utf-8')), self.data)

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
            self.assertEqual(record['reviewed'], self.module.REVIEWED)
            if record['status'] == 'latest_accepted_for_this_contract': self.assertTrue(record['sources'])
        repeats = [r for r in self.data['e2_kernel_vs_cse_flat']['rows'] if r['group'] == 'repeat']
        self.assertEqual(len(repeats), 3)

    def test_historical_source_identity_survives_checkout_line_endings_but_detects_edits(self):
        real_read_bytes = Path.read_bytes
        sources = {ROOT/source['path'] for figure in self.data['_freshness']['figures'].values() for source in figure['sources']}
        def line_endings(path, crlf):
            payload = real_read_bytes(path)
            if path in sources:
                payload = payload.replace(b'\r\n', b'\n')
                if crlf: payload = payload.replace(b'\n', b'\r\n')
            return payload
        for crlf in (False, True):
            with mock.patch.object(Path, 'read_bytes', lambda path: line_endings(path, crlf)):
                self.assertEqual(self.module.build_chart_freshness(SITE, self.data), self.data['_freshness'])
        changed = next(iter(sources))
        with mock.patch.object(Path, 'read_bytes', lambda path: real_read_bytes(path) + (b' altered evidence' if path == changed else b'')):
            self.assertNotEqual(self.module.build_chart_freshness(SITE, self.data), self.data['_freshness'])
        for figure in self.data['_freshness']['figures'].values():
            for source in figure['sources']:
                self.assertEqual(source['hash_mode'], 'text_lf_line_endings')

    def test_all_nine_routes_include_current_results(self):
        for page in ('index','layperson','investor','expert','usecases','feature-model-evidence','learning-neural-evidence','data-downloads','latest-results'):
            text = (SITE/(page+'.html')).read_text(encoding='utf-8')
            self.assertIn('app.append(latestResultsUpdate());', text, page)
            self.assertIn('"reviewed":"'+self.module.REVIEWED+'"', text, page)
            self.assertIn('["latest-results.html", "Latest results"]', text, page)

    def test_new_pages_are_exact_template_expansions(self):
        css = (SITE/'cm_master_shared.css').read_text(encoding='utf-8')
        library = (SITE/'cm_master_shared.js').read_text(encoding='utf-8')
        data = json.dumps(self.data, separators=(',', ':'), ensure_ascii=False)
        for template, page in (('cm_downloads_template.html','data-downloads.html'), ('cm_latest_results_template.html','latest-results.html')):
            expected = (SITE/template).read_text(encoding='utf-8').replace('/*__CM_CSS__*/', css).replace('/*__CM_LIB__*/', library).replace('/*__CM_DATA__*/null', data)
            actual = (SITE/page).read_text(encoding='utf-8')
            self.assertEqual(hashlib.sha256(actual.encode()).hexdigest(), hashlib.sha256(expected.encode()).hexdigest(), page)

    def test_late_scan_status_is_generated_and_preserves_the_final_p15_boundary(self):
        css = (SITE/'cm_master_shared.css').read_text(encoding='utf-8')
        library = (SITE/'cm_master_shared.js').read_text(encoding='utf-8')
        data = json.dumps(self.data, separators=(',', ':'), ensure_ascii=False)
        expected = (SITE/'cm_late_scan_status_template.html').read_text(encoding='utf-8').replace(
            '/*__CM_CSS__*/', css).replace('/*__CM_LIB__*/', library).replace('/*__CM_DATA__*/null', data)
        page = (SITE/'late-scan-status.html').read_text(encoding='utf-8')
        self.assertEqual(page, expected)
        for required in ('NO-GO', 'Production change', 'None', 'P15 semantics', 'PASS',
                         'P15 timing', 'Inconclusive', '0 accepted', 'not a measured speedup',
                         'no performance or production claim', 'P15_FINAL_DISPOSITION_20260921.json'):
            self.assertIn(required, page)
        self.assertIn('late-scan-status.html', (SITE/'index.html').read_text(encoding='utf-8'))

    def test_p_series_study_guide_is_generated_and_keeps_each_phase_boundary_visible(self):
        css = (SITE/'cm_master_shared.css').read_text(encoding='utf-8')
        library = (SITE/'cm_master_shared.js').read_text(encoding='utf-8')
        data = json.dumps(self.data, separators=(',', ':'), ensure_ascii=False)
        expected = (SITE/'cm_p_series_study_guide_template.html').read_text(encoding='utf-8').replace(
            '/*__CM_CSS__*/', css).replace('/*__CM_LIB__*/', library).replace('/*__CM_DATA__*/null', data)
        page = (SITE/'p-series-study-guide.html').read_text(encoding='utf-8')
        self.assertEqual(page, expected)
        for required in ('P1', 'P7B', 'P14', 'P15', 'MECHANISM PASS — NOT A PRODUCTION RESULT',
                         'SEMANTIC PASS / TIMING INCONCLUSIVE', '0.5752', '2.2259', '1.0508', '1.0607',
                         '490', 'Accepted timing worker artifacts', 'not a timing comparison', 'p-series-study-guide.json'):
            self.assertIn(required, page)
        self.assertIn('p-series-study-guide.html', (SITE/'index.html').read_text(encoding='utf-8'))

    def test_p_series_study_guide_download_is_complete_and_preserves_p14_p15_dispositions(self):
        guide = json.loads((SITE/'results/2026-09-22/p-series-study-guide.json').read_text(encoding='utf-8'))
        self.assertEqual(guide['schema'], 'cm-p-series-study-guide/v1')
        self.assertEqual([study['phase'] for study in guide['studies']],
                         ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P7B', 'P8', 'P9', 'P10', 'P11', 'P12', 'P13', 'P14', 'P15'])
        self.assertEqual(guide['studies'][-2]['disposition'], 'NO-GO')
        self.assertEqual(guide['studies'][-1]['disposition'], 'SEMANTIC PASS / TIMING INCONCLUSIVE')
        self.assertEqual(guide['studies'][-1]['metrics'][0]['value'], 490)
        self.assertEqual(guide['studies'][-1]['metrics'][1]['value'], 0)

    def test_p1_p15_ledger_is_complete_and_keeps_negative_results_visible(self):
        ledger = json.loads((SITE/'results/2026-09-20/p1-p15-research-ledger.json').read_text(encoding='utf-8'))
        self.assertEqual(ledger['schema'], 'cm-p1-p15-research-ledger/v1')
        self.assertEqual([row['phase'] for row in ledger['rows']],
                         ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P7B', 'P8', 'P9', 'P10', 'P11', 'P12', 'P13', 'P14', 'P15'])
        self.assertEqual(ledger['reviewed'], '2026-09-21')
        self.assertEqual(ledger['rows'][-1]['status'], 'semantic_pass_timing_inconclusive_no_performance_claim')
        self.assertIn('P15_FINAL_DISPOSITION_20260921.json', ledger['artifact_roots'][-1])
        page = (SITE/'late-scan-status.html').read_text(encoding='utf-8')
        self.assertIn('P1–P15 research ledger', page)
        self.assertIn('p1-p15-research-ledger.json', page)

    def test_final_p15_disposition_preserves_the_semantic_only_claim_boundary(self):
        record = json.loads((SITE/'results/2026-09-21/P15_FINAL_DISPOSITION_20260921.json').read_text(encoding='utf-8'))
        self.assertEqual(record['status'], 'TIMING_INCONCLUSIVE_NO_PERFORMANCE_CLAIM')
        self.assertEqual(record['decision']['p15_semantics'], 'PASS on the sealed fresh corpus')
        self.assertEqual(record['decision']['p15_timing'], 'INCONCLUSIVE')
        self.assertEqual(record['timing']['accepted_worker_artifacts'], 0)
        self.assertEqual(record['decision']['production_rollout'], 'NOT AUTHORIZED AND NOT SUPPORTED')

    def test_frontier_contracts_do_not_relabel_old_timings_or_promote_unverified_counts(self):
        frontier = self.evidence['frontiers']
        self.assertEqual(sum(m['concrete_feature_equivalence'] is True for m in frontier['models']), 9)
        self.assertEqual(sum(m['original_feature_equivalence'] is False for m in frontier['models']), 2)
        self.assertEqual(frontier['consumer']['natural_sessions_admitted'], 0)
        verified = [row for row in frontier['independent_methods'] if row['independently_cross_checked']]
        self.assertEqual({(r['case'],r['method']) for r in verified},
                         {('independent-01','cudd_dynamic'),('independent-02','cudd_dynamic')})
        self.assertEqual(frontier['oracle']['timed_outputs_matched'], 336)
        self.assertEqual(sum(frontier['independent_status_counts'].values()), 90)
        for panel in self.evidence['panels']:
            self.assertEqual(panel['measured'], '2026-09-12' if panel['id'].startswith('component-') else '2026-09-11')
        oracle = frontier['closure_oracle']
        self.assertEqual((oracle['feature_completed'], oracle['independent_completed']), (72, 48))
        self.assertEqual(len(oracle['entries']), 120)
        for kind in ('feature', 'independent'):
            self.assertEqual(oracle[kind+'_cross_checked'], sum(r['independently_cross_checked'] for r in oracle['entries'] if r['kind'] == kind))
        self.assertTrue(frontier['epfl_origin']['rows'][0]['retained_exact'])
        self.assertFalse(frontier['regression']['new_failure_ids'])
        self.assertIn('app.append(frontierResultsUpdate());', (SITE/'latest-results.html').read_text(encoding='utf-8'))
        source = ROOT/self.evidence['sources']['count-closures-summary']['path']
        real_read_bytes = Path.read_bytes
        with mock.patch.object(Path, 'read_bytes', lambda path: real_read_bytes(path)+(b' ' if path==source else b'')):
            with self.assertRaisesRegex(ValueError, 'Unsealed or changed website source'):
                self.module.build_latest_results()

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

    def test_final_closure_preserves_historical_scope_and_balanced_candidate_results(self):
        latest = self.evidence['completion']
        oracle = self.evidence['frontiers']['closure_oracle']
        self.assertEqual((oracle['feature_cross_checked'], oracle['independent_cross_checked']), (72, 48))
        self.assertTrue(all(row['independently_cross_checked'] for row in oracle['entries']))
        earlier = json.loads(self.files[self.evidence['sources']['count-closures-summary']['href']])
        self.assertEqual(earlier['closure_oracle']['feature_cross_checked'], 71)
        closure = latest['independent_count']
        row = next(r for r in oracle['entries'] if (r['case'], r['context_index']) == ('additional-09', 7))
        self.assertEqual(row['exact_value'], closure['total'])
        self.assertFalse(closure['proof_certificate_produced'])
        self.assertEqual((closure['terminal_leaves'], closure['partition_assignments_checked']), (34, 1024))
        historical = latest['historical']
        self.assertEqual((historical['passed'], historical['total'], historical['new_local_passes']), (21, 21, 10))
        self.assertEqual(len({r['test'] for r in historical['rows']}), 21)
        self.assertEqual(sum('3.13.15' in r['runtime'] for r in historical['rows']), 3)
        self.assertIn('not a rerun', historical['note'])
        candidate = latest['component']
        self.assertEqual((candidate['cells'], candidate['outputs_checked']), (180, 1344))
        self.assertEqual(len(candidate['case_table']), 7)
        self.assertTrue(any(r['peak_rss_ratio'] > 1 for r in candidate['case_table']))
        self.assertEqual(sum(r['parent_wall_reduction_percent'] < .1 for r in candidate['case_table']), 2)
        self.assertEqual(latest['remaining']['required_execution'], [])
        self.assertFalse(latest['remaining']['production_default_changed'])
        source = ROOT/self.evidence['sources']['component-historical-closure']['path']
        real_read_bytes = Path.read_bytes
        with mock.patch.object(Path, 'read_bytes', lambda path: real_read_bytes(path)+(b' ' if path == source else b'')):
            with self.assertRaisesRegex(ValueError, 'Unsealed or changed website source'):
                self.module.build_latest_results()

    def test_legacy_pod_labels_are_distinct_on_windows_and_linux(self):
        tree = ast.parse((SITE/'cm_master_build_2026_08_03.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'pod_run_name')
        for path_class in (PurePosixPath, PureWindowsPath):
            context = dict(Path=path_class)
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<pod_run_name>', 'exec'), context)
            for path in ('b6_replication/pod3_example', 'b6_replication\\pod3_example'):
                self.assertEqual(context['pod_run_name'](path), 'pod3_example')
        pods = self.data['e5_pods']['pods']
        self.assertEqual(len({row['label'] for row in pods}), len(pods))
        for row in pods:
            self.assertEqual(row['label'], row['dir'].rsplit('/', 1)[-1].split('_')[0])

    def test_release_gate_verifies_current_site_and_rejects_a_stale_page(self):
        spec = importlib.util.spec_from_file_location('cm_release_test', ROOT/'scripts/cm_website_release_verify.py')
        release = importlib.util.module_from_spec(spec); spec.loader.exec_module(release)
        self.assertEqual(release.verify(SITE)['status'], 'verified_for_publication')
        with tempfile.TemporaryDirectory(prefix='stale-site-test-') as temporary:
            path = Path(temporary)
            (path/'index.html').write_bytes(b'old cached website')
            with self.assertRaisesRegex(ValueError, 'Stale generated page: index.html'):
                release.verify(path)
        workflow = (ROOT/'.github/workflows/publish-results-site.yml').read_text(encoding='utf-8')
        self.assertLess(workflow.index('cm_website_release_verify.py'), workflow.index('actions/upload-pages-artifact'))

    def test_generated_output_is_atomic_and_identical_output_does_not_touch_disk(self):
        tree = ast.parse((SITE/'cm_master_build_2026_08_03.py').read_text(encoding='utf-8'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'write_generated')
        with tempfile.TemporaryDirectory(prefix='generated-output-test-') as temporary:
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
        self.assertIn('late-scan-status.html', workflow)
        self.assertIn('p-series-study-guide.html', workflow)
        self.assertIn('cp -R "$site_dir/results" _site/results', workflow)


if __name__ == '__main__': unittest.main()
