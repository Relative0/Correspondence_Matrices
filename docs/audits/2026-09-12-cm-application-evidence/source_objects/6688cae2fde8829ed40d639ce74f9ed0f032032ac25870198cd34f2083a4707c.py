"""Explicit Boolean-selection abstraction for static FeatureIDE attributes.

Attribute values and prices are not counted. This adapter follows the distinct
feature/attribute parsing in FeatureIDE's XmlExtendedFeatureModelFormat and
admits only ordinary Boolean constraints referring to named features.
"""
from decimal import Decimal, InvalidOperation
import hashlib
import xml.etree.ElementTree as ET

from cmbench.comparative.feature_mapping import feature_mapping, featureide_formula


def boolean_selection_abstraction(payload, dimacs):
    if len(payload)>2<<20 or b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():
        raise ValueError('unsupported XML size or entities')
    root=ET.fromstring(payload)
    if root.tag!='extendedFeatureModel' or root.attrib: raise ValueError('unsupported extended model root')
    structure=root.find('struct')
    if structure is None or len(structure)!=1: raise ValueError('invalid feature structure')
    attributes=[]
    for feature in structure.iter():
        if feature is structure or feature.tag=='attribute': continue
        if feature.tag not in ('and','or','alt','feature'): raise ValueError('unsupported structural extension')
        seen=set()
        for child in list(feature):
            if child.tag!='attribute': continue
            if len(child) or (child.text or '').strip(): raise ValueError('nonstatic attribute expression')
            if set(child.attrib)-{'name','type','unit','value','recursive','configurable'}: raise ValueError('unknown attribute field')
            name=child.get('name')
            if not name or name in seen: raise ValueError('ambiguous attribute identity')
            seen.add(name)
            if child.get('type')!='double': raise ValueError('only static double attributes admitted')
            if child.get('configurable','false')!='false': raise ValueError('configurable attributes not admitted')
            if child.get('recursive','false') not in ('true','false'): raise ValueError('invalid recursive attribute flag')
            if 'value' in child.attrib:
                try: number=Decimal(child.attrib['value'])
                except InvalidOperation as exc: raise ValueError('invalid static double') from exc
                if not number.is_finite(): raise ValueError('nonfinite static double')
            attributes.append(dict(feature=feature.get('name'), **child.attrib))
            feature.remove(child)
    root.tag='featureModel'
    normalized=ET.tostring(root,encoding='utf-8')
    mapping=feature_mapping(normalized,dimacs)
    # This validates every remaining section and requires var leaves to name
    # original Boolean features. Attribute expressions cannot silently survive.
    featureide_formula(normalized,mapping)
    metadata=dict(scope='Boolean feature selections only; no price, cost, or attribute-value configuration counting',
                  original_xml_sha256=hashlib.sha256(payload).hexdigest(),
                  boolean_xml_sha256=hashlib.sha256(normalized).hexdigest(),
                  static_attribute_count=len(attributes), attributes=attributes,
                  primary_source_revision='d769691754fd63cf757902fc1b3daf28d9333535')
    return normalized,mapping,metadata
