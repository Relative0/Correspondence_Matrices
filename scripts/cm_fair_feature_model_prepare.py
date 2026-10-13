"""Prepare immutable source/input selection; no cloud operations."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.cm_fair_feature_model_benchmark import ARMS, encoded, sha, write

AUDIT=ROOT/'docs/audits/2026-09-13-cm-fair-feature-model'
SOURCE=AUDIT/'source-v3'
CLEAN=ROOT/'build/cm-final-web'
HISTORY='deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/configuration-fm-version-delta-full21-2026-08-27/cases.jsonl'


def main():
    AUDIT.mkdir(exist_ok=True)
    SOURCE.mkdir()
    names=['bitset_backend.py','cm_ir.py','cm_exprlib.py','cmbench/__init__.py',
           'cmbench/output_budget.py','scripts/cm_measurement_verify.py']
    for name in names:
        target=SOURCE/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((CLEAN/name).read_bytes())
    for name in ('scripts/cm_fair_feature_model_benchmark.py',
                 'scripts/cm_fair_feature_model_verify.py',
                 'scripts/cm_fair_feature_model_prepare.py',
                 'tests/test_cm_fair_feature_model_benchmark.py'):
        target=SOURCE/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    raw=(CLEAN/HISTORY).read_bytes()
    assert sha(raw)=='3a4a394f458e0064994b4339858401e523f8dea836a3a697120f9db83299ef0e'
    (SOURCE/'historical-cases.jsonl').write_bytes(raw)
    candidates=[json.loads(line) for line in raw.splitlines()]
    cases,ledger,seen=[],[],set()
    for row in sorted(candidates,key=lambda r:(r['case_id'].split('@')[0],r['k'],r['slice_kind']!='incidence',r['case_id'])):
        history=row['case_id'].split('@')[0]
        key=(history,row['k'])
        eligible=max(len(row['earlier_residual']),len(row['later_residual']))<=4096
        selected=eligible and key not in seen
        ledger.append(dict(id=row['case_id'],selected=selected,
            reason='first_eligible_incidence_preferred_transition_per_history_and_width' if selected else
                   'exceeds_4096_clause_input_limit' if not eligible else 'one_transition_per_history_and_width'))
        if not selected: continue
        seen.add(key)
        for version in ('earlier','later'):
            cases.append(dict(id=row['case_id']+'|'+version,history=history,k=row['k'],
                clauses=row[version+'_residual'],source_record_sha256=sha(encoded(row)),
                feature_names=row['feature_names'],version=version))
    assert len(cases)==42 and len(seen)==21
    schedule=[]
    for block in range(5):
        for i,case in enumerate(cases):
            shift=(i+block)%len(ARMS)
            for arm in ARMS[shift:]+ARMS[:shift]:
                schedule.append(dict(case_id=case['id'],arm=arm,block=block))
    files=[dict(path=p.relative_to(SOURCE).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
        for p in sorted(SOURCE.rglob('*')) if p.is_file()]
    protocol=dict(schema='cm-fair-fm-protocol/v1',cases=cases,selection_ledger=ledger,schedule=schedule,
        files=files,campaign_seconds=1800,worker_wall_seconds=20,worker_cpu_seconds=15,
        worker_address_space_bytes=2<<30,source_commit='b48e3a50f0efa415142d4c760cbf42bd9218826f',
        task='complete vector, bit a is assignment with x0 least significant; little-endian bytes',
        input_boundary='Frozen conditioned residual CNF JSON. Full-model parse, witness search and conditioning excluded equally.',
        lifecycle='Five counterbalanced fresh build/reload pairs; five unbatched warm recomputations each; no answer caches.',
        bdd_contract='Native dd.cudd; fixed explicitly disables reorder; sift enables dynamic reorder and charges final explicit sift. Saved graphs retain variable names and final order.',
        timing='Cold includes input read/parse, imports, construction/lowering, first-use binding and output bytes. Parent wall also includes process startup, five warm queries, artifact serialization and cleanup. Reload includes SHA check/read/reconstruction. OS file cache uncontrolled.',
        memory='Linux ru_maxrss in KiB over entire worker lifecycle, plus pre-import process highwater; no claim that subtraction is incremental peak.',
        interpretation='Descriptive implementation comparison on exposed local slices, not held-out confirmation, full-model ranking, scalar count comparison, or all historical M01-M13 closure. Equal history weighting. No changes to defaults.',
        exclusions='d4 scalar counting has a different output contract. d4 full-output adapter, full input-conditioning costs and revision reuse remain separate studies.')
    protocol['admission']='At most 4096 residual clauses in each version. Incidence slices preferred; then hash. No output or timing-based selection.'
    protocol['preparation_revision']='v3 preserves v2 inputs and schedule. V2 produced exact outputs, but all CUDD workers emitted shutdown assertions because recursive closure memo tables retained native node references. V3 clears closures and node references, explicitly closes every arm, includes teardown in the saved/reload lifecycle, and rejects nonempty worker diagnostic logs. No tuning or input selection based on v2 timing.'
    protocol['cleanup']='Release each engine explicitly; record cleanup_ns and include it in save/reload lifecycle. Parent wall includes all cleanup. Reject nonempty worker logs.'
    write(SOURCE/'PROTOCOL.json',protocol)
    write(AUDIT/'PREPARATION-v3.json',dict(protocol_sha256=sha((SOURCE/'PROTOCOL.json').read_bytes()),
        cases=len(cases),cells=len(schedule),workers=len(schedule)*2,source_files=len(files)))
    print(json.dumps(dict(cases=len(cases),cells=len(schedule),source_files=len(files))))

if __name__=='__main__': main()
