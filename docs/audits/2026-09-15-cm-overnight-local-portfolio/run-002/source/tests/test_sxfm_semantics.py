from itertools import product
import pytest
from cmbench.comparative.feature_mapping import feature_mapping
from cmbench.comparative.sxfm_semantics import sxfm_formula,projected_equivalence_miter

XML=b'<feature_model><feature_tree>\n:r Root(r)\n\t:g [1,1]\n\t\t:m Alpha(a)\n\t\t:m Beta(b)\n</feature_tree><constraints/></feature_model>'
CNF='c 1 Root\nc 2 Alpha\nc 3 Beta\nc 4 Enc\np cnf 4 6\n1 0\n-2 1 0\n-3 1 0\n2 3 0\n-2 -3 0\n4 2 0\n'

def evaluate(node,bits):
    if type(node) is int:return bits[abs(node)-1]==(node>0)
    op,*children=node
    return (all if op=='and' else any)(evaluate(c,bits) for c in children)


def test_group_members_are_alternatives_despite_legacy_mandatory_markers():
    mapping=feature_mapping(XML,CNF)
    formula=sxfm_formula(XML,mapping)
    admitted=[bits for bits in product((False,True),repeat=3) if evaluate(formula,bits)]
    assert admitted==[(True,False,True),(True,True,False)]
    clauses,n=projected_equivalence_miter(XML,mapping)
    # Use deterministic propagation of the generated definitional clauses via
    # a small independent DPLL, avoiding a large exhaustive gate enumeration.
    def sat(clauses):
        if not clauses:return True
        if any(not c for c in clauses):return False
        variable=next((c[0] for c in clauses if len(c)==1),clauses[0][0])
        return any(sat([[v for v in c if v!=-choice] for c in clauses if choice not in c]) for choice in (variable,-variable))
    assert not sat(clauses)
    altered=XML.replace(b'[1,1]',b'[1,*]')
    assert sat(projected_equivalence_miter(altered,mapping)[0])
    with pytest.raises(ValueError,match='expansion'):projected_equivalence_miter(XML,mapping,max_auxiliaries=0)


def test_unsupported_or_ambiguous_sxfm_is_refused():
    mapping=feature_mapping(XML,CNF)
    for changed in (XML.replace(b'\t',b' '),XML.replace(b'[1,1]',b'[2,1]'),XML.replace(b'<constraints/>',b'<constraints>c1: a AND b</constraints>')):
        with pytest.raises(ValueError):sxfm_formula(changed,mapping)
