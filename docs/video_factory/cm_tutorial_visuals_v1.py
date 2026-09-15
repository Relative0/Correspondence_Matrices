"""Code-native CM teaching diagrams rendered with the existing POP frame driver."""
from html import escape
import itertools

PAIRS = list(itertools.product((1,0), repeat=2))
OPS = [('TRUE','1111'),('FALSE','0000'),('X↔Y','1001'),('X⇕Y','0110'),
       ('X∧Y','1000'),('NOR','0001'),('X∧¬Y','0100'),('¬X∧Y','0010'),
       ('X→Y','1011'),('Y→X','1101'),('X∨Y','1110'),('NAND','0111'),
       ('Y','1010'),('¬Y','0101'),('X','1100'),('¬X','0011')]

def mname(sub): return f'M<sub>{sub}</sub>'
def eq(t): return f'<div class="equation">{t}</div>'
def small(t): return f'<div class="small">{t}</div>'
def tag(t): return f'<div class="tag">{t}</div>'
def panel(t,body): return f'<section class="panel">{tag(t)}{body}</section>'
def split(a,b,cls=''): return f'<div class="split {cls}">{a}{b}</div>'
def stack(*parts): return '<div class="stack">'+''.join(parts)+'</div>'
def values(pattern): return [list(pattern[:2]),list(pattern[2:])]

def matrix(rows, rlabels=None, clabels=None, select=None, markrow=None, markcol=None,
           block=None, size='normal', hidden=None, axis=''):
    nr,nc=len(rows),len(rows[0]); hidden=hidden or []
    cols=f'<th class="corner">{axis}</th>' if rlabels else ''
    if clabels: cols+=''.join(f'<th class="{ "axis-on" if markcol==c or select and select[1]==c else ""}">{v}</th>' for c,v in enumerate(clabels))
    body='<thead><tr>'+cols+'</tr></thead>' if clabels else ''
    for r,row in enumerate(rows):
        body+='<tr>'
        if rlabels: body+=f'<th class="{ "axis-on" if markrow==r or select and select[0]==r else ""}">{rlabels[r]}</th>'
        for c,value in enumerate(row):
            cls=['cell']
            if select==[r,c]: cls+=['selected']
            elif markrow==r or markcol==c: cls+=['guided']
            if block is not None and [r//2,c//2]==block: cls+=['block-on']
            if nr==4 and r==2: cls+=['block-top']
            if nc==4 and c==2: cls+=['block-left']
            if value in (0,'0'): cls+=['zero']
            if [r,c] in hidden: value='?'
            body+=f'<td class="{" ".join(cls)}">{value}</td>'
        body+='</tr>'
    return f'<div class="matrix-wrap {size}"><table class="matrix">{body}</table></div>'

def trace(lines, active=None):
    return '<div class="trace">'+''.join(f'<div class="trace-line {"active" if i==active else ""}"><span class="number">{i+1}</span><span>{line}</span></div>' for i,line in enumerate(lines))+'</div>'

def tensor_rows():
    rows=[]
    for w,y in PAIRS:
        row=[]
        for x,z in PAIRS:
            row.append(''.join(v if b else '¬'+v for v,b in zip('WXYZ',(w,x,y,z))))
        rows.append(row)
    return rows

def kron(a,b): return [[a[r//2][c//2]*b[r%2][c%2] for c in range(4)] for r in range(4)]
def neg(a): return [[1-x for x in r] for r in a]
def compound_data():
    a=[[0,1],[1,0]]; b=[[0,0],[1,0]]
    terms=[kron(a,b),kron(neg(a),b),kron(neg(a),neg(b))]
    result=[[terms[0][r][c]^terms[1][r][c]^terms[2][r][c] for c in range(4)] for r in range(4)]
    return a,b,terms,result

def repo_matrix(rvars, cvars):
    result=[]
    for r in range(2**len(rvars)):
        row=[]
        for c in range(2**len(cvars)):
            assignment=dict(zip(rvars+cvars,map(int,format(r,f'0{len(rvars)}b')+format(c,f'0{len(cvars)}b'))))
            a,b,cv,d=[assignment[v] for v in 'ABCD']
            row.append(int((a and b) ^ (cv or d)))
        result.append(row)
    return result

def truth(s):
    rule=s['rule']; pattern=dict(and_='1000',or_='1110',xor_='0110')[rule+'_']
    title={'and':'X ∧ Y','or':'X ∨ Y','xor':'X ⇕ Y'}[rule]
    step=s['step']; q=s.get('question',False)
    table='<table class="truth"><tr><th>X</th><th>Y</th><th>output</th></tr>'
    for i,((x,y),out) in enumerate(zip(PAIRS,pattern)):
        selected=s.get('select')==[i//2,i%2]
        table+=f'<tr class="{"truth-on" if selected else ""}"><td>{x}</td><td>{y}</td><td>{out if step else "?"}</td></tr>'
    table+='</table>'
    grid=matrix(values(pattern),['X=1','X=0'],['Y=1','Y=0'],select=s.get('select'))
    return split(panel('TRUTH TABLE',table),panel('IDENTIFY THIS RULE' if q else title,grid if step>=2 else eq('four input cases<br>↓<br>four outputs')))

def body(s):
    v=s['visual']; p=s.get('step',0); q=s.get('question',False)
    if v=='door':
        return split(panel('TWO INPUTS',trace(['X: valid pass','Y: access enabled','1 means yes · 0 means no'])),panel('OPEN ONLY IF BOTH ARE YES','<div class="door-art"><div class="door-leaf"><span>ACCESS</span><b>✓</b><i></i></div></div>'+eq('open = X ∧ Y')))
    if v=='truth': return truth(s)
    if v=='sixteen':
        return '<div class="operator-family">'+''.join(f'<div class="operator">{tag(n)}{matrix(values(pat),size="mini")}</div>' for n,pat in OPS)+'</div>'
    if v=='orders':
        return split(panel('PAPER · TRUE FIRST',matrix([[1,0],[0,0]],['X=1','X=0'],['Y=1','Y=0'],select=[0,0])),panel('WEBSITE EXAMPLE · FALSE FIRST',matrix([[0,0],[0,1]],['X=0','X=1'],['Y=0','Y=1'],select=[1,1])))+small('Both labelled grids represent X ∧ Y.')
    if v=='vectors':
        if p==0: return split(panel('TRUE STATE',eq('|1⟩ =')+matrix([[1],[0]],size='vector')),panel('FALSE STATE',eq('|0⟩ =')+matrix([[0],[1]],size='vector')))
        return split(panel('COLUMN · KET',eq('|0⟩ =')+matrix([[0],[1]],size='vector')),panel('TRANSPOSE TO A ROW · BRA',eq('⟨0| =')+matrix([[0,1]],size='vector')+small('2×1 column → 1×2 row')))
    if v=='outer':
        return split(panel('OUTER PRODUCT', '<div class="inline-math">'+matrix([[1],[0]],size='vector')+eq('×')+matrix([[0,1]],size='vector')+'</div>'+eq('|1⟩⟨0|')),panel('FOUR MULTIPLICATIONS',matrix([['1×0 = 0','1×1 = 1'],['0×0 = 0','0×1 = 0']],select=[0,1],size='expressions')+small('column × row → matrix')))
    if v=='basis':
        if p==0: return panel('X ⇕ Y',matrix([[0,1],[1,0]],['X=1','X=0'],['Y=1','Y=0'],select=[0,1]))
        if p==1: return '<div class="four-basis">'+''.join(panel(f'|{r}⟩⟨{c}|',matrix([[int(rr==r and cc==c) for cc in (1,0)] for rr in (1,0)])) for r,c in PAIRS)+'</div>'
        return '<div class="sum">'+panel('|1⟩⟨0|',matrix([[0,1],[0,0]]))+eq('⇕')+panel('|0⟩⟨1|',matrix([[0,0],[1,0]]))+eq('=')+panel('X ⇕ Y',matrix([[0,1],[1,0]]))+'</div>'
    if v=='selection':
        left=trace(['Left bra: choose row X=0','Right ket: choose column Y=1','Read their intersection'],min(p,2))
        right=matrix([[0,1],[1,0]],['X=1','X=0'],['Y=1','Y=0'],select=[1,0] if p==2 else None)
        return split(panel('SELECT ONE ANSWER',eq('⟨0| '+mname('⇕')+' |1⟩ = '+('1' if p==2 else '?'))+left),panel('X ⇕ Y',right))
    if v=='implications':
        return split(panel('X → Y',matrix([[1,0],[1,1]],['X=1','X=0'],['Y=1','Y=0'],select=[0,1])),panel('Y → X',matrix([[1,1],[0,1]],['X=1','X=0'],['Y=1','Y=0'],select=[1,0])))
    if v=='lm':
        symbolic=[['X∧Y','X∧¬Y'],['¬X∧Y','¬X∧¬Y']]
        if p<=1:
            left=eq('|X⟩ =')+matrix([['X'],['¬X']],size='vector')+small('A column of expressions')
            right=eq('⟨Y| =')+matrix([['Y','¬Y']],size='vector')+small('A row of expressions')
            return split(panel('FIRST FACTOR',left),panel('SECOND FACTOR',right))
        left=eq(mname('XY')+' =')+matrix(symbolic,size='expressions')
        if p==2: right=eq(mname('XY')+' = |X⟩⟨Y|')+trace(['Top row uses X','Bottom row uses ¬X','Each cell combines one row and one column factor'])
        else:
            result=[['1∧1','1∧0'],['0∧1','0∧0']] if p==3 else [[1,0],['0∧1','0∧0']] if p==4 else [[1,0],[0,0]]
            right=eq('X = Y = 1')+matrix(result,size='expressions')+small('¬X = ¬Y = 0')
        return split(panel('EXPRESSION-VALUED LM',left),panel('EVALUATE THE SAME ASSIGNMENT' if p>=3 else 'OUTER PRODUCT',right))
    if v=='equivalence_lm':
        return split(panel('EQUIVALENCE LM',eq(mname('X↔Y')+' =')+matrix([['X↔Y','X⇕Y'],['X⇕Y','X↔Y']],size='expressions')),panel('X = Y = 1',matrix([[1,0],[0,1]] if p==2 else [['?','?'],['?','?']])+small('Agreement on the diagonal; difference off the diagonal.')))
    if v=='tensor':
        a=[['WX','W¬X'],['¬WX','¬W¬X']]; b=[['YZ','Y¬Z'],['¬YZ','¬Y¬Z']]
        factors=split(panel('FIRST COMPLETE LM',eq(mname('WX')+' =')+matrix(a,size='factor')),panel('SECOND COMPLETE LM',eq(mname('YZ')+' =')+matrix(b,size='factor')))
        if p<=1: return '<div class="tensor-intro">'+factors+eq(mname('WX')+' ⊗ '+mname('YZ'))+small('The tensor symbol combines the two complete matrices.')+'</div>'
        rows=tensor_rows()
        if p==2: rows=[['block 1','block 2'],['block 3','block 4']]
        elif p==3: rows=[[x if r<2 and c<2 else '·' for c,x in enumerate(row)] for r,row in enumerate(rows)]
        if q: rows[3][3]='?'
        labs=['WY','W¬Y','¬WY','¬W¬Y']; cols=['XZ','X¬Z','¬XZ','¬X¬Z']
        title=eq(mname('WX')+' ⊗ '+mname('YZ'))+small('Row components: (W,Y)     ·     Column components: (X,Z)')
        return title+matrix(rows,labs if p>=3 else None,cols if p>=3 else None,select=s.get('select'),block=s.get('block'),size='tensor')
    if v=='compound':
        a,b,terms,result=compound_data()
        form=eq('(W ⇕ X) → (¬Y ∧ Z)')
        if p==0: return form+split(panel('LEFT CONDITION · P',eq('W ⇕ X')+small('True when W and X differ.')),panel('RIGHT CONDITION · Q',eq('¬Y ∧ Z')+small('True when Y=0 and Z=1.')))
        if p==1:
            return form+split(panel('IMPLICATION',matrix([[1,0],[1,1]],['P=1','P=0'],['Q=1','Q=0'],select=[0,1])),panel('ONE FAILING CASE',eq('P = 1<br>Q = 0<br>↓<br>P → Q = 0')))
        if p==2: return form+split(panel('A: W ⇕ X',matrix(a,['W=1','W=0'],['X=1','X=0'])),panel('B: ¬Y ∧ Z',matrix(b,['Y=1','Y=0'],['Z=1','Z=0'],select=[1,0])))
        if 3<=p<=5:
            idx=p-3; names=['A⊗B','¬A⊗B','¬A⊗¬B']; statuses=['P=1, Q=1','P=0, Q=1','P=0, Q=0']
            return form+split(panel('ACCEPTED IMPLICATION CASES',trace([statuses[i]+'<br>'+names[i] for i in range(idx+1)],idx)),panel(names[idx],matrix(terms[idx],['11','10','01','00'],['11','10','01','00'],size='compact')+small('Rows WY · Columns XZ · true-first order')))
        left=trace(['A⊗B: both true','¬A⊗B: only Q true','¬A⊗¬B: both false'],2)
        if p>=7:
            left=eq('WXYZ = 0111')+trace(['WY = 01 → third row','XZ = 11 → first column', 'P=1; Q=0 → output '+('0' if p>=8 else '?')],0 if p==7 else 2)
        if q: left=eq('WXYZ = 0111')+trace(['Evaluate P = W ⇕ X','Evaluate Q = ¬Y∧Z','Find row WY and column XZ'])
        grid=matrix(result,['WY=11','WY=10','WY=01','WY=00'],['XZ=11','XZ=10','XZ=01','XZ=00'],select=[2,0] if p==9 else None,size='compact')
        return form+split(panel('CHECK THE CONDITIONS' if p>=7 else 'XOR THE THREE TERMS',left),panel('COMPLETE COMPOUND CM',grid))
    if v=='paper_order':
        return stack(panel('PAPER §5.1.1 · WRITTEN SELECTOR',eq('⟨Y|⟨W| [M] |X⟩|Z⟩')),split(panel('PHYSICAL ROW COMPONENTS',eq('(W,Y): 11, 10, 01, 00')),panel('PHYSICAL COLUMN COMPONENTS',eq('(X,Z): 11, 10, 01, 00'))),small('Use the component expansion with the paper’s reversed written bra factors.'))
    if v=='repo':
        bits=s.get('bits','1011'); a,b,c,d=map(int,bits); r=2*a+b; co=2*c+d
        grid=repo_matrix('AB','CD'); rows=[f'{i:02b} · {i}' for i in range(4)]; cols=rows
        lines=['Rows: AB · columns: CD']
        if p>=3: lines += [f'ABCD = {bits}<br>AB = {bits[:2]} · CD = {bits[2:]}']
        if p>=4: lines += [f'Row = {a}×2 + {b}×1 = <b>{r}</b>']
        if p>=5: lines += [f'Column = {c}×2 + {d}×1 = <b>{co}</b>']
        if p>=6: lines += [f'({a}∧{b}) ⇕ ({c}∨{d})<br>= {int(a and b)} ⇕ {int(c or d)} = <b>{grid[r][co]}</b>']
        left=trace(lines,len(lines)-1)
        if p<=2: left+=panel('BINARY → INDEX',eq('00 → 0 &nbsp; 01 → 1<br>10 → 2 &nbsp; 11 → 3')+small('Left bit has weight 2.<br>Right bit has weight 1.'))
        right=matrix(grid if p>=2 else [['·']*4 for _ in range(4)],rows,cols,markrow=r if p==4 else None,select=[r,co] if p>=5 else None,size='compact')
        return eq('F = (A∧B) ⇕ (C∨D)')+split(panel('SPLIT · INDEX · CHECK',left),panel('AB ROWS · CD COLUMNS',right+small('Each label shows binary bits · numeric index.')))
    if v=='repartition':
        if p==3:
            return eq('F = (A∧B) ⇕ (C∨D)')+'<table class="comparison"><tr><th>Row variables</th><th>Column variables</th><th>Shape</th><th>1011 address</th><th>value</th></tr><tr><td>A,B</td><td>C,D</td><td>4×4</td><td>(2,3)</td><td>1</td></tr><tr><td>A</td><td>B,C,D</td><td>2×8</td><td>(1,3)</td><td>1</td></tr><tr><td>A,B,C</td><td>D</td><td>8×2</td><td>(5,1)</td><td>1</td></tr></table>'+eq('4×4 = 2×8 = 8×2 = 16 cells')
        rv,cv=[('AB','CD'),('A','BCD'),('ABC','D')][p]; bits=s.get('bits','1011'); assign=dict(zip('ABCD',map(int,bits)))
        rb=''.join(str(assign[k]) for k in rv); cb=''.join(str(assign[k]) for k in cv); r,c=int(rb,2),int(cb,2)
        grid=repo_matrix(rv,cv); rows=[f'{i:0{len(rv)}b} · {i}' for i in range(len(grid))]; cols=[f'{i:0{len(cv)}b} · {i}' for i in range(len(grid[0]))]
        heading=eq(f'R = [{",".join(rv)}] &nbsp;&nbsp; C = [{",".join(cv)}]')
        if p==1:
            return heading+matrix(grid,rows,cols,select=[r,c] if s.get('select') else None,size='wide')+eq(f'ABCD = {bits} → {rv} = {rb} · {cv} = {cb}')+small('Binary bits · numeric index. Read each group from left to right.')
        return heading+split(panel('FOLLOW THE ASSIGNMENT',eq('ABCD = '+bits)+trace([rv+' = '+rb+' → row '+str(r),cv+' = '+cb+' → column '+str(c),'output = '+str(grid[r][c])])),panel(f'{len(grid)} ROWS × {len(grid[0])} COLUMNS',matrix(grid,rows,cols,select=[r,c] if s.get('select') else None,size='tall' if p==2 else 'compact')))
    raise ValueError(v)

CSS='''
*{box-sizing:border-box}body{margin:0;background:#091219;color:#edf5f9;font-family:CMsans, sans-serif;width:1280px;height:720px;overflow:hidden}
.stage{position:absolute;inset:0;padding:26px 36px 0;background:radial-gradient(ellipse at 90% 0,#12313c 0,transparent 55%)}
header{font-size:16px;letter-spacing:1.6px;color:#64d8e8;display:flex;justify-content:space-between;text-transform:uppercase}
h1{font-size:32px;line-height:1.13;margin:13px 0 12px;letter-spacing:-.5px;font-weight:650}
.content{height:445px;display:flex;flex-direction:column;justify-content:center;gap:8px}
.split{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:stretch;width:100%;min-height:0}
.panel{padding:15px 18px;background:#10222d;border-top:3px solid #59d1df;border-radius:2px;display:flex;flex-direction:column;justify-content:center;gap:10px;min-width:0}
.tag{font-size:16px;letter-spacing:.7px;color:#86dfe9;line-height:1.2;margin-bottom:4px}.equation{font-family:CMsans;font-size:30px;line-height:1.45;text-align:center;color:#f3f8fa}sub{font-size:.62em;vertical-align:sub}.small{font-size:20px;line-height:1.4;color:#c8dae3;text-align:center}
.matrix-wrap{display:flex;justify-content:center;align-items:center}.matrix{border-collapse:separate;border-spacing:4px;table-layout:fixed;max-width:100%}.matrix th{color:#8fe3ec;font-weight:500;font-size:19px;padding:6px;white-space:nowrap}.matrix td{background:#172e3c;border:1px solid #557483;text-align:center;font-size:35px;width:125px;min-width:74px;height:78px;padding:5px 12px;white-space:nowrap;font-family:CMsans}.matrix td.zero{color:#d2dce1}.matrix .selected{background:#453974;border:3px solid #c2abff;color:white;box-shadow:inset 0 0 0 1px #e0d1ff}.matrix .guided{background:#215467;border-color:#6adef0}.matrix .axis-on{background:#254b5e;color:white;border-radius:3px}.matrix .block-on{border-color:#bb9df4;background:#342e59}.matrix .block-top{border-top:3px solid #81949f}.matrix .block-left{border-left:3px solid #81949f}
.expressions .matrix td{font-size:26px;width:180px;height:78px}.vector .matrix td{width:115px;height:75px;font-size:36px}.vector .matrix{border-left:3px solid #dcecf4;border-right:3px solid #dcecf4}.compact .matrix td{width:94px;height:56px;font-size:30px}.compact .matrix th{font-size:17px}.factor .matrix td{font-size:24px;width:116px;height:61px}.factor-row{display:flex;justify-content:center;align-items:center;gap:16px}.factor-row .equation{font-size:26px}.tensor-intro{display:flex;flex-direction:column;gap:38px}.tensor .matrix td{font-size:25px;width:236px;height:60px}.tensor .matrix th{font-size:21px}.tensor .matrix{border-spacing:5px}.wide .matrix td{min-width:100px;width:115px;height:76px;font-size:32px}.wide .matrix th{font-size:18px}.tall .matrix td{height:35px;width:110px;font-size:24px;padding:1px 10px}.tall .matrix th{font-size:16px;padding:2px}
.trace{display:flex;flex-direction:column;gap:9px}.trace-line{display:flex;gap:12px;align-items:center;font-size:23px;line-height:1.28;padding:8px 10px;border-left:3px solid #46606f}.trace-line.active{background:#203d4d;border-color:#bba5ff}.number{font-family:CMmono;color:#8de4ec;font-size:18px}.trace b{color:#e3d3ff}.trace-line span:last-child{min-width:0}
.truth{border-collapse:collapse;text-align:center;font-size:27px;width:100%}.truth th{font-size:20px;color:#85dbe7}.truth td,.truth th{border-bottom:1px solid #426371;padding:10px}.truth-on{background:#453974}.operator-family{display:grid;grid-template-columns:repeat(8,1fr);gap:14px}.operator{padding:10px 2px;background:#10222d;border-top:2px solid #59d1df}.operator .tag{text-align:center;font-size:17px}.mini .matrix td{font-size:23px;width:48px;min-width:36px;height:43px;padding:2px}.four-basis{display:grid;grid-template-columns:1fr 1fr;gap:18px}.four-basis .matrix td{height:59px}.sum{display:grid;grid-template-columns:1fr 40px 1fr 40px 1fr;gap:6px;align-items:center}.sum .panel{padding:16px 8px}.sum .matrix td{width:100px;min-width:50px}.inline-math{display:flex;gap:22px;justify-content:center;align-items:center}.stack{display:flex;flex-direction:column;gap:18px}.comparison{border-collapse:collapse;text-align:center;width:100%;font-size:28px}.comparison td,.comparison th{padding:18px 10px;border-bottom:1px solid #638291}.comparison th{font-size:20px;color:#8cdeeb}.comparison tr:nth-child(3){background:#203d4d}
.takeaway{position:absolute;bottom:99px;left:36px;right:36px;border-left:4px solid #b9a0fa;background:#1d263c;padding:11px 18px;font-size:23px;line-height:1.15;min-height:49px}.footer{position:absolute;bottom:16px;left:36px;right:36px;font-size:14px;color:#b4cbd6;display:flex;justify-content:space-between}.caption-zone{position:absolute;bottom:40px;left:150px;right:150px;height:51px}.door-art{height:205px;display:flex;align-items:center;justify-content:center}.door-leaf{width:130px;height:194px;border:4px solid #71d5db;background:#183c49;position:relative;text-align:center;padding-top:18px;box-shadow:18px 10px 0 #071116}.door-leaf span{display:block;font-size:16px}.door-leaf b{font-size:72px;color:#97f0c8}.door-leaf i{position:absolute;right:11px;top:110px;width:10px;height:10px;background:#f2db98;border-radius:50%}
'''

def page(lesson, scene, index, sans, mono):
    import re
    fonts=f"@font-face{{font-family:CMsans;src:url(data:font/ttf;base64,{sans})}}@font-face{{font-family:CMmono;src:url(data:font/ttf;base64,{mono})}}"
    n=lesson['id'][:2]; count=len(lesson['scenes']); badge='YOUR TURN · PAUSE TO THINK' if scene.get('question') else 'WORKED TUTORIAL'
    note=re.sub(r'M_([A-Z]+)',r'M<sub>\1</sub>',escape(scene['note']))
    return '<!doctype html><html><meta charset="utf-8"><style>'+fonts+CSS+'</style><body><div class="stage"><header><span>CM FOUNDATIONS · LESSON '+n+'</span><span>'+badge+'</span></header><h1>'+escape(scene['title'])+'</h1><main class="content">'+body(scene)+'</main><div class="takeaway">'+note+'</div><div class="caption-zone"></div><div class="footer"><span>'+escape(lesson['title'])+'</span><span>'+f'{index+1:02d} / {count:02d}'+'</span></div></div><script>window.__seek = function(p) {};</script></body></html>'
