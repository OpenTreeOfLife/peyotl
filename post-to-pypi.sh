#!/bin/sh
if test $(grep version setup.py | wc -l) -gt 1
then
    echo found version too many times in setup.py
    exit 1
fi
version=$(grep version setup.py | sed -E "s/.*version='(.*)'.*/\\1/")
echo posting version $version
set -x
echo python setup.py register -r pypi || exit
echo python setup.py sdist upload -r pypi || exit
echo git commit -m "bump of version to $version" setup.py || exit
echo git tag $version
echo git push origin

echo remember to log in to GitHub and tag this as a release to keep GH and PyPI in sync!


