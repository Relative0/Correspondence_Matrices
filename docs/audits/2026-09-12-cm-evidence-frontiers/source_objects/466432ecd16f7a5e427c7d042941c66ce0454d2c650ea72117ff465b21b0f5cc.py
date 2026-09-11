"""Explicit feature identities and independently checkable Boolean XML semantics.

Names come from the original model and DIMACS comments. Prefixes and numeric
positions never decide which variables are features or encoding auxiliaries.
"""
from __future__ import annotations

import re
from itertools import product
import xml.etree.ElementTree as ET

from cmbench.backends.bucket_counts import parse_dimacs


def projection_dimacs(text: str, *, max_vars=16384, max_clauses=65536):
    """Read the author's c ind projection, including an explicit empty set."""
    n, clauses = parse_dimacs(text, max_vars=max_vars, max_clauses=max_clauses)
    selected=[]; found=False
    for line in text.splitlines():
        tokens=line.split()
        if tokens[:2] != ['c','ind']: continue
        found=True
        if len(tokens)<3 or tokens[-1]!='0': raise ValueError('unterminated projection declaration')
        for token in tokens[2:-1]:
            if not re.fullmatch(r'[1-9][0-9]*',token): raise ValueError('invalid projection variable')
            value=int(token)
            if not 1<=value<=n or value in selected: raise ValueError('duplicate or out-of-range projection variable')
            selected.append(value)
    if not found: raise ValueError('original projection declaration missing')
    return n,clauses,tuple(selected)


def named_dimacs(text: str):
    n,clauses=parse_dimacs(text,max_vars=16384,max_clauses=65536)
    names={}
    for line in text.splitlines():
        match=re.fullmatch(r'c\s+([1-9][0-9]*)\s+(.+)',line.strip())
        if match:
            index=int(match[1]); name=match[2].strip()
            if index in names or not 1<=index<=n or not name: raise ValueError('ambiguous DIMACS name')
            names[index]=name
    if set(names)!=set(range(1,n+1)) or len(set(names.values()))!=n:
        raise ValueError('incomplete or nonunique DIMACS name mapping')
    return n,clauses,names


def xml_features(payload: bytes):
    if len(payload)>2<<20 or b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():
        raise ValueError('unsupported XML size or entity declaration')
    root=ET.fromstring(payload)
    features=[]
    if root.tag=='feature_model':
        tree=root.findtext('feature_tree')
        if tree is None: raise ValueError('missing SXFM feature tree')
        for line in tree.splitlines():
            if not line.strip():continue
            if re.match(r'^\s*:g(?:\s|\()',line):continue
            match=re.fullmatch(r'\s*:(?:r|m|o)?\s*(.*?)\s*\(([^()]*)\)\s*',line)
            if not match or not match[1] or not match[2]:raise ValueError('unsupported SXFM feature declaration')
            features.append({'id':match[2],'name':match[1].strip(),'abstract':False})
        kind='SXFM'
    elif root.tag in ('featureModel','extendedFeatureModel'):
        structure=root.find('struct')
        if structure is None or len(structure)!=1:raise ValueError('invalid FeatureIDE root')
        for element in structure.iter():
            if element is structure:continue
            if element.tag not in ('and','or','alt','feature') or not element.get('name'):
                raise ValueError('unsupported non-Boolean structural element')
            if element.get('abstract','false') not in ('true','false'):raise ValueError('invalid abstract flag')
            features.append({'id':element.attrib['name'],'name':element.attrib['name'],'abstract':element.get('abstract')=='true'})
        kind='FeatureIDE'
    else:raise ValueError('unsupported original feature model format')
    if not features or len({f['id'] for f in features})!=len(features):raise ValueError('duplicate or empty original feature identities')
    return root,kind,features


def feature_mapping(payload: bytes, dimacs: str):
    root,kind,features=xml_features(payload)
    n,clauses,names=named_dimacs(dimacs)
    indices={v:k for k,v in names.items()}
    mappings=[]; used=set()
    for feature in features:
        matches={indices[v] for v in (feature['id'],feature['name']) if v in indices}
        if len(matches)!=1:raise ValueError('original feature does not have one explicit DIMACS match')
        index=matches.pop()
        if index in used:raise ValueError('multiple original features map to one DIMACS variable')
        used.add(index); mappings.append({**feature,'variable':index})
    return {'format':kind,'declared_variables':n,'clauses':clauses,'features':mappings,
            'unmatched_variables':sorted(set(names)-used),
            'feature_variables':sorted(used),
            'concrete_variables':sorted(f['variable'] for f in mappings if not f['abstract']),
            'original_semantics_verified':False}


def featureide_formula(payload: bytes, mapping):
    """Boolean feature configurations only; unsupported extensions fail closed."""
    root,kind,_=xml_features(payload)
    if kind!='FeatureIDE':raise ValueError('SXFM Boolean semantics not implemented')
    if root.tag != 'featureModel':raise ValueError('extended feature semantics not implemented')
    allowed = {'properties','struct','constraints','calculations','comments','featureOrder'}
    if any(child.tag not in allowed for child in root):raise ValueError('unsupported model section')
    if len(root.findall('struct')) != 1 or len(root.findall('constraints')) > 1:
        raise ValueError('duplicate semantic section')
    if any(set(e.attrib)-{'name','abstract','mandatory','hidden'} for e in root.find('struct').iter()):
        raise ValueError('unsupported structural attribute')
    names={f['name']:f['variable'] for f in mapping['features']}
    def boolean(element):
        tag=element.tag; children=[boolean(c) for c in element]
        if tag=='var' and not children and element.text in names:return names[element.text]
        if tag=='not' and len(children)==1:return ('not',*children)
        if tag in ('conj','disj') and children:return ('and' if tag=='conj' else 'or',*children)
        if tag in ('imp','eq') and len(children)==2:
            a,b=children
            return ('or',('not',a),b) if tag=='imp' else ('and',('or',('not',a),b),('or',('not',b),a))
        if tag=='atmost1' and children:
            return ('and',*(('or',('not',a),('not',b)) for i,a in enumerate(children) for b in children[i+1:]))
        raise ValueError('unsupported Boolean constraint operator: '+tag)
    formulas=[]
    def visit(element):
        parent=names[element.attrib['name']]
        children=list(element)
        if element.tag=='feature' and children:raise ValueError('leaf feature has children')
        for child in children:
            value=names[child.attrib['name']]
            formulas.append(('or',('not',value),parent))
            mandatory=child.get('mandatory','false')
            if mandatory not in ('true','false'):raise ValueError('invalid mandatory flag')
            if element.tag=='and' and mandatory=='true':formulas.append(('or',('not',parent),value))
            visit(child)
        if element.tag in ('or','alt'):
            if not children:raise ValueError('empty feature group')
            ids=[names[c.attrib['name']] for c in children]
            formulas.append(('or',('not',parent),*ids))
            if element.tag=='alt':
                formulas.extend(('or',('not',a),('not',b)) for i,a in enumerate(ids) for b in ids[i+1:])
    structure=root.find('struct')[0]
    formulas.append(names[structure.attrib['name']]);visit(structure)
    constraints=root.find('constraints')
    if constraints is not None:
        for rule in constraints:
            if rule.tag!='rule' or len(rule)!=1:raise ValueError('unsupported constraint wrapper')
            formulas.append(boolean(rule[0]))
    return ('and',*formulas)


def equivalence_miter(payload: bytes, mapping):
    """SAT iff XML and CNF disagree, only when all CNF axes are original features.

    This is a structural Tseitin encoding independent of the bucket counter.
    New gate variables are definitionally constrained in both directions.
    """
    if mapping['unmatched_variables']:raise ValueError('auxiliary elimination needs a quantified equivalence proof')
    original=featureide_formula(payload,mapping)
    clauses=[]; next_id=mapping['declared_variables']+1
    def encode(node):
        nonlocal next_id
        if type(node) is int:return node
        op,*children=node
        if op=='not':return -encode(children[0])
        values=[encode(c) for c in children]
        result=next_id;next_id+=1
        if op=='and':
            clauses.extend([-result,value] for value in values)
            clauses.append([result,*(-v for v in values)])
        elif op=='or':
            clauses.extend([result,-value] for value in values)
            clauses.append([-result,*values])
        else:raise ValueError('unsupported miter operator')
        return result
    a=encode(original)
    b=encode(('and',*(('or',*clause) for clause in mapping['clauses'])))
    clauses.extend([[a,b],[-a,-b]])
    return clauses,next_id-1


def concrete_equivalence_miter(payload: bytes, mapping, *, max_hidden=6):
    """Compare concrete-feature selections, explicitly quantifying abstract nodes.

    This is a different contract from all-feature equivalence. Abstract model
    features remain documented features; no name-based auxiliary guess is made.
    """
    selected=set(mapping['concrete_variables'])
    hidden=sorted(set(range(1,mapping['declared_variables']+1))-selected)
    if len(hidden)>max_hidden:raise ValueError('concrete projection expansion limit')
    original=featureide_formula(payload,mapping)
    converted=('and',*(('or',*clause) for clause in mapping['clauses']))
    def substitute(node,fixed):
        if type(node) is int:
            if abs(node) in fixed:return ('and',) if fixed[abs(node)]==(node>0) else ('or',)
            return node
        op,*children=node
        values=[substitute(c,fixed) for c in children]
        if op=='not':
            value=values[0]
            if value==('and',):return ('or',)
            if value==('or',):return ('and',)
            return ('not',value)
        identity=('and',) if op=='and' else ('or',)
        absorbing=('or',) if op=='and' else ('and',)
        if absorbing in values:return absorbing
        return (op,*(v for v in values if v!=identity))
    def quantify(formula):
        return ('or',*(substitute(formula,dict(zip(hidden,bits))) for bits in product((False,True),repeat=len(hidden))))
    clauses=[];next_id=mapping['declared_variables']+1;memo={}
    def encode(node):
        nonlocal next_id
        if type(node) is int:return node
        if node in memo:return memo[node]
        op,*children=node
        if op=='not':return -encode(children[0])
        values=[encode(c) for c in children]
        result=next_id;next_id+=1;memo[node]=result
        if op=='and':
            clauses.extend([-result,v] for v in values);clauses.append([result,*(-v for v in values)])
        elif op=='or':
            clauses.extend([result,-v] for v in values);clauses.append([-result,*values])
        else:raise ValueError('unsupported projection operator')
        return result
    a=encode(quantify(original));b=encode(quantify(converted))
    clauses.extend([[a,b],[-a,-b]])
    return clauses,next_id-1
