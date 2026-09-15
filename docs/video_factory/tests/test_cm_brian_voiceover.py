import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def load():
    spec=importlib.util.spec_from_file_location('brian',ROOT/'docs/video_factory/cm_brian_voiceover.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_only_spoken_content_is_sent_to_tts():
    module=load()
    cues=module.cues()
    assert {c['chapter'] for c in cues}==set(range(1,8))
    assert [c['chapter'] for c in cues if c['kind']=='pause']==[2,5,6]
    for cue in cues:
        if cue['kind']=='speech':
            assert not cue['text'].startswith(('Visual alignment:', '#', '['))

def test_cached_speech_has_ordered_alignment_and_exact_text():
    module=load()
    for cue in module.cues():
        if cue['kind']=='pause': continue
        response=json.loads((module.OUT/'audio'/(cue['id']+'.json')).read_text(encoding='utf-8'))
        assert response['text']==cue['text']
        assert response['voice_id']=='Fu3xLoDFv9UvgA2FXCUS'
        a=response.get('normalized_alignment') or response['alignment']
        starts=a['character_start_times_seconds']; ends=a['character_end_times_seconds']
        assert len(a['characters'])==len(starts)==len(ends)>0
        assert starts==sorted(starts)
        assert all(0<=s<=e for s,e in zip(starts,ends))
        assert (module.OUT/'audio'/(cue['id']+'.mp3')).stat().st_size>1000
