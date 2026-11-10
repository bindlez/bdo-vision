"""Conservative exact trash signatures. Unknown/contradictory evidence stays open."""
from datetime import datetime
from big_drops import CATALOG,spot_key

TRASH={'tungrad ruins fragment':'Tungrad Ruins','corrupt power source':'Yzrahid Highlands'}


def early_trash_rate(items,drop_counts,observed,elapsed):
    """Project common vendor loot only, while the live sample is still short."""
    if not 10<=observed<60 or elapsed<=0 or observed/elapsed<.65:return None
    verified=[item for item in items if item['item'].casefold() in TRASH and
              item['value'] is not None and item['source'].startswith('NPC vendor')]
    if sum(drop_counts.get(item['item'].casefold(),0) for item in verified)<3:return None
    return sum(item['value'] for item in verified)*3600/observed


def session_label(now=None):return 'Grind · '+(now or datetime.now().astimezone()).strftime('%Y-%m-%d %H:%M:%S')


def infer(items):
    candidates=sorted({TRASH[name.casefold().strip()] for name in items if name.casefold().strip() in TRASH})
    return {'spot':candidates[0] if len(candidates)==1 else None,'candidates':candidates,'ambiguous':len(candidates)>1}


def pursuits(spot):return [r['item'] for r in CATALOG if spot_key(spot) in r['spots']]
