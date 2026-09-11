"""Read-only custody and source-bound scope audit of the completed video job."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
BASE=ROOT/'docs/video_factory/runpod/foundational_three_v3'
RUN=BASE/'remote/runpod-foundational-three-v3-20260901-151230'
def sha(data):return hashlib.sha256(data).hexdigest()
bundle=BASE/'bundle.zip'
assert sha(bundle.read_bytes())=='c9cf680f9586db02d61c58fe32157122d7adaf74b08c2263eced23126a68e292'
with zipfile.ZipFile(bundle) as z:
 source=z.read('repo/docs/video_factory/foundational_cm_production.py')
assert sha(source)=='a0d17cc266f3cda33cf7fcfb8a5d3c5ceb30b29deb2456aed7ea89008a943500'
tree=ast.parse(source.decode('utf-8'))
imports=sorted({n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)} |
 {a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names})
functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
scope={name:dict(line=functions[name].lineno,end_line=functions[name].end_lineno,
 source_fragment_sha256=sha(ast.get_source_segment(source.decode('utf-8'),functions[name]).encode()))
 for name in ('matrix','mini_matrix','operator_table_html','production_contracts','render_full')}
verify=json.loads((RUN/'LOCAL_VERIFICATION_V3.json').read_text(encoding='utf-8'))
post=json.loads((RUN/'POSTFLIGHT_V3.json').read_text(encoding='utf-8'))
assert verify['proposal_identity']==post['proposal_identity']
assert verify['remote_render_zero_exit'] and post['local_v3_verification_passed']
episodes=[]
for row in verify['episodes']:
 name=row['video_id'];out=RUN/'results'/name
 master=out/(name+'.narrated-master.mp4')
 assert master.stat().st_size==row['narrated_master_bytes']
 assert sha(master.read_bytes())==row['narrated_master_sha256']
 assert next(r for r in post['outputs'] if r['video_id']==name)['narrated_master_sha256']==row['narrated_master_sha256']
 frames=json.loads((out/'frame_manifest.json').read_text(encoding='utf-8'))
 assert (frames['width'],frames['height'],frames['fps'])==(1920,1080,30)
 episodes.append(dict(video_id=name,narrated_master_sha256=row['narrated_master_sha256'],
  narrated_master_bytes=master.stat().st_size,frame_manifest_sha256=sha((out/'frame_manifest.json').read_bytes()),
  scenes=len(frames['scenes']),duration_s=row['stream_contract']['duration_s'],
  prior_decode_check=row['stream_contract']['full_decode'],media_redecoded_this_audit=False))
report=dict(schema='cm-video-consumer-custody/v1',status='historical_artifacts_verified_no_runtime_trace',
 producer_sha256=sha(source),production_bundle_sha256=sha(bundle.read_bytes()),
 current_producer_matches_archived=sha((ROOT/'docs/video_factory/foundational_cm_production.py').read_bytes())==sha(source),
 producer_imports=imports,inspected_functions=scope,episodes=episodes,
 local_receipts={n:sha((RUN/n).read_bytes()) for n in ('LOCAL_VERIFICATION_V3.json','POSTFLIGHT_V3.json')},
 genuine_completed_artifact_count=len(episodes),natural_runtime_sessions_admitted=0,
 cm_counting_or_materialization_demand_observed=False,
 interpretation='The archived producer formats supplied bit strings and fixed operator tables into HTML for rendering. Its completed masters establish an actual presentation consumer; they do not establish runtime calls to the CM counting/materialization backends. Static source inspection cannot recover call timings or prove a natural demand for those backends.',
 capture_adapter='scripts/capture_foundational_consumer.py',
 next_use='Instrument the next independently needed and separately authorized production render. Preserve its source hash, local receipt and output manifest. Formatter receipts remain presentation evidence; backend-use or speedup claims require actual backend calls and downstream-use review.',
 private_media_published=False,video_rerendered=False,video_publication_authorized=False)
for base in (AUDIT,ROOT/'build/cm-applications/docs/audits/2026-09-12-cm-application-evidence'):
 with (base/'VIDEO-CONSUMER-AUDIT.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(verified_masters=len(episodes),source_changed=not report['current_producer_matches_archived'],natural_runtime_traces=0)))
