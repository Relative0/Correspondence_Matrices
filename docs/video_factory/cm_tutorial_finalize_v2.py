"""Local review navigation, source preservation and immutable v2 delivery."""
from pathlib import Path
import json,html,sys
import cm_tutorial_series_v2 as p

def duration(s):
    n=round(s);m,n=divmod(n,60);return f'{m}:{n:02d}'

def write_vtt(path,caps):
    lines=['WEBVTT','']
    for i,c in enumerate(caps,1):lines.extend([str(i),p.stamp(c['start'])+' --> '+p.stamp(c['end']),c['text'],''])
    path.write_text('\n'.join(lines),encoding='utf-8')

def remux_with_captions(video,subtitles):
    archive=video.parent/'intermediate_before_caption_wrap_fix';archive.mkdir(exist_ok=True)
    dest=archive/video.name
    if dest.exists():raise RuntimeError('Preserve archived initial encode')
    assert p.OUT.resolve() in dest.resolve().parents
    video.rename(dest)
    p.run([p.ffmpeg(),'-v','error','-n','-i',str(dest),'-i',str(subtitles),'-map','0:v:0','-map','0:a:0','-map','1:s:0','-map_metadata','0','-map_chapters','0','-c:v','copy','-c:a','copy','-c:s','mov_text','-metadata:s:s:0','language=eng','-movflags','+faststart',str(video)])
    p.run([p.ffmpeg(),'-v','error','-i',str(video),'-map','0:v','-map','0:a','-f','null','-'])

def repair_captions():
    p.require_unfrozen();combined=[];offset=0;changed_any=False
    for l in p.curriculum.LESSONS:
        f=p.OUT/l['id'];report_path=f/'QA_REPORT_V2.json';q=json.loads(report_path.read_text(encoding='utf-8'))
        response=json.loads((f/'VOICE_RESPONSE_V2.json').read_text(encoding='utf-8'))
        original=q['duration_s']-sum(s['pause'] for s in q['timeline'])
        _,words,_,_=p.align_scenes(l,response,original)
        caps=p.captions(words)
        for cap in caps:cap['end']=min(cap['end'],q['duration_s'])
        if caps!=q['captions']:
            changed_any=True
            archive=f/'intermediate_before_caption_wrap_fix';archive.mkdir(exist_ok=True)
            for path in [report_path,f/'captions_v2.vtt']:
                saved=archive/path.name
                if saved.exists():raise RuntimeError('Preserve archived caption metadata')
                saved.write_bytes(path.read_bytes())
            write_vtt(f/'captions_v2.vtt',caps)
            video=f/(l['id']+'_v2.mp4');remux_with_captions(video,f/'captions_v2.vtt')
            q['captions']=caps;q['video_sha256']=p.sha(video);q['caption_wrap_fix']='At most two lines; source audio and video streams preserved.'
            p.write(report_path,q);print('Repaired caption wrapping: '+l['id'],flush=True)
        combined += [dict(start=x['start']+offset,end=x['end']+offset,text=x['text']) for x in caps]
        offset+=round(q['decoded_frames']/30,9)
    if changed_any:
        sub=p.OUT/'course_captions_v2.vtt';archive=p.OUT/'intermediate_before_caption_wrap_fix';archive.mkdir(exist_ok=True)
        (archive/sub.name).write_bytes(sub.read_bytes());write_vtt(sub,combined)
        video=p.OUT/'cm_foundations_complete_course_v2.mp4';remux_with_captions(video,sub)
        q=json.loads((p.OUT/'COURSE_QA_V2.json').read_text());q['video_sha256']=p.sha(video);q['caption_wrap_fix']='Remuxed from corrected lesson captions; audio/video unchanged.'
        p.write(p.OUT/'COURSE_QA_V2.json',q);print('Combined captions repaired and media decoded',flush=True)

def index():
    p.require_unfrozen();rows=[];cards=[];total=0;new=[];reused=[]
    for l in p.curriculum.LESSONS:
        folder=p.OUT/l['id'];q=json.loads((folder/'QA_REPORT_V2.json').read_text(encoding='utf-8'));v=json.loads((folder/'VOICE_RESPONSE_V2.json').read_text(encoding='utf-8'))
        total+=q['duration_s'];(reused if 'reuse_provenance' in v else new).append(v)
        file=l['id']+'/'+l['id']+'_v2.mp4'
        rows.append(f"| {l['id'][:2]} | [{l['title']}]({file}) | {duration(q['duration_s'])} |")
        cards.append(f'''<article id="lesson-{l['id'][:2]}"><h2>{l['id'][:2]} · {html.escape(l['title'])}<span>{duration(q['duration_s'])}</span></h2><p>{html.escape(l['objective'])}</p><p class="muted">{html.escape(l['prerequisite'])}</p><video controls preload="none" poster="frames/f{q['first_frame']:06d}.png"><source src="{file}" type="video/mp4"><track kind="captions" src="{l['id']}/captions_v2.vtt" srclang="en" label="English"></video><p><a href="{file}">Open this lesson MP4</a> · <a href="{l['id']}/SCRIPT_AND_VISUAL_SPEC_V2.md">Script and visual specification</a> · <a href="{l['id']}/captions_v2.vtt">Captions</a></p></article>''')
    cost=sum(int(x.get('character_cost') or 0) for x in new)
    md='''# CM foundations v2: nine separate lesson videos

Each lesson below is a standalone MP4. Use the [local video index](REVIEW_INDEX_V2.html)
to browse the lesson players, or open an individual video directly.

| Lesson | Standalone video | Duration |
|---|---|---|
'''+ '\n'.join(rows)+f'''

[Combined course](cm_foundations_complete_course_v2.mp4): **{duration(total)}**,
with nine lesson chapters. This convenience copy does not replace the individual
MP4s. The complete learning path is 1–9; the repository-only path is 1, 8, 9.

The main changes are bracketed operator names paired with numeric CMs, a defined
`[θ]` placeholder, the centered Impax overlay, and two new measurement lessons.
Lesson 3 computes `⟨0|[⇕]|1⟩` in both groupings, including the requested final
`0⇕1=1`. Lesson 4 derives the paper's page-7 implication example step by step.
The previous undefined M-based XOR alias is absent.

- [Teaching, chronology and source review](TEACHING_AND_SOURCE_REVIEW_V2.md)
- [Proposed advanced lessons 10–23](ADVANCED_VIDEO_PROPOSAL_V2.md)
- [Validation details](VALIDATION_V2.md)

Each video is 1280×720, 30 fps H.264 with 48 kHz mono Brian narration, an English
subtitle track and a WebVTT sidecar. Each lesson includes a five-second practice
pause. Enable subtitles in your player if desired.

There are {len(new)} new ElevenLabs lesson recordings and {len(reused)} exact reused
source recordings. All use Brian `Fu3xLoDFv9UvgA2FXCUS` with the same model and
settings. New requests reported {cost:,} total `character-cost` units; this is
the API's accounting unit, not a dollar charge. Existing source audio was reused
only after checking identical narration text, voice and settings.

The prior v1 course and its production files remain unchanged. The shared episode
Bible was not renumbered. Advanced lessons are proposed only. No RunPod,
publication, commit or push occurred.

The machine-readable timing and QA report, complete script/specification,
per-scene HTML and source recording are retained in each lesson folder.
`DELIVERY_MANIFEST_V2.json` records the final hashes; run
`python docs/video_factory/cm_tutorial_finalize_v2.py verify` from the repository
to validate the package. Subsequent edits should use another successor version.

Recommended review: watch lessons 3 and 4 first, then decide whether advanced
lessons 10–12 should enter production. Voice naturalness remains a human listening
judgment even when the voice identity, configuration and technical checks agree.
'''
    (p.OUT/'README.md').write_text(md,encoding='utf-8')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CM foundations v2 · nine lessons</title><style>body{background:#091219;color:#edf4f8;font:18px/1.5 system-ui,sans-serif;max-width:1100px;margin:35px auto;padding:0 24px}h1{font-size:39px}h2{font-size:26px}h2 span{float:right;font-size:19px;color:#8cdee6}a{color:#8ddfeb}video{width:100%;background:#061018;border:1px solid #476877}article{margin:45px 0;border-top:3px solid #66d9e8;padding-top:12px}.muted{color:#bfd0d9}nav{display:flex;flex-wrap:wrap;gap:10px 18px}.review{background:#19283a;border-left:4px solid #bda7ee;padding:16px 22px}</style><h1>CM foundations · nine separate lessons</h1><p>Operator symbols, numeric matrices, and fully worked measurements.</p><nav>'''+''.join(f'<a href="#lesson-{l["id"][:2]}">{l["id"][:2]} · {html.escape(l["title"])}</a>' for l in p.curriculum.LESSONS)+'''</nav><div class="review"><p>New measurement material: lessons 3 and 4. Repository path: 1, 8 and 9.</p><a href="ADVANCED_VIDEO_PROPOSAL_V2.md">Advanced-video proposal</a> · <a href="TEACHING_AND_SOURCE_REVIEW_V2.md">Teaching and source review</a></div>'''+''.join(cards)+'''<article><h2>Complete course</h2><video controls preload="none" poster="frames/f000000.png"><source src="cm_foundations_complete_course_v2.mp4" type="video/mp4"><track kind="captions" src="course_captions_v2.vtt" srclang="en" label="English"></video></article></html>'''
    (p.OUT/'REVIEW_INDEX_V2.html').write_text(page,encoding='utf-8')
    p.write(p.OUT/'VOICE_CONTINUITY_QA_V2.json',dict(voice_id=p.VOICE,model=p.MODEL,settings=p.SETTINGS,new_recordings=len(new),reused_recordings=len(reused),new_character_cost_units=cost,human_listening_pending=True))
    print(f'Indexed {len(rows)} individual videos; course {duration(total)}',flush=True)

def preservation():
    old=p.ROOT/'docs/video_factory/deep_series/foundational_cm_tutorial_series_v1/DELIVERY_MANIFEST_V1.json'
    d=json.loads(old.read_text());bad=[a['path'] for a in d['artifacts'] if p.sha(p.ROOT/a['path'])!=a['sha256']]
    p.write(p.OUT/'PRESERVATION_QA_V2.json',dict(prior_manifest=str(old.relative_to(p.ROOT)),checked_artifacts=len(d['artifacts']),mismatches=bad,prior_manifest_sha256=p.sha(old)))
    if bad:raise RuntimeError('Prior frozen artifacts differ: '+str(bad))
    print(f"Preserved all {len(d['artifacts'])} v1 artifacts",flush=True)

def freeze():
    p.require_unfrozen();import imageio_ffmpeg
    course=p.OUT/'cm_foundations_complete_course_v2.mp4';frames,seconds=imageio_ffmpeg.count_frames_and_secs(str(course))
    q=json.loads((p.OUT/'COURSE_QA_V2.json').read_text());q.update(decoded_frames=frames,actual_duration_s=seconds)
    if abs(seconds-q['expected_duration_s'])>.25:raise RuntimeError('Combined duration mismatch')
    p.write(p.OUT/'COURSE_QA_V2.json',q)
    preservation()
    source=p.OUT/'sources/CorrespondenceMatrices_source_2026_09_14.pdf'
    p.write(p.OUT/'SOURCE_IDENTITY_V2.json',dict(url='https://www.b-theory.com/CorrespondenceMatrices.pdf',retrieved_date='2026-09-14',sha256=p.sha(source),visual_pages_reviewed=[7,12]))
    paths=[x for x in p.OUT.rglob('*') if x.is_file()]
    paths += [p.ROOT/'docs/video_factory'/name for name in ['cm_tutorial_curriculum_v2.py','cm_tutorial_visuals_v2.py','cm_tutorial_series_v2.py','cm_tutorial_layout_qa_v2.cjs','cm_tutorial_finalize_v2.py','tests/test_cm_tutorial_series_v2.py','AGENTS.md','cm_tutorial_curriculum_v1.py','cm_tutorial_visuals_v1.py','foundational_cm_corrections_v3.py']]
    paths += [p.ROOT/'docs/CM_NOTATION_STANDARD_V2.md']
    rows=[dict(path=x.relative_to(p.ROOT).as_posix(),bytes=x.stat().st_size,sha256=p.sha(x)) for x in sorted(set(paths))]
    p.write(p.OUT/'DELIVERY_MANIFEST_V2.json',dict(version=2,status='local_review_delivery',date='2026-09-14',artifacts=rows,lessons=9,advanced_proposal_only=True,published=False,runpod=False,commit=False,push=False))
    print(f'Frozen {len(rows)} artifacts',flush=True)

def verify():
    d=json.loads((p.OUT/'DELIVERY_MANIFEST_V2.json').read_text())
    bad=[a['path'] for a in d['artifacts'] if p.sha(p.ROOT/a['path'])!=a['sha256']]
    if bad:raise RuntimeError(str(bad))
    print(f"Verified {len(d['artifacts'])} artifacts",flush=True)

if __name__=='__main__':{'index':index,'repair':repair_captions,'preservation':preservation,'freeze':freeze,'verify':verify}[sys.argv[1]]()
