"""Finish subtitle bounds, local review navigation, and immutable delivery hashes."""
from pathlib import Path
import json, sys, shutil, html
import cm_tutorial_series_v1 as p

def repair_caption_bounds():
    p.require_unfrozen()
    for lesson in p.curriculum.LESSONS:
        folder=p.OUT/lesson['id']; report_path=folder/'QA_REPORT_V1.json'
        report=json.loads(report_path.read_text(encoding='utf-8'))
        changed=False
        for cue in report['captions']:
            if cue['end']>report['duration_s']:
                if cue['end']-report['duration_s']>.003:raise RuntimeError('Unexpected alignment overrun')
                cue['end']=report['duration_s'];changed=True
        if not changed:continue
        video=folder/(lesson['id']+'_v1.mp4');subtitles=folder/'captions_v1.vtt'
        archive=folder/'intermediate_before_subtitle_bound_fix';archive.mkdir(exist_ok=False)
        # Preserve the initial local encode; all paths are within this lesson.
        for old in (video,subtitles,report_path):
            destination=archive/old.name
            assert folder.resolve() in destination.resolve().parents
            if destination.exists():raise RuntimeError('Archive target already exists')
            if old==video:old.rename(destination)
            else:shutil.copyfile(old,destination)
        vtt=['WEBVTT','']
        for i,c in enumerate(report['captions'],1):vtt.extend([str(i),p.stamp(c['start'])+' --> '+p.stamp(c['end']),c['text'],''])
        subtitles.write_text('\n'.join(vtt),encoding='utf-8')
        p.run([p.ffmpeg(),'-v','error','-n','-i',str(archive/video.name),'-i',str(subtitles),'-map','0:v:0','-map','0:a:0','-map','1:s:0','-map_metadata','0','-map_chapters','0','-c:v','copy','-c:a','copy','-c:s','mov_text','-metadata:s:s:0','language=eng','-movflags','+faststart',str(video)])
        p.run([p.ffmpeg(),'-v','error','-i',str(video),'-map','0:v','-map','0:a','-f','null','-'])
        report['video_sha256']=p.sha(video);report['caption_boundary_correction']='Clamped final subtitle to decoded audio length; preserved original encode in intermediate archive.'
        p.write(report_path,report)
        print('Bounded final subtitle: '+lesson['id'],flush=True)

def review_index():
    p.require_unfrozen()
    lessons=p.curriculum.LESSONS;total=0;rows=[];blocks=[];speech_chars=0;cost=0
    for lesson in lessons:
        folder=p.OUT/lesson['id'];report=json.loads((folder/'QA_REPORT_V1.json').read_text(encoding='utf-8'));seconds=report['duration_s'];total+=seconds
        voice=json.loads((folder/'VOICE_RESPONSE_V1.json').read_text(encoding='utf-8'));speech_chars+=len(voice['payload']['text']);cost+=int(voice['character_cost'] or 0)
        duration=f'{int(seconds//60)}:{round(seconds%60):02d}';rel=lesson['id']+'/'+lesson['id']+'_v1.mp4'
        rows.append(f"| {lesson['id'][:2]} | [{lesson['title']}]({rel}) | {duration} |")
        poster=f"frames/f{report['first_frame']:06d}.png"
        blocks.append(f'''<article id="lesson-{lesson['id'][:2]}"><h2>{lesson['id'][:2]} · {html.escape(lesson['title'])}<span>{duration}</span></h2><p>{html.escape(lesson['objective'])}</p><p class="muted">{html.escape(lesson['prerequisite'])}</p><video controls preload="none" poster="{poster}"><source src="{rel}" type="video/mp4"><track kind="captions" src="{lesson['id']}/captions_v1.vtt" srclang="en" label="English"></video><p><a href="{lesson['id']}/SCRIPT_AND_VISUAL_SPEC_V1.md">Script and visual specification</a> · <a href="{lesson['id']}/captions_v1.vtt">Captions</a> · <a href="{lesson['id']}/QA_REPORT_V1.json">Timing and QA</a></p></article>''')
    readme='''# CM foundations: seven complete tutorials

Start with [the local review index](REVIEW_INDEX_V1.html), or watch the
[complete course](cm_foundations_complete_course_v1.mp4). The course has seven
lesson chapters and an optional English caption track.

| Lesson | Video | Duration |
|---|---|---|
'''+ '\n'.join(rows)+f'''

Total narration and teaching pauses: {int(total//60)} minutes {round(total%60)} seconds.
Delivery: 1280×720, 30 fps H.264, 48 kHz mono AAC, embedded English captions and
WebVTT sidecars. Captions may need to be enabled in the player's subtitle menu.
The diagrams use progressive teaching states aligned to spoken paragraphs.

The full paper learning path is 1–5. For repository addressing, watch 1, 6 and 7.
Every lesson includes a worked example, a five-second practice pause and an
explained answer. Pause longer whenever useful.

One saved **Brian** voice is used throughout—the same voice identity as the old
2:50 passage—with identical stable settings and continuity between lesson requests.
Seven full-lesson recordings replace the old separately generated short snippets.
All seven voice identities, settings, source texts and character alignments were
verified. Acoustic naturalness and whether the delivery matches the preferred
Brian tone still benefit from human listening.

The semantic checks cover all sixteen operator patterns, all sixteen compound
matrix cells, and all 48 repository assignment/layout pairs through the actual
API. Layout checks cover all 75 teaching frames. Every delivered video has been
fully decoded for audio/video errors. Prior reel and assembly artifacts match
their existing manifests (151 recorded artifact entries checked).

See [the teaching and ownership review](TEACHING_REVIEW_AND_OWNERSHIP_V1.md) for
what moved, expanded or was kept out; [source and voice notes](SOURCE_AND_VOICE_REVIEW_V1.md)
for mathematical source locators and the voice decision. Each lesson folder holds
the full new script, visual specification, source audio, captions, cue times and QA.

Seven synthesis requests sent {speech_chars:,} script characters. ElevenLabs returned
{cost:,} total `character-cost` units; this is the API's reported unit count, not a
dollar charge. No additional voices, paid generation services, RunPod, publication,
commit or push were used. All earlier delivered versions remain unchanged.

Production sources are `docs/video_factory/cm_tutorial_curriculum_v1.py`,
`cm_tutorial_visuals_v1.py`, `cm_tutorial_series_v1.py`,
`cm_tutorial_layout_qa_v1.cjs`, `cm_tutorial_finalize_v1.py` and
`tests/test_cm_tutorial_series_v1.py`. Use `cm_tutorial_finalize_v1.py verify`
to validate the frozen delivery manifest. Create a successor for subsequent edits.

Recommended next review: listen to lesson 1 and a later lesson for voice consistency,
then note any confusing passage by lesson and timestamp. This is a local review
delivery; it has not been published.
'''
    (p.OUT/'README.md').write_text(readme,encoding='utf-8')
    index='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>CM foundations · tutorial review</title><style>body{background:#091219;color:#e8f2f7;font:18px/1.55 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px}h1{font-size:40px}h2{font-size:26px}h2 span{float:right;color:#86dbe7;font-size:20px}a{color:#85dfec}video{width:100%;background:#071014;border:1px solid #425966}article{border-top:3px solid #79dce7;margin:44px 0;padding-top:12px}.muted{color:#b9cbd4}nav{display:flex;flex-wrap:wrap;gap:16px}.course{border-left:4px solid #bca5ef;padding:16px 22px;background:#182538}</style><h1>CM foundations</h1><p>Seven tutorials with worked examples, practice pauses and Brian narration.</p><nav>'''+''.join(f'<a href="#lesson-{l["id"][:2]}">{l["id"][:2]} · {html.escape(l["title"])}</a>' for l in lessons)+'''</nav><section class="course"><h2>Watch the complete course</h2><video controls preload="none" poster="frames/f000000.png"><source src="cm_foundations_complete_course_v1.mp4" type="video/mp4"><track kind="captions" src="course_captions_v1.vtt" srclang="en" label="English"></video><p class="muted">Enable captions in your player's subtitle menu. For the repository path, start with lessons 1, 6 and 7.</p></section>'''+''.join(blocks)+'''<p><a href="TEACHING_REVIEW_AND_OWNERSHIP_V1.md">Teaching review</a> · <a href="SOURCE_AND_VOICE_REVIEW_V1.md">Sources and voice</a> · <a href="README.md">Delivery notes</a></p></html>'''
    (p.OUT/'REVIEW_INDEX_V1.html').write_text(index,encoding='utf-8')
    p.write(p.OUT/'VOICE_CONTINUITY_QA_V1.json',dict(voice_id=p.VOICE,model=p.MODEL,settings=p.SETTINGS,requests=7,script_characters=speech_chars,reported_character_cost_units=cost,matching_old_reference_cue='06_05 at 170.4066875s',human_listening_pending=True))
    print('Review index and delivery notes created',flush=True)

def freeze():
    target=p.OUT/'DELIVERY_MANIFEST_V1.json'
    if target.exists():raise RuntimeError('Existing frozen delivery must be preserved')
    import imageio_ffmpeg
    course=p.OUT/'cm_foundations_complete_course_v1.mp4';count,dur=imageio_ffmpeg.count_frames_and_secs(str(course))
    q=json.loads((p.OUT/'COURSE_QA_V1.json').read_text());q.update(decoded_frames=count,actual_duration_s=dur)
    p.write(p.OUT/'COURSE_QA_V1.json',q)
    files=[x for x in p.OUT.rglob('*') if x.is_file() and x!=target]
    files += [p.ROOT/'docs/video_factory'/n for n in ['cm_tutorial_curriculum_v1.py','cm_tutorial_visuals_v1.py','cm_tutorial_series_v1.py','cm_tutorial_layout_qa_v1.cjs','cm_tutorial_finalize_v1.py','tests/test_cm_tutorial_series_v1.py']]
    records=[dict(path=x.relative_to(p.ROOT).as_posix(),bytes=x.stat().st_size,sha256=p.sha(x)) for x in sorted(files)]
    p.write(target,dict(version=1,status='local_review_delivery',date='2026-09-13',artifacts=records,publication=False,commit=False,push=False,runpod=False))
    print(f'Frozen {len(records)} artifacts',flush=True)

def verify():
    d=json.loads((p.OUT/'DELIVERY_MANIFEST_V1.json').read_text())
    bad=[a['path'] for a in d['artifacts'] if p.sha(p.ROOT/a['path'])!=a['sha256']]
    if bad:raise RuntimeError('Delivery hash mismatch: '+str(bad))
    print(f"Verified {len(d['artifacts'])} artifacts",flush=True)

if __name__=='__main__':{'repair':repair_caption_bounds,'index':review_index,'freeze':freeze,'verify':verify}[sys.argv[1]]()
