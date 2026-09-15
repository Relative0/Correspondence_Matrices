"""Bracketed operators, centered Impax, and complete Boolean contractions."""
import re
from html import escape
import cm_tutorial_visuals_v1 as old
from cm_tutorial_visuals_v1 import matrix, eq, panel, split, small, trace, stack, mname

SYMBOLS=['impax','0','⇔','⇕','∧','¬∨','⇑','⇓','⇒','⇐','∨','¬∧','R','¬R','L','¬L']
NAMES=['Impax','false','equivalence','exclusive-or','AND','NOR','X∧¬Y','¬X∧Y','X⇒Y','Y⇒X','OR','NAND','right: Y','not Y','left: X','not X']

def impax():
    return '<svg class="impax" viewBox="0 0 100 100" role="img" aria-label="Impax: centered overlay of equivalence and exclusive-or"><text class="impax-h">⇔</text><text class="impax-v">⇕</text></svg>'
def op(s): return '['+(impax() if s=='impax' else s)+']'
def named(s,rows,**kw): return eq(op(s)+' =')+matrix(rows,**kw)
def row(v):return matrix([v],size='calc-vector')
def col(v):return matrix([[x] for x in v],size='calc-vector')
def chain(*parts):return '<div class="calc-chain">'+''.join(parts)+'</div>'
def cm(s,rows,**kw):return '<div class="calc-cm">'+small(op(s)+' =')+matrix(rows,size='calc-matrix',**kw)+'</div>'
def calc(t):return '<div class="calculation">'+t+'</div>'

def numeric(s):
    p=s['step'];xor=[[0,1],[1,0]];main=eq('⟨0|[⇕]|1⟩')
    arrays=chain(row([0,1]),eq('·'),cm('⇕',xor,markcol=0 if p==3 else 1 if p==4 else None),eq('·'),col([1,0]))
    if p==0:return split(panel('LOGICAL MEASUREMENT',main+small('row vector · operator CM · column vector')),panel('DEFINED OPERATOR',named('⇕',xor)))
    if p==1:return main+arrays+small('⟨0|: 1×2 &nbsp;&nbsp; [⇕]: 2×2 &nbsp;&nbsp; |1⟩: 2×1 &nbsp;&nbsp; result: 1×1')
    if p==2:return split(panel('BOOLEAN MATRIX ARITHMETIC',trace(['Pair entries with AND (∧)','Combine products with exclusive-or (⇕)','1 ⇕ 1 = 0, whereas 1 ∨ 1 = 1'])),panel('NUMERIC CM',named('⇕',xor)))
    if p in (3,4):
        formula='(0∧0) ⇕ (1∧1) = 0 ⇕ 1 = 1' if p==3 else '(0∧1) ⇕ (1∧0) = 0 ⇕ 0 = 0'
        return main+arrays+calc(formula)+small('Intermediate row: [1, ?]' if p==3 else 'Intermediate row: [1, 0]')
    if p in (5,6):
        return main+chain(eq('='),row([1,0]),eq('·'),col([1,0]))+calc('= (1∧1) ⇕ (0∧0) = 1 ⇕ 0 = 1' if p==6 else '⟨0|[⇕] = [1,0] &nbsp; · &nbsp; the remaining column is |1⟩')
    if p==7:
        return chain(cm('⇕',xor),eq('·'),col([1,0]),eq('='),col([0,1]))+calc('top: (0∧1) ⇕ (1∧0) = 0<br>bottom: (1∧1) ⇕ (0∧0) = 1')
    if p==8:return eq('⟨0|([⇕]|1⟩)')+chain(eq('='),row([0,1]),eq('·'),col([0,1]))+calc('= (0∧0) ⇕ (1∧1) = 0 ⇕ 1 = 1')
    if p in (9,10):
        return eq('⟨0|[⇕]|0⟩')+chain(eq('='),row([1,0]),eq('·'),col([0,1]))+calc('= ?' if p==9 else '= (1∧0) ⇕ (0∧1) = 0 ⇕ 0 = 0')
    return split(panel('NUMERIC INPUTS',eq('⟨0|[⇕]|1⟩ = 1')+named('⇕',xor)),panel('NEXT: SYMBOLIC INPUTS',eq('⟨X|[⇒]|Y⟩ = X ⇒ Y')+named('⇒',[[1,0],[1,1]])))

def symbolic(s):
    p=s['step'];imp=[[1,0],[1,1]]
    if p<=1:return eq('⟨X|[⇒]|Y⟩')+chain(eq('='),row(['X','¬X']),eq('·'),cm('⇒',imp),eq('·'),col(['Y','¬Y']))+small('X⇒Y: if X is true, Y must be true. Only X=1, Y=0 fails.' if p==0 else 'The state vectors are symbolic; the CM stays numeric.')
    if p in (2,3):
        return chain(row(['X','¬X']),eq('·'),cm('⇒',imp,markcol=p-2))+calc('(X∧1) ⇕ (¬X∧1) = X ⇕ ¬X = 1' if p==2 else '(X∧0) ⇕ (¬X∧1) = 0 ⇕ ¬X = ¬X')+small('First output entry' if p==2 else 'Second output entry')
    if p==4:return eq('⟨X|[⇒]|Y⟩')+calc('= [X ⇕ ¬X, ¬X] [Y, ¬Y]ᵀ')+chain(eq('='),row([1,'¬X']),eq('·'),col(['Y','¬Y']))
    if p==5:return eq('⟨X|[⇒]|Y⟩')+chain(eq('='),row([1,'¬X']),eq('·'),col(['Y','¬Y']))+calc('= (1∧Y) ⇕ (¬X∧¬Y)<br>= Y ⇕ (¬X∧¬Y)')
    if p==6:return eq('Y ⇕ (¬X∧¬Y) = Y ∨ (¬X∧¬Y)')+'<table class="comparison"><tr><th>Case</th><th>First term: Y</th><th>Second term: ¬X∧¬Y</th></tr><tr><td>Y=1</td><td>1</td><td>0</td></tr><tr><td>Y=0</td><td>0</td><td>¬X</td></tr></table>'+small('The terms cannot both be 1. This is why XOR equals OR here.')
    if p==7:return calc('Y ∨ (¬X∧¬Y)<br>= (Y∨¬X) ∧ (Y∨¬Y)<br>= (Y∨¬X) ∧ 1<br>= ¬X∨Y = X⇒Y')
    if p==8:return split(panel('PAPER, PRINTED PAGE 7',named('⇒',imp)+small('⟨X| = [X,¬X]<br>|Y⟩ = [Y,¬Y]ᵀ')),panel('THE COMPLETE DERIVATION',calc('⟨X|[⇒]|Y⟩<br>= [X⇕¬X, ¬X] [Y,¬Y]ᵀ<br>= Y ⇕ (¬X∧¬Y)<br>= ¬X∨Y<br>= X⇒Y')))
    if p in (9,10):return split(panel('CHECK X=1, Y=0',eq('¬X∨Y = '+('?' if p==9 else '¬1∨0 = 0'))+small('⟨1|[⇒]|0⟩ = '+('?' if p==9 else '0'))),panel('IMPLICATION CM',named('⇒',imp,rlabels=['X=1','X=0'],clabels=['Y=1','Y=0'],select=[0,1] if p==10 else None)))
    return split(panel('THIS LESSON: NUMERIC CM',named('⇒',imp)),panel('NEXT: EXPRESSIONS IN LM CELLS',eq(mname('XY')+' =')+matrix([['X∧Y','X∧¬Y'],['¬X∧Y','¬X∧¬Y']],size='expressions')))

def body(s):
    v=s['visual'];p=s.get('step',0)
    if v=='operator_definition':
        return split(panel('OPERATOR NOTATION',eq('[θ] = '+op('∧' if p==0 else '⇕'))+small('θ is a placeholder for a chosen operator.')),panel('THE SAME CM, NUMERICALLY',named('∧' if p==0 else '⇕',[[1,0],[0,0]] if p==0 else [[0,1],[1,0]],rlabels=['X=1','X=0'],clabels=['Y=1','Y=0'])))
    if v=='impax':return split(panel('IMPAX · CENTERED SYMBOL OVERLAY',eq(op('impax'))+small('⇔ and ⇕ share their horizontal<br>and vertical center.')),panel('TAUTOLOGY: ALL FOUR INPUTS ACCEPTED',named('impax',[[1,1],[1,1]],rlabels=['X=1','X=0'],clabels=['Y=1','Y=0'])))
    if v=='sixteen':return small('All CMs: row X=1,0 · column Y=1,0. Symbols identify the complete matrices.')+'<div class="operator-family">'+''.join('<div class="operator">'+eq(op(sym))+small(name)+matrix(old.values(pat),size='mini')+'</div>' for sym,name,(_,pat) in zip(SYMBOLS,NAMES,old.OPS))+'</div>'
    if v=='basis_practice':return split(panel('OUTER PRODUCT',eq('|0⟩⟨1| =')+chain(col([0,1]),eq('·'),row([1,0]))),panel('YOUR MATRIX' if p==0 else 'LOWER-LEFT BASIS CM',matrix([['?','?'],['?','?']]) if p==0 else named('⇓',[[0,0],[1,0]])))
    if v=='measurement_intro':return split(panel('BUILD A CM',eq('|0⟩⟨1| = [⇓]')+named('⇓',[[0,0],[1,0]])),panel('USE A CM',eq('⟨0|[⇕]|1⟩')+named('⇕',[[0,1],[1,0]])))
    if v=='numeric_measurement':return numeric(s)
    if v=='symbolic_measurement':return symbolic(s)
    if v=='basis':
        if p==1:return '<div class="four-basis">'+''.join(panel(f'|{r}⟩⟨{c}| = '+op(symbol),matrix([[int(rr==r and cc==c) for cc in (1,0)] for rr in (1,0)])) for (r,c),symbol in zip(old.PAIRS,['∧','⇑','⇓','¬∨']))+'</div>'
        if p==2:return '<div class="sum">'+panel('|1⟩⟨0| = [⇑]',matrix([[0,1],[0,0]]))+eq('⇕')+panel('|0⟩⟨1| = [⇓]',matrix([[0,0],[1,0]]))+eq('=')+panel('[⇕]',matrix([[0,1],[1,0]]))+'</div>'
    result=old.body(s)
    if v=='truth':
        sym={'and':'∧','or':'∨','xor':'⇕'}[s['rule']]
        if s.get('question'):result=result.replace('IDENTIFY THIS RULE','[θ] = · IDENTIFY THIS RULE')
        else:result=result.replace({'and':'X ∧ Y','or':'X ∨ Y','xor':'X ⇕ Y'}[s['rule']]+'</div>',op(sym)+' =</div>')
    if v=='orders':result=result.replace('PAPER · TRUE FIRST','[∧] = · PAPER · TRUE FIRST').replace('WEBSITE EXAMPLE · FALSE FIRST','[∧] = · WEBSITE · FALSE FIRST')
    if v=='outer':result=result.replace('FOUR MULTIPLICATIONS','[⇑] = · FOUR MULTIPLICATIONS').replace('|1⟩⟨0|</div>','|1⟩⟨0| = [⇑]</div>')
    if v=='basis':result=result.replace('X ⇕ Y</div>','[⇕] =</div>')
    if v=='lm' and p==5:result=result.replace('EVALUATE THE SAME ASSIGNMENT','RESULT: [∧] =')
    if v=='equivalence_lm':
        result=result.replace('X↔Y','X⇔Y')
        if p==2:result=result.replace('X = Y = 1</div>','X = Y = 1 · RESULT: [⇔] =</div>')
    if v=='compound':
        result=result.replace('IMPLICATION</div>','[⇒] =</div>').replace('A: W ⇕ X','A = [⇕] · W ⇕ X').replace('B: ¬Y ∧ Z','B = [⇓] · ¬Y ∧ Z')
    return result

CSS=old.CSS+'''
.calc-chain{display:flex;justify-content:center;align-items:center;gap:19px;min-width:0}.calc-cm{display:flex;flex-direction:column;gap:5px}.calc-matrix .matrix td{font-size:33px;width:92px;height:65px;min-width:60px}.calc-vector .matrix td{font-size:33px;width:85px;height:65px;min-width:64px}.calc-vector .matrix,.calc-matrix .matrix{border-left:3px solid #dfedf2;border-right:3px solid #dfedf2}.calculation{font-size:29px;line-height:1.5;text-align:center;background:#152e3d;padding:13px 17px;border-left:3px solid #bfa6fa}.panel .calculation{font-size:23px;line-height:1.7;padding:9px 7px}.impax{width:1.16em;height:1.16em;display:inline-block;vertical-align:-.22em;overflow:visible}.impax text{font-family:CMsans;font-size:75px;fill:currentColor}.operator-family .equation{font-size:27px;height:40px}.operator-family .small{font-size:13px;white-space:nowrap}.operator-family{gap:12px}.operator{padding-top:5px}.operator-family .mini td{height:39px}.operator-family .matrix{border-spacing:3px}.content{gap:10px}
'''
CENTER_SCRIPT="""window.__seek=function(){document.querySelectorAll('.impax text').forEach(t=>{t.removeAttribute('transform');let b=t.getBBox();t.setAttribute('transform',`translate(${50-b.x-b.width/2},${50-b.y-b.height/2})`);});};"""
def page(l,s,i,sans,mono):
    fonts=f'@font-face{{font-family:CMsans;src:url(data:font/ttf;base64,{sans})}}@font-face{{font-family:CMmono;src:url(data:font/ttf;base64,{mono})}}'
    note=re.sub(r'M_([A-Z]+)',r'M<sub>\1</sub>',escape(s['note']))
    badge='YOUR TURN · PAUSE TO THINK' if s.get('question') else 'WORKED TUTORIAL'
    visual=body(s)
    if s['visual']=='numeric_measurement' and s['step'] in (5,6,8,9,10):
        visual='<div class="reference">'+panel('REFERENCE CM',named('⇕',[[0,1],[1,0]],size='mini'))+'<div class="working">'+visual+'</div></div>'
    if s['visual']=='symbolic_measurement' and s['step'] in (4,5,6,7):
        visual='<div class="reference">'+panel('REFERENCE CM',named('⇒',[[1,0],[1,1]],size='mini'))+'<div class="working">'+visual+'</div></div>'
    extra='.reference{display:grid;grid-template-columns:225px 1fr;gap:18px;align-items:center}.reference .panel{padding:15px 10px}.reference .working{display:flex;flex-direction:column;gap:16px}.reference .calculation{font-size:24px}.reference .comparison td{font-size:22px;padding:14px 8px}.reference .comparison th{font-size:18px}.reference .equation{font-size:28px}'
    return '<!doctype html><html><meta charset="utf-8"><style>'+fonts+CSS+extra+'</style><body><div class="stage"><header><span>CM FOUNDATIONS · LESSON '+l['id'][:2]+'</span><span>'+badge+'</span></header><h1>'+escape(s['title'])+'</h1><main class="content">'+visual+'</main><div class="takeaway">'+note+'</div><div class="caption-zone"></div><div class="footer"><span>'+escape(l['title'])+'</span><span>'+f'{i+1:02d} / {len(l["scenes"]):02d}'+'</span></div></div><script>'+CENTER_SCRIPT+'</script></body></html>'
