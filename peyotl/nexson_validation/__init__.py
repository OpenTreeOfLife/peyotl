#!/usr/bin/env python
'''Functions for validating NexSON.
'''
from nexson_validation.warning_codes import WarningCodes
from nexson_validation.validation_logger import FilteringLogger, \
                                                ValidationLogger


class NexSONError(Exception):
    def __init__(self, v):
        self.value = v
    def __str__(self):
        return repr(self.v)


def create_validation_nexson(obj, warning_codes_to_skip, retain_deprecated=True):
    '''Creates a validatation logger and then creates an object of type NexSON
    Returns the pair:
        validatation_log, NexSON object
    Note that obj can be modified if retain_deprecated is not True.
    Also note that the "raw" dict within the returned NexSON object will hold
        references to parts of `obj`
    '''
    if warning_codes_to_skip:
        v = FilteringLogger(codes_to_skip=list(warning_codes_to_skip), store_messages=True)
    else:
        v = ValidationLogger(store_messages=True)
    v.retain_deprecated = retain_deprecated
    n = NexsonValidationAdaptor(obj, v)
    return v, n

    def prepare_annotation(validation_logger, 
                       author_name='',
                       invocation=tuple(),
                       annotation_label='',
                       author_version=VERSION,
                       url='https://github.com/OpenTreeOfLife/api.opentreeoflife.org',
                       description="validator of NexSON constraints as well as constraints that would allow a study to be imported into the Open Tree of Life's phylogenetic synthesis tools"
                       ):
    checks_performed = list(WarningCodes.numeric_codes_registered)
    for code in validation_logger.codes_to_skip:
        try:
            checks_performed.remove(code)
        except:
            pass
    checks_performed = [WarningCodes.facets[i] for i in checks_performed]
    nuuid = 'meta-' + str(uuid.uuid1())
    annotation = {
        '@property': 'ot:annotation',
        '$': annotation_label,
        '@xsi:type': 'nex:ResourceMeta',
        'author': {
            'name': author_name, 
            'url': url, 
            'description': description,
            'version': author_version,
            'invocation': {
                'commandLine': invocation,
                'checksPerformed': checks_performed,
                'pythonVersion' : platform.python_version(),
                'pythonImplementation' : platform.python_implementation(),
            }
        },
        'dateCreated': datetime.datetime.utcnow().isoformat(),
        'id': nuuid,
        'messages': [],
        'isValid': (len(validation_logger.errors) == 0) and (len(validation_logger.warnings) == 0),
    }
    message_list = annotation['messages']
    for m in validation_logger.errors:
        d = m.as_dict()
        d['severity'] = 'ERROR'
        d['preserve'] = False
        message_list.append(d)
    for m in validation_logger.warnings:
        d = m.as_dict()
        d['severity'] = 'WARNING'
        d['preserve'] = False
        message_list.append(d)
    return annotation



def add_or_replace_annotation(obj, annotation):
    '''Takes a nexson object `obj` and an `annotation` dictionary which is 
    expected to have a string as the value of annotation['author']['name']
    This function will remove all annotations from obj that:
        1. have the same author/name, and
        2. have no messages that are flagged as messages to be preserved (values for 'preserve' that evaluate to true)
    '''
    script_name = annotation['author']['name']
    n = obj['nexml']
    former_meta = n.setdefault('meta', [])
    if not isinstance(former_meta, list):
        former_meta = [former_meta]
        n['meta'] = former_meta
    else:
        indices_to_pop = []
        for annotation_ind, el in enumerate(former_meta):
            try:
                if (el.get('$') == annotation_label) and (el.get('author',{}).get('name') == script_name):
                    m_list = el.get('messages', [])
                    to_retain = []
                    for m in m_list:
                        if m.get('preserve'):
                            to_retain.append(m)
                    if len(to_retain) == 0:
                        indices_to_pop.append(annotation_ind)
                    elif len(to_retain) < len(m_list):
                        el['messages'] = to_retain
                        el['dateModified'] = datetime.datetime.utcnow().isoformat()
            except:
                # different annotation structures could yield IndexErrors or other exceptions.
                # these are not the annotations that you are looking for....
                pass

        if len(indices_to_pop) > 0:
            # walk backwards so pops won't change the meaning of stored indices
            for annotation_ind in indices_to_pop[-1::-1]:
                former_meta.pop(annotation_ind)
    former_meta.append(annotation)
