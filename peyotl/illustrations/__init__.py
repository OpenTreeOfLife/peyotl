 #!/usr/bin/env python
'''Basic functions for creating and manipulating illustrations
'''

def get_empty_illustration():
    import datetime
    illustration = {
        # TODO: add minimal properties for an illustration's "core" JSON file
    }
    return illustration

__all__ = ['git_actions',
           'helper',
           'validation',
           'illustrations_shard',
           'illustrations_umbrella']
from peyotl.illustrations.illustrations_umbrella import IllustrationStore, \
                                                        IllustrationStoreProxy, \
                                                        ILLUSTRATION_ID_PATTERN

# TODO: Define common support functions here (see collections/__init_.py for inspiration)
