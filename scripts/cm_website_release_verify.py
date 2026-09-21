"""Fail publication if a page, figure identity or result download is stale."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SITE = ROOT/'deliverables_n22_24/master_explainer_2026_08_03'
sys.path.insert(0, str(SOURCE_SITE))
from cm_findings_evidence import build_findings, DOWNLOAD as FINDINGS_DOWNLOAD
from cm_latest_results_evidence import build_latest_results, build_chart_freshness, site_snapshots

PAGES = {
    'cm_master_template.html': 'index.html', 'cm_layperson_template.html': 'layperson.html',
    'cm_investor_template.html': 'investor.html', 'cm_expert_template.html': 'expert.html',
    'cm_usecases_template.html': 'usecases.html', 'cm_feature_model_template.html': 'feature-model-evidence.html',
    'cm_learning_neural_template.html': 'learning-neural-evidence.html',
    'cm_findings_template.html': 'findings.html',
    'cm_late_scan_status_template.html': 'late-scan-status.html',
    'cm_p_series_study_guide_template.html': 'p-series-study-guide.html',
    'cm_downloads_template.html': 'data-downloads.html', 'cm_latest_results_template.html': 'latest-results.html',
}
P15_FINAL_DISPOSITION = 'results/2026-09-21/P15_FINAL_DISPOSITION_20260921.json'
P15_FINAL_DISPOSITION_SHA256 = '747b5241ecb15d55d34a6339e9a7c2be160c592b1b883a2823f17b8c0a75bbf8'

def digest(payload):
    return hashlib.sha256(payload).hexdigest()

def verify_late_scan_records(site: Path):
    """Keep the published P15 conclusion bound to its finalized audit record."""
    final_path = site / P15_FINAL_DISPOSITION
    payload = final_path.read_bytes()
    if digest(payload) != P15_FINAL_DISPOSITION_SHA256:
        raise ValueError('Stale or changed P15 final disposition')
    final = json.loads(payload)
    if (final['status'] != 'TIMING_INCONCLUSIVE_NO_PERFORMANCE_CLAIM' or
            final['decision']['p15_semantics'] != 'PASS on the sealed fresh corpus' or
            final['decision']['p15_timing'] != 'INCONCLUSIVE' or
            final['decision']['production_rollout'] != 'NOT AUTHORIZED AND NOT SUPPORTED' or
            final['timing']['accepted_worker_artifacts'] != 0):
        raise ValueError('P15 final disposition does not preserve its claim boundary')
    ledger_path = site / 'results/2026-09-20/p1-p15-research-ledger.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
    if ([row['phase'] for row in ledger['rows']] !=
            ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P7B', 'P8', 'P9', 'P10', 'P11', 'P12', 'P13', 'P14', 'P15']):
        raise ValueError('P1–P15 research ledger is incomplete')
    if (ledger['rows'][-2]['status'] != 'no_go' or
            ledger['rows'][-1]['status'] != 'semantic_pass_timing_inconclusive_no_performance_claim'):
        raise ValueError('P14/P15 dispositions are stale in the research ledger')
    guide_path = site / 'results/2026-09-22/p-series-study-guide.json'
    guide = json.loads(guide_path.read_text(encoding='utf-8'))
    if (guide.get('schema') != 'cm-p-series-study-guide/v1' or
            [row['phase'] for row in guide.get('studies', [])] !=
            ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P7B', 'P8', 'P9', 'P10', 'P11', 'P12', 'P13', 'P14', 'P15']):
        raise ValueError('P-series study guide is incomplete')
    if (guide['studies'][-2]['disposition'] != 'NO-GO' or
            guide['studies'][-1]['disposition'] != 'SEMANTIC PASS / TIMING INCONCLUSIVE'):
        raise ValueError('P14/P15 dispositions are stale in the P-series study guide')
    return {
        P15_FINAL_DISPOSITION: {'bytes': len(payload), 'sha256': digest(payload)},
        'results/2026-09-20/p1-p15-research-ledger.json': {
            'bytes': ledger_path.stat().st_size, 'sha256': digest(ledger_path.read_bytes())},
        'results/2026-09-22/p-series-study-guide.json': {
            'bytes': guide_path.stat().st_size, 'sha256': digest(guide_path.read_bytes())},
    }

def verify(site: Path):
    site = site.resolve()
    data = json.loads((SOURCE_SITE/'cm_master_data_2026_08_03.json').read_text(encoding='utf-8'))
    current, numbers, downloads = build_latest_results()
    if data['e25_latest_results'] != current:
        raise ValueError('Current result data differs from its sealed research sources')
    for key, number in numbers.items():
        if any(data['_numbers'][key][field] != number[field] for field in ('value', 'fmt', 'prov')):
            raise ValueError('Stale headline: '+key)
    if data['_freshness'] != build_chart_freshness(SOURCE_SITE, data):
        raise ValueError('Chart inventory or source identity is stale; rebuild the website')
    findings = build_findings(data)
    if data["e26_findings"] != findings:
        raise ValueError("Stale findings guide")
    downloads[FINDINGS_DOWNLOAD] = (json.dumps(findings, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    downloads.update(site_snapshots(data))
    payload = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    css = (SOURCE_SITE/'cm_master_shared.css').read_text(encoding='utf-8')
    library = (SOURCE_SITE/'cm_master_shared.js').read_text(encoding='utf-8')
    files = {}
    for template, page in PAGES.items():
        expected = (SOURCE_SITE/template).read_text(encoding='utf-8').replace('/*__CM_CSS__*/',css).replace('/*__CM_LIB__*/',library).replace('/*__CM_DATA__*/null',payload).encode('utf-8')
        actual = (site/page).read_bytes()
        if actual != expected: raise ValueError('Stale generated page: '+page)
        files[page] = {'bytes':len(actual),'sha256':digest(actual)}
    for relative, expected in downloads.items():
        actual = (site/relative).read_bytes()
        if actual != expected: raise ValueError('Stale result download: '+relative)
        files[relative] = {'bytes':len(actual),'sha256':digest(actual)}
    files.update(verify_late_scan_records(site))
    if (site/'neural').is_dir():
        manifest=json.loads((site/'neural/publication-manifest.json').read_text(encoding='utf-8'))
        for relative, record in manifest['files'].items():
            path=(site/'neural'/relative).resolve()
            if not path.is_relative_to(site/'neural'): raise ValueError('Neural source escapes publication directory')
            actual=path.read_bytes()
            if digest(actual)!=record['sha256'] or len(actual)!=record['bytes']:
                raise ValueError('Stale neural evidence: '+relative)
            files['neural/'+relative]=record
    return {'status':'verified_for_publication','reviewed':current['reviewed'],
            'pages':len(PAGES),'current_panels':len(current['panels']),
            'current_records':sum(len(p['rows']) for p in current['panels']),
            'shared_figure_definitions':len(data['_freshness']['figures']),
            'files':files,'publication_status':'not_a_deployment_receipt'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,default=SOURCE_SITE)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=verify(args.site)
    if args.output: args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in result.items() if key!='files'}))
