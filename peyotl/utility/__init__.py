#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple utility functions that do not depend on any other part of
peyotl.
"""
from peyotl.utility.input_output import (download, expand_path, open_for_group_write, parse_study_tree_list,
                                         write_to_filepath)
from peyotl.utility.str_util import is_str_type
import peyotl.utility.get_logger
from peyotl.utility.get_logger import get_logger
from peyotl.utility.get_config import (ConfigWrapper, get_config_setting, get_config_object, read_config,
                                       get_raw_default_config_and_read_file_list)
import time
import os

__all__ = ['input_output', 'simple_file_lock', 'str_util', 'get_logger', 'dict_wrapper', 'tokenizer', 'get_config']


def any_early_exit(iterable, predicate):
    """Tests each element in iterable by calling predicate(element). Returns True on first True, or False."""
    for i in iterable:
        if predicate(i):
            return True
    return False


def pretty_timestamp(t=None, style=0):
    if t is None:
        t = time.localtime()
    if style == 0:
        return time.strftime("%Y-%m-%d", t)
    return time.strftime("%Y%m%d%H%M%S", t)


def doi2url(v):
    if v.startswith('http'):
        return v
    if v.startswith('doi:'):
        if v.startswith('doi: '):
            v = v[5:]  # trim 'doi: '
        else:
            v = v[4:]  # trim 'doi:'
    if v.startswith('10.'):  # it's a DOI!
        return 'http://dx.doi.org/' + v
    # convert anything else to URL and hope for the best
    return 'http://' + v


def coerce_amendment_dois_to_urls(json):
    # Convert source DOIs in a taxonomic amendment to URL form (when fetching,
    # saving, or updating an amendment).
    # N.B. `json` is actually a dict (parsed from amendment JSON)!
    if 'taxa' in json:
        # simple amendment JSON
        taxa = json.get('taxa')
    else:
        # JSON includes wrapper w/ history, etc.
        taxa = json.get('data').get('taxa')
    if isinstance(taxa, list):
        for taxon in taxa:
            sources = taxon.get('sources')
            if isinstance(sources, list):
                for src in sources:
                    if src.get('source_type') == "Link (DOI) to publication":
                        # noinspection PyTypeChecker
                        src['source'] = doi2url(src.get('source', ""))


def get_unique_filepath(stem):
    """NOT thread-safe!
    return stems or stem# where # is the smallest
    positive integer for which the path does not exist.
    useful for temp dirs where the client code wants an
    obvious ordering.
    """
    fp = stem
    if os.path.exists(stem):
        n = 1
        fp = stem + str(n)
        while os.path.exists(fp):
            n += 1
            fp = stem + str(n)
    return fp


def propinquity_fn_to_study_tree(inp_fn, strip_extension=True):
    """This should only be called by propinquity - other code should be treating theses
    filenames (and the keys that are based on them) as opaque strings.

    Takes a filename (or key if strip_extension is False), returns (study_id, tree_id)

    propinquity provides a map to look up the study ID and tree ID (and git SHA)
    from these strings.
    """
    if strip_extension:
        study_tree = '.'.join(inp_fn.split('.')[:-1])  # strip extension
    else:
        study_tree = inp_fn
    x = study_tree.split('@')
    if len(x) != 2:
        msg = 'Currently we are expecting studyID@treeID.<file extension> format. Expected exactly 1 @ in the filename. Got "{}"'
        msg = msg.format(study_tree)
        raise ValueError(msg)
    return x
