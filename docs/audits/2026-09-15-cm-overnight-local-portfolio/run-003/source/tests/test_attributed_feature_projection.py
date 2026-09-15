import pytest

from cmbench.comparative.attributed_feature_projection import boolean_selection_abstraction
from cmbench.comparative.feature_mapping import featureide_formula


XML=b'''<extendedFeatureModel><struct><and name="Root" abstract="true"><attribute name="Price" type="double" recursive="true" value="4.5"/><feature name="A"/></and></struct><constraints><rule><imp><var>A</var><var>Root</var></imp></rule></constraints></extendedFeatureModel>'''
CNF='c 1 Root\nc 2 A\np cnf 2 2\n1 0\n-2 1 0\n'


def test_static_attributes_are_separate_from_boolean_features():
    normalized,mapping,metadata=boolean_selection_abstraction(XML,CNF)
    assert mapping['feature_variables']==[1,2] and mapping['concrete_variables']==[2]
    assert metadata['static_attribute_count']==1 and metadata['attributes'][0]['value']=='4.5'
    assert b'<attribute' not in normalized
    assert featureide_formula(normalized,mapping)


@pytest.mark.parametrize('old,new',[(b'type="double"',b'type="long"'),(b'value="4.5"',b'value="NaN"'),
                                 (b'value="4.5"',b'value="4.5" configurable="true"'),
                                 (b'<var>A</var>',b'<var>Price</var>'),(b'imp',b'add')])
def test_unknown_or_nonboolean_semantics_are_refused(old,new):
    with pytest.raises(ValueError):
        boolean_selection_abstraction(XML.replace(old,new),CNF)
