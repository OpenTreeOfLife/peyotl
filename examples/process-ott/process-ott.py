#!/usr/bin/env python
"""Reads OTT files and produces a set of files with preorder
numbering that allow of minimal memory footprint in python scripts

Note: this script is a memory hog
"""

if __name__ == '__main__':
    from peyotl.ott import OTT
    ott = OTT()
    ott.create_pickle_files()

