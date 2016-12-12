#!/usr/bin/env python
"""CollectionValidationAdaptor class.
"""
from peyotl.utility import get_logger

_LOG = get_logger(__name__)


def create_validation_adaptor(obj, errors, **kwargs):
    # just one simple version for now, so one adapter class
    return CollectionValidationAdaptor(obj, errors, **kwargs)


# TODO: Define a simple adapter based on
# nexson_validation._badgerfish_validation.BadgerFishValidationAdapter.
# N.B. that this doesn't need to inherit from NexsonValidationAdapter, since
# we're not adding annotations to the target document. Similarly, we're not using
# the usual validation logger here, just a list of possible error strings.
class CollectionValidationAdaptor(object):
    def __init__(self, obj, errors=None, **kwargs):
        if errors is None:
            errors = []
        try:
            # Python 2.x
            string_types = (str, unicode)
        except NameError:
            # Python 3
            string_types = (str,)
        self.required_toplevel_elements = {
            # N.B. anyjson might parse a text element as str or unicode,
            # depending on its value. Either is fine here.
            'name': string_types,
            'description': string_types,
            'creator': dict,
            'contributors': list,
            'decisions': list,
            'queries': list,
        }
        self.optional_toplevel_elements = {
            'url': string_types,
            # N.B. 'url' is stripped in storage, restored for API consumers
        }
        # track unknown keys in top-level object
        uk = None
        for k in obj.keys():
            if (k not in self.required_toplevel_elements.keys() and
                        k not in self.optional_toplevel_elements.keys()):
                if uk is None:
                    uk = []
                uk.append(k)
        if uk:
            uk.sort()
            errors.append("Found these unexpected taxon properties: {k}".format(k=uk))

        # test for existence and types of all required elements
        for el_key, el_type in self.required_toplevel_elements.items():
            test_el = obj.get(el_key, None)
            try:
                assert test_el is not None
            except:
                errors.append("Property '{p}' not found!".format(p=el_key))
            try:
                assert isinstance(test_el, el_type)
            except:
                errors.append("Property '{p}' should be one of these: {t}".format(p=el_key, t=el_type))
        # test a non-empty creator for expected 'login' and 'name' fields
        self._creator = obj.get('creator')
        if isinstance(self._creator, dict):
            for k in self._creator.keys():
                try:
                    assert k in ['login', 'name']
                except:
                    errors.append("Unexpected key '{k}' found in creator".format(k=k))
            if 'login' in self._creator:
                try:
                    assert isinstance(self._creator.get('name'), string_types)
                except:
                    errors.append("Creator 'name' should be a string")
            if 'name' in self._creator:
                try:
                    assert isinstance(self._creator.get('login'), string_types)
                except:
                    errors.append("Creator 'login' should be a string")
        # test any contributors for expected 'login' and 'name' fields
        self._contributors = obj.get('contributors')
        if isinstance(self._contributors, list):
            for c in self._contributors:
                if isinstance(c, dict):
                    for k in c.keys():
                        try:
                            assert k in ['login', 'name']
                        except:
                            errors.append("Unexpected key '{k}' found in contributor".format(k=k))
                    if 'login' in c:
                        try:
                            assert isinstance(c.get('name'), string_types)
                        except:
                            errors.append("Contributor 'name' should be a string")
                    if 'name' in c:
                        try:
                            assert isinstance(c.get('login'), string_types)
                        except:
                            errors.append("Contributor 'login' should be a string")
                else:
                    errors.append("Unexpected type for contributor (should be dict)")
        # test decisions for valid ids+SHA, valid decision value
        # N.B. that we use the list position for implicit ranking and
        # disregard this position for EXCLUDED trees.
        self._decisions = obj.get('decisions')
        if isinstance(self._decisions, list):
            text_props = ['name', 'studyID', 'treeID', 'SHA', 'decision']
            decision_values = ['INCLUDED', 'EXCLUDED', 'UNDECIDED']
            for d in self._decisions:
                try:
                    assert d.get('decision') in decision_values
                except:
                    errors.append("Each 'decision' should be one of {dl}".format(dl=decision_values))
                for p in text_props:
                    try:
                        assert isinstance(d.get(p), string_types)
                    except:
                        errors.append("Decision property '{p}' should be one of {t}".format(p=p, t=string_types))
        # TODO: test queries (currently unused) for valid properties
        self._queries = obj.get('queries')
