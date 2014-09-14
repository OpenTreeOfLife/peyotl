#!/usr/bin/env python
from peyotl.api import APIWrapper
taxo = APIWrapper().taxomachine
print taxo.valid_contexts
