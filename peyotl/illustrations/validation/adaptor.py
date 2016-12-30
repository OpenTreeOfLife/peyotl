#!/usr/bin/env python
'''IllustrationValidationAdaptor class.
'''
from peyotl.utility import get_logger
_LOG = get_logger(__name__)

def create_validation_adaptor(obj, errors, **kwargs):
    # just one simple version for now, so one adapter class
    return IllustrationValidationAdaptor(obj, errors, **kwargs)

# TODO: Define a simple adapter based on
# nexson_validation._badgerfish_validation.BadgerFishValidationAdapter.
# N.B. that this doesn't need to inherit from NexsonValidationAdapter, since
# we're not adding annotations to the target document. Similarly, we're not using
# the usual validation logger here, just a list of possible error strings.
class IllustrationValidationAdaptor(object):
    def __init__(self, obj, errors=None, **kwargs):
        if errors is None:
            errors = []
        try:
            # Python 2.x
            string_types = (str, unicode)
        except NameError:
            # Python 3
            string_types = (str,)

        # TODO: Test this item's subtype (e.g. illustration, template, style
        # guide) to determine how to validate it. Do we expect all subtypes to
        # have a JSON "core"?

        self.required_toplevel_elements = {
            # N.B. anyjson might parse a text element as str or unicode,
            # depending on its value. Either is fine here.
            'metadata': dict,
            'elements': list,
            'styleGuide': dict,
            'style': dict,
            'vegaSpec': dict,
        }
        self.optional_toplevel_elements = {
            'id': string_types,  # not present in initial request
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
                from peyotl.illustrations import ILLUSTRATION_ID_PATTERN
                assert bool(ILLUSTRATION_ID_PATTERN.match(self._id))
            except:
                errors.append("The top-level illustration 'id' provided is not valid")

        # TODO: other tests for an illustration
        #  - are all referenced ornaments/etc/ found in its folder?
        #  - etc.

        # test for a valid date_created (should be valid ISO 8601)
        self._date_created = obj.get('metadata').get('date_created')
        import dateutil.parser
        try:
            dateutil.parser.parse(self._date_created)
        except:
            errors.append("Property 'metadata.date_created' is not a valid ISO date")

