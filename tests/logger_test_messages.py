#!/usr/bin/env python
# -*- coding: utf-8 -*-
from peyotl import get_logger
_LOG = get_logger()
_LOG.debug("a debug message")
_LOG.info("an info with umlaut ü message")
_LOG.warning("a warning message")
_LOG.error("an error message")
_LOG.critical("a critical message")
try:
    raise RuntimeError("A testing runtime error")
except RuntimeError:
    _LOG.exception("expected exception")
