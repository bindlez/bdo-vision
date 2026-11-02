"""Bounded, side-effect-free CP decisions. No captures, prices, timers or threads.

The curve stores integer EXP required from CURRENT CP to the next point.
Factual public byproducts/level data × 90 rounds to these integers through 599.
Never subtract the source's accumulated float32 totals. See handbook chapter 21.
"""
import json
import math
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def data():
    return json.loads((Path(__file__).parent/'assets/cp-data.json').read_text(encoding='utf-8'))


def number(value, low, high, integer=False):
    if isinstance(value, bool):raise ValueError('Use a number, not a checkbox value')
    try:n=float(value)
    except (ValueError, TypeError):raise ValueError('Enter a valid number') from None
    if not math.isfinite(n) or not low<=n<=high or (integer and n!=int(n)):
        raise ValueError(f'Enter {"a whole number" if integer else "a number"} from {low:,} to {high:,}')
    return int(n) if integer else n


def xp_per_cp(cp):
    if not 0<=cp<data()['maxCp']:return None
    return next(xp for start,xp in reversed(data()['curve']) if cp>=start)


def advance(cp, percent, gained):
    start=cp;xp=xp_per_cp(cp)*percent/100
    remaining=xp+gained
    while cp<data()['maxCp'] and remaining+1e-7>=xp_per_cp(cp):
        remaining-=xp_per_cp(cp);cp+=1
    required=xp_per_cp(cp)
    return {'cp':cp,'percent':remaining/required*100 if required else None,'gained':cp-start,
            'unmodeledXp':max(0,remaining) if required is None else 0}


def to_target(cp, percent, target):
    if target<=cp:return 0
    return max(0,sum(xp_per_cp(p) for p in range(cp,target))-xp_per_cp(cp)*percent/100)


def calculate(state, quotes=None):
    """Quotes are the existing PriceBook snapshot. Unknown routes stay unpriced."""
    spec=data();quotes=quotes or {}
    cp=number(state.get('cp',490),0,599,True);pct=number(state.get('percent',19.26),0,99.9999)
    target=number(state.get('target',500),0,600,True)
    retention=number(state.get('retention',84.5),0,100)/100
    horizon=number(state.get('days',90),1,3650,True)
    income=number(state.get('income',0),0,1_000_000_000)
    deploy=number(state.get('deploy',100),0,600,True)
    delay=number(state.get('delay',0),0,3650)
    split=number(state.get('split',50),0,100)
    policy=state.get('cashPolicy','best')
    if policy not in ('best','vendor'):raise ValueError('Choose best priced exchange or NPC sale')
    counts=state.get('counts',{})
    if not isinstance(counts,dict):raise ValueError('Invalid byproduct counts')
    products=[];all_routes=[];missing=[]
    for product in spec['products']:
        count=number(counts.get(product['key'],0),0,1_000_000_000,True)
        batches=count//product['batch'];left=count%product['batch']
        vendor=product['batch']*product['vendor']
        routes=[{'item':'Direct NPC sale','units':product['batch'],'unit':product['vendor'],
                 'gross':vendor*batches+left*product['vendor'],'net':vendor*batches+left*product['vendor'],
                 'perBatch':vendor,'source':'NPC · no market tax','updated_at':'2026-11-02','known':True,'npc':True}]
        for name,units in product['rewards']:
            quote=quotes.get(name,{})
            value=quote.get('unit_price')
            known=isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and 0<value<=1e12 and quote.get('price_basis')!='npc_vendor'
            if count and not known:missing.append(name)
            gross=value*units*batches if known else None
            routes.append({'item':name,'units':units,'unit':value if known else None,
                           'gross':gross,'net':gross*retention+left*product['vendor'] if known else None,
                           'perBatch':value*units*retention if known else None,'known':known,'npc':False,
                           'source':str(quote.get('source','Unpriced')),'updated_at':str(quote.get('updated_at',''))})
        best=max((r for r in routes if r['known']),key=lambda r:r['perBatch']) if policy=='best' else routes[0]
        entry={**product,'count':count,'batches':batches,'leftover':left,'best':best,'routes':routes}
        products.append(entry)
        if count:all_routes.extend({'product':product['name'],'batches':batches,'leftover':left,**r} for r in routes)
    ordered=sorted(products,key=lambda p:(p['best']['perBatch'],p['key']))
    total_batches=sum(p['batches'] for p in products)
    cash=sum(p['best']['net'] for p in products)
    need=to_target(cp,pct,target)
    target_batches=math.ceil(max(0,need-1e-7)/900)

    def route(key, requested):
        remaining=requested;spent=0;alloc=[]
        for p in ordered:
            n=min(remaining,p['batches']);remaining-=n
            spent+=n*p['best']['perBatch']
            alloc.append({'key':p['key'],'name':p['name'],'batches':n,'items':n*p['batch'],
                          'remaining':p['count']-n*p['batch'],'cashRoute':p['best']['item']})
        used=requested-remaining;finish=advance(cp,pct,used*900)
        active=min(finish['gained'],deploy);daily=active*income
        earnings=daily*max(0,horizon-delay);initial=cash-spent
        return {'key':key,**finish,'batches':used,'xp':used*900,'cash':initial,'foregone':spent,
                'allocation':alloc,'daily':daily,'deployed':active,'future':initial+earnings,
                'earnings':earnings,'difference':earnings-spent,
                'breakEvenDays':delay+spent/daily if daily>0 else None,
                'requiredPerCpDay':spent/(active*max(0,horizon-delay)) if active and horizon>delay else None}
    routes=[route('cash',0),route('cp',total_batches),route('target',min(target_batches,total_batches)),route('split',math.floor(total_batches*split/100))]
    selected=max(routes,key=lambda r:r['future'])
    current=xp_per_cp(cp);next_xp=current*(1-pct/100)
    return {'cp':cp,'percent':pct,'target':target,'days':horizon,'retention':retention,
            'income':income,'deploy':deploy,'delay':delay,'split':split,'cashPolicy':policy,
            'nextXp':next_xp,'nextBatches':math.ceil(max(0,next_xp-1e-7)/900),'targetXp':need,
            'targetBatches':target_batches,'targetReachable':target_batches<=total_batches,
            'totalXp':total_batches*900,'totalBatches':total_batches,'vendorTotal':sum(p['count']*p['vendor'] for p in products),
            'products':products,'exchangeRoutes':all_routes,'missing':sorted(set(missing)),
            'cashTotal':cash,'routes':routes,'winner':selected['key'],'curveVersion':spec['version']}
