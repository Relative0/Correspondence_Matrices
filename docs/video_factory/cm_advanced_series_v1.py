"""Versioned local tutorial production; only explicit generate calls ElevenLabs.

Uses the authorized root .env in memory, never serializes/logs its value.
Long lesson requests share a voice/model/settings and request continuity.
"""
from pathlib import Path
import base64, hashlib, importlib.util, json, math, re, shutil, subprocess, sys, textwrap, time
import urllib.request, urllib.error, wave
import cm_advanced_curriculum_v1 as curriculum
import cm_advanced_visuals_v1 as visuals

ROOT=Path(__file__).resolve().parents[2]
OUT=curriculum.OUT
VOICE='Fu3xLoDFv9UvgA2FXCUS'
MODEL='eleven_multilingual_v2'
SETTINGS={'stability':0.85,'similarity_boost':0.8,'style':0.0,'use_speaker_boost':True,'speed':0.95}
POP=ROOT.parent/'PoP/Tools/POP-Video-Creator'
DRIVER=POP/'pop_video/render/frame_driver.js'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(args,cwd=None):
    result=subprocess.run(args,capture_output=True,cwd=cwd)
    if result.returncode: raise RuntimeError(result.stderr.decode('utf-8',errors='replace')[-2500:])
    return result
def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()
def require_unfrozen():
    if (OUT/'DELIVERY_MANIFEST_V1.json').exists():
        raise RuntimeError('This delivery is frozen. Create a successor version for changes.')
def key():
    for line in (ROOT/'.env').read_text(encoding='utf-8-sig').splitlines():
        m=re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)\s*$',line)
        if m and 'ELEVEN' in m[1].upper() and ('KEY' in m[1].upper() or 'TOKEN' in m[1].upper()):
            val=m[2].strip().strip('\"\'')
            if val: return val
    raise RuntimeError('No ElevenLabs key in authorized root .env')
def api(path,payload=None):
    req=urllib.request.Request('https://api.elevenlabs.io'+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'xi-api-key':key(),'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=240) as response:
            return json.load(response), {'request_id':response.headers.get('request-id'),'character_cost':response.headers.get('character-cost')}
    except urllib.error.HTTPError as exc: raise RuntimeError(f'ElevenLabs HTTP {exc.code}; response body withheld') from None
    except urllib.error.URLError: raise RuntimeError('ElevenLabs connection failed; credential withheld') from None

def prepare():
    require_unfrozen()
    curriculum.export()
    base=loadmod('cm_base',ROOT/'docs/video_factory/foundational_cm_corrections_v3.py')
    sans,mono=base.font_data(); scenes=[]; frames=OUT/'frames'; frames.mkdir(exist_ok=True)
    for lesson in curriculum.LESSONS:
        folder=OUT/lesson['id']; htmls=folder/'visuals'; htmls.mkdir(exist_ok=True)
        for i,s in enumerate(lesson['scenes']):
            html=visuals.page(lesson,s,i,sans,mono)
            (htmls/f'{i+1:02d}.html').write_text(html,encoding='utf-8')
            scenes.append(dict(id=f"{lesson['id']}_{i+1:02d}",kind='cm_tutorial',startIndex=len(scenes),progress=[0],html=html))
    write(OUT/'FRAME_MANIFEST.json',{'width':1280,'height':720,'fps':30,'scenes':scenes})
    run([shutil.which('node'),str(DRIVER),str(OUT/'FRAME_MANIFEST.json'),str(frames),'2'],cwd=POP)
    print(f'Rendered {len(scenes)} teaching states',flush=True)

def generate():
    require_unfrozen()
    prior=[]
    for index,lesson in enumerate(curriculum.LESSONS):
        folder=OUT/lesson['id']; target=folder/'VOICE_RESPONSE_V1.json'; full='\n\n'.join(s['text'] for s in lesson['scenes'])
        if lesson.get('reuse_audio_from') and not target.exists():
            old=ROOT/'docs/video_factory/deep_series/foundational_cm_tutorial_series_v1'/lesson['reuse_audio_from']
            receipt=json.loads((old/'VOICE_RESPONSE_V1.json').read_text(encoding='utf-8'))
            if receipt['payload']['text']!=full or receipt['voice_id']!=VOICE or receipt['payload']['voice_settings']!=SETTINGS:
                raise RuntimeError('Narration reuse requires identical text, voice and settings')
            shutil.copyfile(old/'brian_source_v1.mp3',folder/'brian_source_v1.mp3')
            receipt['reuse_provenance']={'package':'foundational_cm_tutorial_series_v1','lesson':lesson['reuse_audio_from'],'new_paid_request':False}
            write(target,receipt)
        payload={'text':full,'model_id':MODEL,'voice_settings':SETTINGS,'seed':5132026,'apply_text_normalization':'off'}
        if prior: payload['previous_request_ids']=prior[-3:]
        if index+1<len(curriculum.LESSONS): payload['next_text']=curriculum.LESSONS[index+1]['scenes'][0]['text']
        identity=hashlib.sha256(json.dumps({'voice_id':VOICE,'text':full,'model_id':MODEL,'voice_settings':SETTINGS,'seed':5132026},sort_keys=True).encode()).hexdigest()
        if target.exists():
            cached=json.loads(target.read_text(encoding='utf-8'))
            if cached['identity']!=identity: raise RuntimeError('Existing audio differs; create a successor version')
            if cached.get('request_id') and time.time()-cached['generated_unix']<7000: prior.append(cached['request_id'])
            print('Using saved audio: '+lesson['id'],flush=True);continue
        marker=folder/'generation.pending'
        if marker.exists(): raise RuntimeError('Uncertain prior generation. Inspect request history before retrying '+lesson['id'])
        marker.write_text(identity)
        response,headers=api('/v1/text-to-speech/'+VOICE+'/with-timestamps?output_format=mp3_44100_128',payload)
        mp3=base64.b64decode(response.pop('audio_base64')); (folder/'brian_source_v1.mp3').write_bytes(mp3)
        response.update(headers);response.update(identity=identity,voice_id=VOICE,voice_name='Brian',payload=payload,generated_unix=time.time(),source_audio_sha256=sha(folder/'brian_source_v1.mp3'))
        write(target,response);marker.unlink()
        if headers['request_id']:prior.append(headers['request_id'])
        print('Generated '+lesson['id']+f' ({len(full)} characters)',flush=True)

def stamp(t):
    ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'

def align_scenes(lesson,response,duration):
    a=response.get('alignment') or response.get('normalized_alignment')
    chars=''.join(a['characters']); starts=a['character_start_times_seconds'];ends=a['character_end_times_seconds']
    offsets=[];scan=0
    for scene in lesson['scenes']:
        pattern=r'\s+'.join(re.escape(x) for x in scene['text'].split())
        match=re.search(pattern,chars[scan:])
        if not match: raise RuntimeError('Synthesis alignment does not match script: '+scene['title'])
        first,last=scan+match.start(),scan+match.end()-1
        offsets.append((first,last));scan=last+1
    # Cut only between paragraphs, halfway through their natural gap.
    boundaries=[0.0]+[(ends[offsets[i-1][1]]+starts[offsets[i][0]])/2 for i in range(1,len(offsets))]+[duration]
    pauses=[(boundaries[i+1],s['pause']) for i,s in enumerate(lesson['scenes']) if s.get('pause')]
    def shifted(t): return t+sum(n for at,n in pauses if at<=t)
    timeline=[];cursor=0
    for i,s in enumerate(lesson['scenes']):
        length=boundaries[i+1]-boundaries[i]
        timeline.append(dict(index=i,title=s['title'],text=s['text'],start=cursor,speech_end=cursor+length,end=cursor+length+s.get('pause',0),pause=s.get('pause',0)))
        cursor=timeline[-1]['end']
    words=[]
    for m in re.finditer(r'\S+',chars):
        st,en=starts[m.start()],ends[m.end()-1]
        words.append(dict(text=m[0],start=shifted(st),end=shifted(en)))
    return timeline,words,pauses,cursor

def captions(words):
    groups=[];group=[]
    for word in words:
        text=' '.join(w['text'] for w in group+[word])
        if group and (len(text)>76 or len(textwrap.wrap(text,width=42))>2 or word['end']-group[0]['start']>5.5 or word['start']-group[-1]['end']>1):
            groups.append(group);group=[]
        group.append(word)
    if group:groups.append(group)
    return [dict(start=g[0]['start'],end=g[-1]['end'],text='\n'.join(textwrap.wrap(' '.join(w['text'] for w in g),width=42))) for g in groups]

def assemble():
    require_unfrozen()
    import imageio_ffmpeg
    ff=ffmpeg(); global_frame=0
    for lesson in curriculum.LESSONS:
        folder=OUT/lesson['id']; video=folder/(lesson['id']+'_v1.mp4')
        if video.exists():
            print('Preserving existing master: '+lesson['id'],flush=True);global_frame+=len(lesson['scenes']);continue
        response=json.loads((folder/'VOICE_RESPONSE_V1.json').read_text(encoding='utf-8'))
        wav=folder/'brian_decoded_v1.wav'
        run([ff,'-v','error','-y','-i',str(folder/'brian_source_v1.mp3'),'-ar','48000','-ac','1',str(wav)])
        with wave.open(str(wav),'rb') as w: data=w.readframes(w.getnframes()); duration=w.getnframes()/48000
        timeline,words,pauses,total=align_scenes(lesson,response,duration)
        chunks=[];start=0
        for at,length in pauses:
            cut=round(at*48000)*2;chunks.extend([data[start:cut],b'\x00\x00'*round(length*48000)]);start=cut
        chunks.append(data[start:]); audio=folder/'brian_narration_v1.wav'
        with wave.open(str(audio),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(b''.join(chunks))
        cap=captions(words)
        # Alignment is millisecond-quantized; decoded PCM is sample-quantized.
        # Bound the last subtitle to the actual audio end rather than extending it.
        for c in cap: c['end']=min(c['end'],total)
        vtt=['WEBVTT','']
        for i,c in enumerate(cap,1):vtt.extend([str(i),stamp(c['start'])+' --> '+stamp(c['end']),c['text'],''])
        (folder/'captions_v1.vtt').write_text('\n'.join(vtt),encoding='utf-8')
        chapters=[';FFMETADATA1'];concat=[]
        for i,cue in enumerate(timeline):
            chapters.extend(['[CHAPTER]','TIMEBASE=1/1000','START='+str(round(cue['start']*1000)),'END='+str(round(cue['end']*1000)),'title='+cue['title']])
            concat.extend([f"file '../frames/f{global_frame+i:06d}.png'",f"duration {cue['end']-cue['start']:.9f}"])
        concat.append(f"file '../frames/f{global_frame+len(timeline)-1:06d}.png'")
        (folder/'chapters.ffmeta').write_text('\n'.join(chapters),encoding='utf-8');(folder/'visuals.concat.txt').write_text('\n'.join(concat),encoding='utf-8')
        run([ff,'-v','error','-n','-f','concat','-safe','0','-i',str(folder/'visuals.concat.txt'),'-i',str(audio),'-i',str(folder/'captions_v1.vtt'),'-i',str(folder/'chapters.ffmeta'),'-map','0:v','-map','1:a','-map','2:s','-map_metadata','3','-map_chapters','3','-vf','fps=30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ar','48000','-c:s','mov_text','-metadata:s:s:0','language=eng','-t',str(total),'-movflags','+faststart',str(video)])
        run([ff,'-v','error','-i',str(video),'-map','0:v','-map','0:a','-f','null','-'])
        count,vd=imageio_ffmpeg.count_frames_and_secs(str(video))
        report=dict(lesson=lesson['id'],duration_s=total,video_duration_s=vd,decoded_frames=count,video_sha256=sha(video),voice_id=VOICE,model=MODEL,settings=SETTINGS,timeline=timeline,captions=cap,pauses=[dict(at=at,seconds=n) for at,n in pauses],audio_duration_s=len(b''.join(chunks))/96000,first_frame=global_frame,status='technical_checks_passed_human_listening_review_pending')
        write(folder/'QA_REPORT_V1.json',report);global_frame+=len(timeline)
        print(f"Encoded and decoded {lesson['id']}: {total:.2f} seconds",flush=True)

def combine():
    require_unfrozen()
    ff=ffmpeg();target=OUT/'cm_advanced_complete_course_v1.mp4'
    if target.exists():raise RuntimeError('Preserve existing combined course')
    # Concatenate video/audio only, then add a continuous caption track and lesson chapters.
    videos=[];caps=[];chapters=[';FFMETADATA1'];cursor=0
    for lesson in curriculum.LESSONS:
        folder=OUT/lesson['id'];report=json.loads((folder/'QA_REPORT_V1.json').read_text(encoding='utf-8'))
        videos.append("file '"+(folder/(lesson['id']+'_v1.mp4')).as_posix()+"'")
        dur=round(report['decoded_frames']/30,9)
        chapters.extend(['[CHAPTER]','TIMEBASE=1/1000','START='+str(round(cursor*1000)),'END='+str(round((cursor+dur)*1000)),'title='+lesson['title']])
        caps += [{**c,'start':c['start']+cursor,'end':c['end']+cursor} for c in report['captions']]
        cursor+=dur
    (OUT/'course.concat.txt').write_text('\n'.join(videos),encoding='utf-8')
    (OUT/'course.ffmeta').write_text('\n'.join(chapters),encoding='utf-8')
    vtt=['WEBVTT','']
    for i,c in enumerate(caps,1):vtt.extend([str(i),stamp(c['start'])+' --> '+stamp(c['end']),c['text'],''])
    (OUT/'course_captions_v1.vtt').write_text('\n'.join(vtt),encoding='utf-8')
    run([ff,'-v','error','-n','-f','concat','-safe','0','-i',str(OUT/'course.concat.txt'),'-i',str(OUT/'course_captions_v1.vtt'),'-i',str(OUT/'course.ffmeta'),'-map','0:v:0','-map','0:a:0','-map','1:s:0','-map_metadata','2','-map_chapters','2','-c:v','copy','-c:a','aac','-b:a','192k','-c:s','mov_text','-metadata:s:s:0','language=eng','-movflags','+faststart',str(target)])
    run([ff,'-v','error','-i',str(target),'-map','0:v','-map','0:a','-f','null','-'])
    write(OUT/'COURSE_QA_V1.json',dict(expected_duration_s=cursor,chapters=len(curriculum.LESSONS),video_sha256=sha(target),full_decode='passed'))
    print('Combined course encoded and decoded',flush=True)

if __name__=='__main__':
    {'prepare':prepare,'generate':generate,'assemble':assemble,'combine':combine}[sys.argv[1]]()
