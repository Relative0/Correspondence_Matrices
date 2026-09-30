"""Frozen pilot runner. Non-oracle workers never receive semantic partitions."""
from pathlib import Path
import argparse, hashlib, itertools, json, math, os, random, statistics, subprocess, sys, time, traceback

ROOT=Path(__file__).resolve().parents[1]
METHODS=['B0','B1','B2','B3','M1','M2','M3','M4','M5','O']
SEEDS=[3101,3102,3103]

def canon(p): return sorted([sorted(b) for b in p],key=lambda b:b[0])
def leaves(t): return [t] if isinstance(t,int) else leaves(t[0])+leaves(t[1])
def freeze(t): return t if isinstance(t,int) else tuple(map(freeze,t))
def balanced(v):
    if len(v)==1:return v[0]
    m=len(v)//2; return (balanced(v[:m]),balanced(v[m:]))
def random_tree(v,rng):
    if len(v)==1:return v[0]
    v=v[:];rng.shuffle(v);k=rng.randrange(1,len(v))
    return random_tree(v[:k],rng),random_tree(v[k:],rng)
def neighbors(t):
    if isinstance(t,int): return []
    a,b=t;out=[(b,a)]
    if not isinstance(a,int):out.append((a[0],(a[1],b)))
    if not isinstance(b,int):out.append(((a,b[0]),b[1]))
    out.extend((u,b) for u in neighbors(a));out.extend((a,u) for u in neighbors(b))
    return sorted(set(out),key=repr)

def syntax_tree(n,clauses):
    graph={v:set() for v in range(1,n+1)}
    for c in clauses:
        vs=set(map(abs,c))
        for a in vs:graph[a].update(vs-{a})
    unseen=set(graph); comps=[]
    while unseen:
        todo=[min(unseen)];c=set()
        while todo:
            v=todo.pop()
            if v in c:continue
            c.add(v);todo.extend(graph[v]-c)
        unseen-=c;comps.append(c)
    trees=[]
    for c in comps:
        g={v:graph[v]&c for v in c};order=[]
        while g:
            def cost(v):
                ns=g[v];missing=sum(b not in g[a] for a,b in itertools.combinations(ns,2))
                return missing,len(ns),v
            v=min(g,key=cost);ns=g[v]
            for a in ns:g[a].update(ns-{a});g[a].discard(v)
            del g[v];order.append(v)
        trees.append(balanced(order))
    return balanced(trees) if len(trees)>1 else trees[0]

def span_penalty(tree,sets,n):
    if not sets:return 0.0
    clusters=[]
    def visit(t):
        s=set(leaves(t));clusters.append(s)
        if not isinstance(t,int):visit(t[0]);visit(t[1])
    visit(tree)
    return statistics.mean((min(len(c) for c in clusters if set(b)<=c)-len(set(b)))/n for b in sets)

def volume(part):return sum(len(b) for b in part if len(b)>1)
def cut_volume(part):return sum((1<<(len(b)-1))-1 for b in part if len(b)>1)

def objective(method, compiled, carrier, hyperedges, n):
    p=compiled['direct_partition'];t=compiled['tree']
    if method=='M1':return (-len(p),repr(t))
    score=math.log2(1+compiled['sdd_size'])+math.log2(1+cut_volume(p))
    if method in ('M3','M5'):score+=span_penalty(t,carrier,n)
    if method in ('M4','M5'):score+=span_penalty(t,hyperedges,n)
    return (score,repr(t))

def exact_baseline(n,clauses):
    models=[x for x in range(1<<n) if all(any(bool(x&(1<<(abs(l)-1)))==(l>0) for l in c) for c in clauses)]
    if not models:return None
    def rec(vs,rel):
        if len(vs)==1:return [vs]
        first=vs[0]
        for mask in range(1<<(len(vs)-1)):
            a=[first]+[v for j,v in enumerate(vs[1:]) if mask&(1<<j)]
            if len(a)==len(vs):continue
            b=[v for v in vs if v not in a]
            ma=sum(1<<(v-1) for v in a);mb=sum(1<<(v-1) for v in b)
            ra={x&ma for x in rel};rb={x&mb for x in rel}
            if len(ra)*len(rb)==len(rel):return rec(a,ra)+rec(b,rb)
        return [vs]
    return canon(rec(list(range(1,n+1)),set(models)))

def lcc(n,*partitions):
    parent=list(range(n+1))
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for p in partitions:
        for b in p:
            for v in b:parent[find(v)]=find(b[0])
    out={}
    for v in range(1,n+1):out.setdefault(find(v),[]).append(v)
    return canon(out.values())

def worker(payload):
    from hybrid_core import compile_extract,exact_refine,probe_defects
    import psutil
    r=payload['instance'];method=payload['method'];seed=payload['seed'];n=r['n'];clauses=r['clauses'];carrier=r['carrier']
    trace=[];hyperedges=[];probe={};start=time.perf_counter()
    if method=='B1':tree=random_tree(list(range(1,n+1)),random.Random(seed+r['seed']))
    elif method in ['B3','M1','M2','M3','M4','M5']:tree=syntax_tree(n,clauses)
    elif method=='O':tree=balanced([balanced(b) for b in payload['oracle_partition']])
    else:tree=balanced(list(range(1,n+1)))
    if method in ('M4','M5'):
        fixed=balanced(list(range(1,n+1)));cuts=[leaves(fixed[0])]
        for child in fixed:
            if not isinstance(child,int):cuts.append(leaves(child[0]))
        probe=probe_defects(n,clauses,cuts[:3],shrink=True)
        for h in probe.get('witnesses',probe.get('hyperedges',[])):
            hyperedges.append(sorted(set(h['U'])|set(h['W'])))
    current=compile_extract(n,clauses,tree,minimize=method=='B2')
    compile_total=current['compile_seconds'];extract_total=current['extract_seconds']
    minimize_total=current.get('minimize_seconds',0)
    if method.startswith('M'):
        seen={repr(tree)};count=0
        for round_no in range(2):
            old=current;best=current
            # Half of total budget per round leaves room to search around accepted moves.
            candidates=[t for t in neighbors(freeze(current['tree'])) if repr(t) not in seen][:6]
            for t in candidates:
                seen.add(repr(t));cand=compile_extract(n,clauses,t)
                compile_total+=cand['compile_seconds'];extract_total+=cand['extract_seconds'];count+=1
                tr={'round':round_no,'tree':t,'parent_tree':old['tree'],
                    'sdd_size':cand['sdd_size'],'delta_size':cand['sdd_size']-old['sdd_size'],
                    'exposed_blocks':len(cand['direct_partition']),
                    'delta_exposure':len(cand['direct_partition'])-len(old['direct_partition']),
                    'residual_volume':volume(cand['direct_partition']),
                    'delta_residual_volume':volume(cand['direct_partition'])-volume(old['direct_partition']),
                    'direct_partition':cand['direct_partition'],'parent_partition':old['direct_partition'],
                    'compile_seconds':cand['compile_seconds'],'extract_seconds':cand['extract_seconds'],
                    'score':objective(method,cand,carrier,hyperedges,n)}
                trace.append(tr)
                if objective(method,cand,carrier,hyperedges,n)<objective(method,best,carrier,hyperedges,n):best=cand
            current=best
            if freeze(best['tree'])==freeze(old['tree']):break
    search_finished=time.perf_counter()
    exact=exact_refine(n,clauses,current['direct_partition'],carrier=carrier)
    total=time.perf_counter()-start
    mem=psutil.Process().memory_info()
    result={'status':'ok','method':method,'seed':seed,'id':r['id'],'family':r['family'],'split':r['split'],'n':n,
            'total_seconds':total,'search_stage_seconds':search_finished-start,
            'compile_seconds':compile_total,'extract_seconds':extract_total,'minimize_seconds':minimize_total,
            'sdd_size':current['sdd_size'],'sdd_count':current['sdd_count'],
            'tree':current['tree'],'direct_partition':current['direct_partition'],
            'direct_blocks':len(current['direct_partition']),
            'singleton_resolved_fraction':sum(len(b)==1 for b in current['direct_partition'])/n,
            'residual_volume':volume(current['direct_partition']),
            'residual_block_sizes':[len(b) for b in current['direct_partition'] if len(b)>1],
            'peak_memory_bytes':getattr(mem,'peak_wset',mem.rss),'memory_metric':'process_peak_wset' if hasattr(mem,'peak_wset') else 'endpoint_rss',
            'exact':exact,'probe':probe,'moves':trace}
    return result

def run_split(split,limit=None):
    if split=='heldout':
        selection=json.loads((ROOT/'data'/'baseline_selection.json').read_text())
        validation_bytes=(ROOT/'data'/'validation_results.jsonl').read_bytes()
        if selection['validation_sha256']!=hashlib.sha256(validation_bytes).hexdigest():
            raise SystemExit('Validation results changed after baseline selection')
    records=json.loads((ROOT/'data'/'benchmark_manifest.json').read_text())['records']
    selected=[r for r in records if r['split']==split]
    truth_path=ROOT/'data'/'independent_ground_truth.json'
    truths=json.loads(truth_path.read_text()) if truth_path.exists() else {}
    for r in selected:
        if r['id'] not in truths:
            part=exact_baseline(r['n'],r['clauses'])
            if part is None:raise ValueError('False benchmark outside frozen nonfalse contract')
            truths[r['id']]={'semantic':part,'simultaneous':lcc(r['n'],part,r['carrier'])}
    truth_path.write_text(json.dumps(truths,indent=2)+'\n')
    jobs=[(r,m,s) for r in selected for m in METHODS for s in SEEDS]
    random.Random(2026092906+['train','validation','heldout','external'].index(split)).shuffle(jobs)
    out=ROOT/'data'/f'{split}_results.jsonl'
    done=set()
    if out.exists():
        done={(x['id'],x['method'],x['seed']) for x in map(json.loads,out.read_text().splitlines())}
    freeze_paths=[ROOT/'BENCHMARK_PROTOCOL.md',ROOT/'PROTOCOL_CLARIFICATIONS.md',ROOT/'data'/'benchmark_manifest.json',
                  ROOT/'code'/'benchmark.py',ROOT/'code'/'hybrid_core.py',ROOT/'code'/'make_benchmarks.py']
    receipt={'split':split,'utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
             'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in freeze_paths}}
    receipt_path=ROOT/'data'/f'{split}_freeze.json'
    if receipt_path.exists():
        existing=json.loads(receipt_path.read_text())
        if existing['files']!=receipt['files']:
            raise SystemExit('Source/protocol changed: preserve old results under an invalidated run directory before retrying')
        receipt=existing
    elif done:raise SystemExit('Existing rows lack a provenance receipt')
    else:receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    fingerprint=hashlib.sha256(json.dumps(receipt['files'],sort_keys=True).encode()).hexdigest()
    completed=0
    for i,(r,m,s) in enumerate(jobs):
        if (r['id'],m,s) in done:continue
        payload={'instance':r,'method':m,'seed':s}
        if m=='O':payload['oracle_partition']=truths[r['id']]['semantic']
        t=time.perf_counter()
        try:
            p=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'worker'],input=json.dumps(payload),text=True,capture_output=True,timeout=15)
            if p.returncode:raise RuntimeError(p.stderr[-6000:])
            result=json.loads(p.stdout)
            result['correct']=canon(result['exact']['partition'])==truths[r['id']]['simultaneous']
            result['semantic_correct']=canon(result['exact']['semantic_partition'])==truths[r['id']]['semantic']
            result['direct_prime_blocks_evaluation']=sum(sorted(b) in truths[r['id']]['semantic'] for b in result['direct_partition'])
        except subprocess.TimeoutExpired:
            result={'id':r['id'],'family':r['family'],'n':r['n'],'split':split,'method':m,'seed':s,'status':'timeout','total_seconds':None,'correct':None}
        except Exception as e:
            result={'id':r['id'],'family':r['family'],'n':r['n'],'split':split,'method':m,'seed':s,'status':'error','error':str(e),'total_seconds':None,'correct':None}
        result['process_wall_seconds']=time.perf_counter()-t
        result['run_fingerprint']=fingerprint
        with out.open('a') as f:f.write(json.dumps(result,separators=(',',':'))+'\n')
        completed+=1
        if result['status']=='error' or result.get('correct') is False or result.get('semantic_correct') is False:
            print(json.dumps(result),flush=True);raise SystemExit('Correctness/tool failure: stop before more trials')
        if completed%30==0:print(f'{split}: {i+1}/{len(jobs)} status={result["status"]}',flush=True)
        if limit and completed>=limit:break

if __name__=='__main__':
    if sys.argv[1]=='worker':
        print(json.dumps(worker(json.load(sys.stdin)),separators=(',',':')))
    else:
        ap=argparse.ArgumentParser();ap.add_argument('split',choices=['train','validation','heldout','external']);ap.add_argument('--limit',type=int)
        a=ap.parse_args();run_split(a.split,a.limit)
