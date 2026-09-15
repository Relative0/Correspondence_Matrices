from pathlib import Path
import itertools,json,sys,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'docs/video_factory'))
import cm_advanced_curriculum_v1 as c
import cm_advanced_examples_v1 as examples
import cm_advanced_series_v1 as p
import cm_advanced_visuals_v1 as v

def mul(a,b):
    a=np.array(a,dtype=int);b=np.array(b,dtype=int)
    return np.bitwise_xor.reduce(a[:,:,None]&b[None,:,:],axis=1)

def measure(a,t,b):return int(mul(mul([[a,1-a]],t),[[b],[1-b]])[0,0])

def test_all_operator_transformations():
    for bits in itertools.product((0,1),repeat=4):
        t=np.array(bits).reshape(2,2)
        for x,y in itertools.product((0,1),repeat=2):
            assert measure(x,t.T,y)==measure(y,t,x)
            assert measure(x,1-t,y)==1-measure(x,t,y)
            assert measure(x,t[::-1],y)==measure(1-x,t,y)
            assert measure(x,t[:,::-1],y)==measure(x,t,1-y)
        assert np.array_equal(np.rot90(t.T,-1),t[:,::-1])
        assert np.array_equal(np.rot90(t.T,-3),t[::-1])

def test_all_entrywise_compositions_and_quotients():
    tables=[np.array(x).reshape(2,2) for x in itertools.product((0,1),repeat=4)]
    for a,b in itertools.product(tables,repeat=2):
        for x,y in itertools.product((0,1),repeat=2):
            assert measure(x,a^b,y)==(measure(x,a,y)^measure(x,b,y))
            assert measure(x,a&(1-b),y)==(measure(x,a,y)&(1-measure(x,b,y)))
    assert (np.array(c.OPS['⇒'])^c.OPS['∨']).tolist()==c.OPS['¬R']
    assert (np.array(c.OPS['¬∧'])^c.OPS['∨']).tolist()==c.OPS['⇔']
    assert (np.array(c.OPS['⇐'])^c.OPS['∨']).tolist()==c.OPS['¬L']

def test_lm_factorization_and_wrong_product_counterexample():
    for x,y in itertools.product((0,1),repeat=2):
        xl=np.array([[x,x],[1-x,1-x]]);yr=np.array([[y,1-y],[y,1-y]])
        outer=np.array([[x*y,x*(1-y)],[(1-x)*y,(1-x)*(1-y)]])
        assert np.array_equal(xl&yr,outer)
        assert not mul(xl,yr).any()
        assert np.array_equal(1-(xl&yr),(1-xl)|(1-yr))

def test_lm_measurements_for_all_operators_and_valuations():
    for bits in itertools.product((0,1),repeat=4):
        t=np.array(bits).reshape(2,2)
        for x,y in itertools.product((0,1),repeat=2):
            lm=np.array([[measure(x,t,y),measure(x,t,1-y)],[measure(1-x,t,y),measure(1-x,t,1-y)]])
            for i,j in itertools.product((0,1),repeat=2):
                left=x if i==0 else 1-x;right=y if j==0 else 1-y
                assert measure(left,lm,right)==t[i,j]
            if np.array_equal(t,c.OPS['⇒']):
                assert mul([[x,1-x]],lm).tolist()==[[y,1-y]]
                for z in (0,1):assert measure(x,lm,z)==int(y==z)

def test_tensor_entries_and_numeric_example():
    for names,table in [('WXYZ',c.T4),('ABCDEF',c.T6)]:
        n=len(names)//2
        for ri,rb in enumerate(itertools.product((1,0),repeat=n)):
            for ci,cb in enumerate(itertools.product((1,0),repeat=n)):
                expected=''.join(('' if b else '¬')+names[j] for j,b in enumerate(sum(([rb[k],cb[k]] for k in range(n)),[])))
                assert table[ri][ci]==expected
    t=np.array(c.OPS['⇕']);tensor=np.kron(np.kron(t,t),t)
    for bits in itertools.product((0,1),repeat=6):
        a,b,d,e,f,g=bits
        ri=(1-a)*4+(1-d)*2+(1-f);ci=(1-b)*4+(1-e)*2+(1-g)
        assert tensor[ri,ci]==((a^b)&(d^e)&(f^g))
    assert c.T6[2][5]=='A¬B¬CDE¬F'

def test_large_composition_and_permutation():
    for w,x,y,z in itertools.product((0,1),repeat=4):
        d=dict(W=w,X=x,Y=y,Z=z);ri=(1-w)*2+(1-y);ci=(1-x)*2+(1-z)
        f=int((not(w^x)) or ((not y) and z));g=int(not(bool(y and not z)==bool(not w)))
        assert c.GAMMA1[ri][ci]==f and c.GAMMA2[ri][ci]==g
        assert c.GAMMA[ri][ci]==int((not f) or g)
        permuted=c.grid4(c.F4,('Y','W'))
        assert permuted[(1-y)*2+(1-w)][ci]==f
    assert c.GAMMA==[[0,1,1,1],[0,0,0,1],[1,1,1,0],[1,1,1,1]]

def test_repository_examples():
    result=examples.run_examples()
    assert result['layouts'][0]['matrix']==c.REPO
    assert result['policy_matrix']==c.POLICY and result['policy_allowed']==3
    assert result['packed_integer']==7918 and result['true_count']==10
    assert result['hypothetical_break_even_queries']==48

def test_course_coverage_and_notation():
    assert p.MODEL=='eleven_multilingual_v2'
    assert p.VOICE=='Fu3xLoDFv9UvgA2FXCUS'
    assert [int(x['id'][:2]) for x in c.LESSONS]==list(range(10,24))
    for l in c.LESSONS:
        assert len([s for s in l['scenes'] if s.get('pause')==5])==1
        assert l['source'] and l['prerequisite']
        for i,s in enumerate(l['scenes']):
            page=v.page(l,s,i,'','')
            assert not any(bad in page for bad in ['→','⊕','M<sub>⇕</sub>','\\oplus'])
            assert len(s['text'].split())>=28

def test_finished_media_when_present():
    if not (c.OUT/'COURSE_QA_V1.json').exists():return
    assert len(list(c.OUT.glob('[12][0-9]_*/*_v1.mp4')))==14
    for l in c.LESSONS:
        f=c.OUT/l['id'];q=json.loads((f/'QA_REPORT_V1.json').read_text(encoding='utf-8'))
        receipt=json.loads((f/'VOICE_RESPONSE_V1.json').read_text(encoding='utf-8'))
        assert receipt['voice_id']==p.VOICE and receipt['payload']['voice_settings']==p.SETTINGS
        assert receipt['payload']['model_id']==p.MODEL
        assert receipt['source_audio_sha256']==p.sha(f/'brian_source_v1.mp3')
        assert receipt['payload']['text']=='\n\n'.join(s['text'] for s in l['scenes'])
        assert abs(q['decoded_frames']/30-q['duration_s'])<.1
        assert q['video_sha256']==p.sha(f/(l['id']+'_v1.mp4'))
        with wave.open(str(f/'brian_narration_v1.wav'),'rb') as w:data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')
        for s in q['timeline']:
            if s['pause']:
                start=round(s['speech_end']*48000);assert np.all(data[start:start+240000]==0)
                assert not any(x['start']<s['end']-.001 and x['end']>s['speech_end']+.001 for x in q['captions'])
        for cap in q['captions']:
            assert 0<=cap['start']<cap['end']<=q['duration_s']
            assert len(cap['text'].splitlines())<=2 and max(map(len,cap['text'].splitlines()))<=42
