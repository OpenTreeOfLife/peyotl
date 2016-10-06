#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Helper script for making sure that the configuration of the logger works. Called by test-logger.sh"""
from peyotl import get_config_setting
import sys
section, param = sys.argv[1:3]
x = get_config_setting(section, param)
if x is not None:
    sys.stdout.write('{}\n'.format(x))