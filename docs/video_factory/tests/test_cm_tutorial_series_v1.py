"""Semantic and delivery checks for the new teaching series."""
from pathlib import Path
import itertools, json, sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'docs/video_factory'))
import cm_tutorial_curriculum_v1 as content
import cm_tutorial_visuals_v1 as visual
import cm_tutorial_series_v1 as production

def test_all_operator_patterns_are_distinct_and_match_rules():
    funcs=[lambda x,y:1,lambda x,y:0,lambda x,y:x==y,lambda x,y:x!=y,
           lambda x,y:x and y,lambda x,y:not(x or y),lambda x,y:x and not y,
           lambda x,y:not x and y,lambda x,y:not x or y,lambda x,y:not y or x,
           lambda x,y:x or y,lambda x,y:not(x and y),lambda x,y:y,
           lambda x,y:not y,lambda x,y:x,lambda x,y:not x]
    assert len(set(pat for _,pat in visual.OPS))==16
    for (_,pattern),fn in zip(visual.OPS,funcs):
        assert pattern==''.join(str(int(fn(x,y))) for x,y in itertools.product((1,0),repeat=2))

def test_outer_product_and_selection_have_different_shapes():
    ket=np.array([[1],[0]]);bra=np.array([[0,1]])
    assert (ket@bra).tolist()==[[0,1],[0,0]]
    xor=np.array([[0,1],[1,0]])
    assert (bra@xor@ket).shape==(1,1)
    assert int((bra@xor@ket)[0,0])==1

def test_symbolic_tensor_contains_all_literal_patterns_in_correct_positions():
    rows=visual.tensor_rows()
    expected=[]
    for w,y in itertools.product((1,0),repeat=2):
        expected.append([''.join(k if v else '¬'+k for k,v in [('W',w),('X',x),('Y',y),('Z',z)]) for x,z in itertools.product((1,0),repeat=2)])
    assert rows==expected
    assert len({s for r in rows for s in r})==16
    assert rows[1][2]=='W¬X¬YZ'

def test_compound_matrix_against_direct_logic_for_all_assignments():
    a,b,terms,matrix=visual.compound_data()
    assert matrix==[[1,1,0,0],[1,1,1,0],[0,0,1,1],[1,0,1,1]]
    for r,(w,y) in enumerate(itertools.product((1,0),repeat=2)):
        for c,(x,z) in enumerate(itertools.product((1,0),repeat=2)):
            direct=int((w==x) or ((y==0) and z))
            assert matrix[r][c]==direct
            assert sum(t[r][c] for t in terms)<=1
    assert matrix[2][0]==0

def test_all_repository_layouts_against_actual_api_and_scalar_rule():
    from cm_exprlib import Var, And, Or, Xor
    from cm_build import compile_expr_to_cm, eval_cm_boolean
    expr=Xor(And(Var(0),Var(1)),Or(Var(2),Var(3)))
    names=dict(zip('ABCD',['x0','x1','x2','x3']))
    for rv,cv in [('AB','CD'),('A','BCD'),('ABC','D')]:
        R=[names[x] for x in rv];C=[names[x] for x in cv]
        actual=compile_expr_to_cm(expr,R,C,{},use_persistent_cache=False)
        shown=visual.repo_matrix(rv,cv)
        assert actual.tolist()==shown
        for bits in itertools.product((0,1),repeat=4):
            env=dict(zip('ABCD',bits));a,b,c,d=bits
            r=int(''.join(str(env[v]) for v in rv),2);co=int(''.join(str(env[v]) for v in cv),2)
            direct=int(bool(a and b)!=bool(c or d))
            assert actual[r,co]==direct==eval_cm_boolean(actual,R,C,{names[k]:v for k,v in env.items()},{})

def test_every_lesson_has_practice_and_new_notation():
    assert len(content.LESSONS)==7
    for l in content.LESSONS:
        questions=[s for s in l['scenes'] if s.get('question')]
        assert len(questions)==1 and questions[0]['pause']==5
        html=''.join(visual.page(l,s,i,'','') for i,s in enumerate(l['scenes']))
        assert '⊕' not in html and '\\oplus' not in html
        assert 'top-left entry of' not in html and '(W,Y)\\' not in html
        assert 'M_WX' not in html  # shown as a real subscript

def test_generated_audio_matches_full_scripts_and_one_voice():
    for l in content.LESSONS:
        path=content.OUT/l['id']/'VOICE_RESPONSE_V1.json'
        if not path.exists():continue
        data=json.loads(path.read_text(encoding='utf-8'))
        assert data['voice_id']==production.VOICE
        assert data['payload']['voice_settings']==production.SETTINGS
        assert data['payload']['model_id']==production.MODEL
        assert data['payload']['text']=='\n\n'.join(s['text'] for s in l['scenes'])
        a=data['alignment'];st=a['character_start_times_seconds'];en=a['character_end_times_seconds']
        assert len(st)==len(en)==len(a['characters']) and st==sorted(st)
        assert all(0<=x<=y for x,y in zip(st,en))

def test_delivery_timing_and_hidden_answer_pauses():
    for l in content.LESSONS:
        path=content.OUT/l['id']/'QA_REPORT_V1.json'
        if not path.exists():continue
        q=json.loads(path.read_text(encoding='utf-8'));t=q['timeline']
        assert abs(q['duration_s']-q['audio_duration_s'])<.001
        assert abs(q['decoded_frames']/30-q['duration_s'])<.1
        assert all(abs(a['end']-b['start'])<1e-7 for a,b in zip(t,t[1:]))
        for s,c in zip(l['scenes'],t):
            if s.get('question'):
                assert abs(c['end']-c['speech_end']-5)<1e-9
                assert not any(x['start']<c['end']-.001 and x['end']>c['speech_end']+.001 for x in q['captions'])
        assert all(0<=x['start']<x['end']<=q['duration_s'] for x in q['captions'])
        assert all(max(map(len,x['text'].splitlines()))<=42 and len(x['text'].splitlines())<=2 for x in q['captions'])

def test_complete_delivery_and_real_silent_practice_intervals():
    import wave
    assert (content.OUT/'cm_foundations_complete_course_v1.mp4').stat().st_size>1000000
    layout=json.loads((content.OUT/'LAYOUT_QA_V1.json').read_text())
    assert layout['frames']==75 and layout['failed_frames']==0
    assert len(list(content.OUT.glob('*/VOICE_RESPONSE_V1.json')))==7
    for l in content.LESSONS:
        folder=content.OUT/l['id']
        assert (folder/(l['id']+'_v1.mp4')).stat().st_size>1000000
        q=json.loads((folder/'QA_REPORT_V1.json').read_text())
        with wave.open(str(folder/'brian_narration_v1.wav'),'rb') as source:
            assert source.getframerate()==48000 and source.getnchannels()==1
            samples=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2')
        assert np.max(np.abs(samples.astype(np.int32)))>1000
        for scene in q['timeline']:
            if scene['pause']:
                start=round(scene['speech_end']*48000)
                assert np.all(samples[start:start+5*48000]==0)
