# !/usr/bin/env python
"""Basic functions for creating and manipulating amendments JSON.
"""


def get_empty_amendment():
    import datetime
    amendment = {
        "id": "",  # assigned when new ottids are minted
        "curator": {"login": "", "name": ""},
        "date_created": datetime.datetime.utcnow().date().isoformat(),
        "user_agent": "",
        "study_id": "",
        "taxa": [],
    }
    return amendment


__all__ = ['git_actions',
           'helper',
           'validation',
           'amendments_shard',
           'amendments_umbrella']

# noinspection PyPep8
from peyotl.amendments.amendments_umbrella import (TaxonomicAmendmentStore,
                                                   TaxonomicAmendmentStoreProxy,
                                                   AMENDMENT_ID_PATTERN)

# TODO: Define common support functions here (see collections/__init_.py for inspiration)
