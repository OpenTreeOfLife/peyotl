 #!/usr/bin/env python
'''Basic functions for creating and manipulating amendments JSON.
'''

def get_empty_amendment():
    import datetime
    amendment = {
        # TODO: review fields and structure
        "curator": {"login": "", "name": ""},
        "date_created": datetime.datetime.utcnow().isoformat(),
        "study_id": "",
        "taxa": [ ],
        "comment": "",
    }
    return amendment

__all__ = ['git_actions',
           'helper',
           'validation',
           'amendments_shard',
           'amendments_umbrella']

# TODO: Define common support functions here (see collections/__init_.py for inspiration)
