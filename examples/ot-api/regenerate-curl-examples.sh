#!/bin/sh
if ! test -d "$OPEN_TREE_REPO_ROOT/opentree.wiki"
then
    echo 'expecting $OPEN_TREE_REPO_ROOT/opentree.wiki to exist (git clone of the opentree wiki)'
    exit 1
fi
grep '^ *\$ curl' $OPEN_TREE_REPO_ROOT/opentree.wiki/Open-Tree-of-Life-APIs.md \
      | sed -E 's/^ *\$ *//' \
      | sed -E 's/\/([-a-z_A-Z0-9]+)( |$)/\/\1 -o \1.json /' \
      | sed -E 's/\/([-a-z_A-Z0-9]+)( |$)(.*)$/\/\1 \3  -s || echo "\1 failed"/' > with-curl.sh
