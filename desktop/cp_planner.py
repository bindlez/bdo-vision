"""Bounded, side-effect-free CP decisions. No captures, prices, timers or threads.

The curve stores integer EXP required from CURRENT CP to the next point.
Factual public byproducts/level data × 90 rounds to these integers through 599.
Never subtract the source's accumulated float32 totals. See handbook chapter 21.
"""
import json
import math
from functools import lru_cache
from pathlib import Path
from bisect import bisect_right
from cp_forecast import productive_days,payback_days


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


@lru_cache(maxsize=1)
def xp_starts():
    starts=[0]
    for cp in range(data()['maxCp']):starts.append(starts[-1]+xp_per_cp(cp))
    return tuple(starts)


def advance(cp, percent, gained):
    start=cp;position=xp_starts()[cp]+xp_per_cp(cp)*percent/100+gained
    cp=min(data()['maxCp'],bisect_right(xp_starts(),position+1e-7)-1)
    remaining=position-xp_starts()[cp]
    required=xp_per_cp(cp)
    return {'cp':cp,'percent':remaining/required*100 if required else None,'gained':cp-start,
            'unmodeledXp':max(0,remaining) if required is None else 0}


def to_target(cp, percent, target):
    if target<=cp:return 0
    return max(0,xp_starts()[target]-xp_starts()[cp]-xp_per_cp(cp)*percent/100)


def target_plan(report):
    """Inverse planning: exact exchange quantities for a requested CP target.

    Current products all award 900 EXP per complete exchange. Economic ranking
    is withheld if any usable owned stock has no known alternative valuation.
    """
    need=report['targetBatches'];products=report['products']
    if any(p['xp']!=900 for p in products):raise ValueError('Unsupported byproduct exchange EXP')
    finish=advance(report['cp'],report['percent'],need*900)
    def make(key,label,counts):
        rows=[];cost=0;known=True;owned_xp=0
        for p in products:
            batches=counts.get(p['key'],0);items=batches*p['batch'];owned=min(p['count'],items)
            used=min(p['batches'],batches);owned_xp+=used*900
            priced=p['best']['known'];value=batches*p['best']['perBatch'] if priced else None
            if batches and not priced:known=False
            if value is not None:cost+=value
            rows.append({'key':p['key'],'name':p['name'],'batch':p['batch'],'batches':batches,'items':items,
                         'owned':p['count'],'usedOwned':owned,'shortage':max(0,items-p['count']),
                         'leftover':max(0,p['count']-items),'xp':batches*900,'ownedXp':used*900,
                         'opportunityCost':value,'cashRoute':p['best']['item']})
        given=sum(r['batches'] for r in rows);result=advance(report['cp'],report['percent'],given*900)
        return {'key':key,'label':label,'allocation':rows,'batches':given,'xp':given*900,
                'ownedXp':owned_xp,'missingXp':max(0,need*900-owned_xp),'missingBatches':max(0,need-given),
                'shortageItems':sum(r['shortage'] for r in rows),'ownedOnly':all(not r['shortage'] for r in rows),
                'opportunityCost':cost if known else None,'reachesTarget':given>=need,'result':result}
    singles=[make(p['key'],p['name']+' only',{p['key']:need}) for p in products]
    prices_known=all(p['best']['known'] for p in products if p['batches'])
    ordered=sorted(products,key=lambda p:(p['best']['perBatch'],p['key'])) if prices_known else products
    remaining=need;allocation={}
    for p in ordered:
        batches=min(remaining,p['batches']);allocation[p['key']]=batches;remaining-=batches
    owned=make('owned','Owned combination · lowest opportunity cost' if prices_known else 'Owned combination · unpriced economics',allocation)
    additions=sorted((p for p in products if p['best']['known']),key=lambda p:(p['best']['perBatch'],p['key']))
    top=additions[0] if additions else products[0];completed=dict(allocation)
    completed[top['key']]=completed.get(top['key'],0)+remaining
    completion=make('completion','Owned mix + additional '+top['name'],completed)
    balanced=make('balanced','Balanced combination · equal EXP shares',{
        p['key']:need//len(products)+(1 if i<need%len(products) else 0) for i,p in enumerate(products)})
    lines=[]
    start=report['cp'];target=report['target']
    levels=sorted(set([start,target]+[math.floor(start+(target-start)*i/24+.5) for i in range(25)])) if target>start else [start]
    for p in products:
        points=[{'cp':level,'items':math.ceil(max(0,to_target(start,report['percent'],level)-1e-7)/900)*p['batch']} for level in levels]
        lines.append({'key':p['key'],'name':p['name'],'points':points})
    return {'cp':report['cp'],'percent':report['percent'],'target':report['target'],'requiredXp':report['targetXp'],
            'requiredBatches':need,'exchangeXp':need*900,'overshootXp':max(0,need*900-report['targetXp']),
            'finish':finish,'singles':singles,'owned':owned,'completion':completion,'balanced':balanced,'lines':lines,
            'economicOrderKnown':prices_known,'alreadyReached':need==0}


def build_route(report,key,requested):
    ordered=sorted(report['products'],key=lambda p:(p['best']['perBatch'],p['key']))
    remaining=requested;spent=0;allocation=[]
    for product in ordered:
        count=min(remaining,product['batches']);remaining-=count;spent+=count*product['best']['perBatch']
        allocation.append({'key':product['key'],'name':product['name'],'batches':count,'items':count*product['batch'],
                           'remaining':product['count']-count*product['batch'],'cashRoute':product['best']['item']})
    used=requested-remaining;finish=advance(report['cp'],report['percent'],used*900)
    active=min(finish['gained'],report['deploy'])
    full_daily=active*report['income'] if report['incomeMode']=='per_cp' else (report['income']*active/report['referenceDeployed'] if report['referenceDeployed'] else 0)
    daily=full_daily*report['utilization']/100
    setup=report['setup'] if finish['gained'] else 0;investment=spent+setup
    earned=daily*productive_days(report['days'],report['delay'],report['ramp'])
    initial=report.get('_cashKnownTotal',report['cashTotal'])-investment;effective=productive_days(report['days'],report['delay'],report['ramp'])
    route={'key':key,**finish,'batches':used,'xp':used*900,'cash':initial,'foregone':spent,'setupCost':setup,
            'investment':investment,'allocation':allocation,'daily':daily,'fullDaily':full_daily,'deployed':active,
            'future':initial+earned,'earnings':earned,'difference':earned-investment,
            'breakEvenDays':payback_days(investment,daily,report['delay'],report['ramp']),
            'requiredPerCpDay':investment/(active*effective*report['utilization']/100) if active and effective and report['utilization'] else None,
            'recoveryPercent':min(100,earned/investment*100) if investment else 100,
            'roiPercent':100*(earned-investment)/investment if investment else None,
            'costPerCp':investment/finish['gained'] if finish['gained'] else None,
            'costPerDeployedCp':investment/active if active else None}
    if not report.get('cashComplete',True):
        for field in ('cash','foregone','investment','future','difference','breakEvenDays','requiredPerCpDay','recoveryPercent','roiPercent','costPerCp','costPerDeployedCp'):route[field]=None
    return route


def calculate(state, quotes=None):
    """Quotes are the existing PriceBook snapshot. Unknown routes stay unpriced."""
    spec=data();quotes=quotes or {}
    cp=number(state.get('cp',490),0,599,True);pct=number(state.get('percent',19.26),0,99.9999)
    target=number(state.get('target',500),0,600,True)
    retention=number(state.get('retention',84.5),0,100)/100
    horizon=number(state.get('days',90),1,3650,True)
    income=number(state.get('income',0),0,1_000_000_000_000)
    deploy=number(state.get('deploy',100),0,600,True)
    delay=number(state.get('delay',0),0,3650)
    split=number(state.get('split',50),0,100)
    utilization=number(state.get('utilization',100),0,100)
    ramp=number(state.get('ramp',0),0,3650)
    setup=number(state.get('setup',0),0,1_000_000_000_000_000)
    reserve=number(state.get('reserve',0),0,1_000_000_000_000_000)
    grind_rate=number(state.get('grindRate',0),0,1_000_000_000_000)
    income_mode=state.get('incomeMode','per_cp')
    if income_mode not in ('per_cp','project'):raise ValueError('Choose per-CP or whole-project income')
    policy=state.get('cashPolicy','market')
    if policy not in ('market','best','vendor'):raise ValueError('Choose market exchange or optional NPC sale')
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
            volume=quote.get('daily_volume')
            volume=volume if type(volume) in (int,float) and math.isfinite(volume) and volume>0 else None
            routes.append({'item':name,'units':units,'unit':value if known else None,
                           'gross':gross,'net':gross*retention+(0 if policy=='market' else left*product['vendor']) if known else None,
                           'perBatch':value*units*retention if known else None,'known':known,'npc':False,
                           'source':str(quote.get('source','Unpriced')),'updated_at':str(quote.get('updated_at','')),
                           'dailyVolume':volume,'marketVolumeDays':units*batches/volume if volume else None})
        if policy=='market':
            priced=[r for r in routes if r['known'] and not r['npc']]
            best=max(priced,key=lambda r:r['perBatch']) if priced else {'item':'Market quote required','perBatch':0,'net':0,'known':False}
            # Incomplete exchange batches remain in inventory, never silently NPC-sold.
            if priced:best=dict(best)
        else:best=max((r for r in routes if r['known']),key=lambda r:r['perBatch']) if policy=='best' else routes[0]
        entry={**product,'count':count,'batches':batches,'leftover':left,'best':best,'routes':routes}
        products.append(entry)
        if count:all_routes.extend({'product':product['name'],'batches':batches,'leftover':left,**r} for r in routes)
    ordered=sorted(products,key=lambda p:(p['best']['perBatch'],p['key']))
    total_batches=sum(p['batches'] for p in products)
    cash=sum(p['best']['net'] for p in products)
    complete=all(p['best']['known'] for p in products if p['batches'])
    need=to_target(cp,pct,target)
    target_batches=math.ceil(max(0,need-1e-7)/900)

    current=xp_per_cp(cp);next_xp=current*(1-pct/100)
    report={'cp':cp,'percent':pct,'target':target,'days':horizon,'retention':retention,
            'income':income,'deploy':deploy,'delay':delay,'split':split,'cashPolicy':policy,
            'nextXp':next_xp,'nextBatches':math.ceil(max(0,next_xp-1e-7)/900),'targetXp':need,
            'targetBatches':target_batches,'targetReachable':target_batches<=total_batches,
            'totalXp':total_batches*900,'totalBatches':total_batches,'vendorTotal':sum(p['count']*p['vendor'] for p in products),
            'products':products,'exchangeRoutes':all_routes,'missing':sorted(set(missing)),
            'cashTotal':cash if complete else None,'_cashKnownTotal':cash,'cashComplete':complete,
            'curveVersion':spec['version'],'utilization':utilization,'ramp':ramp,'setup':setup,
            'reserve':reserve,'grindRate':grind_rate,'incomeMode':income_mode,
            'referenceDeployed':min(advance(cp,pct,total_batches*900)['gained'],deploy)}
    report['routes']=[build_route(report,'cash',0),build_route(report,'cp',total_batches),build_route(report,'target',min(target_batches,total_batches)),build_route(report,'split',math.floor(total_batches*split/100))]
    report['winner']=max(report['routes'],key=lambda r:r['future'])['key'] if complete else None
    return report
