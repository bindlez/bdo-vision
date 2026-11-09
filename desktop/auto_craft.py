"""Automatic recipe-family inference from accepted drops plus tracked utensils.

No captures or ledger mutation. Rates measure readable time; forecasts are models.
"""
import math
from functools import lru_cache
from collections import defaultdict
from craft_economy import recipes,craft_spec,material_price
from item_names import canonical_item


def name_key(name):return canonical_item(name).casefold()


@lru_cache(maxsize=1)
def families():
    result={};outputs=defaultdict(set);spec=craft_spec()
    for r in recipes():
        if r['type'] not in ('cooking','alchemy'):continue
        key=str(r['itemId']);group=result.setdefault(key,{'key':key,'name':r['name'],'kind':r['type'],'recipes':[],'outputs':set()})
        group['recipes'].append(r);group['outputs'].add(name_key(r['name']));outputs[(r['type'],name_key(r['name']))].add(key)
        if r.get('rare'):
            rare=spec['items'].get(str(r['rare']['itemId']),{}).get('name')
            if rare:group['outputs'].add(name_key(rare));outputs[(r['type'],name_key(rare))].add(key)
    return result,outputs


def identify(item,kind):
    groups,index=families();keys=index.get((kind,name_key(item)),set())
    return groups[next(iter(keys))] if len(keys)==1 else None


def related(item,family):
    if name_key(item) in family['outputs']:return True
    spec=craft_spec();ident=spec.get('byproducts',{}).get(family['kind'],{}).get('id')
    ids={ident}
    if family['kind']=='alchemy':ids.update(pair[0] for rows in spec.get('alchemyExtras',{}).values() for pair in rows)
    return any(name_key(spec['items'].get(str(i),{}).get('name',''))==name_key(item) for i in ids if i)


def valid_price(quote):
    value=quote.get('unit_price') if quote else None
    return value if type(value) in (int,float) and math.isfinite(value) and value>0 else None


def forecast(family,quotes,speed,actions,mastery=0,retention=84.5):
    spec=craft_spec();r=family['recipes'][0]
    rows=spec.get('mastery',{}).get(family['kind'],[]);b=next((b for b in reversed(rows) if b['masteryLevel']<=mastery),{})
    low=r.get('minProc',1);high=r.get('maxProc',1);average=(low+high)/2
    normal=average+(high-average)*b.get('maxProcChance',0);outputs=[{'item':r['name'],'yield':normal}]
    if r.get('rare'):
        rare=r['rare'];avg=(rare['minProc']+rare['maxProc'])/2
        quantity=(avg+(rare['maxProc']-avg)*b.get('maxProcChance',0))*(.2+b.get('rareAdditionalChance',0)) if family['kind']=='cooking' else avg*.2
        outputs.append({'item':spec['items'][str(rare['itemId'])]['name'],'yield':quantity})
    for o in outputs:o['unit']=valid_price(quotes.get(o['item']));o['perBatch']=o['yield']*o['unit'] if o['unit'] is not None else None
    gross=sum(o['perBatch'] for o in outputs) if all(o['perBatch'] is not None for o in outputs) else None
    variants=[]
    for variant in family['recipes']:
        cost=0;known=True
        for m in variant['mats']:
            choices=spec.get('groups',{}).get(str(m.get('groupId')),[]) if m.get('groupId') else []
            choices=choices or [{'itemId':m['itemId'],'value':1}];priced=[]
            for choice in choices:
                meta=spec['items'].get(str(choice['itemId']),{});qty=math.ceil(m.get('required',m['qty'])/choice['value']) if m.get('groupId') else m['qty']
                price=material_price({'itemId':choice['itemId'],'name':meta.get('name',m['name'])},quotes)
                if type(price) in (int,float) and math.isfinite(price) and price>0:priced.append(qty*price)
            if priced:cost+=min(priced)
            else:known=False
        if known:variants.append(cost)
    net=[gross*retention/100-c for c in variants] if gross is not None else []
    return {'perBatch':gross,'perHour':gross*3600/speed if gross is not None else None,
            'toolValue':gross*actions if gross is not None else None,'outputs':outputs,'mastery':mastery,
            'retention':retention,'netPerHourLow':min(net)*3600/speed if net else None,'netPerHourHigh':max(net)*3600/speed if net else None,
            'pricedVariants':len(variants),'variants':len(family['recipes'])}


CRAFT_RATE_MIN_SECONDS = 10


class CraftInference:
    def __init__(self,state=None):
        self.run=state;self.pending=None;self.last_id=max(0,int((state or {}).get('lastId',0)))
        self.last_tick=None;self.last_ready=False;self.sample_tool=None;self.sample_observed=0;self.revision=0;self.state='Waiting for repeated craft output and a tracked tool.'

    def tick(self,context,ready,now):
        active=bool(context and context.get('active'))
        tool=context['tool'] if active else None
        if tool != self.sample_tool:
            self.sample_tool=tool;self.sample_observed=0;self.last_ready=False
        elapsed=max(0,min(3,now-self.last_tick)) if self.last_tick is not None and active and ready and self.last_ready else 0
        self.sample_observed+=elapsed
        for record in [self.run,self.pending]:
            if record and record is self.run and self.pending and self.pending['family']!=record['family']:continue
            if record and active and ready and self.last_ready and record['tool']==context['tool'] and elapsed:
                record['observed']+=min(elapsed,max(0,now-record.get('tickStart',record['at'])))
        self.last_tick=now;self.last_ready=bool(active and ready)
        if self.pending and (not active or self.pending['tool']!=context['tool'] or now-self.pending.get('tickStart',self.pending['at'])>90):self.pending=None

    def observe(self,ident,item,quantity,context,at,now=None):
        if ident<=self.last_id:return False
        self.last_id=ident
        if not context or not context.get('active') or type(quantity) is not int or quantity<=0:return False
        family=identify(item,context['kind'])
        pending=self.pending
        if not family and pending and pending['tool']==context['tool'] and 0<=at-pending['at']<=90 and related(item,families()[0][pending['family']]):
            self.add(pending,item,quantity);pending['ids'].append(ident);pending['lastId']=ident
            return False  # Extra/byproduct evidence never confirms a recipe alone.
        same=self.run and self.run['tool']==context['tool']
        if same and related(item,families()[0][self.run['family']]) and (not family or family['key']==self.run['family']):
            self.add(self.run,item,quantity);self.run['lastId']=ident;self.revision+=1;return True
        if not family:return False
        p=self.pending
        if not p or p['family']!=family['key'] or p['tool']!=context['tool'] or not 0<=at-p['at']<=90:
            startup=self.sample_observed if not same and pending is None and self.sample_tool==context['tool'] else 0
            p=self.pending={'family':family['key'],'tool':context['tool'],'at':at,'tickStart':at if now is None else now,'counts':{},'observed':startup,'samples':[],'lastId':ident,
                'actions':context['remaining'] if same else context['verified'],'changedRecipe':bool(same),'witnesses':[at],'ids':[]}
        self.add(p,item,quantity);p['lastId']=ident;p['ids'].append(ident)
        if all(abs(at-v)>=.5 for v in p['witnesses']):p['witnesses'].append(at)
        if len(p['witnesses'])<2:self.state='Checking '+family['name']+' · waiting for a second capture.';return False
        self.run=p;self.pending=None;self.revision+=1;self.state='Recipe family detected from repeated output and a tracked utensil.';return True

    @staticmethod
    def add(run,item,quantity):
        run['counts'][canonical_item(item)]=run['counts'].get(canonical_item(item),0)+quantity
        run['samples'].append([run['observed'],dict(run['counts'])])
        if len(run['samples'])>48:run['samples']=run['samples'][::2]+([run['samples'][-1]] if run['samples'][-1]!=run['samples'][::2][-1] else [])

    def snapshot(self,context,quotes,ready,mastery=0,retention=84.5):
        if not self.run:return {'detected':False,'status':self.state,'pending':self.pending['family'] if self.pending else None}
        r=self.run;family=families()[0].get(r['family'])
        if not family:return {'detected':False,'status':'Saved recipe is no longer in the catalog.'}
        current=bool(context and context.get('active') and context['tool']==r['tool'])
        speed=context['speed'] if current else 1
        spec=craft_spec();byproduct=spec.get('byproducts',{}).get(family['kind'],{}).get('id');kept=name_key(spec['items'].get(str(byproduct),{}).get('name',''))
        def valuation(counts):
            priced=[];unknown=[];items=[]
            for item,quantity in counts.items():
                unit=None if name_key(item)==kept else valid_price(quotes.get(item));value=unit*quantity if unit is not None else None
                items.append({'item':item,'quantity':quantity,'value':value,'kept':name_key(item)==kept})
                if unit is not None:priced.append(value)
                elif name_key(item)!=kept:unknown.append(item)
            return (sum(priced) if priced else None),unknown,items
        value,unknown,items=valuation(r['counts']);model=forecast(family,quotes,speed,r['actions'],mastery,retention)
        progress=max(0,min(1,1-context['remaining']/max(1,r['actions']))) if current else None
        units=sum(r['counts'].values());next_goal=next((n for n in (100,500,1000,2500,5000,10000,25000,50000) if n>units),((units//50000)+1)*50000)
        status='Observing detected craft' if current and ready else 'Capture paused · rates frozen; forecast remains an estimate' if current else 'Retained craft · waiting for a new verified tool/output'
        return {'detected':True,'toolSession':context['tool'] if current else None,'current':current,'available':bool(current and ready),'recipe':family['name'],'kind':family['kind'],
                'status':status,'observedSeconds':r['observed'],'recordedValue':value,'recordedPerHour':value*3600/r['observed'] if value is not None and r['observed']>=CRAFT_RATE_MIN_SECONDS else None,
                'model':model if current else None,'remainingValue':model['perBatch']*context['remaining'] if current and model['perBatch'] is not None else None,
                'scannedActions':r['actions'],'progress':progress,'items':items,'unpriced':unknown,'units':units,'nextGoal':next_goal,
                'changedRecipe':r.get('changedRecipe',False),'points':[[second,valuation(counts)[0]] for second,counts in r['samples']]}
