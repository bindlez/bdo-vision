"""Optional public Workerman reference adapter and discrete-job CP payback model.

No account access, OCR, startup requests, third-party packages or periodic work.
Only fixed public repository URLs are fetched, and one consistent revision is used.
"""
import heapq
import json
import math
import re
import threading
import time
import urllib.request
from pathlib import Path
from functools import lru_cache
from cp_planner import number, target_plan
from cp_forecast import payback_days, productive_days

SOURCE='https://github.com/shrddr/workermanjs'
FILES={'plantzone.json':700000,'manual/plantzone_drops.json':300000,
       'nodes_links.json':500000,'regioninfo.json':800000,
       'distances_tk2pzk.json':800000,'loc.json':4000000}


def _download(url,limit):
    request=urllib.request.Request(url,headers={'User-Agent':'BDO-Vision-Workerman-reference','Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=12) as response:
        # Never follow a redirect to a different host.
        if response.url.split('/')[2] not in ('api.github.com','raw.githubusercontent.com'):raise ValueError('Unexpected reference host')
        raw=response.read(limit+1)
    if len(raw)>limit:raise ValueError('Reference response exceeds byte budget')
    return json.loads(raw)


def normalize(raw,revision,now=None):
    """Extract public factual fields; keep upstream application code out of the app."""
    graph=raw['nodes_links.json'];regions=raw['regioninfo.json'];names=raw['loc.json']['en']
    towns={str(r['key']):str(r['waypoint']) for r in regions.values()
           if r.get('npcWorkerCharacterKey',0)>0 and graph.get(str(r.get('waypoint')),{}).get('is_base_town')}
    distances=raw['distances_tk2pzk.json'];zones=raw['plantzone.json'];drops=raw['manual/plantzone_drops.json']
    routes={}
    for town,node in towns.items():
        queue=[(0,node,())];visited={}
        while queue:
            cost,key,path=heapq.heappop(queue)
            if key in visited:continue
            visited[key]=(cost,list(path)+( [key] ));path=tuple(visited[key][1])
            for other in graph.get(key,{}).get('link_list',[]):
                other=str(other)
                if other in graph and other not in visited:
                    weight=graph[other].get('need_exploration_point',0)
                    if not isinstance(weight,(int,float)) or not 0<=weight<=100:raise ValueError('Invalid connection CP')
                    heapq.heappush(queue,(cost+int(weight),other,path))
        routes[town]=visited
    jobs=[]
    for ident,drop in drops.items():
        zone=zones.get(ident);options=[]
        if not zone or not drop.get('unlucky'):continue
        for town,node in towns.items():
            route=routes[town].get(ident)
            distance=next((d for p,d in distances.get(town,[]) if str(p)==ident),None)
            if route and type(distance) in (int,float) and 0<=distance<10000000:options.append((route[0],distance,town,route[1]))
        if not options:continue
        cp,distance,town,path=min(options)
        label=names['node'].get(str(zone.get('parent')),'Node '+str(zone.get('parent')))
        outputs=[{'id':str(k),'name':names['item'].get(str(k),'Item '+str(k)),
                  'quantity':float(v),'giant':float(drop.get('unlucky_gi',{}).get(str(k),v))}
                 for k,v in drop['unlucky'].items() if type(v) in (int,float) and math.isfinite(v) and v>0]
        workload=drop.get('workload')
        if not outputs or type(workload) not in (int,float) or not math.isfinite(workload) or workload<=0:continue
        jobs.append({'id':ident,'name':label+' · '+', '.join(x['name'] for x in outputs),
                     'town':names['node'].get(towns[town],'Town '+town),'townKey':town,
                     'connectionCp':cp,'path':path,'distance':distance,'workload':workload,
                     'samples':drop.get('rolls',0),'outputs':outputs})
    if not 1<=len(jobs)<=3000:raise ValueError('No supported Workerman jobs')
    return {'schema':1,'source':SOURCE,'revision':revision,'fetchedAt':time.time() if now is None else now,'jobs':jobs}


class WorkermanReference:
    def __init__(self,path):self.path=Path(path);self.lock=threading.Lock()

    def cached(self):
        try:
            if self.path.stat().st_size>2000000:return None
            result=json.loads(self.path.read_text(encoding='utf-8'))
            if result.get('schema')!=1 or not isinstance(result.get('jobs'),list) or not 1<=len(result['jobs'])<=3000:return None
            if not re.fullmatch('[0-9a-f]{40}',result.get('revision','')) or type(result.get('fetchedAt')) not in (int,float):return None
            return result
        except (OSError,ValueError,TypeError):return None

    def refresh(self):
        if not self.lock.acquire(blocking=False):raise ValueError('Workerman reference refresh already running')
        try:
            cached=self.cached()
            if cached and time.time()-cached['fetchedAt']<7*86400:return cached
            head=_download('https://api.github.com/repos/shrddr/workermanjs/git/ref/heads/main',10000)
            revision=head.get('object',{}).get('sha','')
            if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Invalid source revision')
            raw={name:_download(f'https://raw.githubusercontent.com/shrddr/workermanjs/{revision}/data/{name}',limit) for name,limit in FILES.items()}
            try:result=normalize(raw,revision)
            except (KeyError,TypeError,AttributeError,OverflowError) as exc:raise ValueError('Unsupported public reference schema') from exc
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');temporary.replace(self.path)
            return result
        finally:self.lock.release()


@lru_cache(maxsize=4)
def reference_for(folder):return WorkermanReference(Path(folder)/'workerman-reference.json')


def quote_ids(quotes):
    """Exact database identity only. Conflicting aliases never supply a price."""
    result={};conflicts=set()
    for q in quotes.values():
        ident=str(q.get('item_id') or q.get('id') or '')
        price=q.get('unit_price',q.get('price'))
        if not ident or type(price) not in (int,float) or not math.isfinite(price) or price<=0 or q.get('price_basis')=='npc_vendor':continue
        if ident in result and result[ident]['price']!=price:conflicts.add(ident)
        result[ident]={'price':price,'at':q.get('updated_at',''),'source':q.get('source','Cached market quote')}
    return {k:v for k,v in result.items() if k not in conflicts}


def model_job(job,report,quotes,assumptions=None):
    a=assumptions or {}
    speed=number(a.get('workSpeed',150),1,1000);move=number(a.get('moveSpeed',7.5),.1,100)
    productivity=number(a.get('productivity',0),0,100)/100
    costs=number(a.get('operatingCost',0),0,1e12)
    required=number(a.get('additionalCp',job['connectionCp']),0,600,True)
    giant=a.get('giant',False)
    if not isinstance(giant,bool):raise ValueError('Giant yields must be a checkbox')
    work=math.ceil(job['workload']*(2-productivity)/speed)
    cycle=10*work+2*job['distance']/move/60;cycles=1440/cycle
    book=quote_ids(quotes);outputs=[]
    for p in job['outputs']:
        q=book.get(p['id']);daily=cycles*p['giant' if giant else 'quantity']
        outputs.append({**p,'perDay':daily,'quote':q,'gross':daily*q['price'] if q else None})
    known=all(p['quote'] for p in outputs)
    gross=sum(p['gross'] for p in outputs) if known else None
    net=gross*report['retention']-costs if known else None
    daily=net*report['utilization']/100 if known else None
    plan=target_plan(report)['completion'];gained=plan['result']['gained'];cost=plan['opportunityCost']
    # Full discrete job must fit. Existing/free CP is not an incremental benefit of new CP.
    eligible=required>0 and gained>=required
    investment=cost+report['setup'] if cost is not None and gained else None
    payback=payback_days(investment,daily,report['delay'],report['ramp']) if eligible and investment is not None and daily is not None and daily>0 else None
    effective_daily=daily if eligible and daily is not None else 0
    timeline=[{'day':report['days']*i/24,'earned':effective_daily*productive_days(report['days']*i/24,report['delay'],report['ramp']),
               'difference':effective_daily*productive_days(report['days']*i/24,report['delay'],report['ramp'])-investment if investment is not None else None} for i in range(25)]
    if required==0:status='Existing CP can fund this job; do not credit its income to a byproduct turn-in.'
    elif not eligible:status='Target does not unlock enough new CP for this whole job. No partial-job income credited.'
    elif not plan['ownedOnly']:status='Hypothetical until you obtain the additional byproducts shown in the target plan.'
    elif not known:status='Unpriced output: refresh shared market prices; no zero-price fallback.'
    elif daily<=0:status='No positive modeled net income under these assumptions.'
    elif cost is None:status='Byproduct opportunity cost is unpriced; payback cannot be calculated.'
    else:status='Modeled extra income, not recorded loot or guaranteed sales.'
    return {'job':job,'cycleMinutes':cycle,'cyclesPerDay':cycles,'outputs':outputs,'grossPerDay':gross,
            'netPerDay':net,'effectivePerDay':daily,'requiredCp':required,'minimumTarget':report['cp']+required,
            'unassignedCp':max(0,gained-required),'eligible':eligible,'investment':investment,
            'opportunityCost':cost,'shortageItems':plan['shortageItems'],'ownedOnly':plan['ownedOnly'],
            'breakEvenDays':payback,'status':status,'timeline':timeline,
            'differenceAtHorizon':timeline[-1]['difference'] if eligible and known else None,
            'operatingCost':costs,'assumptions':{'workSpeed':speed,'moveSpeed':move,'productivity':productivity*100,'giant':giant}}
