#! /bin/sh
rm -rfv $(find . -name "*.pyc")
rm -rfv 'pyotree/test/output/'*
rm -rfv 'pyotree/test/coverage/'*
rm -rfv build
rm -rfv dist
