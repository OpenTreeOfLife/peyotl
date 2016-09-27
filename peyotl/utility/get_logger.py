#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import os

_LOG = None
_LOGGING_CONF = None


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
    """Returns a logger with name set as given, and configured
    to the level given by the environment variable _LOGGING_LEVEL_ENVAR.
    """
    logger = logging.getLogger(name)
    if len(logger.handlers) == 0:
        lc = read_logging_config()
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


def get_util_logger():
    global _LOG
    if _LOG is not None:
        return _LOG
    if _LOGGING_CONF is None:
        return None
    _LOG = get_logger("peyotl.utility")
    return _LOG


def read_logging_config():
    global _LOGGING_CONF
    from peyotl.utility.get_config import get_config_object
    if _LOGGING_CONF is not None:
        return _LOGGING_CONF
    _LOGGING_CONF = {}
    # These strings hold the names of env variables that control LOGGING. If LEVEL is defined via the environment
    #   the the
    level_from_env = os.environ.get("PEYOTL_LOGGING_LEVEL")
    format_from_env = os.environ.get("PEYOTL_LOGGING_FORMAT")
    log_file_path_from_env = os.environ.get("PEYOTL_LOG_FILE_PATH")
    if not (level_from_env and format_from_env and log_file_path_from_env):
        # If any aspect is missing from the env, then we need to check the config file
        cfg = get_config_object(None)
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
    _LOGGING_CONF['log_dir'] = os.path.split(fp)[0] if fp else None
    _LOGGING_CONF['level'] = _get_logging_level(_LOGGING_CONF['level_name'])
    _LOGGING_CONF['formatter'] = _get_logging_formatter(_LOGGING_CONF['formatter_name'])
    return _LOGGING_CONF
