#!/bin/bash
source tests/bash-test-helpers.bash || exit
demand_at_top_level || exit

if ! test -d peyotl/test/data/mini_par/mini_illustrations
then
    echo "skipping tests against local illustrations due to lack of mini_illustrations (this is normal if you are not a peyotl maintainer)"
    exit 0
fi
echo "Running tests of the local (mini) illustrations system"
num_fails=0
num_checks=0
refresh_and_test_local_git tests/local_repos_tests/test_illustrations.py
refresh_and_test_local_git tests/local_repos_tests/test_illustrations_api.py
exit ${num_fails}
