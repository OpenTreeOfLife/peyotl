#!/bin/sh
for d in phylesystem-api opentree/curator opentree/webapp opentree-testrunner
do
    find ../$d -name "*py" -exec grep  'peyotl' {} \; > .tmp.output.find_ext
    echo $d
    cat .tmp.output.find_ext | \
         sed -E 's/\s*from peyotl\.([a-z_A-Z]+)[. ].*/ \1/' | \
         sed -E '/import/d' | \
         sed -E '/peyotl/d' | \
         sort | uniq
    rm .tmp.output.find_ext
done
