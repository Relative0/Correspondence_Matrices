"""Reconstruct public mappings/miters and validate exact retained source custody."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cmbench.comparative.feature_mapping import feature_mapping,equivalence_miter,concrete_equivalence_miter,projection_dimacs
from cmbench.comparative.sxfm_semantics import projected_equivalence_miter

AUDIT=ROOT/'docs/audits/2026-09-12-cm-evidence-frontiers'

def read(name):return json.loads((AUDIT/name).read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'))

def verify():
    seal=read('FINAL-MANIFEST.json')
    expected=(AUDIT/'FINAL-MANIFEST.sha256').read_text().split()[0]
    assert sha(AUDIT/'FINAL-MANIFEST.json')==expected
    for name,record in seal['artifacts'].items():
        path=AUDIT/name
        assert path.resolve().is_relative_to(AUDIT.resolve())
        assert path.stat().st_size==record['bytes'] and sha(path)==record['sha256'],name
    for name,digest in seal['current_sources'].items():assert sha(ROOT/name)==digest,name
    pairs=read('FEATURE-PAIRINGS.json');mappings=read('FEATURE-MAPPINGS.json');maps={}
    miters={r['id']:r for r in read('FEATURE-MITERS.json')}
    sxfm={r['id']:r for r in read('SXFM-MITERS.json')}
    concrete={r['id']:r for r in read('CONCRETE-MITERS.json')}
    checked=0
    for pair,record in zip(pairs,mappings):
        xml=(AUDIT/'upstream/features'/next(n for n in pair['originals'] if n.endswith('.xml'))).read_bytes()
        cnf_path=ROOT/'docs/audits/2026-09-11-cm-next-research/corpus'/(pair['id']+'.dimacs')
        assert hashlib.sha256(xml).hexdigest()==record['xml_sha256'] and sha(cnf_path)==record['cnf_sha256']
        try:mapping=feature_mapping(xml,cnf_path.read_text())
        except ValueError:
            assert record['status']=='refused';continue
        assert record['status']=='identity_mapped'
        for key in ('features','feature_variables','concrete_variables','unmatched_variables'):
            assert canonical(mapping[key])==canonical(record[key]),(pair['id'],key)
        maps[pair['id']]=(xml,mapping)
        for frozen,builder in ((miters,equivalence_miter),(sxfm,projected_equivalence_miter),(concrete,concrete_equivalence_miter)):
            if pair['id'] not in frozen:continue
            clauses,n=builder(xml,mapping);saved=frozen[pair['id']]
            assert canonical(clauses)==canonical(saved['clauses']) and n==saved['n'],pair['id']
            checked+=1
    counterexamples=read('FEATURE-COUNTEREXAMPLES.json')
    for row in counterexamples:
        xml,mapping=maps[row['case']]
        values={f['variable']:row['feature_assignment'][f['id']] for f in mapping['features']}
        assert all(any(values[abs(v)]==(v>0) for v in c) for c in mapping['clauses'])
        root_name=ET.fromstring(xml).find('struct')[0].attrib['name']
        assert row['feature_assignment'][root_name] is False
        assert row['cnf_satisfied'] is True and row['xml_satisfied'] is False
    admissions={r['id']:r for r in read('INDEPENDENT-ADMISSIONS.json')}
    cases={r['id']:r for r in read('INDEPENDENT-CASES.json')}
    for selected in read('INDEPENDENT-SELECTION.json'):
        compressed=(AUDIT/'upstream/counting'/selected['path']).read_bytes();raw=gzip.decompress(compressed)
        admitted=admissions[selected['id']]
        assert hashlib.sha256(compressed).hexdigest()==admitted['compressed_sha256']
        assert hashlib.sha256(raw).hexdigest()==admitted['dimacs_sha256']
        try:n,clauses,projection=projection_dimacs(raw.decode())
        except ValueError:
            assert admitted['status']=='refused';continue
        case=cases[selected['id']]
        assert n==case['n'] and canonical(clauses)==canonical(case['clauses'])
        assert [v-1 for v in projection]==case['projected']
    for profile in read('SOURCE-PROFILES.json').values():
        for name,record in profile['members'].items():
            if 'object' in record:assert sha(AUDIT/record['object'])==record['sha256']
            elif 'repository_archive' in record:assert sha(ROOT/record['repository_archive'])==record['sha256']
            else:assert read('FIXTURE-RESTORATION.json')['files'][name]['sha256']==record['sha256']
    return dict(status='pass',artifacts=len(seal['artifacts']),current_sources=len(seal['current_sources']),
        regenerated_miters=checked,validated_counterexamples=len(counterexamples),
        independent_admitted=len(cases),solver_rerun=False,seal_sha256=expected)

if __name__=='__main__':print(json.dumps(verify(),indent=2))
