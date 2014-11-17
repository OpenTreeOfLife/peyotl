#!/usr/bin/env python
'''Simple utility functions that do not depend on any other part of
peyotl.
'''
__all__ = ['io', 'simple_file_lock', 'str_util']
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import logging
import json
import time
import os

from peyotl.utility.io import *

def pretty_timestamp(t=None, style=0):
    if t is None:
        t = time.localtime()
    if style == 0:
        return time.strftime("%Y-%m-%d", t)
    return time.strftime("%Y%m%d%H%M%S", t)

_LOGGING_LEVEL_ENVAR = "PEYOTL_LOGGING_LEVEL"
_LOGGING_FORMAT_ENVAR = "PEYOTL_LOGGING_FORMAT"
_LOGGING_FILE_PATH_ENVAR = "PEYOTL_LOG_FILE_PATH"

_LOG = None
_READING_LOGGING_CONF = True
_LOGGING_CONF = {}

def _get_logging_level(s=None):
    if s is None:
        return logging.NOTSET
    supper = s.upper()
    if supper == "NOTSET":
        level = logging.NOTSET
    elif supper == "DEBUG":
        level = logging.DEBUG
    elif supper == "INFO":
        level = logging.INFO
    elif supper == "WARNING":
        level = logging.WARNING
    elif supper == "ERROR":
        level = logging.ERROR
    elif supper == "CRITICAL":
        level = logging.CRITICAL
    else:
        level = logging.NOTSET
    return level

def _get_logging_formatter(s=None):
    if s is None:
        s = 'NONE'
    else:
        s = s.upper()
    logging_formatter = None
    if s == "RICH":
        logging_formatter = logging.Formatter("[%(asctime)s] %(filename)s (%(lineno)d): %(levelname) 8s: %(message)s")
    elif s == "SIMPLE":
        logging_formatter = logging.Formatter("%(levelname) 8s: %(message)s")
    elif s == "RAW":
        logging_formatter = logging.Formatter("%(message)s")
    else:
        logging_formatter = None
    if logging_formatter is not None:
        logging_formatter.datefmt = '%H:%M:%S'
    return logging_formatter


def read_logging_config(**kwargs):
    global _READING_LOGGING_CONF
    cfg = get_config_object(None, **kwargs)
    level = cfg.get_config_setting('logging', 'level', 'WARNING')
    logging_format_name = cfg.get_config_setting('logging', 'formatter', 'NONE')
    logging_filepath = cfg.get_config_setting('logging', 'filepath', '')
    if logging_filepath == '':
        logging_filepath = None
    _LOGGING_CONF['level_name'] = level
    _LOGGING_CONF['formatter_name'] = logging_format_name
    _LOGGING_CONF['filepath'] = logging_filepath
    _READING_LOGGING_CONF = False
    return _LOGGING_CONF


def get_logger(name="peyotl"):
    """
    Returns a logger with name set as given, and configured
    to the level given by the environment variable _LOGGING_LEVEL_ENVAR.
    """
    logger = logging.getLogger(name)
    if len(logger.handlers) == 0:
        lc = _LOGGING_CONF
        if 'level' not in lc:
            # TODO need some easy way to figure out whether we should use env vars or config
            if _LOGGING_LEVEL_ENVAR in os.environ:
                lc['level_name'] = os.environ.get(_LOGGING_LEVEL_ENVAR)
                lc['formatter_name'] = os.environ.get(_LOGGING_FORMAT_ENVAR)
                lc['filepath'] = os.environ.get(_LOGGING_FILE_PATH_ENVAR)
            else:
                lc = read_logging_config()
            lc['level'] = _get_logging_level(lc['level_name'])
            lc['formatter'] = _get_logging_formatter(lc['formatter_name'])
        logger.setLevel(lc['level'])
        if lc['filepath'] is not None:
            log_dir = os.path.split(lc['filepath'])[0]
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            ch = logging.FileHandler(lc['filepath'])
        else:
            ch = logging.StreamHandler()
        ch.setLevel(lc['level'])
        ch.setFormatter(lc['formatter'])
        logger.addHandler(ch)
    return logger

def _get_util_logger():
    global _LOG
    if _LOG is not None:
        return _LOG
    if _READING_LOGGING_CONF:
        return None
    _LOG = get_logger("peyotl.utility")
    return _LOG

_CONFIG = None
_CONFIG_FN = None
def get_config(section=None, param=None, default=None):
    '''
    Returns the config object if `section` and `param` are None, or the
        value for the requested parameter.

    If the parameter (or the section) is missing, the exception is logged and
        None is returned.
    '''
    global _CONFIG, _CONFIG_FN
    if _CONFIG is None:
        try:
            from ConfigParser import SafeConfigParser
        except ImportError:
            from configparser import ConfigParser as SafeConfigParser
        if 'PEYOTL_CONFIG_FILE' in os.environ:
            _CONFIG_FN = os.environ['PEYOTL_CONFIG_FILE']
        else:
            _CONFIG_FN = os.path.expanduser("~/.peyotl/config")
        if not os.path.exists(_CONFIG_FN):
            from pkg_resources import Requirement, resource_filename
            pr = Requirement.parse('peyotl')
            try:
                _CONFIG_FN = resource_filename(pr, 'peyotl/default.conf')
            except:
                return default
        assert os.path.exists(_CONFIG_FN)
        _CONFIG = SafeConfigParser()
        _CONFIG.read(_CONFIG_FN)
    if section is None and param is None:
        return _CONFIG
    return get_config_setting(_CONFIG_FN, section, param, default, config_filename=_CONFIG_FN)

def get_config_setting(config_obj, section, param, default=None, config_filename=''):
    try:
        return _CONFIG.get(section, param)
    except:
        if default is None:
            mf = 'Config file "{f}" does not contain option "{o}"" in section "{s}"\n'
            msg = mf.format(f=_CONFIG_FN, o=param, s=section)
            _ulog = _get_util_logger()
            if _ulog is not None:
                _ulog.error(msg)
        return default

class ConfigWrapper(object):
    '''Wrapper to provide a richer get_config_setting(section, param, d) behavior. That function will
    return a value from the following cascade:
        1. override[section][param] if section and param are in the resp. dicts
        2. the value in the config obj for section/param it that setting is in the config
        3. dominant_defaults[section][param] if section and param are in the resp. dicts
        4. the `default` arg of the get_config_setting call
        5. fallback_defaults[section][param] if section and param are in the resp. dicts
    '''
    def __init__(self,
                 raw_config_obj=None,
                 config_filename='<programmitcally configured>',
                 overrides=None,
                 dominant_defaults=None,
                 fallback_defaults=None):
        self._config_filename = config_filename
        self._raw = raw_config_obj
        if overrides is None:
            overrides = {}
        if dominant_defaults is None:
            dominant_defaults = {}
        if fallback_defaults is None:
            fallback_defaults = {}
        self._override = overrides
        self._dominant_defaults = dominant_defaults
        self._fallback_defaults = fallback_defaults
    def get_from_config_setting_cascade(self, sec_param_list, default=None):
        '''return the first non-None setting from a series where each
        element in `sec_param_list` is a section, param pair suitable for 
        a get_config_setting call.

        Note that non-None values for overrides or dominant_defaults will cause
            this call to only evaluate the first element in the cascade.
        '''
        for section, param in sec_param_list:
            r = self.get_config_setting(section, param, default=None)
            if r is not None:
                return r
        return default
    def get_config_setting(self, section, param, default=None):
        if section in self._override:
            so = self._override[section]
            if param in so:
                return so[param]
        if self._raw is None:
            self._raw = get_config(None, None)
            self._config_filename = _CONFIG_FN
        if section in self._dominant_defaults:
            so = self._dominant_defaults[section]
            if param in so:
                return get_config_setting(self._raw,
                                          section,
                                          param,
                                          default=so[param],
                                          config_filename=self._config_filename)
        if default is None:
            if section in self._fallback_defaults:
                default = self._dominant_defaults[section].get(param)
        return get_config_setting(self._raw,
                                  section,
                                  param,
                                  default=default,
                                  config_filename=self._config_filename)


def get_config_setting_kwargs(config_obj, section, param, default=None, **kwargs):
    '''Used to provide a consistent kwargs behavior for classes/methods that need to be config-dependent.

    Currently: if config_obj is None, then kwargs['config'] is checked. If it is also None
        then a default ConfigWrapper object is created.
    '''
    cfg = get_config_object(config_obj, **kwargs)
    return cfg.get_config_setting(section, param, default)

def get_config_object(config_obj, **kwargs):
    if config_obj is not None:
        return config_obj
    c = kwargs.get('config')
    if c is None:
        return ConfigWrapper()
    return c

def doi2url(v):
    if v.startswith('http'):
        return v
    if v.startswith('doi:'):
        v = v[4:] # trim doi:
    return 'http://dx.doi.org/' + v

def pretty_dict_str(d, indent=2):
    '''shows JSON indented representation of d'''
    b = StringIO()
    write_pretty_dict_str(b, d, indent=indent)
    return b.getvalue()
def write_pretty_dict_str(out, obj, indent=2):
    '''writes JSON indented representation of obj to out'''
    json.dump(obj,
              out,
              indent=indent,
              sort_keys=True,
              separators=(',', ': '),
              ensure_ascii=False,
              encoding="utf-8")

