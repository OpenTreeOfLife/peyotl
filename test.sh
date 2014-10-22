#!/bin/sh
pip install -r requirements.txt || exit 1
python setup.py develop || exit 1
python setup.py test || exit 1

