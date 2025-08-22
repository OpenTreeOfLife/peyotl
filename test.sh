#!/bin/sh
pip install -r requirements.txt || exit 1
pip install -e . || exit 1
pytest .|| exit 1

