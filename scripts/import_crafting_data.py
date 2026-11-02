"""Normalize public factual recipe data, never another site's implementation.

Usage: python scripts/import_crafting_data.py PATH_TO_PUBLIC_JSON_SNAPSHOTS
Inputs: public-recipes/groups/metadata/mastery-{cooking,alchemy,processing}.json.
The snapshots are ordinary public calculator API responses, not user profiles.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize(folder):
    def load(name):
        return json.loads((folder / ('public-'+name+'.json')).read_bytes())['result']['data']
    raw, groups, metadata = load('recipes'), load('groups'), load('metadata')
    assets = ROOT / 'desktop/assets'
    previous = json.loads((assets/'recipes.json').read_text(encoding='utf-8'))
    legacy = {r['name']: r['id'] for r in previous if not r['id'].startswith('recipe:')}
    existing={r['recipeKey']:r['id'] for r in previous if r.get('recipeKey')}
    group_map = {g['groupId']: g['items'] for g in groups}
    result, assigned = [], set()
    for row in raw:
        item = metadata[str(row['productItemId'])]
        old_id = legacy.get(item['name'])
        ident = existing.get(row['recipeKey']) or (old_id if old_id and old_id not in assigned and old_id not in existing.values() else 'recipe:'+row['recipeKey'])
        assigned.add(ident)
        mats = []
        for mat in row['ingredients']:
            candidates = group_map[mat['groupId']] if mat['type']=='group' else [{'itemId':mat['itemId'], 'value':1}]
            chosen = next((v for v in candidates if v['value']==1), candidates[0])
            import math
            value = {'name':metadata[str(chosen['itemId'])]['name'], 'itemId':chosen['itemId'],
                     'qty':math.ceil(mat['quantity']/chosen['value']), 'required':mat['quantity'], 'value':chosen['value']}
            if mat['type']=='group': value['groupId']=mat['groupId']
            mats.append(value)
        result.append({'id':ident, 'recipeKey':row['recipeKey'], 'itemId':row['productItemId'],
                       'type':row['lifeskillType'], 'method':row.get('processingType',''), 'name':item['name'],
                       'secPerBatch':row.get('processingTime',10), 'minProc':row['minProc'], 'maxProc':row['maxProc'],
                       'xp':row['xp'], 'mats':mats, **({'rare':row['rareProc']} if row.get('rareProc') else {})})
    items = {ident:{'id':m['id'], 'name':m['name'], 'weight':m.get('weight',0),
                   **({'npcBuy':m['vendorPrice']} if m.get('vendorPrice',0) and m['vendorPrice']>0 else {})}
             for ident,m in metadata.items()}
    # Farming exchanges are outside the crafting metadata response, but CP uses them.
    items.setdefault('6717',{'id':6717,'name':'Special Pepper Seed','weight':0})
    items.setdefault('50804',{'id':50804,'name':'Stonetail Fodder','weight':0})
    for row in raw:
        if row.get('processingType','').startswith('imperial_'):
            ident=str(row['productItemId']);items[ident]['imperialBase']=metadata[ident]['buyPrice']
    spec = {'schema':1, 'date':'2026-11-02', 'source':'BDolytics public game-data calculator API',
            'sourceUrl':'https://bdolytics.com/en/crafting',
            'items':items, 'groups':{str(k):v for k,v in group_map.items()},
            'mastery':{activity:load('mastery-'+activity) for activity in ('cooking','alchemy','processing')},
            'byproducts':{'cooking':{'id':9780,'rate':.0236},'alchemy':{'id':9781,'rate':.26196}},
            'legacyIds':legacy, 'alchemyExtras':{'regular': [[5301, 10], [5302, 10], [6601, 10], [6602, 10], [6603, 10], [6604, 10], [6605, 10], [16001, 20.23], [4924, 9.78]], 'special': [[721002, 12.25], [4076, 12.86], [4481, 12.97], [4684, 4.7], [6183, 4.39], [44336, 11.9], [5019, 6.18], [5304, 9.73], [44195, 10.07], [4998, 8.46], [820910, 3.87], [5306, 2.63]], 'rare': [[16080, 10.66], [5964, 24.05], [721003, 24.97], [766107, 38.82], [45216, 0.5], [45248, 0.5], [45280, 0.5]]}}
    for name,body in [('recipes.json',result), ('crafting-data.json',spec)]:
        text=('[\n'+',\n'.join(json.dumps(row,ensure_ascii=False,separators=(',',':')) for row in body)+'\n]') if isinstance(body,list) else json.dumps(body,ensure_ascii=False,indent=2)
        (assets/name).write_text(text+'\n',encoding='utf-8')
    sources = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('public-*.json')}
    provenance = {'date':spec['date'], 'recipes':len(result), 'items':len(items), 'groups':len(groups),
                  'activities':dict(Counter(r['type'] for r in result)), 'sourceResponseSha256':sources,
                  'endpoints':['https://bdolytics.com/api/trpc/calculator.'+name for name in
                               ('getCraftingRecipes','getMaterialGroups','getCraftingItemMetadata','getMasteryCooking','getMasteryAlchemy','getMasteryProcessing')],
                  'modelConstantsSource':'https://bdolytics.com/en/crafting?category=alchemy',
                  'notes':'Factual normalized game data; original code/UI. Mastery formulas and byproduct rates are planning models, not guaranteed in-game yields. No minimum skill requirements supplied.'}
    (assets/'crafting-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print({k:provenance[k] for k in ('recipes','items','groups','activities')})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    normalize(parser.parse_args().folder)
