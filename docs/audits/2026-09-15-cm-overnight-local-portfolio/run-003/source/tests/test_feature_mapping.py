import itertools
import pytest
from cmbench.comparative.feature_mapping import feature_mapping, equivalence_miter, projection_dimacs, concrete_equivalence_miter

XML=b'<featureModel><struct><and name="Root"><feature name="A" mandatory="true"/><feature name="B"/></and></struct><constraints/></featureModel>'
CNF='c 1 Root\nc 2 A\nc 3 B\np cnf 3 4\n1 0\n-2 1 0\n-1 2 0\n-3 1 0\n'

def satisfiable(clauses,n):
    return any(all(any(bits[abs(v)-1]==(v>0) for v in clause) for clause in clauses) for bits in itertools.product((False,True),repeat=n))

def test_xml_cnf_miter_detects_equivalence_and_semantic_drift():
    mapping=feature_mapping(XML,CNF)
    assert mapping['feature_variables']==[1,2,3]
    clauses,n=equivalence_miter(XML,mapping)
    assert not satisfiable(clauses,n)
    altered=XML.replace(b'mandatory="true"',b'mandatory="false"')
    clauses,n=equivalence_miter(altered,mapping)
    assert satisfiable(clauses,n)

def test_auxiliaries_and_duplicate_names_never_receive_guessed_semantics():
    extra=CNF.replace('p cnf 3 4','c 4 aux_1\np cnf 4 4')
    mapping=feature_mapping(XML,extra)
    assert mapping['unmatched_variables']==[4]
    with pytest.raises(ValueError,match='quantified'):equivalence_miter(XML,mapping)
    with pytest.raises(ValueError):feature_mapping(XML,CNF.replace('c 3 B','c 3 A'))
    with pytest.raises(ValueError):feature_mapping(b'<!DOCTYPE x>'+XML,CNF)

def test_original_projection_is_mandatory_and_strict():
    base='p cnf 3 1\n1 2 0\n'
    assert projection_dimacs('c ind 3 1 0\n'+base)[2]==(3,1)
    assert projection_dimacs('c ind 0\n'+base)[2]==()
    for text in ('', 'c ind 1 1 0\n','c ind 4 0\n','c ind 1\n','c ind -1 0\n'):
        with pytest.raises(ValueError):projection_dimacs(text+base)


def test_all_feature_and_concrete_feature_equivalence_are_distinct_contracts():
    xml=b'<featureModel><struct><and name="Root" abstract="true"><feature name="A" mandatory="true"/></and></struct></featureModel>'
    cnf='c 1 Root\nc 2 A\np cnf 2 1\n2 0\n'
    mapping=feature_mapping(xml,cnf)
    assert mapping['feature_variables']==[1,2] and mapping['concrete_variables']==[2]
    assert satisfiable(*equivalence_miter(xml,mapping))
    assert not satisfiable(*concrete_equivalence_miter(xml,mapping))
    with pytest.raises(ValueError,match='expansion'):concrete_equivalence_miter(xml,mapping,max_hidden=0)
