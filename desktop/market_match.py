"""Match observed names to unique market IDs without merging quality variants."""
import re
import unicodedata
from difflib import SequenceMatcher
from item_names import canonical_item


def normalized(name):
    return market_name_key(canonical_item(name))


def market_name_key(name):
    name=unicodedata.normalize('NFKC',name).casefold()
    name=re.sub(r'^[\W\d_]+','',name)
    return ' '.join(re.sub(r'[^\w]+',' ',name).split())


class ItemDatabase:
    """Index the game database once; never scan 70,000 names on the UI thread."""
    def __init__(self,items):
        self.exact={};self.tokens={}
        for item in items:
            if not isinstance(item,dict) or not isinstance(item.get('id'),int) or not item.get('name'):continue
            key=market_name_key(item['name'])
            self.exact.setdefault(key,[]).append(item)
            for token in set(key.split()):self.tokens.setdefault(token,[]).append(item)

    def match(self,observed):
        key=normalized(observed);exact=self.exact.get(key,[])
        if len({i['id'] for i in exact})==1:return exact[0]
        if exact or len(key)<14:return None
        pools=[self.tokens[t] for t in set(key.split()) if t in self.tokens and len(t)>2]
        return match_item(observed,min(pools,key=len)) if pools else None

    def candidates(self,observed):
        # Some event-only items share a name with a tradable item. Ask the market
        # about each exact ID and accept only an unambiguous priced result.
        exact=self.exact.get(normalized(observed),[])
        if exact:return exact
        match=self.match(observed)
        return [match] if match else []


def match_item(observed,catalog):
    needle=normalized(observed)
    exact=[item for item in catalog if market_name_key(item['name'])==needle]
    if len({item['id'] for item in exact})==1:return exact[0]
    if exact or len(needle)<14:return None
    scores=[];tokens=set(needle.split())
    for item in catalog:
        candidate=market_name_key(item['name'])
        if abs(len(candidate)-len(needle))>4:continue
        if len(tokens & set(candidate.split()))<2:continue
        score=SequenceMatcher(None,needle,candidate).ratio()
        if score>=.93:scores.append((score,item))
    scores.sort(key=lambda entry:entry[0],reverse=True)
    if scores and (len(scores)==1 or scores[0][0]-scores[1][0]>=.05):return scores[0][1]
    return None
