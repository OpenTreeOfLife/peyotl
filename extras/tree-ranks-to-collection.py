#!/usr/bin/env python
from peyotl.collections import get_empty_collection
from peyotl.collections.validation import validate_collection
from peyotl import write_as_json
import sys
import requests
import json
import re

"""
Generate a proper tree collection (JSON) document from a tree-rank file in the
'synthesis_trees' repo:
  https://bitbucket.org/josephwb/synthesis_trees/src/af1ac691b18e53d64dea8635d1fb1e2597c225dc/Source_info/Tree_ranks/?at=master

These are .py files (organized in folders by synthesis release) that build a
ranked list of study+tree ids, which we can use to build, verify, and populate
a tree collection.

EXAMPLE $ sudo python tree-ranks-to-collection.py ~/opentree/synthesis_trees/Source_info/Tree_ranks/v3/safe_microbes.py > safe_microbes.json

"""
# running these .py files (not as __main__) creates a list 'studytreelist'
try:
    execfile( sys.argv[1] )
except IOError:
    print "Unable to load the tree-ranking file! Details:"
    raise
    #sys.exit()
except:
    pass

file_name = sys.argv[1].split('/')[-1]  # eg, 'things_with_wings.py'
list_name = file_name[:-3]              # eg, 'things_with_wings'
list_name = list_name.replace("_"," ")  # eg, 'things with wings'

# We'll use the OpenTree APIs to verify each tree's existence and build a
# sensible description for each tree.
singlePropertySearchForTrees_url = 'https://api.opentreeoflife.org/oti/v1/singlePropertySearchForTrees'

# make a new collection to hold this data
c = get_empty_collection()
# give sensible default properties to the new tree collection
# (is there a standard list of creator and contributors? or should this vary with cmd-line args?)
c['creator'] = {'login': 'josephwb', 'name': 'Joseph W. Brown'}
c['contributors'] = [{'login': 'blackrim', 'name': 'Stephen Smith'}]
c['name'] = u"Inputs to synthesis ({})".format(list_name);
# add a legible timestamp
import email
c['description'] = u"Generated by tree-ranks-to-collection.py on {d}".format(d=email.utils.formatdate(usegmt=True));

# now we turn our attention to the decision (tree) list
d = c['decisions']

# NOTE that this logic mirrors that in the 'curation-helpers.js' script of the curation webapp.
#  https://github.com/OpenTreeOfLife/opentree/blob/fa36b973aa8f881d5355add0477337c2441a31df/curator/static/js/curation-helpers.js#L5
def full_to_compact_reference(full_ref):
    if full_ref.strip() == "":
        return "(Untitled)"
    # capture the first valid year in the reference
    regex = re.compile('(?P<year>\d{4})')
    match = regex.search(full_ref)
    if match:
        compact_year = match.group('year') 
    else:
        compact_year = "[no year]" 
    # split on the year to get authors (before), and capture the first surname
    compact_primary_author = full_ref.split(compact_year)[0].split(',')[0]
    compact_ref = u"{a}, {y}".format(a=compact_primary_author, y=compact_year) # eg, "Smith, 1999"
    return compact_ref

assert full_to_compact_reference('\t \n') == "(Untitled)"
assert full_to_compact_reference('Smith, John A., S. Jones, et. al., 2004 etc. ad infinitum') == "Smith, 2004"
assert full_to_compact_reference('Jones, 2010') == "Jones, 2010"
assert full_to_compact_reference('Smith J., R. Jones, J. Schmidt, et. al., etc. ad infinitum') == "Smith J., [no year]"

# move data into the expected format
for tree_info in studytreelist:
    s = tree_info.split('_')
    study_id, tree_frag = '_'.join(s[:-1]), s[-1]
    # add standard prefix to tree IDs 
    # TODO: warn about (or handle) other tree-id conventions?
    tree_id = 'tree' + tree_frag

    # populate with current data by looking up each tree via APIs
    expected_id = u"{s}_{t}".format(s=study_id, t=tree_id)
    payload = {"property": "oti_tree_id",
               "value": expected_id,
               "exact": True,
               "verbose": True}
    headers = {'content-type': 'application/json; charset=utf-8'}
    resp = requests.post(singlePropertySearchForTrees_url,
                         data=json.dumps(payload),
                         headers=headers
                        )
    # if this fails, bail with a sensible error code
    resp.raise_for_status()
    # read JSon response or bail
    matches = resp.json()
    if not matches:
        raise Exception, u"Unable to parse this JSON response:\n\n{}".format(resp.raw())
    matched_studies = matches.get('matched_studies', None)
    # check (carefully) for one matching study...
    if matched_studies is None:
        raise Exception, "matched_studies NOT FOUND in JSON response for {}".format(expected_id)
    if len(matched_studies) > 1:
        raise Exception, u"Multiple matching studies found for {}".format(expected_id)
    if len(matched_studies) == 0:
        #raise Exception, u"No matching study found for {}".format(expected_id)
        # add a 'NOT FOUND' entry for this tree (will hide in normal use)
        # or should this be 'DEPRECATED', 'NO LONGER FOUND', ???
        decision = 'NOT FOUND'
        tree_and_study = u"{t} ({s})".format(t=tree_id, s=study_id)
    else:
        decision = 'INCLUDED'
        the_study = matched_studies[0]
        # ... with one matching tree
        matched_trees = the_study.get('matched_trees', None)
        if not matched_trees:
            raise Exception, "matched_trees NOT FOUND in JSON response for {}".format(expected_id)
        if len(matched_trees) == 0:
            raise Exception, u"No matching tree found for {}".format(expected_id)
        if len(matched_trees) > 1:
            raise Exception, u"Multiple matching trees found for {}".format(expected_id)
        the_tree = matched_trees[0]
        # its name (read-only descriptor) is in the form 'tree1234 (Smith, 2010)'
        # NOTE that this logic mirrors that in the 'curation-helpers.js' script of the curation webapp.
        #  https://github.com/OpenTreeOfLife/opentree/blob/fa36b973aa8f881d5355add0477337c2441a31df/curator/static/js/curation-helpers.js#L807
        compact_ref = full_to_compact_reference(the_study.get('ot:studyPublicationReference', ""))
        tree_name = the_tree.get('@label', None) or tree_id
        tree_and_study = u"{t} ({s})".format(t=tree_name, s=compact_ref)

    # build and add an entry for this tree 
    d.append({'SHA':'',
              'decision': 'INCLUDED',
              'name': tree_and_study,
              'comments': "",
              'studyID': study_id, 
              'treeID': tree_id
              })

assert not (validate_collection(c)[0])
write_as_json(c, sys.stdout)