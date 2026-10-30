"""Read published NPC sell values only after the item ID and name agree."""
import html
import re
import urllib.request
from market_match import market_name_key


def parse_vendor_quote(markup,ident,name):
    title=re.search(r'<title>(.*?)</title>',markup,re.I|re.S)
    if not title:return None
    actual=html.unescape(re.sub('<[^>]*>','',title[1])).strip()
    actual=re.sub(r'\s*[-–]\s*BDO Codex\s*$','',actual,flags=re.I)
    if market_name_key(actual)!=market_name_key(name):return None
    text=html.unescape(re.sub('<[^>]*>',' ',markup))
    if not re.search(r'\bID:\s*'+str(int(ident))+r'\b',text):return None
    match=re.search(r'\bSell\s+price:\s*([\d,\s\u00a0]+)',text,re.I)
    if not match:return None
    value=int(re.sub(r'\D','',match[1]) or '0')
    if not 0<value<=1_000_000_000_000:return None
    return {'id':int(ident),'name':name,'price':value,'source_url':f'https://bdocodex.com/us/item/{int(ident)}/'}


def fetch_vendor_quote(ident,name):
    url=f'https://bdocodex.com/us/item/{int(ident)}/'
    with urllib.request.urlopen(url,timeout=6) as response:markup=response.read(2_000_000).decode('utf-8','replace')
    return parse_vendor_quote(markup,ident,name)
