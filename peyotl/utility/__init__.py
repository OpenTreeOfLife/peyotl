#!/usr/bin/env python
'''Simple utility functions that do not depend on any other part of
peyotl.
'''
__all__ = ['io', 'simple_file_lock', 'str_util']
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO #pylint: disable=E0611
import logging
import json
import time
import os

from peyotl.utility.io import download, \
                              expand_path, \
                              open_for_group_write, \
                              parse_study_tree_list, \
                              write_to_filepath
from peyotl.utility.str_util import is_str_type

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
    level = cfg.get_config_setting('logging', 'level', 'WARNING', warn_on_none_level=None)
    logging_format_name = cfg.get_config_setting('logging', 'formatter', 'NONE', warn_on_none_level=None)
    logging_filepath = cfg.get_config_setting('logging', 'filepath', '', warn_on_none_level=None)
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
def get_default_config_filename():
    global _CONFIG_FN
    if _CONFIG_FN is None:
        if 'PEYOTL_CONFIG_FILE' in os.environ:
            _CONFIG_FN = os.environ['PEYOTL_CONFIG_FILE']
        else:
            _CONFIG_FN = os.path.expanduser("~/.peyotl/config")
        if not os.path.exists(_CONFIG_FN):
            from pkg_resources import Requirement, resource_filename
            pr = Requirement.parse('peyotl')
            _CONFIG_FN = resource_filename(pr, 'peyotl/default.conf')
        assert os.path.exists(_CONFIG_FN)
    return _CONFIG_FN

def read_config(filepaths=None):
    global _CONFIG
    from ConfigParser import SafeConfigParser
    if filepaths is None:
        if _CONFIG is None:
            _CONFIG = SafeConfigParser()
            read_files = _CONFIG.read(get_default_config_filename())
        else:
            read_files = [get_default_config_filename()]
        cfg = _CONFIG
    else:
        if isinstance(filepaths, list) and None in filepaths:
            def_fn = get_default_config_filename()
            f = []
            for i in filepaths:
                f.append(def_fn if i is None else i)
            filepaths = f
        cfg = SafeConfigParser()
        read_files = cfg.read(filepaths)
    return cfg, read_files

def get_config(section=None, param=None, default=None, cfg=None, warn_on_none_level=logging.WARN):
    '''
    Returns the config object if `section` and `param` are None, or the
        value for the requested parameter.

    If the parameter (or the section) is missing, the exception is logged and
        None is returned.
    '''
    if cfg is None:
        try:
            cfg, read_filenames = read_config()
        except:
            return default
    else:
        read_filenames = None
    if section is None and param is None:
        return _CONFIG
    return get_config_setting(_CONFIG,
                              section,
                              param,
                              default,
                              config_filename=read_filenames,
                              warn_on_none_level=warn_on_none_level)

def get_config_setting(config_obj, section, param, default=None, config_filename='', warn_on_none_level=logging.WARN):
    '''Read (section, param) from `config_obj`. If not found, return `default`

    If the setting is not found and `default` is None, then an warn-level message is logged.
    `config_filename` can be None, filepath or list of filepaths - it is only used for logging.

    If warn_on_none_level is None (or lower than the logging level) message for falling through to
        a `None` default will be suppressed.
    '''
    try:
        return config_obj.get(section, param)
    except:
        if (default is None) and warn_on_none_level is not None:
            _warn_missing_setting(section, param, config_filename, warn_on_none_level)
        return default

def _warn_missing_setting(section, param, config_filename, warn_on_none_level=logging.WARN):
    if warn_on_none_level is None:
        return
    _ulog = _get_util_logger()
    if (_ulog is not None) and _ulog.isEnabledFor(warn_on_none_level):
        if config_filename:
            if not is_str_type(config_filename):
                f = ' "{}" '.format('", "'.join(config_filename))
            else:
                f = ' "{}" '.format(config_filename)
        else:
            f = ' '
        mf = 'Config file{f}does not contain option "{o}"" in section "{s}"'
        msg = mf.format(f=f, o=param, s=section)
        _ulog.warn(msg)

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
        '''If `raw_config_obj` is None, the default peyotl cascade for finding a configuration
        file will be used. overrides is a 2-level dictionary of section/param entries that will
        be used instead of the setting.
        The two default dicts will be used if the setting is not in overrides or the config object.
        "dominant" and "fallback" refer to whether the rank higher or lower than the default
        value in a get.*setting.*() call
        '''
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
    def get_from_config_setting_cascade(self, sec_param_list, default=None, warn_on_none_level=logging.WARN):
        '''return the first non-None setting from a series where each
        element in `sec_param_list` is a section, param pair suitable for
        a get_config_setting call.

        Note that non-None values for overrides or dominant_defaults will cause
            this call to only evaluate the first element in the cascade.
        '''
        for section, param in sec_param_list:
            r = self.get_config_setting(section, param, default=None, warn_on_none_level=None)
            if r is not None:
                return r
        section, param = sec_param_list[-1]
        if default is None:
            _warn_missing_setting(section, param, self._config_filename, warn_on_none_level)
        return default
    def _assure_raw(self):
        if self._raw is None:
            self._raw = get_config(None, None)
            self._config_filename = _CONFIG_FN
    def get_config_setting(self, section, param, default=None, warn_on_none_level=logging.WARN):
        if section in self._override:
            so = self._override[section]
            if param in so:
                return so[param]
        self._assure_raw()
        if section in self._dominant_defaults:
            so = self._dominant_defaults[section]
            if param in so:
                return get_config_setting(self._raw,
                                          section,
                                          param,
                                          default=so[param],
                                          config_filename=self._config_filename,
                                          warn_on_none_level=warn_on_none_level)
        if default is None:
            if section in self._fallback_defaults:
                default = self._dominant_defaults[section].get(param)
        return get_config_setting(self._raw,
                                  section,
                                  param,
                                  default=default,
                                  config_filename=self._config_filename,
                                  warn_on_none_level=warn_on_none_level)
    def report(self, out):
        self._assure_raw()
        out.write('Config read from "{f}"\n'.format(f=self._config_filename))
        from_raw = _do_create_overrides_from_config(self._raw)
        k = set(self._override.keys())
        k.update(from_raw.keys())
        k = list(k)
        k.sort()
        for key in k:
            ov_set = self._override.get(key, {})
            fr_set = from_raw.get(key, {})
            v = set(ov_set.keys())
            v.update(fr_set.keys())
            v = list(v)
            v.sort()
            out.write('[{s}]\n'.format(s=key))
            for param in v:
                if param in ov_set:
                    out.write('#{p} from override\n{p} = {s}\n'.format(p=param, s=str(ov_set[param])))
                else:
                    out.write('#{p} from {f}\n{p} = {s}\n' .format(p=param,
                                                                   s=str(fr_set[param]),
                                                                   f=self._config_filename))

def create_overrides_from_config(config, config_filename):
    '''Returns a dictionary of all of the settings in a config file. the
    returned dict is appropriate for use as the overrides arg for a ConfigWrapper.__init__() call.
    '''
    if _READING_LOGGING_CONF:
        read_logging_config()
    _get_util_logger().debug('creating override dict from ' + config_filename)
    return _do_create_overrides_from_config(config)

def _do_create_overrides_from_config(config):
    d = {}
    for s in config.sections():
        d[s] = {}
        for opt in config.options(s):
            d[s][opt] = config.get(s, opt)
    return d

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
get_config_var = get_config

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
def get_unique_filepath(stem):
    '''NOT thread-safe!
    return stems or stem# where # is the smallest
    positive integer for which the path does not exist.
    useful for temp dirs where the client code wants an
    obvious ordering.
    '''
    fp = stem
    if os.path.exists(stem):
        n = 1
        fp = stem + str(n)
        while os.path.exists(fp):
            n += 1
            fp = stem + str(n)
    return fp




def get_test_config(overrides=None):
    '''Returns a config object with the settings in current working directory file "test.conf" overriding
    the peyotl configuration, and the settings in the `overrides` dict
    having the highest priority.
    '''
    try:
        from ConfigParser import SafeConfigParser
    except ImportError:
        from configparser import ConfigParser as SafeConfigParser #pylint: disable=F0401
    _CONFIG_FN = os.path.abspath('test.conf')
    _CONFIG = SafeConfigParser()
    _CONFIG.read(_CONFIG_FN)
    d = create_overrides_from_config(_CONFIG, _CONFIG_FN)
    if overrides is not None:
        d.update(overrides)
    return ConfigWrapper(None, overrides=d)
