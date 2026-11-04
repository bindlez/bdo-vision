"""Validate untrusted browser replies before they reach native widgets."""
import math
from craft_economy import craft_spec


def validate_reply(value,recipe):
    if not isinstance(value,dict):raise ValueError('Invalid crafting reply')
    if 'error' in value:
        if not isinstance(value['error'],str):raise ValueError('Invalid error')
        return {'error':value['error'][:400]}
    if value.get('recipe')!=recipe:raise ValueError('Recipe changed')
    for field in ('batches','maxCrafts'):
        if type(value.get(field)) is not int or not 0<=value[field]<=10**9:raise ValueError('Invalid crafts')
    for field in ('seconds','output','gross','profit','perHour','peak'):
        n=value.get(field)
        if n is None and field in ('gross','profit','perHour'):continue
        if type(n) not in (int,float) or not math.isfinite(n) or abs(n)>1e24:raise ValueError('Invalid model number')
    rows=value.get('rows')
    if not isinstance(rows,list) or len(rows)>12:raise ValueError('Too many ingredients')
    seen=set();spec=craft_spec()['items']
    for row in rows:
        ident=row.get('id') if isinstance(row,dict) else None
        if type(ident) is not int or str(ident) not in spec or ident in seen:raise ValueError('Invalid ingredient')
        seen.add(ident)
        if row.get('name')!=spec[str(ident)]['name']:raise ValueError('Invalid ingredient name')
        for field in ('ratio','quantity','leftover'):
            n=row.get(field)
            if type(n) not in (int,float) or not math.isfinite(n) or not 0<=n<=1e15:raise ValueError('Invalid ingredient count')
        if row['ratio']<=0 or row['quantity']!=row['ratio']*value['batches']:raise ValueError('Invalid ingredient ratio')
    if type(value.get('fits')) is not bool:raise ValueError('Invalid fit state')
    return {**value,'name':str(value.get('name',''))[:120],'note':str(value.get('note',''))[:400]}
