#!/usr/bin/env python
'''Simple utility functions that do not depend on any other part of 
peyotl.
'''
import logging
import time
import os

def expand_path(p):
    return os.path.expanduser(os.path.expandvars(p))

def pretty_timestamp(t=None, style=0):
    if t is None:
        t = time.localtime()
    if style == 0:
        return time.strftime("%Y-%m-%d", t)
    return time.strftime("%Y%m%d%H%M%S", t)

_LOGGING_LEVEL_ENVAR = "PEYOTL_LOGGING_LEVEL"
_LOGGING_FORMAT_ENVAR = "PEYOTL_LOGGING_FORMAT"

def get_logging_level():
    if _LOGGING_LEVEL_ENVAR in os.environ:
        if os.environ[_LOGGING_LEVEL_ENVAR].upper() == "NOTSET":
            level = logging.NOTSET
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "DEBUG":
            level = logging.DEBUG
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "INFO":
            level = logging.INFO
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "WARNING":
            level = logging.WARNING
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "ERROR":
            level = logging.ERROR
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "CRITICAL":
            level = logging.CRITICAL
        else:
            level = logging.NOTSET
    else:
        level = logging.NOTSET
    return level

def get_logger(name="peyotl"):
    """
    Returns a logger with name set as given, and configured
    to the level given by the environment variable _LOGGING_LEVEL_ENVAR.
    """

#     package_dir = os.path.dirname(module_path)
#     config_filepath = os.path.join(package_dir, _LOGGING_CONFIG_FILE)
#     if os.path.exists(config_filepath):
#         try:
#             logging.config.fileConfig(config_filepath)
#             logger_set = True
#         except:
#             logger_set = False
    logger = logging.getLogger(name)
    if not hasattr(logger, 'is_configured'):
        logger.is_configured = False
    if not logger.is_configured:
        level = get_logging_level()
        rich_formatter = logging.Formatter("[%(asctime)s] %(filename)s (%(lineno)d): %(levelname) 8s: %(message)s")
        simple_formatter = logging.Formatter("%(levelname) 8s: %(message)s")
        default_formatter = None
        logging_formatter = default_formatter
        if _LOGGING_FORMAT_ENVAR in os.environ:
            if os.environ[_LOGGING_FORMAT_ENVAR].upper() == "RICH":
                logging_formatter = rich_formatter
            elif os.environ[_LOGGING_FORMAT_ENVAR].upper() == "SIMPLE":
                logging_formatter = simple_formatter
            elif os.environ[_LOGGING_FORMAT_ENVAR].upper() == "NONE":
                logging_formatter = None
            else:
                logging_formatter = default_formatter
        else:
            logging_formatter = default_formatter
        if logging_formatter is not None:
            logging_formatter.datefmt = '%H:%M:%S'
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(logging_formatter)
        logger.addHandler(ch)
        logger.is_configured = True
    return logger
_LOG = get_logger("peyotl.utility")

_CONFIG = None
_CONFIG_FN = None
def get_config(section=None, param=None):
    '''
    Returns the config object if `section` and `param` are None, or the 
        value for the requested parameter.
    
    If the parameter (or the section) is missing, the exception is logged and
        None is returned.
    '''
    global _CONFIG, _CONFIG_FN
    if _CONFIG is None:
        from ConfigParser import SafeConfigParser
        _CONFIG_FN = os.path.expanduser("~/.peyotl/config")
        _CONFIG = SafeConfigParser()
        _CONFIG.read(_CONFIG_FN)
    if section is None and param is None:
        return _CONFIG
    try:
        v = _CONFIG.get(section, param)
        return v
    except:
        mf = 'Config file "{f}" does not contain option "{o}"" in section "{s}"\n'
        msg = mf.format(f=_CONFIG_FN, o=param, s=section)
        _LOG.error(msg)
        return None

class ListDiffObject(object):
    pass
class ListDeletion(ListDiffObject):
    def __init__(self, s_ind, o):
        self.index = s_ind
        self.obj = o
    def __repr__(self):
        return 'ListDeletion({s}, {o})'.format(s=self.index, o=repr(self.obj))
    def __str__(self):
        return repr(self) 
class ListAddition(ListDiffObject):
    def __init__(self, s_ind, o):
        self.index = s_ind
        self.obj = o
    def __repr__(self):
        return 'ListAddition({s}, {o})'.format(s=self.index, o=repr(self.obj))
    def __str__(self):
        return repr(self)

class ListElModification(ListDiffObject):
    def __init__(self, s_ind, src, dest):
        self.index = s_ind
        self.src = src
        self.dest = dest
    def __repr__(self):
        return 'ListElModification({s}, {o}, {d})'.format(s=self.index,
                                                          o=repr(self.src),
                                                          d=repr(self.dest))
    def __str__(self):
        return repr(self)

def recursive_list_diff(src, dest):
    '''Inefficient comparison of src and dest dicts.
    Recurses through dict and lists.
    returns (is_identical, modifications, additions, deletions)
    where each
        is_identical is a boolean True if the dicts have 
            contents that compare equal.
    and the other three are dicts:
        attributes both, but with different values
        attributes in dest but not in src
        attributes in src but not in dest

    Returned dicts may alias objects in src, and dest
    '''
    if src == dest:
        return (True, None, None, None)
    #TODO: find best match in list
    trivial_order = [(i, i) for i in range(min(len(src), len(dest)))]
    optimal_order = trivial_order
    src_ind = 0
    dest_ind = 0
    add_offset = 0
    modl, addl, dell = [], [], []
    for p in optimal_order:
        ns, nd = p
        while src_ind < ns:
            dell.append(ListDeletion(src_ind + add_offset, src[src_ind]))
            src_ind += 1
        while dest_ind < nd:
            addl.append(ListAddition(src_ind + add_offset, dest[dest_ind]))
            dest_ind += 1
            add_offset += 1
        sv, dv = src[ns], dest[nd]
        if sv != dv:
            modl.append(ListElModification(src_ind + add_offset, sv, dv))
        src_ind += 1
        dest_ind += 1
    while src_ind < len(src):
        dell.append(ListDeletion(src_ind + add_offset, src[src_ind]))
        src_ind += 1
    while dest_ind < len(dest):
        addl.append(ListAddition(src_ind + add_offset, dest[dest_ind]))
        dest_ind += 1
        add_offset += 1
    return (False, modl, addl, dell)

            

def recursive_dict_diff(src, dest):
    '''Inefficient comparison of src and dest dicts.
    Recurses through dict and lists.
    returns (is_identical, modifications, additions, deletions)
    where each
        is_identical is a boolean True if the dicts have 
            contents that compare equal.
    and the other three are dicts:
        attributes both, but with different values
        attributes in dest but not in src
        attributes in src but not in dest

    Returned dicts may alias objects in src, and dest
    '''
    if src == dest:
        return (True, None, None, None)
    moddict, adddict, deldict = {}, {}, {}
    sk = set(src.keys())
    dk = set(dest.keys())
    for k in sk:
        v = src[k]
        if k in dest:
            dv = dest[k]
            if v != dv:
                rec_call = None
                if isinstance(v, dict) and isinstance(dv, dict):
                    rec_call = recursive_dict_diff(v, dv)
                elif isinstance(v, list) and isinstance(dv, list):
                    rec_call = recursive_list_diff(v, dv)
                if rec_call is not None:
                    rc, rm, ra, rd = rec_call
                    assert(rc is False)
                    if rm:
                        moddict[k] = rm
                    if ra:
                        adddict[k] = ra
                    if rd:
                        deldict[k] = rd
    return (False, moddict, adddict, deldict)
