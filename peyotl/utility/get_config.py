#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os

_CONFIG = None
_CONFIG_FN = None


def _replace_default_config(cfg):
    """Only to be used internally for testing !
    """
    global _CONFIG
    _CONFIG = cfg


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
    try:
        # noinspection PyCompatibility
        from ConfigParser import SafeConfigParser
    except ImportError:
        # noinspection PyCompatibility,PyUnresolvedReferences
        from configparser import ConfigParser as SafeConfigParser  # pylint: disable=F0401
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


def _get_config_or_none():
    """Returns the config object using the standard cascade, or the None config object if there is an exception.
    """
    # noinspection PyBroadException
    try:
        return read_config()[0]
    except:
        return None


def get_config_setting(config_obj, section, param, default=None, config_filename='', warn_on_none_level=logging.WARN):
    """Read (section, param) from `config_obj`. If not found, return `default`

    If the setting is not found and `default` is None, then an warn-level message is logged.
    `config_filename` can be None, filepath or list of filepaths - it is only used for logging.

    If warn_on_none_level is None (or lower than the logging level) message for falling through to
        a `None` default will be suppressed.
    """
    # noinspection PyBroadException
    try:
        return config_obj.get(section, param)
    except:
        if (default is None) and warn_on_none_level is not None:
            _warn_missing_setting(section, param, config_filename, warn_on_none_level)
        return default


def _warn_missing_setting(section, param, config_filename, warn_on_none_level=logging.WARN):
    if warn_on_none_level is None:
        return
    from peyotl.utility.get_logger import get_util_logger
    from peyotl.utility.str_util import is_str_type
    _ulog = get_util_logger()
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
    """Wrapper to provide a richer get_config_setting(section, param, d) behavior. That function will
    return a value from the following cascade:
        1. override[section][param] if section and param are in the resp. dicts
        2. the value in the config obj for section/param it that setting is in the config
        3. dominant_defaults[section][param] if section and param are in the resp. dicts
        4. the `default` arg of the get_config_setting call
        5. fallback_defaults[section][param] if section and param are in the resp. dicts
    """

    def __init__(self,
                 raw_config_obj=None,
                 config_filename='<programmatically configured>',
                 overrides=None,
                 dominant_defaults=None,
                 fallback_defaults=None):
        """If `raw_config_obj` is None, the default peyotl cascade for finding a configuration
        file will be used. overrides is a 2-level dictionary of section/param entries that will
        be used instead of the setting.
        The two default dicts will be used if the setting is not in overrides or the config object.
        "dominant" and "fallback" refer to whether the rank higher or lower than the default
        value in a get.*setting.*() call
        """
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
        """return the first non-None setting from a series where each
        element in `sec_param_list` is a section, param pair suitable for
        a get_config_setting call.

        Note that non-None values for overrides or dominant_defaults will cause
            this call to only evaluate the first element in the cascade.
        """
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
            self._raw = _get_config_or_none()
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
                    out.write('#{p} from {f}\n{p} = {s}\n'.format(p=param,
                                                                  s=str(fr_set[param]),
                                                                  f=self._config_filename))


def create_overrides_from_config(config):
    """Returns a dictionary of all of the settings in a config file. the
    returned dict is appropriate for use as the overrides arg for a ConfigWrapper.__init__() call.
    """
    from peyotl.utility.get_logger import read_logging_config
    read_logging_config()
    return _do_create_overrides_from_config(config)


def _do_create_overrides_from_config(config):
    d = {}
    for s in config.sections():
        d[s] = {}
        for opt in config.options(s):
            d[s][opt] = config.get(s, opt)
    return d


def get_config_setting_kwargs(config_obj, section, param, default=None, **kwargs):
    """Used to provide a consistent kwargs behavior for classes/methods that need to be config-dependent.

    Currently: if config_obj is None, then kwargs['config'] is checked. If it is also None
        then a default ConfigWrapper object is created.
    """
    cfg = get_config_object(config_obj, **kwargs)
    return cfg.get_config_setting(section, param, default)


def get_config_object(config_obj, **kwargs):
    if config_obj is not None:
        return config_obj
    c = kwargs.get('config')
    if c is None:
        _c = ConfigWrapper()
        return _c
    return c


def get_test_config(overrides=None):
    """Returns a config object with the settings in current working directory file "test.conf" overriding
    the peyotl configuration, and the settings in the `overrides` dict
    having the highest priority.
    """
    try:
        # noinspection PyCompatibility
        from ConfigParser import SafeConfigParser
    except ImportError:
        # noinspection PyCompatibility,PyUnresolvedReferences
        from configparser import ConfigParser as SafeConfigParser  # pylint: disable=F0401
    _test_conf_fn = os.path.abspath('test.conf')
    _test_conf = SafeConfigParser()
    _test_conf.read(_test_conf_fn)
    d = create_overrides_from_config(_test_conf)
    if overrides is not None:
        d.update(overrides)
    return ConfigWrapper(None, overrides=d)
