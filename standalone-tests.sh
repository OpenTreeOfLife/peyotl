#!/bin/sh
stf=0
if ! python standalone_tests/test_caching.py
then
    stf=$(expr $stf + 1)
fi

sh dev/refresh_for_git_tests.sh
if ! python standalone_tests/test_git_workflows.py
then
    stf=$(expr $stf + 1)
fi

sh dev/refresh_for_git_tests.sh
if ! python standalone_tests/test_phylesystem_mirror.py
then
    stf=$(expr $stf + 1)
fi
cd peyotl/test/data/mini_par/mirror/mini_phyl
git push -f GitHubRemote aa8964b55bfa930a91af7a436f55f0acdc94b918:master
cd -

if test $stf -gt 0
then
    echo "Failed at least one standalone_test."
    exit $stf
else
    echo "Passed all standalone_tests passed."
fi
