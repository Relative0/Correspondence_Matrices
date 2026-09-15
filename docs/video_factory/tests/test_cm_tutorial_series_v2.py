from pathlib import Path
import sys,json,itertools,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docs/video_factory'))
import cm_tutorial_curriculum_v2 as c
import cm_tutorial_visuals_v2 as v
import cm_tutorial_series_v2 as p

def mul(a,b):
    out=np.zeros((len(a),len(b[0])),dtype=int)
    for i in range(len(a)):
        for j in range(len(b[0])):
            for k in range(len(b)):out[i,j]^=int(a[i][k]) & int(b[k][j])
    return out.tolist()

def test_xor_actual_intermediates_and_final_results():
    bra=[[0,1]];cm=[[0,1],[1,0]];ket=[[1],[0]]
    assert mul(bra,cm)==[[1,0]] and mul(cm,ket)==[[0],[1]]
    assert mul(mul(bra,cm),ket)==[[1]]==mul(bra,mul(cm,ket))
    assert mul(mul(bra,cm),[[0],[1]])==[[0]]

def test_all_64_numeric_measurements_and_groupings():
    for flat in itertools.product((0,1),repeat=4):
        cm=[list(flat[:2]),list(flat[2:])]
        for x,y in itertools.product((0,1),repeat=2):
            bra=[[x,1-x]];ket=[[y],[1-y]]
            assert mul(mul(bra,cm),ket)==mul(bra,mul(cm,ket))==[[cm[1-x][1-y]]]

def test_paper_symbolic_derivation_for_every_assignment():
    for x,y in itertools.product((0,1),repeat=2):
        intermediate=mul([[x,1-x]],[[1,0],[1,1]])
        assert intermediate==[[1,1-x]]
        assert y ^ ((1-x)&(1-y))==int((not x) or y)==mul(intermediate,[[y],[1-y]])[0][0]
        assert not (y and ((1-x)&(1-y)))

def test_impax_and_operator_faces():
    assert len(v.SYMBOLS)==len(set(v.SYMBOLS))==16
    assert np.bitwise_xor([[1,0],[0,1]],[[0,1],[1,0]]).tolist()==[[1,1],[1,1]]
    assert '⇔' in v.impax() and '⇕' in v.impax()
    assert v.SYMBOLS==['impax','0','⇔','⇕','∧','¬∨','⇑','⇓','⇒','⇐','∨','¬∧','R','¬R','L','¬L']

def test_advanced_examples_and_page12_projection_correction():
    implication=np.array([[1,0],[1,1]]);or_cm=np.array([[1,1],[1,0]]);and_cm=np.array([[1,0],[0,0]])
    assert (implication^or_cm).tolist()==[[0,1],[0,1]]
    assert (or_cm & (1-and_cm)).tolist()==[[0,1],[1,0]]
    assert (and_cm & (1-or_cm)).tolist()==[[0,0],[0,0]]
    for x,y in itertools.product((0,1),repeat=2):
        assert int(bool((not x) or y)!=bool(x or y))==1-y

def test_order_notation_and_visible_computations():
    assert [x['id'][:2] for x in c.LESSONS]==[f'{i:02}' for i in range(1,10)]
    assert c.LESSONS[2]['scenes'][0]['visual']=='numeric_measurement'
    assert c.LESSONS[3]['scenes'][0]['visual']=='symbolic_measurement'
    html=''.join(v.page(l,s,i,'','') for l in c.LESSONS for i,s in enumerate(l['scenes']))
    for bad in ['M<sub>⇕</sub>','M⇕','⊕','\\oplus','top-left entry of']:assert bad not in html
    for required in ['(0∧0) ⇕ (1∧1)','(0∧1) ⇕ (1∧0)','1 ⇕ 0 = 1','0 ⇕ 1 = 1','X ⇕ ¬X','Y ⇕ (¬X∧¬Y)']:assert required in html
    for l in c.LESSONS:assert len([s for s in l['scenes'] if s.get('pause')==5])==1
    first=c.LESSONS[0]['scenes']
    assert next(i for i,s in enumerate(first) if s['visual']=='operator_definition')<next(i for i,s in enumerate(first) if s.get('question'))

def test_delivery():
    if not (c.OUT/'COURSE_QA_V2.json').exists():return
    delivered=set(c.OUT.glob('[0-9][0-9]_*/*_v2.mp4'))
    assert delivered=={c.OUT/l['id']/(l['id']+'_v2.mp4') for l in c.LESSONS}
    assert len(delivered)==9
    for l in c.LESSONS:
        f=c.OUT/l['id'];receipt=json.loads((f/'VOICE_RESPONSE_V2.json').read_text(encoding='utf-8'))
        assert receipt['voice_id']==p.VOICE and receipt['payload']['voice_settings']==p.SETTINGS
        assert receipt['payload']['text']=='\n\n'.join(s['text'] for s in l['scenes'])
        report=json.loads((f/'QA_REPORT_V2.json').read_text(encoding='utf-8'))
        assert abs(report['decoded_frames']/30-report['duration_s'])<.1
        with wave.open(str(f/'brian_narration_v2.wav'),'rb') as w:data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
        for s in report['timeline']:
            if s['pause']:
                start=round(s['speech_end']*48000);assert np.all(data[start:start+240000]==0)
                assert not any(x['start']<s['end']-.001 and x['end']>s['speech_end']+.001 for x in report['captions'])
        for cap in report['captions']:
            assert 0<=cap['start']<cap['end']<=report['duration_s']
            assert len(cap['text'].splitlines())<=2 and max(map(len,cap['text'].splitlines()))<=42

def test_reused_audio_is_exact():
    for l in c.LESSONS:
        if 'reuse_audio_from' not in l or not (c.OUT/l['id']/'brian_source_v2.mp3').exists():continue
        assert p.sha(c.old.OUT/l['reuse_audio_from']/'brian_source_v1.mp3')==p.sha(c.OUT/l['id']/'brian_source_v2.mp3')
