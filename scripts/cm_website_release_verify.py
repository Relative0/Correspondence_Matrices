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
    'cm_downloads_template.html': 'data-downloads.html', 'cm_latest_results_template.html': 'latest-results.html',
}

def digest(payload):
    return hashlib.sha256(payload).hexdigest()

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
