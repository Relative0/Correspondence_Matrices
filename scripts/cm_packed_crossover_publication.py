"""Curate crossover findings without publishing operational receipts."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from statistics import median
import zipfile


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(data if isinstance(data,bytes) else data.encode('utf-8'))
def save(p,data):write(p,json.dumps(data,indent=2,ensure_ascii=False,sort_keys=True)+'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args(); evidence=args.evidence; root=args.root
    seal=load(evidence/'EXECUTION_SHA256SUMS.json')['files']
    assert all(sha(evidence/name)==digest for name,digest in seal.items()),'Evidence drift'
    site=root/'deliverables_n22_24/master_explainer_2026_08_03'
    folder=site/'results/2026-10-14/packed-crossover'
    if folder.exists():assert load(folder/'summary.json')['schema']=='cm-packed-crossover/v1','Refuse unrelated publication directory'
    folder.mkdir(parents=True,exist_ok=True)
    receipt=load(evidence/'FINAL_RECEIPT.json');verification=load(evidence/'RUN_VERIFICATION.json')
    assert verification['passed'] and receipt['valid_cells']==112 and not receipt['post_exit_gate_passed']
    rows=[json.loads(line) for line in (evidence/'ROWS.jsonl').read_text().splitlines()]
    public=[]
    for row in rows:
        r=row['resources']
        public.append({k:row[k] for k in ('cell','status','returncode','wall_ns','valid','result')} | {'resource_summary':{
            k:r[k] for k in ('cleanup_verified','cgroup_removed','peak_job_committed_bytes','pids_peak','memory_events','pids_events','cpu_stat','stdout_truncated','stderr_truncated')}})
    write(folder/'trials.jsonl',''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in public))
    for old,new in [('CASES.json','cases.json'),('SCHEDULE.json','schedule.json'),('PHASE_MEDIANS.json','phase-medians.json')]:
        write(folder/new,(evidence/old).read_bytes())
    source_names=['bitset_backend.py','cm_ir.py','cm_exprlib.py','cm_expr_serde.py','cmbench/__init__.py',
                  'cmbench/output_budget.py','cmbench/backends/__init__.py','cmbench/backends/packed_mask_cache.py']
    bundle={f'source/{name}':(evidence/'source'/name).read_bytes() for name in source_names}
    for name in ('trial.py','worker.py','verify_run.py','test_trial.py','linux_guard.py'):
        bundle[name]=(evidence/name).read_bytes()
    for path in (evidence/'inputs').glob('*.json'):bundle['inputs/'+path.name]=path.read_bytes()
    for old,new in [('CASES.json','CASES.json'),('SCHEDULE.json','SCHEDULE.json')]:bundle[new]=(evidence/old).read_bytes()
    bundle['README.txt']=b'Frozen algorithm subset and semantic controls. Python 3.12.3 / NumPy 2.3.2. Run test_trial.py for small untimed checks. No approval, installer, cloud tools or performance launcher is bundled. This is not the full operational reproduction archive.\n'
    with zipfile.ZipFile(folder/'frozen-source-and-controls.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(bundle.items()):
            info=zipfile.ZipInfo(name,(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(info,data)
    save(folder/'source-sha256.json',{'files':{name:hashlib.sha256(data).hexdigest() for name,data in bundle.items()},'baseline_subset_files':len(source_names)})
    host=load(evidence/'EXECUTION_HOST.json')['runtime']
    runtime_files={('site-packages/'+name.split('/site-packages/',1)[1]) if '/site-packages/' in name else 'interpreter/python3.12':digest for name,digest in host['files'].items()}
    save(folder/'runtime-sha256.json',{'python':'3.12.3','dependencies':host['dependencies'],'files':runtime_files,'restoration_exact_files':2056,
                                    'in_service_preserved':True,'post_exit_preserved':False,'post_exit_missing_files':2055,'deletion_cause':'unknown'})
    analyses=[]
    for result in verification['analysis']:
        ratios=[r['ratio_b_over_a'] for r in result['paired_ratios']]
        analyses.append(result | {'paired_median_ratio':median(ratios),'candidate_wins':sum(r<1 for r in ratios),'pairs':len(ratios)})
    summary={'schema':'cm-packed-crossover/v1','reviewed':'2026-10-14','status':'completed_verified_with_post_exit_preservation_failure',
             'decision':'Keep explicit backend selection; no dispatch threshold promotion.','scheduled_cells':112,'valid_cells':112,'matching_pairs':56,
             'native_route':{'available':False,'reason':'Numba absent; no native crossover measured.'},
             'contract':'Full named-basis packed outputs; three cold and five independently prepared fresh-process pairs per case. All startup/import/setup/q operations/validation/serialization/cleanup charged.',
             'ratio_direction':'candidate/reference full lifecycle; below 1 favors candidate. Median of paired ratios, not ratio of arm medians.',
             'qualification':'Seven synthetic selected edges. Width and query count are not isolated causal effects. No global dispatch threshold or native/74181/count-only inference.',
             'runtime_limitation':'Runtime hashes passed before/after measurements inside service, then the temporary runtime disappeared before later readback. Post-exit preservation gate failed. Same Linux boot; deletion cause unknown.',
             'source_receipts':[{ 'source':'work/packed-backend-crossover-20261014/'+name,'sha256':sha(evidence/name)} for name in
                  ('RESULT.md','SOURCE_SEAL.json','EXECUTION_SHA256SUMS.json','RUN_VERIFICATION.json','FINAL_RECEIPT.json','POST_EXECUTION.json','POST_RUNTIME_DIAGNOSIS.json')],
             'analyses':analyses,'resource_limits':{'elapsed_seconds':1200,'core_seconds':1200,'cpus':1,'memory_bytes':2147483648,'artifact_bytes':134217728,'single_output_bytes':67108864},
             'resource_results':{'conservative_elapsed_seconds':receipt['conservative_shared_elapsed_seconds'],'conservative_core_seconds':receipt['conservative_shared_core_seconds'],
                                 'experiment_peak_bytes':load(evidence/'EXECUTION.json')['resources']['peak_job_committed_bytes'],'services_and_cgroups_removed':True},
             'in_service_verification_checks':verification['checks'],'post_exit_gate_passed':False,
             'publication_scope':'Curated scientific rows, exact cases/orders, phase medians, source subset and anonymized library hashes. Raw operational receipts remain local; not a full operational reproduction archive.'}
    save(folder/'summary.json',summary)
    rows_html=''.join('<tr><td>'+html.escape(a['case'])+'</td><td>'+html.escape(a['numerator']+'/'+a['denominator'])+'</td><td>'+a['lifecycle']+'</td><td>'+f"{a['paired_median_ratio']:.4f}"+'</td><td>'+f"{a['candidate_wins']}/{a['pairs']}"+'</td></tr>' for a in analyses)
    downloads=''.join(f'<li><a href="{name}">{label}</a></li>' for name,label in [('summary.json','Summary and source receipts'),('trials.jsonl','All 112 curated timing records'),('cases.json','Exact cases, contexts and axis orders'),('schedule.json','Paired schedule'),('phase-medians.json','Phase medians'),('frozen-source-and-controls.zip','Frozen source subset and small controls'),('source-sha256.json','Archive source hashes'),('runtime-sha256.json','Interpreter and library hashes')])
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Packed-backend crossover findings — Correspondence Matrices</title><style>body{max-width:1050px;margin:auto;padding:24px;font:17px/1.6 system-ui,sans-serif;color:#172537;background:#f7fafc}a{color:#145ba4}h1{line-height:1.2}.notice{padding:16px;border-left:5px solid #b66b13;background:#fff4dc}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:8px;border-bottom:1px solid #c6d1dd}section{margin-top:32px}li{margin:8px 0}</style></head><body><nav><a href="../../../index.html">CM knowledge base</a> · <a href="../../../latest-results.html">Latest results</a> · <a href="../cpu-pilots/index.html">Predecessor CPU pilots</a></nav><main><h1>Packed-backend crossover findings</h1><p>Reviewed 14 October 2026 · Local WSL2 Ubuntu 24.04 · Seven synthetic comparisons</p><p><strong>Keep explicit backend selection.</strong> All 112 cells and 56 pairs passed independent full-output verification. No candidate had a prepared full-task paired median below 1; these cases do not justify a dispatch threshold or a general CM speedup.</p><p class="notice"><strong>Post-exit preservation failure:</strong> all runtime hashes matched inside the service before and after measurements. The temporary runtime then disappeared before independent readback. The same Linux boot was recorded; deletion cause is unknown. The later preservation gate failed. Source/pilot evidence was preserved and all owned services/cgroups were removed. This qualification accompanies all results.</p><section><h2>Matched full-task results</h2><p>Candidate/reference ratios below 1 favor the candidate. Median of individual paired ratios; three cold and five independently prepared pairs per case. Both session types start fresh and include startup, imports, setup, the complete q sequence, validation, serialization and cleanup.</p><div class="scroll"><table><thead><tr><th>Case</th><th>Candidate/reference</th><th>Lifecycle</th><th>Paired median</th><th>Candidate wins</th></tr></thead><tbody>'''+rows_html+'''</tbody></table></div><p>Full outputs execute 12, 20 or 22 influential axes; restrictions execute 10 or 16. All q64 restrictions produce 64 distinct functions. Permutations move influential axes. Width-20/22 and q1/q64 cases differ in structure or live width, so they do not isolate causal width/query effects. Numba was unavailable; no scalar native crossover was measured.</p></section><section><h2>What the phases show</h2><p>CSE lowers the small integer query subtotal but its preparation cost remains charged. CM adds compilation cost with similar q64 binding/query totals. NumPy words does not consistently offset mask and conversion preparation. Validation and process/import costs dominate these short full-task lifecycles. A resident-process application with a different validation contract needs its own measurement; these values cannot be substituted for that task.</p></section><section><h2>Resources and recovery</h2><p>Conservative elapsed/core accounting, including offline restoration and failed startups: '''+f"{receipt['conservative_shared_elapsed_seconds']:.2f}"+''' seconds, below both 1,200-second caps. Experiment cgroup peak: 60.58 MiB; the enclosing service also enforced one CPU, 2 GiB memory and zero swap. This experiment peak excludes guardian/restoration processes outside that branch. No experiment limit events, malformed output, timeout or incomplete pair occurred. Offline restoration matched all 2,056 frozen runtime hashes before timing. No paid resources or optional native installs were used.</p></section><section><h2>Evidence downloads</h2><p>Curated scientific evidence; operational paths and receipts remain local. This is not the full operational reproduction archive.</p><ul>'''+downloads+'''<li><a href="checksums.json">Public file checksums</a></li></ul></section><section><h2>Decision and next trigger</h2><p>No backend policy changes are supported by this trial. Defer another synthetic campaign until a concrete application decision needs it. Before future execution, investigate runtime deletion and prepare a persistent isolated runtime under scoped authorization. The earlier 74181 and exact-count comparisons remain separate contracts.</p></section></main></body></html>\n'''
    write(folder/'index.html',page)
    save(folder/'checksums.json',{'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(folder.iterdir()) if p.is_file() and p.name!='checksums.json'}})
    block='''\n/* October 14 packed crossover: full-task results and post-exit qualification. */
{
  const p = section("packed-crossover", "October 14 follow-up", "Packed-backend crossover: keep explicit backend choice",
    "Seven comparisons, 112 verified cells, and 64 distinct restrictions in q64 cases.");
  p.append(h("p", {text: "No consistent full-lifecycle advantage justified a dispatch threshold. Runtime hashes passed inside the service, but the temporary runtime disappeared before later readback; the post-exit preservation gate failed and the deletion cause is unknown."}));
  p.append(h("a", {href: "results/2026-10-14/packed-crossover/index.html", text: "Read paired results, phase findings, preservation limitation and evidence downloads"}));
  app.append(p);
}
'''
    for template,page_name in [('cm_master_template.html','index.html'),('cm_latest_results_template.html','latest-results.html'),('cm_downloads_template.html','data-downloads.html')]:
        target=site/template; text=target.read_text(encoding='utf-8')
        marker='app.append(h("footer",' if template=='cm_downloads_template.html' else 'app.append(pageFooter('
        assert text.count(marker)==1
        if 'const p = section("packed-crossover"' not in text:write(target,text.replace(marker,block+'\n'+marker))
        css=(site/'cm_master_shared.css').read_text(encoding='utf-8');lib=(site/'cm_master_shared.js').read_text(encoding='utf-8')
        data=json.dumps(load(site/'cm_master_data_2026_08_03.json'),separators=(',',':'),ensure_ascii=False)
        write(site/page_name,target.read_text(encoding='utf-8').replace('/*__CM_CSS__*/',css).replace('/*__CM_LIB__*/',lib).replace('/*__CM_DATA__*/null',data))
    write(root/'docs/audits/2026-10-14-packed-backend-crossover/REPORT.md',(evidence/'RESULT.md').read_bytes())
    print(json.dumps({'public_trial_records':112,'matching_pairs':56,'post_exit_gate_passed':False,'public_files':len(list(folder.iterdir()))}))


if __name__=='__main__':main()
