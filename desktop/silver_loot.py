"""Value recorded loot using exact Central Market item quotes; never infer costs."""
from loot_insights import summarize


def silver_snapshot(rows,prices):
    result=summarize(rows,prices)
    items=[]
    for entry in result['items']:
        item=dict(entry)
        item['group']='Elixirs' if any(word in item['item'].casefold() for word in ('elixir','draught','perfume')) else 'Extras / other loot'
        item['price_updated_at']=prices.get(item['item'],{}).get('updated_at')
        item['market_id']=prices.get(item['item'],{}).get('item_id')
        item['market_region']=prices.get(item['item'],{}).get('region')
        item['price_basis']=prices.get(item['item'],{}).get('price_basis','market')
        item['source_url']=prices.get(item['item'],{}).get('source_url')
        items.append(item)
    return {'items':items,'market_silver':result['value'],'units':result['quantity'],'events':result['events'],'elixir_units':sum(e['quantity'] for e in items if e['group']=='Elixirs'),'extra_units':sum(e['quantity'] for e in items if e['group']!='Elixirs'),'rare_units':result['rare'],'unpriced_types':result['unpriced'],'priced_types':result['priced_types'],'item_types':result['total_types']}
