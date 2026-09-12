"""Bounded exact projected counts by conditioning and residual components.

Selected decisions form disjoint counted branches. Hidden-only decisions use
existential OR, so multiple hidden witnesses never multiply a projected count.
Every request starts with a fresh cache; this is an opt-in research candidate.
"""
from collections import Counter
import re

from cmbench.backends.bucket_counts import CountPlanLimit


def count_components(case, fixed=None, *, max_vars=16384, max_clauses=65536,
                     max_literals=1048576, max_nodes=100000, max_work=20000000,
                     max_depth=200, max_cache_entries=5000,
                     max_cache_literals=1000000):
    limits=(max_vars,max_clauses,max_literals,max_nodes,max_work,max_depth,
            max_cache_entries,max_cache_literals)
    if any(type(v) is not int or v<0 for v in limits):raise ValueError('invalid resource limit')
    if max_depth>200:raise ValueError('depth limit exceeds supported recursion bound')
    n=case['n']
    if type(n) is not int or n<0:raise ValueError('invalid variable count')
    if n>max_vars:raise CountPlanLimit('component basis exceeds limit')
    projection=tuple(case['projected'])
    if len(set(projection))!=len(projection) or any(type(v) is not int or not 0<=v<n for v in projection):
        raise ValueError('invalid projection')
    selected=frozenset(v+1 for v in projection)
    rows=set();literal_count=0
    for index,clause in enumerate(case['clauses']):
        if index>=max_clauses:raise CountPlanLimit('component clauses exceed limit')
        unique=set()
        for literal in clause:
            literal_count+=1
            if literal_count>max_literals:raise CountPlanLimit('component literals exceed limit')
            if type(literal) is not int or not 1<=abs(literal)<=n:raise ValueError('invalid literal')
            unique.add(literal)
        if not any(-v in unique for v in unique):rows.add(tuple(sorted(unique)))
    for name,value in (fixed or {}).items():
        if not isinstance(name,str) or not re.fullmatch(r'x[0-9]+',name) or type(value) not in (int,bool) or value not in (0,1):
            raise ValueError('invalid fixed assignment')
        var=int(name[1:])+1
        if not 1<=var<=n:raise ValueError('fixed variable outside basis')
        rows.add((var if value else -var,))
    stats=dict(nodes=0,work=0,cache_hits=0,cache_entries=0,cache_literals=0,
               component_splits=0,selected_branches=0,hidden_branches=0,
               maximum_depth=0,input_literals=literal_count)
    cache={}

    def charge(amount):
        stats['work']+=amount
        if stats['work']>max_work:raise CountPlanLimit('component work exceeds limit')

    def condition(clauses,units):
        reduced=set()
        for clause in clauses:
            charge(len(clause))
            if any(v in units for v in clause):continue
            rest=tuple(v for v in clause if -v not in units)
            if not rest:return ((),)
            reduced.add(rest)
        return tuple(sorted(reduced))

    def solve(clauses,counted,depth):
        stats['nodes']+=1;stats['maximum_depth']=max(stats['maximum_depth'],depth)
        if stats['nodes']>max_nodes:raise CountPlanLimit('component node count exceeds limit')
        if depth>max_depth:raise CountPlanLimit('component recursion depth exceeds limit')
        charge(1)
        while True:
            if clauses and not clauses[0]:return 0
            charge(len(clauses))
            units={c[0] for c in clauses if len(c)==1}
            if not units:break
            if any(-v in units for v in units):return 0
            counted=counted-{abs(v) for v in units}
            clauses=condition(clauses,units)
        used={abs(v) for c in clauses for v in c}
        charge(sum(map(len,clauses)))
        free=len(counted-used);counted=counted&used;factor=1<<free
        if not clauses:return factor
        key=(clauses,tuple(sorted(counted)))
        if key in cache:
            stats['cache_hits']+=1;return factor*cache[key]

        # Components contain every residual variable, including shared hidden
        # axes. Splitting only on counted axes would incorrectly factor witnesses.
        parent={v:v for v in used}
        def find(v):
            while parent[v]!=v:
                parent[v]=parent[parent[v]];v=parent[v]
            return v
        for clause in clauses:
            charge(len(clause))
            root=find(abs(clause[0]))
            for literal in clause[1:]:parent[find(abs(literal))]=root
        groups={};variables={}
        for clause in clauses:
            root=find(abs(clause[0]))
            groups.setdefault(root,[]).append(clause)
            variables.setdefault(root,set()).update(map(abs,clause))
        if len(groups)>1:
            stats['component_splits']+=1;answer=1
            for root in sorted(groups):
                answer*=solve(tuple(groups[root]),counted&variables[root],depth+1)
                if not answer:break
        else:
            scores=Counter(abs(v) for c in clauses for v in c if not counted or abs(v) in counted)
            charge(sum(map(len,clauses)))
            var=min(scores,key=lambda v:(-scores[v],v))
            if counted:
                stats['selected_branches']+=1
                remaining=counted-{var}
                answer=solve(condition(clauses,{var}),remaining,depth+1)
                answer+=solve(condition(clauses,{-var}),remaining,depth+1)
            else:
                stats['hidden_branches']+=1
                answer=int(bool(solve(condition(clauses,{var}),counted,depth+1)) or
                           bool(solve(condition(clauses,{-var}),counted,depth+1)))
        cost=len(counted)+sum(len(c)+1 for c in clauses)
        if len(cache)<max_cache_entries and stats['cache_literals']+cost<=max_cache_literals:
            cache[key]=answer;stats['cache_literals']+=cost
        return factor*answer

    value=solve(tuple(sorted(rows)),selected,0)
    stats['cache_entries']=len(cache)
    return value,stats
