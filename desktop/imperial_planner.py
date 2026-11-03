"""Native Imperial comparisons. Parity-tested with the owned browser model.

No network, OCR, timers or ledger writes. Quotes must be keyed by exact item ID.
"""
from collections import defaultdict
import math
from craft_economy import craft_spec,recipes


def finite(value):return type(value) in (int,float) and math.isfinite(value)


def bracket(spec,kind,mastery):
    rows=spec.get('mastery',{}).get(kind,[])
    return next((r for r in reversed(rows) if r['masteryLevel']<=mastery),rows[0] if rows else {})


def imperial_ranks(quotes,*,boxes=1,mastery=None,guru_only=False,catalog=None,spec=None):
    catalog=recipes() if catalog is None else catalog;spec=craft_spec() if spec is None else spec
    if type(boxes) is not int or not 1<=boxes<=10000:raise ValueError('Choose 1–10,000 boxes')
    mastery=mastery or {};result={};by_output=defaultdict(list)
    for recipe in catalog:
        if recipe['type'] not in ('cooking','alchemy'):continue
        by_output[recipe['itemId']].append(recipe)
        if recipe.get('rare'):by_output[recipe['rare']['itemId']].append(recipe)

    def quote(ident):
        q=quotes.get(ident,quotes.get(str(ident),{}))
        price=q.get('price',q.get('unit_price'))
        return (q if finite(price) and price>0 and q.get('price_basis')!='npc_vendor' else {}),price

    def input_price(ident,quantity,stock_only):
        meta=spec['items'].get(str(ident),{});q,market=quote(ident);npc=meta.get('npcBuy')
        market_known=bool(q) and (not stock_only or finite(q.get('stock')) and q['stock']>=quantity)
        if finite(npc) and npc>0 and (not market_known or npc<market):return npc,'NPC purchase',None
        if market_known:return market,q.get('source','Central Market'),q.get('stock')
        return None,'Unpriced',None

    for kind in ('cooking','alchemy'):
        level=mastery.get(kind,0)
        if not finite(level) or not 0<=level<=3000:raise ValueError('Mastery must be 0–3,000')
        b=bracket(spec,kind,level);buy=[];craft=[];stocked=[]
        for box in catalog:
            if box.get('method')!='imperial_'+kind or guru_only and box['itemId'] not in (9856,9871) or len(box['mats'])!=1:continue
            base=spec['items'].get(str(box['itemId']),{}).get('imperialBase')
            if not base:continue
            mat=box['mats'][0];quantity=math.ceil(mat['qty']*boxes/(box.get('minProc') or 1))
            q,unit=quote(mat['itemId']);cost=unit*quantity if q else None
            payout=base*(2.5+b.get('imperialBonus',0))*boxes
            row={'boxId':box['itemId'],'boxName':box['name'],'boxRecipeId':box['id'],'itemId':mat['itemId'],
                 'name':mat['name'],'quantity':quantity,'boxes':boxes,'payout':payout,'stock':q.get('stock')}
            buy.append({**row,'cost':cost,'perBox':None if cost is None else cost/boxes,'profit':None if cost is None else payout-cost,
                        'inStock':cost is not None and finite(q.get('stock')) and q['stock']>=quantity})
            best=None;best_stock=None
            for source in by_output[mat['itemId']]:
                low=source.get('minProc',1);high=source.get('maxProc',1)
                normal=(low+high)/2+(high-(low+high)/2)*b.get('maxProcChance',0)
                rare=source.get('rare');rare_yield=0
                if rare:
                    average=(rare['minProc']+rare['maxProc'])/2
                    rare_yield=(average+(rare['maxProc']-average)*b.get('maxProcChance',0))*(.2+b.get('rareAdditionalChance',0)) if kind=='cooking' else average*.2
                produced=normal if source['itemId']==mat['itemId'] else rare_yield
                if not produced:continue
                runs=math.ceil(quantity/produced)
                for stock_only in (False,True):
                    resolved=[];choices={}
                    for i,slot in enumerate(source['mats']):
                        options=spec.get('groups',{}).get(str(slot.get('groupId')),[]) if slot.get('groupId') else []
                        winner=None
                        for option in options:
                            qty=math.ceil(slot.get('required',slot['qty'])/option['value'])
                            price,_,_=input_price(option['itemId'],qty*runs,stock_only)
                            if price is not None and (winner is None or qty*price<winner[0]):winner=(qty*price,option['itemId'],qty)
                        ident=winner[1] if winner else slot['itemId'];qty=winner[2] if winner else slot['qty']
                        if options:choices[str(i)]=ident
                        resolved.append((ident,qty))
                    needed=defaultdict(float)
                    for ident,qty in resolved:needed[ident]+=qty*runs
                    ingredients=[];cost=0;known=True;in_stock=True
                    for ident,qty in needed.items():
                        price,basis,stock=input_price(ident,qty,stock_only)
                        if price is None:known=False
                        else:cost+=qty*price
                        npc=spec['items'].get(str(ident),{}).get('npcBuy')
                        npc_available=basis=='NPC purchase' and finite(npc) and npc>0 and price==npc
                        if not npc_available and not (finite(stock) and stock>=qty):in_stock=False
                        ingredients.append({'itemId':ident,'name':spec['items'][str(ident)]['name'],'quantity':qty,'unit':price,'basis':basis,'stock':stock})
                    candidate={**row,'cost':cost if known else None,'perBox':cost/boxes if known else None,
                               'profit':payout-cost if known else None,'recipeId':source['id'],'runs':runs,
                               'expectedOutput':runs*produced,'surplus':runs*produced-quantity,
                               'inStock':known and in_stock,'ingredients':ingredients,'choices':choices}
                    if not stock_only and (best is None or known and (best['cost'] is None or cost<best['cost'])):best=candidate
                    if candidate['inStock'] and (best_stock is None or cost<best_stock['cost']):best_stock=candidate
            craft.append(best or {**row,'cost':None,'perBox':None,'profit':None})
            if best_stock:stocked.append(best_stock)
        key=lambda r:(r['cost'] is None,r['cost'] if r['cost'] is not None else math.inf,r['name'])
        result[kind]={'buy':sorted(buy,key=key),'craft':sorted(craft,key=key),'craftInStock':sorted(stocked,key=key)}
    return result
