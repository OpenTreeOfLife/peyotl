#!/bin/bash
# This is a set of tests that use Open Tree web services (or external web services, such as TreeBASE).
# They are useful for testing peyotl's interactions with those services, but they can fail for server
#   or network reasons even if your local copy of peyotl is fine.
source tests/bash-test-helpers.bash || exit
demand_at_top_level || exit
if test -z $RUN_WEB_SERVICE_TESTS
then
    echo 'RUN_WEB_SERVICE_TESTS must be in your environment if you want to run the web-service requiring tests'
    exit 0
fi
num_checks=0
num_fails=0
echo_and_demand_succeeds python tests/ws_tests/read_only/test_phylesystem_api.py
echo_and_demand_succeeds python tests/ws_tests/read_only/test_amendments_api.py
echo_and_demand_succeeds python tests/ws_tests/read_only/test_collections_api.py
echo_and_demand_succeeds python tests/ws_tests/read_only/test_oti.py
echo_and_demand_succeeds python tests/ws_tests/read_only/test_shared_api_tests.py
echo_and_demand_succeeds python tests/ws_tests/read_only/test_taxomachine.py
echo_and_demand_succeeds python tests/ws_tests/read_only/test_treebase_import.py
echo_and_demand_succeeds python tests/ws_tests/read_only/test_treemachine.py
echo_and_demand_succeeds python tests/ws_tests/read_only/test_v2facade.py
stf=0
if test ${num_fails} -gt 0
then
    num_passed=$(expr $num_checks - $num_fails)
    echo "passed ${num_passed} out of ${num_checks} web service tests"
else
    echo "passed ${num_checks} out of ${num_checks} web service tests"
fi
exit ${num_fails}