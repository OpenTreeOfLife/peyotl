#!/usr/bin/env python
from peyutil.dict_wrapper import FrozenDictAttrWrapper
import copy


def normalize_study_id(study_id):
    """We still have some un-prefixed IDs (at least on the devapi)"""
    try:
        int(study_id)
        return 'pg_' + str(study_id)
    except:
        return study_id


class StudyRef(FrozenDictAttrWrapper):
    pass


class TreeRef(FrozenDictAttrWrapper):
    def __init__(self, study_id, tree_id):
        FrozenDictAttrWrapper.__init__(self, {'study_id': normalize_study_id(study_id),
                                              'tree_id': tree_id})

    def __str__(self):
        return 'TreeRef(study_id={s}, tree_id={t})'.format(s=repr(self.study_id), t=repr(self.tree_id))


# noinspection PyMissingConstructor
class TreeRefList(list):
    def __init__(self, oti_response=None):
        # OTI returns a list of objects like:
        #    {u'ot:studyId': u'422',
        #     u'matched_trees': [
        #       {u'nexson_id': u'tree528',
        #        u'oti_tree_id': u'422_tree528'}
        #                       ]
        #    }
        assert oti_response is not None
        self._oti_response = copy.deepcopy(oti_response)
        for el in oti_response:
            study_id = el['ot:studyId']
            for tree in el['matched_trees']:
                self.append(TreeRef(study_id=study_id, tree_id=tree['nexson_id']))
