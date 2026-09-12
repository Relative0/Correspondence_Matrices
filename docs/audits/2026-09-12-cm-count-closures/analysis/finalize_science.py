"""Seal new public research artifacts while keeping operational credentials local."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-closures'
DEST=CHECKOUT/'docs/audits/2026-09-12-cm-count-closures'
sys.path.insert(0,str(CHECKOUT))
from scripts.cm_research_publication import scan_bytes
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def put(name,data):
    scan_bytes(name,data);target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==data,name
    else:target.write_bytes(data)
def write(name,value):put(name,(json.dumps(value,indent=2)+'\n').encode())

assert not (DEST/'FINAL-MANIFEST.json').exists()
public=read(AUDIT/'PUBLIC-RESULTS.json');verification=read(AUDIT/'VERIFICATION.json')
assert verification['status']=='pass' and public['cost']['all_created_pods_deleted']
for name in ('PLAN.md','PUBLIC-RESULTS.json','VERIFICATION.json','HISTORICAL-SOURCE-SEARCH.json','PRIOR-RESERVATIONS.json','REGRESSION-TRIAGE.json'):
    put(name,(AUDIT/name).read_bytes())
for path in sorted(AUDIT.glob('*-PROTOCOL.json')):put(path.name,path.read_bytes())
for path in sorted((AUDIT/'upstream').rglob('*')):
    if path.is_file():put(path.relative_to(AUDIT).as_posix(),path.read_bytes())
put('upstream/EPFL-LICENSE',(ROOT/'external/epfl-benchmarks/LICENSE').read_bytes())
put('receipt-bytes/GIT-ATTRIBUTES.txt',(CHECKOUT/'.gitattributes').read_bytes())
for name in ('setup_phase.py','prepare_retry.py','package.py','prepare_regression.py','restore_receipts.py',
             'audit_epfl_origin.py','audit_source_candidates.py','analyze_closures.py','triage_regression.py','finalize_science.py'):
    put('analysis/'+name,(AUDIT/name).read_bytes())
profiles={}
for path in sorted((AUDIT/'packages').glob('*-FREEZE.json')):
    freeze=read(path);profile=freeze['profile'];bundle=AUDIT/'packages'/(profile+'.zip')
    assert sha(bundle.read_bytes())==freeze['bundle_sha256']
    put('profiles/'+path.name,path.read_bytes());members={}
    with zipfile.ZipFile(bundle) as archive:
        for member in archive.infolist():
            data=archive.read(member);digest=sha(data);name=member.filename
            object_name='source_objects/'+digest+(Path(name).suffix or '.txt')
            put(object_name,data);members[name]=dict(sha256=digest,bytes=len(data),object=object_name)
    profiles[profile]=dict(freeze='profiles/'+path.name,members=members)
write('SOURCE-PROFILES.json',profiles)
for attempt in verification['attempts']:
    directory=AUDIT/attempt['id']
    for path in sorted((directory/'evidence').rglob('*')):
        if path.is_file():put(path.relative_to(AUDIT).as_posix(),path.read_bytes())
    local={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(directory.iterdir()) if p.is_file()}
    write(attempt['id']+'/OPERATIONAL-CUSTODY.json',dict(summary=attempt,local_receipts=local))

sources=['cmbench/comparative/component_counts.py','scripts/cm_d4_closure_oracle.py','scripts/cm_ganak_closure_oracle.py','scripts/cm_remaining_count_oracle.py',
         'scripts/cm_closure_oracle_retry.py','scripts/cm_component_count_study.py','scripts/restore_cm_closure_fixtures.py',
         'scripts/verify_cm_count_closures.py','tests/test_component_counts.py','tests/test_closure_fixture_restoration.py',
         'docs/research/CM_COUNT_CLOSURES.md']
sources += [r['path'] for r in read(DEST/'RECEIPT-RESTORATION.json')]
for name in ('runpod_closure_research_controller.py','runpod_closure_research_controller_v2.py',
             'cm_closure_research_remote.py','cm_closure_research_remote_v2.py'):
    data=(ROOT/'scripts'/name).read_bytes();scan_bytes(name,data)
    path=CHECKOUT/'scripts'/name
    if path.exists():assert path.read_bytes()==data
    else:path.write_bytes(data)
    sources.append('scripts/'+name)
c=public['regression']['counts'];f=public['fixtures'];o=public['closure_oracle'];s=public['component_study'];cost=public['cost']
rows='\n'.join('| '+kind+' | '+' | '.join(str(s[kind]['status_counts'].get(k,0)) for k in ('complete','refused','timeout','failed'))+' |' for kind in ('feature','independent'))
report=f'''# Count and historical evidence closure

All 72 concrete-feature and 48 admitted independent contexts now have completed
exact counts. {o['feature_cross_checked']}/72 feature and
{o['independent_cross_checked']}/48 independent contexts have agreement between
separately implemented counters. These are exact integer results, not certified
proofs. All old and new refusals, timeouts and native errors remain retained.

## Independent counters

The d4 competition binary is bound to upstream commit
`15eff31962466804a48374826b9e5a746fc2766e` and SHA-256
`29cb30f351ed92b02343e5e7a98b082e949d9838245f37c0bcdecf68a57ffd39`.
Its source uses integer arithmetic for projected counting. A fresh forced-true
selected sentinel prevents an empty projection from being treated as full model
counting; the transformation preserves every projected count. All 36 controls
passed, including arbitrary-size integers, free selected axes and empty projections.
The binary is downloaded directly from immutable upstream and not redistributed.

The first new Ganak pass completed seven of eight formerly timed-out queries;
decisionmaking context 7 ended in `std::bad_alloc` at its 2 GiB cap. d4 completed
all eight decisionmaking queries and two of eight QIF3 queries at 90 seconds each.
All overlapping completed values agreed. The separate final follow-up gave the
six remaining QIF3 d4 queries 240 seconds each and retried the one Ganak memory
failure at 6 GiB and 120 seconds. All six QIF3 follow-ups completed; Ganak timed
out. A final separately frozen pass attempts d4 on all eight additional-07
contexts at 90 seconds each and Ganak decisionmaking context 7 at 240 seconds.
See PUBLIC-RESULTS.json for every final outcome
and the list of values still lacking a second counter. The unchanged Ganak
invocation is nonprobabilistic integer mode. Changed caps and placements are not
paired before/after timing comparisons.

## Residual-component representation

The new Python candidate conditions each request, propagates units and splits
residual formulas into components using every variable, including hidden axes.
It adds disjoint selected branches and existentially ORs hidden-only branches.
Free selected axes contribute exact powers of two. Memoization is exact and fresh
for every query. Input, work, node, recursion and cache limits are explicit; no
partial answer is returned on refusal. The default backend is unchanged.

The controls compare 1,280 independently enumerated formulas/contexts with both
cache modes, plus structural, large-integer, wide-clause and refusal edge cases.
The prospectively frozen benchmark has all nine feature and six independent
cases, three methods, eight contexts and three fresh-process repetitions. Every
worker has 15 seconds and 2 GiB address space. Setup, all cold requests and cleanup
are charged; warm outputs are internally checked for equality.

| Cohort | Complete cells | Refused | Timeout | Native/error |
| --- | ---: | ---: | ---: | ---: |
{rows}

Every one of {s['timed_outputs_checked']} completed timed query outputs matches
Ganak or d4. Only complete three-repetition results are plotted. Candidate
completed feature cases: {', '.join(s['feature']['candidate_completed_cases']) or 'none'}.
Candidate completed independent cases: {', '.join(s['independent']['candidate_completed_cases']) or 'none'}.
Cases beyond the prior methods' coverage: {', '.join(s['feature']['newly_completed_cases']+s['independent']['newly_completed_cases']) or 'none'}.
These findings apply to this bounded workload and host; they do not establish a
general speedup or authorize production promotion. Attempt-003 timed out fetching
source before any test or benchmark ran. Attempt-004 retains the same scientific
protocol and extends only that bootstrap download deadline from 300 to 600 seconds.

The candidate is faster than the paired dynamic CUDD arm on additional-01,
additional-02 and additional-04, close but slightly slower on additional-03,
and slower on additional-08. Arrays are faster on additional-02. It completes
additional-05 and additional-06 where both paired controls fail their bounds;
these also expand coverage beyond the earlier five-method study. No
aggregate claim hides these regressions or treats a refusal as zero runtime.
The two unfinished feature cases reach the 100,000-node cap; all six independent
cases reach the 20-million-work-unit cap. Future representation work can target
those specific limits using a new protocol instead of silently raising defaults.

## Historical recovery and corrected source-origin finding

Another 46 original public CNFs restore against the existing P6 freeze, for 318
dependencies including prior phases. The exact empty output directory recorded
by an old preflight refusal is also reconstructed. No cloud action is replayed.
Three tracked files recover surviving original CRLF bytes: the architecture retry
analysis and RUN receipt, and the EPFL pilot raw data. Their existing independent
hashes, values and test expectations are unchanged; Git attributes preserve them.

Current Linux replay: **{c['passed']:,} passed plus {c['subtests_passed']:,} subtests,
{c['failed']} failures, {c['errors']} errors and {c['skipped']} skipped**.
This phase recovers {f['newly_recovered_failure_ids']} prior failing IDs, with zero
new failing IDs. The focused checks pass {public['regression']['focused_passed']} tests.
The historical suite is not green. Remaining failures and their original details
are in PUBLIC-RESULTS.json. A bounded search of 117 surviving same-named backend
files, two local Git versions and 77 pinned archive members found no copy matching
the backend required by three historical packages. That search does not cover
every possible backup, and current code is not replaced with an approximation.
REGRESSION-TRIAGE.json classifies nine Windows-native-on-Linux issues, three
specific missing historical-backend issues and nine other historical replay or
source checks. These categories describe the observed failure, not a guarantee
that there are no further downstream issues.

The EPFL origin discrepancy is resolved. The retained int2float file exactly
matches the declared upstream revision, SHA-256
`6d6e8253b30010fe5b2f574e55e19fd9ce35a7872cd8012a246b716f143121c2`
and Git blob `5c202a31a74dc2b4da0d1ac59377e92c6c37c6d9`. The old audit normalized
retained CRLF to LF but compared it against an upstream blob that already uses
CRLF. That asymmetric normalization caused a false mismatch. Old evidence is
preserved; no source file or historical expected hash was changed for this finding.

## Custody and next work

All seven created research pods were deleted. New conservative rate/lifetime bound:
${cost['new_conservative_bound_usd']:.9f}; cumulative bound:
${cost['combined_conservative_bound_usd']:.9f}. Combined reservations are $9.50
under the $10 authorization. Website validation may have later reservations in
the separate publication audit. These bounds are not posted billing.

The actual video production remains presentation-only evidence. Its capture
adapter awaits an independently needed render; zero natural backend-use sessions
are admitted. Remaining work includes any still singly checked counts, the
representation's documented limits and recovery of historical source/platform
closures. A new study needs a new protocol; previous exposed results must not be
relabeled prospective. Site rebuilding and exact-commit CI follow this science seal.

Primary sources: [d4 pinned source](https://github.com/crillab/d4v2/tree/15eff31962466804a48374826b9e5a746fc2766e),
[EPFL declared revision](https://github.com/lsils/benchmarks/tree/0060e156826e733d69bf5b3322d1bdd0d03a1f9a),
[Ganak](https://github.com/meelgroup/ganak).
'''
put('REPORT.md',report.encode())
put('NEXT-AGENT-PROMPT.md',f'''Continue from build/cm-closures and its published count-closure audit. Read REPORT.md, PUBLIC-RESULTS.json and the separate root publication audit before running anything. Preserve all old seals and the shared dirty parent. All 120 fixed contexts have a completed count; {o['feature_cross_checked']+o['independent_cross_checked']} have independent counter agreement. The new component counter's complete and refused cases are recorded. Do not repeat completed studies merely to obtain better timings.

The final broad replay has {c['passed']} passes, {c['failed']} failures and {c['errors']} errors, with zero new failing IDs. The historical exact backend search is bounded and found no matching copy. The former EPFL mismatch is resolved as asymmetric normalization: raw bytes match declared upstream. Do not continue claiming an unknown EPFL origin.

Remaining: independently motivated production capture, documented backend demand if it exists, any singly checked counts, new bounded representation research, and exact historical source/platform closures. Do not generate a video or fabricate natural use for this study. Existing user RunPod authorization is $10 cumulative; research reservations have reached $9.50 before later publication attempts. Inspect all newer ledgers before any new reservation. Heavy computation belongs on RunPod. Publish only the authorized Relative0 CM site using repository-local authentication; do not switch the global account. No subagents or new task without a request.
'''.encode())
prior_seals={
    'docs/audits/2026-09-12-cm-application-evidence/FINAL-MANIFEST.json':'1ded06d3d710203ed050c8f729edfb71653f09fe339234af2ee5352fc8ed47e7',
    'docs/audits/2026-09-12-cm-evidence-frontiers/FINAL-MANIFEST.json':'78e9e12d848aaf24c22696e7c56d261695206a8a98265a17f22e79b841c79442',
    'docs/audits/2026-09-11-cm-next-research/FINAL-MANIFEST.json':'aecf0d003d970ae72eb7b529479c2a60f29fffe713d672aee3b24ef2f167308b'}
for name,digest in prior_seals.items():assert sha((CHECKOUT/name).read_bytes())==digest
artifacts={p.relative_to(DEST).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(DEST.rglob('*')) if p.is_file()}
manifest=dict(schema='cm-count-closures-scientific-seal/v1',sealed_utc=datetime.now(timezone.utc).isoformat(),
    artifacts=artifacts,current_sources={name:sha((CHECKOUT/name).read_bytes()) for name in sources},prior_seals=prior_seals)
payload=(json.dumps(manifest,indent=2)+'\n').encode();(DEST/'FINAL-MANIFEST.json').write_bytes(payload)
digest=sha(payload);(DEST/'FINAL-MANIFEST.sha256').write_text(digest+'  FINAL-MANIFEST.json\n',encoding='utf-8')
print(json.dumps(dict(status='sealed',artifacts=len(artifacts),sources=len(sources),sha256=digest)))
