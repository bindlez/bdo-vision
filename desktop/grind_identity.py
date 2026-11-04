"""Conservative exact trash signatures. Unknown/contradictory evidence stays open."""
from datetime import datetime
from big_drops import CATALOG,spot_key

TRASH={'tungrad ruins fragment':'Tungrad Ruins','corrupt power source':'Yzrahid Highlands'}


def session_label(now=None):return 'Grind · '+(now or datetime.now().astimezone()).strftime('%Y-%m-%d %H:%M:%S')


def infer(items):
    candidates=sorted({TRASH[name.casefold().strip()] for name in items if name.casefold().strip() in TRASH})
    return {'spot':candidates[0] if len(candidates)==1 else None,'candidates':candidates,'ambiguous':len(candidates)>1}


def pursuits(spot):return [r['item'] for r in CATALOG if spot_key(spot) in r['spots']]
