#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple utility functions that do not depend on any other part of
peyotl.
"""
__all__ = ['get_logger', 'get_config']


def download_large_file(url, destination_filepath):
    """
    See http://stackoverflow.com/questions/16694907/how-to-download-large-file-in-python-with-requests-py
    by Roman Podlinov
    """
    import requests
    r = requests.get(url, stream=True)
    r.raise_for_status()
    par_dir = os.path.split(destination_filepath)[0]
    assure_dir_exists(par_dir)
    with open(destination_filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    return destination_filepath


from peyutil import (any_early_exit,
                     doi2url, download,
                     expand_path,
                     get_unique_filepath,
                     is_str_type,
                     open_for_group_write,
                     parse_study_tree_list, pretty_timestamp, propinquity_fn_to_study_tree,
                     write_to_filepath, )
import peyotl.utility.get_logger
from peyotl.utility.get_logger import get_logger
from peyotl.utility.get_config import (ConfigWrapper, get_config_setting, get_config_object, read_config,
                                       get_raw_default_config_and_read_file_list)

