"""Bounded SXFM Boolean semantics and explicit existential auxiliary removal."""
from itertools import combinations, product
from math import comb
import re

from cmbench.comparative.feature_mapping import xml_features


def sxfm_formula(payload, mapping):
    root,kind,_=xml_features(payload)
    if kind!='SXFM':raise ValueError('SXFM original required')
    if len(root.findall('feature_tree'))!=1 or len(root.findall('constraints'))>1:
        raise ValueError('duplicate SXFM semantic section')
    if any(c.tag not in ('meta','feature_tree','constraints') for c in root):
        raise ValueError('unsupported SXFM section')
    ids={f['id']:f['variable'] for f in mapping['features']}
    stack=[];entries=[]
    for line in root.findtext('feature_tree').splitlines():
        if not line.strip():continue
        prefix=re.match(r'^(\t*):',line)
        if prefix is None:raise ValueError('SXFM indentation must use tabs')
        depth=len(prefix[1])
        if depth>len(stack):raise ValueError('skipped SXFM indentation level')
        stack=stack[:depth]
        parent=stack[-1] if stack else None
        declaration=line[len(prefix[1])+1:]
        group=re.fullmatch(r'g\s+(?:\([^()]+\)\s*)?\[([0-9]+),([0-9]+|\*)\]\s*',declaration)
        if group:
            if parent is None or parent['kind']=='group':raise ValueError('invalid group parent')
            entry=dict(kind='group',lower=int(group[1]),upper=group[2],parent=parent,children=[])
        else:
            feature=re.fullmatch(r'([rmo]?)\s*(.*?)\s*\(([^()]+)\)\s*',declaration)
            if not feature or feature[3] not in ids:raise ValueError('invalid SXFM feature')
            marker=feature[1]
            if parent is None and (entries or marker!='r'):raise ValueError('single marked root required')
            if parent is not None and marker=='r':raise ValueError('nested SXFM root')
            if parent is not None and parent['kind']!='group' and marker not in ('m','o'):
                raise ValueError('ungrouped feature needs optional/mandatory marker')
            entry=dict(kind='feature',variable=ids[feature[3]],marker=marker,parent=parent,children=[])
        if parent:parent['children'].append(entry)
        entries.append(entry);stack.append(entry)
    if not entries:raise ValueError('empty SXFM model')
    formulas=[entries[0]['variable']]
    for entry in entries:
        if entry['kind']=='feature':
            parent=entry['parent']
            if parent is None:continue
            grouped=parent['kind']=='group'
            feature_parent=parent['parent'] if grouped else parent
            value=entry['variable'];p=feature_parent['variable']
            formulas.append(('or',-value,p))
            if not grouped and entry['marker']=='m':formulas.append(('or',-p,value))
        else:
            values=[c['variable'] for c in entry['children']]
            n=len(values);lower=entry['lower'];upper=n if entry['upper']=='*' else int(entry['upper'])
            if not 0<=lower<=upper<=n:raise ValueError('invalid SXFM group cardinality')
            work=(comb(n,n-lower+1) if lower else 0)+(comb(n,upper+1) if upper<n else 0)
            if work>262144:raise ValueError('group cardinality expansion limit')
            p=entry['parent']['variable']
            if lower:formulas.extend(('or',-p,*subset) for subset in combinations(values,n-lower+1))
            if upper<n:formulas.extend(('or',*(-v for v in subset)) for subset in combinations(values,upper+1))
    labels=set()
    for line in (root.findtext('constraints') or '').splitlines():
        if not line.strip():continue
        if ':' not in line:raise ValueError('unlabeled SXFM constraint')
        label,expression=line.split(':',1)
        if not label.strip() or label in labels:raise ValueError('duplicate constraint label')
        labels.add(label);literals=[]
        for token in re.split(r'\s+or\s+',expression.strip()):
            match=re.fullmatch(r'(~?)([^\s~()]+)',token)
            if not match or match[2] not in ids:raise ValueError('unsupported SXFM cross constraint')
            literals.append(-ids[match[2]] if match[1] else ids[match[2]])
        formulas.append(('or',*literals))
    return ('and',*formulas)


def projected_equivalence_miter(payload,mapping,*,max_auxiliaries=6):
    """Compare original feature assignments with existentially projected CNF.

    Every assignment of unmatched variables is explicitly quantified. Their
    names never serve as an auxiliary classification rule.
    """
    hidden=mapping['unmatched_variables']
    if len(hidden)>max_auxiliaries:raise ValueError('auxiliary expansion limit')
    original=sxfm_formula(payload,mapping)
    alternatives=[]
    for bits in product((False,True),repeat=len(hidden)):
        fixed=dict(zip(hidden,bits));terms=[]
        for clause in mapping['clauses']:
            if any(abs(v) in fixed and fixed[abs(v)]==(v>0) for v in clause):continue
            terms.append(('or',*(v for v in clause if abs(v) not in fixed)))
        alternatives.append(('and',*terms))
    projected=('or',*alternatives)
    next_id=mapping['declared_variables']+1;clauses=[];memo={}
    def encode(node):
        nonlocal next_id
        if type(node) is int:return node
        if node in memo:return memo[node]
        op,*children=node
        values=[encode(child) for child in children]
        result=next_id;next_id+=1;memo[node]=result
        if op=='and':
            clauses.extend([-result,v] for v in values);clauses.append([result,*(-v for v in values)])
        elif op=='or':
            clauses.extend([result,-v] for v in values);clauses.append([-result,*values])
        else:raise ValueError('unsupported formula operator')
        return result
    a=encode(original);b=encode(projected);clauses.extend([[a,b],[-a,-b]])
    return clauses,next_id-1
