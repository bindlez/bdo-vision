"""Conservative name hints from the bundled planner and verified screen fixtures."""
import json
from pathlib import Path
from difflib import SequenceMatcher
from functools import lru_cache

try:
    NAMES=json.loads((Path(__file__).parent/'assets'/'item-names.json').read_text(encoding='utf-8'))
except (OSError,ValueError):
    NAMES=[]
EXACT={name.casefold():name for name in NAMES}


@lru_cache(maxsize=4096)
def canonical_item(name):
    name=name.lstrip(' .,:;~—–<>\\|™�').strip()
    if name.casefold() in EXACT:return EXACT[name.casefold()]
    # OCR sometimes reads the item icon as one or two letters before the name.
    suffixes=[n for n in NAMES if name.casefold().endswith(' '+n.casefold()) and len(name)-len(n)<=5]
    if len(suffixes)==1:return suffixes[0]
    # Only a single-character difference to one unambiguous long known name.
    matches=[]
    if len(name)>=14:
        for known in NAMES:
            if abs(len(known)-len(name))>1:continue
            ratio=SequenceMatcher(None,name.casefold(),known.casefold()).ratio()
            if ratio>=.94:matches.append((ratio,known))
    matches.sort(reverse=True)
    if matches and (len(matches)==1 or matches[0][0]-matches[1][0]>=.03):return matches[0][1]
    return name
