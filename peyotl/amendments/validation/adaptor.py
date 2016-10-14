#!/usr/bin/env python
"""AmendmentValidationAdaptor class.
"""
from peyotl.utility import get_logger, doi2url

_LOG = get_logger(__name__)


def create_validation_adaptor(obj, errors, **kwargs):
    # just one simple version for now, so one adapter class
    return AmendmentValidationAdaptor(obj, errors, **kwargs)


# TODO: Define a simple adapter based on
# nexson_validation._badgerfish_validation.BadgerFishValidationAdapter.
# N.B. that this doesn't need to inherit from NexsonValidationAdapter, since
# we're not adding annotations to the target document. Similarly, we're not using
# the usual validation logger here, just a list of possible error strings.
class AmendmentValidationAdaptor(object):
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
            'curator': dict,
            'date_created': string_types,
            'taxa': list,
            'user_agent': string_types,
        }
        self.optional_toplevel_elements = {
            'id': string_types,  # not present in initial request
            'study_id': string_types,
            'new_ottids_required': int,  # provided by some agents
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
            # self._warn_event(_NEXEL.TOP_LEVEL,
            #                  obj=obj,
            #                  err_type=gen_UnrecognizedKeyWarning,
            #                  anc=_EMPTY_TUPLE,
            #                  obj_nex_id=None,
            #                  key_list=uk)
            errors.append("Found these unexpected top-level properties: {k}".format(k=uk))

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

        # test a non-empty id against our expected pattern
        self._id = obj.get('id')
        if self._id and isinstance(self._id, string_types):
            try:
                from peyotl.amendments import AMENDMENT_ID_PATTERN
                assert bool(AMENDMENT_ID_PATTERN.match(self._id))
            except:
                errors.append("The top-level amendment 'id' provided is not valid")

        # test a non-empty curator for expected 'login' and 'name' fields
        self._curator = obj.get('curator')
        if isinstance(self._curator, dict):
            for k in self._curator.keys():
                try:
                    assert k in ['login', 'name', 'email', ]
                except:
                    errors.append("Unexpected key '{k}' found in curator".format(k=k))
            if 'login' in self._curator:
                try:
                    assert isinstance(self._curator.get('name'), string_types)
                except:
                    errors.append("Curator 'name' should be a string")
            if 'name' in self._curator:
                try:
                    assert isinstance(self._curator.get('login'), string_types)
                except:
                    errors.append("Curator 'login' should be a string")
            if 'email' in self._curator:
                try:
                    assert isinstance(self._curator.get('email'), string_types)
                except:
                    # TODO: Attempt to validate as an email address?
                    errors.append("Curator 'email' should be a string (a valid email address)")

        # test for a valid date_created (should be valid ISO 8601)
        self._date_created = obj.get('date_created')
        import dateutil.parser
        try:
            dateutil.parser.parse(self._date_created)
        except:
            errors.append("Property 'date_created' is not a valid ISO date")

        # test for a valid study_id (if it's not an empty string)
        self._study_id = obj.get('study_id')
        if self._study_id and isinstance(self._study_id, string_types):
            from peyotl.phylesystem import STUDY_ID_PATTERN
            try:
                assert bool(STUDY_ID_PATTERN.match(self._study_id))
            except:
                errors.append("The 'study_id' provided is not valid")

        # text taxa for required properties, valid types+values, etc.
        self._taxa = obj.get('taxa')
        if isinstance(self._taxa, list):
            # N.B. required property cannot be empty!
            self.required_toplevel_taxon_elements = {
                'name': string_types,
                'name_derivation': string_types,  # from controlled vocabulary
                'sources': list,
            }
            self.optional_toplevel_taxon_elements = {
                'comment': string_types,
                'rank': string_types,  # can be 'no rank'
                'original_label': string_types,
                'adjusted_label': string_types,
                'parent': int,  # the parent taxon's OTT id
                'parent_tag': string_types,
                'tag': object,  # can be anything (int, string, ...)
                'ott_id': int  # if already assigned
            }

            # N.B. we should reject any unknown keys (not listed above)!
            uk = None
            for taxon in self._taxa:
                for k in taxon.keys():
                    if (k not in self.required_toplevel_taxon_elements.keys() and
                        k not in self.optional_toplevel_taxon_elements.keys()):
                        if uk is None:
                            uk = []
                        uk.append(k)

                for el_key, el_type in self.required_toplevel_taxon_elements.items():
                    test_el = taxon.get(el_key, None)
                    try:
                        assert test_el is not None
                    except:
                        errors.append("Required taxon property '{p}' not found!".format(p=el_key))
                    try:
                        assert isinstance(test_el, el_type)
                    except:
                        errors.append("Taxon property '{p}' should be one of these: {t}".format(p=el_key, t=el_type))

                # TODO: name_derivation should be one of a limited set of values

                # any optional properties found should also be of the required type(s)
                for el_key, el_type in self.optional_toplevel_taxon_elements.items():
                    if el_key in taxon:
                        test_el = taxon.get(el_key, None)
                        try:
                            assert isinstance(test_el, el_type)
                        except:
                            errors.append(
                                "Taxon property '{p}' should be one of these: {t}".format(p=el_key, t=el_type))

                # each taxon must have either 'parent' or 'parent_tag'!
                try:
                    assert ('parent' in taxon) or ('parent_tag' in taxon)
                except:
                    errors.append("Taxon has neither 'parent' nor 'parent_tag'!")

                # we need at least one source with type and (sometimes) non-empty value
                self.source_types_requiring_value = [
                    'Link to online taxonomy',
                    'Link (DOI) to publication',
                    'Other',
                ]
                self.source_types_not_requiring_value = [
                    'The taxon is described in this study',
                ]
                self.source_types_requiring_URL = [
                    'Link to online taxonomy',
                    'Link (DOI) to publication',
                ]
                valid_source_found = False
                if len(taxon.get('sources')) > 0:
                    for s in taxon.get('sources'):
                        s_type = s.get('source_type', None)
                        try:
                            assert (s_type in self.source_types_requiring_value or
                                    s_type in self.source_types_not_requiring_value)
                            if s_type in self.source_types_requiring_value:
                                try:
                                    # the 'source' (value) field should be a non-empty string
                                    assert s.get('source', None)
                                    valid_source_found = True
                                except:
                                    errors.append("Missing value for taxon source of type '{t}'!".format(t=s_type))
                            else:
                                valid_source_found = True
                            if s_type in self.source_types_requiring_URL:
                                try:
                                    # its value should contain a URL (ie, conversion does nothing)
                                    s_val = s.get('source')
                                    assert s_val == doi2url(s_val)
                                except:
                                    errors.append("Source '{s}' (of type '{t}') should be a URL!".format(s=s_val, t=s_type))
                        except:
                            errors.append("Unknown taxon source type '{t}'!".format(t=s_type))

                if not valid_source_found:
                    errors.append("Taxon must have at least one valid source (none found)!")

            if uk:
                uk.sort()
                errors.append("Found these unexpected taxon properties: {k}".format(k=uk))
