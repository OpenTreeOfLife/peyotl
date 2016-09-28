#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import logging
import os

_LOG = None
_LOGGING_CONF = None
_LOGGING_ENV_CONF_OVERRIDES = None
_LOGGING_CONF_LOCK = threading.Lock()
_LOGGING_ENV_CONF_OVERRIDES_LOCK = threading.Lock()


def _get_logging_level(s=None):
    # Called from within locks, so this should not log or trigger reading of logging configuration!
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
    # Called from within locks, so this should not log or trigger reading of logging configuration!
    if s is None:
        s = 'NONE'
    else:
        s = s.upper()
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


def get_logger(name="peyotl"):
    """Returns a logger with name set as given. See _read_logging_config for a description of the env var/config
    file cascade that controls configuration of the logger.
    """
    logger = logging.getLogger(name)
    if len(logger.handlers) == 0:
        lc = _read_logging_config()
        logger.setLevel(lc['level'])
        if lc['filepath'] is not None:
            log_dir = lc['log_dir']
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
    """Only to be used in this file and peyotl.utility.get_config"""
    global _LOG
    if _LOG is not None:
        return _LOG
    # This check is necessary to avoid infinite recursion when called from get_config, because
    #   the _read_logging_conf can require reading a conf file.
    if _LOGGING_CONF is None:
        return None
    _LOG = get_logger("peyotl.utility")
    return _LOG


def _logging_env_conf_overrides():
    """Returns a dictionary that is empty or has a "logging" key that refers to
    the (up to 3) key-value pairs that pertain to logging and are read from the env.
    This is mainly a convenience function for ConfigWrapper so that it can accurately
        report the source of the logging settings without
    """
    # This is called from a locked section of _read_logging_config, so don't call that function or you'll get deadlock
    global _LOGGING_ENV_CONF_OVERRIDES
    if _LOGGING_ENV_CONF_OVERRIDES is not None:
        return _LOGGING_ENV_CONF_OVERRIDES
    with _LOGGING_ENV_CONF_OVERRIDES_LOCK:
        if _LOGGING_ENV_CONF_OVERRIDES is not None:
            return _LOGGING_ENV_CONF_OVERRIDES
        level_from_env = os.environ.get("PEYOTL_LOGGING_LEVEL")
        format_from_env = os.environ.get("PEYOTL_LOGGING_FORMAT")
        log_file_path_from_env = os.environ.get("PEYOTL_LOG_FILE_PATH")
        _LOGGING_ENV_CONF_OVERRIDES = {}
        if level_from_env:
            _LOGGING_ENV_CONF_OVERRIDES.setdefault("logging", {})['level'] = level_from_env
        if format_from_env:
            _LOGGING_ENV_CONF_OVERRIDES.setdefault("logging", {})['formatter'] = format_from_env
        if log_file_path_from_env:
            _LOGGING_ENV_CONF_OVERRIDES.setdefault("logging", {})['filepath'] = log_file_path_from_env
        return _LOGGING_ENV_CONF_OVERRIDES


def _read_logging_config():
    """Returns a dictionary (should be treated as immutable) of settings needed to configure a logger.
    If PEYOTL_LOGGING_LEVEL, PEYOTL_LOGGING_FORMAT, and PEYOTL_LOG_FILE_PATH are all in the env, then
        no config file will be read.
    Otherwise the config will be read, and any of those env vars that are present will then override
        the settings from the config file.
    Crucial keys-value pairs are:
    'level' -> logging.level as returned by _get_logging_level from the string obtained from PEYOTL_LOGGING_LEVEL
        or config.logging.level
    'formatter' -> None or a logging.Formatter as returned by _get_logging_format from the string obtained from
        PEYOTL_LOGGING_FORMAT or config.logging.formatter
    'filepath' -> None (for StreamHandler) or a filepath
    'log_dir' -> None or the parent of the 'filepath' key
    """
    global _LOGGING_CONF
    from peyotl.utility.get_config import get_config_object
    if _LOGGING_CONF is not None:
        return _LOGGING_CONF
    with _LOGGING_CONF_LOCK:
        if _LOGGING_CONF is not None:
            return _LOGGING_CONF
        leco = _logging_env_conf_overrides().get('logging', {})
        _LOGGING_CONF = {}
        # These strings hold the names of env variables that control LOGGING. If LEVEL is defined via the environment
        #   the the
        level_from_env = leco.get("level")
        format_from_env = leco.get("format")
        log_file_path_from_env = leco.get("filepath")
        if not (level_from_env and format_from_env and log_file_path_from_env):
            # If any aspect is missing from the env, then we need to check the config file
            cfg = get_config_object()
            level = cfg.get_config_setting('logging', 'level', 'WARNING', warn_on_none_level=None)
            logging_format_name = cfg.get_config_setting('logging', 'formatter', 'NONE', warn_on_none_level=None)
            logging_filepath = cfg.get_config_setting('logging', 'filepath', '', warn_on_none_level=None)
            if logging_filepath == '':
                logging_filepath = None
            _LOGGING_CONF['level_name'] = level
            _LOGGING_CONF['formatter_name'] = logging_format_name
            _LOGGING_CONF['filepath'] = logging_filepath
        # Override
        if level_from_env:
            _LOGGING_CONF['level_name'] = level_from_env
        if format_from_env:
            _LOGGING_CONF['formatter_name'] = format_from_env
        if log_file_path_from_env:
            _LOGGING_CONF['filepath'] = log_file_path_from_env
        fp = _LOGGING_CONF['filepath']
        if not fp:
            _LOGGING_CONF['filepath'] = None
        _LOGGING_CONF['log_dir'] = os.path.split(fp)[0] if fp else None
        _LOGGING_CONF['level'] = _get_logging_level(_LOGGING_CONF['level_name'])
        _LOGGING_CONF['formatter'] = _get_logging_formatter(_LOGGING_CONF['formatter_name'])
        return _LOGGING_CONF
