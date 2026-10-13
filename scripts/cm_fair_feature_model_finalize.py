"""Record verified conclusions, current cleanup, and seal local evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import types

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import runpod_fair_feature_model_controller_v4 as controller

AUDIT=ROOT/'docs/audits/2026-09-13-cm-fair-feature-model'


def write(path,data):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,sort_keys=True,indent=2)
        stream.write('\n')


def main():
    verification=json.loads((AUDIT/'VERIFICATION-v3.json').read_bytes())
    assert verification['status_counts']=={'ok':1050}
    client=controller.preflight.session()
    try: inventories=controller.shared.inventories(client)
    finally: client.close()
    runs=[(p.parent.name,json.loads(p.read_bytes())) for p in sorted(AUDIT.glob('attempt-*/RUN.json'))]
    owned={r['pod_id'] for _,r in runs}
    assert all(r['cleanup']['owned_pod_absent'] for _,r in runs)
    assert not any(r['id'] in owned for rows in inventories.values() for r in rows)
    cost=dict(checked_utc=controller.preflight.utc_now(),all_owned_pods_absent=True,
        inventories=inventories,reserved_usd=sum(json.loads(p.read_bytes())['reserved_usd']
            for p in AUDIT.glob('attempt-*/RESERVATION.json')),
        conservative_estimated_cost_usd=sum(r['cost_upper_bound_usd'] for _,r in runs),
        posted_billing_available=False,authorized_campaign_ceiling_usd=5,
        initial_tranche_used_only=True,remaining_reservation_allowance_usd=3,
        estimates_do_not_refund_reservations=True,
        attempts=[dict(attempt=name,status=r['status'],pod_id=r['pod_id'],
            owned_pod_absent=r['cleanup']['owned_pod_absent'],estimate_usd=r['cost_upper_bound_usd'])
            for name,r in runs])
    write(AUDIT/'COST-AND-CLEANUP.json',cost)
    current=json.loads((AUDIT/'source-v3/PROTOCOL.json').read_bytes())
    for row in current['files']:
        assert hashlib.sha256((AUDIT/'source-v3'/row['path']).read_bytes()).hexdigest()==row['sha256']
    study=json.loads((AUDIT/'attempt-004/evidence/study/summary.json').read_bytes())
    comparisons={(r['baseline'],r['metric']):r['baseline_over_cm_equal_history_geomean']
                 for r in verification['comparisons']}
    table=['| Baseline | Cold first output | Warm recomputation | Fresh reload | Build/save/reload/cleanup |',
           '| --- | ---: | ---: | ---: | ---: |']
    for arm in ('cse','cnf','cudd_fixed','cudd_sift'):
        vals=[comparisons[arm,metric] for metric in ('build_cold_total_ns','build_warm_median_ns',
              'reload_cold_total_ns','save_reload_lifecycle_ns')]
        table.append('| '+arm+' | '+' | '.join(f'{v:.4f}' for v in vals)+' |')
    resource=['| Arm | Build worker RSS highwater, median KiB | Serialized bundle range, bytes |',
              '| --- | ---: | ---: |']
    for arm in ('cm','cse','cnf','cudd_fixed','cudd_sift'):
        rows=[r for r in verification['medians'] if r['arm']==arm]
        resource.append(f"| {arm} | {statistics.median(r['build_rss_highwater_kib'] for r in rows):.0f} | "
                        f"{min(r['artifact_bytes'] for r in rows):.0f}–{max(r['artifact_bytes'] for r in rows):.0f} |")
    report=f'''# Fair Linux feature-model benchmark: completed

The accepted corrected run passed **1,050/1,050 cells**, comprising **2,100 fresh
workers**, on 42 saved slices from seven histories at widths 8, 12 and 16.
All cold, warm and reloaded outputs agreed with an independent exhaustive scalar
oracle. Independent replay verified all 166 distinct saved structures. All
2,100 worker diagnostic logs were empty, and all four Linux contract tests passed.
The accepted study took {study['elapsed_s']:.2f} seconds ({study['elapsed_s']/60:.2f} minutes).

## What the measurements show

Each number below is **baseline time divided by CM time**, calculated from
per-case medians with equal weighting across histories. Above 1 favors CM;
below 1 favors the baseline. These are descriptive results, not confidence
intervals or a universal ranking.

{chr(10).join(table)}

CM warm recomputation was {comparisons['cse','build_warm_median_ns']:.2f} times
as fast as CSE, but its cold first-output time was
{1/comparisons['cse','build_cold_total_ns']:.2f} times CSE's. Fresh CM/CSE reload
was approximately equal. Direct CNF and both CUDD variants beat CM on warm
recomputation. CM beat CUDD on this adapter's charged cold/reload obligations.
These different results are why warm ratios must not substitute for lifecycle costs.

Cold measurements include per-arm dependency imports. Direct CNF needs neither
NumPy nor CUDD, so it has especially small measured cold costs on this bounded,
sparse cohort. Those large internal cold ratios are not whole-process speedups:
the parent also incurs interpreter startup, supervision and result handling.
Parent-wall medians include timed-wait exit-observation overhead and are too
coarse for interpreting the near-zero CM/CSE differences as a precise gain.

## Scope and limits

- All arms produce the same complete truth vector, not unlike scalar-count and
  vector tasks. Input begins at frozen conditioned residual CNF JSON. Full-model
  parsing, witness search and conditioning are excluded equally.
- Five counterbalanced fresh build/reload blocks; five unbatched warm
  recomputations per worker. Warm samples are not independent experimental units.
- Artifacts contain structure and explicit variable universes, never answers.
  CUDD fixed order is explicitly disabled for reordering; the sifted arm charges
  automatic reordering and final explicit sifting. Its actual graph and final
  named variable order are preserved and correctly restored.
- Serialization, first query, reload, explicit cleanup, and whole-parent wall
  are retained separately. OS file-cache state is uncontrolled.
- These are exposed historical slices, not held-out confirmation. Thirty-two
  have one satisfying assignment; the other ten have two or four. Most paired
  revisions are unchanged. The 4,096-clause admission cap excludes six large
  Linux incidence candidates; eligible hash slices retain that history.
- d4 scalar counting, full-model execution, meaningful revision reuse, and real
  consumer traces remain separate studies. This does not close every M01–M13
  qualification and does not justify changing production defaults.

## Memory and artifacts

{chr(10).join(resource)}

RSS is Linux process highwater over the entire worker lifecycle, including
imports, warm work and serialization. A pre-import highwater is also retained;
subtracting it is not interpreted as incremental peak. Bundle sizes describe
these canonical JSON adapters, not intrinsic representation compactness or
native DDDMP size. All artifacts are self-describing for the same bounded task.

## Attempts, correction, cost and cleanup

1. Unexecuted v1 preparation was superseded after input-size preflight; no
   timing informed the admission change. Its draft receipts are historical.
2. Attempt 001 (v2) produced exact results but all 840 CUDD workers emitted
   shutdown assertions. Recursive closures retained native-node references.
   It is preserved as superseded evidence, not included in accepted statistics.
3. V3 releases those references, explicitly closes every engine, charges cleanup,
   and rejects worker diagnostic output. Inputs and schedule are identical to v2;
   no timing-based tuning or reselection occurred.
4. Attempts 002 and 003 could not get a ready endpoint on the same RunPod machine;
   neither started benchmark cells. Both pods were deleted.
5. Attempt 004 requested AP-JP-1, ran the unchanged v3 bundle on another machine,
   and passed. Result retrieval was delayed after the approximately six-minute
   computation; recorded cost includes the entire allocation through deletion.

All four owned pods are now absent in both API inventories. Conservative estimated
total cost: **${cost['conservative_estimated_cost_usd']:.5f}**; posted billing is
unavailable. **$2.00 was reserved** across four attempts under conservative
nonrefunded reservation accounting. The authorized $5 ceiling was not needed.

## Evidence and reproduction

- Accepted package: `packages/fair-feature-model-v3.zip`; region retry has identical bytes.
- Frozen protocol and measured source: `source-v3/PROTOCOL.json` and `source-v3/`.
- Accepted raw ledger/artifacts: `attempt-004/evidence/study/`.
- Independent verification, all medians and source/file hashes: `VERIFICATION-v3.json`.
- Native tests and host/dependency receipts: `attempt-004/evidence/transport/`.
- Earlier execution: `VERIFICATION.json`, `V2-DISPOSITION.json`, and prior attempt directories.
- Budget and fresh cleanup check: `COST-AND-CLEANUP.json`.

Verification was run with the project virtualenv against the frozen v3 verifier:

```text
python -X utf8 -B scripts/cm_fair_feature_model_verify.py --output ../attempt-004/evidence/study --protocol PROTOCOL.json --destination ../VERIFICATION-v3.json
```

No production source defaults, commits, pushes, or website publication were made.
The root's 31 pre-existing tracked modifications remain unrelated and untouched.

The next useful step is a concise website update explaining these separate cold,
warm and reload results and preserving the sparse-cohort limitation. Further
compute should wait for a materially different consumer workload or reuse question.
'''
    shutil.copyfile(AUDIT/'REPORT.md',AUDIT/'PREPARATION-REPORT.md')
    (AUDIT/'REPORT.md').write_text(report,encoding='utf-8')
    # Capture task sources and imported project transport modules, never session
    # objects, environments, API credentials or dependency caches.
    paths=set(ROOT.glob('scripts/*fair_feature_model*.py'))|{ROOT/'tests/test_cm_fair_feature_model_benchmark.py'}
    visited=set()
    def visit(module):
        if id(module) in visited: return
        visited.add(id(module))
        name=getattr(module,'__file__',None)
        if not name: return
        path=Path(name).resolve()
        if not path.is_relative_to(ROOT) or '.venv' in path.parts: return
        if path.suffix=='.py': paths.add(path)
        for value in vars(module).values():
            if isinstance(value,types.ModuleType): visit(value)
    visit(controller)
    for path in sorted(paths):
        target=AUDIT/'local-source-snapshots'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    tracked=subprocess.run(['git','status','--short','-uno'],cwd=ROOT,capture_output=True,text=True,check=True)
    write(AUDIT/'WORKSPACE-STATUS.json',dict(tracked_status=tracked.stdout,
        tracked_modified_count=len(tracked.stdout.splitlines()),
        new_work='Scoped untracked benchmark scripts, test and audit; no tracked production changes.'))
    files=[dict(path=p.relative_to(AUDIT).as_posix(),bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(AUDIT.rglob('*')) if p.is_file()]
    write(AUDIT/'FINAL-MANIFEST.json',dict(schema='cm-fair-fm-audit-seal/v1',files=files))
    for row in files:
        raw=(AUDIT/row['path']).read_bytes()
        assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    seal=hashlib.sha256((AUDIT/'FINAL-MANIFEST.json').read_bytes()).hexdigest()
    write(AUDIT/'SEAL-VERIFICATION.json',dict(manifest_sha256=seal,files=len(files),all_hashes_match=True,
        excluded_self_describing_files=['FINAL-MANIFEST.json','SEAL-VERIFICATION.json']))
    print(json.dumps(dict(verified_cells=1050,files=len(files),manifest_sha256=seal,
                         estimated_cost_usd=cost['conservative_estimated_cost_usd'],all_owned_pods_absent=True)))

if __name__=='__main__': main()
