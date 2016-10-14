#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functions for interacting with a runtime-configuration.
Typical usage:
    setting = get_config_setting('phylesystem', 'parent', default=None)
Or:
    cfg = get_config_object()
    setting = cfg.get_config_setting('phylesystem', 'parent', default=None)
The latter is more efficient, if you have several settings to check. The former is just sugar for the latter.

The returned `cfg` from get_config_object is a singleton, immutable ConfigWrapper instance. It is populated based
on peyotl's system of finding configuration file locations (see below)
Returned settings are always strings (no type coercion is supported)


The ConfigWrapper class also has a
    setting = cfg.get_from_config_setting_cascade([('apis', 'oti_raw_urls'), ('apis', 'raw_urls')], "FALSE")
syntax to allow client code to check one section+param name after another


It is possible to override settings by creating your own ConfigWrapper instance and using the overrides argument to the
__init__ call, but that is mainly useful for Mock configurations used in testing.

The function `read_config` is an alias for `get_raw_default_config_and_read_file_list` both should be treated as
deprecated.

# Peyotl config file finding/ Env variables.
The default peyotl configuration is read from a file. The configuration filepath is either the value of
    the PEYOTL_CONFIG_FILE environmental variable (if that variable is defined) or ~/.peyotl/config
If that filepath does not exist, then the fallback is the config that is the `default.conf` file that is
    packaged with peyotl.
get_raw_default_config_and_read_file_list() is the accessor for the raw ConfigParser object and list of files
    that were used to populate that file.

This file has some odd acrobatics to deal with the fact that logging is (1) helpful for diagnosing configuration errors
    and (2) itself dependent on configuration-based settings. So this file imports some private functions of the
    peyotl.utility.get_logger file. Those acrobatics should not be needed for any other client of logger or config
    functions in peyotl.

A few settings can also be set using environmental variables (mainly the logging settings discussed in
peyotl.utility.get_logger). If the environmental variable is present it will override the setting from the configuration
file.

If you want to check your configuration, you can run:

    python scripts/clipeyotl.py config -a list

to see the union of all your settings along with comments describing where those settings come from (e.g. which
are from your environment).

"""
import threading
import logging
import os


_CONFIG = None
_CONFIG_FN = None
_READ_DEFAULT_FILES = None
_DEFAULT_CONFIG_WRAPPER = None
_DEFAULT_CONFIG_WRAPPER_LOCK = threading.Lock()
_CONFIG_FN_LOCK = threading.Lock()
_CONFIG_LOCK = threading.Lock()


def _replace_default_config(cfg):
    """Only to be used internally for testing !
    """
    global _CONFIG
    _CONFIG = cfg


def get_default_config_filename():
    """Returns the configuration filepath.

    If PEYOTL_CONFIG_FILE is in the env that is the preferred choice; otherwise ~/.peyotl/config is preferred.
    If the preferred file does not exist, then the packaged peyotl/default.conf from the installation of peyotl is
    used.
    A RuntimeError is raised if that fails.
    """
    global _CONFIG_FN
    if _CONFIG_FN is not None:
        return _CONFIG_FN
    with _CONFIG_FN_LOCK:
        if _CONFIG_FN is not None:
            return _CONFIG_FN
        if 'PEYOTL_CONFIG_FILE' in os.environ:
            cfn = os.path.abspath(os.environ['PEYOTL_CONFIG_FILE'])
        else:
            cfn = os.path.expanduser("~/.peyotl/config")
        if not os.path.isfile(cfn):
            # noinspection PyProtectedMember
            if 'PEYOTL_CONFIG_FILE' in os.environ:
                from peyotl.utility.get_logger import warn_from_util_logger
                msg = 'Filepath "{}" specified via PEYOTL_CONFIG_FILE={} was not found'.format(cfn, os.environ[
                    'PEYOTL_CONFIG_FILE'])
                warn_from_util_logger(msg)
            from pkg_resources import Requirement, resource_filename
            pr = Requirement.parse('peyotl')
            cfn = resource_filename(pr, 'peyotl/default.conf')
        if not os.path.isfile(cfn):
            raise RuntimeError('The peyotl configuration file cascade failed looking for "{}"'.format(cfn))
        _CONFIG_FN = os.path.abspath(cfn)
    return _CONFIG_FN


def get_raw_default_config_and_read_file_list():
    """Returns a ConfigParser object and a list of filenames that were parsed to initialize it"""
    global _CONFIG, _READ_DEFAULT_FILES
    if _CONFIG is not None:
        return _CONFIG, _READ_DEFAULT_FILES
    with _CONFIG_LOCK:
        if _CONFIG is not None:
            return _CONFIG, _READ_DEFAULT_FILES
        try:
            # noinspection PyCompatibility
            from ConfigParser import SafeConfigParser
        except ImportError:
            # noinspection PyCompatibility,PyUnresolvedReferences
            from configparser import ConfigParser as SafeConfigParser  # pylint: disable=F0401
        cfg = SafeConfigParser()
        read_files = cfg.read(get_default_config_filename())
        _CONFIG, _READ_DEFAULT_FILES = cfg, read_files
        return _CONFIG, _READ_DEFAULT_FILES


# Alias the correct function name to our old alias @TODO Deprecate when phylesystem-api calls the right function
read_config = get_raw_default_config_and_read_file_list


def _warn_missing_setting(section, param, config_filename, warn_on_none_level=logging.WARN):
    if warn_on_none_level is None:
        return
    # noinspection PyProtectedMember
    from peyotl.utility.get_logger import warn_from_util_logger
    from peyotl.utility.str_util import is_str_type
    if config_filename:
        if not is_str_type(config_filename):
            f = ' "{}" '.format('", "'.join(config_filename))
        else:
            f = ' "{}" '.format(config_filename)
    else:
        f = ' '
    mf = 'Config file {f} does not contain option "{o}"" in section "{s}"'
    msg = mf.format(f=f, o=param, s=section)
    warn_from_util_logger(msg)


def _raw_config_setting(config_obj, section, param, default=None, config_filename='', warn_on_none_level=logging.WARN):
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


class ConfigWrapper(object):
    """Wrapper to provide a richer get_config_setting(section, param, d) behavior. That function will
    return a value from the following cascade:
        1. override[section][param] if section and param are in the resp. dicts
        2. the value in the config obj for section/param if that setting is in the config
    Must be treated as immutable!
    """

    def __init__(self,
                 raw_config_obj=None,
                 config_filename='<programmatically configured>',
                 overrides=None):
        """If `raw_config_obj` is None, the default peyotl cascade for finding a configuration
        file will be used. overrides is a 2-level dictionary of section/param entries that will
        be used instead of the setting.
        The two default dicts will be used if the setting is not in overrides or the config object.
        "dominant" and "fallback" refer to whether the rank higher or lower than the default
        value in a get.*setting.*() call
        """
        # noinspection PyProtectedMember
        from peyotl.utility.get_logger import _logging_env_conf_overrides
        self._config_filename = config_filename
        self._raw = raw_config_obj
        if overrides is None:
            overrides = {}
        leco = _logging_env_conf_overrides()
        if leco:
            for k, v in leco['logging'].items():
                if k in overrides.setdefault('logging', {}):
                    # noinspection PyProtectedMember
                    from peyotl.utility.get_logger import warn_from_util_logger
                    m = 'Override keys ["logging"]["{}"] was overruled by an environmental variable'.format(k)
                    warn_from_util_logger(m)
                overrides['logging'][k] = v
        self._override = overrides

    @property
    def config_filename(self):
        self._assure_raw()
        return self._config_filename

    @property
    def raw(self):
        self._assure_raw()
        return self._raw

    def get_from_config_setting_cascade(self, sec_param_list, default=None, warn_on_none_level=logging.WARN):
        """return the first non-None setting from a series where each
        element in `sec_param_list` is a section, param pair suitable for
        a get_config_setting call.

        Note that non-None values for overrides for this ConfigWrapper instance will cause
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
            cfg, fllist = get_raw_default_config_and_read_file_list()
            self._raw = cfg
            assert len(fllist) == 1
            self._config_filename = fllist[0]

    def get_config_setting(self, section, param, default=None, warn_on_none_level=logging.WARN):
        if section in self._override:
            so = self._override[section]
            if param in so:
                return so[param]
        self._assure_raw()
        return _raw_config_setting(self._raw,
                                   section,
                                   param,
                                   default=default,
                                   config_filename=self._config_filename,
                                   warn_on_none_level=warn_on_none_level)

    def report(self, out):
        # noinspection PyProtectedMember
        from peyotl.utility.get_logger import _logging_env_conf_overrides
        cfn = self.config_filename
        out.write('# Config read from "{f}"\n'.format(f=cfn))
        cfenv = os.environ.get('PEYOTL_CONFIG_FILE', '')
        if cfenv:
            if os.path.abspath(cfenv) == cfn:
                emsg = '#  config filepath obtained from $PEYOTL_CONFIG_FILE env var.\n'
            else:
                emsg = '#  using packaged default. The filepath from PEYOTL_CONFIG_FILE env. var. did not exist.\n'
        else:
            cfhome = os.path.expanduser("~/.peyotl/config")
            if os.path.abspath(cfhome) == cfn:
                emsg = "#  config filepath obtained via ~/.peyotl/config convention.\n"
            else:
                emsg = '#  using packaged default. PEYOTL_CONFIG_FILE was not set and ~/.peyotl/config was not found.\n'
        out.write(emsg)
        from_raw = _create_overrides_from_config(self._raw)
        k = set(self._override.keys())
        k.update(from_raw.keys())
        k = list(k)
        k.sort()
        env_log_warnings = []
        leco = _logging_env_conf_overrides(log_init_warnings=env_log_warnings)
        for w in env_log_warnings:
            out.write('# Log config warning: {}\n'.format(w))
        lecologging = leco.get('logging', {})
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
                    if key == 'logging' and param in lecologging:
                        out.write('# {p} from env. variable\n{p} = {s}\n'.format(p=param, s=str(ov_set[param])))
                    else:
                        out.write('# {p} from override\n{p} = {s}\n'.format(p=param, s=str(ov_set[param])))
                else:
                    out.write('# {p} from {f}\n{p} = {s}\n'.format(p=param,
                                                                   s=str(fr_set[param]),
                                                                   f=self._config_filename))


def _create_overrides_from_config(config):
    """Creates a two-level dictionary of d[section][option] from a config parser object."""
    d = {}
    for s in config.sections():
        d[s] = {}
        for opt in config.options(s):
            d[s][opt] = config.get(s, opt)
    return d


def get_config_setting(section, param, default=None):
    """
    """
    cfg = get_config_object()
    return cfg.get_config_setting(section, param, default=default)


def get_config_object():
    """Thread-safe accessor for the immutable default ConfigWrapper object"""
    global _DEFAULT_CONFIG_WRAPPER
    if _DEFAULT_CONFIG_WRAPPER is not None:
        return _DEFAULT_CONFIG_WRAPPER
    with _DEFAULT_CONFIG_WRAPPER_LOCK:
        if _DEFAULT_CONFIG_WRAPPER is not None:
            return _DEFAULT_CONFIG_WRAPPER
        _DEFAULT_CONFIG_WRAPPER = ConfigWrapper()
        return _DEFAULT_CONFIG_WRAPPER


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
    d = _create_overrides_from_config(_test_conf)
    if overrides is not None:
        d.update(overrides)
    return ConfigWrapper(None, overrides=d)
