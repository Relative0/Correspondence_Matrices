"""Scoped ElevenLabs Brian generation and local CM assembly. Never logs secrets."""
from pathlib import Path
import json, re, urllib.request, urllib.error, sys, base64, hashlib, subprocess, math, importlib.util, shutil, textwrap

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/video_factory/deep_series/foundational_cm_brian_voiceover_v1'

def key():
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        match = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)\s*$', line)
        if match and 'ELEVEN' in match[1].upper() and ('KEY' in match[1].upper() or 'TOKEN' in match[1].upper()):
            value = match[2].strip().strip('\"\'')
            if value:
                return value
    raise RuntimeError('No ElevenLabs key found in authorized root .env')

def api(path, payload=None):
    req = urllib.request.Request('https://api.elevenlabs.io'+path, data=json.dumps(payload).encode() if payload is not None else None, headers={'xi-api-key':key(), 'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'ElevenLabs HTTP {exc.code}; response body withheld') from None
    except urllib.error.URLError:
        raise RuntimeError('ElevenLabs connection failed; credentials withheld') from None

def probe():
    voices = api('/v1/voices')['voices']
    matches = [{k:v.get(k) for k in ('voice_id','name','category','labels')} for v in voices if 'brian' in v.get('name','').lower()]
    result = {'key_found':True,'brian_voices':matches}
    (OUT/'VOICE_CHECK.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

def cues():
    source = (OUT/'NARRATION_V1.md').read_text(encoding='utf-8')
    result=[]
    for section in re.split(r'\n## ',source)[1:]:
        heading, body=section.split('\n',1)
        chapter=int(heading.split('.')[0]); number=0
        for paragraph in body.strip().split('\n\n'):
            paragraph=paragraph.strip()
            if not paragraph or paragraph.startswith('Visual alignment:'): continue
            number+=1
            result.append({'id':f'{chapter:02d}_{number:02d}','chapter':chapter,'title':heading,'kind':'pause' if paragraph.startswith('[Four-second') else 'speech','text':paragraph})
    return result

def generate():
    voice=json.loads((OUT/'VOICE_CHECK.json').read_text())
    matches=[v for v in voice['brian_voices'] if v['name']=='Brian']
    if len(matches)!=1: raise RuntimeError('Exact Brian voice is ambiguous')
    voice_id=matches[0]['voice_id']
    audio=OUT/'audio'; audio.mkdir(exist_ok=True)
    items=cues()
    for cue in items:
        if cue['kind']=='pause': continue
        target=audio/(cue['id']+'.json')
        payload={'text':cue['text'],'model_id':'eleven_multilingual_v2','voice_settings':{'stability':0.6,'similarity_boost':0.8,'use_speaker_boost':True,'speed':0.95}}
        identity=hashlib.sha256(json.dumps({'voice':voice_id,**payload},sort_keys=True).encode()).hexdigest()
        if target.exists():
            if json.loads(target.read_text())['identity']!=identity: raise RuntimeError('Cached generation differs')
            continue
        marker=audio/(cue['id']+'.pending')
        if marker.exists(): raise RuntimeError('Uncertain earlier generation; inspect ElevenLabs history before retrying '+cue['id'])
        marker.write_text(identity)
        response=api('/v1/text-to-speech/'+voice_id+'/with-timestamps?output_format=mp3_44100_128',payload)
        (audio/(cue['id']+'.mp3')).write_bytes(base64.b64decode(response.pop('audio_base64')))
        response.update({'identity':identity,'voice_id':voice_id,'model_id':payload['model_id'],'text':cue['text']})
        target.write_text(json.dumps(response,ensure_ascii=False),encoding='utf-8')
        marker.unlink()
        print('Generated '+cue['id'],flush=True)
    print('Narration generation complete',flush=True)

def module():
    path=ROOT/'docs/video_factory/foundational_cm_seven_clip_assembly_v1.py'
    spec=importlib.util.spec_from_file_location('assembly',path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def run(command,cwd=None):
    result=subprocess.run(command,cwd=cwd,capture_output=True)
    if result.returncode: raise RuntimeError(result.stderr.decode('utf-8',errors='replace')[-1800:])
    return result

def stamp(seconds):
    ms=round(seconds*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'

def assemble():
    import imageio_ffmpeg, wave
    ff=imageio_ffmpeg.get_ffmpeg_exe(); mod=module(); sans,mono=mod.BASE.font_data()
    media=OUT/'audio'; frames=OUT/'frames'; frames.mkdir(exist_ok=True)
    items=cues(); timeline=[]; words=[]; chunks=[]; cursor=0; by_chapter={}
    for cue in items:
        wav=media/(cue['id']+'.wav')
        if cue['kind']=='pause':
            run([ff,'-v','error','-y','-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t','4',str(wav)])
        else:
            run([ff,'-v','error','-y','-i',str(media/(cue['id']+'.mp3')),'-ar','48000','-ac','1',str(wav)])
        with wave.open(str(wav),'rb') as source:
            data=source.readframes(source.getnframes()); duration=source.getnframes()/48000
        cue={**cue,'start':cursor,'end':cursor+duration,'duration':duration}
        if cue['kind']=='speech':
            meta=json.loads((media/(cue['id']+'.json')).read_text(encoding='utf-8'))
            a=meta.get('normalized_alignment') or meta['alignment']
            chars=''.join(a['characters'])
            for match in re.finditer(r'\S+',chars):
                words.append({'text':match[0],'start':cursor+a['character_start_times_seconds'][match.start()],'end':cursor+a['character_end_times_seconds'][match.end()-1]})
        chunks.append(data); timeline.append(cue); by_chapter.setdefault(cue['chapter'],[]).append(cue); cursor+=duration
    with wave.open(str(OUT/'brian_narration_v1.wav'),'wb') as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(48000); out.writeframes(b''.join(chunks))
    # Align approved visual states to spoken paragraphs and explicit retrieval pauses.
    states={1:[.2,.8],2:[.2,.2,.96],3:[.12,.52,.73,.95],4:[.05,.60,.98],5:[.2,.2,.96],6:[.12,.12,.12,.35,.47,.60,.77,.93],7:[.15,.48,.92,.92]}
    scenes=[]; holds=[]
    for chapter, group in by_chapter.items():
        if len(group)!=len(states[chapter]): raise RuntimeError('Visual cue count mismatch')
        page=mod.corrected_page(mod.CLIPS[chapter-1],sans,mono)
        page=page.replace('SEVEN-CLIP ASSEMBLY','CM FOUNDATIONS').replace('silent local review','Brian · ElevenLabs').replace('conceptual teaching preview','Brian · ElevenLabs').replace('assembly v1','narrated review v1')
        # Keep inherited compound matrix above the caption region.
        extra='.stage{padding-bottom:70px}footer{bottom:8px}'
        if chapter==4: extra+='.cells{height:185px}.stack{gap:6px}.panel{padding:8px}h1{margin:3px 0 5px}'
        page=page.replace('</style>',extra+'</style>')
        for index,cue in enumerate(group):
            progress=states[chapter][index]
            # Sequential term reveals inside the compound-rule explanation.
            parts=[(progress,cue['duration'])]
            if chapter==4 and index==1:
                meta=json.loads((media/(cue['id']+'.json')).read_text())
                a=meta.get('normalized_alignment') or meta['alignment']; text=''.join(a['characters']).lower()
                triggers=[('both sides true',.27),('only the right',.47),('both sides false',.68),('combine their',.98)]
                marks=[(0,.05)]
                for phrase,p in triggers:
                    pos=text.find(phrase)
                    if pos>=0: marks.append((a['character_start_times_seconds'][pos],p))
                parts=[(p,(marks[j+1][0] if j+1<len(marks) else cue['duration'])-t) for j,(t,p) in enumerate(marks)]
            for p,d in parts:
                n=len(scenes)
                scenes.append({'id':f'state_{n:03d}','kind':'cm_brian','startIndex':n,'progress':[p],'html':page})
                holds.append({'frame':n,'duration':d,'cue':cue['id'],'progress':p})
    manifest={'width':960,'height':540,'fps':15,'scenes':scenes}
    (OUT/'FRAME_MANIFEST.json').write_text(json.dumps(manifest),encoding='utf-8')
    run([shutil.which('node'),str(mod.BASE.FRAME_DRIVER),str(OUT/'FRAME_MANIFEST.json'),str(frames),'2'],cwd=mod.BASE.POP_ROOT)
    concat=[]
    for hold in holds:
        concat.extend([f"file 'frames/f{hold['frame']:06d}.png'",f"duration {hold['duration']:.9f}"])
    concat.append(f"file 'frames/f{holds[-1]['frame']:06d}.png'")
    (OUT/'visuals.concat.txt').write_text('\n'.join(concat)+'\n')
    # Phrase captions follow ElevenLabs character alignment, including inserted pauses.
    captions=[]; group=[]
    for word in words:
        combined=' '.join(w['text'] for w in group+[word])
        if group and (len(combined)>76 or word['end']-group[0]['start']>5 or word['start']-group[-1]['end']>1):
            captions.append(group); group=[]
        group.append(word)
    if group: captions.append(group)
    vtt=['WEBVTT','']
    for i,group in enumerate(captions,1):
        vtt.extend([str(i),f"{stamp(group[0]['start'])} --> {stamp(group[-1]['end'])}",'\n'.join(textwrap.wrap(' '.join(w['text'] for w in group),width=42)),''])
    (OUT/'brian_captions_v1.vtt').write_text('\n'.join(vtt),encoding='utf-8')
    chapters=[';FFMETADATA1']
    for chapter,group in by_chapter.items(): chapters.extend(['[CHAPTER]','TIMEBASE=1/1000',f"START={round(group[0]['start']*1000)}",f"END={round(group[-1]['end']*1000)}",'title='+group[0]['title']])
    (OUT/'chapters.ffmeta').write_text('\n'.join(chapters),encoding='utf-8')
    output=OUT/'foundational_cm_brian_narrated_v1.mp4'
    if output.exists(): raise RuntimeError('Final output exists; preserve it')
    run([ff,'-v','error','-n','-f','concat','-safe','0','-i',str(OUT/'visuals.concat.txt'),'-i',str(OUT/'brian_narration_v1.wav'),'-i',str(OUT/'brian_captions_v1.vtt'),'-i',str(OUT/'chapters.ffmeta'),'-map','0:v','-map','1:a','-map','2:s','-map_metadata','3','-map_chapters','3','-vf','fps=30','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:s','mov_text','-metadata:s:s:0','language=eng','-t',str(cursor),'-movflags','+faststart',str(output)])
    run([ff,'-v','error','-i',str(output),'-map','0:v','-map','0:a','-f','null','-'])
    n,d=imageio_ffmpeg.count_frames_and_secs(str(output))
    report={'status':'technical_validation_passed_human_listening_required','voice':'Brian','voice_id':'Fu3xLoDFv9UvgA2FXCUS','model':'eleven_multilingual_v2','duration_s':cursor,'decoded_frames':n,'video_duration_s':d,'chapters':7,'retrieval_pauses':[c for c in timeline if c['kind']=='pause'],'caption_phrases':len(captions),'timeline':timeline,'visual_holds':holds,'source_narration_sha256':hashlib.sha256((OUT/'NARRATION_V1.md').read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'elevenlabs_generation_performed':True,'runpod_used':False,'published':False}
    (OUT/'NARRATED_REPORT_V1.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('timeline','visual_holds','retrieval_pauses')},indent=2))

if __name__=='__main__':
    {'probe':probe,'generate':generate,'assemble':assemble}[sys.argv[1] if len(sys.argv)>1 else 'probe']()
