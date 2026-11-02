"""Optional public market snapshot. Stream rows; retain only recipe item identities.

No polling or resident thread. Called only by the explicit opportunity refresh.
The provider's 14-day volume is divided by 14 and labeled as an average.
"""
import codecs
import json
import re
import time
import urllib.parse
import urllib.request


def market_rows(response,maximum=8_000_000,seconds=20):
    decoder=json.JSONDecoder();utf8=codecs.getincrementaldecoder('utf-8')()
    text='';total=0;started=False;end=time.monotonic()+seconds
    while True:
        if time.monotonic()>end:raise TimeoutError('Market snapshot exceeded its time budget')
        chunk=response.read(16384);total+=len(chunk)
        if total>maximum:raise ValueError('Market snapshot too large')
        text+=utf8.decode(chunk,final=not chunk)
        if not started:
            match=re.search(r'"data"\s*:\s*\[',text)
            if not match:
                if len(text)>1024 or not chunk:raise ValueError('Unexpected market response')
                continue
            text=text[match.end():];started=True
        while True:
            text=text.lstrip(' \r\n\t,')
            if text.startswith(']'):return
            try:row,used=decoder.raw_decode(text)
            except json.JSONDecodeError:break
            if not isinstance(row,dict):raise ValueError('Invalid market item')
            yield row;text=text[used:]
        if len(text)>262144:raise ValueError('Market row too large')
        if not chunk:raise ValueError('Incomplete market snapshot')


def fetch_recipe_market(region,items):
    if region not in ('NA','EU'):raise ValueError('Unknown market region')
    payload=urllib.parse.quote(json.dumps({'language':'en','region':region},separators=(',',':')))
    request=urllib.request.Request('https://bdolytics.com/api/trpc/market.getMarket?input='+payload,
        headers={'User-Agent':'BDO-Vision/1.13','Referer':'https://bdolytics.com/'})
    result=[]
    with urllib.request.urlopen(request,timeout=12) as response:
        for count,row in enumerate(market_rows(response)):
            if count>=30000:raise ValueError('Too many market rows')
            ident=row.get('itemId')
            if type(ident) is not int or str(ident) not in items:continue
            levels=row.get('enhancementLevels')
            base=next((r for r in levels if r.get('enhancementLevel')==0),None) if isinstance(levels,list) else row
            if base is None:continue
            value=base.get('price');name=row.get('name')
            if type(value) is not int or not 0<value<=10**12 or name!=items[str(ident)]['name']:continue
            entry={'id':ident,'name':name,'price':value,'region':region,'marketRegion':region,
                   'source':'BDolytics Central Market reference','price_basis':'market_reference'}
            volume=base.get('fourteenDayVolume');stock=base.get('inStock');stamp=row.get('updatedAt')
            if type(volume) is int and volume>=0:entry.update(fourteen_day_volume=volume,daily_volume=volume/14)
            if type(stock) is int and stock>=0:entry['stock']=stock
            if type(stamp) in (int,float) and 0<stamp<10**14:entry['source_updated_at']=stamp/1000
            result.append(entry)
    return result
