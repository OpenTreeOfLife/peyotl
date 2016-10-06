#!/bin/bash
source tests/bash-test-helpers.bash || exit
demand_at_top_level || exit

if ! test -d peyotl/test/data/mini_par/mini_phyl
then
    echo "skipping tests against local phylesystem due to lack of mini_phyl (this is normal if you are not a peyotl maintainer)"
    exit 0
fi
if ! test -d peyotl/test/data/mini_par/mini_system
then
    echo "skipping tests against local phylesystem due to lack of mini_system (this is normal if you are not a peyotl maintainer)"
    exit 0
fi
echo "Running tests of the local (mini) phylesystem"


num_fails=0
num_checks=0
refresh_and_test_local_git tests/local_repos_tests/test_caching.py
refresh_and_test_local_git tests/local_repos_tests/test_git_workflows.py
refresh_and_test_local_git tests/local_repos_tests/test_study_del.py
refresh_and_test_local_git tests/local_repos_tests/test_git_workflows.py tiny_max_file_size
refresh_and_test_local_git tests/local_repos_tests/test_phylesystem_api.py
refresh_and_test_local_git tests/local_repos_tests/test_phylesystem_mirror.py

# This resets the head on the remote. A dangerous operation, but this is just a testing repo.
cd peyotl/test/data/mini_par/mirror/mini_phyl
git push -f GitHubRemote 2d59ab892ddb3d09d4b18c91470b8c1c4cca86dc:master
cd - >/dev/null 2>&1

exit ${num_fails}
