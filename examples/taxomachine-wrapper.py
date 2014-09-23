#!/usr/bin/env python
from peyotl.api import APIWrapper
taxo = APIWrapper().taxomachine
print taxo.valid_contexts
print taxo.TNRS(['sorex montereyensis'], context_name='Mammals')
print taxo.TNRS(['sorex montereyensis'])
