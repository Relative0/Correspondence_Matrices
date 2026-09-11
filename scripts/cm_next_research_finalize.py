"""Seal scientific evidence and copy its explicit publication allowlist."""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'docs/audits/2026-09-11-cm-next-research'
CHECKOUT=ROOT/'build/cm-next'
sys.path.insert(0,str(CHECKOUT))
from scripts.cm_research_publication import scan_bytes


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())


def report(v,p):
    counted=sum(x['checked_query_outputs'] for x in v['counts'].values())+sum(x['checked_query_outputs'] for x in v['isolated'].values())
    public_status=Counter(r['status'] for r in p['public'])
    projected=next(r for r in p['synthetic'] if (r['case'],r['mode'],r['method'])==('adjacent_exclusion-48','projected','bucket_min_fill'))
    native=next(r for r in p['synthetic'] if (r['case'],r['mode'],r['method'])==('adjacent_exclusion-48','projected','cudd_natural'))
    lines=[
      '# Integrated continuation: implementations, tests and measured limits',
      '',
      'All seven avenues from the continuation plan were pursued. The new APIs and research controls are implemented; the broad suite has no new failures against the published checkout. This is a bounded research completion, not a claim that every historical repository test passes or that an invented trace is production evidence.',
      '',
      '## Implementation and regression results',
      '',
      '- Integrated the preceding packed-mask, cache, stream, factorized, affine and bucket/array work into a separate checkout based on published revision `d15cb618f4eb99b6621e4ab24773a00f03ae484e`. The shared dirty research checkout was not staged or reverted.',
      '- Added `ProjectedCNFCountPlan`: exact distinct selected-variable assignments after existential hidden-variable elimination. Fixed contexts can include both groups; empty projection is 0/1; unused selected variables and arbitrary-precision counts are preserved. Hidden variables are eliminated first with Boolean OR, then selected variables with integer sum. The object-array adapter uses the same semantics and limits.',
      '- Added explicit scalar-plan adapters at the existing comparative task boundary for count, SAT-status, partial-context and version-history outputs. Default backend lists and global routing remain unchanged. Unsupported witnesses, delta outputs and non-affine inputs are rejected. This is a real repository call site with synthetic contract tests, not a deployed application trace.',
      '- Fixed fresh-checkout website tests that assumed a build directory existed. Made the historical H6 portability test use a hash-pinned published closure, and added rejection checks for changed backend/task bytes. Historical freezes and strict validators were not rewritten or weakened.',
      f"- Final Linux suite: **{p['regression_summary']['passed']:,} passed**, **{p['regression_summary']['subtests passed']:,} subtests passed**, {p['regression_summary']['skipped']} skipped; **{p['regression_summary']['failed']} failed and {p['regression_summary']['errors']} errored**. Every final failure/error also failed on the published checkout on the same host. The published baseline was 1,450 passed, 1,175 subtests passed, 40 failed, 35 errors and two skipped. There are zero new failed tests; two baseline failures were fixed. The final differential records every individual result.",
      '- Remaining failures include missing historical research datasets, unavailable Linux replacements for pinned Windows DLLs/native tools, and strict historical source/line-ending bindings. They are retained in the report and full JUnit/log artifacts. Missing CPU PyTorch and PySAT were supplied for the second and final broad runs; those dependency omissions are not silently counted as passing tests.',
      '- Independent projection checks cover every three-variable Boolean function and every projection subset, random partial contexts, expression/CM ingress, forced/unused variables, large integers, concurrent calls, native existential counting, and analytic recurrence controls. The remote new-API set had 64 passing tests. CI now exercises the explicit APIs on its Windows and Linux matrix.',
      '',
      '## Counting studies and unfavorable results',
      '',
      f'- Four original campaign runs and two isolated-method diagnostics checked **{counted:,} cold/warm query outputs**. Repetitions are measurements of the same frozen inputs; they are not independent application diversity.',
      '- Synthetic development uses 8/12 selected variables and confirmation uses 24/48. Independent auxiliaries, adjacent exclusions and deliberately difficult hidden stars were specified before timings. Full and projected contracts are both retained. The latest synthetic replay is attempt-010; attempt-006 remains a consumed earlier run on the same provider machine.',
      f"- In the latest 48-variable adjacent-exclusion projection, Python min-fill took {projected['cold_ms']:.3f} ms per cold 32-query session versus {native['cold_ms']:.3f} ms for natural-order CUDD. The new contract is exact and useful as an explicit facility, but this is not a general native-performance win. Arrays also lose on these thin projection families. All three bucket variants refuse the two hidden-star projection cases under the frozen width limit.",
      '- Public selection was predeclared: choose the smallest whole DIMACS file per previously unused system in the pinned SoftVarE benchmark commit, sort by byte count/path, then take 12. Nine satisfy the 64-KiB, 512-variable, 3,000-clause admission; three screening refusals remain visible. All files have Git-blob and SHA-256 identities and upstream licensing. No file slicing or substitution was used.',
      '- The public contracts count either all declared variables or even-position selected variables. The conversion does not establish original feature-product semantics. The 32-request trace fixes up to three variables, including auxiliaries, with a frozen seed. Limits are width 14, 262,144 cells/work, two million ordering checks, 2 GiB process address space and 120 seconds per child.',
      '- Original attempts 007 and 011 used different provider machine IDs. Their eight completed case/contract groups agreed exactly; ten case/contract groups failed or timed out before measurement because the preliminary natural-order native control could not finish. Both runs retain all 450 missing scheduled rows. Virtualized placements and shared CPUs do not establish broad architecture generalization.',
      f"- The corrected diagnostic isolates each method and retains its failure independently. Latest public results contain {public_status['complete']} complete method/contract cells, {public_status['refused']} explicit admission refusals and {public_status['incomplete']} incomplete native/other cells. Inputs and limits are unchanged. Per-method repetitions are grouped, so no paired confidence or fresh-confirmation claim is made for these consumed diagnostics. Earlier native failures are not reclassified as algorithm answers.",
      '',
      '## Pipe delivery, memory and preparation',
      '',
      '- A separate process consumed real OS-pipe output at n22/n24, unthrottled or after 0.5-ms delays per up-to-4-KiB read. All 288 complete/cancelled transfers matched an independent NumPy parity oracle and the reader hash. Four chunk widths, including a complete-output control, ran in nine alternating fresh-process repetitions. Process startup, producer completion and reader completion are distinguished.',
      '- A writer can acknowledge a large write after the reader has already consumed part of it. The recorded first successful write-return time is an upper bound on first byte acceptance, not its arrival time. The public graph uses the first reader-chunk return instead. Cancellation stops at chunk boundaries and cannot interrupt an already-started complete-output chunk. No durable-storage claim is made for pipes.',
      '- Under n24 slow-reader delivery, 8-KiB chunks used roughly 68 MiB summed producer/reader peak RSS versus roughly 129 MiB for complete output on this run. These are sums of separate lifetime peaks, an upper bound rather than simultaneous memory. Consumer backpressure largely determines completion time; reduced memory is not automatically a throughput gain.',
      f"- The four-thread pressure soak completed {p['headlines']['soak_queries']:,} exact queries in 120 seconds across widths 16–20. Cache-owned payload stayed within 2 MiB. Caller-held environments remained valid after clear; retained plans and environments were released, and final cache ownership was zero. RSS reflects allocator behavior and was measured rather than assumed to return to baseline. This is a two-minute controlled soak, not a production leak certification.",
      '- The 324 preparation measurements compare existing-expression compilation, checked disk JSON reload plus compilation, and resident reuse for projected/affine inputs at q1/q32/q256. Reload was slower than fresh compilation; no compiled serialization optimization was justified. Resident reuse avoids repeated setup only after a useful plan lifetime exists. The public data also provides the resident call with its separately measured original setup charged, and original fsync storage costs.',
      '',
      '## Cost, custody and remaining limits',
      '',
      f"- Authorized RunPod cap: $10. Nonrefunded attempt reservations total ${v['reserved_usd']:.2f}. The conservative accounting bound is ${v['estimated_cost_upper_usd']:.4f}, including a full $0.25 contingency for the uncertain HTTP-500 creation. These are recorded rate/lifetime estimates, not posted billing. The local tool pause delayed result retrieval/deletion for two completed pods; their entire observed lifetimes remain charged in this bound.",
      '- Every observed owned pod has an exact name/ID cleanup receipt. The uncertain creation retains its complete watchdog reconciliation. Other projects sharing the account were neither stopped nor modified. An automatic approval block for one rerun was cleared after proving its 82 source files were identical to an already approved upload and passing the recursive secret scanner.',
      '- Scientific artifacts and source freezes are published from an explicit allowlist. API authentication remains on the controller. Account inventories and operational logs that mention other projects remain local; an operations checksum manifest binds those receipts without publishing their contents.',
      '- Remaining work depends on new evidence: genuine consumer request traces and plan lifetimes, original feature-to-auxiliary projection mappings, broader independent systems, and restoration of historical/platform test fixtures. Existing failed native batch, router, incremental and GPU avenues were not reopened without a new mechanism. No general speedup or default-router promotion follows from these experiments.',
      '',
      'Publication is recorded separately in `2026-09-11-cm-next-publication`; this research seal is not itself a live deployment receipt.',
      '',
    ]
    (AUDIT/'REPORT.md').write_text('\n'.join(lines))


def finalize():
    if (AUDIT/'FINAL-MANIFEST.json').exists(): raise RuntimeError('Research already sealed')
    v=read(AUDIT/'VERIFICATION.json'); p=read(AUDIT/'PUBLIC-RESULTS.json')
    assert not v['final_regression']['new_failures'] and len(v['isolated'])==2
    assert all(r['cleanup_verified'] for r in v['attempts'].values())
    watchdog=read(AUDIT/'attempt-005/WATCHDOG-RESULT.json')
    assert watchdog['status']=='horizon_reconciled' and watchdog['final']['owned_pod_absent']
    report(v,p)
    selected=set()
    top=('PLAN.md','REPORT.md','CORPUS-PROTOCOL.md','CANDIDATES.json','CORPUS.json','COUNT-FIXTURES.json','COUNT-SCHEDULE.json',
         'INTEGRATION-SOURCES.json','DEPENDENCIES.json','REGRESSION-DEPENDENCIES.json','TORCH-CPU-METADATA.txt','TOOLS.json',
         'H6-FIXTURE.json','VERIFICATION.json','PUBLIC-RESULTS.json','BASELINE-FAILURES.json')
    selected.update(AUDIT/name for name in top)
    for pattern in ('*-SOURCES.json','*-COMMANDS.json','*-DEPENDENCIES.json'):
        selected.update(AUDIT.glob(pattern))
    for directory in ('packages','corpus','transport-sources'):
        selected.update(p for p in (AUDIT/directory).rglob('*') if p.is_file())
    for evidence in AUDIT.glob('attempt-*/evidence'):
        for path in evidence.rglob('*'):
            if not path.is_file(): continue
            if 'transport' not in path.relative_to(evidence).parts or path.name in ('SOURCE_VERIFICATION.json','PLACEMENT.json'):
                selected.add(path)
    # The final broad run's log is necessary to distinguish normal tests from
    # JUnit's separate subtest records. It contains no account/API information.
    selected.add(AUDIT/'attempt-014/evidence/transport/full-regression-final.log')
    operations={p.relative_to(AUDIT).as_posix():sha(p) for p in AUDIT.rglob('*') if p.is_file() and p not in selected
                and p.name not in ('OPERATIONS-MANIFEST.json','FINAL-MANIFEST.json','FINAL-MANIFEST.sha256')}
    (AUDIT/'OPERATIONS-MANIFEST.json').write_text(json.dumps(dict(schema='cm-private-operations-checksums/v1',artifacts=operations,
         scope='Local custody; contents omitted from the public release'),indent=2)+'\n')
    selected.add(AUDIT/'OPERATIONS-MANIFEST.json')
    artifacts={}
    for path in sorted(selected):
        relative=path.relative_to(AUDIT).as_posix(); payload=path.read_bytes()
        scan_bytes(relative,payload)
        artifacts[relative]=dict(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
    sources=read(AUDIT/'packages/regression-final-FREEZE.json')['source']['files']
    current={name:sha(CHECKOUT/name) for name in sources if not name.startswith('docs/audits/') and name!='tests/test_cm_latest_results_website.py'}
    # Every algorithm/test source in this seal is still the tested source.
    assert all(value==sources[name] for name,value in current.items())
    for relative in ('scripts/cm_next_evidence_verify.py','scripts/cm_next_public_results.py','scripts/cm_next_research_finalize.py',
                     'scripts/runpod_next_research_controller.py','scripts/cm_next_research_remote.py',
                     'scripts/cm_next_research_package.py','scripts/cm_next_research_corpus.py'):
        shutil.copyfile(ROOT/relative,CHECKOUT/relative); current[relative]=sha(CHECKOUT/relative)
    manifest=dict(schema='cm-next-research-seal/v1',sealed_utc=datetime.now(timezone.utc).isoformat(),
        scope='Bounded scientific continuation; final publication checks have a separate seal',
        artifacts=artifacts,current_sources=current,base_commit='d15cb618f4eb99b6621e4ab24773a00f03ae484e',
        previous_audits=read(AUDIT/'INTEGRATION-SOURCES.json')['prior_seals'])
    (AUDIT/'FINAL-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    seal=sha(AUDIT/'FINAL-MANIFEST.json'); (AUDIT/'FINAL-MANIFEST.sha256').write_text(seal+'\n')
    destination=CHECKOUT/AUDIT.relative_to(ROOT)
    for path in selected|{AUDIT/'FINAL-MANIFEST.json',AUDIT/'FINAL-MANIFEST.sha256'}:
        target=destination/path.relative_to(AUDIT); target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    loader=CHECKOUT/'deliverables_n22_24/master_explainer_2026_08_03/cm_latest_results_evidence.py'
    text=loader.read_text(); assert text.count('NEXT_RESEARCH_SEAL_PENDING')==1
    loader.write_text(text.replace('NEXT_RESEARCH_SEAL_PENDING',seal),newline='\n')
    print(json.dumps(dict(seal=seal,scientific_artifacts=len(artifacts),source_files=len(current),scientific_bytes=sum(r['bytes'] for r in artifacts.values()))))


if __name__=='__main__': finalize()
