#!/bin/sh
if test $(grep version setup.py | wc -l) -gt 1
then
    echo found version too many times in setup.py
    exit 1
fi
version=$(grep version setup.py | sed -E "s/.*version='(.*)'.*/\\1/")
if test -z ${version}
then
    echo grepping out the version failed
    exit 1
fi

echo posting version ${version}

set -x
python setup.py register -r pypi || exit
python setup.py sdist upload -r pypi || exit
git commit -m "bump of version to $version" setup.py || exit
git tag ${version}
git push origin

set +x
echo remember to log in to GitHub and tag this as a release to keep GH and PyPI in sync!


