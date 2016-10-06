#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import logging
import sys
import os

_LOG = None
_LOGGING_CONF = None
_LOGGING_ENV_CONF_OVERRIDES = None
_LOGGING_CONF_LOCK = threading.Lock()
_LOGGING_ENV_CONF_OVERRIDES_LOCK = threading.Lock()


def _get_logging_level(s=None, warning_message_list=None):
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
        if warning_message_list is not None:
            warning_message_list.append('"{}" is an invalid logging level'.format(s))
        level = logging.NOTSET
    return level


def _get_logging_formatter(s=None, warning_message_list=None):
    # Called from within locks, so this should not log or trigger reading of logging configuration!
    if s is None:
        s = 'NONE'
    else:
        s = s.upper()
    if s == "RICH":
        logging_formatter = logging.Formatter("[%(asctime)s] %(filename)s (%(lineno)d): %(levelname) 8s: %(message)s")
    elif s == "SIMPLE":
        logging_formatter = logging.Formatter("%(levelname) 7s: %(message)s")
    elif s == "RAW":
        logging_formatter = logging.Formatter("%(message)s")
    else:
        if warning_message_list is not None:
            warning_message_list.append('"{}" is an invalid formatter name'.format(s))
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
        log_init_warnings = []
        lc = _read_logging_config(log_init_warnings)
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
        if log_init_warnings:
            for w in log_init_warnings:
                logger.warn(w)
    return logger


def warn_from_util_logger(msg):
    """Only to be used in this file and peyotl.utility.get_config"""
    global _LOG
    # This check is necessary to avoid infinite recursion when called from get_config, because
    #   the _read_logging_conf can require reading a conf file.
    if _LOG is None and _LOGGING_CONF is None:
        sys.stderr.write('WARNING: (from peyotl before logging is configured) {}\n'.format(msg))
        return
    if _LOG is None:
        _LOG = get_logger("peyotl.utility")
    _LOG.warn(msg)


def _logging_env_conf_overrides(log_init_warnings=None):
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
            env_w_list = []
            _get_logging_level(level_from_env, env_w_list)
            if len(env_w_list) > 0:
                if log_init_warnings is not None:
                    log_init_warnings.extend(env_w_list)
                    log_init_warnings.append('PEYOTL_LOGGING_LEVEL is invalid. Relying on setting from conf file.')
            else:
                _LOGGING_ENV_CONF_OVERRIDES.setdefault("logging", {})['level'] = level_from_env
        if format_from_env:
            env_w_list = []
            _get_logging_formatter(format_from_env, env_w_list)
            if len(env_w_list) > 0:
                if log_init_warnings is not None:
                    log_init_warnings.extend(env_w_list)
                    log_init_warnings.append('PEYOTL_LOGGING_FORMAT was invalid. Relying on setting from conf file.')
            else:
                _LOGGING_ENV_CONF_OVERRIDES.setdefault("logging", {})['formatter'] = format_from_env
        if log_file_path_from_env is not None:
            _LOGGING_ENV_CONF_OVERRIDES.setdefault("logging", {})['filepath'] = log_file_path_from_env
        return _LOGGING_ENV_CONF_OVERRIDES


def _read_logging_config(log_init_warnings=None):
    """Returns a dictionary (should be treated as immutable) of settings needed to configure a logger.
    If PEYOTL_LOGGING_LEVEL, PEYOTL_LOGGING_FORMAT, and PEYOTL_LOG_FILE_PATH are all in the env, then
        no config file will be read.
    If PEYOTL_LOG_FILE_PATH is set to an empty string, then stderr will be used.
    Otherwise the config will be read, and any of those env vars that are present will then override
        the settings from the config file.
    Crucial keys-value pairs are:
    'level' -> logging.level as returned by _get_logging_level from the string obtained from PEYOTL_LOGGING_LEVEL
        or config.logging.level
    'formatter' -> None or a logging.Formatter as returned by _get_logging_format from the string obtained from
        PEYOTL_LOGGING_FORMAT or config.logging.formatter
    'filepath' -> None (for StreamHandler) or a filepath
    'log_dir' -> None or the parent of the 'filepath' key

    If log_init_warnings is a list, warnings pertaining reading the logging configuration will be appended to
    the list.
    This call is cached via a private global, so log_init_warnings is only used on the first call to the function.
    """
    global _LOGGING_CONF
    from peyotl.utility.get_config import get_config_object
    if _LOGGING_CONF is not None:
        return _LOGGING_CONF
    try:
        with _LOGGING_CONF_LOCK:
            if _LOGGING_CONF is not None:
                return _LOGGING_CONF
            leco = _logging_env_conf_overrides(log_init_warnings).get('logging', {})
            lc = {}
            level_from_env = leco.get("level")
            format_from_env = leco.get("format")
            log_file_path_from_env = leco.get("filepath")
            level_enum = None
            formatter = None
            if not (level_from_env and format_from_env and log_file_path_from_env):
                # If any aspect is missing from the env, then we need to check the config file
                cfg = get_config_object()
                level = cfg.get_config_setting('logging', 'level', 'WARNING', warn_on_none_level=None)
                logging_format_name = cfg.get_config_setting('logging', 'formatter', 'NONE', warn_on_none_level=None)
                logging_filepath = cfg.get_config_setting('logging', 'filepath', '', warn_on_none_level=None)
                if logging_filepath == '':
                    logging_filepath = None
                lc['level_name'] = level
                level_enum = _get_logging_level(level, log_init_warnings)
                lc['formatter_name'] = logging_format_name
                formatter = _get_logging_formatter(logging_format_name, log_init_warnings)
                lc['filepath'] = logging_filepath
            # Override
            if level_from_env:
                lc['level_name'] = level_from_env
                level_enum = _get_logging_level(level_from_env)
            if format_from_env:
                lc['formatter_name'] = format_from_env
                formatter = _get_logging_formatter(format_from_env)
            if log_file_path_from_env is not None:
                lc['filepath'] = log_file_path_from_env
            fp = lc['filepath']
            if not fp:
                lc['filepath'] = None
            lc['log_dir'] = os.path.split(fp)[0] if fp else None
            lc['level'] = level_enum
            lc['formatter'] = formatter
            _LOGGING_CONF = lc
            return _LOGGING_CONF
    except Exception as x:
        sys.stderr.write('Exception in peyotl.utility.get_logger._read_logging_config: {}'.format(str(x)))
        raise
