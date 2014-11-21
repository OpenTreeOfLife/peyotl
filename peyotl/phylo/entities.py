#!/usr/bin/env python
from enum import Enum
class OTULabelStyleEnum(Enum):
    OTT_ID = 0
    CURRENT_LABEL = 1 # OTT_NAME, if mapped or ORIGINAL_LABEL
    ORIGINAL_LABEL = 2
    OTT_NAME = 3
    OTT_UNIQNAME = 4
    CURRENT_LABEL_OTT_ID = 5 # concatenates {c}_{i}.format(c=CURRENT_LABEL, i=OTT_ID)

