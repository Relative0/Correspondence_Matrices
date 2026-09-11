"""Seal public research evidence; retain account, transport and media custody locally."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-applications'
DEST=CHECKOUT/'docs/audits/2026-09-12-cm-application-evidence'
sys.path.insert(0,str(CHECKOUT))
from scripts.cm_research_publication import scan_bytes

def sha(data):return hashlib.sha256(data).hexdigest()
def read(name):return json.loads((AUDIT/name).read_text(encoding='utf-8'))
def put(name,data):
 scan_bytes(name,data)
 target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():assert target.read_bytes()==data,name
 else:target.write_bytes(data)
def write(name,value):put(name,(json.dumps(value,indent=2)+'\n').encode())

public=read('PUBLIC-RESULTS.json');verification=read('VERIFICATION.json')
assert verification['status']=='pass' and public['cost']['all_created_pods_deleted']
selected=['PLAN.md','ORACLE-PROTOCOL.json','QIF-VERIFICATION.json','FEATURE-CASES.json',
 'ATTRIBUTED-ABSTRACTION.json','ATTRIBUTED-MITERS.json','STUDY-PROTOCOL.json','STUDY-ANALYSIS.json',
 'VIDEO-CONSUMER-AUDIT.json','RECEIPT-BYTE-RESTORATION.json','PUBLIC-RESULTS.json','VERIFICATION.json']
for name in selected:
 path=AUDIT/name
 if not path.is_file():
  path=DEST/name
  relative=path.relative_to(CHECKOUT).as_posix()
  expected={json.loads(p.read_text())['source']['files'].get(relative) for p in (AUDIT/'packages').glob('*-FREEZE.json')}
  assert sha(path.read_bytes()) in expected,name
 put(name,path.read_bytes())
for folder in ('upstream','receipt_byte_variants'):
 for path in sorted((AUDIT/folder).rglob('*')):
  if path.is_file():put(path.relative_to(AUDIT).as_posix(),path.read_bytes())
for name in ('analyze_studies.py','final_results.py','audit_video.py','restore_receipt_bytes.py','finalize_science.py'):
 put('analysis/'+name,(AUDIT/name).read_bytes())

profiles={}
for path in sorted((AUDIT/'packages').glob('*-FREEZE.json')):
 freeze=json.loads(path.read_text());profile=freeze['profile'];bundle=AUDIT/'packages'/(profile+'.zip')
 assert sha(bundle.read_bytes())==freeze['bundle_sha256']
 put('profiles/'+path.name,path.read_bytes());members={}
 with zipfile.ZipFile(bundle) as archive:
  for member in archive.infolist():
   data=archive.read(member);digest=sha(data);name=member.filename
   object_name='source_objects/'+digest+(Path(name).suffix or '.txt')
   put(object_name,data)
   members[name]=dict(sha256=digest,bytes=len(data),object=object_name)
 profiles[profile]=dict(freeze='profiles/'+path.name,members=members)
write('SOURCE-PROFILES.json',profiles)
for attempt in verification['attempts']:
 directory=AUDIT/attempt['id']/'evidence'
 for path in sorted(directory.rglob('*')):
  if path.is_file():put(path.relative_to(AUDIT).as_posix(),path.read_bytes())
 local={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in
  sorted((AUDIT/attempt['id']).iterdir()) if p.is_file()}
 write(attempt['id']+'/OPERATIONAL-CUSTODY.json',dict(summary=attempt,local_receipts=local))

c=public['regression']['counts'];cost=public['cost'];f=public['fixtures']
report=f'''# Application evidence continuation

All nine paired original models now have independently checked concrete-feature
selection contracts. Every completed timed output in the new feature and independent
workload studies agrees with Ganak. The bounded simplifier passed correctness
controls but expanded neither cohort and is not installed as a default.

## Concrete features and attributes

The original model/CNF pairs retain their pinned identities from the previous
audit. pc-richmond has 377 named Boolean features, 376 concrete features, no unmatched
CNF axes and 377 static double price attributes. The strict new adapter handles
only nonconfigurable static metadata. It refuses unsupported types, configurable
attributes and constraints it cannot express over named Boolean features.

This interpretation follows the pinned FeatureIDE reader at commit
`d769691754fd63cf757902fc1b3daf28d9333535`: feature structure and propositional
constraints are distinct from attribute metadata. The retained source and license
are included. It does not count prices or attribute-value configurations.
Glucose3 and Minisat22 both return UNSAT for the all-Boolean-feature and concrete
selection disagreement formulas. Both checks were repeated in the separate
benchmark/oracle jobs. These solver agreements are not externally certified proofs.
Fiasco/uClibc retain their earlier abstract-root counterexamples; their concrete
selection contracts remain separately verified.

## Independent exact counting

The official Ganak 2.6.3 Linux binary is pinned by archive hash
`8e0a7d28c00b2e5bd5a92fdaa8c225053e5df81b09f4422722d551ce0e073fcc`.
The nonprobabilistic integer projected-count invocation is `--prob 0 --mode 0 --fast`.
Thirty-three exhaustive query controls cover free selected variables, hidden
multiple witnesses, conditioning, empty projections and SAT/UNSAT cases.

All 16 unchanged QIF contexts match every completed earlier CUDD repetition and
every completed current repetition. The initial feature oracle completed 64/72
queries. All 288 completed feature benchmark outputs and 48 independent benchmark
outputs match it, for **336 checked timed outputs**. Each integer remains an exact
decimal string in the public summaries.

The follow-up on five unresolved cases used a frozen 60-second unconditional gate
and seven 30-second conditional queries only after success. It completed 32/40:
all 24 synthesis queries, seven queries on the third QIF instance, and the
unconditional decisionmaking query. Eight conditional queries timed out. Across
both oracle phases, 65/72 distinct feature and 47/48 distinct admitted independent
queries completed; these counts alone are not performance comparisons.

After observing small synthesis counts, a separately frozen exploratory check
enumerated projected assignments with two SAT solvers. It blocks only selected
assignments, not full witness models, and refuses beyond 512 models or 15 seconds.
All 66 exhaustive controls and 48 solver/query combinations passed; both solvers
agree with Ganak on all 24 synthesis queries. QIF3's seven completed values and
decisionmaking's unconditional value still have only the Ganak result.

## Measured methods and limits

All nine feature cases and all six previously admitted independent cases were
selected before the new timings. Eight fixed generated contexts, five methods and
three fresh-process repetitions were scheduled, using a 15-second worker limit
and 2 GiB address-space limit. All statuses are retained:

| Cohort | Complete | Refused | Timeout | Native error | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Concrete features | 36 | 72 | 13 | 14 | 135 |
| Independent workloads | 6 | 54 | 22 | 8 | 90 |

The candidate conditions each request, propagates units, removes hidden pure
literals and performs bounded hidden-variable resolution. Free selected axes are
preserved. Twelve seeds × seven dimensions × twelve cases give 1,008 independent
exhaustive correctness comparisons; additional edge cases cover hidden witnesses,
contradictory conditions and empty projections. Every request pays simplification
and compilation; no reuse is inferred. The candidate completes only Android in
the feature cohort, and none of the independent cases. On Android its median
eight-query session is 83.575280 ms versus 67.907809 ms for Python bucket and
18.635197 ms for exact arrays. No general speedup is supported.

The current QIF rerun has different deadlines and host placement from the prior
study; its changed timeout/error counts are not a paired speedup or regression
measurement. Only complete, independently verified three-repetition measurements
are eligible for plotted values. Earlier even-position projection benchmarks keep
their original meaning; they are not relabeled as concrete product counts.

## Actual video production and capture

The owner's current-state handoff identified three completed foundational narrated
masters. Their bytes match the completed production receipts and frame manifests.
The archived producer differs from current local source. It renders supplied bit
strings and fixed operator tables into HTML, with no observed CM counting or
materialization calls. This verifies real presentation artifacts, not a historical
runtime trace or a need for an optimized counting backend.

A new opt-in adapter targets that actual producer's `matrix` and `mini_matrix`
functions, preserving set-valued highlighting arguments. It binds source, local
call receipts and the render summary. It is ready for the next independently
needed authorized render. No video was rerendered or published here, and no
natural runtime session is admitted. Private media and the production bundle
remain local. See `docs/research/CM_APPLICATION_RESEARCH.md`.

## Historical restoration and regression

All 157 additional dependencies restore exactly: 156 LogikBench files from the
already retained immutable ZIP/manifest and the pinned public d4 binary downloaded
from its original upstream. Together with 115 previously restored files this is
272 dependencies. The executable is not redistributed in a new archive.

Four historical receipts had been normalized to LF by Git. Surviving CRLF originals
match the hashes recorded in separate original reconciliation/analysis records.
Those exact bytes are restored with four path-specific Git attributes; JSON values
and expected hashes are unchanged. Both byte variants and their bindings are
retained in this new audit. The broad replay before the receipt repair remains
preserved as attempt-005.

Final Linux research replay: **{c['passed']:,} passed + {c['subtests_passed']:,} subtests,
{c['failed']} failures, {c['errors']} errors and {c['skipped']} skipped**. The focused
implementation/restoration checks pass {public['regression']['focused_passed']} tests.
This phase recovers {f['newly_recovered_failure_ids']} of the prior 48 failing IDs,
with zero new failing IDs. The remaining suite is not green. Remaining failures
include historical source closures, Windows DLLs on Linux, stale expected drift
lists, missing older artifacts and downstream assessment bindings. Their complete
details are retained; neither hashes nor checks were weakened to hide failures.
Website changes receive separate validation and exact-commit CI after this research
seal; they are not claimed as part of the earlier broad replay.

## Cost, custody and next work

All {len(verification['attempts'])} created pods are deleted. The new conservative
rate/lifetime estimate is ${cost['new_conservative_bound_usd']:.9f}; the cumulative
prior/current estimate is ${cost['combined_conservative_bound_usd']:.9f}. Combined
nonrefunded reservations are ${cost['combined_nonrefunded_reservations_usd']:.2f}
under the standing $10 cap. These are conservative bounds, not posted billing.

Remaining work: capture the next actual video production job; investigate a real
backend consumer if counting/materialization demand exists; independently check
the remaining Ganak-only outputs; improve representation limits using a newly
frozen mechanism; recover historical source/platform closures and the earlier
EPFL origin discrepancy. New feature subsets or attribute configurations require
separate contracts. The original studies and their seals remain available.

Primary sources: [Ganak](https://github.com/meelgroup/ganak),
[FeatureIDE reader](https://github.com/FeatureIDE/FeatureIDE/tree/d769691754fd63cf757902fc1b3daf28d9333535),
[feature model corpus](https://github.com/SoftVarE-Group/feature-model-benchmark/tree/afa60ee2c836e7bdc4068e0f4f128ea31158d2ad),
[independent corpus](https://github.com/dfremont/counting-benchmarks/tree/daff1084d7487cd85f5a49f6588966275332e73f),
[d4 source](https://github.com/crillab/d4v2/tree/15eff31962466804a48374826b9e5a746fc2766e).
'''
put('REPORT.md',report.encode())
prompt=f'''Continue from the application evidence release in build/cm-applications. Read this audit's REPORT.md, PUBLIC-RESULTS.json and FINAL-MANIFEST.json, plus the separate root publication audit. Do not repeat completed studies. All nine concrete-feature contracts are checked; 336 timed outputs match Ganak and all 24 synthesis contexts also match two SAT enumerators. Bounded simplification expanded neither cohort. The broad research replay has {c['passed']} passes, {c['failed']} failures and {c['errors']} errors, with no new failing IDs.

The owner identified actual intermittent video production in the shared parent. Read docs/video_factory/CM_VIDEO_SERIES_CURRENT_STATE_HANDOFF_PROMPT.md there. Its three completed foundational masters use an archived presentation-only producer, different from current source. No counting/materialization demand or runtime trace is established. Use the new capture_foundational_consumer.py only inside a separately needed and authorized actual render; do not generate a research replay and call it natural. Keep private media local and honor separate video publication rules.

Remaining scientific avenues: independently check QIF3's seven Ganak-only values and decisionmaking's unconditional value; finish their timed-out contexts under a separately frozen protocol if useful; use a genuinely different bounded representation to address the remaining CM method refusals; recover exact historical source/platform closures without weakening hashes. Inspect remaining failure details before altering code. Four receipt byte restorations already recover exact CRLF originals; preserve their Git attributes and both variants. Prior EPFL int2float source-origin discrepancy remains unresolved.

Run heavy computation on RunPod. Current combined reservation ledger is ${cost['combined_nonrefunded_reservations_usd']:.2f} under the standing $10 ceiling; cumulative conservative cost bound is ${cost['combined_conservative_bound_usd']:.9f}. All owned pods are deleted. Verify any later publication/test attempt ledger before new reservations. Use the same ownership-bound cleanup, one-hour watchdog and source freeze. The shared root is dirty; do not stage or revert unrelated work. Preserve prior seals; new evidence gets a new audit. Publish updates through repository-local Relative0 authentication without switching the global account. Do not spawn subagents or create a new task unless requested.
'''
put('NEXT-AGENT-PROMPT.md',prompt.encode())
current=['scripts/cm_application_oracle.py','scripts/cm_application_studies.py','scripts/cm_application_oracle_extension.py',
 'scripts/cm_synthesis_projected_enumeration.py','scripts/restore_cm_application_fixtures.py','scripts/capture_foundational_consumer.py',
 'scripts/verify_cm_application_evidence.py','cmbench/comparative/projected_simplify.py','cmbench/comparative/attributed_feature_projection.py',
 'cmbench/comparative/presentation_capture.py','tests/test_projected_simplify.py','tests/test_attributed_feature_projection.py',
 'tests/test_application_fixture_restoration.py','tests/test_presentation_capture.py','docs/research/CM_APPLICATION_RESEARCH.md']
current += [r['path'] for r in read('RECEIPT-BYTE-RESTORATION.json')['files']]
files={p.relative_to(DEST).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(DEST.rglob('*')) if p.is_file()}
manifest=dict(schema='cm-application-science-seal/v1',sealed_utc=datetime.now(timezone.utc).isoformat(),
 status='verified_with_explicit_limitations',base_commit='6f38fa521619aa0cbf91ee3c294ffca304e313ba',artifacts=files,
 current_sources={name:sha((CHECKOUT/name).read_bytes()) for name in current})
write('FINAL-MANIFEST.json',manifest)
seal=sha((DEST/'FINAL-MANIFEST.json').read_bytes())
put('FINAL-MANIFEST.sha256',(seal+'  FINAL-MANIFEST.json\n').encode())
site=CHECKOUT/'deliverables_n22_24/master_explainer_2026_08_03/cm_latest_results_evidence.py'
text=site.read_text(encoding='utf-8');assert 'APPLICATION_SEAL_PENDING' in text
site.write_text(text.replace('APPLICATION_SEAL_PENDING',seal),encoding='utf-8',newline='\n')
print(json.dumps(dict(artifacts=len(files),sources=len(current),seal=seal,public_bytes=sum(r['bytes'] for r in files.values()))))
