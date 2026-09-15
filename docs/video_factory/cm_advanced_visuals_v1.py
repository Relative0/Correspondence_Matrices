"""Readable, narrated teaching states for the advanced companion course."""
import html,re
def esc(s):return html.escape(str(s))
def math(s):
    t=esc(s)
    t=re.sub(r'M_\{([^}]+)\}',r'M<sub>\1</sub>',t)
    return re.sub(r'M_([A-Za-z]+)',r'M<sub>\1</sub>',t)

def graph():
    # Dependency lines deliberately have no mathematical implication meaning.
    return '''<svg class="graph" viewBox="0 0 1040 255" role="img" aria-label="XOR root with AND and OR children and A, B, C, D leaves">
    <g stroke="#64818a" stroke-width="3"><path d="M520 45 L280 110 M520 45 L760 110 M280 140 L160 205 M280 140 L400 205 M760 140 L640 205 M760 140 L880 205"/></g>
    <g fill="#17333f" stroke="#65d7e5" stroke-width="2"><rect x="440" y="5" width="160" height="55" rx="12"/><rect x="200" y="90" width="160" height="55" rx="12"/><rect x="680" y="90" width="160" height="55" rx="12"/></g>
    <g fill="#d5f6ff" text-anchor="middle" font-family="sans-serif" font-size="28"><text x="520" y="42">XOR ⇕</text><text x="280" y="127">AND ∧</text><text x="760" y="127">OR ∨</text><text x="160" y="228">A</text><text x="400" y="228">B</text><text x="640" y="228">C</text><text x="880" y="228">D</text></g></svg>'''

def card(c):
    if c.get('graph'):return '<section class="card"><h3>'+esc(c['label'])+'</h3>'+graph()+'</section>'
    if 'values' not in c:
        return '<section class="card"><h3>'+esc(c['label'])+'</h3><div class="lines">'+''.join('<div class="line">'+math(x)+'</div>' for x in c['lines'])+'</div></section>'
    v=c['values']; n=len(v);mark=c.get('mark');rows=c['rows'];cols=c['cols']
    table='<table class="matrix '+('tensor' if n>=8 else 'large' if n>=4 else '')+'"><thead><tr><th></th>'+''.join('<th>'+math(x)+'</th>' for x in cols)+'</tr></thead><tbody>'
    for i,row in enumerate(v):
        table+='<tr><th>'+math(rows[i])+'</th>'
        for j,x in enumerate(row):
            cls=' selected' if mark==[i,j] else ''
            table+='<td class="'+cls+'">'+math(x)+'</td>'
        table+='</tr>'
    table+='</tbody></table>'
    return '<section class="card"><h3>'+math(c['name'])+'</h3>'+table+'</section>'

def page(lesson,s,i,sans,mono):
    eq=s['equations'];longest=max(map(len,eq),default=1)
    size=30 if longest<62 else 25 if longest<84 else 21
    body='<div class="equations" style="font-size:'+str(size)+'px">'+''.join('<div class="equation">'+math(x)+'</div>' for x in eq)+'</div>'
    cards=s['cards']
    if s.get('question') and lesson['id']=='23_application':
        # The policy exercise must not expose its selected answer during the pause.
        cards=[]
        for c in s['cards']:
            if c.get('mark'):
                c=dict(c,values=[row[:] for row in c['values']])
                ri,ci=c['mark'];c['values'][ri][ci]='?'
            cards.append(c)
    body+='<div class="cards count-'+str(len(cards))+'">'+''.join(card(c) for c in cards)+'</div>'
    return '''<!doctype html><html><head><meta charset="utf-8"><style>
    @font-face{font-family:Course;src:url(data:font/ttf;base64,'''+sans+''')}
    @font-face{font-family:CourseMono;src:url(data:font/ttf;base64,'''+mono+''')}
    *{box-sizing:border-box}html,body{width:1280px;height:720px;margin:0;overflow:hidden}
    body{background:radial-gradient(ellipse at 85% 10%,#15333c 0,#09151d 52%,#080f14 100%);color:#edf7fb;font-family:Course,Arial,sans-serif}
    header{position:absolute;left:42px;right:42px;top:20px;height:78px;border-bottom:2px solid #3e6c78}
    .eyebrow{color:#78d8e4;letter-spacing:1px;font-size:15px;font-weight:bold}h1{font-size:31px;line-height:1.1;margin:8px 0 0;font-weight:600}
    .step{position:absolute;right:0;top:0;color:#b9cbd1;font-size:15px}
    main{position:absolute;left:42px;right:42px;top:113px;bottom:157px;display:flex;flex-direction:column;gap:17px}
    .equations{border-left:4px solid #b8a5ed;background:#14212e;padding:10px 17px;font-family:CourseMono,monospace;line-height:1.35;flex:none}
    .equation{white-space:nowrap}sub{font-size:.68em;vertical-align:sub}
    .cards{display:flex;gap:18px;flex:1;min-height:0;align-items:stretch}.card{flex:1;min-width:0;border-top:3px solid #68d4e1;background:#10212bdd;padding:12px 15px;overflow:visible}
    h3{font-size:21px;font-weight:600;color:#87ddeb;margin:0 0 10px;text-align:center;line-height:1.2}
    .lines{display:flex;flex-direction:column;gap:14px;padding:7px 3px}.line{font-size:24px;line-height:1.25}
    .count-3 .line{font-size:22px}.matrix{border-collapse:separate;border-spacing:5px;width:100%;text-align:center;font-family:CourseMono,monospace;table-layout:fixed}
    .matrix th{font-size:16px;color:#9cbac5;font-weight:400;padding:3px 0}.matrix th:first-child{width:52px}
    .matrix td{font-size:32px;padding:14px 2px;background:#142f3a;border:1px solid #456671;height:60px;white-space:nowrap}
    .matrix td.selected{background:#42375d;border:2px solid #c2a8ff;color:#fff}
    .count-3 .matrix td{font-size:26px;padding:9px 1px}.matrix.large td{font-size:24px;height:39px;padding:5px 1px}.count-3 .matrix.large td{font-size:23px}
    .matrix.tensor{border-spacing:3px}.matrix.tensor th{font-size:13px}.matrix.tensor th:first-child{width:39px}.matrix.tensor td{font-size:14px;height:27px;padding:3px 0}
    .graph{width:100%;max-height:270px}.takeaway{position:absolute;left:42px;right:42px;top:580px;height:49px;border:2px solid #b9a2eb;background:#182333;padding:10px 15px;font-size:22px;line-height:1.1}
    .source{position:absolute;left:43px;top:642px;font-size:13px;color:#7f9ca9;max-width:1185px}
    .progress{position:absolute;bottom:0;height:4px;background:#69dae4}
    </style></head><body><header><div class="eyebrow">CM ADVANCED · LESSON '''+lesson['id'][:2]+'''</div><div class="step">'''+str(i+1)+' / '+str(len(lesson['scenes']))+(' · YOUR TURN' if s.get('question') else '')+'''</div><h1>'''+esc(s['title'])+'''</h1></header><main>'''+body+'''</main><div class="takeaway">'''+math(s['note'])+'''</div><div class="source">'''+esc(lesson['source'])+'''</div><div class="progress" style="width:'''+str(100*(i+1)/len(lesson['scenes']))+'''%"></div><script>window.__seek=function(t){};</script></body></html>'''
