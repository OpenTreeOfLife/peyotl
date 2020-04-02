#!/usr/bin/env python
from peyutil import read_as_json
from peyotl.nexson_syntax import extract_supporting_file_messages
import codecs
import json
import sys

only_with_url = '-u' in sys.argv
out = codecs.getwriter('utf-8')(sys.stdout)
for fn in sys.argv[1:]:
    if fn == '-u':
        continue
    obj = read_as_json(fn)
    m_list = extract_supporting_file_messages(obj)
    if m_list:
        if only_with_url:
            for m in m_list:
                files = m.get('data', {}).get('files', {}).get('file', [])
                for f in files:
                    if '@url' in f:
                        msg = u'''  Internal-id = {i}
  Broken URL = http://tree.opentreeoflife.org{u}
  Filename = "{f}"
  Publication = {p}
  Curator link = http://tree.opentreeoflife.org/curator/study/view/{s}

'''.format(i=m.get('@id', '-'),
           u=f['@url'].replace('uploadid=', 'uploadId='),
           f=f.get('@filename', ''),
           p=obj['nexml']['^ot:studyPublicationReference'],
           s=obj['nexml']['^ot:studyId'])
                        out.write(msg)
        else:
            json.dump(m_list, out, indent=2, sort_keys=True)
